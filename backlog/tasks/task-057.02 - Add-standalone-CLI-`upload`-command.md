---
id: TASK-057.02
title: Add standalone CLI `upload` command
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-25 17:36'
updated_date: '2026-06-25 17:56'
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
- [x] #1 `romhop upload` runs match and shows interactive checklist of all unmatched (TTY); uploads all resolvable on non-TTY/--yes
- [x] #2 Variadic NAMES substring-match local unmatched game names (like download), deduped
- [x] #3 --platform (repeatable, case-insensitive exact on ES-DE system dir) filters the set
- [x] #4 Picker groups/sorts by system (default) or name, supports select-all/none respecting active filter, default unchecked
- [x] #5 Internal match does NOT seed cache for matched games; only uploaded games are seeded (via run_upload_batch)
- [x] #6 Full parity: offers create-missing-platform, lists unresolvable with reason; calls upload_session.recover() on entry
- [x] #7 Tests cover name match, --platform filter, --yes, and discovery-only (no stray cache writes)
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add _select_for_upload() to cli.py: InquirerPy checkbox sorted by (system,game_name) with Separator groups, ctrl+a hint, default unchecked; fallback to all-or-confirm. 2. Add upload() command to cli.py: roms_root check, recover() on entry, list_roms+match_to_roms (discovery-only, no cache seeding for matched), name substring filter, --platform exact-CI filter on ES-DE system dir, discover_uploadable, missing_platform create offer, _select_for_upload, summary+confirm, run_upload_batch. 3. Tests in tests/test_cli_upload.py: name match, --platform filter, --yes non-interactive, no stray cache writes for matched-only games.
<!-- SECTION:PLAN:END -->
