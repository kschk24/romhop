---
id: TASK-036
title: 'Bug: DetailPanel layout bare and title unformatted'
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 15:54'
updated_date: '2026-06-22 15:50'
labels:
  - bug
  - gui
  - detail-panel
  - detail-panel-redesign
dependencies: []
priority: medium
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DetailPanel layout is bare and broken: raw title overflows, raw platform slug, large empty gap, no cover, no region/language context. Redesign to: rich image header (cover placeholder → screenshot replaces), clean title (parens stripped, 2-line clamp), tag chips (FlowLayout, colored by category, flag emojis for regions), platform label via injected platform_label fn, scrollable metadata, buttons pinned at bottom. Also absorbs TASK-037 (screenshot support). Spec: docs/superpowers/specs/2026-06-18-detail-panel-layout-redesign.md
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Cover/screenshot image shown at top (200px h, proportional); gray 🎮 placeholder when absent
- [x] #2 Screenshot from rom.screenshots[0] loads off-thread, replaces cover once ready
- [x] #3 Title strips parenthetical tags, clamps to 2 lines word-wrap
- [x] #4 Tag chips (regions/languages/tags/revision) in FlowLayout; colored by category; flag emojis for known regions
- [x] #5 Platform shown via injected platform_label (PlatformNames cache), not raw slug
- [x] #6 Summary, genres, release date from RomDetail shown when available
- [x] #7 Empty gap eliminated — metadata in QScrollArea, buttons pinned below
- [x] #8 Files label removed
- [x] #9 Rom dataclass extended: regions, languages, tags, revision, screenshots from list endpoint
- [x] #10 FlowLayout helper added to gui/flow_layout.py
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend Rom dataclass: regions/languages/tags/revision/screenshots fields + populate in list_roms()
2. Add gui/flow_layout.py (FlowLayout QLayout ~50 lines)
3. Rewrite detail_panel.py: image header (cover placeholder + screenshot loader), _strip_tags title, FlowLayout chips, platform_label injection, scroll area + pinned buttons, remove files_label
4. Wire in main_window.py: pass cover_provider + platform_label to DetailPanel
5. Update test_gui_detail_panel.py: Rom factory gets new fields, tests for new layout elements
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: Rom dataclass +regions/languages/tags/revision/screenshots; FlowLayout (gui/flow_layout.py); DetailPanel redesign with image header, _strip_tags title, FlowLayout chips (colored by category + region flag emojis), platform_label injection, QScrollArea + pinned buttons, files_label removed; main_window.py wiring; 463 tests pass.
<!-- SECTION:NOTES:END -->
