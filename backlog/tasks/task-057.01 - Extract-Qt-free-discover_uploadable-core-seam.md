---
id: TASK-057.01
title: Extract Qt-free discover_uploadable core seam
status: To Do
assignee: []
created_date: '2026-06-25 17:35'
labels:
  - upload-frontdoor
dependencies: []
documentation:
  - docs/superpowers/specs/2026-06-25-upload-front-door-design.md
parent_task_id: TASK-057
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract the 'find unmatched local games + categorize' logic currently inline in cli.py _run_upload_unmatched into a Qt-free, echo-free core function so CLI and GUI share it. No behavior change. See spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 discover_uploadable(local_games, romm_platforms, overrides) returns categorized {resolvable, missing_platform, unresolvable}
- [ ] #2 Function is Qt-free and echo-free (no PySide6, no typer.echo); lives in upload.py or scan.py
- [ ] #3 cli.py _run_upload_unmatched refactored to call it; existing scan-path upload behavior unchanged
- [ ] #4 Unit test covers the three categories incl. an ES-DE system that diverges from its RomM slug
<!-- AC:END -->
