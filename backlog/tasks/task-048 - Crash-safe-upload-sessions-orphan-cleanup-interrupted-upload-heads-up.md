---
id: TASK-048
title: 'Crash-safe upload sessions: orphan cleanup + interrupted-upload heads-up'
status: Done
assignee:
  - '@claude'
created_date: '2026-06-23 17:46'
updated_date: '2026-06-24 14:09'
labels:
  - upload
  - task-014
  - resilience
dependencies: []
priority: medium
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Force-quit/power-loss during an upload batch currently leaves two gaps. (A) A hard kill mid-PUT leaves the RomM server holding an orphan upload_id + staged chunks: upload_rom only calls _cancel_upload on graceful stop_event or an in-loop exception, never on process death, so staged chunks accumulate server-side. (B) The upload queue is in-memory only (UploadWorker._jobs / scan dialog jobs), so remaining queued games vanish with no record. Plus a latent bug: scan_result_dialog._on_upload_finished always says 'Upload complete' even when the batch was cancelled.

Scope (decided in grill-with-docs):
- Gap A (orphan cleanup): IN. Persist active upload_id(s); reap on recovery.
- Gap C (in-memory queue loss): C-light-flag. Do NOT build a durable resumable queue — un-uploaded games are still Unmatched, so the next 'scan' self-heals/re-surfaces them. Instead drop a dirty-flag so the next launch can proactively say the last upload was interrupted, and recovery = re-scan.
- Gap B (resume-from-chunk / .part for the in-flight file): DEFERRED, explicit follow-up. Re-upload wastes time, not data; RomM chunked API may not support resume.

Design (decided):
- New core module src/romhop/upload_session.py persisting user_data_dir()/upload_session.json: { in_progress: bool, active_uploads: [{upload_id, platform_id, file_name}] }. Its own module, NOT folded into MappingCache (different lifecycle). Purged automatically by purge_user_data (rmtrees user_data_dir).
- romm_client.upload_rom stays PURE TRANSPORT: gains two injected callbacks on_session_start(upload_id) (fired right after /start) and on_session_end(upload_id) (after /complete or graceful cancel), mirroring the existing progress_fn/stop_event injection. It does not import or write the store.
- upload.py orchestrates: set in_progress at batch start; bracket each file via the callbacks (add upload_id on start, remove on clean end); clear in_progress + empty list on clean batch finish.
- upload_session.recover(client) -> RecoveryInfo: POST .../{upload_id}/cancel for each leftover (idempotent + tolerant of 404/missing — server may already TTL-expire sessions, so reap correctness does NOT depend on that unknown), report whether flag was dirty, then clear the file.
- Trigger sites (NOT global / not every process start): GUI calls recover() at app startup; CLI calls recover() only at the start of the upload-adjacent commands (scan + the upload path), never on config/login/etc.

Known limitation (documented, out of scope): concurrent CLI '--upload-unmatched' while the GUI is open = two writers to upload_session.json, last-writer-wins; worst case a live upload_id gets cancelled and degrades to re-scan/re-upload. No file lock — disproportionate for a vanishingly rare case.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 src/romhop/upload_session.py exists: reads/writes user_data_dir()/upload_session.json with {in_progress, active_uploads:[{upload_id, platform_id, file_name}]}; its own module, not part of MappingCache
- [x] #2 romm_client.upload_rom gains on_session_start(upload_id)/on_session_end(upload_id) callbacks fired right after /start and after /complete (or graceful cancel); romm_client imports nothing from upload_session — pure transport preserved
- [x] #3 upload.py sets in_progress at batch start, brackets each file (add upload_id on start / remove on clean end via the callbacks), and clears in_progress + empties the list on a clean batch finish
- [x] #4 upload_session.recover(client) reaps every leftover upload_id via POST .../cancel, is idempotent and tolerant of 404/already-expired sessions, reports the dirty-flag, then clears the file
- [x] #5 GUI calls recover() at startup; when the flag was dirty it emits an Activity event 'previous upload interrupted — re-run scan to continue'; orphans are reaped silently
- [x] #6 CLI calls recover() only at the start of scan and the upload path (not config/login/other commands); prints a one-line heads-up when the flag was dirty
- [x] #7 Bug fix: scan_result_dialog no longer labels a cancelled batch 'Upload complete'; graceful cancel shows a cancelled state and emits 'batch cancelled, N not uploaded'
- [x] #8 Tests cover: recover reaps orphans, recover is idempotent on a missing/expired session, in_progress set/cleared lifecycle across a clean batch, callbacks fire add/remove around a file, and the cancel-label fix
- [x] #9 CHANGELOG Unreleased section updated; concurrent CLI+GUI race noted as a known limitation in the ticket/notes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. New upload_session.py: session file in user_data_dir(), set_in_progress/add_upload/remove_upload/clear/recover
2. romm_client.upload_rom: add on_session_start(upload_id)/on_session_end(upload_id) callbacks
3. upload.py: thread callbacks through upload_game; add run_upload_batch (batch lifecycle owner)
4. gui/workers.py: UploadWorker uses batch_fn interface (calls run_upload_batch)
5. gui/app.py: upload_action→upload_batch_fn wrapping run_upload_batch; recover at startup
6. gui/main_window.py: rename upload_action→upload_batch_fn
7. gui/scan_result_dialog.py: use upload_batch_fn; fix cancelled label bug
8. cli.py: recover at scan start; _run_upload_unmatched uses run_upload_batch
9. Tests: upload_session recovery, lifecycle, callbacks, cancel-label fix
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: upload_session.py (new module), RommClient callbacks, run_upload_batch in upload.py, UploadWorker batch_fn refactor, recover at GUI startup + CLI scan, cancel label fix. 569 tests pass.
<!-- SECTION:NOTES:END -->
