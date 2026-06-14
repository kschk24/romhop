from __future__ import annotations

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
