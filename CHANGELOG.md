# Changelog

All notable changes to romhop are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

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
