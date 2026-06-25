---
id: TASK-050
title: 'Config: choice FieldSpec type + theme_mode setting'
status: Done
assignee:
  - kschk24
created_date: '2026-06-24 15:20'
updated_date: '2026-06-24 16:32'
labels:
  - adaptive-themes
dependencies: []
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 1 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md and spec docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md. Add an 'options' tuple to FieldSpec, a new 'choice' field type, a theme_mode setting (system|light|dark, default system) to Settings + SCHEMA, remove the old free-text 'theme' SCHEMA entry (keep the dataclass attr, reserved), and make coerce_value('choice') return the raw string. Update test_config.py theme roundtrip test (theme no longer persisted).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FieldSpec has options tuple; type 'choice' supported
- [x] #2 Settings.theme_mode defaults 'system' and persists via ini
- [x] #3 SCHEMA has theme_mode choice field and no 'theme' field
- [x] #4 coerce_value('choice', x) returns x
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. FieldSpec: add options tuple[str,...]=() field
2. coerce_value: add 'choice' branch returning raw string
3. Settings: add theme_mode: str = 'system' after theme attr
4. SCHEMA: replace theme FieldSpec with theme_mode choice field (options=system/light/dark)
5. test_config.py: rewrite theme roundtrip test for theme_mode, fix schema coverage set, add choice to valid types, add coerce_value choice assertion
<!-- SECTION:PLAN:END -->
