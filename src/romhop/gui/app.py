from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run() -> None:
    import sys as _sys
    from pathlib import Path

    import platformdirs
    from PySide6.QtWidgets import QApplication

    from romhop.config import get_token, load_settings
    from romhop.download import download_rom
    from romhop.gui import covers
    from romhop.gui.main_window import MainWindow
    from romhop.mapping_cache import MappingCache
    from romhop.romm_client import RommClient
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

    def download_action(rom, on_progress=None):
        return download_rom(
            rom, client,
            roms_root=settings.roms_root,
            cache=cache,
            overrides=settings.platform_overrides,
            on_progress=on_progress,
        )

    def sync_watch_fn(stop_event):
        watch_and_push(
            [settings.saves_dir, settings.states_dir], cache, client,
            debounce_seconds=settings.sync_delay_seconds,
            core_overrides=settings.core_overrides,
            stop_event=stop_event,
        )

    app = QApplication(_sys.argv)
    window = MainWindow(
        settings=settings,
        rom_provider=rom_provider,
        download_action=download_action,
        sync_watch_fn=sync_watch_fn,
        cover_provider=cover_provider,
        platform_label=platform_label,
        platform_names=names,
    )
    window.resize(900, 600)
    # An unconfigured or unreachable RomM must not crash startup: open the
    # window empty and surface the failure in the status bar instead.
    try:
        window.load_library()
    except Exception as exc:  # noqa: BLE001 - keep the window alive
        logger.warning("Could not load RomM library at startup: %s", exc)
        window.set_sync_status(f"library load failed: {exc}")
    window.show()
    _sys.exit(app.exec())
