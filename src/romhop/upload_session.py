from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from romhop.romm_client import RommClient

_log = logging.getLogger(__name__)
_SESSION_FILENAME = "upload_session.json"


@dataclass
class RecoveryInfo:
    was_dirty: bool
    reaped: int  # number of orphan upload_ids cancelled


def _session_path() -> Path:
    from romhop.config import user_data_dir
    return user_data_dir() / _SESSION_FILENAME


def _load() -> dict:
    try:
        return json.loads(_session_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def set_in_progress() -> None:
    """Mark a batch as started; clears any leftover active_uploads list."""
    _save({"in_progress": True, "active_uploads": []})


def add_upload(upload_id: str, platform_id: int, file_name: str) -> None:
    """Record a new in-flight upload_id (called right after /start)."""
    data = _load()
    uploads = data.get("active_uploads", [])
    uploads.append({"upload_id": upload_id, "platform_id": platform_id, "file_name": file_name})
    data["active_uploads"] = uploads
    data["in_progress"] = True
    _save(data)


def remove_upload(upload_id: str) -> None:
    """Remove a completed/cancelled upload_id (called after /complete or graceful cancel)."""
    data = _load()
    uploads = [u for u in data.get("active_uploads", []) if u.get("upload_id") != upload_id]
    data["active_uploads"] = uploads
    _save(data)


def clear() -> None:
    """Delete the session file (called on clean batch finish)."""
    try:
        _session_path().unlink()
    except FileNotFoundError:
        pass


def recover(client: RommClient) -> RecoveryInfo:
    """Cancel orphan upload_ids and report the dirty flag. Idempotent.

    POST .../cancel for each leftover upload_id; tolerates 404/already-expired
    sessions (server may TTL-expire them). Clears the session file regardless.

    Known limitation: concurrent CLI + GUI writers = last-writer-wins on the
    session file; worst case a live upload_id gets cancelled here. Accepted —
    vanishingly rare, degrades only to re-scan/re-upload.
    """
    data = _load()
    was_dirty = bool(data.get("in_progress", False))
    active_uploads = data.get("active_uploads", [])
    reaped = 0
    for entry in active_uploads:
        uid = entry.get("upload_id")
        if not uid:
            continue
        try:
            client._cancel_upload(uid)
            reaped += 1
            _log.debug("recover: reaped orphan upload_id=%s", uid)
        except Exception as exc:
            _log.debug("recover: cancel %s failed (already expired?): %s", uid, exc)
    clear()
    return RecoveryInfo(was_dirty=was_dirty, reaped=reaped)
