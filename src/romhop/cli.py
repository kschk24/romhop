from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx
import typer
import typer.rich_utils
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from romhop import config, retroarch_cfg
from romhop.platform_names import PlatformNames, display_name


def complete_game_name(incomplete: str):
    """
    Completion callback for the 'name' argument of the 'download' command.
    
    Queries RomM for games matching the incomplete string and returns their names for shell completion.
    """
    # Try to construct a client; on any error, return no completions so we
    # dont break users shell
    try:
        client=_client()
    except typer.Exit:
        return []
    except Exception:
        return []
    
    try:
        # Use server-side search to keep it fast
        roms = client.list_roms(search_term=incomplete)
    except Exception:
        return []

    # Collect unique namees, limited to a small number.
    seen = set()
    suggestions: list[str] = []
    for rom in roms:
        title = rom.name
        if not title:
            continue
        if title in seen:
            continue
        seen.add(title)
        suggestions.append(title)
        if len(suggestions) >= 20:
            break
    
    return suggestions


@contextmanager
def _download_progress(label: str):
    """Yield an on_progress(downloaded, total) callback backed by a Rich bar.

    total may be None (server sent no Content-Length) — the bar shows bytes + speed.
    """
    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        transient=True,
    )
    with progress:
        task_id = progress.add_task(label, total=None)

        def on_progress(downloaded: int, total: int | None):
            progress.update(task_id, completed=downloaded, total=total)

        yield on_progress
from romhop.download import download_rom
from romhop.library import norm
from romhop.local_index import index_local_library, match_to_roms
from romhop.mapping_cache import MappingCache, RomEntry, seed_entry
from romhop.platform_map import esde_system_for_slug
from romhop.pull import pull_games
from romhop.romm_client import Rom, RommClient
from romhop.sync import watch_and_push

from romhop._frog import FROG

_DESC = "Sync a RomM library with a local ES-DE/RetroArch setup."


