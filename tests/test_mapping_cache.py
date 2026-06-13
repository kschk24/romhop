from emusync.mapping_cache import MappingCache, RomEntry


def test_add_lookup_persist(tmp_path):
    path = tmp_path / "cache.json"
    cache = MappingCache(path)
    cache.add(RomEntry(
        rom_id=18,
        system="psx",
        game_name="Metal Gear Solid (USA)",
        candidate_basenames={"Metal Gear Solid (USA)", "Metal Gear Solid (USA) (Disc 1)"},
    ))
    cache.save()

    reloaded = MappingCache(path)
    entry = reloaded.find_by_basename("Metal Gear Solid (USA)")
    assert entry is not None
    assert entry.rom_id == 18
    assert entry.system == "psx"


def test_unknown_basename_returns_none(tmp_path):
    cache = MappingCache(tmp_path / "cache.json")
    assert cache.find_by_basename("Nope") is None
