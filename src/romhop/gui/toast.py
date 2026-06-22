from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from romhop.activity import ActivityEvent

_TOAST_WIDTH = 280
_DISMISS_MS = 4000
_MARGIN = 12
_SPACING = 8
_MAX_TOASTS = 3


class ToastWidget(QFrame):
    closed = Signal()

    def __init__(self, event: ActivityEvent, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFixedWidth(_TOAST_WIDTH)
        self.setAttribute(
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.WA_StyledBackground, True
        )

        label = QLabel(event.message)
        label.setWordWrap(True)
        label.setObjectName("ToastError" if event.is_error else "ToastInfo")

        dismiss_btn = QPushButton("×")
        dismiss_btn.setObjectName("ToastClose")
        dismiss_btn.setFixedSize(18, 18)
        dismiss_btn.setFlat(True)
        dismiss_btn.clicked.connect(self._dismiss)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 4, 6)
        row.addWidget(label, 1)
        row.addWidget(dismiss_btn, 0)

        if not event.is_error:
            self._timer: QTimer | None = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(_DISMISS_MS)
            self._timer.timeout.connect(self._dismiss)
            self._timer.start()
        else:
            self._timer = None

        self.adjustSize()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._dismiss()

    def _dismiss(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.closed.emit()
        self.hide()
        self.deleteLater()


class ToastManager(QObject):
    def __init__(self, parent_window) -> None:
        super().__init__(parent_window)
        self._parent = parent_window
        self._toasts: list[ToastWidget] = []

    def post(self, event: ActivityEvent) -> None:
        if len(self._toasts) >= _MAX_TOASTS:
            oldest = self._toasts[0]
            oldest.closed.disconnect()
            oldest.hide()
            oldest.deleteLater()
            self._toasts.pop(0)

        toast = ToastWidget(event, self._parent)
        toast.closed.connect(lambda t=toast: self._on_closed(t))
        self._toasts.append(toast)
        self.reposition()
        toast.show()
        toast.raise_()

    def reposition(self) -> None:
        pw = self._parent
        bottom_widget = getattr(pw, "bottom", None)
        if bottom_widget is not None:
            bottom_y = bottom_widget.geometry().top() - _MARGIN
        else:
            bottom_y = pw.height() - _MARGIN

        right_x = pw.width() - _MARGIN
        cursor = bottom_y
        for toast in reversed(self._toasts):
            toast.adjustSize()
            x = right_x - toast.width()
            y = cursor - toast.height()
            toast.move(x, y)
            toast.raise_()
            cursor = y - _SPACING

    def _on_closed(self, toast: ToastWidget) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self.reposition()
