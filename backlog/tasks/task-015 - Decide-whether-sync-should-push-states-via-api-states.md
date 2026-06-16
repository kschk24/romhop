---
id: TASK-015
title: Decide whether sync should push states via /api/states
status: To Do
assignee: []
created_date: '2026-06-16 15:07'
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
- [ ] #1 Decision recorded: keep states-under-saves or move to /api/states
- [ ] #2 If changing, migration of existing states-under-saves considered
<!-- AC:END -->
