import threading
from pathlib import Path

import httpx
import pytest

from romhop.romm_client import (
    RommClient, Rom, RomDetail, romm_game_url,
    RomAlreadyExists, UploadCancelled, InsufficientScopeError,
    ScanError, ScanConnectError,
    UPLOAD_CHUNK_SIZE,
)


def _client(handler) -> RommClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url="http://romm.test", transport=transport)
    return RommClient(http=http, token="rmm_test")


def test_set_token_swaps_authorization_header():
    seen = []

    def handler(request):
        seen.append(request.headers["Authorization"])
        return httpx.Response(200, json=[])

    client = _client(handler)
    client.list_roms()
    client.set_token("rmm_new")
    client.list_roms()
    assert seen == ["Bearer rmm_test", "Bearer rmm_new"]


def test_empty_token_drops_authorization_header():
    # `Bearer ` (trailing space) is an illegal header value: h11 rejects it
    # before the request leaves, surfacing as "Illegal header value b'Bearer '".
    seen = []

    def handler(request):
        seen.append(request.headers.get("Authorization"))
        return httpx.Response(200, json=[])

    client = _client(handler)
    client.set_token("")
    assert "Authorization" not in client._http.headers
    client.list_roms()  # must not raise LocalProtocolError
    assert seen == [None]


def test_list_roms_parses_fields():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer rmm_test"
        assert request.url.path == "/api/roms"
        return httpx.Response(200, json=[{
            "id": 18, "name": "Metal Gear Solid (USA)", "platform_slug": "psx",
            "fs_name": "Metal Gear Solid (USA).cue",
            "fs_name_no_ext": "Metal Gear Solid (USA)",
            "has_multiple_files": False,
            "files": [{"id": 1, "file_name": "Metal Gear Solid (USA).cue",
                       "file_size_bytes": 105, "full_path": "psx/x.cue",
                       "crc_hash": None, "md5_hash": None, "sha1_hash": None}],
        }])
    roms = _client(handler).list_roms()
    assert roms[0] == Rom(
        id=18, name="Metal Gear Solid (USA)", platform_slug="psx",
        fs_name="Metal Gear Solid (USA).cue",
        fs_name_no_ext="Metal Gear Solid (USA)",
        file_names=["Metal Gear Solid (USA).cue"],
    )


def test_upload_save_posts_multipart():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["rom_id"] = request.url.params.get("rom_id")
        seen["emulator"] = request.url.params.get("emulator")
        seen["body"] = request.content
        return httpx.Response(200, json={"id": 5})
    _client(handler).upload_save(
        rom_id=18, emulator="genesis_plus_gx",
        file_name="Metal Gear Solid (USA).srm", data=b"SAVE",
    )
    assert seen["path"] == "/api/saves"
    assert seen["rom_id"] == "18"
    assert seen["emulator"] == "genesis_plus_gx"
    assert b"SAVE" in seen["body"]


def test_upload_state_posts_to_states_multipart():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["rom_id"] = request.url.params.get("rom_id")
        seen["emulator"] = request.url.params.get("emulator")
        seen["body"] = request.content
        return httpx.Response(200, json={"id": 7})
    _client(handler).upload_state(
        rom_id=18, emulator="genesis_plus_gx",
        file_name="Sonic.state1", data=b"STATE",
    )
    assert seen["path"] == "/api/states"
    assert seen["rom_id"] == "18"
    assert seen["emulator"] == "genesis_plus_gx"
    assert b'name="stateFile"' in seen["body"]
    assert b"STATE" in seen["body"]


def test_list_roms_handles_null_files():
    def handler(request):
        return httpx.Response(200, json=[{
            "id": 1, "name": "X", "platform_slug": "psx",
            "fs_name": "X.cue", "fs_name_no_ext": "X", "files": None,
        }])
    roms = _client(handler).list_roms()
    assert roms[0].file_names == []


def test_list_saves_requests_rom_id():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["rom_id"] = request.url.params.get("rom_id")
        return httpx.Response(200, json=[{"id": 5, "rom_id": 18}])
    out = _client(handler).list_saves(18)
    assert seen["path"] == "/api/saves"
    assert seen["rom_id"] == "18"
    assert out == [{"id": 5, "rom_id": 18}]


