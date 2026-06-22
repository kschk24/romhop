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
