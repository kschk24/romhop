---
id: TASK-049
title: Windows installed-apps still shows 'RomHop version main' on installed build
status: To Do
assignee: []
created_date: '2026-06-24 15:07'
labels:
  - bug
  - windows
  - packaging
dependencies: []
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User's installed Windows build shows the app in Settings > Installed Apps as 'RomHop version main' with publisher 'main' and version 'romhop' (see screenshot). TASK-004 already fixed this in tree: package.yml computes a clean version (tag semver, else __version__+'-dev', never a branch slug) and romhop.iss pins AppVerName=RomHop / AppPublisher=romhop. So the installed build predates the fix (publisher 'main' confirms a pre-693a914 build). Verify the fix actually ships: build a fresh installer from current main, install it, and confirm Installed Apps shows clean name 'RomHop', publisher 'romhop', and a proper DisplayVersion. If a release was never cut with the fix, instruct user to reinstall from a post-fix build. Closes the gap left by TASK-004 which was marked Done without on-device verification of a shipped installer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fresh installer built from current main shows DisplayName 'RomHop' (no 'version <x>' suffix) in Windows Installed Apps
- [ ] #2 Publisher shows 'romhop', not a branch name
- [ ] #3 DisplayVersion shows clean semver or 'X.Y.Z-dev', never 'main'
- [ ] #4 Confirmed by installing the built setup.exe on Windows (on-device check, not just iss inspection)
<!-- AC:END -->
