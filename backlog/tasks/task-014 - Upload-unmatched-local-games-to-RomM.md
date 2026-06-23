---
id: TASK-014
title: Upload unmatched local games to RomM
status: Done
assignee:
  - '@claude'
created_date: '2026-06-16 15:07'
updated_date: '2026-06-23 16:27'
labels:
  - feature
  - upload-unmatched
dependencies:
  - TASK-044
  - TASK-045
priority: low
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turn scan's Unmatched report into an action: upload some/all unmatched local games up to RomM (the reverse of Download). Captured 2026-06-13 after a live scan left 7 real games unmatched. UX layer over TASK-044 (privileged upload + platform-create + Socket.IO scan-trigger) and TASK-045 (disc-aware local_index, gives a correct file_names). --dep both. Shared label upload-unmatched. DESIGN SPEC (live-API-verified 2026-06-23): docs/superpowers/specs/2026-06-23-upload-unmatched-design.md — read it; it holds the chunked-upload flow, the leaf-only-filename + no-folder constraint, the Socket.IO-only materialization, and the fork-vs-official multi-disc grouping decision. ADR docs/adr/0002-disc-aware-local-index.md.

Resolved design (grilled 2026-06-23, updated after live verification):
- Frontends: BOTH, full parity. GUI = ScanResultDialog gains per-row checkboxes + 'Upload selected'. CLI = arrow-key multi-select checklist via InquirerPy (new runtime dep; non-TTY falls back to the flag). Plus a non-interactive --upload-unmatched flag on both that uploads all resolvable games.
- Flag safety: --upload-unmatched prints a summary (games + platforms it would create) and asks y/N; --yes/-y bypasses for scripting.
- Platform resolution: resolve each unmatched game's ES-DE system dir -> RomM platform_id (invert platform_map -> slug, match GET /api/platforms). Resolvable games are selectable. Missing platform: OFFER to create (TASK-044 create_platform, existence-checked); identity auto-derived (invert platform_map -> IGDB slug + display name) and SHOWN to confirm/override before create. No IGDB slug (or create unsupported) -> game DISABLED with reason.
- Files uploaded: real rom files only; NEVER .m3u/noload.txt/.txt artifacts. Each file uploaded as a flat leaf (upload API cannot create folders). Single-file game -> one rom. Multi-disc -> upload every .cue + every .bin as separate flat leaves; the user's RomM FORK scanner coalesces loose related files into one rom (official RomM leaves them as N separate single-file roms — documented limitation, fork-independent multi-disc deferred). Orphan .m3u with no real files = unresolvable.
- Execution: mirror DownloadWorker. Sequential UploadWorker, STREAM each file from disk (TASK-044 upload_rom), per-item progress + error, whole-batch cancel, continue-on-error + per-game summary as Activity events.
- Duplicates: trust RomM's start-time filename dedup; 400 'already exists' -> skip + report (not error). No client-side fuzzy pre-check (preserves the exact/normalized/platform-scoped matching invariant).
- Post-upload (CHANGED after verification — complete returns no rom id; tasks.run scan is impossible): upload file(s) -> trigger_scan over Socket.IO (TASK-044), await scan:done with a CONFIGURABLE timeout (new SCHEMA Settings field, ~120s default); socket failure -> hand-off (basic seed + 'scan in RomM' message). On done, find the new rom(s) by fs_name (platform-scoped; /api/roms ignores platform_id param), seed mapping cache via seed_entry (full if is_identified in time, else basic 'metadata pending') so saves sync immediately, emit Activity event, drop game from picker. Game shows matched/downloaded next library load.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 scan's Unmatched report offers upload in GUI (ScanResultDialog picker), CLI (InquirerPy checklist), and a non-interactive --upload-unmatched flag with summary + y/N (--yes bypass)
- [x] #2 Each unmatched game's RomM platform is resolved; missing platform offers auto-derived create (user confirms/overrides); unresolvable games shown disabled with reason
- [x] #3 Duplicate detected at upload/start (RomM returns 400 'File <name> already exists', by filename, before any chunk) and reported as a skip (not error); no client-side fuzzy match added
- [x] #4 After a game's file(s) upload, romhop triggers a RomM scan via RommClient.trigger_scan (Socket.IO, platform-scoped, type quick) and awaits completion with a CONFIGURABLE timeout (new SCHEMA Settings field, ~120s default). On socket-unreachable it falls back to hand-off: still seed a basic mapping entry + report 'uploaded — run a Scan in RomM to finish importing'.
- [x] #5 Once materialized, the new rom(s) are found by fs_name (platform-scoped), the mapping cache is seeded via seed_entry (full metadata if is_identified within the timeout, else a BASIC entry + 'metadata pending') so saves sync immediately, an Activity event is emitted, and the game leaves the unmatched picker
- [x] #6 Real rom files only (never .m3u/noload.txt/.txt); each file uploaded as a flat leaf via the chunked flow streamed from disk in an UploadWorker mirroring DownloadWorker (per-item progress/error, whole-batch cancel, continue-on-error + per-game summary). Multi-disc = upload every .cue + every .bin as separate flat leaves; coalescing into one rom relies on the user's RomM fork scanner (documented limitation: official RomM leaves them as N separate roms)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
API + scan VERIFIED LIVE 2026-06-23 (full detail in TASK-044 notes + spec docs/superpowers/specs/2026-06-23-upload-unmatched-design.md). All test residue cleaned.

