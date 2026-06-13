from emusync.platform_map import esde_system_for_slug


def test_identity_when_no_override():
    assert esde_system_for_slug("psx", {}) == "psx"


def test_override_wins():
    assert esde_system_for_slug("genesis-slug", {"genesis-slug": "genesis"}) == "genesis"
