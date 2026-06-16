# romhop

Sync a self-hosted [RomM](https://github.com/rommapp/romm) library with a local
[ES-DE](https://es-de.org/) / [RetroArch](https://www.retroarch.com/) setup.

Two things:

- **Download** a game from RomM into the on-disk layout ES-DE expects
  (an `.m3u` plus a per-game folder).
- **Sync** RetroArch save files and savestates back to RomM automatically
  as they change.

## Requirements

- Python 3.11+
- A reachable RomM instance and a client API token with `roms.read` and
  `assets.read`/`assets.write` scope.

## Install

The recommended way to install romhop is with [pipx](https://pipx.pypa.io/),
which installs it into an isolated environment and automatically puts the
`romhop` command on your PATH — no virtualenv or manual PATH setup needed.

**From source (clone first):**

```
git clone -b gui-desktop-pyside https://github.com/kschk24/romhop
cd romhop
pipx install ".[gui]"
```

**Directly from GitHub (no clone needed):**

```
pipx install "romhop[gui] @ git+https://github.com/kschk24/romhop.git@gui-desktop-pyside"
```

If you don't have pipx yet:

```
pip install pipx
pipx ensurepath
```

## Setup

Interactive first-time setup (RomM URL, API token, and your local paths):

```
romhop setup
```

The token is stored in the OS keyring, never in a config file. Everything else
is written to `settings.ini` (run `romhop config path` to see where).

Non-interactive equivalent:

```
romhop login --url https://romm.example --token rmm_xxx
romhop config set roms_root ~/Games/Emulation
```

`setup` reads your RetroArch `retroarch.cfg` to fill in the saves/states folders:
on Linux/macOS it auto-locates `~/.config/retroarch/retroarch.cfg`; on Windows it
asks for your RetroArch installation folder (where `retroarch.cfg` lives, e.g. a
portable `D:\RetroArch`). If the cfg doesn't specify them, it prompts. The ROMs
root has no universal default and must be set.

As its last step, `setup` offers to scan your ROMs folder (see below) so games
already on disk become save-syncable immediately.

## Usage

Download a game by exact name or a unique substring:

```
romhop download "Sonic"
```

If the game is already in your ROMs folder, `download` skips the transfer and
just records the mapping needed for save sync.

Watch RetroArch saves/states and push changes to RomM until interrupted:

```
romhop sync
```

Restore saves/states from RomM into your local RetroArch layout:

```
romhop pull "Sonic"          # one game
romhop pull --all            # every game in the mapping cache
romhop pull --all --remote   # bulk restore, always take RomM's version
```

`pull` writes a save only when it's new or you choose it: an unchanged save is
skipped, and a differing local save prompts you (showing both dates) to keep
local or take RomM's — unless `--remote` is set. New saves are placed by your
RetroArch sort setting (per-core subfolder or flat), read from `retroarch.cfg`
during `setup`. Needs the RomM token to have `assets.read` scope.

## GUI

A desktop GUI (PySide6) is available as an optional extra:

```
pip install 'romhop[gui]'
romhop gui
```

It browses your RomM library, downloads games (single or multi-select), edits
settings, and shows sync status — all in one window. Closing the window minimizes
to a system-tray icon and keeps save sync running in the background; relaunching
raises the existing window instead of starting a second copy. Quit from the tray
menu to stop sync and exit. The look is themeable: drop a `.romhop-theme` package
(a zip of `manifest.json` + `tokens.json`, with optional `assets/` and
`theme.qss`) into the romhop config dir under `themes/`, then set `theme` in your
settings. A broken or partial theme falls back to the default, so it can never
brick the UI.

## Scan existing games

Match games already in your ROMs folder to your RomM library and seed the
save-sync cache — no re-downloading. Run it once after pointing romhop at an
existing ES-DE library so `sync` can push saves for games you didn't download
through romhop.

```
romhop scan          # preview matches, then confirm
romhop scan --yes    # write mappings without prompting
```

Matching is exact (whitespace- and case-insensitive) and scoped per platform, so
revision/region variants like `(Rev 1)` stay distinct and same-named games on
different systems aren't confused. When two systems do share a save basename,
`sync` disambiguates by the RetroArch core folder; map an unknown core with
`romhop config set-core "<core folder>" <es-de-dir>`.

Scanning needs no extra token scope (`roms.read`, which you already have).

## Configuration

```
romhop config show                  # print current settings (ini)
romhop config set <key> <value>     # romm_url, roms_root, saves_dir, states_dir,
                                    # sort_saves_by_core, sort_states_by_core,
                                    # sync_enabled, sync_delay_seconds,
                                    # download_rate_limit_kbps, theme
romhop config set-platform <slug> <es-de-dir>   # override platform -> ES-DE system dir mapping
romhop config set-core <core-folder> <es-de-dir> # map a RetroArch core folder -> ES-DE system dir
```

`sync_delay_seconds` is the debounce window before a changed save is uploaded
(default 8).

## Development

```
pip install -e '.[dev]'
pytest
```

The RomM client is tested against `httpx`'s `MockTransport`, so the suite runs
with no network and no live server.

## License

GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE).

If you run a modified version as a network-accessible service, the AGPL
requires you to make the modified source available to its users.
