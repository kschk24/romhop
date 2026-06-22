---
id: TASK-033
title: 'Bug: DetailPanel sidebar size inconsistent across games'
status: Done
assignee: []
created_date: '2026-06-17 15:17'
updated_date: '2026-06-18 00:56'
labels:
  - bug
  - gui
  - detail-panel
dependencies: []
priority: medium
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DetailPanel (game detail sidebar) changes size depending on which game is selected. Content varies (different description lengths, metadata, cover art dimensions) causing the panel to resize. Should be fixed width/height so it never reflows on game change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Panel width stays constant regardless of which game is selected
- [ ] #2 Panel height fills available space without growing/shrinking on game switch
- [ ] #3 Content inside panel scrolls or truncates rather than forcing panel to resize
<!-- AC:END -->
