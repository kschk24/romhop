---
id: TASK-005
title: Frozen Windows download progress bar does not render
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
labels:
  - bug
  - gui
  - packaging
  - windows
dependencies: []
priority: medium
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the frozen Windows build the download runs fine but the bottom-bar QProgressBar does not render and the status label is clipped on the left (shows 'nimal Crossing' instead of 'Animal Crossing'). UI/layout bug specific to the frozen build; works in source runs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Bottom-bar progress bar renders during download in frozen Windows build
- [ ] #2 Status label shows full game name, not clipped
<!-- AC:END -->
