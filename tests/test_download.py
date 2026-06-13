import io
import zipfile

from emusync.download import download_rom
from emusync.romm_client import Rom
from emusync.mapping_cache import MappingCache


class FakeClient:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.requested = None
    def download_rom_content(self, rom_id, out_name):
        self.requested = (rom_id, out_name)
        return self._payload


def test_single_file_rom_written_and_cached(tmp_path):
    rom = Rom(id=7, name="Sonic", platform_slug="genesis",
              fs_name="Sonic (USA).md", fs_name_no_ext="Sonic (USA)",
              file_names=["Sonic (USA).md"])
    client = FakeClient(b"MDDATA")
    cache = MappingCache(tmp_path / "cache.json")

    m3u = download_rom(rom, client, roms_root=tmp_path, cache=cache, overrides={})

    assert m3u == tmp_path / "genesis" / "Sonic (USA).m3u"
    assert (tmp_path / "genesis" / "Sonic (USA)" / "Sonic (USA).md").read_bytes() == b"MDDATA"
    entry = cache.find_by_basename("Sonic (USA)")
    assert entry.rom_id == 7 and entry.system == "genesis"


def test_multi_file_rom_zip_is_extracted(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("FF7 (Disc 1).cue", "CUE1")
        zf.writestr("FF7 (Disc 1).bin", "BIN1")
    rom = Rom(id=9, name="FF7", platform_slug="psx",
              fs_name="FF7.cue", fs_name_no_ext="FF7",
              file_names=["FF7 (Disc 1).cue", "FF7 (Disc 1).bin"])

    m3u = download_rom(rom, FakeClient(buf.getvalue()), roms_root=tmp_path,
                       cache=MappingCache(tmp_path / "c.json"), overrides={},
                       is_multi_file=True)

    folder = tmp_path / "psx" / "FF7"
    assert (folder / "FF7 (Disc 1).cue").read_text() == "CUE1"
    # m3u references only the cue descriptor
    assert m3u.read_text().strip() == "FF7/FF7 (Disc 1).cue"
