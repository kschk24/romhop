from romhop.platform_map import esde_system_for_slug, system_for_core


def test_identity_when_no_override():
    assert esde_system_for_slug("psx", {}) == "psx"


def test_override_wins():
    assert esde_system_for_slug("genesis-slug", {"genesis-slug": "genesis"}) == "genesis"


def test_builtin_default_slug_mismatch():
    # RomM/IGDB slugs that differ from the ES-DE system dir name are corrected
    # out of the box (no user override needed), fixing both scan match + download
    # placement.
    assert esde_system_for_slug("atari-st", {}) == "atarist"
    assert esde_system_for_slug("ngc", {}) == "gc"
    assert esde_system_for_slug("3ds", {}) == "n3ds"
    assert esde_system_for_slug("dc", {}) == "dreamcast"
    assert esde_system_for_slug("sms", {}) == "mastersystem"
    assert esde_system_for_slug("sfam", {}) == "sfc"


def test_user_override_beats_builtin_default():
    assert esde_system_for_slug("atari-st", {"atari-st": "custom"}) == "custom"


def test_unknown_slug_still_identity():
    assert esde_system_for_slug("totally-unknown", {}) == "totally-unknown"


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
