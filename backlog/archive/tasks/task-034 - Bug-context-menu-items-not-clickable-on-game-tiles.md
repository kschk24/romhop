---
id: TASK-034
title: 'Bug: context menu items and DetailPanel action buttons not clickable'
status: To Do
assignee: []
created_date: '2026-06-17 15:18'
updated_date: '2026-06-17 15:19'
labels:
  - bug
  - gui
  - detail-panel
dependencies: []
priority: high
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Right-click context menu on game tiles shows options but none are clickable/functional. Same issue affects action buttons in the DetailPanel sidebar — all buttons render but trigger no response when clicked. Both surfaces share the same broken wiring.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All context menu actions (Download, Open in RomM, Open folder, Pull savegames, etc.) respond to click
- [ ] #2 Clicking a menu item executes the expected action
- [ ] #3 No silent failures — error shown if action cannot complete
- [ ] #4 All context menu actions respond to click
- [ ] #5 All DetailPanel sidebar action buttons respond to click
- [ ] #6 Clicking executes the expected action on the selected game
- [ ] #7 No silent failures — error shown if action cannot complete
<!-- AC:END -->
