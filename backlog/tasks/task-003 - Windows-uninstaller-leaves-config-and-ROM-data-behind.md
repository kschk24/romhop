---
id: TASK-003
title: Windows uninstaller leaves config and ROM data behind
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-16 15:03'
updated_date: '2026-06-16 17:13'
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
- [x] #1 Uninstaller offers opt-in prompt to remove config + downloaded data
- [x] #2 Choosing to wipe removes config and ROM data dirs
- [x] #3 Behaviour mirrors Linux uninstall flow
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Wipe = config dir (settings.ini) + user_data_dir (mapping cache, platform names) ONLY. Never roms_root, never RetroArch saves/states (those live outside romhop dirs). Core: config.purge_user_data() Qt-free. Linux: gui/app.py _maybe_uninstall shows QMessageBox (default No) before removal — fires from the 'Uninstall RomHop' app-menu icon (Terminal=false). Windows: romhop.iss CurUninstallStepChanged MsgBox (MB_DEFBUTTON2=No) + DelTree {userappdata}/romhop + {localappdata}/romhop. Both prompts enumerate exactly what is/ isn't deleted. Tests: purge scope + dispatch yes/no. Windows Inno needs manual smoke.
<!-- SECTION:NOTES:END -->
