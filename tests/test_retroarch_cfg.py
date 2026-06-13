from pathlib import Path

from romhop.retroarch_cfg import parse_save_dirs


def _write_cfg(dirpath, body):
    dirpath.mkdir(parents=True, exist_ok=True)
    cfg = dirpath / "retroarch.cfg"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_absolute_quoted_paths(tmp_path):
    cfg = _write_cfg(tmp_path, 'savefile_directory = "/games/saves"\n'
                               'savestate_directory = "/games/states"\n')
    assert parse_save_dirs(cfg) == (Path("/games/saves"), Path("/games/states"))


def test_colon_base_token_resolves_to_cfg_dir(tmp_path):
    # ':' is RetroArch's config-base dir = the folder holding retroarch.cfg.
    cfg = _write_cfg(tmp_path, 'savefile_directory = ":\\saves"\n'
                               'savestate_directory = ":/states"\n')
    assert parse_save_dirs(cfg) == (tmp_path / "saves", tmp_path / "states")


def test_default_and_empty_are_none(tmp_path):
    cfg = _write_cfg(tmp_path, 'savefile_directory = "default"\n'
                               'savestate_directory = ""\n')
    assert parse_save_dirs(cfg) == (None, None)


def test_missing_key_is_none(tmp_path):
    cfg = _write_cfg(tmp_path, 'savefile_directory = "/games/saves"\n')
    assert parse_save_dirs(cfg) == (Path("/games/saves"), None)


def test_missing_file_returns_none_pair(tmp_path):
    assert parse_save_dirs(tmp_path / "nope.cfg") == (None, None)


def test_tilde_expansion(tmp_path):
    cfg = _write_cfg(tmp_path, 'savefile_directory = "~/ra/saves"\n')
    saves, _ = parse_save_dirs(cfg)
    assert saves == Path.home() / "ra" / "saves"
