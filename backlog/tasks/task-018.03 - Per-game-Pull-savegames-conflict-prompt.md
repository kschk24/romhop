---
id: TASK-018.03
title: Per-game Pull savegames + conflict prompt
status: To Do
assignee: []
created_date: '2026-06-16 22:30'
updated_date: '2026-06-16 22:47'
labels:
  - feature
  - game-detail-panel
dependencies:
  - TASK-018.02
references:
  - docs/superpowers/plans/2026-06-17-game-detail-panel.md
parent_task_id: TASK-018
priority: low
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Part 3/3 of the game-detail-panel feature (design spec: docs/superpowers/specs/2026-06-17-game-detail-panel-design.md). Depends on TASK-018.02.

Add a 'Pull savegames' Game action (context menu + Detail panel button) that pulls one game's saves + savestates from RomM. pull_games only reads entry.rom_id, so pass a one-element shim built from Rom.id — no mapping_cache dependency. Pull works regardless of whether the game is downloaded (saves land in saves_dir/states_dir).

Run pull off the UI thread (worker). On a local file that differs from RomM's, prompt PER conflict showing both timestamps (remote_updated vs local mtime); user picks keep-local or take-remote. The on_conflict callback fires on the worker thread — marshal to the UI thread and block for the answer (threading.Event + result, like existing workers). Show a summary (written/skipped/kept/failed) when done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pull savegames action pulls saves+states for one game using a one-rom shim over pull_games (Rom.id only)
- [ ] #2 Pull runs off the UI thread and works whether or not the game is downloaded
- [ ] #3 Differing local file prompts per conflict with both timestamps; keep-local and take-remote both honored
- [ ] #4 Conflict prompt marshals from worker thread to UI thread without freezing/crashing
- [ ] #5 A summary of written/skipped/kept/failed is shown after the pull; tests cover the shim and conflict resolution paths
<!-- AC:END -->
