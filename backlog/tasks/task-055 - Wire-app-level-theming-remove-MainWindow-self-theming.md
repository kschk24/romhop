---
id: TASK-055
title: Wire app-level theming + remove MainWindow self-theming
status: Done
assignee:
  - '@kschk24'
created_date: '2026-06-24 15:20'
updated_date: '2026-06-25 00:49'
labels:
  - adaptive-themes
dependencies:
  - TASK-054
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 6 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md. app.run(): apply_theme at startup, connect colorSchemeChanged (system mode only re-themes), apply_theme inside apply_settings on save. Remove MainWindow self-theming (setStyleSheet lines ~143-144) and now-unused theme import.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MainWindow no longer sets its own theme stylesheet (win.styleSheet()=='')
- [x] #2 app applies theme at startup, on save, and follows OS in system mode
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. main_window.py: remove theme import (line 29) + self.setStyleSheet lines 143-144\n2. app.py: import theme; call apply_theme(app, settings) after QApplication created; connect app.styleHints().colorSchemeChanged to lambda that calls apply_theme when mode==system; call apply_theme(app, new_settings) inside apply_settings
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed theme import + self-setStyleSheet from MainWindow.__init__. app.run(): apply_theme at startup, colorSchemeChanged re-applies in system mode, apply_settings calls apply_theme. Updated test to assert win.styleSheet()==''.
<!-- SECTION:NOTES:END -->
