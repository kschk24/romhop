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
        download_action=lambda rom: called.append(rom.name),
    )
    qtbot.addWidget(win)
    win.load_library()
    check, rom = next(iter(win.library._checks.values()))
    check.setChecked(True)
    with qtbot.waitSignal(win.downloads_finished, timeout=2000):
        win.download_selected()
    assert called == ["Sonic"]
