from __future__ import annotations

import json
from pathlib import Path

import httpx
import typer

from emusync import config
from emusync.download import download_rom
from emusync.mapping_cache import MappingCache
from emusync.romm_client import Rom, RommClient
from emusync.sync import watch_and_push

app = typer.Typer(help="Sync a RomM library with a local ES-DE/RetroArch setup.")

# Settings the user can change via `emusync config set`.
_PATH_KEYS = ("roms_root", "saves_dir", "states_dir")
_STR_KEYS = ("romm_url",)
_FLOAT_KEYS = ("sync_delay_seconds",)
config_app = typer.Typer(help="View or change settings (stored in settings.json).")
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path():
    """Print the settings file location."""
    typer.echo(str(config.settings_path()))


@config_app.command("show")
def config_show():
    """Print all current settings as JSON."""
    typer.echo(json.dumps(config.to_dict(config.load_settings()), indent=2))


@config_app.command("set")
def config_set(key: str = typer.Argument(..., help="e.g. roms_root, saves_dir, states_dir, romm_url, sync_delay_seconds"),
               value: str = typer.Argument(..., help="New value")):
    """Set one setting. Paths accept ~ expansion."""
    settings = config.load_settings()
    if key in _PATH_KEYS:
        setattr(settings, key, Path(value).expanduser())
    elif key in _STR_KEYS:
        setattr(settings, key, value)
    elif key in _FLOAT_KEYS:
        try:
            setattr(settings, key, float(value))
        except ValueError:
            typer.echo(f"{key} must be a number, got {value!r}", err=True)
            raise typer.Exit(code=2)
    else:
        allowed = ", ".join(_PATH_KEYS + _STR_KEYS + _FLOAT_KEYS)
        typer.echo(f"Unknown setting '{key}'. Settable: {allowed}", err=True)
        raise typer.Exit(code=2)
    config.save_settings(settings)
    typer.echo(f"Set {key} = {getattr(settings, key)}")


@config_app.command("set-platform")
def config_set_platform(slug: str = typer.Argument(..., help="RomM platform slug"),
                        system: str = typer.Argument("", help="ES-DE system dir; empty to remove the override")):
    """Map a RomM platform slug to an ES-DE system dir (override). Empty system removes it."""
    settings = config.load_settings()
    if system:
        settings.platform_overrides[slug] = system
    else:
        settings.platform_overrides.pop(slug, None)
    config.save_settings(settings)
    typer.echo(f"platform_overrides = {settings.platform_overrides}")


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
    """Store the RomM URL and API token (non-interactive). For first-time setup use `setup`."""
    config.set_token(token)           # store token first; if keyring fails, no partial state
    settings = config.load_settings()
    settings.romm_url = url
    config.save_settings(settings)
    typer.echo(f"Saved RomM URL {url} and token.")


@app.command()
def setup():
    """Interactive first-time setup: RomM URL + token and the local ROM/save paths."""
    current = config.load_settings()
    existing_token = config.get_token()

    url = typer.prompt("RomM URL", default=current.romm_url or None)
    token = typer.prompt(
        "RomM API token (rmm_...)" + (" [leave blank to keep current]" if existing_token else ""),
        default="" if existing_token else None,
        hide_input=True, show_default=False,
    )
    roms = typer.prompt(
        "Local ROMs folder (your ES-DE library root)",
        default=str(current.roms_root) if config.roms_root_configured(current) else None,
    )
    # saves/states default to the standard per-OS RetroArch paths — usually correct,
    # so only prompt for them if the user opts in.
    typer.echo(f"RetroArch saves:  {current.saves_dir}")
    typer.echo(f"RetroArch states: {current.states_dir}")
    if typer.confirm("Change the saves/states folders?", default=False):
        saves = typer.prompt("RetroArch saves folder", default=str(current.saves_dir))
        states = typer.prompt("RetroArch states folder", default=str(current.states_dir))
    else:
        saves = str(current.saves_dir)
        states = str(current.states_dir)

    if token.strip():
        config.set_token(token.strip())
    elif not existing_token:
        typer.echo("A token is required.", err=True)
        raise typer.Exit(code=1)

    current.romm_url = url.strip()
    current.roms_root = Path(roms).expanduser()
    current.saves_dir = Path(saves).expanduser()
    current.states_dir = Path(states).expanduser()
    config.save_settings(current)
    typer.echo(f"Setup complete. Settings saved to {config.settings_path()}")


def _exit_http(exc: httpx.HTTPStatusError, *, not_found: str | None = None):
    """Turn an httpx error into a friendly message + exit 1 (no traceback)."""
    code = exc.response.status_code
    if code in (401, 403):
        msg = (f"RomM rejected the request ({code} {exc.response.reason_phrase}). The API token is "
               "invalid or lacks scope (needs roms.read + assets.read/write). "
               "Re-run `emusync login` or `emusync setup` with a valid token.")
    elif code == 404 and not_found:
        msg = not_found
    else:
        msg = f"RomM returned HTTP {code} {exc.response.reason_phrase}."
    typer.echo(msg, err=True)
    raise typer.Exit(code=1)


@app.command()
def download(name: str = typer.Argument(..., help="Game name (substring match)")):
    """Download a game into the ES-DE layout (exact name, or a unique substring)."""
    settings = config.load_settings()
    if not config.roms_root_configured(settings):
        typer.echo("ROMs folder not set. Run: emusync setup  (or: emusync config set roms_root <path>)", err=True)
        raise typer.Exit(code=1)
    client = _client()
    try:
        roms = client.list_roms(search_term=name)
    except httpx.HTTPStatusError as exc:
        _exit_http(exc)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach RomM: {exc}", err=True)
        raise typer.Exit(code=1)
    matches = [r for r in roms if name.lower() in r.name.lower()]
    if not matches:
        typer.echo(f"No game matching '{name}'.", err=True)
        raise typer.Exit(code=1)
    rom = _select_match(name, matches)
    cache = MappingCache(_cache_path())
    try:
        m3u = download_rom(rom, client, roms_root=settings.roms_root, cache=cache,
                           overrides=settings.platform_overrides)
    except httpx.HTTPStatusError as exc:
        _exit_http(exc, not_found=(
            f"RomM has no downloadable files for '{rom.name}' (id {rom.id}). "
            "It looks unmatched/unscanned on the server — try a rescan in RomM."))
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
