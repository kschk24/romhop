from romhop.mapping_cache import MappingCache, RomEntry
from romhop.sync import push_save_file


class RecordingClient:
    def __init__(self):
        self.uploads = []
    def upload_save(self, *, rom_id, emulator, file_name, data):
        self.uploads.append((rom_id, emulator, file_name, data))
        return {"id": 1}


def _cache(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=18, system="psx", game_name="Metal Gear Solid (USA)",
                       candidate_basenames={"Metal Gear Solid (USA)"}))
    return cache


def test_push_matches_basename_and_uploads(tmp_path):
    core_dir = tmp_path / "PCSX-ReARMed"
    core_dir.mkdir()
    save = core_dir / "Metal Gear Solid (USA).srm"
    save.write_bytes(b"SAVE")
    client = RecordingClient()
    seen = {}

    pushed = push_save_file(save, _cache(tmp_path), client, seen)

    assert pushed is True
    assert client.uploads == [(18, "PCSX-ReARMed", "Metal Gear Solid (USA).srm", b"SAVE")]


def test_push_skips_unchanged_second_time(tmp_path):
    core_dir = tmp_path / "PCSX-ReARMed"
    core_dir.mkdir()
    save = core_dir / "Metal Gear Solid (USA).srm"
    save.write_bytes(b"SAVE")
    client = RecordingClient()
    seen = {}
    push_save_file(save, _cache(tmp_path), client, seen)
    pushed_again = push_save_file(save, _cache(tmp_path), client, seen)
    assert pushed_again is False
    assert len(client.uploads) == 1


def test_push_returns_false_when_no_match(tmp_path):
    core_dir = tmp_path / "PCSX-ReARMed"
    core_dir.mkdir()
    save = core_dir / "Unknown Game.srm"
    save.write_bytes(b"X")
    client = RecordingClient()
    assert push_save_file(save, _cache(tmp_path), client, {}) is False
    assert client.uploads == []


def test_push_matches_state_file(tmp_path):
    core_dir = tmp_path / "PCSX-ReARMed"
    core_dir.mkdir()
    save = core_dir / "Metal Gear Solid (USA).state1"
    save.write_bytes(b"STATE")
    client = RecordingClient()
    pushed = push_save_file(save, _cache(tmp_path), client, {})
    assert pushed is True
    assert client.uploads == [(18, "PCSX-ReARMed", "Metal Gear Solid (USA).state1", b"STATE")]


def test_push_ignores_non_save_extension(tmp_path):
    core_dir = tmp_path / "PCSX-ReARMed"
    core_dir.mkdir()
    f = core_dir / "Metal Gear Solid (USA).txt"
    f.write_bytes(b"X")
    client = RecordingClient()
    assert push_save_file(f, _cache(tmp_path), client, {}) is False
    assert client.uploads == []
