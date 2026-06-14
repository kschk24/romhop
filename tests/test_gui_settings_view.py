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
