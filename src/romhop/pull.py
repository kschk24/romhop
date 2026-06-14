from __future__ import annotations

import glob
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PullItem:
    kind: str                    # "save" or "state"
    rom_id: int
    file_name: str
    emulator: str | None
    remote_updated: str | None
    data: bytes


def _find_existing(base: Path, file_name: str) -> Path | None:
    """First file named file_name anywhere under base, or None."""
    if not base.is_dir():
        return None
    # Escape glob metacharacters — ROM/save names use [..] dump tags that rglob
    # would otherwise treat as a character class and fail to match.
    for p in base.rglob(glob.escape(file_name)):
        if p.is_file():
            return p
    return None


def resolve_target(item: PullItem, saves_dir: Path, states_dir: Path,
                   sort_saves_by_core: bool, sort_states_by_core: bool) -> Path:
    """Local path to write this item to.

    An existing file of the same name (anywhere under the dir) wins, preserving
    the user's layout. Otherwise place by RetroArch's per-core sort flag: into a
    <core> subfolder when sorting is on and the emulator/core is known, else flat.
    """
    base = saves_dir if item.kind == "save" else states_dir
    sort = sort_saves_by_core if item.kind == "save" else sort_states_by_core
    existing = _find_existing(base, item.file_name)
    if existing is not None:
        return existing
    if sort and item.emulator:
        return base / item.emulator / item.file_name
    return base / item.file_name
