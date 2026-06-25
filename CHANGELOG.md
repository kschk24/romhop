# Changelog

All notable changes to romhop are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [Unreleased]

### Added

- **GUI Upload dialog — standalone "Upload local games to RomM" button (TASK-057.03).** Settings gains an "Upload local games to RomM" button alongside Scan (disabled when `roms_root` unset). Clicking it runs the match off-thread (discovery-only — no cache seeding) then opens a new `UploadDialog` populated from `discover_uploadable`. The dialog has a platform-filter dropdown, sort dropdown (Platform / Name), select-all/none buttons, and per-game checkboxes (unchecked by default). `missing_platform` rows show an inline "Create platform" button that creates the platform and enables the checkbox; `unresolvable` rows are disabled with a tooltip. Upload runs via the existing `UploadWorker`/`run_upload_batch` plumbing. The interrupted-upload recovery message now mentions "upload" as an alternative to re-running scan.

- **`romhop upload` standalone command (TASK-057.02).** New top-level `upload` command mirrors `download`: variadic name arguments do substring match against local unmatched game names, `--platform` (repeatable, case-insensitive) filters by ES-DE system dir, `--yes/-y` skips all interactive prompts. Runs the RomM match internally (discovery-only — no cache seeding for matched games; only uploaded games are seeded via `run_upload_batch`). Interactive InquirerPy checkbox picker groups entries by system dir, with `ctrl+a` select-all and default-unchecked; falls back to all-or-confirm when InquirerPy is unavailable or stdin is non-TTY. Full parity with the scan-path upload: missing-platform create offer, unresolvable-with-reason display, and `upload_session.recover()` on entry (broadened interrupted-upload message mentions `upload` as an alternative to re-running `scan`).

- **`discover_uploadable` Qt-free core seam extracted from CLI (TASK-057.01).** The categorization logic (resolvable / missing_platform / unresolvable) that was inline in `cli._run_upload_unmatched` now lives in `upload.discover_uploadable(local_games, romm_platforms, overrides) -> UploadCandidates`. `_run_upload_unmatched` is refactored to call it; behavior is unchanged. Both the future standalone `upload` command and the GUI upload dialog will share this seam.

- **`romhop download` accepts multiple names and uses InquirerPy for ambiguous matches (TASK-043).** `download` now takes one or more name arguments and downloads them as a single sequential batch (mirroring the GUI). For each term, an exact or unique substring match feeds the batch directly; an ambiguous term opens an InquirerPy checkbox multi-select when stdin is a tty (no picker in non-interactive mode — exits 2 unchanged). Batch continues past network/HTTP failures; a summary line (`Downloaded N, skipped M (already local), failed K`) is printed at the end and the exit code is 1 if any game failed, 0 otherwise. `romhop pull` gains the same ambiguous-match multi-select for tty sessions; `--all` and non-tty exit-2 behavior unchanged. (`TASK-043`)

- **Start on login (autostart) toggle (TASK-016).** A new "Start on login" checkbox in Settings → Behavior registers romhop to auto-launch at boot, starting hidden in the system tray (`--tray`). New Qt-free `gui/autostart.py` writes an XDG `~/.config/autostart/romhop.desktop` entry on Linux and an `HKCU\…\Run` registry value on Windows; the autostart command is the frozen executable (or the pip `romhop-gui` launcher) plus `--tray`. The flag is a normal `start_on_login` setting (ini is the source of truth, like `sync_enabled`); the OS entry is registered/unregistered on save (best-effort — a registry/file failure logs a warning and never breaks saving). Launching with `--tray` keeps the window hidden behind the tray icon when configured, falling back to showing the window if no tray is available or a startup library load fails. (`TASK-016`)
- **`FieldSpec` gains `choice` type + `options` tuple; `Settings.theme_mode` added (TASK-050).** `FieldSpec` now has an `options: tuple[str, ...]` field (default empty) for enumerated choices. `coerce_value` handles `'choice'` by returning the raw string. `Settings.theme_mode` defaults to `'system'` and round-trips via the ini; the old free-text `theme` SCHEMA entry is replaced by a `choice` field with options `(system, light, dark)`. The `theme` dataclass attr is retained as a reserved field but is no longer persisted.

- **`theme.resolve_scheme` and `scheme_theme_dir` helpers (TASK-051).** `resolve_scheme(mode, app)` converts a `theme_mode` string to `'light'` or `'dark'`: forced modes pass through; `'system'` reads `QStyleHints.colorScheme()` (Unknown → dark). `scheme_theme_dir(scheme)` maps the resolved scheme to the correct bundled theme directory (`themes/light` or `themes/default`).

