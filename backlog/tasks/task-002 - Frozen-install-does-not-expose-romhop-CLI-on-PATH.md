---
id: TASK-002
title: Frozen install does not expose romhop CLI on PATH
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-16 15:03'
updated_date: '2026-06-16 17:04'
labels:
  - bug
  - packaging
dependencies: []
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frozen per-user installs (Linux AppImage + Windows Inno) ship the GUI only; the 'romhop' CLI is not available on PATH after install. Confirmed on Windows 2026-06-16. Users who want the CLI cannot reach it from a frozen install.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 romhop CLI invocable after a frozen install on Linux
- [ ] #2 romhop CLI invocable after a frozen install on Windows
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Root cause: frozen bundle ships ONE PyInstaller exe (entry_gui.py -> gui.run); CLI romhop.cli:app has no exe entry, and install dirs (~/.local/lib/romhop, %LOCALAPPDATA%\Programs\romhop) are not on PATH.
Approach (user-approved): single dispatching exe + per-OS native PATH.
1. New src/romhop/frozen_dispatch.py (Qt-free, lazy imports): is_cli_invocation(argv) -> argv[1] present & not a GUI-only flag (--uninstall/--appimage-bootstrap/--smoke-exit); main() routes to romhop.cli:app (CLI) else gui.app.run (GUI); _attach_console_windows() reopens CONOUT$ so console=False exe still prints on Win.
2. packaging/entry.py replaces entry_gui.py -> frozen_dispatch.main; romhop.spec points at entry.py + hiddenimports romhop.cli.
3. install_bootstrap.py: cli_link_path/link_cli/unlink_cli (Linux ~/.local/bin/romhop symlink -> installed exe). app._maybe_bootstrap calls link_cli; _maybe_uninstall calls unlink_cli.
4. romhop.iss: ChangesEnvironment=yes + [Registry] HKCU Environment Path append {app} with [Code] NeedsAddPath dedupe + uninstall removal.
5. Tests: frozen_dispatch routing; link_cli/unlink_cli.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented (gui-desktop-pyside, uncommitted):
- src/romhop/frozen_dispatch.py: is_cli_invocation/main/_attach_console_windows. Single frozen exe routes bare->GUI, args->Typer CLI. Qt-free lazy imports. Windows reopens CONOUT$ so console=False exe still prints.
- packaging/entry.py replaces entry_gui.py (removed); romhop.spec -> entry.py, hiddenimports +romhop.cli, header comment updated.
- install_bootstrap.py: cli_link_path/link_cli/unlink_cli (~/.local/bin/romhop symlink). app._maybe_bootstrap links after install; _maybe_uninstall unlinks.
- romhop.iss: ChangesEnvironment=yes, [Registry] append {app} to HKCU Path w/ NeedsAddPath dedupe, [Code] CurUninstallStepChanged strips it on uninstall.
Tests: tests/test_frozen_dispatch.py (9 routing + 2 main cases) + 5 link/unlink cases in test_install_bootstrap.py. 360 passed (1 pre-existing unrelated fail: romhop-gui not pip-installed in venv).
AC verification PENDING manual smoke: needs real PyInstaller build + frozen install on Linux (AC#1) and Windows (AC#2) — console-attach + Inno PATH not auto-testable on Linux CI.

AC#1 VERIFIED on real local AppImage build (2026-06-16):
- pyinstaller romhop.spec + build_appimage.sh -> dist/romhop-installer-0.1.0-x86_64.AppImage built clean.
- frozen exe 'romhop --help' / 'config path' dispatch to Typer CLI (exit 0).
- --appimage-bootstrap install (isolated HOME) populates ~/.local/lib/romhop, creates ~/.local/bin/romhop symlink -> installed exe + desktop entries.
- CLI invoked through the symlink works (config path returns config path under HOME, exit 0).
- --uninstall removes the symlink AND install dir ('romhop uninstalled', exit 0).
AC#2 (Windows Inno PATH) still needs Windows smoke.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Kilian
created: 2026-06-16 17:04
---
Windows smoke still outstanding, can be moved into done when verified
---
<!-- COMMENTS:END -->
