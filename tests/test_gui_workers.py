import pytest

from romhop.gui import workers


def test_callable_worker_emits_result(qtbot):
    w = workers.CallableWorker(lambda: 2 + 3)
    with qtbot.waitSignal(w.done, timeout=2000) as blocker:
        w.start()
    assert blocker.args == [5]


def test_callable_worker_emits_error(qtbot):
    def boom():
        raise ValueError("nope")

    w = workers.CallableWorker(boom)
    with qtbot.waitSignal(w.error, timeout=2000) as blocker:
        w.start()
    assert "nope" in blocker.args[0]


def _rom(rom_id, name):
    from romhop.romm_client import Rom

    return Rom(id=rom_id, name=name, platform_slug="genesis",
               fs_name=f"{name}.md", fs_name_no_ext=name, file_names=[f"{name}.md"])


def test_download_worker_runs_jobs_sequentially(qtbot):
    roms = [_rom(1, "A"), _rom(2, "B")]
    order = []

    def action(rom, on_progress, stop_event):
        on_progress(100, 100)
        order.append(rom.name)
        return rom.name

    w = workers.DownloadWorker(roms, action)
    started = []
    w.item_started.connect(lambda i, n, name: started.append((i, n, name)))
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    assert order == ["A", "B"]
    assert started == [(1, 2, "A"), (2, 2, "B")]


def test_download_worker_reports_progress_with_speed(qtbot):
    roms = [_rom(1, "A")]

    def action(rom, on_progress, stop_event):
        on_progress(50, 100)
        on_progress(100, 100)
        return rom.name

    w = workers.DownloadWorker(roms, action)
    progressed = []
    w.item_progress.connect(lambda d, t, s: progressed.append((d, t, s)))
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    # First callback and the completion callback always surface.
    seen = {(d, t) for d, t, _ in progressed}
    assert (50, 100) in seen
    assert (100, 100) in seen
    # Speed is a non-negative bytes/sec figure derived in the worker.
    assert all(s >= 0 for _, _, s in progressed)


def test_download_worker_continues_past_item_error(qtbot):
    roms = [_rom(1, "A"), _rom(2, "B")]
    done = []

    def action(rom, on_progress, stop_event):
        if rom.name == "A":
            raise ValueError("boom A")
        done.append(rom.name)
        return rom.name

    w = workers.DownloadWorker(roms, action)
    errors = []
    w.item_error.connect(lambda name, msg: errors.append((name, msg)))
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    assert errors and errors[0][0] == "A" and "boom A" in errors[0][1]
    assert done == ["B"]  # batch keeps going after one failure


def test_cover_loader_emits_only_for_roms_with_covers(qtbot, tmp_path):
    from PySide6.QtGui import QImage, QPixmap

    # Write a real PNG for rom 1 so QImage can decode it.
    img_path = tmp_path / "cover_1.png"
    src = QPixmap(8, 8)
    src.fill()
    assert src.save(str(img_path), "PNG")

    roms = [_rom(1, "A"), _rom(2, "B")]

    # Provider returns a real path for rom 1 only; rom 2 has no cover.
    def provider(rom):
        return img_path if rom.id == 1 else None

    w = workers.CoverLoader(roms, provider)
    ready = []
    w.cover_ready.connect(lambda rid, img: ready.append((rid, img)))
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    assert len(ready) == 1
    rid, img = ready[0]
    assert rid == 1
    assert isinstance(img, QImage)
    assert not img.isNull()


def test_sync_worker_watches_then_stops(qtbot):
    # watch_fn receives a threading.Event and blocks until it is set; stop()
    # sets it so the worker can return (mirrors watch_and_push + stop_event).
    started = []

    def watch_fn(stop_event):
        started.append(True)
        stop_event.wait(timeout=2)

    w = workers.SyncWorker(watch_fn)
    states = []
    w.status.connect(states.append)
    with qtbot.waitSignal(w.status, timeout=2000):
        w.start()  # first status emit == "watching"
    assert started == [True]

    with qtbot.waitSignal(w.finished, timeout=2000):
        w.stop()
    assert states[0] == "watching"
    assert states[-1] == "idle"


