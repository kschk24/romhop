---
id: TASK-016
title: Start on login (autostart) toggle
status: Done
assignee:
  - '@claude'
created_date: '2026-06-16 15:07'
updated_date: '2026-06-25 16:43'
labels:
  - feature
  - ready-for-agent
dependencies: []
priority: low
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A 'Start on login' toggle that auto-launches romhop to tray at boot. Per-OS: Windows (registry Run key / Startup folder) vs Linux (~/.config/autostart/*.desktop). Separate feature from close-to-tray; deferred 2026-06-15 during the background-sync-tray design.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Settings toggle to enable/disable start-on-login
- [x] #2 Enabling registers autostart on Windows (Run key/Startup) and Linux (~/.config/autostart)
- [x] #3 Disabling removes the autostart entry
- [x] #4 Autostart launches to tray
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. New Qt-free src/romhop/gui/autostart.py (stdlib only, mirrors launcher_install.py): _launch_command() -> frozen? sys.executable : launcher_path(), append --tray. Linux: ~/.config/autostart/romhop.desktop (XDG_CONFIG_HOME aware, home param for tests); enable writes desktop entry w/ X-GNOME-Autostart-enabled=true, disable unlinks, is_enabled=path.exists(). Windows: winreg HKCU\\...\\Run value 'RomHop'; enable/disable/is_enabled via winreg. set_enabled(bool) + is_enabled() dispatch by os.name.
2. config.py: add start_on_login: bool = False to Settings + FieldSpec('start_on_login','behavior','Start on login','bool', help) (ini source of truth, bool coerce/format already handled).
3. app.py run(): parse --tray from argv -> start hidden to tray (skip window.show() when configured + tray available; fall back to show if no tray). apply_settings closure: diff start_on_login like debug_logging -> autostart.set_enabled best-effort (try/except).
4. Tests (TDD): tests/test_autostart.py — launch command builder, Linux enable/disable/is_enabled via tmp home, Windows path skipif os.name!='nt'. config round-trip for new field. apply_settings side-effect (monkeypatch autostart).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: new Qt-free gui/autostart.py (Linux XDG ~/.config/autostart/romhop.desktop + Windows winreg HKCU Run key, launch cmd = frozen sys.executable / pip launcher_path + --tray). config: start_on_login bool field + behavior FieldSpec (ini source of truth). app.py: _wants_tray(argv) starts hidden to tray when configured+tray available; apply_settings closure -> _apply_autostart diff registers/unregisters best-effort. Tests: tests/test_autostart.py (8 pass +1 win-skip), config roundtrip, _wants_tray/_apply_autostart unit tests. Full suite 591 pass / 1 skip. CHANGELOG Unreleased updated.
<!-- SECTION:NOTES:END -->
