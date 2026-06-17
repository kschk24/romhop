---
id: TASK-010.09
title: 'Apply mechanism: silent installer re-run'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-17 09:04'
updated_date: '2026-06-17 09:20'
labels:
  - auto-update-gh-releases
  - packaging
dependencies:
  - TASK-010.08
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
parent_task_id: TASK-010
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Apply a downloaded update by re-running the OS installer silently, so the installer owns the file-replace-while-running problem (no hand-rolled onedir swap / Windows locked-exe dance). Touches packaging seams. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Windows: exec romhop-setup-X.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES; upgrades in place per-user, no UAC; then app exits for relaunch
- [ ] #2 Add explicit AppId={{GUID}} to packaging/windows/romhop.iss (hardening so an AppName change cannot orphan installs)
- [ ] #3 Linux: chmod +x downloaded .AppImage and run via --appimage-bootstrap; make install_bootstrap bootstrap idempotent + non-interactive so it upgrades ~/.local/lib/romhop headlessly
- [ ] #4 Relaunch the installed app after the installer completes; installer non-zero exit surfaces update-failed and keeps current install
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add AppId GUID to packaging/windows/romhop.iss
2. Make install_bootstrap --appimage-bootstrap path idempotent + non-interactive (accepts --upgrade or detects upgrade and skips prompts)
3. Expose relaunch logic in update.py download_and_apply (after installer succeeds, relaunch installed binary)
4. Tests: apply_installer called with right flags; relaunch after installer; non-zero exit raises
<!-- SECTION:PLAN:END -->
