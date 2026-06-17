---
id: TASK-010.08
title: update.py GitHub-Releases client core
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 09:04'
updated_date: '2026-06-17 09:20'
labels:
  - auto-update-gh-releases
  - feature
dependencies: []
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
parent_task_id: TASK-010
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Qt-free src/romhop/update.py for the GitHub-Releases self-updater (no tufup). Foundational task: the version check + download + verify the rest of the plan builds on. Reuses the approach-agnostic is_update_supported() gate and the update.py injection seam from the abandoned feature/auto-update-tufup branch. HTTP via existing httpx; version compare via existing packaging. No new runtime deps, no signing keys (TLS-only integrity). See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 is_update_supported() True only when frozen AND install_bootstrap.install_dir() is writable; False (no-op) for dev/pip
- [x] #2 update_check(current_version, include_prereleases) queries /releases/latest (stable) or /releases filtered (experimental), compares tag_name vs __version__ via packaging.version, returns UpdateInfo (target version, this-OS asset name+url+size, SHA256SUMS url) when newer else None
- [x] #3 Asset selection by OS pattern: *-setup-*.exe on Windows, *.AppImage on Linux
- [x] #4 Experimental channel picks highest version incl prereleases; stable excludes prereleases; 0.4.0rc1 rolls forward to 0.4.0
- [x] #5 download_and_apply streams asset to temp .part, verifies SHA-256 against SHA256SUMS entry (mismatch aborts), forwards progress_cb(done,total)
- [x] #6 Add update_include_prereleases: bool=False to config.py SCHEMA + default_settings()
- [x] #7 GitHub API + apply callables injectable; unit tests use fakes, no network
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Cherry-pick c605620 (auto_update_check config field) onto new branch
2. Write src/romhop/update.py from scratch per spec (no tufup):
   - UpdateInfo dataclass
   - is_update_supported() frozen+writable gate
   - update_check() /releases/latest (stable) + /releases (experimental)
   - asset selection by OS pattern
   - download_and_apply() stream+SHA256SUMS verify+exec silently
   - injectable callables for unit tests
3. Add update_include_prereleases to config.py SCHEMA + default_settings()
4. Write tests/test_update.py (no network, fakes for GH API + apply)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented update.py from spec (no tufup). is_update_supported() frozen+writable gate; update_check() hits /releases/latest (stable) or /releases (experimental); asset selection by OS pattern; download_and_apply() streams to .part, verifies SHA-256 vs SHA256SUMS, execs installer; all callables injectable. Added update_include_prereleases to config SCHEMA. 21 unit tests, 391 total pass.
<!-- SECTION:NOTES:END -->
