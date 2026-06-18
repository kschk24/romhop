from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from romhop.pull import PullItem, resolve_target, pull_games
from romhop.mapping_cache import RomEntry


@dataclass
class _Settings:
    saves_dir: Path
    states_dir: Path
    sort_saves_by_core: bool = False
    sort_states_by_core: bool = False


class FakeClient:
    def __init__(self, saves=None, states=None, blobs=None):
        self._saves = saves or {}
        self._states = states or {}
        self._blobs = blobs or {}
    def list_saves(self, rom_id): return self._saves.get(rom_id, [])
    def list_states(self, rom_id): return self._states.get(rom_id, [])
    def download_save_content(self, sid): return self._blobs[("save", sid)]
    def download_state_content(self, sid): return self._blobs[("state", sid)]


def _entry(rom_id=1):
    return RomEntry(rom_id=rom_id, system="genesis", game_name="Sonic",
                    candidate_basenames={"Sonic"})


def test_pull_writes_new_save(tmp_path):
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_entry()], settings)
    assert (tmp_path / "saves" / "Sonic.srm").read_bytes() == b"REMOTE"
    assert summary["written"] == 1


def test_pull_skips_identical(tmp_path):
    (tmp_path / "saves").mkdir()
    (tmp_path / "saves" / "Sonic.srm").write_bytes(b"SAME")
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"SAME"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_entry()], settings)
    assert summary["skipped"] == 1 and summary["written"] == 0


def test_pull_conflict_take_remote_via_flag(tmp_path):
    (tmp_path / "saves").mkdir()
    (tmp_path / "saves" / "Sonic.srm").write_bytes(b"LOCAL")
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_entry()], settings, take_remote=True)
    assert (tmp_path / "saves" / "Sonic.srm").read_bytes() == b"REMOTE"
    assert summary["written"] == 1


def test_pull_conflict_keep_local_via_callback(tmp_path):
    (tmp_path / "saves").mkdir()
    (tmp_path / "saves" / "Sonic.srm").write_bytes(b"LOCAL")
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_entry()], settings,
                         on_conflict=lambda item, path, mtime: False)  # keep local
    assert (tmp_path / "saves" / "Sonic.srm").read_bytes() == b"LOCAL"
    assert summary["kept"] == 1 and summary["written"] == 0


