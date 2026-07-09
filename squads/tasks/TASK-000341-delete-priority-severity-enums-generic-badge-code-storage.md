---
id: TASK-341
sequence_id: 341
type: task
title: Delete Priority/Severity enums; generic badge-code storage
status: Draft
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-340:depends-on
description: Switch runtime off the enums onto fields_for(); store badge code only;
  bug severity -> top-level; render fallback
subentities:
- local_id: ST1
  title: Delete enums/*_EMOJI/DEFAULT_SEVERITY/severity_field; fields_for severity
    lookup
  status: Todo
  story: US1
- local_id: ST2
  title: 'Generic storage: badge code only, bug severity -> top-level, render fallback'
  status: Todo
  story: US1
created_at: '2026-07-09T08:20:10Z'
updated_at: '2026-07-09T09:42:27Z'
---
<!-- sq:body -->
## Scope

Switch the runtime off the hardcoded `Priority`/`Severity` enums and onto the
bundled spec fields landed in the previous task: delete the enums, their emoji
maps, `DEFAULT_SEVERITY`, and `ItemSpec.severity_field`/`item_has_severity()`,
and make item/sub-entity storage generic — store only the badge **code** per
declared field, move item-level bug severity off `extra[X.SEVERITY]` onto a
top-level `severity:` frontmatter key, and resolve label/emoji from the spec at
render time with a graceful fallback (raw code, never a crash). Completes US1.

This is the enum-deletion bisect point: like ADR-322's TASK-328, the delete is
only grep/pyright-clean once **every** reference is repointed onto the generic
`fields_for()` lookup. The on-disk data move for existing bug files is NOT done
here — reads tolerate the legacy `extra[X.SEVERITY]` location and backfill at
load; the shipped one-way migration that normalizes disk + bumps the schema is
the last task.

## Areas / files

- `_models/_enums.py` — delete `Priority`, `Severity`, `PRIORITY_EMOJI`,
  `SEVERITY_EMOJI`, `DEFAULT_SEVERITY`. (With ADR-322 already having removed
  `ItemType`/`Status`, this leaves `_enums.py` essentially empty of
  vocabulary — assess whether it should be removed outright or kept for any
  residual non-vocabulary enum.)
- `_models/_item.py` — `Item.priority: str | None` (was `Priority | None`);
  add a top-level `Item.severity: str | None`. `from_frontmatter` reads
  `severity:` top-level **and** falls back to legacy `extra[X.SEVERITY]` when
  the top-level key is absent (tolerant read, mirroring TASK-328's `prefix`
  backfill); `to_frontmatter_dict` always writes `severity:` top-level and no
  longer writes it into `extra`. Store only the badge **code** per field.
- `_models/_subentity.py` — `SubEntity.severity: str | None` (was
  `Severity | None`); unchanged storage location (already `severity:` in the
  sub-entity block), just the type flips to `str`.
- `_models/_metadata.py` — drop the item-level `"severity"` extra special-case
  (`Kind` literal `"severity"`, the `"bug": (Field(X.SEVERITY, "severity"),)`
  entry, and the `Severity` coercion). `X.SEVERITY` in `_extras.py` stays only
  if the migration/`_meta_compat` still needs the key name; otherwise remove.
- `_workflow/_models.py` — delete `ItemSpec.severity_field` and
  `item_has_severity()`. "Does type `t` carry severity" becomes "does
  `fields_for(t)` include a field with `code == "severity"`" — a generic
  lookup. Add the badge-code validation that runs at the `IndexStore.load()`
  boundary (codes on items/sub-entities checked against the bound collection,
  the same spec-aware seam type/status use — `_models` stays spec-decoupled).
- Render fallback — item/sub-entity badge rendering resolves label/emoji from
  the bound collection; a missing collection/badge renders the **raw code**
  (the same graceful neutral fallback status badges already use via
  `_discussion._DEFAULT_BADGE`), never raising. `--json`/code reads need no
  spec (the code is the stored authoritative value).
- Store load boundary (`_index/_store.py`) — backfill top-level `severity`
  from legacy `extra[X.SEVERITY]` for bug items at load, tolerant of either
  location, so a pre-migration file reads correctly.
- Sweep every remaining `Priority`/`Severity` annotation to `str` (result
  dataclasses, service signatures, `_discussion.py` `_severity_badge`
  internals — though the CLI-facing render generalization is the next task).

## Done criteria

- `grep -rn 'Priority\|Severity\|PRIORITY_EMOJI\|SEVERITY_EMOJI\|
  DEFAULT_SEVERITY\|severity_field\|item_has_severity' src/squads` returns no
  enum/map/flag hits (verify any residual identically-named locals by hand).
- Items/sub-entities store only the badge code per field; item-level bug
  severity serializes as a top-level `severity:` key; label/emoji resolve from
  the spec at render, falling back to the raw code with no crash when a
  collection/badge is missing.
- A pre-migration bug file (severity still in `extra[X.SEVERITY]`) reads
  correctly via the load backfill; a no-override squad shows the same badges,
  filters, and sort order as before.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

Depends-on the schema/bundled-defaults task — this repoints runtime onto the
`fields_for()`/collections the foundation task adds; deleting the enums is only
green once that vocabulary exists to replace them. The on-disk severity move +
`SCHEMA_VERSION` bump is deliberately NOT here (tolerant read + load-backfill
keep this task green against un-migrated files); it lands in the migration
task. Historical migration runners and `_meta_compat.py` must keep their
point-in-time severity/priority handling as **inline frozen local constants** —
if this task touches them, freeze, never track the live collections.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 341 add-subtask "<title>"`; track with `sq task 341 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Delete enums/*_EMOJI/DEFAULT_SEVERITY/severity_field; fields_for severity lookup | US1 |
| ST2 | Todo |  | Generic storage: badge code only, bug severity -> top-level, render fallback | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Delete enums/*_EMOJI/DEFAULT_SEVERITY/severity_field; fields_for severity lookup

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Priority/severity become spec badge collections
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Delete Priority/Severity/*_EMOJI/DEFAULT_SEVERITY from _enums.py and severity_field/item_has_severity from _workflow; flip all annotations to str; 'carries severity' becomes fields_for(t) has code 'severity'.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Generic storage: badge code only, bug severity -> top-level, render fallback

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Priority/severity become spec badge collections
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Store only the badge code per field; add top-level Item.severity written to frontmatter; from_frontmatter tolerantly reads legacy extra[X.SEVERITY]; load-boundary backfill + badge-code validation; render resolves label/emoji from the spec with raw-code fallback.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T09:42:27Z] Catherine Manager:
  - Carry-over from TASK-340 review (REV/APPROVE, LOW): when this task makes fields live, do NOT subtract 'prefix' from _reserved_item_keys() in _workflow/_models.py — keep it reserved (fail-closed). 'prefix' is a tolerated-and-ignored legacy frontmatter key (id always wins), so a live field coded 'prefix' would be silently discarded on round-trip — the exact shadow the reserved-key check prevents. 'path' can stay excluded (never a frontmatter key).
<!-- sq:discussion:end -->
