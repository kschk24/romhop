from __future__ import annotations


def test_status_icon_non_null_per_class(qtbot):
    from romhop.gui.tray import status_icon
    for cls in ("off", "running", "error"):
        assert not status_icon(cls).isNull()


def test_status_icon_unknown_class_falls_back(qtbot):
    from romhop.gui.tray import status_icon
    # An unexpected class must not raise; it falls back to the idle dot.
    assert not status_icon("bogus").isNull()


def test_tray_menu_emits_signals(qtbot):
    from romhop.gui.tray import TrayIcon
    tray = TrayIcon()
    show, quit_, toggled = [], [], []
    tray.show_requested.connect(lambda: show.append(1))
    tray.quit_requested.connect(lambda: quit_.append(1))
    tray.sync_toggled.connect(lambda on: toggled.append(on))
    tray._show_action.trigger()
    tray._quit_action.trigger()
    tray._sync_action.setChecked(True)
    assert show == [1]
    assert quit_ == [1]
    assert toggled == [True]


def test_set_sync_checked_does_not_echo(qtbot):
    from romhop.gui.tray import TrayIcon
    tray = TrayIcon()
    fired = []
    tray.sync_toggled.connect(lambda on: fired.append(on))
    tray.set_sync_checked(True)
    assert tray._sync_action.isChecked() is True
    assert fired == []  # programmatic mirror must not re-emit


def test_set_status_updates_tooltip_and_icon(qtbot):
    from romhop.gui.tray import TrayIcon
    tray = TrayIcon()
    tray.set_status("watching", "running")
    assert "watching" in tray.toolTip()
    assert not tray.icon().isNull()
