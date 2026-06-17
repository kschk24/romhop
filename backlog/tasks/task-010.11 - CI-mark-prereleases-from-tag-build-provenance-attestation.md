---
id: TASK-010.11
title: 'CI: mark prereleases from tag + build-provenance attestation'
status: To Do
assignee: []
created_date: '2026-06-17 09:05'
labels:
  - auto-update-gh-releases
  - packaging
dependencies: []
references:
  - docs/superpowers/specs/2026-06-17-auto-update-github-releases-design.md
parent_task_id: TASK-010
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the existing release job in .github/workflows/package.yml. No new workflow, no signing keys/secrets, no publish-back step. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 softprops/action-gh-release marks prerelease from tag: prerelease: ${{ contains(github.ref_name, '-') }} (hyphenated semver tag = beta, clean = stable)
- [ ] #2 actions/attest-build-provenance attaches a provenance attestation over the installer assets (emits .sigstore.json; gh attestation verify)
- [ ] #3 No tufup publish step, no Actions secrets, no key handling
<!-- AC:END -->
