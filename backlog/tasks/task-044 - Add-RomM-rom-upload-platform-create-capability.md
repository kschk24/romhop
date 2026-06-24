---
id: TASK-044
title: Add RomM rom-upload + platform-create capability
status: Done
assignee:
  - '@claude'
created_date: '2026-06-23 14:42'
updated_date: '2026-06-23 16:08'
labels:
  - feature
  - upload-unmatched
dependencies: []
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Privileged-write + scan-trigger prerequisite for TASK-014 (upload unmatched local games). Design spec: docs/superpowers/specs/2026-06-23-upload-unmatched-design.md (full live-verified API notes there). Adds RommClient capabilities romhop lacks today: (1) upload_rom — chunked store-only upload of a rom file streamed from disk (POST /api/roms/upload/start -> PUT chunks -> /complete; mirrors download.py streaming, no whole-file RAM). x-upload-filename is a BARE LEAF only (a subfolder path 500s). complete returns 201 EMPTY and creates NO rom — it only writes the file to RomM's fs; surfaces the start-time 400 'File already exists' as an already-exists/skip signal. (2) create_platform — POST /api/platforms {fs_slug}; does NOT dedup, so MUST existence-check via GET /api/platforms first. (3) trigger_scan — there is NO REST scan trigger (scan_library is manual_run:false -> tasks.run 400); materialization is Socket.IO-only (/ws/socket.io, emit 'scan' {platforms,roms_ids,type:'quick',apis}, await scan:done/scan:done_ko). Add python-socketio[client] dependency. Provide a hand-off fallback when the socket is unreachable (caller still seeds a basic mapping entry + tells the user to scan in RomM). Shared label upload-unmatched. ADR docs/adr/0002-disc-aware-local-index.md covers the related local_index change (now TASK-045).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 RomM API verified: rom-upload endpoint, platform-create support, dedup behavior, and required token scope documented in the task before implementation
- [x] #2 RommClient.create_platform creates a platform from IGDB slug + display name (or task documents that the API does not support it and TASK-014 falls back to disabled-with-reason)
- [x] #3 Unit tests cover upload_rom + create_platform against httpx MockTransport (success, already-exists, insufficient-scope)
- [x] #4 Token scope verified at setup/login: roms.write (upload), platforms.write (create) + platforms.read (resolve platform_id incl. zero-rom platforms). Clear, actionable error naming the missing scope when absent. NOTE: live token already has roms.write; user broadens it to add platforms.write + platforms.read
- [x] #5 RommClient.upload_rom streams one rom file from disk via the chunked flow (start -> PUT chunks -> complete; bare-leaf x-upload-filename; cancel aborts), accepts platform_id, and surfaces the start-time 400 'File already exists' as an already-exists signal. NOTE: complete returns no rom id and creates no rom (file is only written to fs); the rom id is obtained later by trigger_scan + find-by-fs_name, not from complete.
- [x] #6 RommClient.trigger_scan connects to RomM Socket.IO (/ws/socket.io, bearer auth), emits a platform-scoped quick scan, and awaits scan:done/scan:done_ko with a bounded timeout; raises/returns a clear signal on connect failure so the caller can fall back to hand-off. Adds python-socketio[client] as a dependency.
- [x] #7 After a scan, a helper finds materialized rom(s) by matching uploaded fs_name (platform-scoped; note /api/roms ignores a platform_id query param, filter client-side by platform_slug)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add python-socketio[client] dep to pyproject.toml
2. Add exception classes (RomAlreadyExists, UploadCancelled, ScanError, ScanConnectError, InsufficientScopeError) to romm_client.py
3. Add _check_scope helper (403 -> InsufficientScopeError naming scope)
4. Add list_platforms() - GET /api/platforms, check platforms.read
5. Add create_platform(fs_slug) - existence-check then POST, checks platforms.write
6. Add upload_rom(*, platform_id, file_path, file_name, stop_event=None, progress_fn=None, chunk_size=1MiB) - start/chunk/complete flow, dedup signal, cancel
7. Add trigger_scan(platform_id, *, timeout=60.0, _sio_factory=None) - Socket.IO quick scan, ScanConnectError fallback signal
8. Add find_roms_by_fs_names(platform_slug, fs_names, search_term=None) - client-side filter after scan
9. Write tests for all new methods in test_romm_client.py
10. Install dep + run full test suite
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
API + scan + cleanup VERIFIED LIVE 2026-06-23 against romm.batsnest.de (a FORK of RomM) via OpenAPI + authenticated REST + a full throwaway upload->scan->delete cycle. All test residue removed (library back to 1259 roms, 0 ROMHOP residue). Consolidated design: docs/superpowers/specs/2026-06-23-upload-unmatched-design.md.

