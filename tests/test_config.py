import keyring
from keyring.backends.fail import Keyring as FailKeyring
import pytest

from romhop import config


class MemoryKeyring(FailKeyring):
    """In-memory keyring backend for tests."""
    def __init__(self):
        self._store = {}
    def get_password(self, service, username):
        return self._store.get((service, username))
    def set_password(self, service, username, password):
        self._store[(service, username)] = password
    def delete_password(self, service, username):
        self._store.pop((service, username), None)


@pytest.fixture(autouse=True)
def memory_keyring():
    keyring.set_keyring(MemoryKeyring())


def test_save_and_load_roundtrip(tmp_path):
    s = config.Settings(
        romm_url="http://romm.example",
        roms_root=tmp_path / "roms",
        saves_dir=tmp_path / "saves",
        states_dir=tmp_path / "states",
        platform_overrides={"gba": "Game Boy Advance"},
        sync_delay_seconds=12.5,
    )
    path = tmp_path / "settings.ini"
    config.save_settings(s, path)
    loaded = config.load_settings(path)
    assert loaded.romm_url == "http://romm.example"
    assert loaded.roms_root == tmp_path / "roms"
    assert loaded.saves_dir == tmp_path / "saves"
    assert loaded.states_dir == tmp_path / "states"
    assert loaded.platform_overrides == {"gba": "Game Boy Advance"}
    assert loaded.sync_delay_seconds == 12.5


def test_sync_enabled_defaults_false_and_roundtrips(tmp_path):
    assert config.default_settings().sync_enabled is False
    s = config.default_settings()
    s.sync_enabled = True
    path = tmp_path / "settings.ini"
    config.save_settings(s, path)
    assert config.load_settings(path).sync_enabled is True


def test_start_on_login_defaults_false_and_roundtrips(tmp_path):
    assert config.default_settings().start_on_login is False
    s = config.default_settings()
    s.start_on_login = True
    path = tmp_path / "settings.ini"
    config.save_settings(s, path)
    assert config.load_settings(path).start_on_login is True


def test_token_uses_keyring_not_file(tmp_path):
    config.set_token("rmm_secret")
    assert config.get_token() == "rmm_secret"
    path = tmp_path / "settings.ini"
    config.save_settings(config.default_settings(), path)
    assert "rmm_secret" not in path.read_text()


