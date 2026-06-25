---
id: TASK-052
title: 'Theme assets: base.qss wizard/dialog rules + bundled light theme'
status: Done
assignee: []
created_date: '2026-06-24 15:20'
updated_date: '2026-06-24 17:02'
labels:
  - adaptive-themes
dependencies:
  - TASK-051
references:
  - docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md
  - docs/superpowers/specs/2026-06-24-adaptive-light-dark-themes-design.md
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plan Task 3 of adaptive light/dark themes. See plan docs/superpowers/plans/2026-06-24-adaptive-light-dark-themes.md. Append QDialog/QWizard/QWizard QFrame/QDialogButtonBox background rules to base.qss; create bundled themes/light/ (manifest.json + tokens.json light palette). Both schemes must still carry the TASK-005 QProgressBar rule.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 base.qss has QDialog, QWizard, QDialogButtonBox rules
- [ ] #2 themes/light renders with no raw {{ placeholder and includes QProgressBar::chunk
<!-- AC:END -->
