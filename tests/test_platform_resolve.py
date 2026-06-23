from __future__ import annotations

import pytest

from romhop.platform_resolve import invert_to_slugs, resolve_platform


def test_identity_slug_returned_when_no_override():
    slugs = invert_to_slugs("psx", {})
    assert "psx" in slugs


def test_default_override_inverted():
    # atari-st → atarist in DEFAULT_PLATFORM_OVERRIDES
    slugs = invert_to_slugs("atarist", {})
    assert "atari-st" in slugs


def test_user_override_takes_priority():
    # User maps "myslug" → "atarist", so myslug appears before atari-st.
    slugs = invert_to_slugs("atarist", {"myslug": "atarist"})
    assert slugs[0] == "myslug"
    assert "atari-st" in slugs


def test_identity_always_present():
    # Even when overrides exist, the identity slug is included.
    slugs = invert_to_slugs("snes", {"custom": "snes"})
    assert "snes" in slugs


def test_multiple_slugs_map_same_dir():
    # neogeoaes and neogeomvs both map to neogeo.
    slugs = invert_to_slugs("neogeo", {})
    assert "neogeoaes" in slugs
    assert "neogeomvs" in slugs
    assert "neogeo" in slugs  # identity


def test_resolve_platform_finds_by_slug():
    platforms = [{"id": 10, "slug": "psx", "fs_slug": "psx"}]
    result = resolve_platform("psx", platforms, {})
    assert result is not None
    assert result["id"] == 10


def test_resolve_platform_finds_by_fs_slug():
    platforms = [{"id": 5, "slug": None, "fs_slug": "atari-st"}]
    result = resolve_platform("atarist", platforms, {})
    assert result is not None
    assert result["id"] == 5


def test_resolve_platform_returns_none_when_absent():
    platforms = [{"id": 1, "slug": "snes", "fs_slug": "snes"}]
    result = resolve_platform("psx", platforms, {})
    assert result is None


def test_resolve_platform_user_override_wins():
    # User maps "customslug" → "mydir"; platform list has customslug.
    platforms = [
        {"id": 99, "slug": "customslug", "fs_slug": "customslug"},
        {"id": 1, "slug": "mydir", "fs_slug": "mydir"},
    ]
    result = resolve_platform("mydir", platforms, {"customslug": "mydir"})
    assert result is not None
    assert result["id"] == 99  # user override slug matched first


def test_resolve_platform_identity_fallback():
    # System dir "genesis" — not in DEFAULT_PLATFORM_OVERRIDES → identity slug used.
    platforms = [{"id": 7, "slug": "genesis", "fs_slug": "genesis"}]
    result = resolve_platform("genesis", platforms, {})
    assert result is not None
    assert result["id"] == 7
