---
id: TASK-013.01
title: Toast renderer for Activity events
status: Done
assignee:
  - '@claude'
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 17:59'
labels:
  - feature
  - ready-for-agent
  - activity-feedback
dependencies:
  - TASK-013.04
parent_task_id: TASK-013
priority: low
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Transient in-app Toast renderer for the unified Activity stream. Spec: docs/superpowers/activity-feedback-spec.md. Subscribes to ActivityHub.event; presentation policy (cap/sticky) lives here, not in the event stream. Execute with the superpowers:executing-plans skill (/executing-plans), working from the spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Successful sync push shows a transient bottom-right toast in the GUI
- [x] #2 Toast wired via existing watch_and_push on_event hook
- [x] #3 Frameless ToastWidget overlay anchored bottom-right above the bottom bar, owned by MainWindow
- [x] #4 Fires for all 3 kinds (sync-push, download-done, error), subscribed to ActivityHub.event
- [x] #5 Capped stack of 3; info kinds auto-dismiss ~4s; error toasts are sticky (dismiss on click)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create src/romhop/gui/toast.py: ToastWidget (frameless child QFrame, 4s auto-dismiss, error sticky, click-dismiss) + ToastManager (cap-3 stack, bottom-right above bottom bar, reposition on add/remove)
2. Update main_window.py: init ToastManager, subscribe activity_hub.event, override resizeEvent to reposition
3. Add tests/test_gui_toast.py: dismiss, error-sticky, cap, manager wiring
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
480 tests pass (was 470, +10 new toast tests). ToastWidget: child QFrame overlay, 4s QTimer auto-dismiss for info, no timer for errors, click-dismiss always. ToastManager: cap-3 stack, oldest evicted when full, reposition on add/remove/resize.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/romhop/gui/toast.py (ToastWidget + ToastManager). Wired into MainWindow: ToastManager created, activity_hub.event → post, resizeEvent repositions stack. 10 tests in tests/test_gui_toast.py cover timer, sticky, cap, dismiss, manager. All 480 tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
