from romhop.gui import library_view
from romhop.romm_client import Rom


def _rom(name, slug):
    return Rom(id=hash((name, slug)) & 0xffff, name=name, platform_slug=slug,
               fs_name=name, fs_name_no_ext=name, file_names=[name])


def test_platforms_from_roms_sorted_unique():
    roms = [_rom("A", "snes"), _rom("B", "nes"), _rom("C", "snes")]
    assert library_view.platforms_from_roms(roms) == ["nes", "snes"]


# --- filter_games tests (Step 1 replacements) ---

def test_filter_games_all_platforms_sorted_asc():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="")
    assert [r.name for r in out] == ["Mario", "Sonic", "Zelda"]


def test_filter_games_platform_scopes():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes")]
    out = library_view.filter_games(roms, platform="genesis", query="")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_query_combines_with_platform():
    roms = [_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis")]
    out = library_view.filter_games(roms, platform="genesis", query="so")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_sort_desc():
    roms = [_rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="", sort="desc")
    assert [r.name for r in out] == ["Zelda", "Mario"]


def test_filter_games_downloaded_modes():
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    ids = {a.id}
    only_dl = library_view.filter_games([a, b], platform=None, query="",
                                        downloaded_ids=ids, downloaded_mode="downloaded")
    assert [r.name for r in only_dl] == ["Sonic"]
    only_missing = library_view.filter_games([a, b], platform=None, query="",
                                             downloaded_ids=ids, downloaded_mode="missing")
    assert [r.name for r in only_missing] == ["Mario"]


# --- LibraryView widget tests (Step 3 replacements) ---

def test_library_view_populates_all_platforms(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic", "Mario"}
    check, rom = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    assert view.selected_roms()[0].name == "Sonic"


def test_platform_filter_scopes_grid(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    view.set_platform_filter("genesis")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}


def test_selection_survives_platform_filter(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    check, _ = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    view.set_platform_filter("nes")
    check2, _ = next((c, r) for c, r in view._checks.values() if r.name == "Mario")
    check2.setChecked(True)
    assert sorted(r.name for r in view.selected_roms()) == ["Mario", "Sonic"]


def test_tiles_have_fixed_size_regardless_of_game_count(qtbot):
    from romhop.gui.library_view import CELL_HEIGHT, CELL_WIDTH, LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom(f"G{i}", "nds") for i in range(30)] + [_rom("Solo", "threeds")])
    assert view._cells
    for c in view._cells:
        assert c.minimumHeight() == CELL_HEIGHT and c.maximumHeight() == CELL_HEIGHT
        assert c.minimumWidth() == CELL_WIDTH and c.maximumWidth() == CELL_WIDTH


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


def test_switching_platform_does_not_drop_running_cover_loader(qtbot):
    # Regression: set_roms overwrote the single _cover_loader slot, dropping the
    # previous loader's last reference while its QThread was still running -> GC
    # destroyed it -> "QThread: Destroyed while thread is still running" abort.
    import threading
    from romhop.gui.library_view import LibraryView

    started = threading.Event()
    release = threading.Event()

    def slow_provider(rom):
        started.set()
        release.wait(2.0)        # block so the loader stays running
        return None

    view = LibraryView(cover_provider=slow_provider)
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Tails", "genesis")])
    assert started.wait(2.0)     # first loader is running
    first = view._cover_loader
    assert first in view._cover_loaders

    # Switch platform while the first loader is mid-run.
    view.set_roms([_rom("Mario", "nes")])

    # The old loader must be asked to stop AND kept referenced until it finishes,
    # never silently dropped while running.
    assert first.isInterruptionRequested()
    assert first in view._cover_loaders

    release.set()
    qtbot.waitUntil(lambda: first not in view._cover_loaders, timeout=2000)
    assert not first.isRunning()


# --- Indicator tests (Step 6) ---

def test_tile_shows_platform_pill(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView(platform_label=lambda rom: "Game Boy")
    qtbot.addWidget(view)
    view.set_roms([_rom("Tetris", "gb")])
    pill = next(iter(view._pills.values()))
    assert pill.text() == "Game Boy"


def test_downloaded_tile_gets_ribbon_others_do_not(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    assert a.id in view._ribbons
    assert b.id not in view._ribbons


def test_downloaded_filter_hides_missing(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    view.set_downloaded_filter("downloaded")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}


def test_set_roms_clears_stale_downloaded_ids(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a = _rom("Sonic", "genesis")
    view.set_roms([a])
    view.set_downloaded({a.id})
    assert a.id in view._ribbons
    # Reload with a different library; the old downloaded id must not persist.
    b = _rom("Mario", "nes")
    view.set_roms([b])
    assert view._downloaded_ids == set()
    assert view._ribbons == {}
