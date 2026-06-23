from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from romhop.activity import ActivityEvent, ActivityKind
from romhop.local_index import LocalGame
from romhop.mapping_cache import MappingCache, seed_entry
from romhop.romm_client import RomAlreadyExists, RommClient, ScanConnectError, UploadCancelled

_log = logging.getLogger(__name__)

# ES-DE layout artifacts — never upload these.
_ARTIFACT_SUFFIXES = frozenset({".m3u", ".txt"})


def _is_real_rom_file(fname: str) -> bool:
    return Path(fname).suffix.lower() not in _ARTIFACT_SUFFIXES


def _file_path(game: LocalGame, roms_root: Path, fname: str) -> Path:
    """Resolve a game file's on-disk path.

    Flat games: roms_root/system/fname.
    Subfolder games: roms_root/system/game_name/fname.
    Try flat first; fall back to subfolder if the flat path doesn't exist.
    """
    flat = roms_root / game.system / fname
    if flat.exists():
        return flat
    return roms_root / game.system / game.game_name / fname


@dataclass
class UploadResult:
    game_name: str
    system: str
    uploaded_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)  # already-existed on RomM
    seeded: bool = False
    pending_metadata: bool = False
    fallback: bool = False  # scan connect failed; basic mapping entry seeded


def upload_game(
    game: LocalGame,
    client: RommClient,
    platform_id: int,
    platform_slug: str,
    roms_root: Path,
    cache: MappingCache,
    scan_timeout: float = 120.0,
    stop_event: threading.Event | None = None,
    progress_fn: Callable[[str, int], None] | None = None,
    on_event: Callable[[ActivityEvent], None] | None = None,
) -> UploadResult:
    """Upload all real rom files for a LocalGame to RomM, then trigger a scan.

    Flow:
    1. Upload each real file (skip .m3u/.txt; dedup signal = skip, not error).
    2. If any file was uploaded: trigger a Socket.IO quick scan (or fall back).
    3. Find the new rom(s) by fs_name after the scan.
    4. Seed the mapping cache so saves sync immediately.
    5. Emit an Activity event.

    Raises UploadCancelled if stop_event fires during upload.
    """
    result = UploadResult(game_name=game.game_name, system=game.system)

    real_files = [f for f in game.file_names if _is_real_rom_file(f)]
    if not real_files:
        _emit(on_event, ActivityKind.ERROR,
              f"Upload skipped: {game.game_name} — no real rom files found")
        return result

    # --- 1. Upload files ---
    for fname in real_files:
        if stop_event and stop_event.is_set():
            raise UploadCancelled(game.game_name)
        fpath = _file_path(game, roms_root, fname)
        if not fpath.exists():
            _log.warning("upload_game: file not found: %s", fpath)
            continue
        bytes_uploaded = 0

        def _progress(chunk_bytes: int) -> None:
            nonlocal bytes_uploaded
            bytes_uploaded += chunk_bytes
            if progress_fn:
                progress_fn(fname, bytes_uploaded)

        try:
            client.upload_rom(
                platform_id=platform_id,
                file_path=fpath,
                file_name=fname,
                stop_event=stop_event,
                progress_fn=_progress,
            )
            result.uploaded_files.append(fname)
            _log.debug("upload_game: uploaded %s", fname)
        except RomAlreadyExists:
            result.skipped_files.append(fname)
            _log.debug("upload_game: already exists %s", fname)
        except UploadCancelled:
            raise
        except Exception as exc:
            _log.warning("upload_game: upload failed for %s: %s", fname, exc)
            raise

    if not result.uploaded_files:
        # All files already existed → report as skipped, not error.
        _emit(on_event, ActivityKind.UPLOAD_DONE,
              f"Already in RomM: {game.game_name} ({len(result.skipped_files)} file(s))")
        return result

    # --- 2. Trigger scan ---
    scan_ok = False
    if scan_timeout > 0:
        try:
            client.trigger_scan(platform_id, timeout=scan_timeout)
            scan_ok = True
        except ScanConnectError as exc:
            _log.warning("upload_game: socket connect failed (%s) — using fallback", exc)
            result.fallback = True
        except Exception as exc:
            _log.warning("upload_game: scan failed (%s) — using fallback", exc)
            result.fallback = True
    else:
        result.fallback = True

    # --- 3. Find materialized roms ---
    fs_names = set(result.uploaded_files)
    found_roms = []
    if scan_ok:
        try:
            found_roms = client.find_roms_by_fs_names(platform_slug, fs_names)
        except Exception as exc:
            _log.warning("upload_game: find_roms_by_fs_names failed: %s", exc)

    # --- 4. Seed mapping cache ---
    if found_roms:
        for rom in found_roms:
            entry = seed_entry(rom.id, game.system, rom.fs_name_no_ext, game.file_names)
            cache.add(entry)
        cache.save()
        result.seeded = True
        result.pending_metadata = all(
            not getattr(r, "is_identified", True) for r in found_roms
        )
    elif result.fallback or not scan_ok:
        # Fallback: seed a basic entry keyed by game_name so saves can still sync.
        from romhop.mapping_cache import RomEntry
        from romhop.library import candidate_basenames
        fake_entry = RomEntry(
            rom_id=0,
            system=game.system,
            game_name=game.game_name,
            candidate_basenames=candidate_basenames(game.game_name, game.file_names),
        )
        cache.add(fake_entry)
        cache.save()
        result.seeded = True

    # --- 5. Emit activity ---
    n_up = len(result.uploaded_files)
    n_sk = len(result.skipped_files)
    if result.fallback:
        msg = (f"Uploaded {game.game_name} ({n_up} file(s)) — "
               "run a Scan in RomM to finish importing")
    else:
        msg = f"Uploaded {game.game_name} ({n_up} file(s))"
        if n_sk:
            msg += f", {n_sk} already existed"
    _emit(on_event, ActivityKind.UPLOAD_DONE, msg)
    return result


def _emit(
    on_event: Callable[[ActivityEvent], None] | None,
    kind: ActivityKind,
    message: str,
) -> None:
    if on_event is not None:
        on_event(ActivityEvent(kind=kind, message=message))
