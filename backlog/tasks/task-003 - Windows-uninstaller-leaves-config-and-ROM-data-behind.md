---
id: TASK-003
title: Windows uninstaller leaves config and ROM data behind
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
updated_date: '2026-06-16 16:54'
labels:
  - bug
  - packaging
  - windows
dependencies: []
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Inno Setup uninstaller leaves config plus downloaded ROM data on disk with no wipe prompt. Add an opt-in MsgBox prompt + UninstallDelete entries, mirroring the existing Linux uninstall behaviour.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Uninstaller offers opt-in prompt to remove config + downloaded data
- [ ] #2 Choosing to wipe removes config and ROM data dirs
- [ ] #3 Behaviour mirrors Linux uninstall flow
<!-- AC:END -->
