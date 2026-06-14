import json
import zipfile
from pathlib import Path

from romhop.gui import theme


def test_render_qss_substitutes_known_tokens():
    base = "QWidget { background: {{bg}}; color: {{text}}; }"
    out = theme.render_qss(base, {"bg": "#101010", "text": "#eaeaea"})
    assert out == "QWidget { background: #101010; color: #eaeaea; }"


def test_render_qss_fills_missing_tokens_from_defaults():
    # A token not provided by the theme must fall back to a default, never
    # leave a raw {{placeholder}} in the output.
    base = "QWidget { color: {{text}}; border: 1px solid {{accent}}; }"
    out = theme.render_qss(base, {"text": "#fff"})
    assert "{{" not in out
    assert theme.DEFAULT_TOKENS["accent"] in out


def test_render_qss_caller_overrides_default():
    # A caller-supplied token must win over the default for the same key.
    out = theme.render_qss("{{bg}}", {"bg": "#custom"})
    assert out == "#custom"


def test_load_theme_dir_renders_with_tokens(tmp_path):
    tdir = tmp_path / "midnight"
    tdir.mkdir()
    (tdir / "manifest.json").write_text(json.dumps({"name": "midnight"}))
    (tdir / "tokens.json").write_text(json.dumps({"bg": "#000000"}))
    loaded = theme.load_theme_dir(tdir)
    assert loaded.name == "midnight"
    assert "#000000" in loaded.qss
    assert "{{" not in loaded.qss


def test_load_theme_dir_appends_optional_theme_qss(tmp_path):
    tdir = tmp_path / "withoverride"
    tdir.mkdir()
    (tdir / "manifest.json").write_text(json.dumps({"name": "withoverride"}))
    (tdir / "tokens.json").write_text(json.dumps({}))
    (tdir / "theme.qss").write_text("QLabel { font-weight: bold; }")
    loaded = theme.load_theme_dir(tdir)
    assert "font-weight: bold" in loaded.qss


def test_load_theme_dir_falls_back_on_broken_theme(tmp_path):
    tdir = tmp_path / "broken"
    tdir.mkdir()
    (tdir / "tokens.json").write_text("{ this is not valid json")
    loaded = theme.load_theme_dir(tdir)
    # Degrades to the bundled default rather than raising.
    assert loaded.name == "default"
    assert "{{" not in loaded.qss


def test_install_theme_extracts_zip(tmp_path, monkeypatch):
    dest = tmp_path / "themes"
    monkeypatch.setattr(theme, "themes_dir", lambda: dest)
    src = tmp_path / "neon.romhop-theme"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"name": "neon"}))
        zf.writestr("tokens.json", json.dumps({"accent": "#39ff14"}))
    name = theme.install_theme(src)
    assert name == "neon"
    assert (dest / "neon" / "tokens.json").exists()
