---
id: TASK-057.02
title: Add standalone CLI `upload` command
status: To Do
assignee: []
created_date: '2026-06-25 17:36'
labels:
  - upload-frontdoor
dependencies:
  - TASK-057.01
documentation:
  - docs/superpowers/specs/2026-06-25-upload-front-door-design.md
parent_task_id: TASK-057
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
New top-level `upload` command mirroring `download`: runs the match internally (discovery only, no cache seed), variadic name list, --platform filter on ES-DE system dir, --yes non-interactive. Interactive InquirerPy picker with sort/filter/select-all. Keep scan --upload-unmatched and post-scan prompt unchanged. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `romhop upload` runs match and shows interactive checklist of all unmatched (TTY); uploads all resolvable on non-TTY/--yes
- [ ] #2 Variadic NAMES substring-match local unmatched game names (like download), deduped
- [ ] #3 --platform (repeatable, case-insensitive exact on ES-DE system dir) filters the set
- [ ] #4 Picker groups/sorts by system (default) or name, supports select-all/none respecting active filter, default unchecked
- [ ] #5 Internal match does NOT seed cache for matched games; only uploaded games are seeded (via run_upload_batch)
- [ ] #6 Full parity: offers create-missing-platform, lists unresolvable with reason; calls upload_session.recover() on entry
- [ ] #7 Tests cover name match, --platform filter, --yes, and discovery-only (no stray cache writes)
<!-- AC:END -->
