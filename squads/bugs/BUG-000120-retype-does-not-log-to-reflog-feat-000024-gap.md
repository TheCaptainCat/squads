---
id: BUG-000120
sequence_id: 120
type: bug
title: retype does not log to reflog (FEAT-000024 gap)
status: Done
author: qa
refs:
- FEAT-000024
- TASK-000112
created_at: '2026-06-15T10:16:30Z'
updated_at: '2026-06-15T10:21:41Z'
---
<!-- sq:body -->
The sq task N retype <type> command (implemented in src/squads/_services/_retype.py) does not call store._log() and therefore appends zero lines to .reflog.jsonl.

This violates FEAT-000024 acceptance ('remove, retype, forced-status, and repair each emit a reconstructable line') and TASK-000112 ST2 ('removals/retypes/forced-status/repair are reconstructable from reflog lines alone').

Reproduction: in any squad, note the line count of .reflog.jsonl; run sq task N retype bug; recount — the count is unchanged.

Fix: in _retype.py RetypeMixin.retype(), inside the store.transaction() block, add self.store._log('retype', old_id, {'new_id': new_id, 'old_type': old_type.value, 'new_type': new_type.value, 'status_carried': not status_reset, 'status': item.status.value}). Also add a test in test_reflog_core.py covering this case.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T10:21:41Z] Elias Python:
  - Fixed: added `self.store._log('retype', new_id, {...})` inside the existing `with self.store.transaction()` block in `_retype.py::RetypeMixin.retype()`, immediately before the `return RetypeResult` line.
  - Delta shape: `{old_id, new_id, old_type, new_type, status_carried, status}` — mirrors the remove op's gone-item snapshot convention; target is the new_id so reflog readers see the surviving ID.
  - Also added `retype` to the op table in `docs/workflow.md`, and a new test `test_retype_emits_reflog_line` in `tests/test_reflog_core.py` that asserts exactly one well-formed retype line with all expected delta fields.
  - Applied REV-000119 low findings F1 (stale docstrings in _items.py + _results.py), F2 (misleading actor-reset comment in _cli/__init__.py), and F4 (moved autouse _reset_actor fixture to conftest.py).
  - Gate: 700 passed, 1 skipped; pyright 0 errors; ruff clean. @qa please re-verify.
<!-- sq:discussion:end -->