def _show_frog() -> bool:
    # Frog gutter only on an interactive terminal (not when piped, redirected,
    # or NO_COLOR is set) so logs and pipes stay clean.
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _format_help_with_frog(*, obj, ctx, markup_mode) -> None:
    """typer help with the frog art in a left gutter and the body to its right.

    Renders the usage line full-width, then composes a two-column grid: the
    packaged frog on the left and typer's normal help body (description +
    Options/Commands panels) captured at a reduced width on the right.
    """
    from collections import defaultdict

    from rich.align import Align
    from rich.console import Console
    from rich.padding import Padding
    from rich.table import Table
    from rich.text import Text

    import typer.rich_utils as ru
    from typer.core import TyperArgument, TyperGroup, TyperOption

    console = ru._get_rich_console()
    art = FROG.strip("\n").split("\n")
    art_w = max(len(line) for line in art)
    gap = 3
    left_pad = 1
    body_w = max(24, console.width - art_w - gap - left_pad)

    # Capture typer's normal help body (everything below the usage line) at the
    # reduced width so the panels wrap into the right-hand column.
    cap = Console(width=body_w, force_terminal=True,
                  color_system=console.color_system)
    with cap.capture() as captured:
        if obj.help:
            cap.print(Padding(
                Align(ru._get_help_text(obj=obj, markup_mode=markup_mode), pad=False),
                (0, 1, 1, 1)))

        panel_to_arguments: defaultdict[str, list] = defaultdict(list)
        panel_to_options: defaultdict[str, list] = defaultdict(list)
        for param in obj.get_params(ctx):
            if getattr(param, "hidden", False):
                continue
            if isinstance(param, TyperArgument):
                name = getattr(param, ru._RICH_HELP_PANEL_NAME, None) or ru.ARGUMENTS_PANEL_TITLE
                panel_to_arguments[name].append(param)
            elif isinstance(param, TyperOption):
                name = getattr(param, ru._RICH_HELP_PANEL_NAME, None) or ru.OPTIONS_PANEL_TITLE
                panel_to_options[name].append(param)

        ru._print_options_panel(
            name=ru.ARGUMENTS_PANEL_TITLE,
            params=panel_to_arguments.get(ru.ARGUMENTS_PANEL_TITLE, []),
            ctx=ctx, markup_mode=markup_mode, console=cap)
        for name, args in panel_to_arguments.items():
            if name == ru.ARGUMENTS_PANEL_TITLE:
                continue
            ru._print_options_panel(name=name, params=args, ctx=ctx,
                                    markup_mode=markup_mode, console=cap)
        ru._print_options_panel(
            name=ru.OPTIONS_PANEL_TITLE,
            params=panel_to_options.get(ru.OPTIONS_PANEL_TITLE, []),
            ctx=ctx, markup_mode=markup_mode, console=cap)
        for name, opts in panel_to_options.items():
            if name == ru.OPTIONS_PANEL_TITLE:
                continue
            ru._print_options_panel(name=name, params=opts, ctx=ctx,
                                    markup_mode=markup_mode, console=cap)

        if isinstance(obj, TyperGroup):
            panel_to_commands: defaultdict[str, list] = defaultdict(list)
            for command_name in obj.list_commands(ctx):
                command = obj.get_command(ctx, command_name)
                if command and not command.hidden:
                    name = getattr(command, ru._RICH_HELP_PANEL_NAME, None) or ru.COMMANDS_PANEL_TITLE
                    panel_to_commands[name].append(command)
            max_cmd_len = max(
                (len(c.name or "") for cmds in panel_to_commands.values() for c in cmds),
                default=0)
            ru._print_commands_panel(
                name=ru.COMMANDS_PANEL_TITLE,
                commands=panel_to_commands.get(ru.COMMANDS_PANEL_TITLE, []),
                markup_mode=markup_mode, console=cap, cmd_len=max_cmd_len)
            for name, cmds in panel_to_commands.items():
                if name == ru.COMMANDS_PANEL_TITLE:
                    continue
                ru._print_commands_panel(name=name, commands=cmds,
                                         markup_mode=markup_mode, console=cap,
                                         cmd_len=max_cmd_len)

    # Usage line, full width.
    console.print(Padding(ru.highlighter(obj.get_usage(ctx)), 1),
                  style=ru.STYLE_USAGE_COMMAND)

    grid = Table.grid(padding=0)
    grid.add_column(width=art_w + gap, vertical="top")
    grid.add_column(vertical="top")
    grid.add_row(Padding(Text("\n".join(art)), (0, 0, 0, left_pad)),
                 Text.from_ansi(captured.get().rstrip("\n")))
    console.print(grid)


_orig_rich_format_help = typer.rich_utils.rich_format_help


def _rich_format_help(*, obj, ctx, markup_mode) -> None:
    if not _show_frog():
        return _orig_rich_format_help(obj=obj, ctx=ctx, markup_mode=markup_mode)
    try:
        _format_help_with_frog(obj=obj, ctx=ctx, markup_mode=markup_mode)
    except Exception:
        # Never let cosmetics break --help.
        _orig_rich_format_help(obj=obj, ctx=ctx, markup_mode=markup_mode)


typer.rich_utils.rich_format_help = _rich_format_help

app = typer.Typer(rich_markup_mode="markdown", help=_DESC)

# Settings the user can change via `romhop config set`.
_PATH_KEYS = ("roms_root", "saves_dir", "states_dir")
_STR_KEYS = ("romm_url",)
_FLOAT_KEYS = ("sync_delay_seconds",)
config_app = typer.Typer(help="View or change settings (stored in settings.ini).")
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path():
    """Print the settings file location."""
    typer.echo(str(config.settings_path()))


@config_app.command("show")
def config_show():
    """Print all current settings in INI format."""
    typer.echo(config.format_ini(config.load_settings()))


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


@config_app.command("set-core")
def config_set_core(core: str = typer.Argument(..., help="RetroArch core folder name"),
                    system: str = typer.Argument("", help="ES-DE system dir; empty to remove the override")):
    """Map a RetroArch core folder name to an ES-DE system dir (override). Empty system removes it."""
    settings = config.load_settings()
    if system:
        settings.core_overrides[core] = system
    else:
        settings.core_overrides.pop(core, None)
    config.save_settings(settings)
    typer.echo(f"core_overrides = {settings.core_overrides}")


