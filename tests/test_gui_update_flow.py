from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from romhop import config
from romhop.gui.main_window import MainWindow
from romhop.update import AssetInfo, UpdateInfo

_FAKE_INFO = UpdateInfo(
    version="0.4.0",
    asset=AssetInfo(name="romhop-0.4.0.AppImage", url="https://example.com/x", size=1000),
    sha256sums_url="https://example.com/SHA256SUMS",
)


def _window(qtbot, **overrides):
    kwargs = dict(
        update_check_fn=lambda: None,
        update_apply_fn=lambda info, cb: None,
        relaunch_fn=None,
    )
    kwargs.update(overrides)
    w = MainWindow(settings=config.default_settings(), **kwargs)
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Banner visibility
# ---------------------------------------------------------------------------

def test_banner_shown_when_update_available(qtbot):
    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO)
    w.check_for_updates()
    qtbot.waitUntil(lambda: w.update_banner.isVisibleTo(w), timeout=2000)
    assert "0.4.0" in w.update_banner.text()


def test_banner_hidden_when_no_update(qtbot):
    w = _window(qtbot, update_check_fn=lambda: None)
    w.check_for_updates()
    qtbot.wait(200)
    assert not w.update_banner.isVisibleTo(w)


def test_later_hides_banner(qtbot):
    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO)
    w.check_for_updates()
    qtbot.waitUntil(lambda: w.update_banner.isVisibleTo(w), timeout=2000)
    w._update_later_btn.click()
    assert not w.update_banner.isVisibleTo(w)


# ---------------------------------------------------------------------------
# Controls hidden when auto-update unsupported
# ---------------------------------------------------------------------------

def test_controls_hidden_when_unsupported(qtbot):
    w = _window(qtbot, update_check_fn=None)
    assert not w.settings_view.update_check_btn.isVisibleTo(w.settings_view)
    w.check_for_updates()
    qtbot.wait(100)
    assert not w.update_banner.isVisibleTo(w)


def test_check_btn_visible_when_supported(qtbot):
    w = _window(qtbot, update_check_fn=lambda: None)
    assert w.settings_view.update_check_btn.isVisibleTo(w.settings_view)


# ---------------------------------------------------------------------------
# Apply + progress
# ---------------------------------------------------------------------------

def test_update_clicked_invokes_apply(qtbot):
    applied: list[object] = []

    def fake_apply(info, cb):
        applied.append(info)
        cb(100, 100)

    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO, update_apply_fn=fake_apply)
    w.check_for_updates()
    qtbot.waitUntil(lambda: w.update_banner.isVisibleTo(w), timeout=2000)
    w._on_update_clicked()
    qtbot.waitUntil(lambda: len(applied) == 1, timeout=2000)
    assert applied[0] is _FAKE_INFO


def test_update_progress_shown(qtbot):
    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO)
    w._claim_progress("update")
    w._on_update_progress(50, 100)
    assert w.progress_bar.isVisibleTo(w)
    assert w.progress_bar.value() == w._PROGRESS_SCALE // 2


# ---------------------------------------------------------------------------
# Restart / relaunch
# ---------------------------------------------------------------------------

def test_relaunch_fn_called_after_apply(qtbot, monkeypatch):
    relaunched: list[bool] = []

    def fake_apply(info, cb):
        pass

    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.information",
        lambda *a, **kw: None,
    )
    w = _window(
        qtbot,
        update_check_fn=lambda: _FAKE_INFO,
        update_apply_fn=fake_apply,
        relaunch_fn=lambda: relaunched.append(True),
    )
    w.check_for_updates()
    qtbot.waitUntil(lambda: w.update_banner.isVisibleTo(w), timeout=2000)
    w._on_update_clicked()
    qtbot.waitUntil(lambda: len(relaunched) == 1, timeout=2000)


def test_no_relaunch_when_fn_is_none(qtbot, monkeypatch):
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.information",
        lambda *a, **kw: None,
    )
    w = _window(
        qtbot,
        update_check_fn=lambda: _FAKE_INFO,
        update_apply_fn=lambda info, cb: None,
        relaunch_fn=None,
    )
    w._on_update_applied()  # should not raise even without relaunch_fn


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_update_failed_does_not_crash(qtbot):
    def bad_check():
        raise RuntimeError("network down")

    w = _window(qtbot, update_check_fn=bad_check)
    w.check_for_updates()
    qtbot.wait(300)
    # No exception raised, banner stays hidden
    assert not w.update_banner.isVisibleTo(w)


# ---------------------------------------------------------------------------
# Thread cleanup
# ---------------------------------------------------------------------------

def test_check_for_updates_twice_no_dangling_thread(qtbot):
    """Second call cleans up the first worker; only one result arrives."""
    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO)
    w.check_for_updates()
    w.check_for_updates()
    qtbot.waitUntil(lambda: w.update_banner.isVisibleTo(w), timeout=3000)
    assert "0.4.0" in w.update_banner.text()
    # First worker was replaced — current worker must have finished
    assert w._check_worker is not None
    assert not w._check_worker.isRunning()


# ---------------------------------------------------------------------------
# Progress bar ownership / isolation (TASK-029)
# ---------------------------------------------------------------------------

def test_update_apply_cancels_active_download_and_claims_bar(qtbot):
    """Update click cancels in-flight download and takes ownership of the bar."""
    cancelled: list[bool] = []

    class _FakeWorker:
        def cancel(self):
            cancelled.append(True)

        def was_cancelled(self):
            return True

        def deleteLater(self):
            pass

    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO, update_apply_fn=lambda i, cb: None)
    w._download_worker = _FakeWorker()  # type: ignore[assignment]
    w._pending_update = _FAKE_INFO
    w._on_update_clicked()

    assert len(cancelled) == 1
    assert w._progress_owner == "update"
    assert "Updating" in w.progress_bar.format()


def test_late_download_teardown_does_not_hide_update_bar(qtbot):
    """_on_batch_finished fired after update claimed bar must not hide the bar."""
    w = _window(qtbot)
    w._claim_progress("update")
    w.progress_bar.setFormat("Updating…")

    # Simulate a stale _on_batch_finished (download worker already None).
    w._on_batch_finished()

    assert w._progress_owner == "update"
    assert w.progress_bar.isVisibleTo(w)
    assert "Updating" in w.progress_bar.format()


def test_download_start_refused_during_update(qtbot):
    """_start_download is a no-op when update owns the bar."""
    from romhop.romm_client import Rom

    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]

    def action(rom, on_progress, stop_event, on_event=None):
        return rom.name

    w = _window(qtbot, update_check_fn=lambda: _FAKE_INFO,
                update_apply_fn=lambda i, cb: None)
    w._download_action = action
    w._progress_owner = "update"
    w.download_btn.setEnabled(False)

    w._start_download(roms)

    assert w._download_worker is None
    assert not w.download_btn.isEnabled()


def test_update_failure_releases_bar_and_reenables_download(qtbot):
    """_on_update_failed must release the bar and re-enable the download button."""
    w = _window(qtbot)
    w._claim_progress("update")
    w.download_btn.setEnabled(False)

    w._on_update_failed("network error")

    assert w._progress_owner is None
    assert w.progress_bar.isHidden()
    assert w.download_btn.isEnabled()
