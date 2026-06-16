---
id: TASK-006
title: Windows setup wizard theme mismatch (light header/footer on dark body)
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
labels:
  - bug
  - gui
  - windows
dependencies: []
priority: low
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On Windows the setup QWizard renders its header and footer bands light/white while the body is dark. The dark qss does not cover the QWizard chrome. Fix by setting ClassicStyle or extending the qss to cover wizard header/footer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Wizard header and footer match the dark theme on Windows
<!-- AC:END -->
