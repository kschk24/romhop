# romhop

Syncs a self-hosted RomM library with a local ES-DE / RetroArch setup: downloads
games into the on-disk layout ES-DE expects, and syncs RetroArch saves/savestates
back to RomM. Typer CLI + optional PySide6 desktop GUI.

## Language

### Library & browsing

**Library grid**:
The flat, scrollable grid of game tiles in the GUI (one tile per Rom across all
platforms). Filtered by platform / text / downloaded status.
_Avoid_: list, gallery.

**Tile**:
A single game's cell in the Library grid: cover image, name, platform pill,
downloaded ribbon, and a batch-select checkbox.
_Avoid_: card, cell, item.

**Batch selection**:
The set of games checked (via each tile's checkbox glyph) for a multi-game
operation, primarily download. Spans every filter/platform, not just visible tiles.
Distinct from opening a game — a tile's body click opens its Detail panel; only the
checkbox glyph toggles Batch selection.
_Avoid_: highlight, active game.

**Detail panel**:
A panel docked on the right of the main window showing one game's metadata and its
Game actions. Opened by clicking a tile's body; updates in place when another tile
is clicked; dismissed with a close button. Shows local Rom fields instantly, then
fills in RomM-fetched detail (summary, release date, genres, file size) when it
arrives.
_Avoid_: detail screen, detail dialog, info popup.

### Actions

**Game action**:
A single-game operation exposed identically in the Detail panel (as a button) and
the tile's right-click menu. The set: Download, Pull savegames, Open in RomM, Open
containing folder.
_Avoid_: command, operation.

**Download** (Game action):
Fetch one game's files into the ES-DE layout. Same path as a batch Download, scoped
to one Rom.

**Pull savegames** (Game action):
Download a single game's saves + savestates from RomM into the local saves/states
dirs. Needs only the Rom's id. On a local file that differs from RomM's, prompts
per conflict (keep local vs take remote).
_Avoid_: restore, sync down.

**Open in RomM**:
Open the game's RomM web page (`{romm_url}/rom/{id}`) in the system browser.
_Avoid_: link out, view online.

**Open containing folder**:
Open the downloaded game's on-disk folder in the OS file manager. Available only
when the game is downloaded.

### Matching & upload

**Unmatched game**:
A local game in the ES-DE tree that `scan` could not pair to any RomM rom by its
exact, normalized, platform-scoped key. Surfaced in scan's Unmatched report. A flat
`.cue`+`.bin` disc game counts as one Unmatched game (the descriptor and its tracks
coalesce), not several.
_Avoid_: orphan, missing rom, unsynced game.

**Upload to RomM**:
Send an Unmatched game's actual rom file(s) up to RomM so it becomes a tracked rom —
the reverse of Download. Offered from the Unmatched report (GUI dialog picker + CLI
checklist, or the non-interactive `--upload-unmatched` flag). Only the real rom
files go up (never the ES-DE `.m3u`/`noload.txt` artifacts). Resolvable only when the
game's ES-DE system maps to a RomM platform, or the user opts to create that platform.
If an upload is interrupted (force-quit, power loss), recovery is to re-run `scan`:
an un-uploaded game is still an Unmatched game, so it re-surfaces on its own — there
is no separate resumable upload queue.
_Avoid_: push, sync up, send, publish.

**Resolvable** (of an Unmatched game):
Whether the game can actually be uploaded: its ES-DE system maps to an existing RomM
platform (or one the user agrees to create) and it has real files on disk. Unresolvable
games are shown but disabled, with the reason.
_Avoid_: uploadable, eligible.

### Activity feedback

**Activity event**:
A single user-meaningful thing romhop did while running: a save synced up, a
download finished, or an operation failed. Typed and timestamped, with a
human-readable message. One stream of these is emitted by the core; the GUI
renders the same stream three ways — a transient Toast, an opt-in Desktop
notification, and a persistent Activity log.
_Avoid_: notification (as the generic term — that names one renderer), message,
status update.

**Toast**:
A transient, self-dismissing in-app banner (bottom-right of the main window)
rendering an Activity event. Always on; the lightest-weight renderer.
_Avoid_: popup, snackbar, alert.

**Desktop notification**:
An opt-in, OS-level notification (delivered through the system tray) rendering an
Activity event when romhop is not focused or is minimized to tray. Off by default;
toggled in settings.
_Avoid_: OS toast, system alert, push.

**Activity log**:
The in-app, scrollable panel listing recent Activity events so the user can review
what romhop has done this session. Distinct from the Diagnostic log (a file for
remote troubleshooting); the Activity log is user-facing history, not a log file.
_Avoid_: history, event log, console.

### Diagnostics

**Diagnostic log**:
The rotating log file romhop always writes, capturing INFO-level events so a
remote user can send it when reporting a setup-specific problem. The user never
turns it on; they only retrieve and share it.
_Avoid_: debug output, console log, trace.

**Detailed logging**:
The opt-in mode that raises the Diagnostic log from INFO to DEBUG. Persisted as a
setting (a GUI checkbox) so a non-technical user can be talked through enabling it,
reproduce, then export. The CLI equivalent is a per-run `-v` flag.
_Avoid_: verbose mode, trace mode (in user-facing copy).

**Redaction**:
The rule that certain values never appear in the Diagnostic log regardless of
level: the RomM API token (never), the RomM host (masked), and the user's home
directory in paths (abbreviated). Because exported logs are effectively shared.
_Avoid_: scrubbing, sanitizing, masking (pick one term: redaction).
