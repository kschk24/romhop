from __future__ import annotations

import threading
import time
from typing import Callable, Sequence

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage

from romhop.download import DownloadCancelled


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


class DownloadWorker(QThread):
    """Runs a batch of downloads sequentially, one bar at a time.

    Model = "one bar, current game, queue the rest": each job runs in turn and
    drives a single progress source. ``action(rom, on_progress)`` performs the
    download; ``on_progress(downloaded, total)`` (total may be None) is forwarded
    from the underlying transfer. The worker derives a bytes/sec speed and
    throttles intermediate updates so chunk-rate callbacks don't flood the UI.

    Signals:
      item_started(index, count, name) - 1-based position in the batch
      item_progress(downloaded, total, speed) - total is -1 when unknown
      item_error(name, message)        - one job failed; the batch continues
      finished (built-in)              - whole batch done
    """

    item_started = Signal(int, int, str)
    # qlonglong (64-bit): byte counts for large roms (e.g. ~4 GiB 3DS titles)
    # exceed a signed 32-bit int, which a plain `int` signal silently clamps.
    item_progress = Signal("qlonglong", "qlonglong", float)
    item_error = Signal(str, str)

    # Don't emit more often than this between non-terminal updates (seconds).
    _MIN_INTERVAL = 0.1

    def __init__(self, jobs: Sequence, action: Callable[..., object],
                 parent=None):
        super().__init__(parent)
        self._jobs = list(jobs)
        self._action = action
        self._cancel = threading.Event()
        self._cancelled = False

    def cancel(self) -> None:
        """Request the batch stop: drops the queue and aborts the in-flight
        transfer via the stop_event handed to the action."""
        self._cancel.set()

    def was_cancelled(self) -> bool:
        return self._cancelled

    def _make_on_progress(self):
        state = {"t0": None, "last_t": 0.0, "last_b": 0, "emitted": False}

        def on_progress(downloaded: int, total: int | None) -> None:
            now = time.monotonic()
            if state["t0"] is None:
                state.update(t0=now, last_t=now, last_b=0)
            complete = total is not None and downloaded >= total
            elapsed = now - state["last_t"]
            if state["emitted"] and not complete and elapsed < self._MIN_INTERVAL:
                return
            dt = now - state["last_t"]
            db = downloaded - state["last_b"]
            speed = db / dt if dt > 0 else 0.0
            self.item_progress.emit(downloaded, -1 if total is None else total,
                                    max(speed, 0.0))
            state.update(last_t=now, last_b=downloaded, emitted=True)

        return on_progress

    def run(self) -> None:
        count = len(self._jobs)
        for index, rom in enumerate(self._jobs, start=1):
            if self._cancel.is_set():
                self._cancelled = True
                break
            self.item_started.emit(index, count, rom.name)
            try:
                self._action(rom, self._make_on_progress(), self._cancel)
            except DownloadCancelled:
                self._cancelled = True
                break
            except Exception as exc:  # one failure must not abort the queue
                self.item_error.emit(rom.name, str(exc))


class CoverLoader(QThread):
    """Fetches and decodes cover art off the UI thread.

    ``cover_provider(rom)`` returns a cached image path (or None). For each rom
    that resolves to a path, decodes the file into a ``QImage`` (optionally
    scaled to ``cover_size``), and emits ``cover_ready(rom_id, image)`` so the
    grid can convert to QPixmap and drop it into the matching tile on the UI
    thread. Misses and per-rom errors are skipped silently — the tile keeps its
    placeholder.

    QImage operations are safe off the GUI thread; only QPixmap must stay on it.
    """

    cover_ready = Signal(int, "QImage")

    def __init__(self, roms: Sequence, cover_provider: Callable[[object], object],
                 cover_size: tuple[int, int] | None = None,
                 parent=None):
        super().__init__(parent)
        self._roms = list(roms)
        self._cover_provider = cover_provider
        self._cover_size = cover_size

    def run(self) -> None:
        for rom in self._roms:
            if self.isInterruptionRequested():  # superseded by a newer load
                return
            try:
                path = self._cover_provider(rom)
            except Exception:  # a bad cover must not sink the rest of the batch
                continue
            if not path:
                continue
            image = QImage(str(path))
            if image.isNull():
                continue
            if self._cover_size is not None:
                w, h = self._cover_size
                image = image.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_ready.emit(rom.id, image)


class UpdateWorker(QThread):
    """Off-UI-thread update check or download+apply. One instance per phase."""

    available = Signal(object)      # UpdateInfo | None
    progress = Signal("qlonglong", "qlonglong")  # bytes_done, bytes_total
    applied = Signal()
    failed = Signal(str)

    def __init__(self, *, check_fn=None, apply_fn=None, info=None, parent=None):
        super().__init__(parent)
        self._check_fn = check_fn
        self._apply_fn = apply_fn
        self._info = info

    def run(self) -> None:
        try:
            if self._apply_fn is not None:
                self._apply_fn(self._info, lambda d, t: self.progress.emit(d, t))
                self.applied.emit()
            else:
                self.available.emit(self._check_fn())
        except Exception as exc:  # noqa: BLE001 - surface, never crash the app
            self.failed.emit(str(exc))


class SyncWorker(QThread):
    """Runs the sync watch loop until stop() is requested.

    watch_fn receives a ``threading.Event`` and must return promptly once it is
    set (pass it through to ``watch_and_push(stop_event=...)``). status(text)
    reports state to the bottom bar.
    """

    status = Signal(str)
    error = Signal(str)

    def __init__(self, watch_fn: Callable[[threading.Event], None], parent=None):
        super().__init__(parent)
        self._watch_fn = watch_fn
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        self.status.emit("watching")
        try:
            self._watch_fn(self._stop_event)
        except Exception as exc:
            self.error.emit(str(exc))
            return
        self.status.emit("idle")
