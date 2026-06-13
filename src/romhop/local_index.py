from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from romhop.library import NOLOAD_SENTINEL, candidate_basenames, norm
from romhop.platform_map import esde_system_for_slug
from romhop.romm_client import Rom


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


@dataclass
class Collision:
    basename: str          # normalized save basename shared by 2+ matched roms
    rom_ids: list[int]


@dataclass
class MatchResult:
    matched: list[tuple[LocalGame, Rom]] = field(default_factory=list)
    unmatched: list[LocalGame] = field(default_factory=list)
    collisions: list[Collision] = field(default_factory=list)


def match_to_roms(local_games: list[LocalGame], roms: list[Rom],
                  overrides: dict[str, str]) -> MatchResult:
    """Pair each LocalGame to a Rom by exact, normalized, platform-scoped key.

    A rom is registered under (system, norm(fs_name)) and (system, norm(fs_name_no_ext)).
    A local game matches only when exactly one rom sits at (its system, its match_key).
    """
    by_key: dict[tuple[str, str], list[Rom]] = defaultdict(list)
    for rom in roms:
        system = esde_system_for_slug(rom.platform_slug, overrides)
        for value in (rom.fs_name, rom.fs_name_no_ext):
            roms_at = by_key[(system, norm(value))]
            if rom not in roms_at:
                roms_at.append(rom)

    result = MatchResult()
    for local in local_games:
        candidates = by_key.get((local.system, local.match_key), [])
        if len(candidates) == 1:
            result.matched.append((local, candidates[0]))
        else:
            result.unmatched.append(local)

    # Collisions: a save basename shared by 2+ matched roms (sync keys on basename
    # across all entries, then disambiguates by system).
    basename_to_roms: dict[str, set[int]] = defaultdict(set)
    for local, rom in result.matched:
        for b in candidate_basenames(rom.fs_name_no_ext, local.file_names):
            basename_to_roms[norm(b)].add(rom.id)
    for basename, ids in sorted(basename_to_roms.items()):
        if len(ids) > 1:
            result.collisions.append(Collision(basename=basename, rom_ids=sorted(ids)))

    return result
