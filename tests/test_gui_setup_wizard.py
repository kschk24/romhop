from __future__ import annotations

from pathlib import Path

from romhop.gui.setup_wizard import SetupWizard


def _noop_detect():
    return (None, None, False, False)


def test_wizard_prefills_from_initial_settings(qtbot):
    from romhop import config

    settings = config.default_settings()
    settings.romm_url = "http://romm.saved"
    settings.roms_root = Path("/games/roms")
    settings.saves_dir = Path("/games/saves")
    settings.states_dir = Path("/games/states")

    wiz = SetupWizard(validate_fn=lambda u, t: None, detect_retroarch_fn=_noop_detect,
                      persist=lambda s: None, initial_settings=settings)
    qtbot.addWidget(wiz)
    assert wiz.connection_page.url_edit.text() == "http://romm.saved"
    assert wiz.paths_page.roms_edit.text() == "/games/roms"
    assert wiz.paths_page.saves_edit.text() == "/games/saves"
    assert wiz.paths_page.states_edit.text() == "/games/states"


def test_wizard_skips_cwd_placeholder_roms_root(qtbot):
    from romhop import config

    settings = config.default_settings()  # roms_root defaults to "."
    wiz = SetupWizard(validate_fn=lambda u, t: None, detect_retroarch_fn=_noop_detect,
                      persist=lambda s: None, initial_settings=settings)
    qtbot.addWidget(wiz)
    assert wiz.paths_page.roms_edit.text() == ""
    assert wiz.paths_page.isComplete() is False


def test_connection_page_next_locked_until_validated(qtbot):
    def validate_ok(url, token):
        return None  # success

    wiz = SetupWizard(validate_fn=validate_ok, detect_retroarch_fn=_noop_detect,
                      persist=lambda s: None)
    qtbot.addWidget(wiz)
    page = wiz.connection_page
    page.url_edit.setText("http://romm.test")
    page.token_edit.setText("rmm_x")
    assert page.isComplete() is False  # not tested yet

    with qtbot.waitSignal(page.completeChanged, timeout=2000):
        page.test_connection()
    qtbot.waitUntil(lambda: page.isComplete() is True, timeout=2000)


def test_connection_page_edit_relocks_after_validation(qtbot):
    wiz = SetupWizard(validate_fn=lambda u, t: None,
                      detect_retroarch_fn=_noop_detect, persist=lambda s: None)
    qtbot.addWidget(wiz)
    page = wiz.connection_page
    page.url_edit.setText("http://romm.test")
    page.token_edit.setText("rmm_x")
    with qtbot.waitSignal(page.completeChanged, timeout=2000):
        page.test_connection()
    qtbot.waitUntil(lambda: page.isComplete() is True, timeout=2000)
    page.url_edit.setText("http://changed")  # editing must re-lock
    assert page.isComplete() is False


def test_connection_page_validation_failure_keeps_locked(qtbot):
    def validate_bad(url, token):
        raise RuntimeError("401 unauthorized")

    wiz = SetupWizard(validate_fn=validate_bad, detect_retroarch_fn=_noop_detect,
                      persist=lambda s: None)
    qtbot.addWidget(wiz)
    page = wiz.connection_page
    page.url_edit.setText("http://romm.test")
    page.token_edit.setText("bad")
    with qtbot.waitSignal(page.completeChanged, timeout=2000):
        page.test_connection()
    qtbot.wait(50)
    assert page.isComplete() is False
    assert "401" in page.status_label.text()


def test_paths_page_detect_fills_fields(qtbot, tmp_path):
    saves = tmp_path / "saves"
    states = tmp_path / "states"

    def detect():
        return (saves, states, True, False)

    wiz = SetupWizard(validate_fn=lambda u, t: None, detect_retroarch_fn=detect,
                      persist=lambda s: None)
    qtbot.addWidget(wiz)
    page = wiz.paths_page
    page.detect_retroarch()
    assert page.saves_edit.text() == str(saves)
    assert page.states_edit.text() == str(states)
    assert page.sort_saves is True
    assert page.sort_states is False


