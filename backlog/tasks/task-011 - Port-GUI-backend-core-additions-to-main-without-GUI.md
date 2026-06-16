---
id: TASK-011
title: Port GUI backend-core additions to main without GUI
status: Done
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-16 17:52'
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
- [x] #1 sync stop_event support ported to main
- [x] #2 config sync_enabled + theme fields ported to main
- [x] #3 romm_client url_cover + download_cover ported to main
- [x] #4 No PySide6 imports leak into main core
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Superseded by merging gui-desktop-pyside into main: the full-branch merge lands all backend-core additions (sync stop_event, config sync_enabled/theme, romm_client url_cover/download_cover) directly in main. Standalone GUI-free port no longer needed.
<!-- SECTION:NOTES:END -->
