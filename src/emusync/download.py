from __future__ import annotations

import io
import zipfile
from pathlib import Path

from emusync.library import candidate_basenames, write_game
from emusync.mapping_cache import MappingCache, RomEntry
from emusync.platform_map import esde_system_for_slug
from emusync.romm_client import Rom


def _zip_to_files(payload: bytes) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # flatten any internal folders; ES-DE layout is our concern
            files[Path(info.filename).name] = zf.read(info)
    return files


def download_rom(rom: Rom, client, *, roms_root: Path, cache: MappingCache,
                 overrides: dict[str, str], is_multi_file: bool | None = None) -> Path:
    """Download a rom into the ES-DE tree and record a cache entry."""
    if is_multi_file is None:
        is_multi_file = len(rom.file_names) > 1

    out_name = f"{rom.fs_name_no_ext}.zip" if is_multi_file else rom.fs_name
    payload = client.download_rom_content(rom.id, out_name)

    if is_multi_file:
        files = _zip_to_files(payload)
    else:
        files = {rom.fs_name: payload}

    system = esde_system_for_slug(rom.platform_slug, overrides)
    game_name = rom.fs_name_no_ext
    m3u = write_game(roms_root, system, game_name, files)

    cache.add(RomEntry(
        rom_id=rom.id,
        system=system,
        game_name=game_name,
        candidate_basenames=candidate_basenames(game_name, list(files)),
    ))
    cache.save()
    return m3u
