---
id: TASK-018.01
title: Game detail side panel + RomM detail fetch
status: To Do
assignee: []
created_date: '2026-06-16 22:27'
updated_date: '2026-06-16 22:47'
labels:
  - feature
  - game-detail-panel
dependencies: []
references:
  - docs/superpowers/plans/2026-06-17-game-detail-panel.md
parent_task_id: TASK-018
priority: low
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Part 1/3 of the game-detail-panel feature (design spec: docs/superpowers/specs/2026-06-17-game-detail-panel-design.md).

Add a Detail panel docked on the right of MainWindow. Clicking a tile's BODY (not the checkbox) opens it; clicking another tile updates it in place; a close button dismisses it. The tile's QCheckBox(name) must split into a bare checkbox glyph (batch-select only) + a separate name label so body-click no longer toggles selection.

Panel shows local Rom fields instantly (cover, name, platform, file list, downloaded status), then fills in RomM-fetched detail when it arrives: summary, release date, genres, file size. Add RommClient.get_rom(id) returning these (all OPTIONAL, degrade gracefully — field names need a live probe of GET /api/roms/{id} on the real server first, MockTransport tests only). Fetch off the UI thread via a worker; cache result per rom id for quick game-to-game flipping. On fetch failure, keep local fields + show a 'couldn't load details' note.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Clicking a tile body opens the Detail panel; checkbox glyph still toggles batch selection without opening the panel
- [ ] #2 Panel docks right, grid stays visible, updates in place on another tile click, and a close button hides it
- [ ] #3 RommClient.get_rom(id) returns summary/release date/genres/file size, each tolerant of missing keys
- [ ] #4 Detail fetched off the UI thread, cached per rom id; local fields shown immediately as fallback; fetch failure shows local fields + an error note
- [ ] #5 Tests cover get_rom parsing (incl. missing fields) and the click-vs-select split
<!-- AC:END -->
