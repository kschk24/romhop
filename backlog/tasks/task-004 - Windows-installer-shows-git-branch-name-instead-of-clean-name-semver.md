---
id: TASK-004
title: Windows installer shows git branch name instead of clean name/semver
status: Done
assignee: []
created_date: '2026-06-16 15:03'
updated_date: '2026-06-22 16:53'
labels:
  - bug
  - ready-for-agent
dependencies: []
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Installed Apps lists 'RomHop version packaging-freeze-installers' and version equals the git branch slug. CI feeds the git branch into Inno AppName/AppVersion instead of a clean product name + semver. Fix the .iss variable population in CI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Installed Apps shows clean product name (RomHop)
- [x] #2 Version field shows the release semver, not a branch slug
<!-- AC:END -->
