---
id: TASK-051
title: 'Theme: resolve_scheme + scheme_theme_dir helpers'
status: Done
assignee:
  - '@kschk24'
created_date: '2026-06-24 15:20'
updated_date: '2026-06-24 16:58'
labels:
  - adaptive-themes
dependencies:
  - TASK-050
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 2 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md. Add theme.resolve_scheme(mode, app)->'light'|'dark' (system reads QStyleHints.colorScheme(), Unknown->dark) and theme.scheme_theme_dir(scheme)->Path (light->themes/light, dark->themes/default).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 resolve_scheme forces light/dark; system reads OS scheme; Unknown->dark
- [x] #2 scheme_theme_dir maps light->themes/light, dark->themes/default
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented resolve_scheme + scheme_theme_dir in theme.py. 3 new tests, all 16 theme tests pass. Committed 75916a6.
<!-- SECTION:NOTES:END -->
