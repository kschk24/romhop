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
