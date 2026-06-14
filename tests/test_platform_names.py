from romhop.platform_names import PlatformNames, display_name
from romhop.romm_client import Rom


def _rom(slug, platform_name=None):
    return Rom(id=1, name="G", platform_slug=slug, fs_name="G",
               fs_name_no_ext="G", file_names=[], platform_name=platform_name)


def test_name_for_falls_back_to_slug(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    assert names.name_for("gb") == "gb"


def test_update_from_roms_persists_and_reloads(tmp_path):
    path = tmp_path / "p.json"
    names = PlatformNames(path)
    names.update_from_roms([_rom("gb", "Game Boy"), _rom("snes", "Super Nintendo")])
    assert names.name_for("gb") == "Game Boy"
    assert PlatformNames(path).name_for("snes") == "Super Nintendo"


def test_update_from_roms_ignores_missing_names(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    names.update_from_roms([_rom("gba", None)])
    assert names.name_for("gba") == "gba"


def test_display_name_prefers_rom_then_cache_then_slug(tmp_path):
    names = PlatformNames(tmp_path / "p.json")
    names.update_from_roms([_rom("gb", "Game Boy")])
    assert display_name(_rom("gb", "GB Color"), names) == "GB Color"
    assert display_name(_rom("gb", None), names) == "Game Boy"
    assert display_name(_rom("xyz", None), names) == "xyz"
    assert display_name(_rom("gb", None)) == "gb"
