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
