from romhop.library import build_m3u, candidate_basenames, write_game


def test_build_m3u_relative_forward_slash_lf_no_bom():
    content = build_m3u(
        "Final Fantasy VII (Europe)",
        ["Final Fantasy VII (Europe) (Disc 1).cue",
         "Final Fantasy VII (Europe) (Disc 2).cue"],
    )
    assert content == (
        "Final Fantasy VII (Europe)/Final Fantasy VII (Europe) (Disc 1).cue\n"
        "Final Fantasy VII (Europe)/Final Fantasy VII (Europe) (Disc 2).cue\n"
    )
    assert not content.startswith("﻿")
    assert "\r" not in content


def test_candidate_basenames_covers_m3u_and_disc_names():
    names = candidate_basenames(
        "Silent Hill (USA)",
        ["Silent Hill (USA).bin", "Silent Hill (USA).cue"],
    )
    assert "Silent Hill (USA)" in names          # m3u / content name
    assert "Silent Hill (USA).bin" in names       # disc file with ext


def test_write_game_creates_layout(tmp_path):
    files = {"Silent Hill (USA).bin": b"BIN", "Silent Hill (USA).cue": b"CUE"}
    m3u = write_game(tmp_path, "psx", "Silent Hill (USA)", files)
    assert m3u == tmp_path / "psx" / "Silent Hill (USA).m3u"
    assert m3u.exists()
    folder = tmp_path / "psx" / "Silent Hill (USA)"
    assert (folder / "Silent Hill (USA).bin").read_bytes() == b"BIN"
    assert (folder / "noload.txt").exists()
    assert "Silent Hill (USA)/Silent Hill (USA).cue" in m3u.read_text()


def test_m3u_file_bytes_are_lf_and_no_bom(tmp_path):
    files = {"Game (USA).bin": b"BIN", "Game (USA).cue": b"CUE"}
    m3u = write_game(tmp_path, "psx", "Game (USA)", files)
    raw = m3u.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")   # no UTF-8 BOM on disk
    assert b"\r" not in raw                        # LF only


def test_m3u_excludes_bin_when_cue_present(tmp_path):
    files = {"Game (USA).bin": b"BIN", "Game (USA).cue": b"CUE"}
    m3u = write_game(tmp_path, "psx", "Game (USA)", files)
    text = m3u.read_text()
    assert "Game (USA).bin" not in text
    assert "Game (USA)/Game (USA).cue" in text


def test_discs_sorted_naturally(tmp_path):
    from romhop.library import build_m3u
    content = build_m3u("G", ["G (Disc 10).cue", "G (Disc 2).cue", "G (Disc 1).cue"])
    assert content == "G/G (Disc 1).cue\nG/G (Disc 2).cue\nG/G (Disc 10).cue\n"


def test_write_game_rejects_unsafe_game_name(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        write_game(tmp_path, "psx", "bad/name", {"a.bin": b"X"})


def test_write_game_strips_traversal_in_file_keys(tmp_path):
    write_game(tmp_path, "psx", "Game (USA)", {"../escape.bin": b"X"})
    # written as basename inside the game folder, not a sibling/parent
    assert (tmp_path / "psx" / "Game (USA)" / "escape.bin").read_bytes() == b"X"
    assert not (tmp_path / "psx" / "escape.bin").exists()


def test_write_single_file_is_flat(tmp_path):
    from romhop.library import write_single_file
    p = write_single_file(tmp_path, "gba", "Sonic Advance (USA).zip", b"ROM")
    assert p == tmp_path / "gba" / "Sonic Advance (USA).zip"
    assert p.read_bytes() == b"ROM"
    # no subfolder, no m3u, no noload
    assert list((tmp_path / "gba").iterdir()) == [p]


def test_write_single_file_strips_traversal(tmp_path):
    from romhop.library import write_single_file
    p = write_single_file(tmp_path, "gba", "../escape.gba", b"X")
    assert p == tmp_path / "gba" / "escape.gba"
    assert not (tmp_path / "escape.gba").exists()
