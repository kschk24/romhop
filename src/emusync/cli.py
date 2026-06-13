from __future__ import annotations

from pathlib import Path

import httpx
import typer

from emusync import config
from emusync.download import download_rom
from emusync.mapping_cache import MappingCache
from emusync.romm_client import Rom, RommClient
from emusync.sync import watch_and_push

app = typer.Typer(help="Sync a RomM library with a local ES-DE/RetroArch setup.")


def _select_match(name: str, matches: list[Rom]) -> Rom:
    """Pick the rom to download. Prefer an exact (case-insensitive) name match;
    otherwise refuse to guess and list the candidates so the user can be specific."""
    if len(matches) == 1:
        return matches[0]
    exact = [r for r in matches if r.name.lower() == name.lower()]
    if len(exact) == 1:
        return exact[0]
    typer.echo(f"{len(matches)} games match '{name}'. Be more specific (or use the exact name):", err=True)
    for r in matches:
        typer.echo(f"  {r.name}", err=True)
    raise typer.Exit(code=2)


def _client() -> RommClient:
    settings = config.load_settings()
    token = config.get_token()
    if not settings.romm_url or not token:
        typer.echo("Not logged in. Run: emusync login --url <url> --token <rmm_...>", err=True)
        raise typer.Exit(code=1)
    return RommClient(base_url=settings.romm_url, token=token)


def _cache_path() -> Path:
    import platformdirs
    return Path(platformdirs.user_data_dir("emusync")) / "mapping_cache.json"


@app.command()
def login(url: str = typer.Option(..., "--url"),
          token: str = typer.Option(..., "--token")):
    """Store the RomM URL and API token."""
    config.set_token(token)           # store token first; if keyring fails, no partial state
    settings = config.load_settings()
    settings.romm_url = url
    config.save_settings(settings)
    typer.echo(f"Saved RomM URL {url} and token.")


@app.command()
def download(name: str = typer.Argument(..., help="Game name (substring match)")):
    """Download the first matching game into the ES-DE layout."""
    settings = config.load_settings()
    client = _client()
    matches = [r for r in client.list_roms(search_term=name) if name.lower() in r.name.lower()]
    if not matches:
        typer.echo(f"No game matching '{name}'.", err=True)
        raise typer.Exit(code=1)
    rom = _select_match(name, matches)
    cache = MappingCache(_cache_path())
    try:
        m3u = download_rom(rom, client, roms_root=settings.roms_root, cache=cache,
                           overrides=settings.platform_overrides)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            typer.echo(
                f"RomM has no downloadable files for '{rom.name}' (id {rom.id}). "
                "It looks unmatched/unscanned on the server — try a rescan in RomM.",
                err=True,
            )
        else:
            typer.echo(f"Download failed for '{rom.name}': HTTP {exc.response.status_code}", err=True)
        raise typer.Exit(code=1)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach RomM: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Downloaded {rom.name} -> {m3u}")


@app.command()
def sync():
    """Watch RetroArch saves/states and push changes to RomM."""
    settings = config.load_settings()
    client = _client()
    cache = MappingCache(_cache_path())
    typer.echo("Watching for save changes (Ctrl-C to stop)...")
    watch_and_push(
        [settings.saves_dir, settings.states_dir], cache, client,
        on_event=lambda p: typer.echo(f"Pushed {p.name}"),
        debounce_seconds=settings.sync_delay_seconds,
    )


if __name__ == "__main__":
    app()
