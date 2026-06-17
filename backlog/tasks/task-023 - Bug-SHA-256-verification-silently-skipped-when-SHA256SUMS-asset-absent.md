---
id: TASK-023
title: 'Bug: SHA-256 verification silently skipped when SHA256SUMS asset absent'
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 13:02'
updated_date: '2026-06-17 13:31'
labels:
  - bug
  - security
  - update
  - ready-for-agent
dependencies: []
priority: high
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
update.py download_and_apply() skips integrity check when sha256sums_url is empty. _sha256sums_url() returns '' if no SHA256SUMS asset exists in release; lines 251-254 set sha_content=''; lines 266-267 skip _verify_sha256 entirely. A misconfigured release causes unverified installer binary to execute silently. Found in code review of TASK-010.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 download_and_apply raises explicit error when sha256sums_url is empty, before apply_fn is called
- [x] #2 Error message names SHA256SUMS as missing for maintainer diagnosis
- [x] #3 Test: download_and_apply with sha256sums_url='' raises before apply_fn called
- [x] #4 Existing happy-path and hash-mismatch tests still pass
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Raise ValueError in download_and_apply when sha256sums_url is empty, before any download\n2. Remove if sha_content guard — make _verify_sha256 unconditional\n3. Update test_download_and_apply_no_sha256sums_skips_verify to expect ValueError before apply_fn called
<!-- SECTION:PLAN:END -->
