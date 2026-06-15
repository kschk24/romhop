from romhop import config


def test_main_window_builds_and_applies_theme(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    # Theme QSS is applied to the window.
    assert win.styleSheet() != ""
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
    assert win.settings_view.is_field_visible("RomM URL:")
    assert not win.settings_view.is_field_visible("Saves directory:")


def test_switching_into_settings_applies_current_query(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    # Query typed while in the library view...
    win.search.setText("saves")
    # ...takes effect on the settings rows once settings opens.
    win.show_settings()
    assert win.settings_view.is_field_visible("Saves directory:")
    assert not win.settings_view.is_field_visible("RomM URL:")


def test_switching_back_to_library_reapplies_query_to_library(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    win.show_settings()
    win.search.setText("zelda")
    # Returning to the library re-applies the query to the game list.
    win.show_library()
    assert win.library._query == "zelda"


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
        download_action=lambda rom, on_progress, stop_event: called.append(rom.name),
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
    assert "2/5" in win.progress_label.text()
    assert "Sonic" in win.progress_label.text()

    win._on_item_progress(50, 100, 2048.0)
    # Progress is tracked on a fixed permille scale (byte counts overflow the
    # bar's 32-bit range on large roms), so 50/100 reads as 500/1000.
    assert win.progress_bar.maximum() == 1000
    assert win.progress_bar.value() == 500

    win._end_progress()
    assert win.progress_bar.isHidden()
    assert win.progress_label.isHidden()


def test_download_selected_drives_progress_and_recovers(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]

    def action(rom, on_progress, stop_event):
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

    def watch_fn(stop_event):
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

    def watch_fn(stop_event):
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

    def watch_fn(stop_event):
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
    assert "Animal Crossing" in win.progress_label.text()
    assert "rescan" in win.progress_label.text().lower()
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
    txt = win.progress_label.text()
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
        def __init__(self, res, parent=None):
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

    def action(rom, on_progress, stop_event):
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


