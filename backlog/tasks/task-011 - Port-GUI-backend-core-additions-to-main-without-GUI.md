---
id: TASK-011
title: Port GUI backend-core additions to main without GUI
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
labels:
  - chore
  - refactor
dependencies: []
priority: low
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Deferred plan to port the backend additions made on gui-desktop-pyside into main without the GUI layer: sync stop_event, config sync_enabled/theme fields, romm_client url_cover/download_cover. Plan file lives in ~/.claude/plans/. Goal: keep main's Qt-free core current with GUI-branch backend work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 sync stop_event support ported to main
- [ ] #2 config sync_enabled + theme fields ported to main
- [ ] #3 romm_client url_cover + download_cover ported to main
- [ ] #4 No PySide6 imports leak into main core
<!-- AC:END -->
