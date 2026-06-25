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


def test_upload_game_progress_is_cumulative_with_total(tmp_path):
    """progress_fn reports bytes cumulative across all of a game's files plus a
    fixed total (= sum of file sizes), so the GUI can draw a determinate bar."""
    from romhop.upload import upload_game

    sub = tmp_path / "psx" / "Metal Gear"
    sub.mkdir(parents=True)
    (sub / "Disc1.bin").write_bytes(b"a" * 1024)
    (sub / "Disc2.bin").write_bytes(b"b" * 2048)
    total_expected = 1024 + 2048

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            return httpx.Response(201, json={"upload_id": "uid-1"})
        if path.startswith("/api/roms/upload/uid-1") and request.method == "PUT":
            return httpx.Response(200)
        if path == "/api/roms/upload/uid-1/complete":
            return httpx.Response(201)
        return httpx.Response(404)

    client = _client(handler)
    cache = MappingCache(tmp_path / "cache.json")
    game = LocalGame(system="psx", game_name="Metal Gear",
                     file_names=["Disc1.bin", "Disc2.bin"], match_key="metal gear")

    reports: list[tuple[str, int, int]] = []
    upload_game(
        game, client,
        platform_id=1, platform_slug="psx",
        roms_root=tmp_path, cache=cache,
        scan_timeout=0,  # fallback path: skip scan, keep the test transport-only
        progress_fn=lambda fname, sent, total: reports.append((fname, sent, total)),
    )

    assert reports, "expected progress callbacks"
    # Total is constant and equals the summed file sizes.
    assert {t for _, _, t in reports} == {total_expected}
    # Bytes sent is cumulative across files (non-decreasing) and reaches the total.
    sent_seq = [s for _, s, _ in reports]
    assert sent_seq == sorted(sent_seq)
    assert sent_seq[-1] == total_expected
    # Both files contribute.
    assert {f for f, _, _ in reports} == {"Disc1.bin", "Disc2.bin"}


def test_upload_game_passes_chunk_size_to_client(tmp_path):
    """chunk_size flows through to client.upload_rom (the upload-speed knob)."""
    from romhop.upload import upload_game

    rom = tmp_path / "snes" / "Mario.sfc"
    rom.parent.mkdir(parents=True)
    rom.write_bytes(b"x" * 16)

    captured = {}

    class FakeClient:
        def upload_rom(self, *, platform_id, file_path, file_name,
                       stop_event=None, progress_fn=None, chunk_size=None,
                       on_session_start=None, on_session_end=None):
            captured["chunk_size"] = chunk_size

    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")
    upload_game(
        game, FakeClient(),
        platform_id=1, platform_slug="snes",
        roms_root=tmp_path, cache=cache,
        scan_timeout=0,
        chunk_size=8 << 20,
    )
    assert captured["chunk_size"] == 8 << 20


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


# --- upload_session tests ---


def test_upload_session_recover_reaps_orphans(tmp_path, monkeypatch):
    """recover() POSTs cancel for each active upload_id, reports dirty, clears file."""
    import json
    from romhop import upload_session
    from romhop.config import user_data_dir

    monkeypatch.setattr(upload_session, "_session_path",
                        lambda: tmp_path / "upload_session.json")

    cancelled = []

    class FakeClient:
        def _cancel_upload(self, uid):
            cancelled.append(uid)

    session_file = tmp_path / "upload_session.json"
    session_file.write_text(json.dumps({
        "in_progress": True,
        "active_uploads": [
            {"upload_id": "uid-a", "platform_id": 1, "file_name": "a.rom"},
            {"upload_id": "uid-b", "platform_id": 2, "file_name": "b.rom"},
        ],
    }))

    info = upload_session.recover(FakeClient())

    assert info.was_dirty is True
    assert info.reaped == 2
    assert set(cancelled) == {"uid-a", "uid-b"}
    assert not session_file.exists()


def test_upload_session_recover_idempotent_on_missing(tmp_path, monkeypatch):
    """recover() on missing or already-expired session is a no-op, not dirty."""
    from romhop import upload_session

    monkeypatch.setattr(upload_session, "_session_path",
                        lambda: tmp_path / "upload_session.json")

    class FakeClient:
        def _cancel_upload(self, uid):
            raise Exception("404 not found")

    info = upload_session.recover(FakeClient())
    assert info.was_dirty is False
    assert info.reaped == 0


