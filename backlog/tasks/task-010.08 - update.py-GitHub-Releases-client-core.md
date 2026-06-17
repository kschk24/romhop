---
id: TASK-010.08
title: update.py GitHub-Releases client core
status: To Do
assignee: []
created_date: '2026-06-17 09:04'
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
- [ ] #1 is_update_supported() True only when frozen AND install_bootstrap.install_dir() is writable; False (no-op) for dev/pip
- [ ] #2 update_check(current_version, include_prereleases) queries /releases/latest (stable) or /releases filtered (experimental), compares tag_name vs __version__ via packaging.version, returns UpdateInfo (target version, this-OS asset name+url+size, SHA256SUMS url) when newer else None
- [ ] #3 Asset selection by OS pattern: *-setup-*.exe on Windows, *.AppImage on Linux
- [ ] #4 Experimental channel picks highest version incl prereleases; stable excludes prereleases; 0.4.0rc1 rolls forward to 0.4.0
- [ ] #5 download_and_apply streams asset to temp .part, verifies SHA-256 against SHA256SUMS entry (mismatch aborts), forwards progress_cb(done,total)
- [ ] #6 Add update_include_prereleases: bool=False to config.py SCHEMA + default_settings()
- [ ] #7 GitHub API + apply callables injectable; unit tests use fakes, no network
<!-- AC:END -->
