from pathlib import Path

from typer.testing import CliRunner

from romhop import cli
from romhop.romm_client import Rom

runner = CliRunner()


def test_login_stores_token(monkeypatch):
    stored = {}
    monkeypatch.setattr(cli.config, "set_token", lambda t: stored.setdefault("t", t))
    monkeypatch.setattr(cli.config, "load_settings", lambda: cli.config.default_settings())
    saved = {}
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))

    result = runner.invoke(cli.app, ["login", "--url", "http://romm.test", "--token", "rmm_x"])

    assert result.exit_code == 0
    assert stored["t"] == "rmm_x"
    assert saved["s"].romm_url == "http://romm.test"


def test_show_frog_hidden_when_not_a_tty(monkeypatch):
    # Frog gutter must only appear on an interactive terminal.
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: False)
    assert cli._show_frog() is False


def test_show_frog_shown_on_tty(monkeypatch):
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert cli._show_frog() is True


def test_help_renders_frog_gutter_on_tty(monkeypatch):
    # CliRunner swaps sys.stdout during invoke, so patch the gate directly.
    monkeypatch.setattr(cli, "_show_frog", lambda: True)
    monkeypatch.setenv("COLUMNS", "120")
    result = runner.invoke(cli.app, ["--help"], color=True)
    assert result.exit_code == 0
    # Frog art and the description both present in the rendered help.
    assert "+#++*##*+" in result.output
    assert "RomM" in result.output
    # A recognizable art row sits to the left of body text on the same line.
    assert any("=*#*=" in line and len(line) > 40 for line in result.output.splitlines())


def test_download_invokes_orchestrator(monkeypatch, tmp_path):
    rom = Rom(id=7, name="Sonic", platform_slug="genesis", fs_name="Sonic.md",
              fs_name_no_ext="Sonic", file_names=["Sonic.md"])

    class FakeClient:
        def __init__(self, *a, **k): pass
        def list_roms(self, search_term=None): return [rom]

    monkeypatch.setattr(cli, "RommClient", FakeClient)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = tmp_path
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)

    called = {}
    def fake_download(rom_arg, client, **kwargs):
        called["rom_id"] = rom_arg.id
        return tmp_path / "genesis" / "Sonic.m3u"
    monkeypatch.setattr(cli, "download_rom", fake_download)

    result = runner.invoke(cli.app, ["download", "Sonic"])

    assert result.exit_code == 0
    assert called["rom_id"] == 7


def test_client_not_logged_in_exits_1(monkeypatch):
    settings = cli.config.default_settings()  # romm_url == ""
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    result = runner.invoke(cli.app, ["download", "Sonic"])
    assert result.exit_code == 1


def test_download_no_match_exits_1(monkeypatch, tmp_path):
    class FakeClient:
        def __init__(self, *a, **k): pass
        def list_roms(self, search_term=None): return []
    monkeypatch.setattr(cli, "RommClient", FakeClient)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = tmp_path
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    result = runner.invoke(cli.app, ["download", "Nope"])
    assert result.exit_code == 1


def _login(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = tmp_path
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)


def _fake_client(monkeypatch, roms):
    class FakeClient:
        def __init__(self, *a, **k): pass
        def list_roms(self, search_term=None): return roms
    monkeypatch.setattr(cli, "RommClient", FakeClient)


