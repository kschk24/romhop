from __future__ import annotations

import threading
from pathlib import Path

import httpx
import pytest

from romhop.local_index import LocalGame
from romhop.mapping_cache import MappingCache
from romhop.romm_client import RommClient, RomAlreadyExists, UploadCancelled


def _client(handler) -> RommClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url="http://romm.test", transport=transport)
    return RommClient(http=http, token="rmm_test")


def _game(system="snes", name="Mario.sfc", files=None) -> LocalGame:
    if files is None:
        files = [name]
    return LocalGame(system=system, game_name=name, file_names=files, match_key=name.lower())


# --- upload.py unit tests ---


def test_upload_game_skips_artifact_files(tmp_path):
    """Files with .m3u or .txt suffix are skipped; only real rom files are uploaded."""
    from romhop.upload import _is_real_rom_file

    assert _is_real_rom_file("Game.sfc") is True
    assert _is_real_rom_file("Game.cue") is True
    assert _is_real_rom_file("Game.bin") is True
    assert _is_real_rom_file("Game.m3u") is False
    assert _is_real_rom_file("noload.txt") is False
    assert _is_real_rom_file("Game.txt") is False


def test_upload_game_flat_path_resolution(tmp_path):
    """_file_path finds a flat file in the system dir."""
    from romhop.upload import _file_path

    system_dir = tmp_path / "snes"
    system_dir.mkdir()
    rom = system_dir / "Mario.sfc"
    rom.write_bytes(b"data")

    game = _game("snes", "Mario.sfc")
    assert _file_path(game, tmp_path, "Mario.sfc") == rom


def test_upload_game_subfolder_path_fallback(tmp_path):
    """_file_path falls back to game_name subfolder when flat path doesn't exist."""
    from romhop.upload import _file_path

    system_dir = tmp_path / "psx"
    system_dir.mkdir()
    sub = system_dir / "Metal Gear"
    sub.mkdir()
    disc = sub / "Disc1.cue"
    disc.write_bytes(b"data")

    game = LocalGame(system="psx", game_name="Metal Gear",
                     file_names=["Disc1.cue"], match_key="metal gear")
    assert _file_path(game, tmp_path, "Disc1.cue") == disc


def test_upload_game_uploads_and_seeds_cache(tmp_path):
    """upload_game uploads files, triggers scan, finds roms, seeds cache."""
    from romhop.upload import upload_game
    from romhop.activity import ActivityKind

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"x" * 1024)

    upload_start_calls = []
    upload_put_calls = []
    scan_connected = []
    events = []

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            upload_start_calls.append(dict(request.headers))
            return httpx.Response(201, json={"upload_id": "uid-1"})
        if path.startswith("/api/roms/upload/uid-1") and request.method == "PUT":
            upload_put_calls.append(request.headers.get("x-chunk-index"))
            return httpx.Response(200)
        if path == "/api/roms/upload/uid-1/complete":
            return httpx.Response(201)
        if path == "/api/roms":
            return httpx.Response(200, json=[{
                "id": 42, "name": "Mario", "platform_slug": "snes",
                "fs_name": "Mario.sfc", "fs_name_no_ext": "Mario",
                "has_multiple_files": False, "files": [],
            }])
        return httpx.Response(404)

    client = _client(handler)

    # Patch trigger_scan to simulate success.
    def fake_trigger_scan(platform_id, *, timeout=60.0, _sio_factory=None):
        scan_connected.append(platform_id)
        return {"new_roms": 1}

    client.trigger_scan = fake_trigger_scan

    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")

    def on_event(e):
        events.append(e)

    result = upload_game(
        game, client,
        platform_id=1,
        platform_slug="snes",
        roms_root=tmp_path,
        cache=cache,
        scan_timeout=10.0,
        on_event=on_event,
    )

    assert "Mario.sfc" in result.uploaded_files
    assert result.skipped_files == []
    assert result.seeded is True
    assert result.fallback is False
    assert scan_connected == [1]
    assert any(e.kind == ActivityKind.UPLOAD_DONE for e in events)
    # Cache should have an entry for the new rom.
    assert cache.find_by_basename("Mario") is not None


def test_upload_game_dedup_skip(tmp_path):
    """RomAlreadyExists from upload/start → file goes to skipped_files, not error."""
    from romhop.upload import upload_game
    from romhop.activity import ActivityKind

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"data")

    def handler(request):
        if request.url.path == "/api/roms/upload/start":
            return httpx.Response(400, json={"detail": "File Mario.sfc already exists"})
        return httpx.Response(404)

    client = _client(handler)
    events = []
    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")

    result = upload_game(
        game, client,
        platform_id=1, platform_slug="snes",
        roms_root=tmp_path, cache=cache,
        scan_timeout=0.0,
        on_event=lambda e: events.append(e),
    )

    assert result.uploaded_files == []
    assert "Mario.sfc" in result.skipped_files
    assert any(e.kind == ActivityKind.UPLOAD_DONE for e in events)
    # Not an error event.
    assert not any(e.is_error for e in events)


def test_upload_game_scan_connect_fallback(tmp_path):
    """ScanConnectError → fallback=True, basic mapping entry seeded."""
    from romhop.upload import upload_game
    from romhop.romm_client import ScanConnectError

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"x" * 512)

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            return httpx.Response(201, json={"upload_id": "uid-2"})
        if "/upload/uid-2" in path and request.method == "PUT":
            return httpx.Response(200)
        if path == "/api/roms/upload/uid-2/complete":
            return httpx.Response(201)
        return httpx.Response(404)

    client = _client(handler)

    def fail_scan(*args, **kwargs):
        raise ScanConnectError("connection refused")

    client.trigger_scan = fail_scan

    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")
    events = []

    result = upload_game(
        game, client,
        platform_id=1, platform_slug="snes",
        roms_root=tmp_path, cache=cache,
        scan_timeout=10.0,
        on_event=lambda e: events.append(e),
    )

    assert "Mario.sfc" in result.uploaded_files
    assert result.fallback is True
    assert result.seeded is True
    assert "run a Scan" in events[-1].message


def test_upload_game_cancel(tmp_path):
    """stop_event pre-set cancels before any upload, raises UploadCancelled."""
    from romhop.upload import upload_game

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"data")

    http_calls = []

    def handler(request):
        http_calls.append(request.url.path)
        return httpx.Response(404)

    client = _client(handler)
    stop = threading.Event()
    stop.set()  # pre-cancelled

    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")

    with pytest.raises(UploadCancelled):
        upload_game(
            game, client,
            platform_id=1, platform_slug="snes",
            roms_root=tmp_path, cache=cache,
            scan_timeout=10.0,
            stop_event=stop,
        )

    # No HTTP calls made — cancelled before upload/start
    assert http_calls == []


def test_upload_game_no_real_files(tmp_path):
    """Game with only artifact files → no upload, ERROR event."""
    from romhop.upload import upload_game
    from romhop.activity import ActivityKind

    called = []
    client = _client(lambda r: (called.append(r), httpx.Response(404))[1])
    cache = MappingCache(tmp_path / "cache.json")

    game = LocalGame(system="snes", game_name="Game",
                     file_names=["Game.m3u", "noload.txt"], match_key="game")
    events = []
    result = upload_game(
        game, client,
        platform_id=1, platform_slug="snes",
        roms_root=tmp_path, cache=cache,
        on_event=lambda e: events.append(e),
    )

    assert result.uploaded_files == []
    assert called == []  # no HTTP calls made
    assert any(e.is_error for e in events)
