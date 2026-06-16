---
id: TASK-018.02
title: 'Per-game actions: menu + panel buttons (Download, Open in RomM, Open folder)'
status: To Do
assignee: []
created_date: '2026-06-16 22:28'
updated_date: '2026-06-16 22:47'
labels:
  - feature
  - game-detail-panel
dependencies:
  - TASK-018.01
references:
  - docs/superpowers/plans/2026-06-17-game-detail-panel.md
parent_task_id: TASK-018
priority: low
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Part 2/3 of the game-detail-panel feature (design spec: docs/superpowers/specs/2026-06-17-game-detail-panel-design.md). Depends on TASK-018.01.

Expose a shared per-game action set in BOTH the tile's right-click context menu and the Detail panel (as buttons): Download, Open in RomM, Open containing folder (Pull savegames is Part 3). Wire each as an injected callable in gui/app.run() per the Qt-free-core boundary — widgets do not import backend modules.

- Download: scope the existing download_action to one Rom; relabel to 'Re-download' when already downloaded.
- Open in RomM: open '{romm_url}/rom/{id}' in the system browser (QDesktopServices). Keep the URL pattern as a single constant.
- Open containing folder: QDesktopServices.openUrl on the downloaded game's on-disk folder (resolve via roms_root + platform_map / library layout). Greyed out / disabled when the game is not downloaded.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Right-click on a tile shows a context menu with Download, Open in RomM, Open folder; the Detail panel shows the same actions as buttons
- [ ] #2 Download triggers a single-game download (reuses download_action); label reflects downloaded state
- [ ] #3 Open in RomM opens {romm_url}/rom/{id} in the browser via an injected callable; URL pattern is a single constant
- [ ] #4 Open folder opens the game's on-disk folder and is disabled when the game is not downloaded
- [ ] #5 Actions injected in app.run() (no backend imports in widgets); tests cover menu/button wiring and folder-path resolution
<!-- AC:END -->
