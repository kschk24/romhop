---
id: TASK-013.01
title: Bottom-right transient toast on successful sync push
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
labels:
  - feature
  - gui
dependencies: []
parent_task_id: TASK-013
priority: low
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Show a transient bottom-right notification in the GUI when a save sync push succeeds. Cheap: watch_and_push already exposes on_event; just wire it to a transient widget.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Successful sync push shows a transient bottom-right toast in the GUI
- [ ] #2 Toast wired via existing watch_and_push on_event hook
<!-- AC:END -->
