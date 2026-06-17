---
id: TASK-021
title: 'Fix: AppImage segfaults on non-Ubuntu distros (AT-SPI2 + libtiff.so.5)'
status: Done
assignee: []
created_date: '2026-06-17 11:19'
updated_date: '2026-06-17 11:21'
labels:
  - bug
  - packaging
  - linux
dependencies: []
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Fresh 0.1.0 AppImage segfaults on non-Ubuntu-24.04 distros. Two root causes via QT_DEBUG_PLUGINS=1: (1) Bundled libatk-bridge-2.0.so.0 initialises AT-SPI2 D-Bus bridge on xcb launch; ABI mismatch with system AT-SPI2 → segfault. Fix: NO_AT_BRIDGE=1 before Qt init in frozen_dispatch.py. (2) libqtiff.so links to libtiff.so.5 but newer distros ship libtiff.so.6; failed dlopen may corrupt dl state. Fix: delete libqtiff.so in build_appimage.sh (romhop uses JPEG/PNG/WebP only). Workaround: NO_AT_BRIDGE=1 romhop
<!-- SECTION:DESCRIPTION:END -->
