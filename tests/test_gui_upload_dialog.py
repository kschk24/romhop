from __future__ import annotations

from romhop.local_index import LocalGame
from romhop.upload import UploadCandidates


def _local(system, name):
    return LocalGame(system=system, game_name=name,
                     file_names=[name], match_key=name.lower())


def _platform(id_, slug):
    return {"id": id_, "slug": slug}


def _make_candidates(
    resolvable=(),
    missing_platform=(),
    unresolvable=(),
):
    return UploadCandidates(
        resolvable=list(resolvable),
        missing_platform=list(missing_platform),
        unresolvable=list(unresolvable),
    )


# --- open / summary ---

def test_dialog_opens_with_summary(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[(_local("snes", "Mario.sfc"), _platform(1, "snes"))],
        missing_platform=[(_local("nes", "Metroid.nes"), "nes")],
        unresolvable=[_local("unknown", "Weird.rom")],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    # 3 total, 1 ready, 1 missing, 1 unresolvable
    assert dlg.windowTitle() == "Upload local games to RomM"
    # Three rows built
    assert len(dlg._rows) == 3


def test_dialog_resolvable_unchecked_by_default(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[(_local("snes", "Game.sfc"), _platform(1, "snes"))],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    row = dlg._rows[0]
    assert not row.cb.isChecked()
    assert row.cb.isEnabled()


def test_dialog_unresolvable_row_disabled(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(unresolvable=[_local("??", "Odd.rom")])
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    row = dlg._rows[0]
    assert not row.cb.isEnabled()
    assert row.kind == "unresolvable"


def test_dialog_missing_platform_row_disabled_with_create_btn(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(missing_platform=[(_local("nes", "Contra.nes"), "nes")])
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    row = dlg._rows[0]
    assert not row.cb.isEnabled()
    assert row.create_btn is not None
    assert row.create_btn.isEnabled()


# --- filter ---

def test_platform_filter_all_shows_all_rows(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "A.sfc"), _platform(1, "snes")),
            (_local("nes", "B.nes"), _platform(2, "nes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._platform_combo.setCurrentText("All")
    assert dlg._inner_layout.count() == 2


def test_platform_filter_narrows_rows(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "A.sfc"), _platform(1, "snes")),
            (_local("nes", "B.nes"), _platform(2, "nes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._platform_combo.setCurrentText("snes")
    assert dlg._inner_layout.count() == 1


# --- sort ---

def test_sort_name_orders_alphabetically(qtbot):
    from romhop.gui.upload_dialog import UploadDialog, _SORT_NAME

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "Zelda.sfc"), _platform(1, "snes")),
            (_local("nes", "Contra.nes"), _platform(2, "nes")),
            (_local("nes", "Battletoads.nes"), _platform(2, "nes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._sort_combo.setCurrentText(_SORT_NAME)
    sorted_rows = dlg._sorted_rows()
    names = [r.game.game_name for r in sorted_rows]
    assert names == sorted(names, key=str.lower)


def test_sort_platform_groups_by_system(qtbot):
    from romhop.gui.upload_dialog import UploadDialog, _SORT_PLATFORM

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "Zelda.sfc"), _platform(1, "snes")),
            (_local("nes", "Contra.nes"), _platform(2, "nes")),
            (_local("snes", "Mario.sfc"), _platform(1, "snes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._sort_combo.setCurrentText(_SORT_PLATFORM)
    sorted_rows = dlg._sorted_rows()
    systems = [r.game.system for r in sorted_rows]
    # nes rows grouped before snes rows
    assert systems == sorted(systems)


# --- select all / none ---

def test_select_all_checks_visible_enabled_rows(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "A.sfc"), _platform(1, "snes")),
            (_local("nes", "B.nes"), _platform(2, "nes")),
        ],
        unresolvable=[_local("??", "C.rom")],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._select_all()
    ok_rows = [r for r in dlg._rows if r.kind == "ok"]
    assert all(r.cb.isChecked() for r in ok_rows)
    # Unresolvable stays unchecked
    bad_rows = [r for r in dlg._rows if r.kind == "unresolvable"]
    assert not any(r.cb.isChecked() for r in bad_rows)


def test_select_none_unchecks_all(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "A.sfc"), _platform(1, "snes")),
            (_local("nes", "B.nes"), _platform(2, "nes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._select_all()
    dlg._select_none()
    assert not any(r.cb.isChecked() for r in dlg._rows)


def test_select_all_with_filter_only_affects_visible(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    cands = _make_candidates(
        resolvable=[
            (_local("snes", "A.sfc"), _platform(1, "snes")),
            (_local("nes", "B.nes"), _platform(2, "nes")),
        ],
    )
    dlg = UploadDialog(cands)
    qtbot.addWidget(dlg)
    dlg._platform_combo.setCurrentText("snes")
    dlg._select_all()
    snes_row = next(r for r in dlg._rows if r.game.system == "snes")
    nes_row = next(r for r in dlg._rows if r.game.system == "nes")
    assert snes_row.cb.isChecked()
    assert not nes_row.cb.isChecked()


# --- upload_action called ---

def test_upload_action_called_with_selected_games(qtbot):
    """Only checked, enabled rows with a resolved platform become upload jobs."""
    from romhop.gui.upload_dialog import UploadDialog

    game_a = _local("snes", "A.sfc")
    game_b = _local("nes", "B.nes")
    cands = _make_candidates(
        resolvable=[
            (game_a, _platform(1, "snes")),
            (game_b, _platform(2, "nes")),
        ],
    )

    uploaded_jobs = []

    def fake_batch(jobs, *, on_item_started, progress_factory, on_item_error, stop_event, on_event):
        uploaded_jobs.extend(jobs)
        return True

    dlg = UploadDialog(cands, upload_action=fake_batch)
    qtbot.addWidget(dlg)

    # Check only game_a
    snes_row = next(r for r in dlg._rows if r.game.system == "snes")
    snes_row.cb.setChecked(True)

    # Trigger upload and wait for worker to finish
    dlg._on_upload_clicked()
    if dlg._upload_worker is not None:
        qtbot.waitSignal(dlg._upload_worker.finished, timeout=3000)

    assert len(uploaded_jobs) == 1
    assert uploaded_jobs[0][0] is game_a
    assert uploaded_jobs[0][1] == 1    # platform id
    assert uploaded_jobs[0][2] == "snes"  # platform slug


def test_create_platform_enables_row_and_checks(qtbot):
    from romhop.gui.upload_dialog import UploadDialog

    game = _local("nes", "Contra.nes")
    cands = _make_candidates(missing_platform=[(game, "nes")])

    created = {}

    def fake_create(slug):
        created["slug"] = slug
        return {"id": 99, "slug": slug}

    dlg = UploadDialog(cands, create_platform_fn=fake_create)
    qtbot.addWidget(dlg)

    row = dlg._rows[0]
    assert not row.cb.isEnabled()

    dlg._on_create_platform(row)

    assert created["slug"] == "nes"
    assert row.cb.isEnabled()
    assert row.cb.isChecked()
    assert row.platform is not None
    assert row.platform["id"] == 99
