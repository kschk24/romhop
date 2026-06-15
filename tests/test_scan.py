from romhop import local_index
from romhop.local_index import LocalGame, MatchResult
from romhop.scan import run_scan


def test_run_scan_seeds_cache_and_returns_result(monkeypatch):
    class FakeRom:
        id = 7
        name = "Sonic"
        platform_slug = "genesis"
        fs_name_no_ext = "Sonic"

    rom = FakeRom()
    local = LocalGame(system="megadrive", game_name="Sonic.md",
                      file_names=["Sonic.md"], match_key="sonic")

    class FakeClient:
        def list_roms(self):
            return [rom]

    class FakeNames:
        def __init__(self):
            self.updated = None
        def update_from_roms(self, roms):
            self.updated = roms

    class FakeCache:
        def __init__(self):
            self.added = []
            self.saved = False
        def add(self, entry):
            self.added.append(entry)
        def save(self):
            self.saved = True

    result = MatchResult(matched=[(local, rom)], unmatched=[], collisions=[])
    monkeypatch.setattr(local_index, "index_local_library",
                        lambda root, ov: [local])
    monkeypatch.setattr(local_index, "match_to_roms",
                        lambda locals_, roms, ov: result)

    from romhop import config
    settings = config.default_settings()
    names = FakeNames()
    cache = FakeCache()

    out = run_scan(FakeClient(), cache, names, settings)

    assert out is result
    assert names.updated == [rom]
    assert len(cache.added) == 1
    assert cache.saved is True
    assert cache.added[0].rom_id == 7