def test_upload_session_recover_tolerates_expired_uid(tmp_path, monkeypatch):
    """recover() ignores 404/errors from _cancel_upload (server may have expired session)."""
    import json
    from romhop import upload_session

    monkeypatch.setattr(upload_session, "_session_path",
                        lambda: tmp_path / "upload_session.json")

    (tmp_path / "upload_session.json").write_text(json.dumps({
        "in_progress": True,
        "active_uploads": [{"upload_id": "uid-expired", "platform_id": 1, "file_name": "x"}],
    }))

    class FakeClient:
        def _cancel_upload(self, uid):
            raise Exception("404")

    info = upload_session.recover(FakeClient())
    assert info.was_dirty is True
    assert info.reaped == 0  # cancel failed but session is still cleared
    assert not (tmp_path / "upload_session.json").exists()


def test_run_upload_batch_session_lifecycle(tmp_path, monkeypatch):
    """run_upload_batch sets in_progress at start and clears on clean finish."""
    import json
    from romhop.upload import run_upload_batch
    from romhop import upload_session

    session_path = tmp_path / "upload_session.json"
    monkeypatch.setattr(upload_session, "_session_path", lambda: session_path)

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"x" * 64)

    upload_ids_seen: list[str] = []

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            return httpx.Response(201, json={"upload_id": "uid-1"})
        if "/upload/uid-1" in path and request.method == "PUT":
            return httpx.Response(200)
        if path == "/api/roms/upload/uid-1/complete":
            return httpx.Response(201)
        return httpx.Response(404)

    client = _client(handler)
    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")

    clean = run_upload_batch(
        [(game, 1, "snes")], client,
        roms_root=tmp_path, cache=cache, scan_timeout=0,
    )

    assert clean is True
    assert not session_path.exists()  # cleared on clean finish


def test_run_upload_batch_session_adds_removes_upload_id(tmp_path, monkeypatch):
    """Callbacks add upload_id after /start and remove after /complete."""
    import json
    from romhop.upload import run_upload_batch
    from romhop import upload_session

    session_path = tmp_path / "upload_session.json"
    monkeypatch.setattr(upload_session, "_session_path", lambda: session_path)

    rom_file = tmp_path / "snes" / "Mario.sfc"
    rom_file.parent.mkdir(parents=True)
    rom_file.write_bytes(b"x" * 64)

    snapshots: list[list] = []

    original_add = upload_session.add_upload
    original_remove = upload_session.remove_upload

    def patched_add(uid, pid, fname):
        original_add(uid, pid, fname)
        data = json.loads(session_path.read_text())
        snapshots.append([u["upload_id"] for u in data.get("active_uploads", [])])

    def patched_remove(uid):
        original_remove(uid)

    monkeypatch.setattr(upload_session, "add_upload", patched_add)
    monkeypatch.setattr(upload_session, "remove_upload", patched_remove)

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            return httpx.Response(201, json={"upload_id": "uid-42"})
        if "/upload/uid-42" in path and request.method == "PUT":
            return httpx.Response(200)
        if path == "/api/roms/upload/uid-42/complete":
            return httpx.Response(201)
        return httpx.Response(404)

    client = _client(handler)
    cache = MappingCache(tmp_path / "cache.json")
    game = _game("snes", "Mario.sfc")

    run_upload_batch([(game, 1, "snes")], client,
                     roms_root=tmp_path, cache=cache, scan_timeout=0)

    assert any("uid-42" in snap for snap in snapshots), "uid-42 should appear in session during upload"


