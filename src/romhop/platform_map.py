from __future__ import annotations


def esde_system_for_slug(slug: str, overrides: dict[str, str]) -> str:
    """Return the ES-DE system directory name for a RomM platform slug.

    Defaults to identity (RomM slugs match ES-DE dir names for most systems);
    an override entry takes precedence for the exceptions.
    """
    return overrides.get(slug, slug)


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
