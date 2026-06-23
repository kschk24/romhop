from __future__ import annotations

from romhop.platform_map import DEFAULT_PLATFORM_OVERRIDES


def invert_to_slugs(system: str, overrides: dict[str, str]) -> list[str]:
    """Return candidate RomM/IGDB slugs that map to an ES-DE system directory.

    Checks user overrides first, then DEFAULT_PLATFORM_OVERRIDES, then the
    identity mapping (system dir name == slug). Preserves order so callers can
    prefer the first slug for platform creation.
    """
    seen: set[str] = set()
    slugs: list[str] = []

    def _add(slug: str) -> None:
        if slug not in seen:
            seen.add(slug)
            slugs.append(slug)

    for slug, esde_dir in overrides.items():
        if esde_dir == system:
            _add(slug)
    for slug, esde_dir in DEFAULT_PLATFORM_OVERRIDES.items():
        if esde_dir == system:
            _add(slug)
    _add(system)  # identity: system dir name == RomM slug for most platforms
    return slugs


def resolve_platform(
    system: str,
    romm_platforms: list[dict],
    overrides: dict[str, str],
) -> dict | None:
    """Find the RomM platform dict for an ES-DE system dir, or None if absent.

    Tries each candidate slug in priority order (user override > default >
    identity) against both ``fs_slug`` and ``slug`` fields of every platform.
    Returns the first match, or None when the platform doesn't exist in RomM.
    """
    for slug in invert_to_slugs(system, overrides):
        for p in romm_platforms:
            if p.get("fs_slug") == slug or p.get("slug") == slug:
                return p
    return None
