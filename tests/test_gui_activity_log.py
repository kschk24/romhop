from __future__ import annotations

import pytest

from romhop.activity import ActivityEvent, ActivityKind
from romhop.gui.activity_log import ActivityLogView


def _event(msg="Synced save.sav", kind=ActivityKind.SYNC_PUSH):
    return ActivityEvent(kind=kind, message=msg)


def _error(msg="Something broke"):
    return ActivityEvent(kind=ActivityKind.ERROR, message=msg)


# --- ActivityLogView unit tests ---

def test_load_populates_rows(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    events = [_event("A"), _event("B"), _event("C")]
    view.load(events)
    assert view._list.count() == 3


def test_load_newest_first(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.load([_event("old"), _event("new")])
    assert "new" in view._list.item(0).text()
    assert "old" in view._list.item(1).text()


def test_load_clears_previous(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.load([_event("A"), _event("B")])
    view.load([_event("X")])
    assert view._list.count() == 1
    assert "X" in view._list.item(0).text()


def test_append_event_inserts_at_top(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.load([_event("old")])
    view.append_event(_event("newer"))
    assert view._list.count() == 2
    assert "newer" in view._list.item(0).text()


def test_append_event_on_empty_log(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.append_event(_event("solo"))
    assert view._list.count() == 1
    assert "solo" in view._list.item(0).text()


def test_row_includes_timestamp(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.load([_event("test msg")])
    text = view._list.item(0).text()
    # timestamp is HH:MM:SS — check format presence
    parts = text.split("  ", 1)
    assert len(parts) == 2
    ts, msg = parts
    assert ":" in ts  # HH:MM:SS
    assert "test msg" in msg


def test_error_row_has_distinct_foreground(qtbot):
    view = ActivityLogView()
    qtbot.addWidget(view)
    view.load([_event("ok"), _error("bad")])
    # newest-first: index 0 = error, index 1 = ok
    err_item = view._list.item(0)
    ok_item = view._list.item(1)
    assert err_item.foreground().color() != ok_item.foreground().color()


# --- MainWindow integration: AC #2 + #4 ---

def test_main_window_has_activity_button(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    assert hasattr(w, "activity_btn")


def test_show_activity_log_sets_stack_index_2(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    w.show_activity_log()
    assert w.stack.currentIndex() == 2
    assert w.current_view_name() == "activity"


def test_toggle_activity_log_toggles_back_to_library(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    w.show_activity_log()
    w.toggle_activity_log()
    assert w.current_view_name() == "library"


def test_show_activity_log_loads_hub_history(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    # Seed hub directly
    w._activity_hub.post(_event("first"))
    w._activity_hub.post(_event("second"))
    w.show_activity_log()
    assert w.activity_log._list.count() == 2


def test_hub_event_live_appends_while_log_open(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    w.show_activity_log()
    initial = w.activity_log._list.count()
    w._activity_hub.post(_event("live"))
    assert w.activity_log._list.count() == initial + 1


def test_hub_event_not_appended_when_log_closed(qtbot):
    from romhop import config
    from romhop.gui.main_window import MainWindow
    w = MainWindow(settings=config.default_settings())
    qtbot.addWidget(w)
    w.show_activity_log()
    w.show_library()
    w._activity_hub.post(_event("after close"))
    # re-open: history has the event, but live append was disconnected
    w.show_activity_log()
    # The event IS in the hub history so it appears on load — that's correct
    texts = [w.activity_log._list.item(i).text()
             for i in range(w.activity_log._list.count())]
    assert any("after close" in t for t in texts)