def _select_match(name: str, matches: list[Rom]) -> Rom:
    """Pick the rom to download. Prefer an exact (case-insensitive) name match;
    otherwise refuse to guess and list the candidates so the user can be specific."""
    if len(matches) == 1:
        return matches[0]
    exact = [r for r in matches if r.name.lower() == name.lower()]
    if len(exact) == 1:
        return exact[0]
    typer.echo(f"{len(matches)} games match '{name}'. Be more specific (or use the exact name):", err=True)
    names = PlatformNames(_platform_names_path())
    for r in matches:
        typer.echo(f"  {r.name} - {display_name(r, names)}", err=True)
    raise typer.Exit(code=2)


def _select_entries_by_name(entries: list[RomEntry], name: str) -> list[RomEntry]:
    """Pick cached entries by game name: exact (case-insensitive) preferred,
    else unique substring. Aborts (exit 2) on ambiguity, exit 1 on no match."""
    matches = [e for e in entries if name.lower() in e.game_name.lower()]
    if not matches:
        typer.echo(f"No cached game matching '{name}'.", err=True)
        raise typer.Exit(code=1)
    exact = [e for e in matches if e.game_name.lower() == name.lower()]
    if len(exact) == 1:
        return exact
    if len(matches) == 1:
        return matches
    typer.echo(f"{len(matches)} cached games match '{name}'. Be more specific:", err=True)
    for e in matches:
        typer.echo(f"  {e.game_name}", err=True)
    raise typer.Exit(code=2)


def _client() -> RommClient:
    settings = config.load_settings()
    token = config.get_token()
    if not settings.romm_url or not token:
        typer.echo("Not logged in. Run: romhop login --url <url> --token <rmm_...>", err=True)
        raise typer.Exit(code=1)
    return RommClient(base_url=settings.romm_url, token=token)


def _cache_path() -> Path:
    import platformdirs
    return Path(platformdirs.user_data_dir("romhop")) / "mapping_cache.json"


def _platform_names_path() -> Path:
    import platformdirs
    return Path(platformdirs.user_data_dir("romhop")) / "platform_names.json"


@app.command()
def login(url: str = typer.Option(..., "--url"),
          token: str = typer.Option(..., "--token")):
    """Store the RomM URL and API token (non-interactive). For first-time setup use `setup`."""
    config.set_token(token)           # store token first; if keyring fails, no partial state
    settings = config.load_settings()
    settings.romm_url = url
    config.save_settings(settings)
    typer.echo(f"Saved RomM URL {url} and token.")


def _retroarch_cfg_values(current) -> tuple[Path | None, Path | None, bool, bool]:
    """Detect RetroArch's saves/states dirs AND per-core sort flags.

    Windows: prompt for the install folder (no reliable auto-location for a
    portable install). Other OSes: auto-locate the standard retroarch.cfg.
    Delegates the parsing to retroarch_cfg.detect."""
    folder = None
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        guess = Path(appdata) / "RetroArch" if appdata else None
        folder = Path(typer.prompt(
            "RetroArch installation folder (where retroarch.cfg lives)",
            default=str(guess) if guess and guess.exists() else None,
        )).expanduser()
    return retroarch_cfg.detect(folder)


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
    # Detect the saves/states folders from retroarch.cfg. When both are found we
    # show them and let the user override; if either is unknown we re-prompt.
    det_saves, det_states, sort_saves, sort_states = _retroarch_cfg_values(current)
    if det_saves is not None and det_states is not None:
        typer.echo(f"RetroArch saves:  {det_saves}")
        typer.echo(f"RetroArch states: {det_states}")
        if typer.confirm("Change the saves/states folders?", default=False):
            saves = typer.prompt("RetroArch saves folder", default=str(det_saves))
            states = typer.prompt("RetroArch states folder", default=str(det_states))
        else:
            saves = str(det_saves)
            states = str(det_states)
    else:
        saves = typer.prompt("RetroArch saves folder",
                             default=str(det_saves or current.saves_dir))
        states = typer.prompt("RetroArch states folder",
                              default=str(det_states or current.states_dir))

    if token.strip():
        config.set_token(token.strip())
    elif not existing_token:
        typer.echo("A token is required.", err=True)
        raise typer.Exit(code=1)

    current.romm_url = url.strip()
    current.roms_root = Path(roms).expanduser()
    current.saves_dir = Path(saves).expanduser()
    current.states_dir = Path(states).expanduser()
    current.sort_saves_by_core = sort_saves
    current.sort_states_by_core = sort_states
    config.save_settings(current)
    typer.echo(f"Setup complete. Settings saved to {config.settings_path()}")
    if typer.confirm("Scan your ROMs folder now to enable save sync for existing games?",
                     default=True):
        _run_scan(config.load_settings(), assume_yes=True)


