# romhop

Sync a self-hosted [RomM](https://github.com/rommapp/romm) library with a local
[ES-DE](https://es-de.org/) / [RetroArch](https://www.retroarch.com/) setup.

It does two things:

- **Download** a game from RomM into the on-disk layout ES-DE expects
  (an `.m3u` plus a per-game folder).
- **Sync** RetroArch save files and savestates back to RomM automatically
  as they change.

There's a [Typer](https://typer.tiangolo.com/) CLI for scripting and a desktop
GUI (PySide6) for everyday use. Pick whichever you like — they share the same core.

## Install

### Most people — desktop app, no Python needed

Download the latest installer from the [Releases page](../../releases):

- **Windows:** `romhop-setup-<version>.exe` — double-click, install (no admin needed),
  launch from the Start Menu. Windows SmartScreen may warn "unknown publisher" the first
  time; choose **More info → Run anyway**.
- **Linux:** `romhop-installer-<version>-x86_64.AppImage` — make it executable
  (`chmod +x`) and double-click (or run it). It installs RomHop to
  `~/.local/lib/romhop` and adds a menu entry; launch RomHop from your menu afterwards.
  To uninstall, use the "Uninstall RomHop" menu entry (or run the app with `--uninstall`);
  your settings and saves are left untouched.

Verify a download against `SHA256SUMS` on the release if you wish.

On first launch the GUI runs a short setup wizard (RomM URL, API token, local
paths) — see [Setup](#setup).

### Power users — CLI via pipx

If you want the `romhop` command for scripting or headless use, install with
[pipx](https://pipx.pypa.io/). It drops romhop into an isolated environment and
puts both `romhop` (CLI) and `romhop-gui` on your PATH — no virtualenv or manual
PATH setup.

Directly from GitHub (no clone needed):

```
pipx install "romhop[gui] @ git+https://github.com/kschk24/romhop.git@gui-desktop-pyside"
```

Or from a clone:

```
git clone -b gui-desktop-pyside https://github.com/kschk24/romhop
cd romhop
pipx install ".[gui]"
```

Drop the `[gui]` extra if you only want the CLI. If you don't have pipx yet:

```
pip install pipx
pipx ensurepath
```

### Requirements

- A reachable RomM instance and a client API token with `roms.read` and
  `assets.read`/`assets.write` scope.
- Python 3.11+ — **only** for the pipx / source install. The desktop installers
  bundle their own runtime; you don't need Python for those.

## Setup

Interactive first-time setup (RomM URL, API token, and your local paths). The
GUI runs this as a wizard on first launch; from the CLI:

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

As its last step, `setup` offers to scan your ROMs folder (see
[Scan existing games](#scan-existing-games)) so games already on disk become
save-syncable immediately.

## GUI

Launch the desktop GUI:

```
romhop gui          # or the Start-Menu / app-menu entry from an installer
```

It browses your RomM library, downloads games (single or multi-select), edits
settings, and shows sync status — all in one window. Closing the window minimizes
to a system-tray icon and keeps save sync running in the background; relaunching
raises the existing window instead of starting a second copy. Quit from the tray
menu to stop sync and exit.

The look is themeable: drop a `.romhop-theme` package (a zip of `manifest.json` +
`tokens.json`, with optional `assets/` and `theme.qss`) into the romhop config dir
under `themes/`, then set `theme` in your settings. A broken or partial theme
falls back to the default, so it can never brick the UI.

## CLI usage

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

## Scan existing games

Match games already in your ROMs folder to your RomM library and seed the
save-sync cache — no re-downloading. Run it once after pointing romhop at an
existing ES-DE library so `sync` can push saves for games you didn't download
through romhop. (The GUI exposes the same thing as a "Scan local library" button
in settings.)

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
with no network and no live server. GUI tests use `pytest-qt`.

## Releasing (maintainers)

Releases are built and published by the `package` GitHub Actions workflow
(`.github/workflows/package.yml`). It builds a frozen GUI app on each OS
(PyInstaller onedir) and wraps it in a Windows Inno Setup installer and a Linux
bootstrap AppImage. CI also attaches a build-provenance attestation (verifiable
with `gh attestation verify`) — no signing keys or secrets required.

### Stable release

Bump `__version__` in `src/romhop/__init__.py`, then push a **clean** version tag
(no hyphens):

```
git tag v0.4.0
git push origin v0.4.0
```

CI marks the GitHub Release as **stable** (not prerelease). All installed copies
with auto-update on will see this release on next launch.

### Pre-release / release-candidate

Use a **hyphenated** tag:

```
git tag v0.4.0-rc1
git push origin v0.4.0-rc1
```

CI marks the release `prerelease: true`. Users who have enabled
**"Include experimental pre-release updates"** in Settings will see it; stable
users will not. When the final `v0.4.0` tag ships, experimental users roll forward
automatically (packaging.version ordering: `0.4.0rc1 < 0.4.0`).

### Dry run

Trigger the workflow manually (`workflow_dispatch`) to build and upload artifacts
**without** publishing a Release — useful for testing a build.

Only a maintainer should bump the version and push a tag; don't tag from a
feature branch you don't intend to release.

### Release smoke checklist

After a tagged build publishes, verify on each OS:

**Fresh install**

- **Windows:** run `romhop-setup-*.exe` → installs without admin → Start-Menu shortcut
  launches the GUI → uninstall via Add/Remove Programs removes it.
- **Linux:** `chmod +x` the AppImage → run it → menu entry appears → menu entry launches
  the installed copy → re-running the AppImage just launches (does not reinstall).

**Auto-update (stable)**

1. Install the **previous** stable release on each OS.
2. Publish the **new** release tag. Wait for CI to finish.
3. Launch the installed app. The banner `vX.Y.Z available [Update] [Later]`
   should appear within seconds.
4. Click **Update**. The progress bar fills while the new installer downloads.
5. `Restart romhop to finish updating` dialog appears.
6. The new version launches automatically.
7. Confirm `romhop --version` shows the new version.

**Auto-update (experimental / pre-release)**

1. Toggle **"Include experimental pre-release updates"** on in Settings, Save.
2. Repeat the update smoke with a `-rc` tag. The banner should appear for the
   pre-release version. Stable-channel users should see nothing.

**Troubleshooting**

| Symptom | Likely cause | Action |
|---|---|---|
| Banner never appears | App not frozen, install dir not writable, or `auto_update_check` off | Settings → "Check for updates" manually; verify frozen build |
| Banner appears but "No update" | Version in tag == installed version | Check `__version__` was bumped before tagging |
| `update error: SHA-256 mismatch` | Corrupt/truncated download | Retry next launch; the `.part` temp is discarded |
| `update error: Installer exited with code N` | Silent installer failed | Check installer log on disk; keep current install intact |
| Update on Linux leaves old version | Bootstrap not extracting | Ensure `--appimage-bootstrap` completes (check for FUSE errors) |
| GitHub rate-limit (403) | > 60 API calls/hour per IP | Back off automatically; retry next launch |

## License

GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE).

If you run a modified version as a network-accessible service, the AGPL
requires you to make the modified source available to its users.