def test_paths_page_complete_requires_roms(qtbot):
    wiz = SetupWizard(validate_fn=lambda u, t: None,
                      detect_retroarch_fn=_noop_detect, persist=lambda s: None)
    qtbot.addWidget(wiz)
    page = wiz.paths_page
    assert page.isComplete() is False
    page.roms_edit.setText("/games/roms")
    assert page.isComplete() is True


def test_finish_persists_and_emits(qtbot, monkeypatch, tmp_path):
    import romhop.config as config
    saved = {}
    tokens = {}
    monkeypatch.setattr(config, "set_token", lambda t: tokens.setdefault("v", t))
    monkeypatch.setattr(config, "get_token", lambda: None)
    monkeypatch.setattr(config, "load_settings", config.default_settings)

    wiz = SetupWizard(validate_fn=lambda u, t: None,
                      detect_retroarch_fn=_noop_detect,
                      persist=lambda s: saved.setdefault("settings", s))
    qtbot.addWidget(wiz)
    wiz.connection_page.url_edit.setText("http://romm.test")
    wiz.connection_page.token_edit.setText("rmm_new")
    wiz.paths_page.roms_edit.setText(str(tmp_path / "roms"))
    wiz.paths_page.saves_edit.setText(str(tmp_path / "saves"))
    wiz.paths_page.states_edit.setText(str(tmp_path / "states"))
    wiz.scan_page.scan_check.setChecked(True)

    with qtbot.waitSignal(wiz.completed, timeout=2000) as blocker:
        wiz.accept()

    settings, do_scan = blocker.args
    assert saved["settings"].romm_url == "http://romm.test"
    assert str(saved["settings"].roms_root).endswith("roms")
    assert tokens["v"] == "rmm_new"
    assert do_scan is True


def test_finish_blank_token_keeps_existing(qtbot, monkeypatch, tmp_path):
    import romhop.config as config
    calls = []
    monkeypatch.setattr(config, "set_token", lambda t: calls.append(t))
    monkeypatch.setattr(config, "get_token", lambda: "rmm_existing")
    monkeypatch.setattr(config, "load_settings", config.default_settings)

    wiz = SetupWizard(validate_fn=lambda u, t: None,
                      detect_retroarch_fn=_noop_detect, persist=lambda s: None)
    qtbot.addWidget(wiz)
    wiz.connection_page.url_edit.setText("http://romm.test")
    wiz.paths_page.roms_edit.setText(str(tmp_path / "roms"))
    with qtbot.waitSignal(wiz.completed, timeout=2000):
        wiz.accept()
    assert calls == []  # blank token -> set_token never called


def test_main_window_run_setup_wizard_refreshes(qtbot, monkeypatch, tmp_path):
    import romhop.config as config
    from romhop.config import default_settings
    from romhop.gui.main_window import MainWindow

    monkeypatch.setattr(config, "set_token", lambda t: None)
    monkeypatch.setattr(config, "get_token", lambda: "rmm_x")
    monkeypatch.setattr(config, "load_settings", default_settings)
    monkeypatch.setattr(config, "save_settings", lambda s: None)  # never touch real config

    recreated = {}
    scans = []
    win = MainWindow(
        default_settings(),
        rom_provider=lambda: [],
        validate_fn=lambda u, t: None,
        detect_retroarch_fn=lambda: (None, None, False, False),
        recreate_client=lambda s: recreated.setdefault("settings", s),
        scan_action=lambda s: scans.append(s) or [],
    )
    qtbot.addWidget(win)

    # Drive the wizard programmatically instead of showing it modally.
    wiz = win._build_setup_wizard()
    wiz.connection_page.url_edit.setText("http://romm.test")
    wiz.paths_page.roms_edit.setText(str(tmp_path / "roms"))
    wiz.scan_page.scan_check.setChecked(False)
    with qtbot.waitSignal(wiz.completed, timeout=2000):
        wiz.accept()

    assert recreated["settings"].romm_url == "http://romm.test"
    assert win.settings_view._edits["RomM URL"].text() == "http://romm.test"
