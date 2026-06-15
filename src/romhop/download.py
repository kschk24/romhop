from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import httpx

from romhop.library import (
    write_game,
    write_single_file,
)
from romhop.mapping_cache import MappingCache, seed_entry
from romhop.platform_map import esde_system_for_slug
from romhop.romm_client import Rom

# Rom files that are themselves archives — a zip payload IS the rom, not a server bundle.
ARCHIVE_EXTS = {".zip", ".7z"}


class RateLimiter:
    """Paces a download to a max rate. ``kbps`` is KiB/s; 0 means unlimited.

    Call ``tick(downloaded_total)`` after each chunk with the cumulative byte
    count. If the transfer is ahead of the allowed schedule it sleeps the
    difference. ``now``/``sleep`` are injectable for tests.
    """

    def __init__(self, kbps: int, *, now=time.monotonic, sleep=time.sleep):
        self._limit = kbps * 1024  # bytes/sec
        self._now = now
        self._sleep = sleep
        # Anchor the schedule at construction (download start), so elapsed time
        # is measured from the real beginning rather than the first chunk.
        self._start = now()

    def tick(self, downloaded_total: int) -> None:
        if self._limit <= 0:
            return
        target = downloaded_total / self._limit          # ideal elapsed seconds
        elapsed = self._now() - self._start
        behind = target - elapsed
        if behind > 0:
            self._sleep(behind)


def friendly_download_error(rom_name: str, rom_id: int, exc: Exception) -> str:
    """User-facing message for a failed rom download.

    A bare ``404`` from ``/api/roms/<id>/content`` means RomM has the rom's
    metadata but no actual file to serve (unscanned / missing on the server) —
    the common cause behind a raw "No files found for ROM <id>". Map that, and
    auth failures, to actionable text; fall back to ``str(exc)`` otherwise.
    Mirrors the CLI's ``_exit_http`` wording so both frontends agree.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return (f"RomM rejected the request ({code}). The API token is invalid "
                    "or lacks scope — re-run login/setup with a valid token.")
        if code == 404:
            return (f"RomM has no downloadable files for '{rom_name}' (id {rom_id}). "
                    "It looks unscanned/missing on the server — try a rescan in RomM.")
        return f"RomM returned HTTP {code}."
    if isinstance(exc, httpx.HTTPError):
        return f"Could not reach RomM: {exc}"
    return str(exc)


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
                 overrides: dict[str, str], is_multi_file: bool | None = None,
                 on_progress=None) -> Path:
    """Download a rom into the ES-DE layout and record a cache entry.

    Single-file roms are written flat into <system>/; multi-disc roms get a
    subfolder + .m3u + noload.txt. Returns the path written (the file or the .m3u).
    `on_progress(downloaded, total)` is called during the transfer (total may be None).
    """
    payload = client.download_rom_content(rom.id, rom.fs_name, on_progress=on_progress)

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

    cache.add(seed_entry(rom.id, system, game_name, cache_files))
    cache.save()
    return written
