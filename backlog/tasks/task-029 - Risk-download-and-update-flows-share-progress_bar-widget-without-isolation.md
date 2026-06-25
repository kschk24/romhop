---
id: TASK-029
title: 'Risk: download and update flows share progress_bar widget without isolation'
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 13:05'
updated_date: '2026-06-25 17:33'
labels:
  - bug
  - update
  - gui
  - ready-for-agent
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
- [x] #1 Download progress and update progress cannot interfere: either separate widgets or explicit mutex/owner state
- [x] #2 Starting an update apply while a download is in progress does not corrupt the download bar display
- [x] #3 Existing download progress tests pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach: shared progress bar, owner-gated, update preempts

Single `self.progress_bar`/`self.progress_label` stays. Add owner state so download and update flows can never stomp each other's bar.

### Owner state
- `self._progress_owner` in {None, "download", "update"}.
- `_claim_progress(owner)`: set owner + show bar.
- `_release_progress(owner)`: hide + clear owner ONLY if `self._progress_owner == owner` (stale callbacks can't release a bar they no longer own).

### Owner-gate every bar/label mutation (both flows)
Show, hide, setFormat/setMaximum/setValue, AND the "Download cancelled" label all early-return when `self._progress_owner != <their owner>`. Loser's stale callbacks may still touch their own buttons/workers, never the bar.
- Download: `_begin_progress`, `_on_item_started`, `_on_item_progress`, `_on_item_error`, `_end_progress` gate on owner == "download".
- Update: `_on_update_progress`, `_on_update_applied` gate on owner == "update".

### Update preempts (always wins)
`_on_update_clicked`: if a download worker is live, call `self._download_worker.cancel()`, then `_claim_progress("update")` and write "Updating…". Download yields; partial `.part` aborts (app relaunches anyway).

### Late download teardown stays safe
`_on_batch_finished` / `_end_progress` no-op their bar+label calls when owner != "download" (gated), but STILL clean up the worker and re-enable download_btn. So the cancelled download's late `finished` signal can't hide the now-update-owned bar.

### Download refused during update
`_start_download` early-returns when owner == "update". `download_btn` greyed while update owns the bar.

### Update terminal paths release the bar
- Failure (`_on_update_failed`): `_release_progress("update")` + re-enable download_btn (control returns to app; today it leaves the bar stuck at "Updating…" — latent bug, fixed here).
- Success (`_on_update_applied`): relaunch follows, cleanup moot.

### Out of scope
- Pull flow: uses dialogs/QMessageBox, not the bar — untouched.
- Background update *check* (`check_for_updates`): never touches the bar — untouched.

### AC#2 note
Satisfied via preempt-and-cancel: starting an update apply cancels the in-flight download and hands the bar to update cleanly. No garbled simultaneous writes (the "corruption"); download outcome changes (it yields) rather than the two coexisting.

### Tests (pytest-qt)
1. `test_update_apply_cancels_active_download` — start download, click update; assert worker.cancel() called, owner == "update", bar format == "Updating…".
2. `test_late_download_teardown_does_not_hide_update_bar` — fire `_on_batch_finished` after update claimed bar; assert bar still visible + still update's format.
3. `test_download_start_refused_during_update` — owner == "update"; call `_start_download`; assert no worker spawned + download_btn disabled.
4. `test_update_failure_releases_bar` — apply then fail; assert bar hidden, owner None, download_btn enabled.
5. Existing download progress tests unchanged and green (AC#3).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented _claim_progress/_release_progress owner-gating. All 612 tests pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added _progress_owner state + _claim_progress/_release_progress helpers. All download and update slot mutations gate on owner. _on_update_clicked cancels in-flight download before claiming bar. _on_update_failed releases bar + re-enables download_btn (latent stuck-bar bug fixed). _start_download no-ops when owner==update. 4 new isolation tests added; all 612 tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
