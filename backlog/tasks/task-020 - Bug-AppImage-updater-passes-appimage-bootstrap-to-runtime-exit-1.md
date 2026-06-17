---
id: TASK-020
title: 'Bug: AppImage updater passes --appimage-bootstrap to runtime, exit 1'
status: Done
assignee: []
created_date: '2026-06-17 10:20'
labels:
  - bug
  - auto-update-gh-releases
dependencies: []
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during smoke test of TASK-010 update flow.

_apply_installer in update.py ran the downloaded AppImage as:
  [path, '--appimage-bootstrap']

The AppImage type2 runtime intercepts unknown --appimage-* flags before
AppRun executes and returns exit code 1 ('not yet implemented').
AppRun already hardcodes --appimage-bootstrap in its exec line, so the
extra flag was redundant and fatal.

Fix: invoke the AppImage bare ([path] only). Committed in 4b47672 on
feature/auto-update-github-releases. v0.1.0 release retagged and rebuilt
with the fix before smoke test completed.
<!-- SECTION:DESCRIPTION:END -->
