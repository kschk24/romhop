---
id: TASK-026
title: 'Bug: UpdateWorker threads leak on reassignment and window close'
status: Done
assignee: []
created_date: '2026-06-17 13:05'
updated_date: '2026-06-17 14:20'
labels:
  - bug
  - update
  - ready-for-agent
dependencies: []
priority: medium
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
main_window.py _check_worker (line 101) and _apply_worker (line 102) are reassigned without cleanup. check_for_updates() (line 582) creates a new UpdateWorker but never calls quit()/deleteLater() on the previous one. _on_update_clicked (line 604) same. closeEvent/_shutdown_sync only cleans _sync_worker. Calling check_for_updates() twice leaks the first QThread and its captured closures. Pattern: call old_worker.quit(); old_worker.wait(); old_worker.deleteLater() before reassigning, matching how _sync_worker is handled. Found in code review of TASK-010.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 check_for_updates() quits and deletes existing _check_worker before creating a new one
- [ ] #2 _on_update_clicked quits and deletes existing _apply_worker before creating a new one
- [ ] #3 closeEvent/_quit_app also stops any in-progress update workers
- [ ] #4 Test: calling check_for_updates() twice does not leave dangling threads
<!-- AC:END -->
