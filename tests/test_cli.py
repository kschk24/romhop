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
        def list_roms(self): return [rom]

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
        def list_roms(self): return []
    monkeypatch.setattr(cli, "RommClient", FakeClient)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = tmp_path
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    result = runner.invoke(cli.app, ["download", "Nope"])
    assert result.exit_code == 1
