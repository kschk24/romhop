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
    path = tmp_path / "settings.json"
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
    path = tmp_path / "settings.json"
    config.save_settings(s, path)
    assert config.load_settings(path).sync_enabled is True


def test_token_uses_keyring_not_file(tmp_path):
    config.set_token("rmm_secret")
    assert config.get_token() == "rmm_secret"
    path = tmp_path / "settings.json"
    config.save_settings(config.default_settings(), path)
    assert "rmm_secret" not in path.read_text()


def test_core_overrides_round_trips(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.core_overrides = {"MyCore": "n64"}
    p = tmp_path / "settings.json"
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
    path = tmp_path / "settings.json"
    config.save_settings(s, path)
    loaded = config.load_settings(path)
    assert loaded.theme == "neon"


def test_sort_flags_round_trip(tmp_path):
    from romhop import config
    s = config.default_settings()
    s.sort_saves_by_core = True
    s.sort_states_by_core = True
    p = tmp_path / "settings.json"
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
    p = tmp_path / "settings.json"
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
        "sync_enabled", "sync_delay_seconds",
        "download_rate_limit_kbps", "theme",
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
