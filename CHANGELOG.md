# Changelog

All notable changes to romhop are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [Unreleased]

### Fixed

- **Installer download no longer buffers the full asset in RAM.** `update.py` previously accumulated all 65536-byte chunks into a list before writing to disk, holding a full AppImage/exe in memory. Chunks are now written directly to the `.part` temp file as they arrive, and the SHA-256 digest is computed incrementally during the same pass — eliminating both the in-memory accumulation and the post-write `path.read_bytes()` re-load that doubled peak RAM use. (`TASK-024`)

- **Windows "Installed Apps" now shows "RomHop", not "RomHop version …".** Inno
  was defaulting the uninstall display name to the product name plus the build
  version (which was the raw git ref, e.g. a branch slug like
  *packaging-freeze-installers*). The installer now pins the display name to
  `RomHop`, and the version is reported separately as a clean semver — tag
  builds strip the leading `v`, manual builds use the package `__version__` with
  a `-dev` suffix.

- **`romhop --help` now uses full terminal width on Windows.** Rich's `console.width` returned 80 in the PyInstaller `.exe` even on wider terminals; switched to `shutil.get_terminal_size()` which queries the OS directly, so the frog/body layout fills the real terminal width.

- **DetailPanel image header no longer flips or flashes between cover and screenshot.** Both loaders raced for the same slot, so the displayed image was nondeterministic and re-clicking flashed cover→screenshot every time. Games with a screenshot now load only the screenshot (no cover-upgrade flash), and loaded images are cached per game so re-selecting one re-displays it instantly instead of blanking to a placeholder and reloading.

- **DetailPanel sidebar now stays a fixed 300 px wide.** Previously the panel resized with each game selection as word-wrapped labels responded to varying content; long descriptions, summaries, and file lists now scroll inside the panel rather than pushing it wider or taller.

- **Search bar clears when switching between library and settings views.** Previously the search text carried over, leaving stale filter state in the newly activated view.

- **Pull no longer aborts on orphan save/state rows.** When RomM lists a save or
  state whose content blob is missing (HTTP 404 on `/content`), the file is
  skipped rather than crashing the entire pull. These orphans are reported as a
  separate *Missing on RomM* count — kept distinct from genuine local write
  *failures* so a server-side orphan no longer looks like the pull broke. Auth
  errors (401/403) and server errors (5xx) still surface as hard failures.

### Added

- **Opt-in OS desktop notifications for activity events (TASK-013.02).** New `desktop_notifications` bool setting (Behavior group, default off) fires `tray.showMessage` for sync pushes, completed downloads, and errors. Focus-gated: suppressed when romhop is the active window so the toast already covers it. The toggle is shown disabled with a hint when no system tray is available.

- **Toast notifications for sync/download/error activity (TASK-013.01).** New `gui/toast.py` adds a `ToastWidget` (frameless child overlay, word-wrapped message, ×-dismiss button) and `ToastManager` (capped stack of 3 above the bottom bar, bottom-right). Info toasts auto-dismiss after 4 s; error toasts are sticky until clicked. `MainWindow` subscribes `ActivityHub.event` to `ToastManager.post` and repositions the stack on resize. Fires for all three activity kinds.

- **Activity event model + hub foundation (TASK-013.04).** New Qt-free `activity.py` module defines `ActivityKind` (`SYNC_PUSH`, `DOWNLOAD_DONE`, `ERROR`) and a frozen `ActivityEvent` dataclass with pre-rendered message and tz-aware timestamp. `sync.py` now emits `SYNC_PUSH` events via `on_event`; `download.py` emits `DOWNLOAD_DONE` on successful write. `ActivityHub` QObject (owned by `MainWindow`) aggregates events from all worker threads via queued signals into a capped 200-event ring buffer — the shared source all three activity renderers (toast/.01, desktop notif/.02, log/.03) will read from.

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
