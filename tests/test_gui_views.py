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
