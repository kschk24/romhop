---
id: TASK-013
title: GUI sync/download user feedback
status: To Do
assignee: []
created_date: '2026-06-16 15:04'
updated_date: '2026-06-22 17:33'
labels:
  - feature
  - activity-feedback
dependencies: []
priority: low
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Umbrella for surfacing sync/download/error activity to the GUI user. Spec: docs/superpowers/activity-feedback-spec.md. One unified Activity-event stream emitted by the Qt-free core, rendered three ways in the GUI. Foundation (.04) lands first; the three renderers (.01 Toast, .02 Desktop notification, .03 Activity log) each depend on it and are mutually independent. Execute with the superpowers:executing-plans skill (/executing-plans), working from the spec.
<!-- SECTION:DESCRIPTION:END -->
