---
id: TASK-929
sequence_id: 929
type: task
title: Serialise the index by sequence_id so sq repair diffs stay stable
status: Draft
author: tech-lead
refs:
- REV-926:addresses
created_at: '2026-09-04T14:41:50Z'
updated_at: '2026-09-04T14:41:53Z'
---
<!-- sq:body -->
## Scope

REV-926 F10, deferred out of FEAT-906: `sq repair` rebuilds `.squads.json` by globbing the corpus
(`_rebuild_index_from_disk`), so the rebuilt `items` map lands in directory-walk order rather than
the incremental insertion order it replaces. On this repo's own mandatory backfill the result was a
37,994-line diff for a semantically identical index (889 items before and after, identical key set,
exactly three real field changes — parsed and compared field by field). Neither order is sorted, so
a reviewer cannot see from the diff that nothing moved without parsing both revisions, and two
people repairing the same squad on different filesystems produce conflicting orders.

This is pre-existing `sq repair` behaviour, not something FEAT-906 introduced — but FEAT-906's own
upgrade-path fix (TASK-927/928's sibling work) is what makes every adopter run the convergence sweep
at least once, so it is the first time this lands as a large diff on a file a team actually shares.
Deferred rather than bundled into either fix task because the fix is orthogonal to the view-tag
mechanism entirely: it is a general property of how `Service.repair()`/`_rebuild_index_from_disk`
serialises `SquadsDB.items`, unrelated to role/skill/system-skill tags, and deserves its own review
scope rather than riding in on an unrelated feature's fix.

## Fix

Serialise `items` in `sequence_id` order on every write that rebuilds or persists the index (at
minimum `_rebuild_index_from_disk`; audit `IndexStore`'s other write paths for the same exposure),
so the on-disk key order is deterministic and independent of filesystem walk order. Confirm this
does not change `SquadsDB`'s runtime dict semantics (Python dicts already preserve insertion order;
this only changes what order gets inserted in), and that `get`/`add`/`allocate_id` and the
model_validator normalizing legacy full-id keys are unaffected.

## Acceptance

1. **Driven, not asserted.** Run `sq repair` on a real multi-hundred-item corpus (this repo's own
   squad, or an equivalent fixture) twice from two different starting orders (e.g. once after a
   fresh `sq repair`, once after deleting and re-adding a file so the filesystem walk order
   changes) and confirm the resulting `.squads.json` is byte-identical both times when no item
   actually changed.
2. Falsify: revert the ordering fix, confirm the two runs above diverge in key order again;
   restore, confirm they agree.
3. Test-selection floor: this touches the index/`_maintenance.py` write path — run `tests/meta`
   and `tests/integration` regardless of the diff-based grep selection.
4. Narration sweep on any new/changed prose, validated scanner, never committed.
5. `uv run sq check` clean.

## Dependency

None. Purely technical, deliberately left unlinked to any feature (its own convention: "leave
purely-technical work items unlinked to a feature"). Not required for FEAT-906 to close — refs
REV-926 as the review that surfaced it, kind `addresses`, since F10 already has a treated
disposition (a named home) rather than being left Open with no plan.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 929 add-subtask "<title>"`; track with `sq task 929 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
