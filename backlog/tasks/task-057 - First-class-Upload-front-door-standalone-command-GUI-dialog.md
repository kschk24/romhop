---
id: TASK-057
title: First-class Upload front door (standalone command + GUI dialog)
status: To Do
assignee: []
created_date: '2026-06-25 17:34'
labels:
  - upload-frontdoor
dependencies: []
documentation:
  - docs/superpowers/specs/2026-06-25-upload-front-door-design.md
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make Upload-to-RomM a first-class action in both frontends instead of being reachable only through scan. Standalone CLI `upload` command (variadic names like download, --platform filter, --yes) and a standalone GUI Upload dialog, both running the match internally to discover Unmatched games (discovery only — scan keeps cache seeding). Full parity with the scan-path (create-missing-platform, unresolvable shown disabled). See design spec for grilled decisions.
<!-- SECTION:DESCRIPTION:END -->
