---
id: TASK-057.03
title: Add standalone GUI Upload dialog + button
status: Done
assignee:
  - '@claude'
created_date: '2026-06-25 17:36'
updated_date: '2026-06-25 18:07'
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
- [x] #1 Settings has an 'Upload local games to RomM' button, disabled when roms_root unset (like Scan)
- [x] #2 Click runs match off-thread (discovery only, no cache write) then opens the Upload dialog
- [x] #3 Dialog has platform-filter dropdown + sort (platform default/name) + select-all/none + default-unchecked checkboxes
- [x] #4 missing_platform rows offer Create platform; unresolvable rows disabled-with-reason (full parity)
- [x] #5 Upload runs via existing upload_action/UploadWorker; recover-on-entry copy broadened to 'scan or upload'
- [x] #6 pytest-qt tests cover open/filter/sort/select-all and that upload_action is called with selected games
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. gui/upload_dialog.py: new UploadDialog(candidates, upload_action, create_platform_fn, overrides) — platform-filter dropdown, sort dropdown, select-all/none, resolvable checkboxes (unchecked default), missing_platform rows with inline Create button, unresolvable disabled-with-tooltip, UploadWorker + progress/log
2. gui/settings_view.py: add upload_requested Signal + upload_btn (disabled when roms_root unset, like scan_btn); set_uploading(bool); _refresh_upload_enabled(); call refresh in reset()
3. gui/main_window.py: add discover_action param + _discover_worker; connect settings_view.upload_requested → run_upload_discover; _on_discover_done opens UploadDialog; _on_discover_error; _on_discover_finished
4. gui/app.py: discover_fn closure (list_roms + index_local + match + discover_uploadable, no cache write); inject into MainWindow; broaden recovery copy ('scan or upload')
5. tests/test_upload_dialog.py: pytest-qt tests for open/filter/sort/select-all/upload_action called with selected
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: gui/upload_dialog.py (new UploadDialog), settings_view.py (upload_requested signal + upload_btn + set_uploading), main_window.py (discover_action param + run_upload_discover flow), app.py (discover_action closure + broadened recovery copy). 13 new pytest-qt tests, all 641 pass. Committed 2500679.
<!-- SECTION:NOTES:END -->
