---
id: TASK-023
title: 'Bug: SHA-256 verification silently skipped when SHA256SUMS asset absent'
status: To Do
assignee: []
created_date: '2026-06-17 13:02'
updated_date: '2026-06-17 13:09'
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
- [ ] #1 download_and_apply raises explicit error when sha256sums_url is empty, before apply_fn is called
- [ ] #2 Error message names SHA256SUMS as missing for maintainer diagnosis
- [ ] #3 Test: download_and_apply with sha256sums_url='' raises before apply_fn called
- [ ] #4 Existing happy-path and hash-mismatch tests still pass
<!-- AC:END -->