def test_download_worker_progress_survives_files_over_int32(qtbot):
    # Bravely Default is ~4 GiB; byte counts exceed a signed 32-bit int. The
    # item_progress signal must carry them intact (not raise / wrap).
    big = 4294967295  # 2**32 - 1
    roms = [_rom(1, "Bravely Default")]

    def action(rom, on_progress, stop_event):
        on_progress(big // 2, big)
        on_progress(big, big)
        return rom.name

    w = workers.DownloadWorker(roms, action)
    progressed = []
    w.item_progress.connect(lambda d, t, s: progressed.append((d, t)))
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    seen = {(d, t) for d, t in progressed}
    assert (big, big) in seen  # full size emitted without overflow


def test_detail_worker_emits_loaded(qtbot):
    w = workers.DetailWorker(lambda: {"summary": "hi"})
    with qtbot.waitSignal(w.loaded, timeout=2000) as blocker:
        w.start()
    assert blocker.args == [{"summary": "hi"}]


def test_detail_worker_emits_failed(qtbot):
    def boom():
        raise RuntimeError("offline")

    w = workers.DetailWorker(boom)
    with qtbot.waitSignal(w.failed, timeout=2000) as blocker:
        w.start()
    assert "offline" in blocker.args[0]


def test_download_worker_cancel_stops_batch_without_item_error(qtbot):
    from romhop.download import DownloadCancelled
    roms = [_rom(1, "A"), _rom(2, "B")]
    started = []

    def action(rom, on_progress, stop_event):
        started.append(rom.name)
        if rom.name == "A":
            raise DownloadCancelled  # first item cancelled mid-stream
        return rom.name

    w = workers.DownloadWorker(roms, action)
    errors = []
    w.item_error.connect(lambda n, m: errors.append((n, m)))
    w.cancel()  # pre-cancel so the run aborts deterministically
    with qtbot.waitSignal(w.finished, timeout=2000):
        w.start()

    assert errors == []                 # cancel is not an error
    assert w.was_cancelled() is True
    assert started == []                # cancelled before the first item ran


# --- PullWorker ---

def test_pull_worker_emits_done(qtbot):
    def pull_fn(on_conflict):
        return {"written": 1, "skipped": 0, "kept": 0, "failed": 0}

    w = workers.PullWorker(pull_fn)
    with qtbot.waitSignal(w.done, timeout=2000) as blocker:
        w.start()
    assert blocker.args[0] == {"written": 1, "skipped": 0, "kept": 0, "failed": 0}


def test_pull_worker_emits_failed_on_exception(qtbot):
    def pull_fn(on_conflict):
        raise RuntimeError("network error")

    w = workers.PullWorker(pull_fn)
    with qtbot.waitSignal(w.failed, timeout=2000) as blocker:
        w.start()
    assert "network error" in blocker.args[0]


def test_pull_worker_conflict_marshals_and_resolves(qtbot):
    from dataclasses import dataclass
    from datetime import datetime

    @dataclass
    class _Item:
        file_name: str
        remote_updated: str | None

    conflicts_seen = []

    def pull_fn(on_conflict):
        item = _Item("save.srm", "2026-06-17T10:00:00")
        result = on_conflict(item, "/saves/save.srm", datetime(2026, 6, 16, 9, 0, 0))
        conflicts_seen.append(result)
        return {"written": 1 if result else 0, "skipped": 0, "kept": 0, "failed": 0}

    w = workers.PullWorker(pull_fn)
    conflict_args = []

    def handle_conflict(item, local_path, local_mtime):
        conflict_args.append((item.file_name, local_path, local_mtime))
        # Resolve from the "UI thread" (here: the test thread) immediately
        w.resolve_conflict(True)  # take remote

    w.conflict.connect(handle_conflict)
    with qtbot.waitSignal(w.done, timeout=2000) as blocker:
        w.start()

    assert conflict_args[0][0] == "save.srm"
    assert conflicts_seen == [True]
    assert blocker.args[0]["written"] == 1


def test_pull_worker_conflict_keep_local(qtbot):
    from dataclasses import dataclass
    from datetime import datetime

    @dataclass
    class _Item:
        file_name: str
        remote_updated: str | None

    kept = []

    def pull_fn(on_conflict):
        item = _Item("save.srm", None)
        result = on_conflict(item, "/saves/save.srm", datetime(2026, 6, 16, 9, 0, 0))
        kept.append(result)
        return {"written": 0, "skipped": 0, "kept": 1, "failed": 0}

    w = workers.PullWorker(pull_fn)
    w.conflict.connect(lambda item, p, m: w.resolve_conflict(False))  # keep local
    with qtbot.waitSignal(w.done, timeout=2000):
        w.start()

    assert kept == [False]
