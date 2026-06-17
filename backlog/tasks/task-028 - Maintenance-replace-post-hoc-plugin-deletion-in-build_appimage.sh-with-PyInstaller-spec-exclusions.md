---
id: TASK-028
title: >-
  Maintenance: replace post-hoc plugin deletion in build_appimage.sh with
  PyInstaller spec exclusions
status: To Do
assignee: []
created_date: '2026-06-17 13:05'
updated_date: '2026-06-17 13:09'
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
- [ ] #1 libqtiff and AT-SPI2 Qt plugins excluded via PyInstaller spec or hook, not deleted post-build
- [ ] #2 build_appimage.sh deletion block removed
- [ ] #3 AppImage still launches on Ubuntu and Arch without libtiff/AT-SPI2 errors
- [ ] #4 CI build passes on both OS targets
<!-- AC:END -->
