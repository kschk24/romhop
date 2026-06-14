from pathlib import Path

from romhop.retroarch_cfg import default_cfg_path, parse_save_dirs, parse_sort_flags, save_dirs_from_install


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


def test_save_dirs_from_install_reads_cfg(tmp_path):
    _write_cfg(tmp_path, 'savefile_directory = ":/saves"\n'
                         'savestate_directory = ":/states"\n')
    assert save_dirs_from_install(tmp_path) == (tmp_path / "saves", tmp_path / "states")


def test_save_dirs_from_install_no_cfg(tmp_path):
    assert save_dirs_from_install(tmp_path) == (None, None)


def test_default_cfg_path_uses_xdg_when_present(tmp_path, monkeypatch):
    cfg = _write_cfg(tmp_path / "retroarch", 'savefile_directory = "x"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_cfg_path() == cfg


def test_default_cfg_path_falls_back_to_home_config(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    cfg = _write_cfg(tmp_path / ".config" / "retroarch", 'savefile_directory = "x"\n')
    assert default_cfg_path() == cfg


def test_default_cfg_path_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # no cfg written here
    assert default_cfg_path() is None


def test_parse_sort_flags_true(tmp_path):
    cfg = _write_cfg(tmp_path, 'sort_savefiles_enable = "true"\n'
                               'sort_savestates_enable = "true"\n')
    assert parse_sort_flags(cfg) == (True, True)


def test_parse_sort_flags_false_and_absent(tmp_path):
    cfg = _write_cfg(tmp_path, 'sort_savefiles_enable = "false"\n')  # savestates key absent
    assert parse_sort_flags(cfg) == (False, False)


def test_parse_sort_flags_missing_file(tmp_path):
    assert parse_sort_flags(tmp_path / "nope.cfg") == (False, False)
