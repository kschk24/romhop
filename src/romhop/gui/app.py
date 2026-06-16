from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _prompt_purge_user_data() -> bool:
    """Ask (GUI) whether to also delete config + app data on uninstall.

    The "Uninstall RomHop" launcher runs with ``Terminal=false`` from the app
    menu, so there is no console to prompt on — use a QMessageBox. Default is No
    (a wipe is destructive). Returns False if Qt is unavailable rather than
    risking an unwanted delete.
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except Exception:
        return False
    QApplication.instance() or QApplication([])
    box = QMessageBox()
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle("Uninstall RomHop")
    box.setText("Also remove RomHop's settings and local cache?")
    box.setInformativeText(
        "Will delete:\n"
        "  • RomHop settings (settings.ini)\n"
        "  • RomHop cache (save↔game mapping, platform names)\n"
        "\n"
        "Will NOT touch:\n"
        "  • Your downloaded ROM library\n"
        "  • Your RetroArch save files and savestates"
    )
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec() == QMessageBox.Yes


def _notify_uninstalled() -> None:
    """Confirm completion to the user after a Linux uninstall.

    The "Uninstall RomHop" launcher runs with ``Terminal=false``, so the
    ``print`` below goes nowhere and the app just vanishes with no feedback
    (TASK-019). Show a blocking QMessageBox so the click has a visible result.
    Best-effort: a no-op if Qt is unavailable (the print still serves a shell).
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except Exception:
        return
    QApplication.instance() or QApplication([])
    box = QMessageBox()
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("RomHop uninstalled")
    box.setText("RomHop has been removed.")
    box.setInformativeText(
        "The launcher and app files are gone.\n"
        "Your ROM library, saves, and savestates were left untouched."
    )
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()


def _maybe_uninstall(argv) -> bool:
    """Handle `--uninstall` for the Linux frozen install. Returns True if handled."""
    if "--uninstall" not in argv:
        return False
    import sys as _sys

    from romhop import config
    from romhop import install_bootstrap as ib
    from romhop.gui import launcher_install as li

    if _prompt_purge_user_data():
        config.purge_user_data()  # config + app data; never the ROM library
    li.uninstall_linux()          # remove .desktop entries + icons
    ib.unlink_cli()               # remove the ~/.local/bin/romhop CLI symlink
    ib.remove_install()           # remove the installed app dir
    print("romhop uninstalled")
    _notify_uninstalled()         # visible feedback (Terminal=false launcher)
    _sys.exit(0)


def _maybe_bootstrap(argv) -> bool:
    """Handle the AppImage first-run install. Returns True if handled (caller exits).

    Extraction/install errors propagate uncaught (no user-facing error UI yet).
    """
    if "--appimage-bootstrap" not in argv:
        return False
    import sys as _sys
    from pathlib import Path

    from romhop import install_bootstrap as ib
    from romhop.gui import launcher_install as li

    if not ib.is_installed():
        src = Path(_sys.executable).parent  # the onedir we are frozen into
        launcher = ib.extract_and_install(src)
        li.install_linux(exec_path=str(launcher))
        ib.link_cli()  # expose the CLI as ~/.local/bin/romhop
    ib.launch_installed()  # execv — does not return
    return True


def _maybe_smoke_exit(argv) -> bool:
    """CI headless check: build a QApplication and exit 0. Returns True if handled."""
    if "--smoke-exit" not in argv:
        return False
    import sys as _sys

    from PySide6.QtWidgets import QApplication

    QApplication(_sys.argv)  # fails loudly if the Qt platform plugin is missing
    print("romhop smoke ok")
    _sys.exit(0)


