---
id: TASK-007
title: Tray close hint ignores sync-off state
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
labels:
  - bug
  - gui
dependencies: []
priority: low
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The close-to-tray balloon hardcodes 'Still running — save-sync active.' (src/romhop/gui/main_window.py:292) even when sync_enabled is off, which is misleading. Branch the message on the current sync state.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Balloon message reflects sync_enabled state (active vs idle)
<!-- AC:END -->
