---
id: TASK-013.03
title: Activity log panel (session history)
status: In Progress
assignee:
  - '@claude'
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 18:09'
labels:
  - feature
  - ready-for-agent
  - activity-feedback
dependencies:
  - TASK-013.04
parent_task_id: TASK-013
priority: low
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Persistent in-app Activity log panel for the unified Activity stream. Spec: docs/superpowers/activity-feedback-spec.md. Reads the hub ring buffer; session-only, no disk persistence (distinct from the Diagnostic log file). Execute with the superpowers:executing-plans skill (/executing-plans), working from the spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUI exposes a panel listing recent sync and download events
- [x] #2 New page in the central QStackedWidget (same mechanism as Settings), toggled by a bottom-bar button
- [x] #3 Newest-first list of timestamp + message; error rows styled via is_error
- [x] #4 On open renders the ActivityHub ring buffer; live-appends via hub.event while open
- [x] #5 Session-only/in-memory; nothing written to disk; no filters/search in v1
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create src/romhop/gui/activity_log.py (ActivityLogView: QListWidget, load/append_event, error rows via setForeground)
2. Update main_window.py: add ActivityLogView to stack (index 2), add Activity bottom-bar button, show_activity_log/toggle_activity_log, connect/disconnect hub.event, update current_view_name
3. Write tests/test_gui_activity_log.py covering all 5 ACs
<!-- SECTION:PLAN:END -->