KEY CHANGES vs the original design:
- DEDUP (verified): upload/start with an existing filename on the platform -> 400 {detail:'File <name> already exists'} (by filename, pre-chunk). Skip path = catch this 400.
- UPLOAD CREATES NO ROM (verified): chunked complete returns 201 empty, no rom id; the file is only written to RomM's fs and does not appear as a rom until a scan runs.
- NO REST SCAN (verified): scan_library is manual_run:false -> tasks.run 400. Materialization is Socket.IO-only (TASK-044 trigger_scan). Post-upload flow is therefore: upload -> trigger_scan (socket) / hand-off fallback -> find rom by fs_name -> seed mapping cache -> poll is_identifying for metadata (configurable timeout). There is no immediate rom id to seed from.
- MULTI-DISC RESOLVED: x-upload-filename must be a bare leaf (a '/' path 500s), so the upload API cannot create the grouping folder. Upload every .cue + every .bin as separate flat leaves; the user's RomM FORK scanner sorts loose related files into a per-game subfolder and coalesces them into one rom. Official RomM does NOT -> stays N single-file roms (documented limitation). The 'one multi-file rom via subfolder upload' hypothesis is FALSE.
- AC#1 (disc-aware local_index) was carved into TASK-045 (no API dep, buildable now).

Implemented: platform_resolve.py (ES-DE dir→slug inversion), upload.py (Qt-free upload_game: stream files, trigger scan, seed cache), UploadWorker (mirrors DownloadWorker), ScanResultDialog enhanced (checkboxes, Upload selected, platform creation confirm, progress log), cli.py scan --upload-unmatched (InquirerPy checklist + --yes bypass), Settings.scan_timeout_seconds, ActivityKind.UPLOAD_DONE, InquirerPy dep. 554 tests pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added upload-unmatched flow: platform_resolve.py inverts platform_map to find RomM platform ids, upload.py streams files via chunked upload (artifact-filtered, dedup-as-skip, Socket.IO scan trigger, cache seed, fallback on socket error), UploadWorker mirrors DownloadWorker, ScanResultDialog gains checkboxes + upload flow with platform-create confirmation, CLI scan gets --upload-unmatched with InquirerPy checklist, scan_timeout_seconds config field, InquirerPy dep added. 554 tests pass (530 original + 24 new).
<!-- SECTION:FINAL_SUMMARY:END -->
