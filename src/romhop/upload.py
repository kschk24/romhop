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
from romhop import upload_session as _sess

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
    chunk_size: int | None = None,
    stop_event: threading.Event | None = None,
    progress_fn: Callable[[str, int, int], None] | None = None,
    on_event: Callable[[ActivityEvent], None] | None = None,
    on_session_start: Callable[[str], None] | None = None,
    on_session_end: Callable[[str], None] | None = None,
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

    # Resolve every file's path once, then sum sizes so progress can report a
    # determinate "bytes sent / total" across the whole game (not per file).
    paths = {fname: _file_path(game, roms_root, fname) for fname in real_files}
    total_bytes = sum(p.stat().st_size for p in paths.values() if p.exists())
    game_sent = 0  # cumulative across all of this game's files

    # --- 1. Upload files ---
    for fname in real_files:
        if stop_event and stop_event.is_set():
            raise UploadCancelled(game.game_name)
        fpath = paths[fname]
        if not fpath.exists():
            _log.warning("upload_game: file not found: %s", fpath)
            continue

        def _progress(chunk_bytes: int, _fname: str = fname) -> None:
            nonlocal game_sent
            game_sent += chunk_bytes
            if progress_fn:
                progress_fn(_fname, game_sent, total_bytes)

        try:
            upload_kwargs = {} if chunk_size is None else {"chunk_size": chunk_size}
            client.upload_rom(
                platform_id=platform_id,
                file_path=fpath,
                file_name=fname,
                stop_event=stop_event,
                progress_fn=_progress,
                on_session_start=on_session_start,
                on_session_end=on_session_end,
                **upload_kwargs,
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


def run_upload_batch(
    jobs: list[tuple[LocalGame, int, str]],
    client: RommClient,
    roms_root: Path,
    cache: MappingCache,
    *,
    scan_timeout: float = 120.0,
    chunk_size: int | None = None,
    stop_event: threading.Event | None = None,
    on_item_started: Callable[[int, int, str], None] | None = None,
    progress_factory: Callable[[], Callable] | None = None,
    on_item_error: Callable[[str, str], None] | None = None,
    on_event: Callable[[ActivityEvent], None] | None = None,
) -> bool:
    """Upload a batch of games to RomM with crash-safe session tracking.

    Calls upload_session.set_in_progress() at batch start and clear() on a
    clean finish. Each file's upload_id is bracketed (add/remove) via the
    on_session_start/on_session_end callbacks so a hard kill leaves reapable
    orphans that recover() can cancel at next startup.

    Returns True if the batch completed without cancellation.
    """
    _sess.set_in_progress()
    n = len(jobs)
    cancelled = False

    try:
        for i, (game, platform_id, platform_slug) in enumerate(jobs, 1):
            if stop_event and stop_event.is_set():
                cancelled = True
                break
            if on_item_started:
                on_item_started(i, n, game.game_name)
            progress_fn = progress_factory() if progress_factory else None

            def _on_sess_start(uid: str, _pid: int = platform_id) -> None:
                _sess.add_upload(uid, _pid, "")

            def _on_sess_end(uid: str) -> None:
                _sess.remove_upload(uid)

            try:
                upload_game(
                    game, client,
                    platform_id=platform_id,
                    platform_slug=platform_slug,
                    roms_root=roms_root,
                    cache=cache,
                    scan_timeout=scan_timeout,
                    chunk_size=chunk_size,
                    stop_event=stop_event,
                    progress_fn=progress_fn,
                    on_event=on_event,
                    on_session_start=_on_sess_start,
                    on_session_end=_on_sess_end,
                )
            except UploadCancelled:
                cancelled = True
                break
            except Exception as exc:
                if on_item_error:
                    on_item_error(game.game_name, str(exc))
                _emit(on_event, ActivityKind.ERROR, str(exc))
    finally:
        if not cancelled:
            _sess.clear()

    return not cancelled


def _emit(
    on_event: Callable[[ActivityEvent], None] | None,
    kind: ActivityKind,
    message: str,
) -> None:
    if on_event is not None:
        on_event(ActivityEvent(kind=kind, message=message))
