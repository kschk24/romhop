from romhop import config
from romhop.romm_client import Rom, RomDetail


def test_main_window_does_not_self_theme(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    # Theme is applied at app level; MainWindow must not set its own stylesheet.
    assert win.styleSheet() == ""
    # Bottom bar starts in the idle sync state.
    assert "idle" in win.sync_status_text().lower()


def test_main_window_toggles_to_settings(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.show_settings()
    assert win.current_view_name() == "settings"
    win.show_library()
    assert win.current_view_name() == "library"


def test_gear_toggles_back_out_of_settings(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.toggle_settings()
    assert win.current_view_name() == "settings"
    # Gear pressed again returns to the library (no save required).
    win.toggle_settings()
    assert win.current_view_name() == "library"


def test_search_filters_settings_when_settings_active(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.show_settings()
    win.search.setText("rom")
    # In settings, the search box filters settings rows, not the library.
    assert win.settings_view.is_field_visible("RomM URL")
    assert not win.settings_view.is_field_visible("Saves directory")


def test_search_clears_on_view_switch(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.search.setText("zelda")
    win.show_settings()
    assert win.search.text() == ""


def test_cancelling_settings_returns_to_library(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.show_settings()
    win.settings_view.cancelled.emit()
    assert win.current_view_name() == "library"


def test_load_library_populates_view(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]
    win = MainWindow(settings=config.default_settings(), rom_provider=lambda: roms)
    qtbot.addWidget(win)
    win.load_library()
    # Library should have populated with the Sonic rom (flat grid; no sidebar).
    assert any(rom.platform_slug == "genesis" for _, rom in win.library._checks.values())


def test_download_selected_invokes_action(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]
    called = []
    win = MainWindow(
        settings=config.default_settings(),
        rom_provider=lambda: roms,
        download_action=lambda rom, on_progress, stop_event, on_event=None: called.append(rom.name),
    )
    qtbot.addWidget(win)
    win.load_library()
    check, rom = next(iter(win.library._checks.values()))
    check.setChecked(True)
    with qtbot.waitSignal(win.downloads_finished, timeout=2000):
        win.download_selected()
    assert called == ["Sonic"]


def test_progress_slots_update_bottom_bar(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    # Idle: progress widgets hidden.
    assert win.progress_bar.isHidden()
    assert win.progress_label.isHidden()

    win._begin_progress()
    win._on_item_started(2, 5, "Sonic")
    assert not win.progress_bar.isHidden()
    assert "2/5" in win.progress_bar.format()
    assert "Sonic" in win.progress_bar.format()

    win._on_item_progress(50, 100, 2048.0)
    # Progress is tracked on a fixed permille scale (byte counts overflow the
    # bar's 32-bit range on large roms), so 50/100 reads as 500/1000.
    assert win.progress_bar.maximum() == 1000
    assert win.progress_bar.value() == 500

    win._end_progress()
    assert win.progress_bar.isHidden()
    assert win.progress_label.isHidden()


def test_progress_label_does_not_clip(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSizePolicy

    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    policy = win.progress_label.sizePolicy().horizontalPolicy()
    assert policy in (QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
    assert win.progress_label.alignment() & Qt.AlignmentFlag.AlignLeft


def test_download_selected_drives_progress_and_recovers(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]

    def action(rom, on_progress, stop_event, on_event=None):
        on_progress(40, 100)
        on_progress(100, 100)
        return rom.name

    win = MainWindow(
        settings=config.default_settings(),
        rom_provider=lambda: roms,
        download_action=action,
    )
    qtbot.addWidget(win)
    win.load_library()
    check, rom = next(iter(win.library._checks.values()))
    check.setChecked(True)
    with qtbot.waitSignal(win.downloads_finished, timeout=2000):
        win.download_selected()
    # Button re-enabled and progress hidden once the batch settles.
    assert win.download_btn.isEnabled()
    assert win.progress_bar.isHidden()


def test_sync_toggle_starts_and_stops_worker(qtbot):
    from romhop.gui.main_window import MainWindow

    def watch_fn(stop_event, on_event=None):
        stop_event.wait(timeout=2)

    persisted = []
    win = MainWindow(
        settings=config.default_settings(),
        sync_watch_fn=watch_fn,
        persist_settings=lambda s: persisted.append(s.sync_enabled),
    )
    qtbot.addWidget(win)

    # Toggle on -> worker runs, indicator shows "watching", setting persisted.
    with qtbot.waitSignal(win._sync_status_changed, timeout=2000):
        win.sync_button.setChecked(True)
    qtbot.waitUntil(lambda: "watching" in win.sync_status_text().lower(), timeout=2000)
    assert persisted[-1] is True

    # Toggle off -> worker stops, indicator returns to idle.
    win.sync_button.setChecked(False)
    qtbot.waitUntil(lambda: "idle" in win.sync_status_text().lower(), timeout=2000)
    assert persisted[-1] is False


def test_sync_button_dot_reflects_running_state(qtbot):
    from romhop.gui.main_window import MainWindow

    def watch_fn(stop_event, on_event=None):
        stop_event.wait(timeout=2)

    win = MainWindow(
        settings=config.default_settings(),
        sync_watch_fn=watch_fn,
        persist_settings=lambda s: None,
    )
    qtbot.addWidget(win)

    # At rest the dot is grey ("off").
    assert win.sync_state() == "off"
    # Running -> green dot.
    with qtbot.waitSignal(win._sync_status_changed, timeout=2000):
        win.sync_button.setChecked(True)
    qtbot.waitUntil(lambda: win.sync_state() == "running", timeout=2000)
    # Stopped -> back to grey.
    win.sync_button.setChecked(False)
    qtbot.waitUntil(lambda: win.sync_state() == "off", timeout=2000)


def test_sync_enabled_on_startup_starts_worker(qtbot):
    from dataclasses import replace
    from romhop.gui.main_window import MainWindow

    def watch_fn(stop_event, on_event=None):
        stop_event.wait(timeout=2)

    # Persisted sync_enabled=True: the dot must go green without any user toggle.
    win = MainWindow(
        settings=replace(config.default_settings(), sync_enabled=True),
        sync_watch_fn=watch_fn,
        persist_settings=lambda s: None,
    )
    qtbot.addWidget(win)

    assert win.sync_button.isChecked() is True
    qtbot.waitUntil(lambda: win.sync_state() == "running", timeout=2000)


def test_bottom_toggle_propagates_to_settings_menu(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None)
    qtbot.addWidget(win)
    # Both controls start in agreement (off).
    assert win.sync_button.isChecked() is False
    assert win.settings_view.sync_check.isChecked() is False

    # Flipping the bottom button must be reflected in the settings menu.
    win.sync_button.setChecked(True)
    win.show_settings()
    assert win.settings_view.sync_check.isChecked() is True


def test_settings_save_reconciles_sync_toggle(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "save_settings", lambda s: None)
    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None)
    qtbot.addWidget(win)
    assert win.sync_button.isChecked() is False

    # Enabling sync via the settings section + Save flips the bottom button.
    win.settings_view.sync_check.setChecked(True)
    win.settings_view._on_save()
    assert win.sync_button.isChecked() is True


def test_settings_save_pushes_live_settings_to_apply_callback(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "save_settings", lambda s: None)
    applied = []
    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None,
                     apply_settings=lambda s: applied.append(s))
    qtbot.addWidget(win)

    # Change the download limit in the form and save: the live settings (the ones
    # download_action reads) must be refreshed, not just the in-window copy.
    label = "Download limit (KB/s, 0 = unlimited)"
    win.settings_view._edits[label].setText("500")
    win.settings_view._on_save()
    assert applied and applied[-1].download_rate_limit_kbps == 500


def test_token_save_applies_to_live_client_and_reloads(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "save_settings", lambda s: None)
    monkeypatch.setattr(config, "set_token", lambda t: None)
    monkeypatch.setattr(config, "get_token", lambda: None)
    applied = []
    loads = []
    win = MainWindow(settings=config.default_settings(),
                     rom_provider=lambda: loads.append(1) or [],
                     apply_token=lambda t: applied.append(t))
    qtbot.addWidget(win)
    loads.clear()  # ignore any startup load

    win.settings_view.token_edit.setText("rmm_new")
    win.settings_view._on_save()
    assert applied == ["rmm_new"]  # pushed onto the live client
    assert loads == [1]  # library refreshed without restart


def test_blank_token_save_does_not_apply_or_reload(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "save_settings", lambda s: None)
    monkeypatch.setattr(config, "get_token", lambda: "rmm_existing")
    applied = []
    loads = []
    win = MainWindow(settings=config.default_settings(),
                     rom_provider=lambda: loads.append(1) or [],
                     apply_token=lambda t: applied.append(t))
    qtbot.addWidget(win)
    loads.clear()

    win.settings_view._on_save()  # token field left blank
    assert applied == []
    assert loads == []


def test_filter_bar_hidden_in_settings_shown_in_library(qtbot):
    from romhop.gui.main_window import MainWindow
    win = MainWindow(config.default_settings(), rom_provider=lambda: [])
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    assert win.filter_bar.isVisible()
    win.show_settings()
    assert not win.filter_bar.isVisible()
    win.show_library()
    assert win.filter_bar.isVisible()


def test_load_library_populates_filter_platforms_and_downloaded(qtbot, monkeypatch, tmp_path):
    from romhop.gui import main_window
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    rom = Rom(id=1, name="Sonic", platform_slug="genesis", fs_name="Sonic.md",
              fs_name_no_ext="Sonic", file_names=["Sonic.md"], platform_name="Genesis")
    monkeypatch.setattr(main_window, "downloaded_rom_ids", lambda roms, root, ov: {1})

    settings = config.default_settings()
    from dataclasses import replace
    settings = replace(settings, roms_root=tmp_path)
    win = MainWindow(settings, rom_provider=lambda: [rom])
    qtbot.addWidget(win)
    win.load_library()
    assert win.filter_bar.platform_combo.itemText(1) == "Genesis"
    assert win.library._downloaded_ids == {1}


def test_filter_dropdown_uses_names_cache_when_platform_name_absent(qtbot, monkeypatch, tmp_path):
    from romhop.config import default_settings
    from dataclasses import replace
    from romhop.gui import main_window
    from romhop.gui.main_window import MainWindow
    from romhop.platform_names import PlatformNames
    from romhop.romm_client import Rom

    names = PlatformNames(tmp_path / "names.json")
    names.update_from_roms([Rom(id=9, name="x", platform_slug="gb", fs_name="x",
                                fs_name_no_ext="x", file_names=[], platform_name="Game Boy")])
    # A rom WITHOUT platform_name; the dropdown must fall back to the cache, not the slug.
    rom = Rom(id=1, name="Tetris", platform_slug="gb", fs_name="Tetris.gb",
              fs_name_no_ext="Tetris", file_names=["Tetris.gb"], platform_name=None)
    monkeypatch.setattr(main_window, "downloaded_rom_ids", lambda r, root, ov: set())

    settings = replace(default_settings(), roms_root=tmp_path)
    win = MainWindow(settings, rom_provider=lambda: [rom], platform_names=names)
    qtbot.addWidget(win)
    win.load_library()
    assert win.filter_bar.platform_combo.itemText(1) == "Game Boy"


def test_item_error_surfaces_in_download_area_not_sync(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    sync_before = win.sync_status_text()

    win._begin_progress()
    win._on_item_started(1, 1, "Animal Crossing")
    win._on_item_error("Animal Crossing", "no downloadable files (id 1542) — rescan in RomM")

    # The failure shows in the download progress label, with the rom + reason.
    assert "Animal Crossing" in win.progress_bar.format()
    assert "rescan" in win.progress_bar.format().lower()
    # ...and must NOT hijack the sync indicator.
    assert win.sync_status_text() == sync_before
    assert "error" not in win.sync_status_text().lower()


def test_progress_bar_handles_files_larger_than_int32(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win._begin_progress()
    win._on_item_started(1, 1, "Bravely Default")

    big = 4294967295  # 2**32 - 1, beyond QProgressBar's 32-bit range
    # Must not raise OverflowError (the bug: setMaximum(big) on a ~4GB file).
    win._on_item_progress(big // 2, big, 1024.0)

    assert win.progress_bar.maximum() > 0
    # Value stays a valid fraction within the bar's range.
    assert 0 <= win.progress_bar.value() <= win.progress_bar.maximum()
    assert abs(win.progress_bar.value() / win.progress_bar.maximum() - 0.5) < 0.05


def test_human_size_formats_bytes():
    from romhop.gui.main_window import _human_size
    assert _human_size(0) == "0 B"
    assert _human_size(1536) == "1.5 KB"
    assert _human_size(4294967295).endswith("GB")


def test_byte_indicator_shows_downloaded_over_total(qtbot):
    from romhop.gui.main_window import MainWindow
    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win._begin_progress()
    win._on_item_started(1, 1, "Bravely Default")
    big = 4294967295
    win._on_item_progress(big // 2, big, 5_000_000.0)
    txt = win.progress_bar.format()
    assert "/" in txt and "GB" in txt          # "2.0 / 4.0 GB"
    assert "MB/s" in txt


def test_run_scan_invokes_action_and_shows_dialog(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow
    from romhop.gui import main_window as mw
    from romhop.local_index import LocalGame, MatchResult
    from romhop import config
    from pathlib import Path

    result = MatchResult(
        matched=[], unmatched=[LocalGame("nes", "X.nes", ["X.nes"], "x")],
        collisions=[])
    called = {}

    def fake_scan(settings):
        called["ran"] = True
        return result

    shown = {}

    class FakeDialog:
        def __init__(self, res, parent=None, **kwargs):
            shown["result"] = res
        def exec(self):
            shown["execed"] = True

    monkeypatch.setattr(mw, "ScanResultDialog", FakeDialog)

    s = config.default_settings()
    s.roms_root = Path("/games")
    win = MainWindow(settings=s, scan_action=fake_scan)
    qtbot.addWidget(win)

    win.run_scan()
    qtbot.waitUntil(lambda: win._scan_worker is None, timeout=2000)

    assert called.get("ran") is True
    assert shown.get("result") is result
    assert shown.get("execed") is True


def test_run_scan_error_shows_message_box(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow
    from romhop.gui import main_window as mw
    from romhop import config
    from pathlib import Path

    def boom(settings):
        raise RuntimeError("no server")

    seen = {}
    monkeypatch.setattr(mw.QMessageBox, "critical",
                        lambda *a, **k: seen.setdefault("msg", a[-1]))

    s = config.default_settings()
    s.roms_root = Path("/games")
    win = MainWindow(settings=s, scan_action=boom)
    qtbot.addWidget(win)

    win.run_scan()
    qtbot.waitUntil(lambda: win._scan_worker is None, timeout=2000)

    assert "no server" in seen.get("msg", "")


def test_cancel_button_hidden_until_download_then_cancels(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom
    import threading
    roms = [Rom(id=1, name="A", platform_slug="gba", fs_name="A.gba",
                fs_name_no_ext="A", file_names=["A.gba"])]
    gate = threading.Event()

    def action(rom, on_progress, stop_event, on_event=None):
        gate.wait(timeout=2)               # hold until cancel fires
        return rom.name

    win = MainWindow(settings=config.default_settings(),
                     rom_provider=lambda: roms, download_action=action)
    qtbot.addWidget(win)
    win.load_library()
    assert win.cancel_btn.isHidden()       # hidden when idle

    check, rom = next(iter(win.library._checks.values()))
    check.setChecked(True)
    win.download_selected()
    assert not win.cancel_btn.isHidden()   # visible during a batch

    with qtbot.waitSignal(win.downloads_finished, timeout=2000):
        win.cancel_btn.click()
        gate.set()                         # let the held action return
    assert win._download_worker is None
    assert win.cancel_btn.isHidden()       # hidden again after the batch


def test_close_hides_to_tray_when_available(qtbot, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: True))
    from PySide6.QtGui import QCloseEvent
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.show()
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert not ev.isAccepted()   # close intercepted, app stays alive
    assert win.isHidden()
    assert win.tray is not None


def test_close_warns_and_hides_when_no_tray(qtbot, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: False))
    from PySide6.QtGui import QCloseEvent
    from romhop.gui.main_window import MainWindow

    warned = []
    win = MainWindow(settings=config.default_settings(),
                     confirm_no_tray=lambda: warned.append(True))
    qtbot.addWidget(win)
    win.show()
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert warned == [True]       # user warned once
    assert win.isHidden()         # still hides + keeps running headless
    assert win.tray is None


def test_tray_sync_toggle_propagates_to_button_and_settings(qtbot, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: True))
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None,
                     sync_watch_fn=lambda ev: ev.wait(timeout=2))
    qtbot.addWidget(win)
    win.tray._sync_action.setChecked(True)
    assert win.sync_button.isChecked() is True
    assert win.settings_view.sync_check.isChecked() is True


def test_set_sync_status_updates_tray_tooltip(qtbot, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: True))
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.set_sync_status("watching")
    assert "watching" in win.tray.toolTip()


def test_quit_app_stops_sync_then_quits(qtbot, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable",
                        staticmethod(lambda: True))
    from romhop.gui.main_window import MainWindow

    quit_called = []
    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None,
                     sync_watch_fn=lambda ev: ev.wait(timeout=5),
                     quit_fn=lambda: quit_called.append(True))
    qtbot.addWidget(win)
    win.sync_button.setChecked(True)
    qtbot.waitUntil(lambda: win._sync_worker is not None, timeout=2000)
    win.quit_app()
    qtbot.waitUntil(
        lambda: win._sync_worker is None or win._sync_worker.isFinished(),
        timeout=3000)
    assert quit_called == [True]


def test_tile_activation_shows_detail_panel(qtbot):
    from romhop.gui.main_window import MainWindow

    rom = Rom(id=1, name="Sonic", platform_slug="genesis",
              fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])
    win = MainWindow(settings=config.default_settings(),
                     rom_provider=lambda: [rom],
                     detail_provider=lambda r: RomDetail(summary="Fast."))
    qtbot.addWidget(win)
    win.load_library()
    assert win.detail_panel.isHidden()
    win.library.tile_activated.emit(rom)
    assert not win.detail_panel.isHidden()
    assert "Sonic" in win.detail_panel._name_label.text()


def test_sigint_handler_installed_and_fires_quit_app(qtbot, monkeypatch):
    import signal
    from PySide6.QtWidgets import QApplication
    from romhop import config
    from romhop.gui.app import _install_sigint_handler
    from romhop.gui.main_window import MainWindow

    app = QApplication.instance()
    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)

    quit_called = []
    monkeypatch.setattr(win, "quit_app", lambda: quit_called.append(True))

    _install_sigint_handler(app, win)

    handler = signal.getsignal(signal.SIGINT)
    assert callable(handler), "SIGINT handler must be set before app.exec()"

    # Simulate Ctrl-C: handler schedules quit_app via QTimer.singleShot(0, ...)
    handler(signal.SIGINT, None)
    qtbot.waitUntil(lambda: quit_called == [True], timeout=1000)




def test_dispatch_download_starts_worker(qtbot):
    from romhop.gui.main_window import MainWindow

    called = []
    def fake_download(rom, on_progress=None, stop_event=None, on_event=None):
        called.append(rom.id)

    win = MainWindow(settings=config.default_settings(), download_action=fake_download)
    qtbot.addWidget(win)
    rom = Rom(id=9, name="Kirby", platform_slug="gba",
              fs_name="Kirby.gba", fs_name_no_ext="Kirby", file_names=["Kirby.gba"])
    with qtbot.waitSignal(win.downloads_finished, timeout=3000):
        win._dispatch_action("download", rom)
    assert called == [9]


def test_dispatch_open_romm_calls_injected_fn(qtbot):
    from romhop.gui.main_window import MainWindow

    called = []
    win = MainWindow(settings=config.default_settings(),
                     open_in_romm=lambda r: called.append(r.id))
    qtbot.addWidget(win)
    rom = Rom(id=5, name="Sonic", platform_slug="genesis",
              fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])
    win._dispatch_action("open_romm", rom)
    assert called == [5]


def test_dispatch_open_folder_calls_injected_fn(qtbot):
    from romhop.gui.main_window import MainWindow

    called = []
    win = MainWindow(settings=config.default_settings(),
                     open_folder=lambda r: called.append(r.id))
    qtbot.addWidget(win)
    rom = Rom(id=3, name="Link", platform_slug="gbc",
              fs_name="Link.gbc", fs_name_no_ext="Link", file_names=["Link.gbc"])
    win._dispatch_action("open_folder", rom)
    assert called == [3]


def test_library_action_requested_routes_to_dispatch(qtbot):
    from romhop.gui.main_window import MainWindow

    called = []
    win = MainWindow(settings=config.default_settings(),
                     open_in_romm=lambda r: called.append(("open_romm", r.id)))
    qtbot.addWidget(win)
    rom = Rom(id=7, name="Mario", platform_slug="snes",
              fs_name="Mario.sfc", fs_name_no_ext="Mario", file_names=["Mario.sfc"])
    win.library.set_roms([rom])
    win.library.action_requested.emit("open_romm", rom)
    assert called == [("open_romm", 7)]


def test_detail_panel_open_romm_routes_to_dispatch(qtbot):
    from romhop.gui.main_window import MainWindow

    called = []
    win = MainWindow(settings=config.default_settings(),
                     open_in_romm=lambda r: called.append(r.id))
    qtbot.addWidget(win)
    rom = Rom(id=11, name="Metroid", platform_slug="nes",
              fs_name="Metroid.nes", fs_name_no_ext="Metroid", file_names=["Metroid.nes"])
    win.detail_panel.set_rom(rom)
    win.detail_panel.open_romm_requested.emit(rom)
    assert called == [11]
