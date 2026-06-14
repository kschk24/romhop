from __future__ import annotations

from pathlib import Path

import platformdirs

from romhop.romm_client import Rom


def cache_dir() -> Path:
    d = Path(platformdirs.user_cache_dir("romhop")) / "covers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_cover(rom: Rom, client) -> Path | None:
    """Return a path to the cached cover image, fetching if needed.

    Returns None when the rom has no cover URL or the fetch fails — callers
    show a text fallback in that case.
    """
    if not rom.url_cover:
        return None
    dest = cache_dir() / f"{rom.id}.img"
    if dest.exists():
        return dest
    try:
        data = client.download_cover(rom.url_cover)
    except Exception:
        return None
    dest.write_bytes(data)
    return dest
