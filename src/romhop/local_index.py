from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from romhop.library import candidate_basenames, norm
from romhop.platform_map import esde_system_for_slug
from romhop.romm_client import Rom

_log = logging.getLogger(__name__)

_CUE_FILE_RE = re.compile(r'^\s*FILE\s+"([^"]+)"', re.MULTILINE | re.IGNORECASE)


def _parse_cue(path: Path) -> list[str]:
    """Return bare filenames referenced by FILE lines in a .cue sheet."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [Path(m.group(1)).name for m in _CUE_FILE_RE.finditer(text)]


def _parse_m3u(path: Path) -> list[str]:
    """Return non-blank, non-comment lines from an .m3u playlist."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


@dataclass
class LocalGame:
    system: str             # the <system> dir name on disk
    game_name: str          # flat: filename incl ext; subfolder/m3u: the bare name
    file_names: list[str]   # flat: [the one file]; subfolder: the disc files inside
    match_key: str          # norm() of the value matched against the rom


def index_local_library(roms_root: Path, overrides: dict[str, str],
                         system: str | None = None) -> list[LocalGame]:
    """Walk the ES-DE tree and return one LocalGame per game.

    Layout mirrors download writes: a flat file in <system>/ is one game; a
    <system>/<game>/ subfolder (usually paired with a sibling <game>.m3u) is one
    multi-disc game whose disc files become its candidate basenames.

    `overrides` is accepted for call-site parity with match_to_roms (callers pass
    settings.platform_overrides to both); the local system is just the dir name,
    so platform overrides are applied on the rom side during matching.

    `system` limits the walk to a single ``roms_root/<system>`` dir. download's
    already-local check filters to one system anyway, so scoping the walk avoids
    a full-tree scan on every download (TASK-009).
    """
    games: list[LocalGame] = []
    if not roms_root.is_dir():
        return games
    if system is not None:
        one = roms_root / system
        system_dirs = [one] if one.is_dir() else []
    else:
        system_dirs = sorted(p for p in roms_root.iterdir() if p.is_dir())
    for system_dir in system_dirs:
        system = system_dir.name
        subfolder_names: set[str] = set()
        # Multi-disc games: each subfolder is one game.
        for sub in sorted(p for p in system_dir.iterdir() if p.is_dir()):
            subfolder_names.add(sub.name)
            file_names = sorted(
                f.name for f in sub.iterdir()
                if f.is_file() and f.suffix.lower() != ".txt"
            )
            games.append(LocalGame(
                system=system,
                game_name=sub.name,
                file_names=file_names,
                match_key=norm(sub.name),
            ))
        # Flat files directly in <system>/: collect first, then process in passes
        # to coalesce .cue+.bin and .m3u+.cue+.bin into single LocalGames.
        flat_files: dict[str, Path] = {}  # filename → path
        for f in sorted(p for p in system_dir.iterdir() if p.is_file()):
            if f.suffix.lower() != ".txt":
                flat_files[f.name] = f

        suppressed: set[str] = set()  # filenames absorbed into a coalesced LocalGame

        # Pass 1: .m3u files — either pair with a subfolder (suppress) or parse
        # as an orphan multi-disc descriptor that references flat .cue files.
        for fname, fpath in sorted(flat_files.items()):
            if fpath.suffix.lower() != ".m3u":
                continue
            if fpath.stem in subfolder_names:
                suppressed.add(fname)  # already emitted as part of the subfolder game
                continue
            disc_refs = _parse_m3u(fpath)
            file_names_out: list[str] = []
            for disc_ref in disc_refs:
                disc_name = Path(disc_ref).name
                if disc_name not in flat_files:
                    _log.warning("local_index: %s references missing file %r", fpath, disc_ref)
                    continue
                disc_path = flat_files[disc_name]
                suppressed.add(disc_name)
                if disc_path.suffix.lower() == ".cue":
                    file_names_out.append(disc_name)
                    for track_ref in _parse_cue(disc_path):
                        track_name = Path(track_ref).name
                        if track_name not in flat_files:
                            _log.warning("local_index: %s references missing file %r",
                                         disc_path, track_ref)
                            continue
                        file_names_out.append(track_name)
                        suppressed.add(track_name)
                else:
                    file_names_out.append(disc_name)
            suppressed.add(fname)  # .m3u is an ES-DE artifact, not a real rom file
            games.append(LocalGame(
                system=system,
                game_name=fpath.stem,
                file_names=sorted(set(file_names_out)),
                match_key=norm(fpath.stem),
            ))

        # Pass 2: remaining .cue files (single-disc flat layout: .cue + .bin tracks).
        for fname, fpath in sorted(flat_files.items()):
            if fpath.suffix.lower() != ".cue" or fname in suppressed:
                continue
            file_names_out = [fname]
            suppressed.add(fname)
            for track_ref in _parse_cue(fpath):
                track_name = Path(track_ref).name
                if track_name not in flat_files:
                    _log.warning("local_index: %s references missing file %r", fpath, track_ref)
                    continue
                file_names_out.append(track_name)
                suppressed.add(track_name)
            games.append(LocalGame(
                system=system,
                game_name=fpath.stem,
                file_names=sorted(set(file_names_out)),
                match_key=norm(fpath.stem),
            ))

        # Pass 3: all remaining flat files (cartridges, .chd, etc.).
        for fname, fpath in sorted(flat_files.items()):
            if fname in suppressed:
                continue
            games.append(LocalGame(
                system=system,
                game_name=fname,
                file_names=[fname],
                match_key=norm(fname),
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


def downloaded_rom_ids(roms: list[Rom], roms_root: Path,
                       overrides: dict[str, str]) -> set[int]:
    """Ids of roms already present in the local ES-DE tree.

    Walks the library once and matches each rom by its platform-scoped,
    normalized filename keys — the same match `download`/`scan` use, generalized
    to the whole rom set.
    """
    by_system: dict[str, set[str]] = defaultdict(set)
    for game in index_local_library(roms_root, overrides):
        by_system[game.system].add(game.match_key)
    ids: set[int] = set()
    for rom in roms:
        system = esde_system_for_slug(rom.platform_slug, overrides)
        keys = by_system.get(system, set())
        if norm(rom.fs_name) in keys or norm(rom.fs_name_no_ext) in keys:
            ids.add(rom.id)
    return ids
