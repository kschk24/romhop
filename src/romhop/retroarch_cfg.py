from __future__ import annotations

from pathlib import Path

_SAVE_KEYS = ("savefile_directory", "savestate_directory")


def _resolve(value: str | None, cfg_path: Path) -> Path | None:
    """Turn a cfg value into a Path, or None when it means 'no fixed folder'."""
    if value is None:
        return None
    value = value.strip().strip('"')
    if value == "" or value.lower() == "default":
        return None
    if value.startswith(":"):
        # ':' = the directory holding retroarch.cfg. The rest may use \ or /.
        rel = value[1:].replace("\\", "/").lstrip("/")
        return cfg_path.parent.joinpath(*rel.split("/")) if rel else cfg_path.parent
    return Path(value).expanduser()


def parse_save_dirs(cfg_path: Path) -> tuple[Path | None, Path | None]:
    """Return (savefile_dir, savestate_dir) from a retroarch.cfg.

    Each slot is None when its key is absent, empty, or 'default'. Missing or
    unreadable file -> (None, None).
    """
    try:
        text = cfg_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return (None, None)
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if key in _SAVE_KEYS:
            values[key] = raw  # last assignment wins
    return (
        _resolve(values.get("savefile_directory"), cfg_path),
        _resolve(values.get("savestate_directory"), cfg_path),
    )
