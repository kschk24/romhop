---
id: TASK-025
title: 'Fix: GUI segfault in bundled libxkbcommon on first keypress (non-Ubuntu Linux)'
status: Done
assignee: []
created_date: '2026-06-17 13:04'
updated_date: '2026-06-17 13:11'
labels:
  - bug
  - packaging
  - linux
dependencies: []
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Packaged Linux build (onedir at ~/.local/lib/romhop/_internal/, and AppImage) ships its own libxkbcommon.so.0 + libxkbcommon-x11.so.0 (collected from /usr/lib by PyInstaller). The bundled copy cannot build a valid xkb_state against the host's XKB keymap data, so xkb_state_key_get_layout dereferences garbage and SIGSEGVs on the first keypress that reaches a window/dialog (e.g. QDialog.exec in the setup wizard). 100% reproducible under key-spam on Arch/X11; A/B proven: LD_PRELOAD of the system lib survives 120s. Fix: filter libxkbcommon* out of a.binaries in packaging/romhop.spec so the loader falls back to the system library (stable .so.0 ABI, standard Qt-on-Linux approach). No-op on Windows. Same packaging family as TASK-021. Report: ~/Pictures/bugs_romhop/romhop-segfault-report.md. User workaround: rm bundled lib or LD_PRELOAD system lib.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 packaging/romhop.spec excludes libxkbcommon.so.0 and libxkbcommon-x11.so.0 from a.binaries
- [ ] #2 Fix is cross-platform safe (filter is a no-op when libs are absent, e.g. Windows)
- [ ] #3 Rebuilt onedir/_internal contains no libxkbcommon* and GUI survives key-spam without segfault
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Filtered libxkbcommon* out of a.binaries in packaging/romhop.spec. Rebuilt onedir: no libxkbcommon* present; ldd of libqxcb.so (with _internal on LD_LIBRARY_PATH) resolves libxkbcommon.so.0 + libxkbcommon-x11.so.0 to /usr/lib system copies — the report's verified passing condition. --smoke-exit QApplication init OK on X11. 401 tests pass. AppImage inherits via copytree of the same onedir. libxcb-xkb.so.1 (X11 protocol binding, not keymap state) left bundled, not implicated.
<!-- SECTION:NOTES:END -->
