---
id: TASK-057.03
title: Add standalone GUI Upload dialog + button
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
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Evolve ScanResultDialog's upload picker into a standalone Upload dialog opened by an 'Upload local games to RomM' button in Settings (near Scan, disabled when roms_root unset). Runs match off-thread discovery-only, then opens dialog from discover_uploadable. Reuses UploadWorker/run_upload_batch plumbing. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Settings has an 'Upload local games to RomM' button, disabled when roms_root unset (like Scan)
- [ ] #2 Click runs match off-thread (discovery only, no cache write) then opens the Upload dialog
- [ ] #3 Dialog has platform-filter dropdown + sort (platform default/name) + select-all/none + default-unchecked checkboxes
- [ ] #4 missing_platform rows offer Create platform; unresolvable rows disabled-with-reason (full parity)
- [ ] #5 Upload runs via existing upload_action/UploadWorker; recover-on-entry copy broadened to 'scan or upload'
- [ ] #6 pytest-qt tests cover open/filter/sort/select-all and that upload_action is called with selected games
<!-- AC:END -->
