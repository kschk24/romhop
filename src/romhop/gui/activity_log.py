from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

_ERROR_COLOR = QColor("#e05252")


class ActivityLogView(QWidget):
    """Session-only in-app activity log. Shows events newest-first."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._list = QListWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._list)

    def load(self, history: list) -> None:
        """Populate from hub ring buffer. Clears existing rows first."""
        self._list.clear()
        for event in history:
            self._insert_top(event)

    def append_event(self, event) -> None:
        """Live-append a new event at the top of the list."""
        self._insert_top(event)

    def _insert_top(self, event) -> None:
        ts = event.timestamp.strftime("%H:%M:%S")
        item = QListWidgetItem(f"{ts}  {event.message}")
        if event.is_error:
            item.setForeground(_ERROR_COLOR)
        self._list.insertItem(0, item)
