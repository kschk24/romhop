import io
import zipfile

from romhop.download import download_rom
from romhop.romm_client import Rom
from romhop.mapping_cache import MappingCache


class FakeClient:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.requested = None
    def download_rom_content(self, rom_id, out_name, on_progress=None):
        self.requested = (rom_id, out_name)
        return self._payload


def _zip_bytes(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_single_file_rom_written_flat_and_cached(tmp_path):
    rom = Rom(id=7, name="Sonic", platform_slug="genesis",
              fs_name="Sonic (USA).md", fs_name_no_ext="Sonic (USA)",
              file_names=["Sonic (USA).md"])
    client = FakeClient(b"MDDATA")
    cache = MappingCache(tmp_path / "cache.json")

    written = download_rom(rom, client, roms_root=tmp_path, cache=cache, overrides={})

    # flat: file sits directly in the platform folder, no subfolder, no .m3u
    assert written == tmp_path / "genesis" / "Sonic (USA).md"
    assert written.read_bytes() == b"MDDATA"
    assert not (tmp_path / "genesis" / "Sonic (USA)").exists()
    assert not (tmp_path / "genesis" / "Sonic (USA).m3u").exists()
    # cache entry persisted and reloads
    reloaded = MappingCache(tmp_path / "cache.json")
    assert reloaded.find_by_basename("Sonic (USA)").rom_id == 7


def test_single_file_zip_rom_stays_flat(tmp_path):
    # The rom is itself a .zip (cartridge rom). Even though the payload is a zip,
    # it must be written as-is, not extracted.
    payload = _zip_bytes({"Sonic Advance (USA).gba": "ROM"})
    rom = Rom(id=8, name="Sonic Advance", platform_slug="gba",
              fs_name="Sonic Advance (USA).zip", fs_name_no_ext="Sonic Advance (USA)",
              file_names=[])
    cache = MappingCache(tmp_path / "c.json")

    written = download_rom(rom, FakeClient(payload), roms_root=tmp_path, cache=cache, overrides={})

    assert written == tmp_path / "gba" / "Sonic Advance (USA).zip"
    assert written.read_bytes() == payload          # not extracted
    assert not (tmp_path / "gba" / "Sonic Advance (USA)").exists()


def test_multi_disc_zip_extracted_to_subfolder(tmp_path):
    # Non-archive fs_name + zip payload => server bundle => subfolder + our own .m3u.
    payload = _zip_bytes({
        "FF7 (Disc 1).cue": "CUE1", "FF7 (Disc 1).bin": "BIN1",
        "FF7 (Disc 2).cue": "CUE2", "FF7 (Disc 2).bin": "BIN2",
    })
    rom = Rom(id=9, name="FF7", platform_slug="psx",
              fs_name="FF7.cue", fs_name_no_ext="FF7", file_names=[])
    cache = MappingCache(tmp_path / "c.json")

    m3u = download_rom(rom, FakeClient(payload), roms_root=tmp_path, cache=cache, overrides={})

    folder = tmp_path / "psx" / "FF7"
    assert (folder / "FF7 (Disc 1).cue").read_text() == "CUE1"
    assert (folder / "noload.txt").exists()
    # our .m3u lists only the cue descriptors, in natural order
    assert m3u == tmp_path / "psx" / "FF7.m3u"
    assert m3u.read_text() == "FF7/FF7 (Disc 1).cue\nFF7/FF7 (Disc 2).cue\n"
    assert cache.find_by_basename("FF7").rom_id == 9


def test_multi_disc_drops_romm_bundled_m3u_and_noload(tmp_path):
    # RomM's bundle includes its own .m3u + noload.txt; we must not write them into
    # the subfolder (write_game rebuilds them).
    payload = _zip_bytes({
        "Game.m3u": "Game/Game (Disc 1).cue\n",
        "Game/noload.txt": "",
        "Game (Disc 1).cue": "C1", "Game (Disc 1).bin": "B1",
    })
    rom = Rom(id=11, name="Game", platform_slug="psx",
              fs_name="Game.cue", fs_name_no_ext="Game", file_names=[],
              has_multiple_files=True)
    cache = MappingCache(tmp_path / "c.json")

    m3u = download_rom(rom, FakeClient(payload), roms_root=tmp_path, cache=cache, overrides={})
    folder = tmp_path / "psx" / "Game"
    # RomM's own m3u is not deposited as a file inside the subfolder
    assert not (folder / "Game.m3u").exists()
    assert (folder / "Game (Disc 1).cue").read_text() == "C1"
    assert m3u.read_text() == "Game/Game (Disc 1).cue\n"


def test_download_rom_forwards_on_progress(tmp_path):
    seen = []

    class ProgClient:
        def download_rom_content(self, rom_id, out_name, on_progress=None):
            on_progress(5, 10)
            on_progress(10, 10)
            return b"X"

    rom = Rom(id=1, name="A", platform_slug="gba", fs_name="A.gba", fs_name_no_ext="A",
              file_names=["A.gba"])
    download_rom(rom, ProgClient(), roms_root=tmp_path, cache=MappingCache(tmp_path / "c.json"),
                 overrides={}, on_progress=lambda d, t: seen.append((d, t)))
    assert seen == [(5, 10), (10, 10)]


def test_friendly_download_error_maps_content_404_to_rescan_hint():
    import httpx

    from romhop.download import friendly_download_error

    req = httpx.Request("GET", "http://romm/api/roms/1542/content/Animal.3ds")
    resp = httpx.Response(404, request=req,
                          json={"detail": "No files found for ROM 1542"})
    exc = httpx.HTTPStatusError("404", request=req, response=resp)
    msg = friendly_download_error("Animal Crossing", 1542, exc)
    assert "Animal Crossing" in msg
    assert "1542" in msg
    assert "rescan" in msg.lower()


def test_friendly_download_error_flags_auth_failure():
    import httpx

    from romhop.download import friendly_download_error

    req = httpx.Request("GET", "http://romm/api/roms/1/content/x")
    resp = httpx.Response(403, request=req)
    exc = httpx.HTTPStatusError("403", request=req, response=resp)
    msg = friendly_download_error("X", 1, exc)
    assert "token" in msg.lower()


def test_friendly_download_error_falls_back_to_str_for_unknown():
    from romhop.download import friendly_download_error

    assert friendly_download_error("X", 1, ValueError("boom")) == "boom"


def test_rate_limiter_unlimited_never_sleeps():
    from romhop.download import RateLimiter
    slept = []
    rl = RateLimiter(0, now=lambda: 0.0, sleep=slept.append)
    rl.tick(10_000_000)
    assert slept == []


def test_rate_limiter_sleeps_when_ahead_of_cap():
    from romhop.download import RateLimiter
    t = [0.0]
    slept = []
    rl = RateLimiter(100, now=lambda: t[0], sleep=slept.append)
    rl.tick(200 * 1024)  # 200 KiB at 100 KiB/s should take ~2s
    assert slept and abs(sum(slept) - 2.0) < 0.05


def test_rate_limiter_no_sleep_when_under_cap():
    from romhop.download import RateLimiter
    t = [10.0]  # 10s elapsed
    slept = []
    rl = RateLimiter(100, now=lambda: t[0], sleep=slept.append)
    rl.tick(100 * 1024)  # 100 KiB in 10s = 10 KiB/s, under 100 => no sleep
    assert slept == []
