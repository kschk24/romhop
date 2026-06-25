---
id: TASK-053
title: 'Theme: app-level apply_theme(app, settings)'
status: Done
assignee:
  - '@claude'
created_date: '2026-06-24 15:20'
updated_date: '2026-06-24 17:32'
labels:
  - adaptive-themes
dependencies:
  - TASK-052
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 66000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 4 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md. Add theme.apply_theme(app,settings): setColorScheme(Light/Dark) for forced modes, Unknown for system; resolve scheme, load theme dir, app.setStyleSheet(qss). Drives native title bar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 apply_theme sets app colorScheme to requested scheme for light/dark
- [x] #2 apply_theme sets a non-empty app stylesheet with QWizard rule and no raw placeholder; light != dark qss
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
apply_theme implemented in gui/theme.py. setColorScheme spy used in test (Wayland headless: setColorScheme called but colorScheme() always returns OS value). 19/19 tests pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added apply_theme(app, settings) to gui/theme.py: sets colorScheme (Light/Dark/Unknown) via styleHints then resolves scheme, loads matching theme dir, and sets app stylesheet. Test uses mock.patch.object spy on setColorScheme (Wayland ignores the call but it's correct for Windows/macOS). 19/19 theme tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
