from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from romhop.library import candidate_basenames, norm


@dataclass
class RomEntry:
    rom_id: int
    system: str
    game_name: str
    candidate_basenames: set[str] = field(default_factory=set)


class MappingCache:
    def __init__(self, path: Path):
        self.path = path
        self._entries: list[RomEntry] = []
        if path.exists():
            raw = json.loads(path.read_text())
            for e in raw:
                self._entries.append(RomEntry(
                    rom_id=e["rom_id"],
                    system=e["system"],
                    game_name=e["game_name"],
                    candidate_basenames=set(e["candidate_basenames"]),
                ))

    def add(self, entry: RomEntry) -> None:
        self._entries = [e for e in self._entries if e.rom_id != entry.rom_id]
        self._entries.append(entry)

    def candidates_for(self, basename: str) -> list[RomEntry]:
        """All entries whose candidate basenames include this one (normalized)."""
        key = norm(basename)
        return [e for e in self._entries
                if any(norm(b) == key for b in e.candidate_basenames)]

    def find_by_basename(self, basename: str, system: str | None = None) -> RomEntry | None:
        """Resolve a save basename to one entry, or None if absent or ambiguous.

        When several entries share the basename (cross-platform collision), a
        matching `system` is used to disambiguate; without it, returns None.
        """
        candidates = self.candidates_for(basename)
        if len(candidates) == 1:
            return candidates[0]
        if system is not None:
            scoped = [e for e in candidates if e.system == system]
            if len(scoped) == 1:
                return scoped[0]
        return None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "rom_id": e.rom_id,
                "system": e.system,
                "game_name": e.game_name,
                "candidate_basenames": sorted(e.candidate_basenames),
            }
            for e in self._entries
        ]
        self.path.write_text(json.dumps(data, indent=2))


def seed_entry(rom_id: int, system: str, game_name: str,
               file_names: list[str]) -> RomEntry:
    """Build a RomEntry for the cache. Shared by download and scan so both
    produce identical entries."""
    return RomEntry(
        rom_id=rom_id,
        system=system,
        game_name=game_name,
        candidate_basenames=candidate_basenames(game_name, file_names),
    )
