---
id: TASK-010
title: Auto-update for frozen installers (GitHub Releases)
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-17 09:06'
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
- [ ] #1 Frozen build checks for and applies updates via tufup
- [ ] #2 Update flow works on Windows and Linux frozen builds
- [ ] #3 Update flow works on Windows and Linux frozen builds
- [ ] #4 Opt-in experimental channel (prerelease releases) gated by update_include_prereleases setting (default off)
- [ ] #5 TLS-only: no signing keys; downloaded asset verified against published SHA256SUMS before running
- [ ] #6 Frozen build checks GitHub Releases on launch and applies an update via silent installer re-run, then relaunches
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Research 2026-06-17 (tufup-example): hosting blocker RESOLVED — metadata_base_url & target_base_url are independent Client args (demo only looks nested due to http.server -d). All tufup filenames flat → single flat tuf-repo release works (metadata_base==target_base==release download URL); split-host (metadata→Pages/raw, targets→Release assets) is config-only fallback. Repo-side = init/add_bundle scripts mapping to update_repo.py init/publish. root.json bundled via spec datas; check_for_updates + download_and_apply_update(progress_hook) confirm update.py surface. See docs/superpowers/specs/2026-06-16-auto-update-tufup-design.md Research findings section. Resume: checkout feature/auto-update-tufup + git stash pop.
<!-- SECTION:NOTES:END -->
