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


def test_push_resolves_collision_by_core_system(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    cache.add(RomEntry(rom_id=2, system="snes", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    core_dir = tmp_path / "Snes9x"   # known core -> snes
    core_dir.mkdir()
    save = core_dir / "Sonic.srm"
    save.write_bytes(b"S")
    client = RecordingClient()
    pushed = push_save_file(save, cache, client, {}, core_overrides={})
    assert pushed is True
    assert client.uploads == [(2, "Snes9x", "Sonic.srm", b"S")]


def test_push_warns_and_skips_on_unresolved_collision(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    cache.add(RomEntry(rom_id=2, system="snes", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    core_dir = tmp_path / "saves"    # unknown core -> system None
    core_dir.mkdir()
    save = core_dir / "Sonic.srm"
    save.write_bytes(b"S")
    client = RecordingClient()
    warned = []
    pushed = push_save_file(save, cache, client, {}, core_overrides={},
                            on_ambiguous=lambda p, c: warned.append(p))
    assert pushed is False
    assert client.uploads == []
    assert warned == [save]


def test_watch_and_push_returns_when_stop_event_preset(tmp_path):
    # A stop_event already set must make the watcher return promptly instead of
    # blocking forever (this is what lets the GUI toggle sync off).
    import threading

    from romhop.sync import watch_and_push

    saves = tmp_path / "saves"
    states = tmp_path / "states"
    saves.mkdir()
    states.mkdir()
    stop = threading.Event()
    stop.set()

    done = threading.Event()

    def run():
        watch_and_push([saves, states], _cache(tmp_path), object(),
                       debounce_seconds=0.05, stop_event=stop)
        done.set()

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=5)
    assert done.is_set(), "watch_and_push did not honor a preset stop_event"