- **Bundled light theme and shared dialog/wizard QSS rules (TASK-052).** A new `themes/light/` bundle ships with a light-palette `tokens.json`. `base.qss` gains explicit `QDialog`, `QWizard` / `QFrame` child, and `QDialogButtonBox` background rules so dialogs and wizards inherit the active theme palette on all platforms.

- **Settings view renders `choice` fields as `QComboBox` (TASK-054).** `_make_widget` now detects `FieldSpec.type == 'choice'` and builds a `QComboBox` populated from `FieldSpec.options`; `_populate` selects the current value by string; `_read_widget` returns `currentText()`. The theme-mode row in Settings now shows a drop-down (System / Light / Dark) instead of a free-text field.

- **Upload unmatched local games to RomM (TASK-014).** Scan's Unmatched report becomes an action: GUI `ScanResultDialog` gains per-row checkboxes and an "Upload selected" button; CLI `romhop scan --upload-unmatched` adds an InquirerPy interactive checklist (falls back to a prompt when not on a TTY). Each game's ES-DE system dir is resolved to a RomM platform (inverted from `platform_map`); missing platforms are offered for auto-creation (user confirms before any POST). Uploads stream each real rom file as a bare leaf via the chunked flow (`.m3u`/`.txt` artifacts excluded). After upload, a Socket.IO quick scan materialises the files; on connect failure, a basic mapping entry is seeded and the user is told to scan in RomM. A `RomAlreadyExists` 400 from upload/start becomes a skip, not an error. The scan timeout is configurable via a new `scan_timeout_seconds` setting (default 120 s). New `UploadWorker` mirrors `DownloadWorker` (per-item progress, error, cancel, continue-on-error). New `InquirerPy` runtime dependency.

- **`RommClient` gains upload, platform-create, and scan-trigger capability (TASK-044).** `upload_rom` streams a rom file from disk via the chunked `start→PUT→complete` flow (no whole-file RAM), surfaces a `RomAlreadyExists` dedup signal on 400, and accepts a `stop_event` for cancellation. `create_platform` existence-checks before posting so no duplicate platforms are created. `trigger_scan` connects to RomM's Socket.IO endpoint (`/ws/socket.io`) and emits a platform-scoped quick scan, raising `ScanConnectError` on failure so callers can fall back to a hand-off. `find_roms_by_fs_names` locates materialized roms client-side after a scan. All write operations raise `InsufficientScopeError` on HTTP 403 naming the missing scope. Added `python-socketio[client]` dependency.

- **`local_index` is now disc-aware: flat `.cue`+`.bin` and `.m3u`+`.cue`+`.bin` layouts coalesce into one `LocalGame`.** Previously a flat single-disc PS1 game split into a `.cue` "game" plus orphan `.bin` "games" in the scan Unmatched report. `local_index` now parses `.cue` sheets for their referenced track files and `.m3u` playlists for their disc descriptors, coalescing the descriptor and all referenced files into a single `LocalGame`. Missing referenced files emit a warning rather than crashing. The coalesced `file_names` field carries every real rom file (`.cue`+`.bin`), excluding ES-DE artifacts (`.m3u`, `.txt`). (`TASK-045`)

- **Bulk "Pull saves" button in the GUI.** The library bottom bar now has a Pull
  button that restores saves/states for every selected game in one pass (off the
  UI thread), streaming the same per-file conflict prompt the CLI uses so local
  files are never overwritten without confirmation. (`TASK-008`)

- **Upload UX polish: `romhop scan` offers to upload + GUI shows a real upload progress bar (TASK-046).** Plain `romhop scan` (no `--upload-unmatched`) now prompts *"Upload N unmatched game(s) to RomM now?"* when run on a TTY and runs the existing upload flow on confirmation; `--upload-unmatched` stays as the non-interactive override and `--yes`/non-TTY never upload silently. The GUI `ScanResultDialog` upload bar is now determinate like the download bar: `upload_game` reports bytes cumulatively across all of a game's files plus a fixed total, `UploadWorker.item_progress` carries `(sent, total, speed)`, and the dialog renders a permille fill with a `name (i/n) · sent/total · rate` label (falling back to indeterminate when the total is unknown). (`TASK-046`)

