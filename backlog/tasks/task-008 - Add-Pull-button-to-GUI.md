---
id: TASK-008
title: Add Pull button to GUI
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-16 15:04'
updated_date: '2026-06-23 12:58'
labels:
  - feature
  - ready-for-agent
dependencies:
  - TASK-035
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a Pull button to the GUI that calls pull.py to restore saves/states for all selected games. Inject pull as a callable in app.run(), run it on an off-thread worker, feed it selected_roms, and surface the conflict-resolution dialog.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pull button visible in GUI and enabled when games are selected
- [x] #2 Clicking Pull restores saves/states for all selected games via pull.py
- [x] #3 Pull runs off the UI thread (worker), GUI stays responsive
- [x] #4 Conflict-resolution surfaced to user
- [x] #5 pull injected as a callable in app.run() (widgets do not import backend)
- [x] #6 pull acts like in cli, so overwriting saveguards/ user prompts work in gui aswell
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. app.py: rework pull_action(rom,on_conflict) -> pull_action(roms,on_conflict); build one _Shim per rom; single pull_games(client, shims, s, on_conflict=...) call.
2. main_window.py: add pull_btn QPushButton("Pull saves") after download_btn in bottom row; wire clicked -> _pull_selected.
3. main_window.py: _pull_selected(): read selected_roms(), no-op if empty; guard against a second concurrent BULK pull (ignore click while a bulk worker live); set button "Pulling…"+disable; one PullWorker(lambda oc: self._pull_action(selected, oc)); reuse existing _on_pull_conflict/_on_pull_done/_on_pull_failed; restore button via worker.finished. NO enable-gate (always enabled, mirrors download).
4. main_window.py: _pull_one now calls _pull_action([rom], on_conflict) (list of one).
5. main_window.py: add pull_btn.show()/.hide() alongside download_btn in show_library/show_settings/show_activity_log.
6. Reuse PullConflictDialog per-file prompt (single worker streams conflicts sequentially -> per-game/per-file choice intact). Final summary QMessageBox only, no progress. No take-all toggle.
7. tests/test_gui_views.py: (a) bulk dispatch passes full selected list to pull_action; (b) empty selection no-ops; (c) view parity pull_btn hidden after show_settings/show_activity_log, visible after show_library. Stub QMessageBox.information / PullConflictDialog.ask.
Note: AC#1 "enabled when selected" read as satisfied via always-enabled per user decision (drop enable-gate); reword AC at finalization if needed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented bulk Pull button. app.py pull_action now takes a roms LIST (shim per rom, single pull_games call). main_window.py: pull_btn in bottom bar, _pull_selected (single PullWorker over whole selection, guards 2nd concurrent bulk, "Pulling…" busy state restored via worker.finished), _pull_one now passes [rom], show/hide parity in show_library/settings/activity. Reuses PullWorker + PullConflictDialog + existing handlers untouched (per-file conflict prompts preserved). 3 new tests in test_gui_views.py (bulk dispatch / empty no-op / view parity). Full suite 506 passed. AC#1 enable-gate intentionally dropped per user — pull_btn always enabled, mirrors download_btn.
<!-- SECTION:NOTES:END -->
