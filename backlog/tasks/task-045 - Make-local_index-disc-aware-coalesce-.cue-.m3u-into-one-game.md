---
id: TASK-045
title: Make local_index disc-aware (coalesce .cue/.m3u into one game)
status: Done
assignee:
  - '@claude'
created_date: '2026-06-23 15:38'
updated_date: '2026-06-23 15:55'
labels:
  - feature
  - upload-unmatched
dependencies: []
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Carved out of TASK-014 (was its AC#1) so it can ship now with no RomM API dependency. Make local_index parse .cue (-> referenced .bin/track files) and .m3u (-> disc descriptors) and COALESCE a descriptor plus its referenced files into a single LocalGame, suppressing the referenced files as standalone games. Fixes scan's Unmatched report everywhere (a flat .cue+.bin disc game no longer splits into a .cue 'game' + orphan .bin 'games') and gives the upload feature (TASK-014) a correct file_names (every .cue + every .bin). Design spec: docs/superpowers/specs/2026-06-23-upload-unmatched-design.md ; ADR docs/adr/0002-disc-aware-local-index.md. Shared label upload-unmatched. Deviates from local_index's prior 'one file = one game' rule and means the indexer now reads file CONTENTS (cue/m3u bodies), not just names.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 local_index parses .cue and reads its referenced .bin/track file names
- [x] #2 local_index parses .m3u and reads its referenced disc descriptors
- [x] #3 A descriptor (.cue or .m3u) and its referenced files coalesce into ONE LocalGame; the referenced files no longer appear as standalone games
- [x] #4 A flat .cue+.bin disc game placed directly in a <system>/ dir resolves to one Unmatched game, not several
- [x] #5 The coalesced LocalGame exposes its full real-file set (every .cue + every .bin) for upload; ES-DE artifacts (.m3u/noload.txt/.txt) are excluded from that file set
- [x] #6 Missing referenced files are tolerated with a warning (do not crash; report which file is absent)
- [x] #7 Ships test-first with .cue and .m3u fixtures covering flat single-disc, multi-disc, and a missing-referenced-file case
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write failing tests for all 7 ACs (cue+bin coalesce, m3u multi-disc, missing-ref warning, ES-DE artifact exclusion)
2. Add _parse_cue + _parse_m3u helpers to local_index.py
3. Rewrite flat-file loop: orphan-m3u pass → cue pass → remainder pass; build suppressed set
4. Run full suite, fix any regressions
5. Update CHANGELOG.md Unreleased section
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented _parse_cue + _parse_m3u helpers. Rewrote flat-file section as 3 passes (m3u → cue → remainder). suppressed set prevents referenced files becoming standalone games. match_key uses stem for .cue games to hit fs_name_no_ext. 8 new tests, all 7 ACs green. 513/513 tests pass.
<!-- SECTION:NOTES:END -->