=== SCOPES (re-probed; supersedes earlier 'ABSENT' note) ===
roms.write PRESENT, platforms.read PRESENT (GET /api/platforms 200), tasks.run PRESENT (GET /api/tasks 200). platforms.write NOT re-verified (only probeable destructively) -> verify at setup/login, name the missing scope on failure. users.read absent (irrelevant).

=== UPLOAD = CHUNKED, STORE-ONLY ===
start (headers x-upload-platform int, x-upload-filename, x-upload-total-size, x-upload-total-chunks) -> 201 {upload_id}; PUT /upload/{id} (x-chunk-index) raw bytes; /complete -> 201 EMPTY, NO rom id, creates NO rom (writes file to fs only); /cancel -> 204. Dedup: start with existing filename -> 400 {detail:'File <name> already exists'} (by filename, pre-chunk) = skip signal.
x-upload-filename MUST be a BARE LEAF: a '/' subfolder path -> 500 {detail:'Error assembling file chunks'} at complete (VERIFIED by isolation: spaces/parens in the leaf are fine; only the slash breaks it). The upload API CANNOT create subfolders.

=== MATERIALIZATION = SOCKET.IO ONLY (no REST scan) ===
scan_library is manual_run:false -> POST /api/tasks/run/scan_library returns 400 {detail:"Task 'scan_library' cannot be run"}. Runnable manual tasks (cleanup_orphaned_resources/cleanup_missing_roms/sync_folder_scan/recompute_save_content_hashes) do NOT import roms. cleanup_orphaned_resources does NOT remove orphaned uploaded files (removed_fs_roms:0).
Scan IS triggerable over Socket.IO at /ws/socket.io (VERIFIED working): connect bearer-auth, transports=[websocket], socketio_path=/ws/socket.io; emit event 'scan' {platforms:[id], roms_ids:[], type:'quick', apis:[]}; server emits scan:update_stats / scan:scanning_platform / scan:scanning_rom / scan:done (or scan:done_ko). A quick platform-scoped scan materialized 3 just-uploaded files in seconds (new_roms:3). type:quick imports new files WITHOUT re-identifying existing roms; new roms come back is_unidentified:true (quick did not run IGDB -> identified_roms:0) -> treat metadata as pending.

=== GROUPING (the big unknown — RESOLVED) ===
Flat uploaded files each materialize as a SEPARATE single-file rom (has_simple_single_file:true, empty files[]/sibling_roms[]). One multi-file rom needs a folder, which upload CANNOT create. DECISION (with user): upload each real disc file as a flat leaf (every .cue + every .bin); the user's RomM FORK scanner auto-sorts loose related files into a per-game subfolder and coalesces them into one rom. On OFFICIAL RomM this does NOT happen (stays N single-file roms) — documented limitation, fork-independent multi-disc deferred.

=== FIND / DELETE / POLL ===
/api/roms IGNORES a platform_id query param (returned full 1259-rom library) -> filter materialized roms client-side by platform_slug + match fs_name to uploaded leaf; search_term narrows. Delete: POST /api/roms/delete {roms:[ids], delete_from_fs:[ids]} -> {successful_items,failed_items,errors} (materialized roms only; deleted the 3 test roms cleanly). Poll rom.is_identifying/is_identified/is_unidentified.

=== PLATFORM CREATE ===
POST /api/platforms {fs_slug:<slug>}, scope platforms.write. Does NOT dedup -> existence-check via GET /api/platforms (resolve slug->id, reuse if present) before create.

=== CLEANUP CAVEAT for future live tests ===
Orphaned uploaded files (completed upload but never scanned) are NOT deletable via API (delete needs a materialized rom; cleanup_orphaned_resources skips them). Only removable by scanning them in (then /api/roms/delete) or server fs access. This session's 3 failed slash-path uploads left only transient upload-temp chunks (~135 bytes, not in roms dir, RomM GCs them) — negligible.

Implemented in src/romhop/romm_client.py: RomAlreadyExists, UploadCancelled, InsufficientScopeError, ScanError, ScanConnectError exceptions; list_platforms(), create_platform(), upload_rom() (chunked streaming, dedup signal, cancel, scope check), trigger_scan() (Socket.IO, timeout, _sio_factory seam), find_roms_by_fs_names(). Added python-socketio[client]>=5.11 to pyproject.toml. 17 new tests in test_romm_client.py, all 40 pass. Full suite 529/530 pass (1 flaky pre-existing Qt race unrelated to this task).
<!-- SECTION:NOTES:END -->
