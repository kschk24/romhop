from __future__ import annotations

from romhop.local_index import LocalGame, Collision, MatchResult


def _local(system, name):
    return LocalGame(system=system, game_name=name,
                     file_names=[name], match_key=name.lower())


def test_scan_dialog_shows_counts_and_lists(qtbot):
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(
        matched=[(_local("snes", "Mario.sfc"), object())],
        unmatched=[_local("nes", "Weird Game.nes")],
        collisions=[Collision(basename="mario", rom_ids=[1, 2])],
    )
    dlg = ScanResultDialog(result)
    qtbot.addWidget(dlg)

    text = dlg.summary_text()
    assert "1 matched" in text
    assert "1 unmatched" in text
    assert "1 collision" in text  # substring also matches "collisions"

    body = dlg.detail_text()
    assert "nes/Weird Game.nes" in body
    assert "mario" in body
    assert "[1, 2]" in body


def test_scan_dialog_handles_empty_result(qtbot):
    from romhop.gui.scan_result_dialog import ScanResultDialog

    dlg = ScanResultDialog(MatchResult())
    qtbot.addWidget(dlg)
    assert "0 matched" in dlg.summary_text()
    assert dlg.detail_text() == ""  # nothing to list


def test_scan_dialog_shows_checkboxes_when_upload_action(qtbot):
    """With upload_action, unmatched games get checkboxes instead of plain text."""
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(
        matched=[],
        unmatched=[_local("nes", "Unknown.nes"), _local("snes", "Missing.sfc")],
        collisions=[],
    )
    called = {}

    def fake_upload(game, pid, pslug, on_progress, stop_event, on_event=None):
        called[game.game_name] = True

    dlg = ScanResultDialog(result, upload_action=fake_upload)
    qtbot.addWidget(dlg)

    # Checkboxes for each unmatched game.
    assert len(dlg._checkboxes) == 2
    assert "nes/Unknown.nes" in dlg._checkboxes
    assert "snes/Missing.sfc" in dlg._checkboxes


def test_scan_dialog_select_all(qtbot):
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(
        unmatched=[_local("nes", "A.nes"), _local("snes", "B.sfc")],
    )
    dlg = ScanResultDialog(result, upload_action=lambda *a, **k: None)
    qtbot.addWidget(dlg)

    dlg._select_all()
    assert all(cb.isChecked() for cb in dlg._checkboxes.values())


def test_scan_dialog_progress_bar_is_determinate_with_total(qtbot):
    """Upload progress mirrors the download bar: determinate permille fill plus a
    'name (i/n) · sent/total · rate' label once a total is known."""
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(unmatched=[_local("snes", "Mario.sfc")])
    dlg = ScanResultDialog(result, upload_action=lambda *a, **k: None)
    qtbot.addWidget(dlg)

    dlg._on_item_started(1, 1, "Mario.sfc")
    dlg._on_item_progress(512, 1024, 2048.0)

    assert dlg._progress_bar.maximum() == dlg._PROGRESS_SCALE
    assert dlg._progress_bar.value() == dlg._PROGRESS_SCALE // 2  # 512/1024
    fmt = dlg._progress_bar.format()
    assert "Mario.sfc" in fmt
    assert "(1/1)" in fmt
    assert "/" in fmt  # sent / total


def test_scan_dialog_progress_indeterminate_when_total_unknown(qtbot):
    from romhop.gui.scan_result_dialog import ScanResultDialog

    dlg = ScanResultDialog(MatchResult(unmatched=[_local("nes", "X.nes")]),
                           upload_action=lambda *a, **k: None)
    qtbot.addWidget(dlg)

    dlg._on_item_started(1, 1, "X.nes")
    dlg._on_item_progress(4096, 0, 0.0)  # total unknown
    assert dlg._progress_bar.maximum() == 0  # stays indeterminate


def test_scan_dialog_upload_resolves_platform(qtbot, monkeypatch):
    """_resolve_platforms returns correct job tuples for a resolvable game."""
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(unmatched=[_local("snes", "Mario.sfc")])
    platforms = [{"id": 7, "slug": "snes", "fs_slug": "snes"}]

    dlg = ScanResultDialog(
        result,
        upload_action=lambda *a, **k: None,
        list_platforms_fn=lambda: platforms,
        create_platform_fn=None,
        overrides={},
    )
    qtbot.addWidget(dlg)

    games = [_local("snes", "Mario.sfc")]
    jobs = dlg._resolve_platforms(games)

    assert len(jobs) == 1
    game, platform_id, platform_slug = jobs[0]
    assert game.game_name == "Mario.sfc"
    assert platform_id == 7
    assert platform_slug == "snes"


