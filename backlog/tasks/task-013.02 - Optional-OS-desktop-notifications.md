---
id: TASK-013.02
title: Desktop notification renderer (opt-in)
status: Done
assignee:
  - '@claude'
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 18:03'
labels:
  - feature
  - ready-for-agent
  - activity-feedback
dependencies:
  - TASK-013.04
parent_task_id: TASK-013
priority: low
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Opt-in OS desktop-notification renderer for the unified Activity stream. Spec: docs/superpowers/activity-feedback-spec.md. Reuses the existing tray.showMessage; focus-gated. Execute with the superpowers:executing-plans skill (/executing-plans), working from the spec.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 User can enable/disable desktop notifications in settings
- [x] #2 Notifications fire for sync pushes, completed downloads, and errors
- [x] #3 New FieldSpec desktop_notifications (behavior group, bool, default False); toggle shown but disabled with hint when no system tray available
- [x] #4 Fires via tray.showMessage for all 3 kinds, subscribed to ActivityHub.event
- [x] #5 Focus-gated: only fires when romhop is not the focused window (minimized/hidden-to-tray/backgrounded)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. config.py: add desktop_notifications bool field to Settings + FieldSpec in SCHEMA (behavior group)
2. settings_view.py: add DESKTOP_NOTIF_LABEL constant + set_desktop_notifications_available(available, hint) method to disable/hint the checkbox when no tray
3. main_window.py: connect activity_hub.event to _on_activity_desktop_notify; check desktop_notifications setting + focus gate + tray; disable toggle in settings_view if no tray at init
4. tests/test_gui_desktop_notif.py: fires when unfocused, gated when focused, gated by setting, no-tray no-fire, toggle disabled when no tray
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
490 tests pass (was 480, +10 new). Settings field desktop_notifications added to Settings dataclass + SCHEMA. SettingsView.set_desktop_notifications_available() disables checkbox + tooltip; disabled state survives reset(). MainWindow._on_activity_desktop_notify: checks setting + tray + focus gate before calling tray.showMessage. test_config.py expected set updated.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added desktop_notifications bool to Settings/SCHEMA. settings_view: set_desktop_notifications_available disables toggle with hint when no tray. main_window: _on_activity_desktop_notify wired to activity_hub.event, focus-gated, uses Critical/Information icon per is_error. MainWindow disables toggle at init when tray unavailable. 10 tests. All 490 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
