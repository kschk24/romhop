from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

import keyring
import platformdirs

KEYRING_SERVICE = "emusync"
KEYRING_USER = "api_token"


@dataclass
class Settings:
    romm_url: str
    roms_root: Path
    saves_dir: Path
    states_dir: Path
    platform_overrides: dict[str, str] = field(default_factory=dict)
    sync_delay_seconds: float = 8.0


def settings_path() -> Path:
    return Path(platformdirs.user_config_dir("emusync")) / "settings.json"


def default_settings() -> Settings:
    if sys.platform.startswith("win"):
        import os
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        ra = appdata / "RetroArch"
        return Settings(
            romm_url="",
            roms_root=Path.home() / "Games" / "Emulation",
            saves_dir=ra / "saves",
            states_dir=ra / "states",
        )
    return Settings(
        romm_url="",
        roms_root=Path.home() / "Games" / "Emulation",
        saves_dir=Path.home() / ".config" / "retroarch" / "saves",
        states_dir=Path.home() / ".config" / "retroarch" / "states",
    )


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(settings)
    for key in ("roms_root", "saves_dir", "states_dir"):
        data[key] = str(data[key])
    path.write_text(json.dumps(data, indent=2))


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
        sync_delay_seconds=data.get("sync_delay_seconds", 8.0),
    )


def set_token(token: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