def test_download_ambiguous_aborts_exit_2(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    roms = [
        Rom(id=1, name="Sonic Advance", platform_slug="gba", fs_name="a.zip", fs_name_no_ext="a", file_names=["a.zip"]),
        Rom(id=2, name="Aerobiz Supersonic", platform_slug="snes", fs_name="b.zip", fs_name_no_ext="b", file_names=["b.zip"]),
    ]
    _fake_client(monkeypatch, roms)
    called = {"n": 0}
    monkeypatch.setattr(cli, "download_rom", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    result = runner.invoke(cli.app, ["download", "sonic"])
    assert result.exit_code == 2
    assert called["n"] == 0  # never downloaded anything


def test_download_exact_name_wins_over_substring(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    roms = [
        Rom(id=1, name="Sonic Advance", platform_slug="gba", fs_name="a.zip", fs_name_no_ext="a", file_names=["a.zip"]),
        Rom(id=2, name="Sonic", platform_slug="genesis", fs_name="s.md", fs_name_no_ext="s", file_names=["s.md"]),
    ]
    _fake_client(monkeypatch, roms)
    picked = {}
    monkeypatch.setattr(cli, "download_rom", lambda rom, *a, **k: picked.setdefault("id", rom.id) or (tmp_path / "x.m3u"))
    result = runner.invoke(cli.app, ["download", "Sonic"])
    assert result.exit_code == 0
    assert picked["id"] == 2  # exact "Sonic", not the substring match


def test_download_http_404_friendly(monkeypatch, tmp_path):
    import httpx
    _login(monkeypatch, tmp_path)
    rom = Rom(id=9, name="Broken", platform_slug="snes", fs_name="x.zip", fs_name_no_ext="x", file_names=["x.zip"])
    _fake_client(monkeypatch, [rom])

    def boom(*a, **k):
        raise httpx.HTTPStatusError(
            "404", request=httpx.Request("GET", "http://romm.test"),
            response=httpx.Response(404),
        )
    monkeypatch.setattr(cli, "download_rom", boom)
    result = runner.invoke(cli.app, ["download", "Broken"])
    assert result.exit_code == 1
    assert "rescan" in result.output.lower()


def test_config_set_roms_root(monkeypatch, tmp_path):
    import json as _json
    saved = {}
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    result = runner.invoke(cli.app, ["config", "set", "roms_root", str(tmp_path / "ROMs")])
    assert result.exit_code == 0
    assert saved["s"].roms_root == tmp_path / "ROMs"


def test_config_set_unknown_key_exits_2(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    result = runner.invoke(cli.app, ["config", "set", "bogus", "x"])
    assert result.exit_code == 2


def test_config_set_bad_float_exits_2(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    result = runner.invoke(cli.app, ["config", "set", "sync_delay_seconds", "soon"])
    assert result.exit_code == 2


def test_config_show_outputs_json(monkeypatch):
    import json as _json
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    result = runner.invoke(cli.app, ["config", "show"])
    assert result.exit_code == 0
    parsed = _json.loads(result.output)
    assert parsed["romm_url"] == "http://romm.test"
    assert "roms_root" in parsed


def test_config_set_platform_add_and_remove(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    r1 = runner.invoke(cli.app, ["config", "set-platform", "genesis-slug", "genesis"])
    assert r1.exit_code == 0 and settings.platform_overrides["genesis-slug"] == "genesis"
    r2 = runner.invoke(cli.app, ["config", "set-platform", "genesis-slug"])
    assert r2.exit_code == 0 and "genesis-slug" not in settings.platform_overrides


def test_download_requires_roms_root(monkeypatch):
    settings = cli.config.default_settings()   # roms_root unset
    settings.romm_url = "http://romm.test"
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    result = runner.invoke(cli.app, ["download", "Sonic"])
    assert result.exit_code == 1
    assert "setup" in result.output.lower()


def test_setup_writes_settings_and_token(monkeypatch):
    settings = cli.config.default_settings()    # romm_url "", roms_root unset
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    stored = {}
    saved = {}
    monkeypatch.setattr(cli.config, "set_token", lambda t: stored.setdefault("t", t))
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (current.saves_dir, current.states_dir, False, False))

    # url, token, roms, then "N" to keep the saves/states defaults, "N" to skip scan
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_secret\n/tmp/MyROMs\nN\nN\n",
    )
    assert result.exit_code == 0, result.output
    assert stored["t"] == "rmm_secret"
    assert saved["s"].romm_url == "http://romm.test"
    assert saved["s"].roms_root == Path("/tmp/MyROMs")
    # saves/states kept the OS RetroArch defaults (not prompted)
    assert "retroarch" in str(saved["s"].saves_dir).lower()


def test_setup_changes_saves_states_when_confirmed(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    saved = {}
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (current.saves_dir, current.states_dir, False, False))

    # url, token, roms, "y" to change, then custom saves + states, "N" to skip scan
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_x\n/tmp/MyROMs\ny\n/tmp/sv\n/tmp/st\nN\n",
    )
    assert result.exit_code == 0, result.output
    assert saved["s"].saves_dir == Path("/tmp/sv")
    assert saved["s"].states_dir == Path("/tmp/st")


def test_setup_keeps_existing_token_when_blank(monkeypatch):
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = Path("/tmp/old")
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_existing")
    set_calls = []
    monkeypatch.setattr(cli.config, "set_token", lambda t: set_calls.append(t))
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (current.saves_dir, current.states_dir, False, False))

    # accept url default, blank token (keep existing), new roms, "N" keep saves/states, "N" skip scan
    result = runner.invoke(cli.app, ["setup"], input="\n\n/tmp/new\nN\nN\n")
    assert result.exit_code == 0, result.output
    assert set_calls == []   # token untouched because blank + existing present


def test_config_set_core_add_and_remove(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    r1 = runner.invoke(cli.app, ["config", "set-core", "MyCore", "n64"])
    assert r1.exit_code == 0 and settings.core_overrides["MyCore"] == "n64"
    r2 = runner.invoke(cli.app, ["config", "set-core", "MyCore"])
    assert r2.exit_code == 0 and "MyCore" not in settings.core_overrides


def test_download_list_roms_403_friendly(monkeypatch, tmp_path):
    import httpx
    _login(monkeypatch, tmp_path)

    class FakeClient:
        def __init__(self, *a, **k): pass
        def list_roms(self, search_term=None):
            raise httpx.HTTPStatusError(
                "403", request=httpx.Request("GET", "http://romm.test/api/roms"),
                response=httpx.Response(403),
            )
    monkeypatch.setattr(cli, "RommClient", FakeClient)
    result = runner.invoke(cli.app, ["download", "Sonic"])
    assert result.exit_code == 1
    assert "token" in result.output.lower()
    assert "Traceback" not in result.output


def test_scan_matches_and_writes_with_yes(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    # one local flat game on disk
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "Sonic (USA).md").write_bytes(b"x")
    rom = Rom(id=7, name="Sonic", platform_slug="genesis",
              fs_name="Sonic (USA).md", fs_name_no_ext="Sonic (USA)",
              file_names=["Sonic (USA).md"])
    _fake_client(monkeypatch, [rom])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")

    result = runner.invoke(cli.app, ["scan", "--yes"])
    assert result.exit_code == 0, result.output
    from romhop.mapping_cache import MappingCache
    cache = MappingCache(tmp_path / "cache.json")
    assert cache.find_by_basename("Sonic (USA)").rom_id == 7


def test_scan_preview_aborts_without_confirm(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "Sonic (USA).md").write_bytes(b"x")
    rom = Rom(id=7, name="Sonic", platform_slug="genesis",
              fs_name="Sonic (USA).md", fs_name_no_ext="Sonic (USA)",
              file_names=["Sonic (USA).md"])
    _fake_client(monkeypatch, [rom])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")

    result = runner.invoke(cli.app, ["scan"], input="n\n")
    assert result.exit_code == 0
    assert not (tmp_path / "cache.json").exists()
    assert "1 matched" in result.output


def test_scan_requires_roms_root(monkeypatch):
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"   # roms_root still unset
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    result = runner.invoke(cli.app, ["scan"])
    assert result.exit_code == 1
    assert "setup" in result.output.lower()


def test_setup_offers_scan_at_end(monkeypatch, tmp_path):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    ran = {"scan": False}
    monkeypatch.setattr(cli, "_run_scan", lambda s, *, assume_yes: ran.__setitem__("scan", assume_yes))
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (current.saves_dir, current.states_dir, False, False))

    # url, token, roms, "N" keep saves/states, then "y" to scan now
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_x\n/tmp/MyROMs\nN\ny\n",
    )
    assert result.exit_code == 0, result.output
    assert ran["scan"] is True          # scan ran with assume_yes=True


def test_setup_skips_scan_when_declined(monkeypatch, tmp_path):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)
    ran = {"scan": 0}
    monkeypatch.setattr(cli, "_run_scan", lambda s, *, assume_yes: ran.__setitem__("scan", ran["scan"] + 1))
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (current.saves_dir, current.states_dir, False, False))

    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_x\n/tmp/MyROMs\nN\nn\n",
    )
    assert result.exit_code == 0, result.output
    assert ran["scan"] == 0


