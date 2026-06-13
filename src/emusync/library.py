from __future__ import annotations

from pathlib import Path

# Disc descriptor extensions: when present, only these go in the .m3u
# (avoids invalid raw .bin track entries — matches RomM's own m3u logic).
DESCRIPTOR_EXTS = {".cue", ".gdi", ".ccd", ".m3u8", ".chd", ".iso", ".pbp"}


def _descriptors(file_names: list[str]) -> list[str]:
    cues = [f for f in file_names if Path(f).suffix.lower() == ".cue"]
    if cues:
        return cues
    descriptors = [f for f in file_names if Path(f).suffix.lower() in DESCRIPTOR_EXTS]
    return descriptors or file_names


def build_m3u(game_name: str, file_names: list[str]) -> str:
    """Build .m3u content: relative <game>/<file> lines, LF, no BOM."""
    lines = [f"{game_name}/{name}" for name in _descriptors(sorted(file_names))]
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
    """Write a game into the ES-DE layout. Returns the .m3u path."""
    system_dir = roms_root / system
    game_dir = system_dir / game_name
    game_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (game_dir / name).write_bytes(data)
    (game_dir / "noload.txt").write_text("")
    m3u_path = system_dir / f"{game_name}.m3u"
    # newline="" keeps our explicit LF; encoding utf-8 has no BOM
    m3u_path.write_text(build_m3u(game_name, list(files)), encoding="utf-8", newline="")
    return m3u_path
