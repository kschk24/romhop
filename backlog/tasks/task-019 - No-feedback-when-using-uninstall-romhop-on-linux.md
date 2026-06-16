---
id: TASK-019
title: No feedback when using uninstall romhop on linux
status: Done
assignee: []
created_date: '2026-06-16 16:13'
updated_date: '2026-06-16 21:57'
labels:
  - bug
dependencies: []
priority: low
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
it works perfectly fine, the tool dissappears from search but there is no feedback, just a click on uninstall and its gone
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added _notify_uninstalled() QMessageBox in gui/app.py, called after removal in _maybe_uninstall — Terminal=false launcher now shows visible completion dialog. Dispatch tests assert it fires. 369 suite green.
<!-- SECTION:NOTES:END -->
