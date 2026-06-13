from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

import keyring
import platformdirs

KEYRING_SERVICE = "romhop"
KEYRING_USER = "api_token"


@dataclass
class Settings:
    romm_url: str
    roms_root: Path
    saves_dir: Path
    states_dir: Path
    platform_overrides: dict[str, str] = field(default_factory=dict)
    core_overrides: dict[str, str] = field(default_factory=dict)
    sync_delay_seconds: float = 8.0


def settings_path() -> Path:
    return Path(platformdirs.user_config_dir("romhop")) / "settings.json"


# Sentinel for an unset ROMs root. There is no universal default ROM library
# path (every user's layout differs), so it must be set via `setup`/`config`.
UNSET_PATH = Path("")


def default_settings() -> Settings:
    # saves/states DO have standard per-OS RetroArch defaults; roms_root does not.
    if sys.platform.startswith("win"):
        import os
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        ra = appdata / "RetroArch"
        return Settings(
            romm_url="",
            roms_root=UNSET_PATH,
            saves_dir=ra / "saves",
            states_dir=ra / "states",
        )
    return Settings(
        romm_url="",
        roms_root=UNSET_PATH,
        saves_dir=Path.home() / ".config" / "retroarch" / "saves",
        states_dir=Path.home() / ".config" / "retroarch" / "states",
    )


def roms_root_configured(settings: Settings) -> bool:
    """True if the user has set a real ROMs root (not the unset sentinel)."""
    return str(settings.roms_root) not in ("", ".")


def to_dict(settings: Settings) -> dict:
    """JSON-serialisable view of Settings (Path fields as strings)."""
    data = asdict(settings)
    # Path objects are not JSON-serialisable; convert explicitly.
    for key in ("roms_root", "saves_dir", "states_dir"):
        data[key] = str(data[key])
    return data


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(settings), indent=2))


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return default_settings()
    data = json.loads(path.read_text())
    return Settings(
        romm_url=data["romm_url"],
        roms_root=Path(data["roms_root"]),
        saves_dir=Path(data["saves_dir"]),
        states_dir=Path(data["states_dir"]),
        platform_overrides=data.get("platform_overrides", {}),
        core_overrides=data.get("core_overrides", {}),
        sync_delay_seconds=data.get("sync_delay_seconds", 8.0),
    )


def set_token(token: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
