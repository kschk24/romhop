from __future__ import annotations


# RomM/IGDB platform slug -> ES-DE system dir, for the systems where the two
# conventions disagree. Without these, esde_system_for_slug returns the slug
# verbatim, so download writes to a folder ES-DE never reads (e.g. atari-st/
# instead of atarist/) and scan keys the rom under the wrong system, leaving the
# real local game unmatched. A user override (config set-platform) still wins.
#
# Built by joining RomM's IGDB_PLATFORM_LIST slugs (romm backend) to ES-DE's
# es_systems list by platform name; every target below is a real ES-DE system
# dir. Slugs that already equal their ES-DE dir (gb, gba, n64, nes, snes, psx,
# ps2, msx2, ...) need no entry. Two RomM slugs merge platforms ES-DE splits
# (genesis-slash-megadrive, turbografx-16-slash-pc-engine-cd) and are left out --
# pick a side with `config set-platform`.
DEFAULT_PLATFORM_OVERRIDES: dict[str, str] = {
    "3ds": "n3ds",
    "64dd": "n64dd",
    "acorn-archimedes": "archimedes",
    "acorn-electron": "electron",
    "acpc": "amstradcpc",
    "amiga-cd32": "amigacd32",
    "amstrad-gx4000": "gx4000",
    "apple-iigs": "apple2gs",
    "appleii": "apple2",
    "astrocade": "astrocde",
    "atari-jaguar-cd": "atarijaguarcd",
    "atari-st": "atarist",
    "c-plus-4": "plus4",
    "commodore-cdtv": "cdtv",
    "dc": "dreamcast",
    "dragon-32-slash-64": "dragon32",
    "epoch-super-cassette-vision": "scv",
    "fairchild-channel-f": "channelf",
    "fm-7": "fm7",
    "fm-towns": "fmtowns",
    "g-and-w": "gameandwatch",
    "handheld-electronic-lcd": "lcdgames",
    "jaguar": "atarijaguar",
    "lynx": "atarilynx",
    "mega-duck-slash-cougar-boy": "megaduck",
    "neo-geo-cd": "neogeocd",
    "neo-geo-pocket": "ngp",
    "neo-geo-pocket-color": "ngpc",
    "neogeoaes": "neogeo",
    "neogeomvs": "neogeo",
    "ngc": "gc",
    "palm-os": "palm",
    "pc-8800-series": "pc88",
    "pc-9800-series": "pc98",
    "pc-fx": "pcfx",
    "philips-cd-i": "cdimono1",
    "pokemon-mini": "pokemini",
    "sega-cd": "segacd",
    "sega32": "sega32x",
    "sfam": "sfc",
    "sg1000": "sg-1000",
    "sharp-x68000": "x68000",
    "sinclair-zx81": "zx81",
    "sms": "mastersystem",
    "super-acan": "supracan",
    "ti-99": "ti99",
    "turbografx16--1": "tg16",
    "vic-20": "vic20",
    "watara-slash-quickshot-supervision": "supervision",
    "win": "windows",
    "wonderswan-color": "wonderswancolor",
    "zxs": "zxspectrum",
}


def esde_system_for_slug(slug: str, overrides: dict[str, str]) -> str:
    """Return the ES-DE system directory name for a RomM platform slug.

    Precedence: user override > built-in default correction > identity (RomM
    slugs match ES-DE dir names for most systems).
    """
    if slug in overrides:
        return overrides[slug]
    return DEFAULT_PLATFORM_OVERRIDES.get(slug, slug)


# RetroArch core folder name -> ES-DE system dir. Used to disambiguate a save's
# platform when its basename collides across systems. Extend via `config set-core`.
CORE_TO_SYSTEM: dict[str, str] = {
    "Snes9x": "snes",
    "Genesis Plus GX": "genesis",
    "Nestopia": "nes",
    "mGBA": "gba",
    "PCSX-ReARMed": "psx",
    "Beetle PSX HW": "psx",
    "Mupen64Plus-Next": "n64",
    "Mednafen PCE": "pcengine",
    "Sega - Saturn (Beetle Saturn)": "saturn",
    "Beetle Saturn": "saturn",
}


def system_for_core(core: str, overrides: dict[str, str]) -> str | None:
    """Map a RetroArch core folder name to an ES-DE system dir, or None if unknown.

    A user override (config set-core) takes precedence over the built-in table.
    """
    if core in overrides:
        return overrides[core]
    return CORE_TO_SYSTEM.get(core)
