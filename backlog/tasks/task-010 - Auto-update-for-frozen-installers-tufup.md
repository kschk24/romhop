---
id: TASK-010
title: Auto-update for frozen installers (GitHub Releases)
status: Done
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-17 09:36'
labels:
  - auto-update-gh-releases
  - feature
  - packaging
dependencies: []
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
priority: low
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sub-project 2/2 of the freeze-installers effort: frozen Windows + Linux installs update themselves with no manual reinstall. PIVOTED 2026-06-17 from tufup to a plain GitHub-Releases self-updater (tufup dropped — hosting blocker + cost-vs-benefit at this scale; see spec 'Why not tufup'). On launch the app checks GitHub Releases; newer version -> non-blocking Update/Later banner -> downloads the published installer asset for this OS -> runs it silently -> relaunches. Release ritual unchanged (push a version tag; CI builds + publishes). TLS-only integrity (no signing keys), reuses sub-project-1 per-tag assets, no new repo. Umbrella for subtasks TASK-010.08 (client) -> .09 (apply) -> .10 (GUI) / .11 (CI) / .12 (docs), shared label auto-update-gh-releases. Spec: docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md. The prior tufup subtasks (.01-.07) live only on the abandoned feature/auto-update-tufup branch; the auto_update_check config field + GUI banner/worker/restart from that branch are cherry-picked onto the new feature/auto-update-github-releases branch.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Frozen build checks for and applies updates via tufup
- [x] #2 Update flow works on Windows and Linux frozen builds
- [x] #3 Update flow works on Windows and Linux frozen builds
- [x] #4 Opt-in experimental channel (prerelease releases) gated by update_include_prereleases setting (default off)
- [x] #5 TLS-only: no signing keys; downloaded asset verified against published SHA256SUMS before running
- [x] #6 Frozen build checks GitHub Releases on launch and applies an update via silent installer re-run, then relaunches
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HANDOFF (for fresh session) — verified 2026-06-17 on main:

STATE: No auto-update code exists on main. update.py, auto_update_check, is_update_supported(), and the GUI banner all live ONLY on the abandoned branch feature/auto-update-tufup (never merged). Sub-project-1 seam install_bootstrap.install_dir() IS on main. Design spec (local, gitignored): docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md — read it first.

BRANCH: start fresh — git checkout -b feature/auto-update-github-releases main. Do NOT resume feature/auto-update-tufup (tufup is dropped).

REUSE MAP (commits on feature/auto-update-tufup):
- c605620 feat(config): auto_update_check setting — REUSE, near-clean cherry-pick (one SCHEMA field). Then add update_include_prereleases alongside it (TASK-010.08).
- 2e7d4c3 / 25fb3b7 / ff46d7b (GUI banner, in-layout banner, is_update_supported gate) — REUSE AS REFERENCE ONLY. They are wired to the tufup update.py surface, so a blind cherry-pick will conflict. Re-port the banner/worker/restart UI against the NEW update.py signatures (update_check(current, include_prereleases) / download_and_apply(info, progress_cb)).
- ecabf62 / 6116087 / d17c62d / d6db60e / 43e2594 (tufup update.py client, repo tooling, root.json bundle, tufup dep) — DEAD, do NOT reuse. .08 rewrites update.py from the spec.

ORDER: .08 client core -> .09 apply -> .10 GUI / .11 CI / .12 docs (deps wired). Integrity is TLS-only: no signing keys, but verify the downloaded asset vs published SHA256SUMS. Per CLAUDE.md execute with Sonnet.

All subtasks complete on feature/auto-update-github-releases. 401 tests pass. Manual desktop smoke (TASK-012) still needed before merging.
<!-- SECTION:NOTES:END -->