def test_download_save_content_returns_bytes():
    def handler(request):
        assert request.url.path == "/api/saves/5/content"
        return httpx.Response(200, content=b"SAVEBYTES")
    assert _client(handler).download_save_content(5) == b"SAVEBYTES"


def test_list_roms_reads_paginated_wrapper():
    # Real RomM returns CustomLimitOffsetPage: {"items": [...], "total": N, ...}
    def handler(request):
        assert request.url.path == "/api/roms"
        assert request.url.params.get("limit") == "500"
        assert request.url.params.get("offset") == "0"
        assert request.url.params.get("search_term") == "Sonic"
        return httpx.Response(200, json={
            "items": [{
                "id": 3, "name": "Sonic (USA)", "platform_slug": "genesis",
                "fs_name": "Sonic (USA).md", "fs_name_no_ext": "Sonic (USA)",
                "files": None,
            }],
            "total": 1, "limit": 500, "offset": 0,
        })
    roms = _client(handler).list_roms(search_term="Sonic")
    assert len(roms) == 1
    assert roms[0].id == 3
    assert roms[0].fs_name_no_ext == "Sonic (USA)"


def test_list_roms_parses_has_multiple_files():
    def handler(request):
        return httpx.Response(200, json={"items": [
            {"id": 1, "name": "A", "platform_slug": "psx", "fs_name": "A.m3u",
             "fs_name_no_ext": "A", "files": None, "has_multiple_files": True},
            {"id": 2, "name": "B", "platform_slug": "gba", "fs_name": "B.zip",
             "fs_name_no_ext": "B", "files": None},
        ], "total": 2})
    roms = _client(handler).list_roms()
    assert roms[0].has_multiple_files is True
    assert roms[1].has_multiple_files is False   # default when absent


def test_list_roms_captures_url_cover():
    import httpx
    from romhop.romm_client import RommClient

    def handler(request):
        return httpx.Response(200, json={"items": [{
            "id": 1, "name": "Sonic", "platform_slug": "genesis",
            "fs_name": "Sonic.md", "fs_name_no_ext": "Sonic",
            "files": [{"file_name": "Sonic.md"}],
            "url_cover": "/assets/covers/1.png",
        }], "total": 1, "limit": 500, "offset": 0})

    client = RommClient(httpx.Client(base_url="http://romm.test", transport=httpx.MockTransport(handler)))
    roms = client.list_roms()
    assert roms[0].url_cover == "/assets/covers/1.png"


def test_list_states_queries_rom_id():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["rom_id"] = request.url.params.get("rom_id")
        return httpx.Response(200, json=[{"id": 3, "file_name": "Sonic.state1",
                                          "emulator": "genesis", "updated_at": "2026-06-01T10:00:00"}])
    states = _client(handler).list_states(18)
    assert seen["path"] == "/api/states"
    assert seen["rom_id"] == "18"
    assert states[0]["file_name"] == "Sonic.state1"


def test_download_state_content_returns_bytes():
    def handler(request):
        assert request.url.path == "/api/states/3/content"
        return httpx.Response(200, content=b"STATEBYTES")
    assert _client(handler).download_state_content(3) == b"STATEBYTES"


def test_list_roms_captures_platform_name():
    import httpx
    from romhop.romm_client import RommClient

    def handler(request):
        return httpx.Response(200, json={
            "items": [{
                "id": 1, "name": "Sonic", "platform_slug": "genesis",
                "platform_name": "Sega Genesis",
                "fs_name": "Sonic.md", "fs_name_no_ext": "Sonic",
                "files": [], "has_multiple_files": False, "url_cover": None,
            }],
            "total": 1, "limit": 500, "offset": 0,
        })

    client = RommClient(httpx.Client(transport=httpx.MockTransport(handler),
                                     base_url="http://x"))
    roms = client.list_roms()
    assert roms[0].platform_name == "Sega Genesis"


def test_stream_rom_content_yields_total_and_chunks():
    body = b"Z" * 2500
    def handler(request):
        assert request.url.path == "/api/roms/9/content/g.3ds"
        return httpx.Response(200, content=body)
    out = bytearray()
    with _client(handler).stream_rom_content(9, "g.3ds") as (total, chunks):
        assert total == 2500            # from Content-Length
        for c in chunks:
            out.extend(c)
    assert bytes(out) == body


