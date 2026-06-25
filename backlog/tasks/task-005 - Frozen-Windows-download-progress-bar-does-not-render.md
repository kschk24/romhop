---
id: TASK-005
title: Frozen Windows download progress bar does not render
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
updated_date: '2026-06-24 15:03'
labels:
  - bug
  - ready-for-human
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Code complete on branch fix/windows-frozen-gui-theme (commits 68806b5 QProgressBar QSS + 36a974f progress_label size policy/align). Frozen Windows smoke 2026-06-24: wizard verified (TASK-006), but download bar+label NOT yet tested. Remaining acceptance: start a download in the frozen build, confirm AC#1 bottom-bar progress bar renders + AC#2 full game name shows (not clipped).
<!-- SECTION:NOTES:END -->
