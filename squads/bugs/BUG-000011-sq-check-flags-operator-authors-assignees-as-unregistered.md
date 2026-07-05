---
id: BUG-11
sequence_id: 11
type: bug
title: sq check flags operator authors/assignees as unregistered
status: Verified
author: op-pierre
assignee: python-dev
priority: high
description: check() validates author/assignee against roles only, while the write
  gate accepts operators too
created_at: '2026-06-10T12:30:52Z'
updated_at: '2026-06-10T12:32:14Z'
extra:
  severity: medium
---
<!-- sq:body -->
The write-path gate (`ServiceCore._is_participant`) accepts a registered role **or operator** as author/assignee, but `MaintenanceMixin.check` builds its `registered` set from `ItemType.ROLE` items only (`_services/_maintenance.py`). Any operator-authored item — including the operator's own registration item — gets a bogus `warn: author 'op-...' is not a registered agent`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-10T12:32:14Z] Elias Python:
  - Fixed: `check()` now builds its registered set from roles **and** operators, matching the write gate. Regression test: `test_check_accepts_operator_author_and_assignee`.
<!-- sq:discussion:end -->
