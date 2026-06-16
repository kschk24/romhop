---
id: TASK-002
title: Frozen install does not expose romhop CLI on PATH
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
labels:
  - bug
  - packaging
dependencies: []
priority: medium
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Frozen per-user installs (Linux AppImage + Windows Inno) ship the GUI only; the 'romhop' CLI is not available on PATH after install. Confirmed on Windows 2026-06-16. Users who want the CLI cannot reach it from a frozen install.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 romhop CLI invocable after a frozen install on Linux
- [ ] #2 romhop CLI invocable after a frozen install on Windows
<!-- AC:END -->
