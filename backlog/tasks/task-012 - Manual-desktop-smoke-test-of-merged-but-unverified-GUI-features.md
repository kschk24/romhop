---
id: TASK-012
title: Manual desktop smoke test of merged-but-unverified GUI features
status: Done
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 17:06'
labels:
  - chore
  - ready-for-human
dependencies: []
priority: medium
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Several merged GUI features on gui-desktop-pyside still need a manual desktop smoke pass: setup wizard (3-page QWizard, auto-launch, Test-blocks-Next, opt-in scan), background sync via tray (tray show/hide, relaunch-raises, quit, status-colored icon), and the freeze installers. Run these by hand on a real desktop and log any defects as new tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Setup wizard smoke-tested (launch, test gating, scan opt-in)
- [ ] #2 Tray behaviour smoke-tested (close-to-tray, relaunch raises, quit, status icon)
- [ ] #3 Defects found are filed as new backlog tasks
<!-- AC:END -->
