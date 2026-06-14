from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

import platformdirs

# Default token palette. Every token a theme may set has a default here, so a
# partial theme never leaves an unsubstituted {{placeholder}} in the QSS.
DEFAULT_TOKENS: dict[str, str] = {
    "bg": "#1e1f22",
    "panel": "#2b2d31",
    "accent": "#5865f2",
    "text": "#e6e6e6",
    "text_dim": "#9a9a9a",
    "font_family": "sans-serif",
    "font_size": "13px",
    # Filled in at load time with the theme's assets dir (see load_theme).
    "assets": "",
}


def render_qss(base_qss: str, tokens: dict[str, str]) -> str:
    """Substitute {{token}} placeholders in base_qss.

    Theme tokens override defaults; any token the theme omits uses its default,
    guaranteeing no raw placeholder survives.
    """
    merged = {**DEFAULT_TOKENS, **tokens}
    out = base_qss
    for key, value in merged.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


@dataclass
class LoadedTheme:
    name: str
    qss: str
    assets_dir: Path | None


def _gui_themes_root() -> Path:
    return Path(__file__).parent / "themes"


def base_qss() -> str:
    return (_gui_themes_root() / "base.qss").read_text()


def bundled_default_dir() -> Path:
    return _gui_themes_root() / "default"


def themes_dir() -> Path:
    """User-installed themes live here (created on demand)."""
    d = Path(platformdirs.user_config_dir("romhop")) / "themes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render_dir(path: Path) -> LoadedTheme:
    """Render a theme directory. Raises on any malformed input."""
    manifest = json.loads((path / "manifest.json").read_text())
    name = manifest["name"]
    tokens = json.loads((path / "tokens.json").read_text())
    assets_dir = path / "assets" if (path / "assets").is_dir() else None
    tokens = dict(tokens)
    tokens["assets"] = str(assets_dir) if assets_dir else ""
    qss = render_qss(base_qss(), tokens)
    override = path / "theme.qss"
    if override.exists():
        qss = qss + "\n" + override.read_text()
    return LoadedTheme(name=name, qss=qss, assets_dir=assets_dir)


def load_theme_dir(path: Path) -> LoadedTheme:
    """Load a theme directory, falling back to the default if it is broken."""
    try:
        return _render_dir(path)
    except Exception:
        return _render_dir(bundled_default_dir())


def load_active_theme(name: str) -> LoadedTheme:
    """Resolve a theme by name: user themes dir first, then bundled default."""
    if name and name != "default":
        candidate = themes_dir() / name
        if candidate.is_dir():
            return load_theme_dir(candidate)
    return _render_dir(bundled_default_dir())


def install_theme(zip_path: Path) -> str:
    """Extract a .romhop-theme zip into the themes dir. Returns its name."""
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("manifest.json") as fh:
            name = json.loads(fh.read())["name"]
        dest = themes_dir() / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        zf.extractall(dest)
    return name
