from __future__ import annotations

import hashlib
from pathlib import Path

from watchfiles import watch

from romhop.mapping_cache import MappingCache

SAVE_EXTS = {".srm", ".sav"}
STATE_EXTS = {".state", ".state1", ".state2", ".state3", ".state4",
              ".state5", ".state6", ".state7", ".state8", ".state9"}
WATCHED_EXTS = SAVE_EXTS | STATE_EXTS


def _digest(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def push_save_file(path: Path, cache: MappingCache, client,
                   seen: dict[str, str]) -> bool:
    """Match a save file to a rom and upload it. Returns True if uploaded.

    `seen` maps file path -> last-uploaded content digest, to skip no-op writes.
    The parent directory name is the RetroArch core (RomM `emulator`).
    """
    if path.suffix.lower() not in WATCHED_EXTS:
        return False
    entry = cache.find_by_basename(path.stem)
    if entry is None:
        return False
    try:
        data = path.read_bytes()
    except OSError:
        # File vanished/locked between detection and read; skip this event.
        return False
    digest = _digest(data)
    if seen.get(str(path)) == digest:
        return False
    core = path.parent.name
    client.upload_save(rom_id=entry.rom_id, emulator=core,
                       file_name=path.name, data=data)
    seen[str(path)] = digest
    return True


def watch_and_push(dirs: list[Path], cache: MappingCache, client,
                   on_event=None, debounce_seconds: float = 8.0) -> None:
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
            if path.is_file() and push_save_file(path, cache, client, seen):
                if on_event:
                    on_event(path)
