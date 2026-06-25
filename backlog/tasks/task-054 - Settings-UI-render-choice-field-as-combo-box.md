---
id: TASK-054
title: 'Settings UI: render choice field as combo box'
status: In Progress
assignee:
  - '@kschk24'
created_date: '2026-06-24 15:20'
updated_date: '2026-06-25 00:44'
labels:
  - adaptive-themes
dependencies:
  - TASK-053
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 67000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 5 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md. settings_view: _make_widget renders type=='choice' as QComboBox from FieldSpec.options; _populate selects current value by string; _read_widget returns currentText().
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Theme row renders a QComboBox with options system/light/dark, default selected
- [x] #2 _read_widget returns the selected string
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added QComboBox branch to _make_widget/_populate/_read_widget. Two new tests cover AC1+AC2. 27/27 tests pass.
<!-- SECTION:NOTES:END -->
