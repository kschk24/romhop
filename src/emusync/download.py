from __future__ import annotations

import io
import zipfile
from pathlib import Path

from emusync.library import (
    candidate_basenames,
    write_game,
    write_single_file,
)
from emusync.mapping_cache import MappingCache, RomEntry
from emusync.platform_map import esde_system_for_slug
from emusync.romm_client import Rom

# Rom files that are themselves archives — a zip payload IS the rom, not a server bundle.
ARCHIVE_EXTS = {".zip", ".7z"}


def _zip_to_files(payload: bytes) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # flatten any internal folders; ES-DE layout is our concern
            files[Path(info.filename).name] = zf.read(info)
    return files


def _is_multi_disc(rom: Rom, payload: bytes) -> bool:
    """Decide whether a download is a multi-file/disc bundle (subfolder + .m3u) or a
    single flat rom. RomM returns a zip bundle for multi-part roms and the raw file
    otherwise — but a single-file rom can itself be a .zip, so an archive rom is never
    treated as a bundle."""
    ext = Path(rom.fs_name).suffix.lower()
    if rom.has_multiple_files or ext == ".m3u":
        return True
    if ext in ARCHIVE_EXTS:
        return False  # the rom is its own archive; keep it flat
    return payload[:2] == b"PK"  # a zip bundle for a non-archive rom = disc set


def download_rom(rom: Rom, client, *, roms_root: Path, cache: MappingCache,
                 overrides: dict[str, str], is_multi_file: bool | None = None) -> Path:
    """Download a rom into the ES-DE layout and record a cache entry.

    Single-file roms are written flat into <system>/; multi-disc roms get a
    subfolder + .m3u + noload.txt. Returns the path written (the file or the .m3u).
    """
    payload = client.download_rom_content(rom.id, rom.fs_name)

    if is_multi_file is None:
        is_multi_file = _is_multi_disc(rom, payload)

    system = esde_system_for_slug(rom.platform_slug, overrides)
    game_name = rom.fs_name_no_ext

    if is_multi_file:
        # Bundle zip: drop RomM's own .m3u / noload.txt — write_game rebuilds them.
        files = {
            name: data
            for name, data in _zip_to_files(payload).items()
            if not name.lower().endswith(".m3u") and name != "noload.txt"
        }
        written = write_game(roms_root, system, game_name, files)
        cache_files = list(files)
    else:
        files = {rom.fs_name: payload}
        written = write_single_file(roms_root, system, rom.fs_name, payload)
        cache_files = [rom.fs_name]

    cache.add(RomEntry(
        rom_id=rom.id,
        system=system,
        game_name=game_name,
        candidate_basenames=candidate_basenames(game_name, cache_files),
    ))
    cache.save()
    return written
