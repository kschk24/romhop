from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from romhop.library import NOLOAD_SENTINEL, norm


@dataclass
class LocalGame:
    system: str             # the <system> dir name on disk
    game_name: str          # flat: filename incl ext; subfolder/m3u: the bare name
    file_names: list[str]   # flat: [the one file]; subfolder: the disc files inside
    match_key: str          # norm() of the value matched against the rom


def index_local_library(roms_root: Path, overrides: dict[str, str]) -> list[LocalGame]:
    """Walk the ES-DE tree and return one LocalGame per game.

    Layout mirrors download writes: a flat file in <system>/ is one game; a
    <system>/<game>/ subfolder (usually paired with a sibling <game>.m3u) is one
    multi-disc game whose disc files become its candidate basenames.

    `overrides` is accepted for call-site parity with match_to_roms (callers pass
    settings.platform_overrides to both); the local system is just the dir name,
    so platform overrides are applied on the rom side during matching.
    """
    games: list[LocalGame] = []
    if not roms_root.is_dir():
        return games
    for system_dir in sorted(p for p in roms_root.iterdir() if p.is_dir()):
        system = system_dir.name
        subfolder_names: set[str] = set()
        # Multi-disc games: each subfolder is one game.
        for sub in sorted(p for p in system_dir.iterdir() if p.is_dir()):
            subfolder_names.add(sub.name)
            file_names = sorted(
                f.name for f in sub.iterdir()
                if f.is_file() and f.name != NOLOAD_SENTINEL
            )
            games.append(LocalGame(
                system=system,
                game_name=sub.name,
                file_names=file_names,
                match_key=norm(sub.name),
            ))
        # Flat files + orphan .m3u files directly in <system>/.
        for f in sorted(p for p in system_dir.iterdir() if p.is_file()):
            if f.suffix.lower() == ".m3u":
                # Pairs with a subfolder we already emitted; only emit if orphaned.
                if f.stem not in subfolder_names:
                    games.append(LocalGame(
                        system=system,
                        game_name=f.stem,
                        file_names=[],
                        match_key=norm(f.stem),
                    ))
                continue
            games.append(LocalGame(
                system=system,
                game_name=f.name,
                file_names=[f.name],
                match_key=norm(f.name),
            ))
    return games
