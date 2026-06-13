from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


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

    def find_by_basename(self, basename: str) -> RomEntry | None:
        for entry in self._entries:
            if basename in entry.candidate_basenames:
                return entry
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
