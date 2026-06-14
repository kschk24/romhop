from romhop import config
from romhop.gui import settings_view


def test_settings_to_rows_lists_editable_fields():
    s = config.default_settings()
    s.romm_url = "https://romm.example"
    rows = settings_view.settings_to_rows(s)
    assert rows["romm_url"] == "https://romm.example"
    assert "sync_delay_seconds" in rows
    assert "roms_root" in rows


def test_apply_rows_updates_settings():
    s = config.default_settings()
    updated = settings_view.apply_rows(s, {
        "romm_url": "https://x",
        "roms_root": "/games",
        "saves_dir": "/saves",
        "states_dir": "/states",
        "sync_delay_seconds": "12",
    })
    assert updated.romm_url == "https://x"
    assert str(updated.roms_root) == "/games"
    assert updated.sync_delay_seconds == 12.0
    assert updated.theme == s.theme
    assert updated.platform_overrides == s.platform_overrides


def test_settings_view_builds_with_all_fields(qtbot):
    from romhop.gui.settings_view import SettingsView, EDITABLE_FIELDS
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)
    assert set(view._edits.keys()) == set(EDITABLE_FIELDS)


def test_settings_view_cancel_discards_edits_and_emits(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    s.romm_url = "https://original"
    view = SettingsView(s)
    qtbot.addWidget(view)
    # User types a change but then cancels.
    view._edits["romm_url"].setText("https://edited")
    with qtbot.waitSignal(view.cancelled, timeout=1000):
        view._on_cancel()
    # Edited text is reverted to the original (changes discarded).
    assert view._edits["romm_url"].text() == "https://original"


def test_settings_view_reset_repopulates_from_settings(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    s.romm_url = "https://original"
    view = SettingsView(s)
    qtbot.addWidget(view)
    view._edits["romm_url"].setText("https://stale")
    view.reset()
    assert view._edits["romm_url"].text() == "https://original"


def test_settings_view_filter_hides_nonmatching_rows(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)
    view.filter("rom")
    # Fields whose name contains the query stay visible; others hide.
    assert view.is_field_visible("romm_url")
    assert view.is_field_visible("roms_root")
    assert not view.is_field_visible("saves_dir")
    assert not view.is_field_visible("sync_delay_seconds")


def test_settings_view_filter_is_case_insensitive(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)
    view.filter("SAVES")
    assert view.is_field_visible("saves_dir")
    assert not view.is_field_visible("romm_url")


def test_settings_view_filter_empty_shows_all(qtbot):
    from romhop.gui.settings_view import SettingsView, EDITABLE_FIELDS
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)
    view.filter("rom")
    view.filter("")
    for field in EDITABLE_FIELDS:
        assert view.is_field_visible(field)


def test_settings_view_escape_key_cancels(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)
    with qtbot.waitSignal(view.cancelled, timeout=1000):
        ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape,
                       Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(view, ev)


def test_settings_view_has_sync_section_reflecting_enabled(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    s.sync_enabled = True
    view = SettingsView(s)
    qtbot.addWidget(view)
    assert view.sync_check.isChecked() is True


def test_settings_view_save_persists_sync_enabled(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    s.sync_enabled = False
    view = SettingsView(s)
    qtbot.addWidget(view)

    saved = {}
    monkeypatch.setattr(config, "save_settings", lambda st: saved.update(s=st))
    view.sync_check.setChecked(True)
    with qtbot.waitSignal(view.saved, timeout=1000):
        view._on_save()
    assert saved["s"].sync_enabled is True
    assert view.sync_enabled() is True


def test_settings_view_reset_restores_sync_checkbox(qtbot):
    from romhop.gui.settings_view import SettingsView
    s = config.default_settings()
    s.sync_enabled = False
    view = SettingsView(s)
    qtbot.addWidget(view)
    view.sync_check.setChecked(True)
    view.reset()
    assert view.sync_check.isChecked() is False


def test_settings_view_focus_sync_is_callable(qtbot):
    from romhop.gui.settings_view import SettingsView
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.focus_sync()  # must not raise; points the user at the sync section
