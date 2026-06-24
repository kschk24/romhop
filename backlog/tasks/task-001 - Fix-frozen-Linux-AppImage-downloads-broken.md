---
id: TASK-001
title: Validate roms_root before download; friendly error instead of raw traceback
status: Done
assignee:
  - '@claude'
created_date: '2026-06-16 15:03'
updated_date: '2026-06-24 14:19'
labels:
  - bug
  - ready-for-agent
dependencies: []
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Downloads are NOT broken in the frozen build — earlier 'frozen Linux downloads broken' diagnosis was wrong. Real cause: user had roms_root set to an unwritable/nonexistent path (/home/Games/Emulator), so download_rom's system_dir.mkdir(parents=True) raised PermissionError: [Errno 13] Permission denied: '/home/Games' and dumped a raw Rich traceback. romhop never checks roms_root is set to a usable (existing-or-creatable, writable) directory and gives no friendly feedback. Affects CLI download and GUI (silent failure in worker thread).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 download_rom / pre-download path validates roms_root is usable (creatable + writable) before streaming
- [x] #2 Unusable roms_root yields a clear actionable error (which path, why) — no raw traceback in CLI
- [x] #3 GUI surfaces the same error to the user instead of failing silently in the worker
- [x] #4 Setup wizard / settings ideally validate roms_root writability when set
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add config.roms_root_problem(path) -> str|None: actionable msg if roms_root unset/nonexistent-parent/not-writable, walking to nearest existing ancestor + os.access check.
2. download.py: add RomsRootError; download_rom pre-checks roms_root_problem before mkdir, raises RomsRootError(msg). friendly_download_error maps it.
3. cli.download: echo problem + Exit(1) instead of raw traceback.
4. GUI download_action already wraps Exception->friendly_download_error->RuntimeError; RomsRootError msg flows through to UI.
5. Setup wizard + settings: validate roms_root writability when set (AC#4).
6. TDD: tests in test_config.py (roms_root_problem) + test_download.py (RomsRootError raised, no mkdir traceback).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done: config.roms_root_problem() (nearest-existing-ancestor + os.access W_OK|X_OK). download_rom pre-checks → raises RomsRootError; friendly_download_error maps it. CLI download echoes msg + Exit(1), no traceback. GUI download_action already wraps Exception→friendly_download_error→RuntimeError so RomsRootError msg surfaces. Setup wizard accept() blocks Finish + QMessageBox warn; settings_view _on_save warns (non-blocking). Tests: test_config (4), test_download (2), test_cli (1 friendly exit), test_gui_setup_wizard (1 block). Full suite 577 pass.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-06-16 15:44
---
Diagnosis 2026-06-16: reproduced via 'romhop download "Sonic Advance 2"'. roms_root was /home/Games/Emulator/gba. Traceback chain: download.py:117 system_dir.mkdir(parents=True, exist_ok=True) -> pathlib mkdir recursion up to /home/Games -> PermissionError [Errno 13] Permission denied: '/home/Games'. So the frozen build downloads fine; this was a config/path-validation + error-UX bug, not a packaging/TLS bug. Repurposed from old 'frozen Linux AppImage downloads broken / certifi' framing.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added config.roms_root_problem() validating roms_root is a creatable+writable dir (nearest-existing-ancestor + os.access). download_rom pre-checks and raises new RomsRootError instead of a raw mkdir PermissionError; friendly_download_error maps it. CLI download exits 1 with the actionable message (no traceback); GUI surfaces it via the existing friendly_download_error wrap. Setup wizard blocks Finish and settings dialog warns on an unusable folder. Verified: 577 tests pass (8 new).
<!-- SECTION:FINAL_SUMMARY:END -->