def _exit_http(exc: httpx.HTTPStatusError, *, not_found: str | None = None):
    """Turn an httpx error into a friendly message + exit 1 (no traceback)."""
    code = exc.response.status_code
    if code in (401, 403):
        msg = (f"RomM rejected the request ({code} {exc.response.reason_phrase}). The API token is "
               "invalid or lacks scope (needs roms.read + assets.read/write). "
               "Re-run `romhop login` or `romhop setup` with a valid token.")
    elif code == 404 and not_found:
        msg = not_found
    else:
        msg = f"RomM returned HTTP {code} {exc.response.reason_phrase}."
    typer.echo(msg, err=True)
    raise typer.Exit(code=1)


@app.command()
def download(
    name: str = typer.Argument(
        ..., help="Game name (substring match)",
        autocompletion=complete_game_name,
        )
    ):
    """Download a game into the ES-DE layout (exact name, or a unique substring)."""
    settings = config.load_settings()
    if not config.roms_root_configured(settings):
        typer.echo("ROMs folder not set. Run: romhop setup  (or: romhop config set roms_root <path>)", err=True)
        raise typer.Exit(code=1)
    client = _client()
    try:
        roms = client.list_roms(search_term=name)
    except httpx.HTTPStatusError as exc:
        _exit_http(exc)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach RomM: {exc}", err=True)
        raise typer.Exit(code=1)
    PlatformNames(_platform_names_path()).update_from_roms(roms)
    matches = [r for r in roms if name.lower() in r.name.lower()]
    if not matches:
        typer.echo(f"No game matching '{name}'.", err=True)
        raise typer.Exit(code=1)
    rom = _select_match(name, matches)
    # Already on disk? Skip the transfer, just record the mapping for save sync.
    system = esde_system_for_slug(rom.platform_slug, settings.platform_overrides)
    locals_ = index_local_library(settings.roms_root, settings.platform_overrides, system=system)
    target_keys = {norm(rom.fs_name), norm(rom.fs_name_no_ext)}
    already = next((g for g in locals_ if g.match_key in target_keys), None)
    if already is not None:
        cache = MappingCache(_cache_path())
        cache.add(seed_entry(rom.id, system, rom.fs_name_no_ext, already.file_names))
        cache.save()
        typer.echo(f"Already local: {rom.name} — mapped for save sync (no download).")
        raise typer.Exit(code=0)
    cache = MappingCache(_cache_path())
    try:
        with _download_progress(rom.name) as on_progress:
            m3u = download_rom(rom, client, roms_root=settings.roms_root, cache=cache,
                               overrides=settings.platform_overrides, on_progress=on_progress)
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
        core_overrides=settings.core_overrides,
        on_ambiguous=lambda p, cands: typer.echo(
            f"Skipped {p.name}: ambiguous across systems "
            f"({', '.join(sorted(c.system for c in cands))}). "
            f"Set a core mapping: romhop config set-core '{p.parent.name}' <system>",
            err=True),
    )


