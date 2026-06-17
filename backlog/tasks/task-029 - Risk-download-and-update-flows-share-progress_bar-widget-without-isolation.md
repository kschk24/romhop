---
id: TASK-029
title: 'Risk: download and update flows share progress_bar widget without isolation'
status: To Do
assignee: []
created_date: '2026-06-17 13:05'
updated_date: '2026-06-17 13:09'
labels:
  - bug
  - update
  - gui
  - needs-triage
dependencies: []
priority: low
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
main_window.py _on_update_progress (line 612) and _on_item_progress share self.progress_bar and self._PROGRESS_SCALE. If a download batch is in flight when an update apply starts (or vice versa), both write to the same widget simultaneously. If either side changes its range or format, the other breaks silently — this already happened with the large-ROM overflow fix (TASK overflow bug). Each flow should own its own progress widget or the shared bar should have explicit owner tracking. Found in code review of TASK-010.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Download progress and update progress cannot interfere: either separate widgets or explicit mutex/owner state
- [ ] #2 Starting an update apply while a download is in progress does not corrupt the download bar display
- [ ] #3 Existing download progress tests pass
<!-- AC:END -->
