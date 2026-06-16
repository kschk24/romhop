---
id: TASK-015
title: Decide whether sync should push states via /api/states
status: Done
assignee: []
created_date: '2026-06-16 15:07'
updated_date: '2026-06-16 16:35'
labels:
  - investigation
dependencies: []
priority: low
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Confirmed live 2026-06-14: RomM /api/saves?rom_id= returns BOTH .srm and .state files (emulator=core); /api/states is empty. So sync's upload_save is the only path and states live under saves on the server. pull works around this by routing downloaded files to saves/states dirs by file EXTENSION, not endpoint. Open question: should sync upload .state* via a dedicated /api/states endpoint instead? Would split future data and orphan existing states-under-saves; needs thought before changing. Not urgent; pull handles current reality. Decision task, not necessarily code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Decision recorded: keep states-under-saves or move to /api/states
- [x] #2 If changing, migration of existing states-under-saves considered
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision: MOVE states to /api/states. Shipped commit 2104fc9 (gui-desktop-pyside).

- Added RommClient.upload_state -> POST /api/states (stateFile field, rom_id+emulator params), mirrors upload_save.
- push_save_file routes by extension: is_state_file(name) -> upload_state, else upload_save.
- Replaced fixed STATE_EXTS set (.state,.state1-9) with regex \.state\d*$ so multi-digit RetroArch slots (.state10/.state995) detected; previously unmatched = silently skipped. .png state thumbnails still ignored.

Migration (AC#2): existing states already under /api/saves on the server are NOT auto-migrated server-side. pull.py keeps extension-based routing (now via is_state_file) so those legacy states still download into states_dir locally. New states from now on land in /api/states. Verified live: state push confirmed by user.
<!-- SECTION:NOTES:END -->