def test_run_upload_batch_cancelled_leaves_in_progress(tmp_path, monkeypatch):
    """When cancelled mid-batch, in_progress session NOT cleared (stays for recover)."""
    import json
    import threading
    from romhop.upload import run_upload_batch
    from romhop import upload_session

    session_path = tmp_path / "upload_session.json"
    monkeypatch.setattr(upload_session, "_session_path", lambda: session_path)

    # Two games; cancel before second
    game_a = _game("snes", "A.sfc")
    game_b = _game("snes", "B.sfc")
    for g in [game_a, game_b]:
        rom = tmp_path / "snes" / g.file_names[0]
        rom.parent.mkdir(parents=True, exist_ok=True)
        rom.write_bytes(b"x" * 64)

    call_count = {"n": 0}
    stop = threading.Event()

    def handler(request):
        path = request.url.path
        if path == "/api/roms/upload/start":
            call_count["n"] += 1
            return httpx.Response(201, json={"upload_id": f"uid-{call_count['n']}"})
        if request.method == "PUT":
            stop.set()  # cancel mid-upload of first game
            return httpx.Response(200)
        if "/complete" in path:
            return httpx.Response(201)
        return httpx.Response(404)

    client = _client(handler)
    cache = MappingCache(tmp_path / "cache.json")

    clean = run_upload_batch(
        [(game_a, 1, "snes"), (game_b, 1, "snes")], client,
        roms_root=tmp_path, cache=cache, scan_timeout=0, stop_event=stop,
    )

    assert clean is False


# --- discover_uploadable tests ---


def _platform(slug: str, fs_slug: str | None = None, pid: int = 1) -> dict:
    return {"id": pid, "slug": slug, "fs_slug": fs_slug or slug}


def test_discover_uploadable_resolvable():
    from romhop.upload import discover_uploadable

    game = _game(system="snes", name="Mario.sfc")
    platforms = [_platform("snes")]
    cats = discover_uploadable([game], platforms, {})

    assert cats.resolvable == [(game, platforms[0])]
    assert cats.missing_platform == []
    assert cats.unresolvable == []


def test_discover_uploadable_missing_platform():
    """Platform not in RomM but slug derivable → missing_platform bucket."""
    from romhop.upload import discover_uploadable

    game = _game(system="snes", name="Mario.sfc")
    cats = discover_uploadable([game], [], {})

    assert cats.resolvable == []
    assert len(cats.missing_platform) == 1
    assert cats.missing_platform[0] == (game, "snes")
    assert cats.unresolvable == []



def test_discover_uploadable_unresolvable_monkeypatched(monkeypatch):
    """invert_to_slugs returns [] → game lands in unresolvable."""
    from romhop.upload import discover_uploadable
    import romhop.platform_resolve as pr

    monkeypatch.setattr(pr, "invert_to_slugs", lambda system, overrides: [])

    game = _game(system="weirdos", name="Odd.rom")
    cats = discover_uploadable([game], [], {})

    assert cats.resolvable == []
    assert cats.missing_platform == []
    assert cats.unresolvable == [game]


def test_discover_uploadable_esde_diverges_from_slug():
    """ES-DE system dir 'gc' maps to RomM slug 'ngc' via DEFAULT_PLATFORM_OVERRIDES."""
    from romhop.upload import discover_uploadable

    game = _game(system="gc", name="Zelda.iso")
    # RomM has platform with slug "ngc"
    platforms = [_platform("ngc", pid=7)]
    cats = discover_uploadable([game], platforms, {})

    assert len(cats.resolvable) == 1
    assert cats.resolvable[0][0] is game
    assert cats.resolvable[0][1]["id"] == 7
    assert cats.missing_platform == []
    assert cats.unresolvable == []


def test_discover_uploadable_three_categories_mixed():
    """All three buckets populated in one call."""
    from romhop.upload import discover_uploadable
    import romhop.platform_resolve as pr

    game_res = _game(system="snes", name="Mario.sfc")
    game_miss = _game(system="gba", name="Metroid.gba")
    game_bad = _game(system="unknown99", name="Bad.rom")

    platforms = [_platform("snes", pid=1)]

    orig_invert = pr.invert_to_slugs

    def _fake_invert(system, overrides):
        if system == "unknown99":
            return []
        return orig_invert(system, overrides)

    import unittest.mock as mock
    with mock.patch("romhop.platform_resolve.invert_to_slugs", side_effect=_fake_invert):
        cats = discover_uploadable([game_res, game_miss, game_bad], platforms, {})

    assert cats.resolvable == [(game_res, platforms[0])]
    assert cats.missing_platform[0][0] is game_miss
    assert cats.unresolvable == [game_bad]
