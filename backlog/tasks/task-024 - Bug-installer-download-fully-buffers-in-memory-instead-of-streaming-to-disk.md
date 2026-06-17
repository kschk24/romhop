---
id: TASK-024
title: 'Bug: installer download fully buffers in memory instead of streaming to disk'
status: To Do
assignee: []
created_date: '2026-06-17 13:02'
updated_date: '2026-06-17 13:09'
labels:
  - bug
  - update
  - performance
  - ready-for-agent
dependencies: []
priority: medium
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
update.py _default_get_bytes() (line 232) accumulates all 65536-byte chunks into a list then joins with b''.join() before writing to disk. For a 200MB AppImage this holds the full installer in RAM with no ability to cancel mid-write. Also _verify_sha256 (line 188) calls path.read_bytes() which re-loads the full file from disk instead of streaming the hash. Both should stream: write chunks directly to the .part temp file (as download.py already does) and feed hashlib incrementally during download. Found in code review of TASK-010.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 _default_get_bytes replaced: chunks written directly to .part file as they arrive (no in-memory accumulation)
- [ ] #2 SHA-256 computed incrementally during download (no path.read_bytes() after write)
- [ ] #3 progress_cb still called with accurate (bytes_done, bytes_total) on each chunk
- [ ] #4 Test: fake get_bytes with multiple chunks verifies correct hash and no full-buffer
- [ ] #5 Existing download_and_apply tests pass
<!-- AC:END -->
