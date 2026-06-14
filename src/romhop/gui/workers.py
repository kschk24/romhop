from __future__ import annotations

import threading
import time
from typing import Callable, Sequence

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
    item_progress = Signal(int, int, float)
    item_error = Signal(str, str)

    # Don't emit more often than this between non-terminal updates (seconds).
    _MIN_INTERVAL = 0.1

    def __init__(self, jobs: Sequence, action: Callable[[object, Callable], object],
                 parent=None):
        super().__init__(parent)
        self._jobs = list(jobs)
        self._action = action

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
            self.item_started.emit(index, count, rom.name)
            try:
                self._action(rom, self._make_on_progress())
            except Exception as exc:  # one failure must not abort the queue
                self.item_error.emit(rom.name, str(exc))


class CoverLoader(QThread):
    """Fetches cover-art paths off the UI thread.

    ``cover_provider(rom)`` returns a cached image path (or None). For each rom
    that resolves to a path, emits ``cover_ready(rom_id, path)`` so the grid can
    drop the pixmap into the matching tile. Misses and per-rom errors are skipped
    silently — the tile keeps its placeholder.
    """

    cover_ready = Signal(int, str)

    def __init__(self, roms: Sequence, cover_provider: Callable[[object], object],
                 parent=None):
        super().__init__(parent)
        self._roms = list(roms)
        self._cover_provider = cover_provider

    def run(self) -> None:
        for rom in self._roms:
            try:
                path = self._cover_provider(rom)
            except Exception:  # a bad cover must not sink the rest of the batch
                continue
            if path:
                self.cover_ready.emit(rom.id, str(path))


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
