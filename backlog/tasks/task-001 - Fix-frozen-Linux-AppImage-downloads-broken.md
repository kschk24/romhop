---
id: TASK-001
title: Fix frozen Linux AppImage downloads broken
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
labels:
  - bug
  - packaging
  - linux
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Downloads do not work in the frozen Linux AppImage build (failure mode TBC). Suspected cause: missing certifi/TLS CA bundle or missing hiddenimports in the PyInstaller spec. High priority — core download flow unusable in the shipped frozen build.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Root cause of failed download in frozen AppImage identified
- [ ] #2 Download of a rom succeeds end-to-end from the frozen AppImage
- [ ] #3 PyInstaller spec includes any required hiddenimports/data (e.g. certifi)
<!-- AC:END -->
