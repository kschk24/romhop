---
id: TASK-027
title: >-
  Cleanup: update.py code quality — logging, asserts, Signal type, duplicate
  guard call
status: Done
assignee:
  - '@kschk24'
created_date: '2026-06-17 13:05'
updated_date: '2026-06-17 13:29'
labels:
  - cleanup
  - update
  - ready-for-agent
dependencies: []
priority: low
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Four small code quality issues found in update.py and main_window.py during code review of TASK-010:
1. update.py:167 and main_window.py:628 import logging inside except/method instead of module-level logger = logging.getLogger(__name__) (breaks pattern of rest of codebase, harder to mock).
2. update.py:125 and 129 use assert isinstance() for type guards — stripped by python -O; replace with explicit if/raise.
3. workers.py:160 UpdateWorker.progress = Signal(int, int) — architecturally inconsistent with DownloadWorker which uses Signal('qlonglong','qlonglong', float) for the same byte-count reason; fix for consistency.
4. app.py:234 and 285 call _update.is_update_supported() twice on startup; cache result in a local.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 update.py and main_window.py use module-level logger, no import inside except/method
- [x] #2 assert isinstance() replaced with explicit if not isinstance(): raise TypeError
- [x] #3 UpdateWorker.progress uses Signal('qlonglong','qlonglong') matching DownloadWorker
- [x] #4 app.py caches is_update_supported() in one local variable, used in both places
- [x] #5 All existing update tests pass
<!-- AC:END -->
