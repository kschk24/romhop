from __future__ import annotations


def test_status_icon_non_null_per_class(qtbot):
    from romhop.gui.tray import status_icon
    for cls in ("off", "running", "error"):
        assert not status_icon(cls).isNull()


def test_status_icon_unknown_class_falls_back(qtbot):
    from romhop.gui.tray import status_icon
    # An unexpected class must not raise; it falls back to the idle dot.
    assert not status_icon("bogus").isNull()
