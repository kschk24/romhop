---
id: TASK-016
title: Start on login (autostart) toggle
status: To Do
assignee: []
created_date: '2026-06-16 15:07'
updated_date: '2026-06-16 22:07'
labels:
  - feature
  - ready-for-agent
dependencies: []
priority: low
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A 'Start on login' toggle that auto-launches romhop to tray at boot. Per-OS: Windows (registry Run key / Startup folder) vs Linux (~/.config/autostart/*.desktop). Separate feature from close-to-tray; deferred 2026-06-15 during the background-sync-tray design.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Settings toggle to enable/disable start-on-login
- [ ] #2 Enabling registers autostart on Windows (Run key/Startup) and Linux (~/.config/autostart)
- [ ] #3 Disabling removes the autostart entry
- [ ] #4 Autostart launches to tray
<!-- AC:END -->
