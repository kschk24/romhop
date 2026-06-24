---
id: TASK-047
title: 'Upload too slow: chunk size latency-bound (1 chunk/sec)'
status: Done
assignee: []
created_date: '2026-06-23 17:08'
labels:
  - upload
  - perf
  - task-014
dependencies: []
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Chunked upload PUTs each chunk synchronously and waits the full server round-trip before sending the next, so throughput is ~1 chunk per RTT. With UPLOAD_CHUNK_SIZE=1 MiB that capped real-world uploads at ~1.0 MB/s regardless of bandwidth. Fix: bump default chunk size and make it configurable so users can tune to their server/reverse proxy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Default upload chunk size raised from 1 MiB to 8 MiB (8x fewer round-trips)
- [ ] #2 New upload_chunk_size_mb setting (in SCHEMA, GUI + CLI config), wired through upload_game to client.upload_rom
- [ ] #3 CLI and GUI upload paths both pass the configured chunk size
- [ ] #4 Tests cover chunk_size flowing through upload_game to the client
<!-- AC:END -->
