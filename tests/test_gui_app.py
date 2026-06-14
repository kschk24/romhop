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
    assert win.settings_view.is_field_visible("romm_url")
    assert not win.settings_view.is_field_visible("saves_dir")


def test_switching_into_settings_applies_current_query(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    # Query typed while in the library view...
    win.search.setText("saves")
    # ...takes effect on the settings rows once settings opens.
    win.show_settings()
    assert win.settings_view.is_field_visible("saves_dir")
    assert not win.settings_view.is_field_visible("romm_url")


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
    assert win.library.current_platform() == "genesis"


def test_download_selected_invokes_action(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]
    called = []
    win = MainWindow(
        settings=config.default_settings(),
        rom_provider=lambda: roms,
        download_action=lambda rom, on_progress: called.append(rom.name),
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
    assert win.progress_bar.maximum() == 100
    assert win.progress_bar.value() == 50

    win._end_progress()
    assert win.progress_bar.isHidden()
    assert win.progress_label.isHidden()


def test_download_selected_drives_progress_and_recovers(qtbot):
    from romhop.gui.main_window import MainWindow
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]

    def action(rom, on_progress):
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
        win.sync_toggle.setChecked(True)
    qtbot.waitUntil(lambda: "watching" in win.sync_status_text().lower(), timeout=2000)
    assert persisted[-1] is True

    # Toggle off -> worker stops, indicator returns to idle.
    win.sync_toggle.setChecked(False)
    qtbot.waitUntil(lambda: "idle" in win.sync_status_text().lower(), timeout=2000)
    assert persisted[-1] is False


def test_sync_indicator_click_opens_sync_settings(qtbot):
    from romhop.gui.main_window import MainWindow

    win = MainWindow(settings=config.default_settings())
    qtbot.addWidget(win)
    assert win.current_view_name() == "library"
    win._sync_label.click()
    assert win.current_view_name() == "settings"


def test_settings_save_reconciles_sync_toggle(qtbot, monkeypatch):
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "save_settings", lambda s: None)
    win = MainWindow(settings=config.default_settings(),
                     persist_settings=lambda s: None)
    qtbot.addWidget(win)
    assert win.sync_toggle.isChecked() is False

    # Enabling sync via the settings section + Save flips the bottom toggle.
    win.settings_view.sync_check.setChecked(True)
    win.settings_view._on_save()
    assert win.sync_toggle.isChecked() is True
