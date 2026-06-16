---
id: TASK-010
title: Auto-update for frozen installers (tufup)
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
labels:
  - feature
  - packaging
dependencies: []
priority: low
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sub-project 2/2 of the freeze-installers packaging effort: wire tufup-based auto-update into the frozen PyInstaller builds so end users get updates without manual reinstall. Sub-project 1 (frozen installers) already shipped and merged to gui-desktop-pyside.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Frozen build checks for and applies updates via tufup
- [ ] #2 Update flow works on Windows and Linux frozen builds
<!-- AC:END -->
