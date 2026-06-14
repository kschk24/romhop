from romhop.mapping_cache import MappingCache, RomEntry, seed_entry


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


def test_seed_entry_builds_candidate_basenames():
    entry = seed_entry(rom_id=7, system="genesis", game_name="Sonic (USA)",
                       file_names=["Sonic (USA).md"])
    assert entry.rom_id == 7
    assert entry.system == "genesis"
    assert "Sonic (USA)" in entry.candidate_basenames
    assert "Sonic (USA).md" in entry.candidate_basenames


def test_find_by_basename_normalizes_whitespace_and_case(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic (USA)",
                       candidate_basenames={"Sonic (USA)"}))
    assert cache.find_by_basename("sonic  (usa)").rom_id == 1


def test_candidates_for_returns_all_matches(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    cache.add(RomEntry(rom_id=2, system="snes", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    assert {e.rom_id for e in cache.candidates_for("Sonic")} == {1, 2}


def test_find_by_basename_disambiguates_by_system(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    cache.add(RomEntry(rom_id=2, system="snes", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    assert cache.find_by_basename("Sonic", system="snes").rom_id == 2
    # ambiguous without a system hint
    assert cache.find_by_basename("Sonic") is None


def test_entries_returns_all(tmp_path):
    cache = MappingCache(tmp_path / "c.json")
    cache.add(RomEntry(rom_id=1, system="genesis", game_name="Sonic",
                       candidate_basenames={"Sonic"}))
    cache.add(RomEntry(rom_id=2, system="snes", game_name="Mario",
                       candidate_basenames={"Mario"}))
    assert {e.rom_id for e in cache.entries()} == {1, 2}