def test_download_skips_when_already_local(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    # game already present on disk
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "Sonic (USA).md").write_bytes(b"x")
    rom = Rom(id=7, name="Sonic", platform_slug="genesis",
              fs_name="Sonic (USA).md", fs_name_no_ext="Sonic (USA)",
              file_names=["Sonic (USA).md"])
    _fake_client(monkeypatch, [rom])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")

    called = {"n": 0}
    monkeypatch.setattr(cli, "download_rom", lambda *a, **k: called.__setitem__("n", called["n"] + 1))

    result = runner.invoke(cli.app, ["download", "Sonic"])
    assert result.exit_code == 0, result.output
    assert called["n"] == 0                       # never downloaded
    assert "Already local" in result.output
    from romhop.mapping_cache import MappingCache
    assert MappingCache(tmp_path / "cache.json").find_by_basename("Sonic (USA)").rom_id == 7


def test_setup_uses_detected_cfg_dirs(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    saved = {}
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (Path("/tmp/sv"), Path("/tmp/st"), False, False))

    # url, token, roms, "N" keep detected saves/states, "N" skip scan
    result = runner.invoke(cli.app, ["setup"],
                           input="http://romm.test\nrmm_x\n/tmp/MyROMs\nN\nN\n")
    assert result.exit_code == 0, result.output
    assert saved["s"].saves_dir == Path("/tmp/sv")
    assert saved["s"].states_dir == Path("/tmp/st")


