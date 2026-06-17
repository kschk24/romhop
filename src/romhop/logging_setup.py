from __future__ import annotations

import logging
import logging.handlers
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import platformdirs


_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
_BACKUP_COUNT = 5

_configured = False


class RedactionFilter(logging.Filter):
    """Strip sensitive data from every log record before it reaches any handler."""

    def __init__(self, token: str = "", romm_url: str = "") -> None:
        super().__init__()
        self._token = token
        self._home = str(Path.home())
        host = ""
        if romm_url:
            parsed = urlparse(romm_url)
            host = parsed.netloc or parsed.path  # bare host without scheme
        self._host = host

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(str(record.msg))
        record.args = self._redact_args(record.args)
        return True

    def _redact(self, text: str) -> str:
        if self._token and self._token in text:
            text = text.replace(self._token, "***")
        # Also catch "Bearer <token>" patterns
        if self._token:
            text = re.sub(r"Bearer\s+\S+", "Bearer ***", text)
        if "Authorization" in text:
            text = re.sub(r"Authorization['\"]?\s*[:=]\s*['\"]?[^\s,'\"]+", "Authorization: ***", text)
        if self._host and self._host in text:
            text = text.replace(self._host, "<romm-host>")
        if self._home and self._home in text:
            text = text.replace(self._home, "~")
        return text

    def _redact_args(self, args):
        if args is None:
            return args
        if isinstance(args, dict):
            return {k: self._redact(str(v)) if isinstance(v, str) else v for k, v in args.items()}
        if isinstance(args, tuple):
            return tuple(self._redact(str(a)) if isinstance(a, str) else a for a in args)
        return args


def configure_logging(
    *,
    debug: bool = False,
    verbose: bool = False,
    token: str = "",
    romm_url: str = "",
) -> None:
    """Set up rotating file handler (always) + optional stderr handler (-v).

    Safe to call multiple times; reconfigures on subsequent calls so a
    settings change mid-session takes effect.
    """
    log_dir = Path(platformdirs.user_log_dir("romhop"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "romhop.log"

    level = logging.DEBUG if (debug or verbose) else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    redact = RedactionFilter(token=token, romm_url=romm_url)

    # Remove handlers from prior configure_logging calls (settings change).
    for h in list(root.handlers):
        if getattr(h, "_romhop_managed", False):
            root.removeHandler(h)
            h.close()

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    file_handler.addFilter(redact)
    file_handler._romhop_managed = True  # type: ignore[attr-defined]
    root.addHandler(file_handler)

    if verbose:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        stream_handler.addFilter(redact)
        stream_handler._romhop_managed = True  # type: ignore[attr-defined]
        root.addHandler(stream_handler)


def get_log_dir() -> Path:
    return Path(platformdirs.user_log_dir("romhop"))


def export_logs(dest_path: Path) -> None:
    """Zip all current and rotated log files to dest_path."""
    log_dir = get_log_dir()
    log_files = sorted(log_dir.glob("romhop.log*"))
    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in log_files:
            zf.write(f, arcname=f.name)
