from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from romhop import config
from romhop.activity import ActivityEvent, ActivityKind


def _event(kind=ActivityKind.SYNC_PUSH, message="Synced save.sav"):
    return ActivityEvent(kind=kind, message=message)


def _error_event(message="Download failed"):
    return ActivityEvent(kind=ActivityKind.ERROR, message=message)


def _settings(**kwargs):
    s = config.default_settings()
    for k, v in kwargs.items():
        object.__setattr__(s, k, v)
    return s


# --- SettingsView toggle ---

def test_desktop_notif_toggle_exists_in_settings(qtbot):
    from romhop.gui.settings_view import SettingsView, DESKTOP_NOTIF_LABEL
    sv = SettingsView(config.default_settings())
    qtbot.addWidget(sv)
    assert DESKTOP_NOTIF_LABEL in sv._edits


def test_desktop_notif_toggle_disabled_when_unavailable(qtbot):
    from romhop.gui.settings_view import SettingsView, DESKTOP_NOTIF_LABEL
    sv = SettingsView(config.default_settings())
    qtbot.addWidget(sv)
    sv.set_desktop_notifications_available(False, "No tray")
    assert not sv._edits[DESKTOP_NOTIF_LABEL].isEnabled()


def test_desktop_notif_toggle_enabled_by_default(qtbot):
    from romhop.gui.settings_view import SettingsView, DESKTOP_NOTIF_LABEL
    sv = SettingsView(config.default_settings())
    qtbot.addWidget(sv)
    assert sv._edits[DESKTOP_NOTIF_LABEL].isEnabled()


def test_desktop_notif_disabled_survives_reset(qtbot):
    from romhop.gui.settings_view import SettingsView, DESKTOP_NOTIF_LABEL
    sv = SettingsView(config.default_settings())
    qtbot.addWidget(sv)
    sv.set_desktop_notifications_available(False, "No tray")
    sv.reset()
    assert not sv._edits[DESKTOP_NOTIF_LABEL].isEnabled()


# --- MainWindow._on_activity_desktop_notify ---

def _make_window_with_mock_tray(qtbot, settings=None):
    from romhop.gui.main_window import MainWindow
    if settings is None:
        settings = config.default_settings()
    win = MainWindow(settings=settings)
    qtbot.addWidget(win)
    mock_tray = MagicMock()
    win.tray = mock_tray
    return win, mock_tray


def test_notif_fires_when_unfocused_and_enabled(qtbot):
    settings = _settings(desktop_notifications=True)
    win, mock_tray = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = None  # window not focused
        win._on_activity_desktop_notify(_event())

    mock_tray.showMessage.assert_called_once()


def test_notif_gated_when_window_focused_and_visible(qtbot):
    settings = _settings(desktop_notifications=True)
    win, mock_tray = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings
    win.show()

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = win  # window IS focused
        win._on_activity_desktop_notify(_event())

    mock_tray.showMessage.assert_not_called()


def test_notif_suppressed_when_setting_off(qtbot):
    settings = _settings(desktop_notifications=False)
    win, mock_tray = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = None
        win._on_activity_desktop_notify(_event())

    mock_tray.showMessage.assert_not_called()


def test_notif_suppressed_when_no_tray(qtbot):
    settings = _settings(desktop_notifications=True)
    win, _ = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings
    win.tray = None  # no tray

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = None
        win._on_activity_desktop_notify(_event())
    # no AttributeError = pass (tray is None, no call attempted)


def test_notif_uses_critical_icon_for_errors(qtbot):
    settings = _settings(desktop_notifications=True)
    win, mock_tray = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = None
        win._on_activity_desktop_notify(_error_event())

    args = mock_tray.showMessage.call_args
    from PySide6.QtWidgets import QSystemTrayIcon
    assert args[0][2] == QSystemTrayIcon.MessageIcon.Critical


def test_notif_uses_info_icon_for_non_errors(qtbot):
    settings = _settings(desktop_notifications=True)
    win, mock_tray = _make_window_with_mock_tray(qtbot, settings)
    win._settings = settings

    with patch("romhop.gui.main_window.QApplication") as mock_app:
        mock_app.activeWindow.return_value = None
        win._on_activity_desktop_notify(_event())

    args = mock_tray.showMessage.call_args
    from PySide6.QtWidgets import QSystemTrayIcon
    assert args[0][2] == QSystemTrayIcon.MessageIcon.Information
