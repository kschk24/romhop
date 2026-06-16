---
id: TASK-017
title: 'Scan tidy-ups: HTTP-error test + remove redundant system re-derive'
status: To Do
assignee: []
created_date: '2026-06-16 15:07'
labels:
  - chore
  - test
dependencies: []
priority: low
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Minor scan tidy-ups flagged in scan-local-match review: (1) scan has no HTTP-error test — its path is identical to download's already-tested 403 handling, add coverage; (2) _run_scan re-derives system in the write loop (harmless redundancy), drop it. Not blockers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scan has an HTTP-error (e.g. 403) test
- [ ] #2 _run_scan no longer redundantly re-derives system in the write loop
<!-- AC:END -->