- **Crash-safe upload sessions: orphan cleanup + interrupted-upload heads-up (TASK-048).** A hard kill mid-upload previously left orphan `upload_id`s staged on the RomM server and no record of the in-progress batch. New `upload_session.py` persists `{in_progress, active_uploads:[{upload_id, platform_id}]}` to `user_data_dir()/upload_session.json`. `RommClient.upload_rom` gains `on_session_start(upload_id)` / `on_session_end(upload_id)` callbacks (pure transport — no import of `upload_session`). `upload.py` exposes a new `run_upload_batch` that owns the session lifecycle: `set_in_progress` at batch start, bracket each file via the callbacks (add/remove the upload_id), `clear` on clean finish. `upload_session.recover(client)` reaps orphans via POST `.../cancel` (idempotent, 404-tolerant), reports whether the dirty flag was set, and clears the file. GUI calls `recover` at startup and emits an activity event if dirty; CLI calls it at the start of `scan`. `ScanResultDialog` no longer labels a cancelled batch "Upload complete" — a graceful cancel now shows "Cancelled" and logs "batch cancelled, N not uploaded". Known limitation: concurrent CLI `--upload-unmatched` + GUI = two writers; last-writer-wins; documented in the ticket.

### Fixed

- **Settings Save now shows a brief toast confirmation (TASK-041).** `_on_settings_saved` in `MainWindow` now posts an `ActivityEvent(SETTINGS_SAVED, "Settings saved")` through `_activity_hub`, which routes it to `ToastManager` as an info-style toast. `ActivityKind.SETTINGS_SAVED` was added to the enum; no new UI widgets introduced.

- **Download progress bar now renders in the frozen Windows build (TASK-005).** `base.qss` had no `QProgressBar` rule, so the bar relied on the native Qt style's default painting — invisible against the dark bottom bar when the frozen build falls back to a different style than source runs use. Added explicit token-colored `QProgressBar` / `QProgressBar::chunk` rules to the shared `base.qss` so every theme renders a visible bar regardless of the active Qt style.

- **Download status label no longer clips the game name in the frozen Windows build (TASK-005).** The bottom-bar `progress_label` had no size policy or alignment, so the frozen build's differing font metrics under-allocated its width and clipped the leading characters (e.g. "nimal Crossing"). It now uses `AlignLeft | AlignVCenter` and a `Minimum` horizontal size policy so the allocation is deterministic and the full name shows.

- **Setup wizard chrome now matches dark theme on Windows (TASK-006).** `SetupWizard.__init__` now explicitly sets `QWizard.WizardStyle.ClassicStyle`. On Windows the default is Aero/Modern style, which draws native header/footer bands that ignore application QSS and render light against the dark body. Forcing ClassicStyle makes those bands plain QWidgets styled by `base.qss`. No banner/watermark pixmaps are set, so no visual content is lost. The underlying root cause — the OS/frozen-build color scheme not being forced at app startup — is now fixed by `apply_theme` calling `QApplication.setColorScheme` (TASK-053/TASK-055); `ClassicStyle` is retained for style consistency.

- **Unusable ROMs folder now fails with a clear message, not a raw traceback (TASK-001).** A `roms_root` pointing at an unwritable or nonexistent path (e.g. `/home/Games/Emulator`) made `download_rom`'s `mkdir(parents=True)` raise `PermissionError: [Errno 13]` and dump a Rich traceback in the CLI / fail silently in the GUI worker. New `config.roms_root_problem()` walks to the nearest existing ancestor and checks it is a writable directory; `download_rom` pre-checks it and raises the new `RomsRootError` with an actionable message ("…is not writable — pick a folder you own"). The CLI `download` command surfaces that message and exits 1 (no traceback); the GUI routes it through `friendly_download_error` into the UI. The setup wizard blocks Finish and the settings dialog warns when the chosen ROMs folder isn't usable. (`TASK-001`)

- **Upload no longer crawls at ~1 MB/s (TASK-047).** The chunked upload sends each chunk as a synchronous PUT and waits the full server round-trip before the next, so throughput was capped at roughly one chunk per round-trip — with the old 1 MiB chunk that meant ~1.0 MB/s regardless of available bandwidth. The default chunk size is now 8 MiB (8× fewer round-trips) and is configurable via a new `upload_chunk_size_mb` setting, wired through `upload_game` → `RommClient.upload_rom`. Lower it if a strict reverse proxy rejects large request bodies. (`TASK-047`)

- **Installer download no longer buffers the full asset in RAM.** `update.py` previously accumulated all 65536-byte chunks into a list before writing to disk, holding a full AppImage/exe in memory. Chunks are now written directly to the `.part` temp file as they arrive, and the SHA-256 digest is computed incrementally during the same pass — eliminating both the in-memory accumulation and the post-write `path.read_bytes()` re-load that doubled peak RAM use. (`TASK-024`)

- **Windows "Installed Apps" now shows "RomHop", not "RomHop version …".** Inno
  was defaulting the uninstall display name to the product name plus the build
  version (which was the raw git ref, e.g. a branch slug like
  *packaging-freeze-installers*). The installer now pins the display name to
  `RomHop`, and the version is reported separately as a clean semver — tag
  builds strip the leading `v`, manual builds use the package `__version__` with
  a `-dev` suffix.

