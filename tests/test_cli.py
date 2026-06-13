from pathlib import Path

from typer.testing import CliRunner

from emusync import cli
from emusync.romm_client import Rom

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

    # url, token, roms; blank lines accept the saves/states defaults
    result = runner.invoke(
        cli.app, ["setup"],
        input="http://romm.test\nrmm_secret\n/tmp/MyROMs\n\n\n",
    )
    assert result.exit_code == 0, result.output
    assert stored["t"] == "rmm_secret"
    assert saved["s"].romm_url == "http://romm.test"
    assert saved["s"].roms_root == Path("/tmp/MyROMs")
    # saves/states defaulted to the OS RetroArch paths
    assert "retroarch" in str(saved["s"].saves_dir).lower()
    assert "only change them" in result.output.lower()


def test_setup_keeps_existing_token_when_blank(monkeypatch):
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = Path("/tmp/old")
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_existing")
    set_calls = []
    monkeypatch.setattr(cli.config, "set_token", lambda t: set_calls.append(t))
    monkeypatch.setattr(cli.config, "save_settings", lambda s: None)

    # accept url default, blank token (keep existing), new roms, accept saves/states
    result = runner.invoke(cli.app, ["setup"], input="\n\n/tmp/new\n\n\n")
    assert result.exit_code == 0, result.output
    assert set_calls == []   # token untouched because blank + existing present
