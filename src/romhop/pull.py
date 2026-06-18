from __future__ import annotations

import glob
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

from romhop.sync import is_state_file


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


def pull_games(client, entries, settings, *, take_remote: bool = False,
               on_conflict=None, on_written=None, on_error=None) -> dict:
    """Download saves+states for each entry and write them locally.

    For each remote file: write when no local file exists; skip when bytes are
    identical; on a differing local file take remote if `take_remote` or the
    `on_conflict(item, local_path, local_mtime)` callback returns True, else keep
    local. `on_written(path)` is called for each file written; `on_error(path,
    exc)` for each file that fails to write (the run continues). Returns a summary
    dict with counts: written / skipped / kept / failed.
    """
    summary = {"written": 0, "skipped": 0, "kept": 0, "failed": 0}
    fetchers = (
        ("save", client.list_saves, client.download_save_content),
        ("state", client.list_states, client.download_state_content),
    )
    for entry in entries:
        for _source, lister, downloader in fetchers:
            for remote in lister(entry.rom_id):
                try:
                    data = downloader(remote["id"])
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 404:
                        raise
                    # Orphan row: RomM lists it but content blob is gone.
                    summary["failed"] += 1
                    if on_error is not None:
                        on_error(Path(remote["file_name"]), exc)
                    continue
                file_name = remote["file_name"]
                # Route by extension, not by endpoint: a .state* name must land in
                # states_dir even if it came back from /api/saves (legacy uploads
                # before sync routed states to /api/states landed there).
                kind = "state" if is_state_file(file_name) else "save"
                item = PullItem(
                    kind=kind, rom_id=entry.rom_id,
                    file_name=file_name,
                    emulator=remote.get("emulator"),
                    remote_updated=remote.get("updated_at"),
                    data=data,
                )
                target = resolve_target(
                    item, settings.saves_dir, settings.states_dir,
                    settings.sort_saves_by_core, settings.sort_states_by_core)
                if target.exists():
                    if target.read_bytes() == data:
                        summary["skipped"] += 1
                        continue
                    if not take_remote:
                        local_mtime = datetime.fromtimestamp(target.stat().st_mtime)
                        if on_conflict is None or not on_conflict(item, target, local_mtime):
                            logger.info("pull conflict kept local: %s", target)
                            summary["kept"] += 1
                            continue
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                except OSError as exc:
                    # One unwritable file shouldn't abort the whole run.
                    summary["failed"] += 1
                    if on_error is not None:
                        on_error(target, exc)
                    continue
                summary["written"] += 1
                if on_written is not None:
                    on_written(target)
    return summary
