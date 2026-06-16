---
id: TASK-001
title: Validate roms_root before download; friendly error instead of raw traceback
status: To Do
assignee: []
created_date: '2026-06-16 15:03'
updated_date: '2026-06-16 15:44'
labels:
  - bug
  - cli
dependencies: []
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Downloads are NOT broken in the frozen build — earlier 'frozen Linux downloads broken' diagnosis was wrong. Real cause: user had roms_root set to an unwritable/nonexistent path (/home/Games/Emulator), so download_rom's system_dir.mkdir(parents=True) raised PermissionError: [Errno 13] Permission denied: '/home/Games' and dumped a raw Rich traceback. romhop never checks roms_root is set to a usable (existing-or-creatable, writable) directory and gives no friendly feedback. Affects CLI download and GUI (silent failure in worker thread).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 download_rom / pre-download path validates roms_root is usable (creatable + writable) before streaming
- [ ] #2 Unusable roms_root yields a clear actionable error (which path, why) — no raw traceback in CLI
- [ ] #3 GUI surfaces the same error to the user instead of failing silently in the worker
- [ ] #4 Setup wizard / settings ideally validate roms_root writability when set
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-06-16 15:44
---
Diagnosis 2026-06-16: reproduced via 'romhop download "Sonic Advance 2"'. roms_root was /home/Games/Emulator/gba. Traceback chain: download.py:117 system_dir.mkdir(parents=True, exist_ok=True) -> pathlib mkdir recursion up to /home/Games -> PermissionError [Errno 13] Permission denied: '/home/Games'. So the frozen build downloads fine; this was a config/path-validation + error-UX bug, not a packaging/TLS bug. Repurposed from old 'frozen Linux AppImage downloads broken / certifi' framing.
---
<!-- COMMENTS:END -->
