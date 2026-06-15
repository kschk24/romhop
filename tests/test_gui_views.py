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
    from PySide6.QtGui import QImage, QPixmap
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    rom_id = next(iter(view._cover_labels))

    # Build a real QImage (as the loader now emits).
    src = QPixmap(8, 8)
    src.fill()
    image = src.toImage()
    view._apply_cover(rom_id, image)

    assert not view._cover_labels[rom_id].pixmap().isNull()
    assert rom_id in view._pixmap_cache


def test_apply_cover_ignores_unknown_rom(qtbot):
    from PySide6.QtGui import QImage, QPixmap
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    # Stale emit for a rom not on screen: pass a real QImage, must be a no-op.
    src = QPixmap(4, 4)
    src.fill()
    image = src.toImage()
    unknown_id = 999999
    view._apply_cover(unknown_id, image)
    assert unknown_id not in view._pixmap_cache


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


def test_cover_pixmap_cache_reused_across_platform_switch(qtbot, tmp_path):
    """Cache hit on platform switch: provider not called again, pixmap instant."""
    from PySide6.QtGui import QPixmap
    from romhop.gui.library_view import LibraryView

    # Write a real PNG so QImage decode succeeds inside CoverLoader.
    img_a = tmp_path / "rom_a.png"
    img_b = tmp_path / "rom_b.png"
    for p in (img_a, img_b):
        px = QPixmap(8, 8)
        px.fill()
        assert px.save(str(p), "PNG")

    rom_a = _rom("Sonic", "genesis")
    rom_b = _rom("Mario", "nes")

    call_counts: dict[int, int] = {}

    def provider(rom):
        call_counts[rom.id] = call_counts.get(rom.id, 0) + 1
        if rom.id == rom_a.id:
            return img_a
        if rom.id == rom_b.id:
            return img_b
        return None

    view = LibraryView(cover_provider=provider)
    qtbot.addWidget(view)
    view.set_roms([rom_a, rom_b])

    # Filter to platform A and wait until rom_a is in the pixmap cache.
    view.set_platform_filter("genesis")
    qtbot.waitUntil(lambda: rom_a.id in view._pixmap_cache, timeout=3000)

    count_a_after_first = call_counts.get(rom_a.id, 0)
    assert count_a_after_first >= 1  # provider was called at least once

    # Switch to platform B then back to A.
    view.set_platform_filter("nes")
    view.set_platform_filter("genesis")

    # rom_a's label must show its pixmap immediately (cache hit, no new decode).
    label = view._cover_labels.get(rom_a.id)
    assert label is not None
    assert not label.pixmap().isNull()

    # Provider must NOT have been called again for rom_a.
    assert call_counts.get(rom_a.id, 0) == count_a_after_first


def test_settings_form_has_download_rate_limit_field(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    # _on_save persists via config.save_settings — stub it so the test never
    # writes the real user settings file.
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    assert "Download limit (KB/s, 0 = unlimited)" in view._edits
    view._edits["Download limit (KB/s, 0 = unlimited)"].setText("256")
    view._on_save()
    assert view.current_settings().download_rate_limit_kbps == 256