@app.command()
def pull(name: str = typer.Argument(None, help="Game name (omit and use --all for everything)"),
         all_games: bool = typer.Option(False, "-a", "--all", help="Pull every cached game."),
         remote: bool = typer.Option(False, "--remote", help="On conflict, always take RomM's version (no prompt).")):
    """Download saves/states from RomM into the local RetroArch layout."""
    if not name and not all_games:
        typer.echo("Name a game or pass --all.", err=True)
        raise typer.Exit(code=2)
    settings = config.load_settings()
    client = _client()
    cache = MappingCache(_cache_path())
    entries = cache.entries()
    if not entries:
        typer.echo("No cached games. Run: romhop scan", err=True)
        raise typer.Exit(code=1)
    if all_games:
        targets = entries
    else:
        targets = _select_entries_by_name(entries, name)

    def on_conflict(item, local_path, local_mtime):
        typer.echo(f"{item.file_name}: local {local_mtime:%Y-%m-%d %H:%M} "
                   f"vs RomM {item.remote_updated}")
        return typer.confirm("Take RomM's version? (n = keep local)", default=False)

    try:
        summary = pull_games(client, targets, settings, take_remote=remote,
                             on_conflict=on_conflict,
                             on_written=lambda p: typer.echo(f"Pulled {p.name}"),
                             on_error=lambda p, exc: typer.echo(
                                 f"Could not write {p}: {exc}", err=True))
    except httpx.HTTPStatusError as exc:
        _exit_http(exc)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach RomM: {exc}", err=True)
        raise typer.Exit(code=1)
    line = (f"Pulled {summary['written']}, skipped {summary['skipped']} "
            f"(up to date), kept {summary['kept']} local.")
    if summary.get("failed"):
        line += f" {summary['failed']} failed."
    typer.echo(line)


def _run_scan(settings, *, assume_yes: bool) -> None:
    """Match local games to RomM roms and seed the cache. Preview then confirm
    unless assume_yes. Assumes roms_root is configured and login is valid."""
    client = _client()
    try:
        roms = client.list_roms()
    except httpx.HTTPStatusError as exc:
        _exit_http(exc)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach RomM: {exc}", err=True)
        raise typer.Exit(code=1)
    PlatformNames(_platform_names_path()).update_from_roms(roms)

    locals_ = index_local_library(settings.roms_root, settings.platform_overrides)
    result = match_to_roms(locals_, roms, settings.platform_overrides)

    typer.echo(f"{len(result.matched)} matched, {len(result.unmatched)} unmatched, "
               f"{len(result.collisions)} basename collisions.")
    if result.unmatched:
        typer.echo("Unmatched (no RomM rom found — rescan in RomM or rename):")
        for g in result.unmatched:
            typer.echo(f"  {g.system}/{g.game_name}")
    if result.collisions:
        typer.echo("Collisions (saves disambiguated by core at sync time):")
        for c in result.collisions:
            typer.echo(f"  {c.basename}: roms {c.rom_ids}")

    if not result.matched:
        typer.echo("Nothing to map.")
        return
    if not assume_yes and not typer.confirm(f"Write {len(result.matched)} mappings?", default=False):
        typer.echo("Aborted; cache unchanged.")
        return

    cache = MappingCache(_cache_path())
    for local, rom in result.matched:
        # local.system already equals esde_system_for_slug(rom.platform_slug) —
        # match_to_roms only pairs a rom with a local game in the same system dir.
        cache.add(seed_entry(rom.id, local.system, rom.fs_name_no_ext, local.file_names))
    cache.save()
    typer.echo(f"Wrote {len(result.matched)} mappings to {_cache_path()}")


@app.command()
def scan(yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt.")):
    """Match games already in your ROMs folder to RomM and seed the save-sync cache."""
    settings = config.load_settings()
    if not config.roms_root_configured(settings):
        typer.echo("ROMs folder not set. Run: romhop setup  (or: romhop config set roms_root <path>)", err=True)
        raise typer.Exit(code=1)
    _run_scan(settings, assume_yes=yes)


@app.command()
def gui() -> None:
    """Launch the romhop desktop GUI (requires the [gui] extra: PySide6)."""
    try:
        from romhop.gui.app import run
    except ImportError:
        typer.secho(
            "The GUI needs PySide6. Install it with:  pip install 'romhop[gui]'",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    run()


@app.command(name="install-desktop")
def install_desktop(
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove the desktop launcher instead."),
):
    """Register (or remove) a native desktop launcher for the GUI.

    Linux: writes an XDG .desktop entry + icons. Windows: creates a Start Menu
    shortcut to the no-console romhop-gui.exe. Paths are absolute, so it works
    regardless of PATH.
    """
    from romhop.gui import launcher_install

    if uninstall:
        removed = launcher_install.uninstall()
        if removed:
            for p in removed:
                typer.echo(f"Removed {p}")
        else:
            typer.echo("No launcher found to remove.")
        return

    written = launcher_install.install()
    for p in written:
        typer.echo(f"Wrote {p}")
    typer.secho("Desktop launcher installed. Look for 'RomHop' in your app menu.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
