---
id: TASK-010.12
title: 'Docs: GitHub-Releases update + release runbook'
status: Done
assignee: []
created_date: '2026-06-17 09:05'
updated_date: '2026-06-17 09:36'
labels:
  - auto-update-gh-releases
  - docs
dependencies:
  - TASK-010.08
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
parent_task_id: TASK-010
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Maintainer runbook for the GitHub-Releases auto-update (replaces the tufup key-management runbook). See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Documents stable vs prerelease tag flow (clean vs hyphenated tag) and the experimental-channel toggle
- [x] #2 Manual desktop smoke checklist: install old build, launch, accept update, confirm silent installer runs + relaunches new version (Win + Linux)
- [x] #3 Troubleshooting: offline / rate-limit / SHA mismatch / installer-failure behavior
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Expanded README Releasing section: stable/RC tag flow, experimental channel toggle, auto-update smoke checklist (both OS, both channels), troubleshooting table.
<!-- SECTION:NOTES:END -->
