from __future__ import annotations

from collections import deque

from PySide6.QtCore import QObject, Signal


class ActivityHub(QObject):
    """Aggregates ActivityEvents from all worker threads; renderers subscribe here.

    Keeps a capped session-only ring buffer so the Activity log can populate
    on open without replaying a live stream. Workers connect their ``activity``
    signal to ``post`` via a queued connection for thread safety.
    """

    event = Signal(object)
    _CAPACITY = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer: deque = deque(maxlen=self._CAPACITY)

    def post(self, activity_event) -> None:
        self._buffer.append(activity_event)
        self.event.emit(activity_event)

    def post_error(self, message: str) -> None:
        from romhop.activity import ActivityEvent, ActivityKind
        self.post(ActivityEvent(ActivityKind.ERROR, message))

    def history(self) -> list:
        return list(self._buffer)
