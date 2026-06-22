---
id: TASK-034
title: search bar doesnt clear when switching from games library to settings
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 15:40'
updated_date: '2026-06-22 15:57'
labels:
  - bug
dependencies: []
priority: high
ordinal: 45000
---

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Clear search.text() in show_settings() and show_library() on switch\n2. Also clear when Esc closes search (if any)\n3. Add test: search text typed in library view, switch to settings → search bar empty\n4. Commit
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed: search.clear() in show_settings() + show_library(). Removed stale filter() calls after clear (signal handles it). Updated test suite (removed 2 carry-over tests, added test_search_clears_on_view_switch). 453 tests pass. Committed 76bbb4f.
<!-- SECTION:NOTES:END -->
