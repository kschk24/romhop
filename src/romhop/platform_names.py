from __future__ import annotations

import json
from pathlib import Path

from romhop.romm_client import Rom


class PlatformNames:
    """Persisted RomM platform `slug -> display name` map.

    Harvested from rom payloads on every fetch (so it stays current) and read
    back with a slug fallback, so platform labels survive offline and are
    identical in the GUI and the CLI.
    """

    def __init__(self, path: Path):
        self.path = path
        self._names: dict[str, str] = {}
        if path.exists():
            self._names = json.loads(path.read_text())

    def update_from_roms(self, roms: list[Rom]) -> None:
        changed = False
        for rom in roms:
            name = getattr(rom, "platform_name", None)
            if name and self._names.get(rom.platform_slug) != name:
                self._names[rom.platform_slug] = name
                changed = True
        if changed:
            self.save()

    def name_for(self, slug: str) -> str:
        return self._names.get(slug, slug)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._names, indent=2, sort_keys=True))


def display_name(rom: Rom, names: PlatformNames | None = None) -> str:
    """Platform label for a rom: its own name, else the cache, else the slug."""
    if getattr(rom, "platform_name", None):
        return rom.platform_name
    if names is not None:
        return names.name_for(rom.platform_slug)
    return rom.platform_slug
