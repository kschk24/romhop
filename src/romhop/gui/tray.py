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


class TrayIcon(QSystemTrayIcon):
    """System tray icon: show/hide, a sync toggle that mirrors the bottom-bar
    button, and quit. Construct only when QSystemTrayIcon.isSystemTrayAvailable()."""

    show_requested = Signal()
    sync_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        menu = QMenu()
        self._show_action = menu.addAction("Show romhop")
        self._show_action.triggered.connect(self.show_requested)
        self._sync_action = menu.addAction("Save-Sync")
        self._sync_action.setCheckable(True)
        self._sync_action.toggled.connect(self.sync_toggled)
        menu.addSeparator()
        self._quit_action = menu.addAction("Quit romhop")
        self._quit_action.triggered.connect(self.quit_requested)
        self.setContextMenu(menu)
        self._menu = menu  # keep a ref so the menu isn't GC'd
        self.setIcon(status_icon("off"))
        self.setToolTip("Sync: idle")
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        # Left-click / double-click toggles the window; right-click shows the menu.
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_requested.emit()

    def set_sync_checked(self, on: bool) -> None:
        # Mirror the bottom-bar/settings state without echoing a toggle back.
        self._sync_action.blockSignals(True)
        self._sync_action.setChecked(on)
        self._sync_action.blockSignals(False)

    def set_status(self, state: str, state_class: str) -> None:
        self.setToolTip(f"Sync: {state}")
        self.setIcon(status_icon(state_class))
