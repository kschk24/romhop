from __future__ import annotations

import logging
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
    # Require a non-empty file: a zero-byte blob from a truncated prior write
    # would otherwise be served forever and fail to load as an image.
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        data = client.download_cover(rom.url_cover)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Cover fetch failed for rom %s: %s", rom.id, exc
        )
        return None
    dest.write_bytes(data)
    return dest
