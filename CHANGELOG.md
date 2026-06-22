# Changelog

All notable changes to romhop are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [Unreleased]

### Fixed

- **DetailPanel image header no longer flips between cover and screenshot on repeated clicks.** Both loaders wrote to the same slot and whichever finished last won. Screenshot is now authoritative — a late-arriving cover is ignored once a screenshot has been applied for the current game.

- **DetailPanel sidebar now stays a fixed 300 px wide.** Previously the panel resized with each game selection as word-wrapped labels responded to varying content; long descriptions, summaries, and file lists now scroll inside the panel rather than pushing it wider or taller.

- **Search bar clears when switching between library and settings views.** Previously the search text carried over, leaving stale filter state in the newly activated view.

- **Pull no longer aborts on orphan save/state rows.** When RomM lists a save or
  state whose content blob is missing (HTTP 404 on `/content`), the file is
  skipped rather than crashing the entire pull. These orphans are reported as a
  separate *Missing on RomM* count — kept distinct from genuine local write
  *failures* so a server-side orphan no longer looks like the pull broke. Auth
  errors (401/403) and server errors (5xx) still surface as hard failures.

### Added

- **Detail panel redesign.** The Detail panel now shows a rich layout: cover art
  (200 px image header, with screenshot replacing it once loaded off-thread), a
  clean title with parenthetical tags stripped, colored tag chips for regions
  (with flag emojis), languages, revision, and tags in a wrapping FlowLayout,
  the human-readable platform name, and a scrollable metadata/summary block —
  with action buttons pinned at the bottom. File list removed.

- **Game Detail panel.** Clicking a game tile (body, not the checkbox) opens a
  Detail panel docked to the right of the library grid. It shows name,
  platform, and file list instantly, then fills in RomM-fetched metadata
  (summary, release date, genres, file size) off the UI thread. Results are
  cached per game so switching between titles is instant. A close button
  dismisses the panel without affecting the library.
- **Tile checkbox/body split.** The checkbox now selects only when clicked
  directly; clicking anywhere else on the tile opens the Detail panel. Batch
  selection behavior is unchanged.
- **Per-game actions — context menu and Detail panel buttons.** Right-clicking
  a tile and the Detail panel both expose the same set of actions:
  - *Download* (or *Re-download* when already on disk) — single-game download
    reusing the existing download worker.
  - *Open in RomM* — opens the game's page in the system browser.
  - *Open containing folder* — opens the game's on-disk directory in the file
    manager; disabled when the game is not downloaded.
- **Per-game Pull savegames.** A *Pull savegames* action in both the context
  menu and Detail panel downloads saves and savestates for one game from RomM
  — no need to run a full pull. Works whether or not the game is downloaded
  locally; files land in the configured saves/states directories. When a local
  file differs from the RomM copy, a per-file conflict dialog shows both
  timestamps (remote vs. local) so you can choose to keep the local version or
  take the remote one.

## [v0.1.4] — 2026-06-17

### Added

- **Always-on diagnostic logging.** romhop now keeps a rotating log file (INFO
  level, 1 MB × 5 files) under your OS log directory with no setup required, so
  remote bug reports finally come with context. Sensitive data is redacted
  automatically: API tokens and `Authorization` headers are stripped, your RomM
  host is masked, and your home path is shortened to `~`. Use `-v`/`--verbose`
  on the CLI to raise everything to DEBUG and echo to the terminal.
- **Logging controls in Settings.** A new logging section in the GUI lets you
  toggle *Detailed logging (debug)* live, *Open log folder* in your file
  manager, and *Export logs…* to bundle the current and rotated logs into a zip
  for sharing.

### Fixed

- **Ctrl-C now exits the GUI cleanly from a terminal.** Previously a forced
  second Ctrl-C could tear down Qt mid-state and segfault. A SIGINT handler now
  schedules a graceful quit (stopping the sync worker and removing the tray
  icon).
- **Update installer is no longer run unverified.** If the release is missing
  its `SHA256SUMS`, the updater now refuses to download instead of silently
  executing an unverified installer.
- **Fixed update-worker thread leaks.** Repeated update checks or clicks could
  orphan a `QThread`, and the worker also leaked on app exit; workers are now
  stopped before reassignment and during shutdown.
- Internal code-quality cleanups in the updater and main window
  (module-level loggers, explicit type errors, signal type alignment).