- **`romhop --help` now uses full terminal width on Windows.** Rich's `console.width` returned 80 in the PyInstaller `.exe` even on wider terminals; switched to `shutil.get_terminal_size()` which queries the OS directly, so the frog/body layout fills the real terminal width.

- **Game detail panel now hides when switching to Settings or Activity Log (TASK-042).** Previously the panel remained visible behind other screens when a tile was selected before navigating away. `show_settings` and `show_activity_log` now call `detail_panel.hide()`; returning to the library restores the panel only when a rom is already loaded. A new `DetailPanel.has_rom` property exposes the selection state cleanly.

### Changed

- **Download and update flows no longer share the progress bar without isolation (TASK-029).** `MainWindow` now tracks `_progress_owner` (`"download"` | `"update"` | `None`). `_claim_progress(owner)` / `_release_progress(owner)` are the only entry points for show/hide; stale callbacks from the losing flow early-return without touching the bar. Clicking "Update" while a download is running cancels the download first, then claims the bar. `_on_update_failed` releases the bar and re-enables the download button (previously the bar was left stuck at "Updating…"). `_start_download` is a no-op when the update flow owns the bar.

- **Qt plugin exclusions moved from `build_appimage.sh` post-hoc deletion to PyInstaller spec (TASK-028).** `libqtiff.so`, `libqjasper.so`, and `libqatspiplugin.so` are now filtered out in `romhop.spec` alongside `libxkbcommon`, so they are never bundled regardless of SONAME changes on the build host. The fragile `find … | xargs rm` block in `build_appimage.sh` is removed.

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

- **In-app Activity log panel (TASK-013.03).** New `gui/activity_log.py` adds `ActivityLogView`: a `QListWidget`-backed panel showing sync/download/error events newest-first, with timestamps and error rows highlighted in red. Accessible via an "Activity" button in the bottom bar; toggling it opens/closes the panel as a third page in the central `QStackedWidget`. On open it populates from `ActivityHub`'s 200-event ring buffer and live-appends new events while visible. Session-only — nothing written to disk.

- **Opt-in OS desktop notifications for activity events (TASK-013.02).** New `desktop_notifications` bool setting (Behavior group, default off) fires `tray.showMessage` for sync pushes, completed downloads, and errors. Focus-gated: suppressed when romhop is the active window so the toast already covers it. The toggle is shown disabled with a hint when no system tray is available.

- **Toast notifications for sync/download/error activity (TASK-013.01).** New `gui/toast.py` adds a `ToastWidget` (frameless child overlay, word-wrapped message, ×-dismiss button) and `ToastManager` (capped stack of 3 above the bottom bar, bottom-right). Info toasts auto-dismiss after 4 s; error toasts are sticky until clicked. `MainWindow` subscribes `ActivityHub.event` to `ToastManager.post` and repositions the stack on resize. Fires for all three activity kinds.

- **Activity event model + hub foundation (TASK-013.04).** New Qt-free `activity.py` module defines `ActivityKind` (`SYNC_PUSH`, `DOWNLOAD_DONE`, `ERROR`) and a frozen `ActivityEvent` dataclass with pre-rendered message and tz-aware timestamp. `sync.py` now emits `SYNC_PUSH` events via `on_event`; `download.py` emits `DOWNLOAD_DONE` on successful write. `ActivityHub` QObject (owned by `MainWindow`) aggregates events from all worker threads via queued signals into a capped 200-event ring buffer — the shared source all three activity renderers (toast/.01, desktop notif/.02, log/.03) will read from.

- **Detail panel redesign.** The Detail panel now shows a rich layout: cover art
  (200 px image header, with screenshot replacing it once loaded off-thread), a
  clean title with parenthetical tags stripped, colored tag chips for regions
  (with flag emojis), languages, revision, and tags in a wrapping FlowLayout,
  the human-readable platform name, and a scrollable metadata/summary block —
  with action buttons pinned at the bottom. File list removed.

- **App-level theming: theme applied at startup, on save, and on OS scheme change (TASK-055).** `app.run()` calls `theme.apply_theme(app, settings)` immediately after `QApplication` is created, so every top-level window is styled before any widget appears. `colorSchemeChanged` is connected to re-apply the theme live when the OS color scheme changes (relevant in `system` mode). `apply_settings` also re-applies the theme on settings save so a mode change takes effect without a restart. `MainWindow` no longer sets its own stylesheet — per-window `self.setStyleSheet` and the now-unused `theme` import are removed.

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
