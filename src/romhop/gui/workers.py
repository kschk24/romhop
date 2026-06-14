from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal


class CallableWorker(QThread):
    """Runs a zero-arg callable off the UI thread.

    Emits done(result) on success or error(message) on failure. This is the
    base for download/pull/sync actions: wrap the core function call in a
    lambda and connect to the bottom bar's slots.
    """

    done = Signal(object)
    error = Signal(str)

    def __init__(self, fn: Callable[[], object], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # surfaced to the UI as a non-fatal error
            self.error.emit(str(exc))
            return
        self.done.emit(result)


class SyncWorker(QThread):
    """Runs the sync watch loop until stop() is requested.

    watch_fn receives a should_stop() predicate and must return promptly after
    it starts returning True. status(text) reports state to the bottom bar.
    """

    status = Signal(str)
    error = Signal(str)

    def __init__(self, watch_fn: Callable[[Callable[[], bool]], None], parent=None):
        super().__init__(parent)
        self._watch_fn = watch_fn
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        self.status.emit("watching")
        try:
            self._watch_fn(lambda: self._stop)
        except Exception as exc:
            self.error.emit(str(exc))
            return
        self.status.emit("idle")