def test_core_overrides_round_trips(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.core_overrides = {"MyCore": "n64"}
    p = tmp_path / "settings.ini"
    config.save_settings(s, p)
    loaded = config.load_settings(p)
    assert loaded.core_overrides == {"MyCore": "n64"}


def test_core_overrides_defaults_empty(tmp_path):
    from romhop import config
    assert config.default_settings().core_overrides == {}


def test_settings_theme_defaults_and_roundtrips(tmp_path):
    from romhop import config
    s = config.default_settings()
    assert s.theme == "default"
    s.theme = "neon"
    path = tmp_path / "settings.ini"
    config.save_settings(s, path)
    loaded = config.load_settings(path)
    assert loaded.theme == "neon"


def test_sort_flags_round_trip(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.sort_saves_by_core = True
    s.sort_states_by_core = True
    p = tmp_path / "settings.ini"
    config.save_settings(s, p)
    loaded = config.load_settings(p)
    assert loaded.sort_saves_by_core is True
    assert loaded.sort_states_by_core is True


def test_sort_flags_default_false(tmp_path):
    from romhop import config
    s = config.default_settings()
    assert s.sort_saves_by_core is False
    assert s.sort_states_by_core is False


def test_download_rate_limit_roundtrips_and_defaults_zero(tmp_path):
    from romhop import config
    s = config.default_settings()
    assert s.download_rate_limit_kbps == 0  # unlimited by default
    s.download_rate_limit_kbps = 512
    p = tmp_path / "settings.ini"
    config.save_settings(s, p)
    loaded = config.load_settings(p)
    assert loaded.download_rate_limit_kbps == 512


def test_schema_covers_every_scalar_settings_field():
    from romhop import config
    schema_keys = {f.key for f in config.SCHEMA}
    # Every scalar Settings field is in SCHEMA; the two dict fields are not.
    expected = {
        "romm_url", "roms_root", "saves_dir", "states_dir",
        "sort_saves_by_core", "sort_states_by_core",
        "sync_enabled", "start_on_login", "sync_delay_seconds",
        "download_rate_limit_kbps", "theme",
        "auto_update_check", "update_include_prereleases",
        "debug_logging", "desktop_notifications",
        "scan_timeout_seconds", "upload_chunk_size_mb",
    }
    assert schema_keys == expected
    assert "platform_overrides" not in schema_keys
    assert "core_overrides" not in schema_keys


def test_schema_categories_are_known_and_ordered():
    from romhop import config
    assert config.CATEGORY_ORDER == ["connection", "paths", "behavior"]
    for f in config.SCHEMA:
        assert f.category in config.CATEGORY_ORDER
        assert f.type in {"str", "path", "int", "float", "bool"}
        assert f.label  # non-empty


def test_coerce_value_by_type():
    from pathlib import Path
    from romhop import config
    assert config.coerce_value("str", "hello") == "hello"
    assert config.coerce_value("path", "/games") == Path("/games")
    assert config.coerce_value("int", "512") == 512
    assert config.coerce_value("float", "12.5") == 12.5
    assert config.coerce_value("bool", "true") is True
    assert config.coerce_value("bool", "FALSE") is False
    assert config.coerce_value("bool", "1") is True
    assert config.coerce_value("bool", "off") is False


def test_coerce_value_raises_on_bad_number():
    from romhop import config
    import pytest
    with pytest.raises(ValueError):
        config.coerce_value("int", "not-a-number")
    with pytest.raises(ValueError):
        config.coerce_value("float", "abc")


def test_settings_path_is_ini():
    from romhop import config
    assert config.settings_path().name == "settings.ini"


def test_save_writes_category_sections_and_help_comments(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.romm_url = "http://romm.example"
    p = tmp_path / "settings.ini"
    config.save_settings(s, p)
    text = p.read_text()
    assert "[connection]" in text
    assert "[paths]" in text
    assert "[behavior]" in text
    assert "romm_url = http://romm.example" in text
    # help text is emitted as a comment above its key
    assert "# Base URL of your RomM server" in text


def test_load_bad_number_falls_back_to_default(tmp_path):
    from romhop import config
    p = tmp_path / "settings.ini"
    p.write_text(
        "[behavior]\n"
        "download_rate_limit_kbps = not-a-number\n"
        "sync_delay_seconds = 3.5\n"
    )
    loaded = config.load_settings(p)
    # bad int -> default (0); the valid float on the next line still applies
    assert loaded.download_rate_limit_kbps == 0
    assert loaded.sync_delay_seconds == 3.5


def test_load_missing_key_keeps_default(tmp_path):
    from romhop import config
    p = tmp_path / "settings.ini"
    p.write_text("[connection]\nromm_url = http://x\n")
    loaded = config.load_settings(p)
    assert loaded.romm_url == "http://x"
    assert loaded.theme == "default"  # untouched key keeps its default


def test_override_sections_preserve_case_and_round_trip(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.platform_overrides = {"gba": "Game Boy Advance"}
    s.core_overrides = {"MyCore": "n64"}  # mixed case must survive
    p = tmp_path / "settings.ini"
    config.save_settings(s, p)
    loaded = config.load_settings(p)
    assert loaded.platform_overrides == {"gba": "Game Boy Advance"}
    assert loaded.core_overrides == {"MyCore": "n64"}


def test_corrupt_file_returns_defaults(tmp_path):
    from romhop import config
    p = tmp_path / "settings.ini"
    p.write_text("this is not = valid [ini\n at all ]]]\n")
    loaded = config.load_settings(p)
    assert loaded.romm_url == config.default_settings().romm_url


def test_missing_file_returns_defaults(tmp_path):
    from romhop import config
    loaded = config.load_settings(tmp_path / "nope.ini")
    assert loaded.theme == "default"


def test_migrates_legacy_json_when_ini_absent(tmp_path):
    """Upgrading from the old settings.json format must not silently wipe a
    user's RomM connection: when the ini is absent but a sibling settings.json
    exists, load it and migrate."""
    from romhop import config
    (tmp_path / "settings.json").write_text(
        '{"romm_url": "http://romm.legacy", '
        '"roms_root": "/games/roms", '
        '"saves_dir": "/games/saves", '
        '"states_dir": "/games/states", '
        '"platform_overrides": {"gba": "Game Boy Advance"}, '
        '"sync_enabled": true, '
        '"download_rate_limit_kbps": 256}'
    )
    ini = tmp_path / "settings.ini"
    loaded = config.load_settings(ini)
    assert loaded.romm_url == "http://romm.legacy"
    assert loaded.platform_overrides == {"gba": "Game Boy Advance"}
    assert loaded.sync_enabled is True
    assert loaded.download_rate_limit_kbps == 256
    # The legacy file is migrated to the new ini so the next launch is native.
    assert ini.exists()
    assert "romm_url = http://romm.legacy" in ini.read_text()


def test_ini_wins_over_legacy_json(tmp_path):
    """Once an ini exists it is authoritative; a stale settings.json is ignored."""
    from romhop import config
    (tmp_path / "settings.json").write_text('{"romm_url": "http://stale"}')
    ini = tmp_path / "settings.ini"
    ini.write_text("[connection]\nromm_url = http://current\n")
    assert config.load_settings(ini).romm_url == "http://current"


def test_is_configured_true_when_url_and_token(monkeypatch):
    from romhop import config
    monkeypatch.setattr(config, "get_token", lambda: "rmm_x")
    s = config.default_settings()
    s.romm_url = "http://romm.test"
    assert config.is_configured(s) is True


def test_is_configured_false_when_url_missing(monkeypatch):
    from romhop import config
    monkeypatch.setattr(config, "get_token", lambda: "rmm_x")
    s = config.default_settings()
    s.romm_url = ""
    assert config.is_configured(s) is False


def test_is_configured_false_when_token_missing(monkeypatch):
    from romhop import config
    monkeypatch.setattr(config, "get_token", lambda: None)
    s = config.default_settings()
    s.romm_url = "http://romm.test"
    assert config.is_configured(s) is False


def test_auto_update_check_defaults_on_and_roundtrips(tmp_path):
    from romhop.config import default_settings, load_settings, save_settings
    s = default_settings()
    assert s.auto_update_check is True
    s.auto_update_check = False
    path = tmp_path / "config.ini"
    save_settings(s, path)
    assert load_settings(path).auto_update_check is False


def test_purge_user_data_removes_given_dirs(tmp_path):
    from romhop import config

    cfg = tmp_path / "config" / "romhop"
    data = tmp_path / "data" / "romhop"
    cfg.mkdir(parents=True)
    (cfg / "settings.ini").write_text("x")
    data.mkdir(parents=True)
    (data / "mapping_cache.json").write_text("{}")
    missing = tmp_path / "gone"

    removed = config.purge_user_data([cfg, data, missing])

    assert not cfg.exists() and not data.exists()
    assert removed == [cfg, data]  # missing dir skipped, not reported


def test_purge_user_data_default_dirs_exclude_roms_and_saves(tmp_path, monkeypatch):
    """Default scope is romhop's config + app-data dirs only; the ROM library
    and RetroArch saves/states live elsewhere and must never be in scope."""
    from romhop import config

    cfg = tmp_path / "config" / "romhop"
    data = tmp_path / "data" / "romhop"
    logs = tmp_path / "log" / "romhop"
    roms = tmp_path / "roms"
    saves = tmp_path / "retroarch" / "saves"
    for d in (cfg, data, logs, roms, saves):
        d.mkdir(parents=True)

    monkeypatch.setattr(config, "settings_path", lambda: cfg / "settings.ini")
    monkeypatch.setattr(config, "user_data_dir", lambda: data)
    import platformdirs as _pd
    monkeypatch.setattr(_pd, "user_log_dir", lambda *_: str(logs))

    removed = config.purge_user_data()

    assert removed == [cfg, data, logs]
    assert roms.exists() and saves.exists()  # untouched


def test_roms_root_problem_ok_for_writable_dir(tmp_path):
    assert config.roms_root_problem(tmp_path / "roms") is None  # creatable under tmp


def test_roms_root_problem_flags_unset():
    msg = config.roms_root_problem(config.UNSET_PATH)
    assert msg and "not set" in msg.lower()


def test_roms_root_problem_flags_unwritable(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)  # r-x: no write
    try:
        msg = config.roms_root_problem(ro / "games")
        assert msg and "writable" in msg.lower()
        assert str(ro) in msg
    finally:
        ro.chmod(0o700)  # let pytest clean up


def test_roms_root_problem_flags_nonexistent_root(tmp_path):
    # A path whose nearest existing ancestor is a non-writable system dir.
    msg = config.roms_root_problem("/proc/nonexistent/games")
    assert msg is not None
