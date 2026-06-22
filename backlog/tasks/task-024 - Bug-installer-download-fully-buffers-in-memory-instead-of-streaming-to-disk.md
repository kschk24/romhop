---
id: TASK-024
title: 'Bug: installer download fully buffers in memory instead of streaming to disk'
status: To Do
assignee: []
created_date: '2026-06-17 13:02'
updated_date: '2026-06-22 16:53'
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
- [x] #1 _default_get_bytes replaced: chunks written directly to .part file as they arrive (no in-memory accumulation)
- [x] #2 SHA-256 computed incrementally during download (no path.read_bytes() after write)
- [x] #3 progress_cb still called with accurate (bytes_done, bytes_total) on each chunk
- [x] #4 Test: fake get_bytes with multiple chunks verifies correct hash and no full-buffer
- [x] #5 Existing download_and_apply tests pass
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Change _verify_sha256(path, ...) → _verify_sha256(digest, ...) — no path.read_bytes()
2. Add _default_stream_asset(url, dest, cb) -> str: streams to dest path, updates sha256 incrementally, returns hex digest
3. Add _gh_stream_asset injectable to download_and_apply; keep _gh_get_bytes for SHA256SUMS (backward compat)
4. _default_get_bytes becomes simple httpx.get for the small SHA256SUMS file
5. Update existing tests to inject _gh_stream_asset fakes
6. Add AC4 test: multi-chunk fake stream_asset verifies incremental hash and per-chunk writes
<!-- SECTION:PLAN:END -->
