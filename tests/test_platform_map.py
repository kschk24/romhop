from romhop.platform_map import esde_system_for_slug, system_for_core


def test_identity_when_no_override():
    assert esde_system_for_slug("psx", {}) == "psx"


def test_override_wins():
    assert esde_system_for_slug("genesis-slug", {"genesis-slug": "genesis"}) == "genesis"


def test_system_for_known_core():
    assert system_for_core("Snes9x", overrides={}) == "snes"
    assert system_for_core("Genesis Plus GX", overrides={}) == "genesis"


def test_system_for_unknown_core_is_none():
    assert system_for_core("saves", overrides={}) is None
    assert system_for_core("Totally Unknown Core", overrides={}) is None


def test_core_override_takes_precedence():
    assert system_for_core("MyCore", overrides={"MyCore": "n64"}) == "n64"
    # override also wins over a built-in
    assert system_for_core("Snes9x", overrides={"Snes9x": "sfc"}) == "sfc"