def test_scan_dialog_upload_skips_unresolvable(qtbot, monkeypatch):
    """Games with no resolvable platform and no create_platform_fn are skipped."""
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(unmatched=[_local("unknownsystem", "X.rom")])

    dlg = ScanResultDialog(
        result,
        upload_action=lambda *a, **k: None,
        list_platforms_fn=lambda: [],  # no platforms
        create_platform_fn=None,       # can't create
        overrides={},
    )
    qtbot.addWidget(dlg)

    games = [_local("unknownsystem", "X.rom")]
    jobs = dlg._resolve_platforms(games)

    assert jobs == []


def _make_batch_fn(per_game_fn):
    """Wrap a per-game callable into the batch_fn signature UploadWorker expects."""
    def batch_fn(jobs, *, on_item_started, progress_factory,
                 on_item_error, stop_event, on_event):
        for i, (game, pid, pslug) in enumerate(jobs, 1):
            if stop_event.is_set():
                return False
            on_item_started(i, len(jobs), game.game_name)
            try:
                per_game_fn(game, pid, pslug)
            except Exception as exc:
                on_item_error(game.game_name, str(exc))
        return True
    return batch_fn


def test_upload_worker_runs_action(qtbot):
    """UploadWorker calls batch_fn for each job and emits item_started/finished."""
    from romhop.gui.workers import UploadWorker
    from romhop.local_index import LocalGame

    game = LocalGame(system="snes", game_name="Mario.sfc",
                     file_names=["Mario.sfc"], match_key="mario.sfc")
    started = []
    errors = []

    def fake_per_game(g, pid, pslug):
        started.append(g.game_name)

    worker = UploadWorker([(game, 1, "snes")], _make_batch_fn(fake_per_game))
    worker.item_started.connect(lambda i, c, n: None)
    worker.item_error.connect(lambda n, m: errors.append(m))

    with qtbot.waitSignal(worker.finished, timeout=2000):
        worker.start()

    assert "Mario.sfc" in started
    assert errors == []


def test_upload_worker_continues_after_error(qtbot):
    """UploadWorker emits item_error and continues with the next game."""
    from romhop.gui.workers import UploadWorker
    from romhop.local_index import LocalGame

    game_a = LocalGame(system="snes", game_name="A.sfc", file_names=["A.sfc"], match_key="a")
    game_b = LocalGame(system="snes", game_name="B.sfc", file_names=["B.sfc"], match_key="b")
    done_names = []
    error_names = []

    def fake_per_game(g, pid, pslug):
        if g.game_name == "A.sfc":
            raise RuntimeError("boom")
        done_names.append(g.game_name)

    worker = UploadWorker([(game_a, 1, "snes"), (game_b, 1, "snes")],
                          _make_batch_fn(fake_per_game))
    worker.item_error.connect(lambda n, m: error_names.append(n))

    with qtbot.waitSignal(worker.finished, timeout=2000):
        worker.start()

    assert "A.sfc" in error_names
    assert "B.sfc" in done_names  # second game still ran


def test_scan_dialog_finished_shows_cancelled_not_complete(qtbot):
    """_on_upload_finished shows 'Cancelled' not 'Upload complete' when worker cancelled."""
    from romhop.gui.scan_result_dialog import ScanResultDialog

    result = MatchResult(unmatched=[_local("snes", "Mario.sfc")])
    dlg = ScanResultDialog(result, upload_action=lambda *a, **k: None)
    qtbot.addWidget(dlg)

    # Simulate a worker that reports cancelled.
    class FakeWorker:
        def was_cancelled(self):
            return True
        def deleteLater(self):
            pass

    # show buttons/progress so _on_upload_finished can hide them
    dlg._upload_btn.show()
    dlg._progress_bar.show()
    dlg._upload_worker = FakeWorker()
    dlg._on_upload_finished()

    assert dlg._upload_btn.text() == "Cancelled"
    assert dlg._ok_btn.isEnabled()
