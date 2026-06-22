from __future__ import annotations

import pytest

from romhop.activity import ActivityEvent, ActivityKind
from romhop.gui.toast import ToastManager, ToastWidget, _MAX_TOASTS


def _event(kind=ActivityKind.SYNC_PUSH, message="Synced game.sav"):
    return ActivityEvent(kind=kind, message=message)


def _error_event(message="Something went wrong"):
    return ActivityEvent(kind=ActivityKind.ERROR, message=message)


# --- ToastWidget ---

def test_toast_shows_message(qtbot):
    ev = _event(message="Synced save.sav")
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    labels = [c for c in toast.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)]
    texts = [lb.text() for lb in labels]
    assert any("Synced save.sav" in t for t in texts)


def test_toast_info_has_timer(qtbot):
    ev = _event()
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    assert toast._timer is not None
    assert toast._timer.isActive()


def test_toast_error_has_no_timer(qtbot):
    ev = _error_event()
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    assert toast._timer is None


def test_toast_closed_signal_on_dismiss(qtbot):
    ev = _event()
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    with qtbot.waitSignal(toast.closed, timeout=500):
        toast._dismiss()


def test_toast_timer_fires_dismiss(qtbot):
    ev = _event()
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    toast._timer.setInterval(50)
    with qtbot.waitSignal(toast.closed, timeout=500):
        pass  # timer fires on its own


def test_toast_error_sticky_no_auto_dismiss(qtbot):
    ev = _error_event()
    toast = ToastWidget(ev)
    qtbot.addWidget(toast)
    fired = []
    toast.closed.connect(lambda: fired.append(True))
    qtbot.wait(100)
    assert not fired


# --- ToastManager ---

class _FakeWindow:
    """Minimal stand-in for MainWindow — just needs a parent-widget interface."""

    def __init__(self, qtbot):
        from PySide6.QtWidgets import QWidget
        self._w = QWidget()
        qtbot.addWidget(self._w)
        self._w.resize(600, 400)
        # expose attributes ToastManager reads
        self.bottom = self._w

    # delegate enough QObject/QWidget interface for ToastManager
    def __getattr__(self, name):
        return getattr(self._w, name)


def _manager(qtbot):
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(600, 400)
    mgr = ToastManager(parent)
    return mgr, parent


def test_manager_adds_toasts(qtbot):
    mgr, parent = _manager(qtbot)
    mgr.post(_event(message="A"))
    mgr.post(_event(message="B"))
    assert len(mgr._toasts) == 2


def test_manager_caps_at_max(qtbot):
    mgr, parent = _manager(qtbot)
    for i in range(_MAX_TOASTS + 2):
        mgr.post(_event(message=f"msg {i}"))
    assert len(mgr._toasts) == _MAX_TOASTS


def test_manager_oldest_evicted_first(qtbot):
    mgr, parent = _manager(qtbot)
    for i in range(_MAX_TOASTS):
        mgr.post(_event(message=f"msg {i}"))
    mgr.post(_event(message="newest"))
    texts = [
        lbl.text()
        for t in mgr._toasts
        for lbl in t.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)
    ]
    assert "newest" in " ".join(texts)
    assert "msg 0" not in " ".join(texts)


def test_manager_removes_on_dismiss(qtbot):
    mgr, parent = _manager(qtbot)
    mgr.post(_event(message="A"))
    toast = mgr._toasts[0]
    toast._dismiss()
    qtbot.wait(50)
    assert len(mgr._toasts) == 0
