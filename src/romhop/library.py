from __future__ import annotations

import re
from pathlib import Path

# Disc descriptor extensions: when present, only these go in the .m3u
# (avoids invalid raw .bin track entries — matches RomM's own m3u logic).
DESCRIPTOR_EXTS = {".cue", ".gdi", ".ccd", ".m3u8", ".chd", ".iso", ".pbp"}
NOLOAD_SENTINEL = "noload.txt"


def norm(s: str) -> str:
	"""Match key: collapse internal whitespace, trim, case-fold. Nothing else —
	so revision/region tags like (Rev 1) / (USA) stay distinct."""
	return " ".join(s.split()).casefold()


def _natural_key(name: str) -> list:
    # Split into digit / non-digit runs so numeric chunks sort numerically.
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _descriptors(file_names: list[str]) -> list[str]:
    cues = [f for f in file_names if Path(f).suffix.lower() == ".cue"]
    if cues:
        return cues
    descriptors = [f for f in file_names if Path(f).suffix.lower() in DESCRIPTOR_EXTS]
    return descriptors or file_names


def build_m3u(game_name: str, file_names: list[str]) -> str:
    """Build .m3u content: relative <game>/<file> lines, LF, no BOM."""
    lines = [f"{game_name}/{name}" for name in _descriptors(sorted(file_names, key=_natural_key))]
    return "".join(line + "\n" for line in lines)


def candidate_basenames(game_name: str, file_names: list[str]) -> set[str]:
    """Every basename RetroArch might name a save after for this game."""
    names = {game_name}
    for f in file_names:
        names.add(f)                 # with extension
        names.add(Path(f).stem)      # without extension
    return names


def write_game(
    roms_root: Path, system: str, game_name: str, files: dict[str, bytes]
) -> Path:
    """Write a game into the ES-DE layout. Returns the .m3u path.

    Raises ValueError if game_name is unsafe as a directory name. File keys are
    reduced to their basename to prevent writes escaping the game folder.
    """
    if not game_name or "/" in game_name or "\\" in game_name or game_name in (".", ".."):
        raise ValueError(f"unsafe game_name for filesystem: {game_name!r}")
    # Reduce every key to a bare filename so a malicious/odd key cannot escape game_dir.
    safe_files = {Path(name).name: data for name, data in files.items()}
    system_dir = roms_root / system
    game_dir = system_dir / game_name
    game_dir.mkdir(parents=True, exist_ok=True)
    for name, data in safe_files.items():
        (game_dir / name).write_bytes(data)
    (game_dir / NOLOAD_SENTINEL).write_text("", encoding="utf-8")
    m3u_path = system_dir / f"{game_name}.m3u"
    # newline="" keeps our explicit LF; encoding utf-8 has no BOM
    m3u_path.write_text(build_m3u(game_name, list(safe_files)), encoding="utf-8", newline="")
    return m3u_path


def write_single_file(roms_root: Path, system: str, file_name: str, data: bytes) -> Path:
    """Write a single-file rom directly into the platform folder (no subfolder/.m3u).

    ES-DE launches cartridge roms (.zip/.gba/.sfc/.md, a lone .chd/.iso) straight from
    <system>/<file>. Returns the written file path. file_name is reduced to its basename.
    """
    safe_name = Path(file_name).name
    if not safe_name or safe_name in (".", ".."):
        raise ValueError(f"unsafe file_name for filesystem: {file_name!r}")
    system_dir = roms_root / system
    system_dir.mkdir(parents=True, exist_ok=True)
    target = system_dir / safe_name
    target.write_bytes(data)
    return target
