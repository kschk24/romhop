---
id: TASK-064
title: 'Gallery: covers full-width, downloaded banner sized to cover'
status: Done
assignee: []
created_date: '2026-06-25 19:06'
updated_date: '2026-06-25 19:06'
labels: []
dependencies: []
ordinal: 85000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Rework LibraryView tile rendering to match new gallery mockup. (1) Covers scale to full inner tile width (width-priority) so portrait box-art no longer gets letterbox bars on the left/right. (2) DOWNLOADED ribbon sized to the cover's actual rendered width, not the full label width, so it never overhangs the cover. (3) Covers are bottom-anchored in a taller fixed cover area (COVER_HEIGHT 205) tall enough for ~0.71 portrait box-art at full width; wider covers come out shorter and leave a gap at the top, with the DOWNLOADED ribbon filling that top gap above the cover.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Covers render at full inner tile width with no left/right letterbox bars
- [ ] #2 DOWNLOADED banner width matches the rendered cover width (no overhang)
- [ ] #3 Wide-aspect covers leave a top gap; ribbon sits above the cover in that gap
- [ ] #4 All covers in a row share the same width; aspect ratio preserved
- [ ] #5 tests/test_gui_views.py passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
library_view.py: width-priority cover scaling (COVER_WIDTH=CELL_WIDTH-2*COVER_PAD), COVER_HEIGHT 120->205, CELL_HEIGHT 170->255. Cover QLabel AlignHCenter|AlignBottom. New _place_cover() sizes/moves the ribbon to the rendered pixmap width at y=0 (top gap); used by both cached + async cover paths. CoverLoader cover_size now (COVER_WIDTH, COVER_HEIGHT).
<!-- SECTION:NOTES:END -->
