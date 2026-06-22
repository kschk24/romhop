from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from watchfiles import watch

logger = logging.getLogger(__name__)

from romhop.activity import ActivityEvent, ActivityKind
from romhop.mapping_cache import MappingCache
from romhop.platform_map import system_for_core

SAVE_EXTS = {".srm", ".sav"}
# RetroArch savestate slots: ".state" plus an arbitrary slot index (".state1",
# ".state10", ".state995", ...). Match any digits, not a fixed 0-9 set.
_STATE_RE = re.compile(r"\.state\d*$", re.IGNORECASE)


def is_state_file(name: str) -> bool:
    """True if a file name is a RetroArch savestate (any slot index)."""
    return _STATE_RE.search(name) is not None


def is_watched_file(name: str) -> bool:
    return Path(name).suffix.lower() in SAVE_EXTS or is_state_file(name)


def _digest(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def push_save_file(path: Path, cache: MappingCache, client,
                   seen: dict[str, str], *, core_overrides: dict[str, str] | None = None,
                   on_ambiguous=None) -> bool:
    """Match a save file to a rom and upload it. Returns True if uploaded.

    `seen` maps file path -> last-uploaded content digest, to skip no-op writes.
    The parent directory name is the RetroArch core (RomM `emulator`); it is also
    used to recover the save's platform when a basename collides across systems.
    """
    if not is_watched_file(path.name):
        return False
    core = path.parent.name
    candidates = cache.candidates_for(path.stem)
    if not candidates:
        return False
    if len(candidates) == 1:
        entry = candidates[0]
    else:
        system = system_for_core(core, core_overrides or {})
        scoped = [c for c in candidates if system is not None and c.system == system]
        if len(scoped) == 1:
            entry = scoped[0]
        else:
            if on_ambiguous is not None:
                on_ambiguous(path, candidates)
            return False
    try:
        data = path.read_bytes()
    except OSError:
        # File vanished/locked between detection and read; skip this event.
        return False
    digest = _digest(data)
    if seen.get(str(path)) == digest:
        return False
    # Route by extension: savestates go to /api/states, save files to /api/saves.
    # Mixing them up puts states in RomM's saves list (and vice versa).
    upload = client.upload_state if is_state_file(path.name) else client.upload_save
    upload(rom_id=entry.rom_id, emulator=core, file_name=path.name, data=data)
    seen[str(path)] = digest
    logger.debug("sync pushed: %s (rom_id=%d)", path.name, entry.rom_id)
    return True


def watch_and_push(dirs: list[Path], cache: MappingCache, client,
                   on_event=None, debounce_seconds: float = 8.0,
                   core_overrides: dict[str, str] | None = None,
                   on_ambiguous=None, stop_event=None) -> None:
    """Watch save/state dirs and push changed files. Blocks.

    `debounce_seconds` is user-configurable (Settings.sync_delay_seconds); watchfiles
    coalesces writes within this window so we upload once the file settles.
    `stop_event` (a threading.Event) lets a caller cancel the watch — watchfiles
    polls it and returns when set, which is how the GUI toggles sync off.
    """
    seen: dict[str, str] = {}
    existing = [str(d) for d in dirs if d.exists()]
    if not existing:
        logger.info("sync: no watchable dirs exist, exiting")
        return
    logger.info("sync watching: %s", existing)
    for changes in watch(*existing, debounce=int(debounce_seconds * 1000),
                         stop_event=stop_event):
        for _change, raw_path in changes:
            logger.debug("sync event: %s", raw_path)
            path = Path(raw_path)
            if path.is_file() and push_save_file(
                path, cache, client, seen,
                core_overrides=core_overrides, on_ambiguous=on_ambiguous,
            ):
                if on_event:
                    on_event(ActivityEvent(ActivityKind.SYNC_PUSH, f"Synced {path.name}"))
