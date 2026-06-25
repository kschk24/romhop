---
id: TASK-042
title: Game Details view should be hidden when in settings screen
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-22 18:37'
updated_date: '2026-06-25 14:43'
labels:
  - bug
  - quick fix
dependencies: []
priority: low
ordinal: 55000
---

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Hide detail_panel in show_settings() and show_activity_log(). 2. Add DetailPanel.has_rom property. 3. Restore panel in show_library() only if has_rom.
<!-- SECTION:PLAN:END -->
