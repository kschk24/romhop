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

```
pip install .
```

This installs the `romhop` command.

## Setup

Interactive first-time setup (RomM URL, API token, and your local paths):

```
romhop setup
```

The token is stored in the OS keyring, never in a config file. Everything else
is written to `settings.json` (run `romhop config path` to see where).

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
romhop config show                  # print current settings as JSON
romhop config set <key> <value>     # roms_root, saves_dir, states_dir, romm_url, sync_delay_seconds
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
