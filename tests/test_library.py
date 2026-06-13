from emusync.library import build_m3u, candidate_basenames, write_game


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
