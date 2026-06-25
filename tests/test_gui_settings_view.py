from pathlib import Path

from PySide6.QtWidgets import QLineEdit

from romhop import config
from romhop.gui.settings_view import SettingsView, TOKEN_LABEL


def _labels_for(category):
    return [f.label for f in config.SCHEMA if f.category == category]


def test_view_has_one_groupbox_per_category_in_order(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    titles = [g.title() for g in view._groups]
    assert titles == [config.CATEGORY_LABELS[c] for c in config.CATEGORY_ORDER]


def test_view_edits_keyed_by_schema_label(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    expected = {f.label for f in config.SCHEMA}
    assert set(view._edits.keys()) == expected


def test_bool_field_is_checkbox_others_are_lineedit(qtbot):
    from PySide6.QtWidgets import QCheckBox, QLineEdit
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    assert isinstance(view._edits["Enable save sync"], QCheckBox)
    assert isinstance(view._edits["RomM URL"], QLineEdit)


def test_field_tooltip_comes_from_help(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    spec = next(f for f in config.SCHEMA if f.key == "romm_url")
    assert view._edits["RomM URL"].toolTip() == spec.help


def test_initial_values_populate_from_settings(qtbot):
    s = config.default_settings()
    s.romm_url = "https://romm.example"
    s.sync_enabled = True
    view = SettingsView(s)
    qtbot.addWidget(view)
    assert view._edits["RomM URL"].text() == "https://romm.example"
    assert view._edits["Enable save sync"].isChecked() is True


def test_sync_check_attribute_points_at_sync_field(qtbot):
    s = config.default_settings()
    s.sync_enabled = True
    view = SettingsView(s)
    qtbot.addWidget(view)
    assert view.sync_check is view._edits["Enable save sync"]
    assert view.sync_check.isChecked() is True


def test_save_persists_all_fields_via_config(qtbot, monkeypatch):
    s = config.default_settings()
    view = SettingsView(s)
    qtbot.addWidget(view)

    saved = {}
    monkeypatch.setattr(config, "save_settings", lambda st: saved.update(s=st))
    view._edits["RomM URL"].setText("https://x")
    view._edits["Download limit (KB/s, 0 = unlimited)"].setText("512")
    view._edits["Enable save sync"].setChecked(True)
    with qtbot.waitSignal(view.saved, timeout=1000):
        view._on_save()
    assert saved["s"].romm_url == "https://x"
    assert saved["s"].download_rate_limit_kbps == 512
    assert saved["s"].sync_enabled is True


def test_token_row_is_masked_and_blank(qtbot, monkeypatch):
    monkeypatch.setattr(config, "get_token", lambda: "rmm_existing")
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    assert view.token_edit.echoMode() == QLineEdit.EchoMode.Password
    # Never echo the secret back into the widget; placeholder signals it's set.
    assert view.token_edit.text() == ""
    assert "leave blank" in view.token_edit.placeholderText().lower()


def test_blank_token_save_keeps_current(qtbot, monkeypatch):
    monkeypatch.setattr(config, "save_settings", lambda st: None)
    calls = []
    monkeypatch.setattr(config, "set_token", lambda t: calls.append(t))
    monkeypatch.setattr(config, "get_token", lambda: "rmm_existing")
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    with qtbot.waitSignal(view.saved, timeout=1000):
        view._on_save()
    assert calls == []  # blank field never clobbers the keyring


def test_nonblank_token_save_writes_keyring(qtbot, monkeypatch):
    monkeypatch.setattr(config, "save_settings", lambda st: None)
    calls = []
    monkeypatch.setattr(config, "set_token", lambda t: calls.append(t))
    monkeypatch.setattr(config, "get_token", lambda: None)
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.token_edit.setText("  rmm_new  ")  # stripped before store
    with qtbot.waitSignal(view.saved, timeout=1000):
        view._on_save()
    assert calls == ["rmm_new"]


def test_token_row_is_searchable(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.filter("api token")
    assert view.is_field_visible(TOKEN_LABEL)
    assert not view.is_field_visible("RomM URL")


def test_save_preserves_override_dicts(qtbot, monkeypatch):
    s = config.default_settings()
    s.platform_overrides = {"gba": "Game Boy Advance"}
    s.core_overrides = {"MyCore": "n64"}
    view = SettingsView(s)
    qtbot.addWidget(view)
    saved = {}
    monkeypatch.setattr(config, "save_settings", lambda st: saved.update(s=st))
    with qtbot.waitSignal(view.saved, timeout=1000):
        view._on_save()
    assert saved["s"].platform_overrides == {"gba": "Game Boy Advance"}
    assert saved["s"].core_overrides == {"MyCore": "n64"}


def test_cancel_discards_edits_and_emits(qtbot):
    s = config.default_settings()
    s.romm_url = "https://original"
    view = SettingsView(s)
    qtbot.addWidget(view)
    view._edits["RomM URL"].setText("https://edited")
    with qtbot.waitSignal(view.cancelled, timeout=1000):
        view._on_cancel()
    assert view._edits["RomM URL"].text() == "https://original"


def test_reset_repopulates_including_checkbox(qtbot):
    s = config.default_settings()
    s.romm_url = "https://original"
    s.sync_enabled = False
    view = SettingsView(s)
    qtbot.addWidget(view)
    view._edits["RomM URL"].setText("https://stale")
    view.sync_check.setChecked(True)
    view.reset()
    assert view._edits["RomM URL"].text() == "https://original"
    assert view.sync_check.isChecked() is False


def test_filter_hides_nonmatching_rows(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.filter("rom")
    assert view.is_field_visible("RomM URL")
    assert view.is_field_visible("Rom directory")
    assert not view.is_field_visible("Saves directory")


def test_filter_is_case_insensitive(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.filter("SAVES")
    assert view.is_field_visible("Saves directory")
    assert not view.is_field_visible("RomM URL")


def test_filter_empty_shows_all(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.filter("rom")
    view.filter("")
    for f in config.SCHEMA:
        assert view.is_field_visible(f.label)


def test_escape_key_cancels(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    with qtbot.waitSignal(view.cancelled, timeout=1000):
        ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape,
                       Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(view, ev)


def test_set_sync_enabled_mirrors_into_checkbox(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.set_sync_enabled(True)
    assert view.sync_check.isChecked() is True
    assert view.sync_enabled() is True


def test_focus_sync_is_callable(qtbot):
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    view.focus_sync()  # must not raise


def test_scan_button_emits_scan_requested(qtbot):
    s = config.default_settings()
    s.roms_root = Path("/games")
    view = SettingsView(s)
    qtbot.addWidget(view)
    with qtbot.waitSignal(view.scan_requested, timeout=500):
        view.scan_btn.click()


def test_scan_button_disabled_when_roms_root_unconfigured(qtbot):
    s = config.default_settings()
    assert not config.roms_root_configured(s)
    view = SettingsView(s)
    qtbot.addWidget(view)
    assert not view.scan_btn.isEnabled()


def test_set_scanning_toggles_busy_state(qtbot):
    s = config.default_settings()
    s.roms_root = Path("/games")
    view = SettingsView(s)
    qtbot.addWidget(view)
    view.set_scanning(True)
    assert not view.scan_btn.isEnabled()
    assert view.scan_btn.text() == "Scanning…"
    view.set_scanning(False)
    assert view.scan_btn.isEnabled()
    assert view.scan_btn.text() == "Scan local library"


def test_setup_button_emits_setup_requested(qtbot):
    from romhop.config import default_settings
    from romhop.gui.settings_view import SettingsView
    view = SettingsView(default_settings())
    qtbot.addWidget(view)
    with qtbot.waitSignal(view.setup_requested, timeout=1000):
        view.setup_btn.click()


def test_load_repopulates_from_new_settings(qtbot):
    from romhop.config import default_settings
    from romhop.gui.settings_view import SettingsView
    view = SettingsView(default_settings())
    qtbot.addWidget(view)
    s = default_settings()
    s.romm_url = "http://new.test"
    view.load(s)
    assert view._edits["RomM URL"].text() == "http://new.test"


def test_choice_field_renders_as_combobox_with_options(qtbot):
    from PySide6.QtWidgets import QComboBox
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    widget = view._edits["Theme"]
    assert isinstance(widget, QComboBox)
    items = [widget.itemText(i) for i in range(widget.count())]
    assert items == ["system", "light", "dark"]
    assert widget.currentText() == "system"


def test_choice_field_read_widget_returns_selected_text(qtbot):
    from PySide6.QtWidgets import QComboBox
    s = config.default_settings()
    s.theme_mode = "dark"
    view = SettingsView(s)
    qtbot.addWidget(view)
    widget = view._edits["Theme"]
    assert isinstance(widget, QComboBox)
    assert view._read_widget("Theme") == "dark"
