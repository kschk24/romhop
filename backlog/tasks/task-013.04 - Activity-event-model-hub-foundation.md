---
id: TASK-013.04
title: Activity event model + hub (foundation)
status: Done
assignee:
  - '@claude'
created_date: '2026-06-22 17:28'
updated_date: '2026-06-22 17:54'
labels:
  - feature
  - ready-for-agent
  - activity-feedback
dependencies: []
parent_task_id: TASK-013
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Foundation for the unified Activity-feedback model. Spec: docs/superpowers/activity-feedback-spec.md. Qt-free core event model + GUI aggregation hub that all three renderers (toast/.01, desktop notif/.02, activity log/.03) sit on. Renders nothing itself. Execute with the superpowers:executing-plans skill (/executing-plans), working from the spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New Qt-free module src/romhop/activity.py defines ActivityEvent (frozen dataclass: kind, message, tz-aware timestamp, is_error property) + ActivityKind enum (SYNC_PUSH, DOWNLOAD_DONE, ERROR)
- [x] #2 Core emits on success, raises on failure: sync.py emits SYNC_PUSH via on_event, download.py emits DOWNLOAD_DONE; messages pre-rendered by core
- [x] #3 ActivityHub QObject (owned by MainWindow) exposes event=Signal(object); SyncWorker/DownloadWorker/error catch-sites each funnel ActivityEvents into it via queued cross-thread signal
- [x] #4 Hub keeps a capped in-memory ring buffer (~200) for the Activity log to read
- [x] #5 Error ActivityEvents constructed at GUI catch-sites reusing friendly_download_error; DownloadCancelled emits nothing
- [x] #6 cli.py on_event updated to read e.message (callback now receives ActivityEvent, not Path)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create src/romhop/activity.py (ActivityKind + ActivityEvent)
2. Update sync.py to emit ActivityEvent via on_event
3. Update download.py to add on_event param, emit DOWNLOAD_DONE
4. Create src/romhop/gui/activity_hub.py (ActivityHub QObject + ring buffer)
5. Update gui/workers.py: SyncWorker gets activity signal + passes on_event; DownloadWorker gets activity signal + passes on_event kwarg + emits ERROR
6. Update gui/app.py: sync_watch_fn + download_action accept on_event
7. Update gui/main_window.py: create ActivityHub, wire worker.activity to hub
8. Update cli.py on_event lambda to read e.message
9. Update test lambdas to accept on_event=None
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
All 470 tests pass. ActivityEvent/ActivityKind in activity.py, ActivityHub in gui/activity_hub.py, SyncWorker+DownloadWorker activity signals wired to hub, download.py+sync.py emit events, cli.py on_event updated.
<!-- SECTION:NOTES:END -->
