from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ActivityKind(Enum):
    SYNC_PUSH = "sync_push"
    DOWNLOAD_DONE = "download_done"
    UPLOAD_DONE = "upload_done"
    SETTINGS_SAVED = "settings_saved"
    ERROR = "error"


@dataclass(frozen=True)
class ActivityEvent:
    kind: ActivityKind
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_error(self) -> bool:
        return self.kind is ActivityKind.ERROR
