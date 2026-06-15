from __future__ import annotations


def run_scan(client, cache, names, settings):
    """Match local ROMs to RomM roms and seed the save-sync mapping cache.

    Qt-free core sharing cli._run_scan's shape (minus echo/confirm): list the
    server's roms, refresh the platform-name cache, index the local library,
    match, then seed one cache entry per match and persist. Returns the
    MatchResult so the caller can report matched/unmatched/collisions.
    """
    from romhop.local_index import index_local_library, match_to_roms
    from romhop.mapping_cache import seed_entry
    from romhop.platform_map import esde_system_for_slug

    roms = client.list_roms()
    names.update_from_roms(roms)
    locals_ = index_local_library(settings.roms_root, settings.platform_overrides)
    result = match_to_roms(locals_, roms, settings.platform_overrides)
    for local, rom in result.matched:
        system = esde_system_for_slug(rom.platform_slug, settings.platform_overrides)
        cache.add(seed_entry(rom.id, system, rom.fs_name_no_ext, local.file_names))
    cache.save()
    return result
