---
id: TASK-028
title: >-
  Maintenance: replace post-hoc plugin deletion in build_appimage.sh with
  PyInstaller spec exclusions
status: Done
assignee:
  - '@claude'
created_date: '2026-06-17 13:05'
updated_date: '2026-06-25 16:45'
labels:
  - packaging
  - linux
  - maintenance
  - ready-for-human
dependencies: []
priority: low
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
packaging/linux/build_appimage.sh (lines 17-27) deletes libqtiff.so and libqatspiplugin.so after the PyInstaller build to work around AT-SPI2 ABI and libtiff SONAME mismatches on non-Ubuntu distros. This is a bandaid: when libtiff bumps SONAME again (e.g. .so.5 -> .so.6) the deletion targets the wrong name, the old broken lib ships, and users get the same crash with no obvious cause. Fix: exclude these plugins in the PyInstaller spec/hook at build time so they are never bundled, removing the per-distro deletion logic. Related to TASK-021.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 libqtiff and AT-SPI2 Qt plugins excluded via PyInstaller spec or hook, not deleted post-build
- [x] #2 build_appimage.sh deletion block removed
- [ ] #3 AppImage still launches on Ubuntu and Arch without libtiff/AT-SPI2 errors
- [ ] #4 CI build passes on both OS targets
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add exclusion filter in romhop.spec for libqtiff.so, libqjasper.so, libqatspiplugin.so (after existing libxkbcommon filter)\n2. Remove post-hoc deletion block from build_appimage.sh\n3. Run tests (no CI available locally, verify spec syntax)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Excluded via _EXCLUDED_PLUGINS set filter in romhop.spec. Shell deletion block removed from build_appimage.sh. AC3/AC4 need CI validation on actual build.
<!-- SECTION:NOTES:END -->
