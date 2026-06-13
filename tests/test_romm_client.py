import httpx

from emusync.romm_client import RommClient, Rom


def _client(handler) -> RommClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url="http://romm.test", transport=transport)
    return RommClient(http=http, token="rmm_test")


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


def test_download_rom_content_returns_bytes():
    def handler(request):
        assert request.url.path == "/api/roms/18/content/game.zip"
        return httpx.Response(200, content=b"ROMBYTES")
    data = _client(handler).download_rom_content(18, "game.zip")
    assert data == b"ROMBYTES"


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


def test_download_rom_content_quotes_special_chars():
    seen = {}
    def handler(request):
        seen["raw_path"] = request.url.raw_path
        return httpx.Response(200, content=b"X")
    _client(handler).download_rom_content(18, "Final Fantasy VII (Europe)/Disc 1.cue")
    # httpx decodes %2F back to / in .path, so check raw_path (bytes) to confirm
    # the slash inside out_name was percent-encoded and didn't corrupt the path structure
    assert b"%2F" in seen["raw_path"]


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