def test_pull_routes_state_by_extension(tmp_path):
    # RomM serves a .state under /api/saves (sync pushes states there). It must
    # still be written to states_dir, while the .srm goes to saves_dir.
    client = FakeClient(
        saves={1: [
            {"id": 4, "file_name": "Sonic.srm", "emulator": "mGBA",
             "updated_at": "2026-06-01T10:00:00"},
            {"id": 5, "file_name": "Sonic.state", "emulator": "mGBA",
             "updated_at": "2026-06-01T10:00:00"},
        ]},
        blobs={("save", 4): b"SRM", ("save", 5): b"STATE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states",
                         sort_saves_by_core=True, sort_states_by_core=True)
    pull_games(client, [_entry()], settings)
    assert (tmp_path / "saves" / "mGBA" / "Sonic.srm").read_bytes() == b"SRM"
    assert (tmp_path / "states" / "mGBA" / "Sonic.state").read_bytes() == b"STATE"
    assert not (tmp_path / "saves" / "mGBA" / "Sonic.state").exists()


def test_pull_fetches_states_too(tmp_path):
    client = FakeClient(
        states={1: [{"id": 4, "file_name": "Sonic.state1", "emulator": "genesis",
                     "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("state", 4): b"ST"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    pull_games(client, [_entry()], settings)
    assert (tmp_path / "states" / "Sonic.state1").read_bytes() == b"ST"


def test_pull_conflict_take_remote_via_callback(tmp_path):
    (tmp_path / "saves").mkdir()
    (tmp_path / "saves" / "Sonic.srm").write_bytes(b"LOCAL")
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_entry()], settings,
                         on_conflict=lambda item, path, mtime: True)  # take remote
    assert (tmp_path / "saves" / "Sonic.srm").read_bytes() == b"REMOTE"
    assert summary["written"] == 1


def test_pull_calls_on_written(tmp_path):
    written = []
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    pull_games(client, [_entry()], settings, on_written=written.append)
    assert written == [tmp_path / "saves" / "Sonic.srm"]


def test_pull_write_failure_continues_and_counts(tmp_path):
    # saves_dir is a FILE, so creating the save's parent dir fails -> OSError.
    saves = tmp_path / "saves"
    saves.write_bytes(b"not a dir")
    client = FakeClient(
        saves={1: [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis",
                    "updated_at": "2026-06-01T10:00:00"}]},
        blobs={("save", 9): b"REMOTE"})
    settings = _Settings(saves, tmp_path / "states")
    errors = []
    summary = pull_games(client, [_entry()], settings,
                         on_error=lambda p, exc: errors.append(p))
    assert summary["failed"] == 1 and summary["written"] == 0
    assert len(errors) == 1


def _item(kind="save", file_name="Sonic.srm", emulator="genesis"):
    return PullItem(kind=kind, rom_id=1, file_name=file_name, emulator=emulator,
                    remote_updated="2026-06-01T10:00:00", data=b"X")


def test_existing_file_found_in_place(tmp_path):
    saves = tmp_path / "saves"
    existing = saves / "Snes9x" / "Sonic.srm"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    target = resolve_target(_item(), saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == existing


def test_existing_file_with_bracket_tag_found(tmp_path):
    # ROM/save names use [..] dump tags; rglob must match them literally.
    saves = tmp_path / "saves"
    existing = saves / "Pokemon [!].srm"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    item = _item(file_name="Pokemon [!].srm")
    target = resolve_target(item, saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == existing


def test_new_flat_when_sort_off(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(), saves, tmp_path / "states",
                            sort_saves_by_core=False, sort_states_by_core=False)
    assert target == saves / "Sonic.srm"


def test_new_per_core_when_sort_on(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(emulator="genesis"), saves, tmp_path / "states",
                            sort_saves_by_core=True, sort_states_by_core=False)
    assert target == saves / "genesis" / "Sonic.srm"


def test_new_sort_on_but_no_emulator_falls_back_flat(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    target = resolve_target(_item(emulator=None), saves, tmp_path / "states",
                            sort_saves_by_core=True, sort_states_by_core=False)
    assert target == saves / "Sonic.srm"


def test_state_uses_states_dir_and_flag(tmp_path):
    states = tmp_path / "states"
    states.mkdir()
    item = _item(kind="state", file_name="Sonic.state1", emulator="genesis")
    target = resolve_target(item, tmp_path / "saves", states,
                            sort_saves_by_core=False, sort_states_by_core=True)
    assert target == states / "genesis" / "Sonic.state1"


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    return httpx.HTTPStatusError("mock", request=MagicMock(), response=response)


def test_pull_content_404_skips_file_continues_batch(tmp_path):
    # State id=14 returns 404 content; the .srm and .state from saves must still write.
    class _Client404:
        def list_saves(self, rom_id):
            return [
                {"id": 4, "file_name": "Sonic.srm", "emulator": "mGBA", "updated_at": ""},
                {"id": 5, "file_name": "Sonic.state", "emulator": "mGBA", "updated_at": ""},
            ]
        def list_states(self, rom_id):
            return [{"id": 14, "file_name": "Sonic.state", "emulator": "mGBA", "updated_at": ""}]
        def download_save_content(self, sid):
            return {4: b"SRM", 5: b"STATE"}[sid]
        def download_state_content(self, sid):
            raise _http_status_error(404)

    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    errors = []
    summary = pull_games(_Client404(), [_entry()], settings,
                         on_error=lambda p, exc: errors.append(p))

    assert summary["written"] == 2
    assert summary["failed"] == 1
    assert len(errors) == 1
    assert errors[0].name == "Sonic.state"


def test_pull_content_non404_http_error_propagates(tmp_path):
    class _Client403:
        def list_saves(self, rom_id):
            return [{"id": 9, "file_name": "Sonic.srm", "emulator": "genesis", "updated_at": ""}]
        def list_states(self, rom_id):
            return []
        def download_save_content(self, sid):
            raise _http_status_error(403)
        def download_state_content(self, sid):  # pragma: no cover
            return b""

    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    with pytest.raises(httpx.HTTPStatusError):
        pull_games(_Client403(), [_entry()], settings)


def test_one_rom_shim_works_with_pull_games(tmp_path):
    # Verify the one-rom shim used by pull_action exposes .rom_id so pull_games
    # can iterate it without touching mapping_cache.
    class _Shim:
        def __init__(self, rom_id):
            self.rom_id = rom_id

    client = FakeClient(
        saves={42: [{"id": 9, "file_name": "Game.srm", "emulator": "genesis",
                     "updated_at": "2026-06-17T10:00:00"}]},
        blobs={("save", 9): b"DATA"})
    settings = _Settings(tmp_path / "saves", tmp_path / "states")
    summary = pull_games(client, [_Shim(42)], settings)
    assert summary["written"] == 1
    assert (tmp_path / "saves" / "Game.srm").read_bytes() == b"DATA"
