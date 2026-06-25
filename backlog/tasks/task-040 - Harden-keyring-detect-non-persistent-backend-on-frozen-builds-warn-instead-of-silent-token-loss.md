---
id: TASK-040
title: >-
  Keyring-only token: detect non-persisting backend on desktop, warn
  session-only instead of silent loss
status: To Do
assignee: []
created_date: '2026-06-22 16:18'
updated_date: '2026-06-25 19:01'
labels:
  - bug
  - keyring
dependencies: []
priority: medium
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Keyring-only token storage hardening. romhop stores the RomM API token only in the OS keyring (see docs/adr/0004-keyring-only-token-storage.md). On a desktop frozen build with no running keyring daemon (e.g. Linux AppImage under a bare WM), keyring.set_password can silently no-op and get_password later returns None, so the token appears lost and the user re-enters it every launch with no explanation. config.py:326-331 currently does raw set/get with no detection. Harden set_token to detect non-persistence and let callers warn the user, keeping the session usable via the in-memory RommClient. Env-var (former TASK-058) and encrypted-file fallbacks were considered and rejected per ADR 0004; headless use is out of scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 config.set_token writes then reads back the token and raises a typed TokenPersistenceError when the keyring did not persist it (covers both NoKeyringError and the silent-no-op / get-returns-None daemon-down case), instead of silently succeeding.
- [ ] #2 All set_token callers (CLI login, CLI setup, GUI setup wizard, GUI settings view) catch TokenPersistenceError and surface a clear session-only warning; the running session keeps working because the live RommClient holds the token in memory independently.
- [ ] #3 config.get_token stays str|None with no read-side backend probe — the guard is concentrated at the save moment, not duplicated on every read.
- [ ] #4 Behaviour is covered by tests using a faked keyring backend (no real OS keyring): persist-ok, silent-no-op (set returns None on readback), and raises-NoKeyringError paths.
- [ ] #5 Decision recorded in docs/adr/0004-keyring-only-token-storage.md; env-var and encrypted-file fallbacks explicitly rejected and headless declared out of scope.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision settled via grill-with-docs 2026-06-25 (ADR 0004). Was ready-for-human (blocked on fallback-policy choice); policy now decided = keyring-only + session-only-warn, so this is delegatable. TASK-058 (env-var fallback) closed/archived as out-of-scope by the same decision.
<!-- SECTION:NOTES:END -->
