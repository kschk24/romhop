---
id: TASK-037
title: 'Enhancement: game screenshot in DetailPanel from RomM API'
status: Done
assignee: []
created_date: '2026-06-17 23:49'
updated_date: '2026-06-22 17:06'
labels:
  - enhancement
  - gui
  - detail-panel
dependencies: []
priority: low
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DetailPanel could show a game screenshot fetched from RomM alongside the cover thumbnail. RomM API likely exposes screenshot URLs on the rom detail endpoint but RomDetail dataclass does not capture them yet. Requires: inspect /api/roms/{id} response for screenshot fields, extend RomDetail, fetch + display in panel.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 RomDetail dataclass extended with screenshot URL field(s) from /api/roms/{id} response
- [ ] #2 DetailPanel displays one screenshot image when available, falls back gracefully when absent
- [ ] #3 Screenshot fetched off UI thread (same pattern as cover loading)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Absorbed into TASK-036 (detail-panel-redesign). merged_screenshots confirmed on SimpleRomSchema (list endpoint), no detail fetch needed. Implementation will land with TASK-036.
<!-- SECTION:NOTES:END -->
