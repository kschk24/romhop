from __future__ import annotations


def esde_system_for_slug(slug: str, overrides: dict[str, str]) -> str:
    """Return the ES-DE system directory name for a RomM platform slug.

    Defaults to identity (RomM slugs match ES-DE dir names for most systems);
    an override entry takes precedence for the exceptions.
    """
    return overrides.get(slug, slug)
