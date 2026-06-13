from __future__ import annotations

from pathlib import Path

import typer

from emusync import config
from emusync.download import download_rom
from emusync.mapping_cache import MappingCache
from emusync.romm_client import RommClient
from emusync.sync import watch_and_push

app = typer.Typer(help="Sync a RomM library with a local ES-DE/RetroArch setup.")


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
    if len(matches) > 1:
        typer.echo(f"{len(matches)} matches; downloading first: {matches[0].name}", err=True)
    rom = matches[0]
    cache = MappingCache(_cache_path())
    m3u = download_rom(rom, client, roms_root=settings.roms_root, cache=cache,
                       overrides=settings.platform_overrides)
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