def test_setup_reprompts_when_cfg_unset(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    saved = {}
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values", lambda current: (None, None, False, False))

    # url, token, roms, saves (re-prompt), states (re-prompt), "N" skip scan
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_x\n/tmp/MyROMs\n/tmp/sv\n/tmp/st\nN\n")
    assert result.exit_code == 0, result.output
    assert saved["s"].saves_dir == Path("/tmp/sv")
    assert saved["s"].states_dir == Path("/tmp/st")


def test_setup_windows_prompts_install_folder(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    saved = {}
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    # Force the Windows branch and a known cfg result regardless of the folder typed.
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(cli.retroarch_cfg, "save_dirs_from_install",
                        lambda folder: (Path("D:/RA/saves"), Path("D:/RA/states")))

    # url, token, roms, install-folder, "N" keep detected, "N" skip scan
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_x\n/tmp/MyROMs\nD:/Programme/RetroArch\nN\nN\n")
    assert result.exit_code == 0, result.output
    assert saved["s"].saves_dir == Path("D:/RA/saves")
    assert saved["s"].states_dir == Path("D:/RA/states")


def test_setup_stores_sort_flags(monkeypatch):
    settings = cli.config.default_settings()
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: None)
    monkeypatch.setattr(cli.config, "set_token", lambda t: None)
    saved = {}
    monkeypatch.setattr(cli.config, "save_settings", lambda s: saved.setdefault("s", s))
    monkeypatch.setattr(cli, "_run_scan", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_retroarch_cfg_values",
                        lambda current: (Path("/tmp/sv"), Path("/tmp/st"), True, True))

    result = runner.invoke(cli.app, ["setup"],
                           input="http://romm.test\nrmm_x\n/tmp/MyROMs\nN\nN\n")
    assert result.exit_code == 0, result.output
    assert saved["s"].sort_saves_by_core is True
    assert saved["s"].sort_states_by_core is True


def test_pull_requires_name_or_all(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    _fake_client(monkeypatch, [])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")
    from romhop.mapping_cache import MappingCache, RomEntry
    c = MappingCache(tmp_path / "cache.json")
    c.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic", candidate_basenames={"Sonic"}))
    c.save()
    result = runner.invoke(cli.app, ["pull"])
    assert result.exit_code == 2
    assert "name a game" in result.output.lower() or "--all" in result.output.lower()


def test_pull_empty_cache_exits_1(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    _fake_client(monkeypatch, [])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")
    result = runner.invoke(cli.app, ["pull", "--all"])
    assert result.exit_code == 1
    assert "scan" in result.output.lower()


def test_pull_all_invokes_pull_games(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    _fake_client(monkeypatch, [])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")
    from romhop.mapping_cache import MappingCache, RomEntry
    c = MappingCache(tmp_path / "cache.json")
    c.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic", candidate_basenames={"Sonic"}))
    c.save()
    captured = {}
    def fake_pull(client, entries, settings, *, take_remote, on_conflict, on_written, on_error):
        captured["ids"] = [e.rom_id for e in entries]
        captured["take_remote"] = take_remote
        return {"written": 0, "skipped": 0, "kept": 0}
    monkeypatch.setattr(cli, "pull_games", fake_pull)
    result = runner.invoke(cli.app, ["pull", "--all", "--remote"])
    assert result.exit_code == 0, result.output
    assert captured["ids"] == [1]
    assert captured["take_remote"] is True


def test_pull_name_selects_one(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    _fake_client(monkeypatch, [])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")
    from romhop.mapping_cache import MappingCache, RomEntry
    c = MappingCache(tmp_path / "cache.json")
    c.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic", candidate_basenames={"Sonic"}))
    c.add(RomEntry(rom_id=2, system="snes", game_name="Mario", candidate_basenames={"Mario"}))
    c.save()
    captured = {}
    def fake_pull(client, entries, settings, *, take_remote, on_conflict, on_written, on_error):
        captured["ids"] = [e.rom_id for e in entries]
        return {"written": 0, "skipped": 0, "kept": 0}
    monkeypatch.setattr(cli, "pull_games", fake_pull)
    result = runner.invoke(cli.app, ["pull", "Sonic"])
    assert result.exit_code == 0, result.output
    assert captured["ids"] == [1]


def test_pull_name_no_match_exits_1(monkeypatch, tmp_path):
    _login(monkeypatch, tmp_path)
    _fake_client(monkeypatch, [])
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "cache.json")
    from romhop.mapping_cache import MappingCache, RomEntry
    c = MappingCache(tmp_path / "cache.json")
    c.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic", candidate_basenames={"Sonic"}))
    c.save()
    result = runner.invoke(cli.app, ["pull", "Zelda"])
    assert result.exit_code == 1
    assert "no cached game" in result.output.lower()


def test_download_ambiguous_lists_platform(monkeypatch, tmp_path):
    settings = cli.config.default_settings()
    settings.roms_root = tmp_path
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "roms_root_configured", lambda s: True)

    class FakeClient:
        def list_roms(self, search_term=None):
            return [
                Rom(id=1, name="Super Mario Land", platform_slug="gb",
                    fs_name="a", fs_name_no_ext="a", file_names=[],
                    platform_name="Game Boy"),
                Rom(id=2, name="Super Mario Land 2: 6 Golden Coins",
                    platform_slug="gb", fs_name="b", fs_name_no_ext="b",
                    file_names=[], platform_name="Game Boy"),
            ]

    monkeypatch.setattr(cli, "_client", lambda: FakeClient())
    monkeypatch.setattr(cli, "_cache_path", lambda: tmp_path / "map.json")
    monkeypatch.setattr(cli, "_platform_names_path", lambda: tmp_path / "names.json")

    result = runner.invoke(cli.app, ["download", "Super Mario"])
    combined = result.output + result.stderr
    assert result.exit_code == 2
    assert "Super Mario Land - Game Boy" in combined
    assert "Super Mario Land 2: 6 Golden Coins - Game Boy" in combined
