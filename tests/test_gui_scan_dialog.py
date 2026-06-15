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
