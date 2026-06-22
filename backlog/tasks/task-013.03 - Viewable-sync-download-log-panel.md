---
id: TASK-013.03
title: Activity log panel (session history)
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 17:33'
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
- [ ] #1 GUI exposes a panel listing recent sync and download events
- [ ] #2 New page in the central QStackedWidget (same mechanism as Settings), toggled by a bottom-bar button
- [ ] #3 Newest-first list of timestamp + message; error rows styled via is_error
- [ ] #4 On open renders the ActivityHub ring buffer; live-appends via hub.event while open
- [ ] #5 Session-only/in-memory; nothing written to disk; no filters/search in v1
<!-- AC:END -->
