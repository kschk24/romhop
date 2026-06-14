from romhop.local_index import Collision, LocalGame, MatchResult, index_local_library, match_to_roms
from romhop.romm_client import Rom


def _touch(p, data=b""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def test_flat_file_indexed_as_one_game(tmp_path):
    _touch(tmp_path / "genesis" / "Sonic (USA).md", b"x")
    games = index_local_library(tmp_path, overrides={})
    assert games == [LocalGame(
        system="genesis",
        game_name="Sonic (USA).md",
        file_names=["Sonic (USA).md"],
        match_key="sonic (usa).md",
    )]


def test_subfolder_with_m3u_indexed_as_one_game(tmp_path):
    base = tmp_path / "psx" / "Final Fantasy VII (USA)"
    _touch(base / "Final Fantasy VII (USA) (Disc 1).chd", b"a")
    _touch(base / "Final Fantasy VII (USA) (Disc 2).chd", b"b")
    _touch(base / "noload.txt", b"")
    _touch(tmp_path / "psx" / "Final Fantasy VII (USA).m3u", b"x")
    games = index_local_library(tmp_path, overrides={})
    assert len(games) == 1
    g = games[0]
    assert g.system == "psx"
    assert g.game_name == "Final Fantasy VII (USA)"
    assert g.match_key == "final fantasy vii (usa)"
    assert sorted(g.file_names) == [
        "Final Fantasy VII (USA) (Disc 1).chd",
        "Final Fantasy VII (USA) (Disc 2).chd",
    ]


def test_m3u_in_system_dir_not_emitted_as_flat_file(tmp_path):
    # The .m3u pairs with the subfolder; it must not become its own flat game.
    base = tmp_path / "psx" / "Game (USA)"
    _touch(base / "Game (USA) (Disc 1).chd", b"a")
    _touch(tmp_path / "psx" / "Game (USA).m3u", b"x")
    games = index_local_library(tmp_path, overrides={})
    assert [g.game_name for g in games] == ["Game (USA)"]


def test_orphan_m3u_indexed_on_stem(tmp_path):
    _touch(tmp_path / "psx" / "Lonely (USA).m3u", b"x")
    games = index_local_library(tmp_path, overrides={})
    assert len(games) == 1
    assert games[0].game_name == "Lonely (USA)"
    assert games[0].match_key == "lonely (usa)"
    assert games[0].file_names == []


def test_files_outside_a_system_dir_ignored(tmp_path):
    _touch(tmp_path / "loose.txt", b"x")  # directly under roms_root, not a system dir file
    assert index_local_library(tmp_path, overrides={}) == []


def test_txt_sidecars_ignored_as_flat_games(tmp_path):
    # ES-DE drops a systeminfo.txt in every system dir; .txt is never a rom.
    _touch(tmp_path / "genesis" / "systeminfo.txt", b"meta")
    _touch(tmp_path / "genesis" / "Sonic (USA).md", b"x")
    games = index_local_library(tmp_path, overrides={})
    assert [g.game_name for g in games] == ["Sonic (USA).md"]


def test_txt_sidecars_excluded_from_subfolder_file_names(tmp_path):
    # A promo/readme .txt inside a multi-disc folder must not become a save candidate.
    base = tmp_path / "psx" / "Game (USA)"
    _touch(base / "Game (USA) (Disc 1).chd", b"a")
    _touch(base / "Vimm's Lair.txt", b"promo")
    _touch(base / "noload.txt", b"")
    games = index_local_library(tmp_path, overrides={})
    assert len(games) == 1
    assert games[0].file_names == ["Game (USA) (Disc 1).chd"]


# ---------------------------------------------------------------------------
# match_to_roms tests (Task 3)
# ---------------------------------------------------------------------------

def _rom(rid, name, slug, fs_name, fs_no_ext, files=None):
    return Rom(id=rid, name=name, platform_slug=slug, fs_name=fs_name,
               fs_name_no_ext=fs_no_ext, file_names=files or [fs_name])


def test_flat_file_matches_on_fs_name():
    local = LocalGame("genesis", "Sonic (USA).md", ["Sonic (USA).md"], "sonic (usa).md")
    rom = _rom(7, "Sonic", "genesis", "Sonic (USA).md", "Sonic (USA)")
    result = match_to_roms([local], [rom], overrides={})
    assert result.matched == [(local, rom)]
    assert result.unmatched == []


def test_subfolder_matches_on_fs_name_no_ext():
    local = LocalGame("psx", "FF7 (USA)", ["FF7 (USA) (Disc 1).chd"], "ff7 (usa)")
    rom = _rom(9, "FF7", "psx", "FF7 (USA).m3u", "FF7 (USA)",
               files=["FF7 (USA) (Disc 1).chd"])
    result = match_to_roms([local], [rom], overrides={})
    assert result.matched == [(local, rom)]


def test_whitespace_differences_still_match():
    local = LocalGame("genesis", "Sonic  (USA).md", ["Sonic  (USA).md"], "sonic (usa).md")
    rom = _rom(7, "Sonic", "genesis", "Sonic (USA).md", "Sonic (USA)")
    assert match_to_roms([local], [rom], overrides={}).matched == [(local, rom)]


def test_revision_difference_does_not_match():
    local = LocalGame("genesis", "Sonic (Rev 1).md", ["Sonic (Rev 1).md"], "sonic (rev 1).md")
    rom = _rom(7, "Sonic", "genesis", "Sonic (Rev 2).md", "Sonic (Rev 2)")
    result = match_to_roms([local], [rom], overrides={})
    assert result.matched == []
    assert result.unmatched == [local]


def test_wrong_system_does_not_match():
    local = LocalGame("snes", "Sonic (USA).md", ["Sonic (USA).md"], "sonic (usa).md")
    rom = _rom(7, "Sonic", "genesis", "Sonic (USA).md", "Sonic (USA)")
    assert match_to_roms([local], [rom], overrides={}).matched == []


def test_overrides_apply_to_system_scope():
    # rom platform slug "md" maps to ES-DE "genesis" via override.
    local = LocalGame("genesis", "Sonic (USA).md", ["Sonic (USA).md"], "sonic (usa).md")
    rom = _rom(7, "Sonic", "md", "Sonic (USA).md", "Sonic (USA)")
    result = match_to_roms([local], [rom], overrides={"md": "genesis"})
    assert result.matched == [(local, rom)]


def test_ambiguous_rom_side_left_unmatched():
    # Two roms in the same system normalize to the same name — can't choose.
    local = LocalGame("genesis", "Sonic (USA).md", ["Sonic (USA).md"], "sonic (usa).md")
    r1 = _rom(1, "Sonic", "genesis", "Sonic (USA).md", "Sonic (USA)")
    r2 = _rom(2, "Sonic", "genesis", "Sonic (USA).md", "Sonic (USA)")
    result = match_to_roms([local], [r1, r2], overrides={})
    assert result.matched == []
    assert result.unmatched == [local]


def test_collision_reported_across_systems():
    # Same save basename across two systems => collision flagged for sync awareness.
    l1 = LocalGame("genesis", "Sonic.md", ["Sonic.md"], "sonic.md")
    l2 = LocalGame("snes", "Sonic.sfc", ["Sonic.sfc"], "sonic.sfc")
    r1 = _rom(1, "Sonic", "genesis", "Sonic.md", "Sonic")
    r2 = _rom(2, "Sonic", "snes", "Sonic.sfc", "Sonic")
    result = match_to_roms([l1, l2], [r1, r2], overrides={})
    assert {rid for c in result.collisions for rid in c.rom_ids} == {1, 2}
    assert any(c.basename == "sonic" for c in result.collisions)


def test_downloaded_rom_ids_marks_on_disk_games(tmp_path):
    from romhop.local_index import downloaded_rom_ids
    from romhop.romm_client import Rom

    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "Sonic.md").write_bytes(b"x")

    roms = [
        Rom(id=1, name="Sonic", platform_slug="genesis",
            fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"]),
        Rom(id=2, name="Mario", platform_slug="nes",
            fs_name="Mario.nes", fs_name_no_ext="Mario", file_names=["Mario.nes"]),
    ]
    assert downloaded_rom_ids(roms, tmp_path, {}) == {1}


def test_downloaded_rom_ids_empty_when_root_missing(tmp_path):
    from romhop.local_index import downloaded_rom_ids
    from romhop.romm_client import Rom
    roms = [Rom(id=1, name="Sonic", platform_slug="genesis",
                fs_name="Sonic.md", fs_name_no_ext="Sonic", file_names=["Sonic.md"])]
    assert downloaded_rom_ids(roms, tmp_path / "nope", {}) == set()


def test_downloaded_rom_ids_matches_multi_disc_subfolder(tmp_path):
    from romhop.local_index import downloaded_rom_ids
    from romhop.romm_client import Rom

    game_dir = tmp_path / "psx" / "Final Fantasy VII"
    game_dir.mkdir(parents=True)
    (game_dir / "disc1.bin").write_bytes(b"x")
    (game_dir / "disc2.bin").write_bytes(b"x")

    rom = Rom(id=7, name="Final Fantasy VII", platform_slug="psx",
              fs_name="Final Fantasy VII.m3u", fs_name_no_ext="Final Fantasy VII",
              file_names=["disc1.bin", "disc2.bin"])
    assert downloaded_rom_ids([rom], tmp_path, {}) == {7}
