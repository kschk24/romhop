---
id: TASK-009
title: Limit already-local download check to roms_root/system
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-16 15:07'
labels:
  - feature
dependencies: []
priority: low
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
download's already-local short-circuit calls index_local_library(roms_root, overrides) then filters to the rom's system, so every download pays for a full ROMs-tree scan even when the game isn't local. Fine at personal scale; lags on a large multi-system library. Fix: limit the walk to roms_root/system (optional system filter on index_local_library, or a focused existence check). Flagged in final review of scan-local-match. NOTE: base detect-already-local feature already SHIPPED 2026-06-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Already-local check walks only roms_root/system, not the whole tree
- [ ] #2 index_local_library gains optional system filter (or equivalent focused check)
- [ ] #3 Behaviour unchanged for the matched/skip path
<!-- AC:END -->
