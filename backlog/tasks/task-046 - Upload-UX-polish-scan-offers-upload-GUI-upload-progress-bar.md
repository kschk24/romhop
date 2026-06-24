---
id: TASK-046
title: 'Upload UX polish: scan offers upload + GUI upload progress bar'
status: Done
assignee:
  - '@me'
created_date: '2026-06-23 16:51'
updated_date: '2026-06-23 17:00'
labels:
  - task-014
  - upload
  - gui
dependencies: []
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two gaps in the freshly-shipped scan->upload flow (TASK-014). (1) Plain 'romhop scan' never offers to upload unmatched games -- upload only runs when --upload-unmatched is passed, so users who just run 'romhop scan' get no prompt. (2) The GUI upload progress in ScanResultDialog is an indeterminate spinner (setMaximum(0)) showing only cumulative bytes that reset per file -- unlike the download bar which is a determinate permille bar showing 'name (i/n) sent/total rate'. Make upload feedback match download quality and make the CLI offer upload interactively.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Plain 'romhop scan' on a TTY with unmatched games prompts 'Upload N unmatched game(s) to RomM now?' and runs the existing upload flow on yes
- [ ] #2 --upload-unmatched still forces upload non-interactively; --yes still skips prompts; non-TTY behavior unchanged (no hang)
- [ ] #3 GUI upload progress bar is determinate: fills proportionally to bytes sent across all files of a game (permille scale like download)
- [ ] #4 GUI upload progress format shows game name + batch position + sent/total + rate, matching the download bar style
- [ ] #5 upload_game emits cumulative bytes across a game's files plus a total; UploadWorker.item_progress carries (sent, total, speed)
- [ ] #6 Tests cover the CLI offer prompt branch and the new upload progress total/cumulative emission
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
CLI: scan() now offers upload when result.unmatched and _stdin_isatty() and not --yes; --upload-unmatched stays non-interactive override; added _stdin_isatty() seam (CliRunner is non-TTY). upload.py: precompute total bytes across game's real files, accumulate game_sent across files, progress_fn signature now (fname, sent, total). workers.UploadWorker.item_progress widened to (sent, total, speed); on_progress accepts total. scan_result_dialog: determinate permille bar mirroring download (_PROGRESS_SCALE, name/pos label, sent/total/rate). Tests: 1 upload progress, 4 cli (accept/decline/non-tty/flag), 2 dialog progress. Full suite 561 pass. CHANGELOG Unreleased updated.
<!-- SECTION:NOTES:END -->
