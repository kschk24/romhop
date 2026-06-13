from __future__ import annotations

import hashlib
from pathlib import Path

from watchfiles import watch

from romhop.mapping_cache import MappingCache
from romhop.platform_map import system_for_core

SAVE_EXTS = {".srm", ".sav"}
STATE_EXTS = {".state", ".state1", ".state2", ".state3", ".state4",
              ".state5", ".state6", ".state7", ".state8", ".state9"}
WATCHED_EXTS = SAVE_EXTS | STATE_EXTS


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
    if path.suffix.lower() not in WATCHED_EXTS:
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
    client.upload_save(rom_id=entry.rom_id, emulator=core,
                       file_name=path.name, data=data)
    seen[str(path)] = digest
    return True


def watch_and_push(dirs: list[Path], cache: MappingCache, client,
                   on_event=None, debounce_seconds: float = 8.0,
                   core_overrides: dict[str, str] | None = None,
                   on_ambiguous=None) -> None:
    """Watch save/state dirs and push changed files. Blocks.

    `debounce_seconds` is user-configurable (Settings.sync_delay_seconds); watchfiles
    coalesces writes within this window so we upload once the file settles.
    """
    seen: dict[str, str] = {}
    existing = [str(d) for d in dirs if d.exists()]
    if not existing:
        return
    for changes in watch(*existing, debounce=int(debounce_seconds * 1000)):
        for _change, raw_path in changes:
            path = Path(raw_path)
            if path.is_file() and push_save_file(
                path, cache, client, seen,
                core_overrides=core_overrides, on_ambiguous=on_ambiguous,
            ):
                if on_event:
                    on_event(path)