def test_stream_rom_content_total_none_without_content_length():
    def handler(request):
        # streaming generator response => httpx sets no Content-Length
        return httpx.Response(200, content=iter([b"a", b"b"]))
    with _client(handler).stream_rom_content(1, "x") as (total, chunks):
        assert total is None
        assert b"".join(chunks) == b"ab"


def test_ping_hits_roms_with_limit_one():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["limit"] = request.url.params.get("limit")
        return httpx.Response(200, json={"items": [], "total": 0, "limit": 1, "offset": 0})

    _client(handler).ping()
    assert seen["path"] == "/api/roms"
    assert seen["limit"] == "1"


def test_ping_raises_on_http_error():
    import pytest

    def handler(request):
        return httpx.Response(401, json={"detail": "bad token"})

    with pytest.raises(httpx.HTTPStatusError):
        _client(handler).ping()


def test_get_rom_parses_detail():
    def handler(request):
        assert request.url.path == "/api/roms/42"
        return httpx.Response(200, json={
            "id": 42, "name": "Sonic",
            "summary": "A fast hedgehog.",
            "first_release_date_string": "1991",
            "genres": [{"name": "Platform"}, {"name": "Action"}],
            "fs_size_bytes": 524288,
        })

    detail = _client(handler).get_rom(42)
    assert isinstance(detail, RomDetail)
    assert detail.summary == "A fast hedgehog."
    assert detail.release_date == "1991"
    assert detail.genres == ["Platform", "Action"]
    assert detail.file_size == 524288


def test_get_rom_tolerates_missing_fields():
    def handler(request):
        return httpx.Response(200, json={"id": 7, "name": "Bare"})

    detail = _client(handler).get_rom(7)
    assert detail.summary is None
    assert detail.release_date is None
    assert detail.genres == []
    assert detail.file_size is None


def test_get_rom_accepts_plain_string_genres():
    def handler(request):
        return httpx.Response(200, json={"genres": ["RPG"]})

    assert _client(handler).get_rom(1).genres == ["RPG"]


def test_romm_game_url_basic():
    assert romm_game_url("https://romm.example.com", 42) == "https://romm.example.com/rom/42"


def test_romm_game_url_strips_trailing_slash():
    assert romm_game_url("https://romm.example.com/", 7) == "https://romm.example.com/rom/7"


# ---------------------------------------------------------------------------
# list_platforms
# ---------------------------------------------------------------------------

def test_list_platforms_returns_list():
    def handler(request):
        assert request.url.path == "/api/platforms"
        return httpx.Response(200, json=[{"id": 1, "fs_slug": "genesis"}])
    result = _client(handler).list_platforms()
    assert result == [{"id": 1, "fs_slug": "genesis"}]


def test_list_platforms_raises_scope_error_on_403():
    def handler(request):
        return httpx.Response(403, json={"detail": "Forbidden"})
    with pytest.raises(InsufficientScopeError) as exc_info:
        _client(handler).list_platforms()
    assert exc_info.value.scope == "platforms.read"


# ---------------------------------------------------------------------------
# create_platform
# ---------------------------------------------------------------------------

def test_create_platform_reuses_existing_by_fs_slug():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        assert request.url.path == "/api/platforms"
        return httpx.Response(200, json=[{"id": 7, "fs_slug": "genesis"}])
    result = _client(handler).create_platform("genesis")
    assert result == {"id": 7, "fs_slug": "genesis"}
    # only GET, no POST
    assert all(r.method == "GET" for r in [])  # checked via calls
    assert len([c for c in calls if c == "/api/platforms"]) == 1


def test_create_platform_creates_when_absent():
    seen = []
    def handler(request):
        seen.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": 3, "fs_slug": "snes"}])
        # POST
        assert request.method == "POST"
        return httpx.Response(201, json={"id": 99, "fs_slug": "genesis"})
    result = _client(handler).create_platform("genesis")
    assert result["id"] == 99
    assert ("GET", "/api/platforms") in seen
    assert ("POST", "/api/platforms") in seen


def test_create_platform_scope_error_on_post_403():
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(403, json={"detail": "Forbidden"})
    with pytest.raises(InsufficientScopeError) as exc_info:
        _client(handler).create_platform("genesis")
    assert exc_info.value.scope == "platforms.write"


