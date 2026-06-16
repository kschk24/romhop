from __future__ import annotations

from romhop.gui.setup_wizard import SetupWizard


def _noop_detect():
    return (None, None, False, False)


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
