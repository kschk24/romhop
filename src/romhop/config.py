from __future__ import annotations

import configparser
import sys
from dataclasses import dataclass, field
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


_TRUE_TOKENS = {"true", "1", "yes", "on"}


def coerce_value(type_: str, raw: str):
    """Turn a string from the ini into a typed Python value.

    Raises ValueError on a malformed int/float (callers fall back to the
    default in that case). Booleans are permissive and never raise.
    """
    if type_ == "str":
        return raw
    if type_ == "path":
        return Path(raw)
    if type_ == "int":
        return int(raw)
    if type_ == "float":
        return float(raw)
    if type_ == "bool":
        return raw.strip().lower() in _TRUE_TOKENS
    raise ValueError(f"unknown field type: {type_}")


def settings_path() -> Path:
    return Path(platformdirs.user_config_dir("romhop")) / "settings.ini"


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


def is_configured(settings: Settings) -> bool:
    """True when the RomM connection is usable: a URL is set and a token is in
    the keyring. Drives whether the GUI auto-launches the setup wizard."""
    return bool(settings.romm_url) and bool(get_token())


_OVERRIDE_SECTIONS = (
    ("platform_overrides", "platform_overrides"),
    ("core_overrides", "core_overrides"),
)


def format_ini(settings: Settings) -> str:
    """Render Settings as commented ini text (configparser can't write the
    comments, so build the text by hand; configparser reads it back fine)."""
    lines: list[str] = []
    for category in CATEGORY_ORDER:
        lines.append(f"[{category}]")
        for spec in SCHEMA:
            if spec.category != category:
                continue
            value = getattr(settings, spec.key)
            if spec.type == "bool":
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            lines.append(f"# {spec.help}")
            lines.append(f"{spec.key} = {rendered}")
        lines.append("")  # blank line between sections
    for attr, section in _OVERRIDE_SECTIONS:
        lines.append(f"[{section}]")
        for key, val in getattr(settings, attr).items():
            lines.append(f"{key} = {val}")
        lines.append("")
    return "\n".join(lines)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_ini(settings))


def _new_parser() -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.optionxform = str  # preserve key case (override keys are arbitrary)
    return cp


def _load_legacy_json(json_path: Path) -> Settings:
    """Parse the pre-ini settings.json into a Settings, overlaying onto the
    real per-OS defaults so a partial/old file keeps sensible fallbacks."""
    import json

    data = json.loads(json_path.read_text())
    settings = default_settings()
    for spec in SCHEMA:
        if spec.key in data:
            value = data[spec.key]
            # JSON already holds typed scalars; only paths need wrapping.
            setattr(settings, spec.key,
                    Path(value) if spec.type == "path" else value)
    for attr, _section in _OVERRIDE_SECTIONS:
        if isinstance(data.get(attr), dict):
            setattr(settings, attr, dict(data[attr]))
    return settings


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        # One-time migration: the storage format changed from settings.json to
        # settings.ini. Without this, upgrading users silently lose their RomM
        # connection (empty url -> no games). Adopt the old file and rewrite it
        # as an ini so the next launch is native.
        legacy = path.with_name("settings.json")
        if legacy.exists():
            try:
                settings = _load_legacy_json(legacy)
            except (ValueError, OSError):
                return default_settings()
            try:
                save_settings(settings, path)
            except OSError:
                pass  # migration is best-effort; still return the loaded values
            return settings
        return default_settings()
    cp = _new_parser()
    try:
        cp.read_string(path.read_text())
    except (configparser.Error, OSError):
        return default_settings()

    settings = default_settings()
    for spec in SCHEMA:
        if not cp.has_option(spec.category, spec.key):
            continue
        raw = cp.get(spec.category, spec.key)
        try:
            setattr(settings, spec.key, coerce_value(spec.type, raw))
        except ValueError:
            pass  # malformed value -> keep the default already in place
    for attr, section in _OVERRIDE_SECTIONS:
        if cp.has_section(section):
            setattr(settings, attr, dict(cp.items(section)))
    return settings


def set_token(token: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