# ---------------------------------------------------------------------------
# upload_rom
# ---------------------------------------------------------------------------

def test_upload_rom_success(tmp_path):
    data = b"X" * 10
    rom_file = tmp_path / "Sonic.md"
    rom_file.write_bytes(data)

    seen = []
    def handler(request):
        seen.append((request.method, request.url.path))
        if request.url.path == "/api/roms/upload/start":
            assert request.headers["x-upload-platform"] == "7"
            assert request.headers["x-upload-filename"] == "Sonic.md"
            assert request.headers["x-upload-total-size"] == "10"
            assert request.headers["x-upload-total-chunks"] == "1"
            return httpx.Response(201, json={"upload_id": "abc123"})
        if "/upload/abc123" in request.url.path and request.method == "PUT":
            assert request.headers["x-chunk-index"] == "0"
            assert request.content == data
            return httpx.Response(200)
        if request.url.path == "/api/roms/upload/abc123/complete":
            return httpx.Response(201, content=b"")
        raise ValueError(f"unexpected {request.method} {request.url.path}")

    _client(handler).upload_rom(platform_id=7, file_path=rom_file, file_name="Sonic.md")
    paths = [p for _, p in seen]
    assert "/api/roms/upload/start" in paths
    assert "/api/roms/upload/abc123" in paths
    assert "/api/roms/upload/abc123/complete" in paths


def test_upload_rom_multi_chunk(tmp_path):
    chunk_size = 4
    data = b"ABCDEFGH"  # 8 bytes → 2 chunks of 4
    rom_file = tmp_path / "game.bin"
    rom_file.write_bytes(data)

    chunks_received = []
    def handler(request):
        if request.url.path == "/api/roms/upload/start":
            assert request.headers["x-upload-total-chunks"] == "2"
            return httpx.Response(201, json={"upload_id": "uid"})
        if request.method == "PUT":
            chunks_received.append((
                int(request.headers["x-chunk-index"]),
                request.content,
            ))
            return httpx.Response(200)
        if "complete" in request.url.path:
            return httpx.Response(201, content=b"")
        raise ValueError(request.url.path)

    _client(handler).upload_rom(
        platform_id=1, file_path=rom_file, file_name="game.bin", chunk_size=chunk_size,
    )
    assert chunks_received == [(0, b"ABCD"), (1, b"EFGH")]


def test_upload_rom_already_exists(tmp_path):
    rom_file = tmp_path / "Dupe.md"
    rom_file.write_bytes(b"data")

    def handler(request):
        if request.url.path == "/api/roms/upload/start":
            return httpx.Response(400, json={"detail": "File Dupe.md already exists"})
        raise ValueError("should not reach chunks")

    with pytest.raises(RomAlreadyExists):
        _client(handler).upload_rom(platform_id=1, file_path=rom_file, file_name="Dupe.md")


def test_upload_rom_cancel_during_chunks(tmp_path):
    data = b"X" * (UPLOAD_CHUNK_SIZE + 1)
    rom_file = tmp_path / "big.bin"
    rom_file.write_bytes(data)

    stop = threading.Event()
    cancelled_ids = []

    def handler(request):
        if request.url.path == "/api/roms/upload/start":
            return httpx.Response(201, json={"upload_id": "u1"})
        if request.method == "PUT" and "/api/roms/upload/u1" == request.url.path:
            stop.set()  # trigger cancel before next chunk
            return httpx.Response(200)
        if "cancel" in request.url.path:
            cancelled_ids.append(request.url.path)
            return httpx.Response(204)
        raise ValueError(request.url.path)

    with pytest.raises(UploadCancelled):
        _client(handler).upload_rom(
            platform_id=1, file_path=rom_file, file_name="big.bin", stop_event=stop,
        )
    assert any("cancel" in p for p in cancelled_ids)


def test_upload_rom_scope_error(tmp_path):
    rom_file = tmp_path / "x.md"
    rom_file.write_bytes(b"data")

    def handler(request):
        return httpx.Response(403, json={"detail": "Forbidden"})

    with pytest.raises(InsufficientScopeError) as exc_info:
        _client(handler).upload_rom(platform_id=1, file_path=rom_file, file_name="x.md")
    assert exc_info.value.scope == "roms.write"


