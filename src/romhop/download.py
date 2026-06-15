from __future__ import annotations

import io
import os
import time
import zipfile
from pathlib import Path

import httpx

from romhop.library import write_game
from romhop.mapping_cache import MappingCache, seed_entry
from romhop.platform_map import esde_system_for_slug
from romhop.romm_client import Rom

# Rom files that are themselves archives — a zip payload IS the rom, not a server bundle.
ARCHIVE_EXTS = {".zip", ".7z"}


class RateLimiter:
    """Paces a download to a max rate. ``kbps`` is KiB/s; 0 means unlimited.

    ``kbps`` may be an int or a zero-arg callable returning the current KiB/s,
    so the cap can change mid-download (e.g. the GUI's live settings). Call
    ``tick(downloaded_total)`` after each chunk with the cumulative byte count;
    each segment is priced at the cap in effect when it arrived, so a limit
    change throttles the in-flight transfer from the next chunk on. If a segment
    arrived faster than the cap allows it sleeps the shortfall.
    ``now``/``sleep`` are injectable for tests.
    """

    def __init__(self, kbps, *, now=time.monotonic, sleep=time.sleep):
        self._kbps = kbps if callable(kbps) else (lambda value=kbps: value)
        self._now = now
        self._sleep = sleep
        self._last_total = 0
        self._last_time = now()

    def tick(self, downloaded_total: int) -> None:
        delta = downloaded_total - self._last_total
        limit = self._kbps() * 1024  # bytes/sec
        if limit > 0 and delta > 0:
            needed = delta / limit                  # seconds this segment should take
            actual = self._now() - self._last_time
            if needed > actual:
                self._sleep(needed - actual)
        self._last_total = downloaded_total
        self._last_time = self._now()


class DownloadCancelled(Exception):
    """Raised when a download is aborted via stop_event."""


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


def _is_multi_disc_head(rom: Rom, head: bytes) -> bool:
    """Decide whether a download is a multi-file/disc bundle (subfolder + .m3u)
    or a single flat rom, given the first bytes of the payload. RomM returns a
    zip bundle for multi-part roms and the raw file otherwise — but a single-file
    rom can itself be a .zip, so an archive rom is never treated as a bundle."""
    ext = Path(rom.fs_name).suffix.lower()
    if rom.has_multiple_files or ext == ".m3u":
        return True
    if ext in ARCHIVE_EXTS:
        return False  # the rom is its own archive; keep it flat
    return head[:2] == b"PK"  # a zip bundle for a non-archive rom = disc set


def download_rom(rom: Rom, client, *, roms_root: Path, cache: MappingCache,
                 overrides: dict[str, str], is_multi_file: bool | None = None,
                 on_progress=None, stop_event=None, rate_limit_kbps=0) -> Path:
    """Download a rom into the ES-DE layout and record a cache entry.

    Streams the rom to a ``.part`` temp file in the destination platform dir,
    then finalizes: single-file roms are renamed into <system>/; multi-disc
    bundles are extracted into a subfolder + .m3u + noload.txt. Returns the path
    written (the file or the .m3u). ``on_progress(downloaded, total)`` is called
    during the transfer (total may be None). Pass ``stop_event`` to abort
    mid-stream (raises DownloadCancelled) and ``rate_limit_kbps`` to throttle.
    """
    system = esde_system_for_slug(rom.platform_slug, overrides)
    game_name = rom.fs_name_no_ext
    system_dir = roms_root / system
    system_dir.mkdir(parents=True, exist_ok=True)
    part = system_dir / (Path(rom.fs_name).name + ".part")
    limiter = RateLimiter(rate_limit_kbps)

    try:
        downloaded = 0
        with part.open("wb") as f, \
                client.stream_rom_content(rom.id, rom.fs_name) as (total, chunks):
            for chunk in chunks:
                if stop_event is not None and stop_event.is_set():
                    raise DownloadCancelled
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress is not None:
                    on_progress(downloaded, total)
                limiter.tick(downloaded)

        if is_multi_file is None:
            with part.open("rb") as f:
                head = f.read(2)
            is_multi_file = _is_multi_disc_head(rom, head)

        if is_multi_file:
            payload = part.read_bytes()
            files = {
                name: data
                for name, data in _zip_to_files(payload).items()
                if not name.lower().endswith(".m3u") and name != "noload.txt"
            }
            written = write_game(roms_root, system, game_name, files)
            cache_files = list(files)
            part.unlink(missing_ok=True)
        else:
            target = system_dir / Path(rom.fs_name).name
            os.replace(part, target)
            written = target
            cache_files = [rom.fs_name]
    finally:
        part.unlink(missing_ok=True)

    cache.add(seed_entry(rom.id, system, game_name, cache_files))
    cache.save()
    return written
