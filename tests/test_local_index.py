from romhop.local_index import LocalGame, index_local_library


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
