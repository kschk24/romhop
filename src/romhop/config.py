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
    sort_saves_by_core: bool = False
    sort_states_by_core: bool = False
    sync_delay_seconds: float = 8.0
    sync_enabled: bool = False
    theme: str = "default"
    download_rate_limit_kbps: int = 0  # 0 = unlimited


@dataclass(frozen=True)
class FieldSpec:
    key: str       # Settings attribute name
    category: str  # one of CATEGORY_ORDER
    label: str     # GUI label / never written to the ini
    type: str      # "str" | "path" | "int" | "float" | "bool"
    help: str      # tooltip in GUI; comment above the key in the ini


CATEGORY_ORDER = ["connection", "paths", "behavior"]
CATEGORY_LABELS = {
    "connection": "Connection",
    "paths": "Paths",
    "behavior": "Behavior",
}

# Order within a category is on-screen field order. Defaults are NOT stored
# here: load_settings starts from default_settings() and overlays ini values,
# so the natural fallback for a missing/bad value is the real per-OS default.
SCHEMA: list[FieldSpec] = [
    FieldSpec("romm_url", "connection", "RomM URL", "str",
              "Base URL of your RomM server"),
    FieldSpec("roms_root", "paths", "Rom directory", "path",
              "Local root of your ROM library"),
    FieldSpec("saves_dir", "paths", "Saves directory", "path",
              "Folder RetroArch reads/writes save files in"),
    FieldSpec("states_dir", "paths", "States directory", "path",
              "Folder RetroArch reads/writes save states in"),
    FieldSpec("sort_saves_by_core", "behavior", "Sort saves by core", "bool",
              "Mirror RetroArch's per-core save subfolders"),
    FieldSpec("sort_states_by_core", "behavior", "Sort states by core", "bool",
              "Mirror RetroArch's per-core state subfolders"),
    FieldSpec("sync_enabled", "behavior", "Enable save sync", "bool",
              "Auto-push changed saves to RomM after play"),
    FieldSpec("sync_delay_seconds", "behavior", "Sync delay (seconds)", "float",
              "Debounce window before pushing a changed save"),
    FieldSpec("download_rate_limit_kbps", "behavior",
              "Download limit (KB/s, 0 = unlimited)", "int",
              "Throttle downloads; 0 disables the cap"),
    FieldSpec("theme", "behavior", "Theme", "str", "GUI theme name"),
]


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
        sort_saves_by_core=data.get("sort_saves_by_core", False),
        sort_states_by_core=data.get("sort_states_by_core", False),
        sync_delay_seconds=data.get("sync_delay_seconds", 8.0),
        sync_enabled=data.get("sync_enabled", False),
        theme=data.get("theme", "default"),
        download_rate_limit_kbps=data.get("download_rate_limit_kbps", 0),
    )


def set_token(token: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
