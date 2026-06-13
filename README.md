# emusync

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

This installs the `emusync` command.

## Setup

Interactive first-time setup (RomM URL, API token, and your local paths):

```
emusync setup
```

The token is stored in the OS keyring, never in a config file. Everything else
is written to `settings.json` (run `emusync config path` to see where).

Non-interactive equivalent:

```
emusync login --url https://romm.example --token rmm_xxx
emusync config set roms_root ~/Games/Emulation
```

The RetroArch saves/states folders default to the standard per-OS RetroArch
paths, which are usually correct. The ROMs root has no universal default and
must be set.

## Usage

Download a game by exact name or a unique substring:

```
emusync download "Sonic"
```

Watch RetroArch saves/states and push changes to RomM until interrupted:

```
emusync sync
```

## Configuration

```
emusync config show                  # print current settings as JSON
emusync config set <key> <value>     # roms_root, saves_dir, states_dir, romm_url, sync_delay_seconds
emusync config set-platform <slug> <es-de-dir>   # override platform -> ES-DE system dir mapping
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

Not yet licensed. All rights reserved until a license is added.
