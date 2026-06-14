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