def test_upload_rom_progress_fn(tmp_path):
    data = b"HELLO"
    rom_file = tmp_path / "game.md"
    rom_file.write_bytes(data)
    reported = []

    def handler(request):
        if "start" in request.url.path:
            return httpx.Response(201, json={"upload_id": "p1"})
        if request.method == "PUT":
            return httpx.Response(200)
        if "complete" in request.url.path:
            return httpx.Response(201, content=b"")
        raise ValueError(request.url.path)

    _client(handler).upload_rom(
        platform_id=1, file_path=rom_file, file_name="game.md",
        progress_fn=reported.append,
    )
    assert sum(reported) == len(data)


# ---------------------------------------------------------------------------
# trigger_scan  (uses fake Socket.IO factory)
# ---------------------------------------------------------------------------

class _FakeSio:
    """Synchronous fake that fires scan:done immediately on emit."""

    def __init__(self, *, fail_connect: bool = False, ko: bool = False, timeout_sim: bool = False):
        self._handlers: dict = {}
        self._fail_connect = fail_connect
        self._ko = ko
        self._timeout_sim = timeout_sim
        self.connected_url: str | None = None
        self.emitted: list = []
        self.disconnected = False

    def on(self, event):
        def decorator(fn):
            self._handlers[event] = fn
            return fn
        return decorator

    def connect(self, url, headers=None, socketio_path=None, transports=None):
        if self._fail_connect:
            raise ConnectionRefusedError("fake connect failure")
        self.connected_url = url

    def emit(self, event, data):
        self.emitted.append((event, data))
        if self._timeout_sim:
            return  # never fire any handler
        evt = "scan:done_ko" if self._ko else "scan:done"
        handler = self._handlers.get(evt)
        if handler:
            handler({"new_roms": 3})

    def disconnect(self):
        self.disconnected = True


def _scan_client() -> RommClient:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=[]))
    http = httpx.Client(base_url="http://romm.test", transport=transport)
    return RommClient(http=http, token="tok")


def test_trigger_scan_success():
    fake = _FakeSio()
    result = _scan_client().trigger_scan(7, _sio_factory=lambda: fake)
    assert result == {"new_roms": 3}
    assert fake.emitted[0] == ("scan", {
        "platforms": [7], "roms_ids": [], "type": "quick", "apis": [],
    })
    assert fake.disconnected


def test_trigger_scan_connect_error():
    fake = _FakeSio(fail_connect=True)
    with pytest.raises(ScanConnectError):
        _scan_client().trigger_scan(7, _sio_factory=lambda: fake)


def test_trigger_scan_done_ko():
    fake = _FakeSio(ko=True)
    with pytest.raises(ScanError):
        _scan_client().trigger_scan(7, _sio_factory=lambda: fake)


def test_trigger_scan_timeout():
    fake = _FakeSio(timeout_sim=True)
    with pytest.raises(ScanError, match="timed out"):
        _scan_client().trigger_scan(7, timeout=0.05, _sio_factory=lambda: fake)


# ---------------------------------------------------------------------------
# find_roms_by_fs_names
# ---------------------------------------------------------------------------

def test_find_roms_by_fs_names_filters_platform_and_name():
    def handler(request):
        return httpx.Response(200, json={"items": [
            {"id": 1, "name": "Sonic", "platform_slug": "genesis",
             "fs_name": "Sonic.md", "fs_name_no_ext": "Sonic", "files": []},
            {"id": 2, "name": "Mario", "platform_slug": "snes",
             "fs_name": "Mario.sfc", "fs_name_no_ext": "Mario", "files": []},
            {"id": 3, "name": "Knuckles", "platform_slug": "genesis",
             "fs_name": "Knuckles.md", "fs_name_no_ext": "Knuckles", "files": []},
        ], "total": 3})
    roms = _client(handler).find_roms_by_fs_names("genesis", {"Sonic.md"})
    assert len(roms) == 1
    assert roms[0].id == 1


def test_find_roms_by_fs_names_empty_when_no_match():
    def handler(request):
        return httpx.Response(200, json={"items": [
            {"id": 1, "name": "Sonic", "platform_slug": "genesis",
             "fs_name": "Sonic.md", "fs_name_no_ext": "Sonic", "files": []},
        ], "total": 1})
    roms = _client(handler).find_roms_by_fs_names("snes", {"Sonic.md"})
    assert roms == []
