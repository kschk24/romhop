from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

# Dot palette, shared with the bottom-bar indicator: grey idle, green watching,
# red error. main_window imports these instead of keeping its own copy.
SYNC_DOT_COLORS = {"off": "#8b949e", "running": "#3fb950", "error": "#f85149"}


def status_icon(state_class: str) -> QIcon:
    """A 16x16 filled-circle icon coloured by coarse sync class. Painted at
    runtime so no binary asset ships and the colour tracks SYNC_DOT_COLORS."""
    color = SYNC_DOT_COLORS.get(state_class, SYNC_DOT_COLORS["off"])
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(0, 0, 0, 0))  # transparent background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(QColor(color))
    painter.drawEllipse(2, 2, 12, 12)
    painter.end()
    return QIcon(pixmap)
