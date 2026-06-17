---
id: TASK-010.10
title: 'GUI update flow: worker, banner, restart, settings toggles'
status: To Do
assignee: []
created_date: '2026-06-17 09:05'
labels:
  - auto-update-gh-releases
  - feature
dependencies:
  - TASK-010.08
  - TASK-010.09
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
parent_task_id: TASK-010
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUI surface for the GitHub-Releases updater. Reuses the approach-agnostic banner/worker/restart commits from the abandoned feature/auto-update-tufup branch (cherry-pick onto the new branch). app.run() injects update_check_fn/update_apply_fn as plain callables; widgets never import update.py. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 UpdateWorker(QThread) runs check+download off the UI thread and emits progress
- [ ] #2 On launch, if auto_update_check and is_update_supported(), background check passes update_include_prereleases; update-available shows non-blocking banner 'vX.Y.Z available [Update][Later]'
- [ ] #3 Update -> progress bar -> modal 'Restart to finish updating' -> relaunch
- [ ] #4 Settings: 'Check for updates' button + auto-check toggle + 'Include experimental pre-release updates' checkbox; hidden/disabled when is_update_supported() is False
<!-- AC:END -->
