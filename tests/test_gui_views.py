from romhop.gui import library_view
from romhop.romm_client import Rom


def _rom(name, slug):
    return Rom(id=hash((name, slug)) & 0xffff, name=name, platform_slug=slug,
               fs_name=name, fs_name_no_ext=name, file_names=[name])


def test_platforms_from_roms_sorted_unique():
    roms = [_rom("A", "snes"), _rom("B", "nes"), _rom("C", "snes")]
    assert library_view.platforms_from_roms(roms) == ["nes", "snes"]


def test_filter_games_by_platform_and_query():
    roms = [_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis"),
            _rom("Mario", "nes")]
    out = library_view.filter_games(roms, platform="genesis", query="so")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_empty_query_returns_whole_platform():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes")]
    out = library_view.filter_games(roms, platform="genesis", query="")
    assert [r.name for r in out] == ["Sonic"]


def test_library_view_populates_and_selects(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    assert view.current_platform() == "genesis"
    # Check the one genesis game and confirm it reports as selected.
    check, rom = next(iter(view._checks.values()))
    check.setChecked(True)
    assert view.selected_roms()[0].name == "Sonic"


def test_columns_for_width_scales_and_floors_at_one():
    # Wider viewport -> more columns; never fewer than one even when tiny.
    assert library_view.columns_for_width(640, cell_width=160) == 4
    assert library_view.columns_for_width(330, cell_width=160) == 2
    assert library_view.columns_for_width(50, cell_width=160) == 1
    assert library_view.columns_for_width(0, cell_width=160) == 1


def test_grid_reflows_on_resize(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom(f"G{i}", "genesis") for i in range(12)])
    view.resize(960, 600)
    view.show()
    qtbot.waitExposed(view)
    wide_cols = view._cols
    view.resize(280, 600)
    qtbot.wait(20)
    narrow_cols = view._cols
    assert wide_cols > narrow_cols
    assert narrow_cols >= 1


def test_library_view_selection_survives_filter(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis")])
    for check, rom in list(view._checks.values()):
        if rom.name == "Sonic":
            check.setChecked(True)
    # Narrow the view to just "Sonic"; its checked state must persist.
    view.filter("Sonic")
    assert [r.name for r in view.selected_roms()] == ["Sonic"]


def test_selection_persists_across_platform_switch(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    assert view.current_platform() == "genesis"

    # Check Sonic on the genesis tab.
    check, _ = next(iter(view._checks.values()))
    check.setChecked(True)

    # Switch to the nes tab and check Mario.
    view.sidebar.setCurrentRow(1)
    assert view.current_platform() == "nes"
    check2, _ = next(iter(view._checks.values()))
    check2.setChecked(True)

    # Global selection spans BOTH platforms regardless of active tab.
    assert sorted(r.name for r in view.selected_roms()) == ["Mario", "Sonic"]

    # Returning to genesis must restore Sonic's checkmark (not wiped).
    view.sidebar.setCurrentRow(0)
    assert view.current_platform() == "genesis"
    check_back, _ = next(iter(view._checks.values()))
    assert check_back.isChecked()


def test_tiles_have_fixed_size_regardless_of_game_count(qtbot):
    from romhop.gui.library_view import CELL_HEIGHT, CELL_WIDTH, LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    # One platform with a single game, one with many. Tile dimensions must match.
    roms = [_rom("Solo", "threeds")] + [_rom(f"G{i}", "nds") for i in range(30)]
    view.set_roms(roms)

    def all_cells_fixed():
        assert view._cells
        for c in view._cells:
            assert c.minimumHeight() == CELL_HEIGHT
            assert c.maximumHeight() == CELL_HEIGHT
            assert c.minimumWidth() == CELL_WIDTH
            assert c.maximumWidth() == CELL_WIDTH

    all_cells_fixed()                  # platform on row 0
    view.sidebar.setCurrentRow(1)      # switch to the other platform
    all_cells_fixed()                  # same fixed dimensions, different count


def test_cells_have_cover_label_placeholder(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    # Each game has a registered cover label, blank (null pixmap) until loaded.
    assert view._cover_labels
    label = next(iter(view._cover_labels.values()))
    assert label.pixmap().isNull()


def test_apply_cover_sets_pixmap(qtbot, tmp_path):
    from PySide6.QtGui import QPixmap
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    rom_id = next(iter(view._cover_labels))

    # Write a real image to disk, then apply it to that cell.
    src = QPixmap(8, 8)
    src.fill()
    path = tmp_path / "cover.png"
    assert src.save(str(path), "PNG")
    view._apply_cover(rom_id, str(path))

    assert not view._cover_labels[rom_id].pixmap().isNull()


def test_apply_cover_ignores_unknown_rom(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    # Stale emit for a rom not on screen must be a no-op (no crash).
    view._apply_cover(999999, "/nonexistent.png")


def test_unchecking_removes_from_global_selection(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    check, _ = next(iter(view._checks.values()))
    check.setChecked(True)
    assert len(view.selected_roms()) == 1
    check.setChecked(False)
    assert view.selected_roms() == []
