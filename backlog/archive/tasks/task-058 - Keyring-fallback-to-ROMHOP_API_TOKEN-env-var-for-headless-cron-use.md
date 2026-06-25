---
id: TASK-058
title: Keyring fallback to ROMHOP_API_TOKEN env var for headless/cron use
status: To Do
assignee: []
created_date: '2026-06-25 18:01'
updated_date: '2026-06-25 19:01'
labels:
  - architecture-analysis
  - Enhancement
dependencies: []
priority: high
ordinal: 79000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Source: architecture review consensus (rhanalysis2/4). get_token() in config.py:331 is keyring-only; breaks in headless/Docker/cron (no D-Bus). Add an env-var fallback so the CLI works server-side.

Resolution order: explicit env ROMHOP_API_TOKEN > keyring. Keep keyring as the GUI/desktop default. Document the env path + security caveat (plaintext in env) in README.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 get_token() returns ROMHOP_API_TOKEN when set, else falls back to keyring
- [ ] #2 Empty/unset env var does not shadow a valid keyring token
- [ ] #3 README documents headless/cron usage and the plaintext-env security caveat
- [ ] #4 Test covers env-set, env-empty, and keyring-only paths
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Closed as out-of-scope 2026-06-25. Headless/cron/Docker use is not a romhop target; env-var token would put the credential in plaintext in the process environment for no in-scope benefit. Decision recorded in docs/adr/0004-keyring-only-token-storage.md; the in-scope desktop keyring-failure hardening lives in TASK-040.
<!-- SECTION:NOTES:END -->
