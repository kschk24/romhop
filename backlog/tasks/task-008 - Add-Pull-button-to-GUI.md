---
id: TASK-008
title: Add Pull button to GUI
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-16 15:59'
labels:
  - feature
  - gui
dependencies: []
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a Pull button to the GUI that calls pull.py to restore saves/states for all selected games. Inject pull as a callable in app.run(), run it on an off-thread worker, feed it selected_roms, and surface the conflict-resolution dialog.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pull button visible in GUI and enabled when games are selected
- [ ] #2 Clicking Pull restores saves/states for all selected games via pull.py
- [ ] #3 Pull runs off the UI thread (worker), GUI stays responsive
- [ ] #4 Conflict-resolution surfaced to user
- [ ] #5 pull injected as a callable in app.run() (widgets do not import backend)
- [ ] #6 pull acts like in cli, so overwriting saveguards/ user prompts work in gui aswell
<!-- AC:END -->