def run() -> None:
    import sys as _sys
    if _maybe_uninstall(_sys.argv):
        return
    if _maybe_bootstrap(_sys.argv):
        return
    if _maybe_smoke_exit(_sys.argv):
        return
    from pathlib import Path

    import platformdirs
    from PySide6.QtWidgets import QApplication

    from romhop import retroarch_cfg
    from romhop.config import get_token, is_configured, load_settings
    from romhop.download import download_rom, friendly_download_error, DownloadCancelled
    from romhop.gui import covers
    from romhop.gui.main_window import MainWindow
    from romhop.gui.single_instance import SingleInstance
    from romhop.mapping_cache import MappingCache
    from romhop.romm_client import RommClient
    from romhop.scan import run_scan
    from romhop.sync import watch_and_push

    settings = load_settings()
    client = RommClient(base_url=settings.romm_url, token=get_token() or "")
    cache_path = Path(platformdirs.user_data_dir("romhop")) / "mapping_cache.json"
    cache = MappingCache(cache_path)

    from romhop.platform_names import PlatformNames, display_name

    names = PlatformNames(Path(platformdirs.user_data_dir("romhop")) / "platform_names.json")

    def platform_label(rom):
        return display_name(rom, names)

    def rom_provider():
        roms = client.list_roms()
        names.update_from_roms(roms)
        return roms

    def cover_provider(rom):
        return covers.get_cover(rom, client)

    # Hold settings in a mutable box so the backend closures below always read
    # the current values. MainWindow swaps in a new Settings on save and calls
    # apply_settings, so changes (download limit, roms_root, sync dirs) take
    # effect live rather than only after a restart.
    live = {"settings": settings}

    def apply_settings(new_settings):
        live["settings"] = new_settings

    def download_action(rom, on_progress=None, stop_event=None):
        s = live["settings"]
        try:
            return download_rom(
                rom, client,
                roms_root=s.roms_root,
                cache=cache,
                overrides=s.platform_overrides,
                on_progress=on_progress,
                stop_event=stop_event,
                # Callable cap: read live each chunk so a limit change re-throttles
                # the in-flight download, not just the next rom in the batch.
                rate_limit_kbps=lambda: live["settings"].download_rate_limit_kbps,
            )
        except DownloadCancelled:
            raise  # let the worker classify this as a cancel, not an error
        except Exception as exc:  # surface a clear, actionable reason in the UI
            raise RuntimeError(friendly_download_error(rom.name, rom.id, exc)) from exc

    def sync_watch_fn(stop_event):
        s = live["settings"]
        watch_and_push(
            [s.saves_dir, s.states_dir], cache, client,
            debounce_seconds=s.sync_delay_seconds,
            core_overrides=s.core_overrides,
            stop_event=stop_event,
        )

    def scan_action(settings):
        return run_scan(client, cache, names, settings)

    def validate_fn(url, token):
        # Throwaway client: base_url is baked into httpx.Client at construction,
        # so testing arbitrary creds means a fresh client, not the live one.
        RommClient(base_url=url, token=token).ping()

    def detect_retroarch_fn():
        folder = None
        if _sys.platform.startswith("win"):
            from PySide6.QtWidgets import QFileDialog
            picked = QFileDialog.getExistingDirectory(None, "RetroArch installation folder")
            folder = Path(picked) if picked else None
        return retroarch_cfg.detect(folder)

    def recreate_client(new_settings):
        # The wizard may have changed the URL and RommClient has no base_url
        # setter, so rebuild it. The closures above read `client` at call time,
        # so this nonlocal rebind takes effect for all of them.
        nonlocal client
        client = RommClient(base_url=new_settings.romm_url, token=get_token() or "")
        apply_settings(new_settings)

    app = QApplication(_sys.argv)
    # Hiding the window must not quit the app — the sync worker lives on.
    app.setQuitOnLastWindowClosed(False)

    # Single instance: if one is already up, ask it to surface and exit.
    instance = SingleInstance()
    if instance.is_running():
        return
    instance.listen()

    window = MainWindow(
        settings=settings,
        rom_provider=rom_provider,
        download_action=download_action,
        sync_watch_fn=sync_watch_fn,
        cover_provider=cover_provider,
        platform_label=platform_label,
        platform_names=names,
        scan_action=scan_action,
        apply_token=lambda t: client.set_token(t),  # late-bind: recreate_client may swap client
        apply_settings=apply_settings,
        validate_fn=validate_fn,
        detect_retroarch_fn=detect_retroarch_fn,
        recreate_client=recreate_client,
    )
    instance.activated.connect(window.show_and_raise)
    window.resize(900, 600)
    if not is_configured(settings):
        # Unconfigured: guide the user before trying to talk to RomM. The
        # wizard's completion handler refreshes the library itself; a cancel
        # leaves the window empty (nothing to load anyway).
        window.show()
        window.run_setup_wizard()
    else:
        # Configured by presence (URL + token), but presence != reachability: a
        # bad/stale URL or revoked token passes is_configured yet fails here. Open
        # the window, surface the failure, and guide the user back into the wizard
        # so they can fix it instead of staring at an empty, silent library.
        window.show()
        try:
            window.load_library()
        except Exception as exc:  # noqa: BLE001 - keep the window alive
            logger.warning("Could not load RomM library at startup: %s", exc)
            window.set_sync_status(f"library load failed: {exc}")
            window.run_setup_wizard()
    _sys.exit(app.exec())
