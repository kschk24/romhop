from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_blocking_message_boxes(monkeypatch):
    """Make OK-only QMessageBox popups non-blocking in tests.

    ``information``/``warning``/``critical`` open a modal dialog that waits for a
    manual click — that stalls the headless suite. Stub them to return ``Ok`` so
    the code path runs through without human interaction. ``question`` and
    ``.exec()`` carry branch logic, so they are left alone for tests to control.
    """
    try:
        from PySide6.QtWidgets import QMessageBox
    except ImportError:
        return

    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(
            QMessageBox, name, staticmethod(lambda *a, **kw: QMessageBox.Ok)
        )
