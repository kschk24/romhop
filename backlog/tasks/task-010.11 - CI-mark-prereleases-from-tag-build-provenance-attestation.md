---
id: TASK-010.11
title: 'CI: mark prereleases from tag + build-provenance attestation'
status: Done
assignee: []
created_date: '2026-06-17 09:05'
updated_date: '2026-06-17 09:36'
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
- [x] #1 softprops/action-gh-release marks prerelease from tag: prerelease: ${{ contains(github.ref_name, '-') }} (hyphenated semver tag = beta, clean = stable)
- [x] #2 actions/attest-build-provenance attaches a provenance attestation over the installer assets (emits .sigstore.json; gh attestation verify)
- [x] #3 No tufup publish step, no Actions secrets, no key handling
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added prerelease flag (contains('-') on ref_name) to softprops/action-gh-release. Added actions/attest-build-provenance@v2 step. Added id-token:write+attestations:write to top-level permissions. No signing keys, no secrets.
<!-- SECTION:NOTES:END -->
