---
id: TASK-343
sequence_id: 343
type: task
title: Bug severity data migration extra->top-level; SCHEMA_VERSION 0.8
status: Draft
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-341:depends-on
description: 'First 0.8 change: _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION
  0.7->0.8; frozen vocab; one-way'
subentities:
- local_id: ST1
  title: _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump
  status: Todo
  story: US3
created_at: '2026-07-09T08:20:11Z'
updated_at: '2026-07-09T08:21:08Z'
---
<!-- sq:body -->
## Scope

Ship the one-way data migration that moves item-level bug severity from
`extra[X.SEVERITY]` to the top-level `severity:` frontmatter key for every
existing bug, and **own the `SCHEMA_VERSION` 0.7 -> 0.8 bump** that goes with
it. Delivers US3.

## CRITICAL — this is the FIRST 0.8 schema change on the release line

FEAT-326 did **not** bump `SCHEMA_VERSION`: the prefix-line normalization that
was going to carry a 0.7 -> 0.8 bump was reverted, because the prefix is now
**derived from the persisted id** and needs no migration (see the FEAT-326
close). `SCHEMA_VERSION` therefore still reads `"0.7"` (verified in
`_models/_schema.py`). Unlike the prefix case, this change **moves persisted
data** (severity out of `extra` into a top-level key), so it genuinely needs a
shipped, ordered migration.

**This task OWNS, as the first 0.8 change:**
- the `SCHEMA_VERSION` `"0.7"` -> `"0.8"` bump in `_models/_schema.py`;
- a new ordered runner `_migrations/_v0_7_to_v0_8.py` with
  `migrate(paths) -> int` + a `MANUAL` runbook string;
- its `Migration` record wired into `_migrations/_registry.py::MIGRATIONS`
  (`to_schema = "0.8"`), running through `sq migrate up` then `repair` + stamp.

## Areas / files

- `_migrations/_v0_7_to_v0_8.py` — for each bug `.md` file, move the severity
  value from the legacy `extra[X.SEVERITY]` (the body/`extra` `:meta` location
  `_meta_compat.py` handles) to a top-level `severity:` frontmatter key, and
  drop the `extra` entry. **One-way.** Only bug item files carry item-level
  severity; finding severity (already `severity:` in the sub-entity block) and
  priority (already top-level) are untouched — do not walk them.
  - **Freeze the vocabulary point-in-time.** The runner inlines the severity
    codes it needs as **frozen local constants** — it must NEVER read the live
    spec or any collection (which a project can rename/re-badge after this
    migration ships). A migration transforms files as they were at the version
    it targets; its vocabulary is pinned, not re-derived. This mirrors
    ADR-322's migration-freeze discipline.
  - The runner only relocates the stored **code** string; it does not validate
    it against a collection (that is the load-boundary's job) and does not
    touch label/emoji.
- `_migrations/_registry.py` — add the `Migration` record (`version`,
  `to_schema = "0.8"`, `run = _wrap_sync(_v0_7_to_v0_8.migrate)`,
  `manual = _v0_7_to_v0_8.MANUAL`) after the `_v0_5_to_v0_7` entry.
- `_models/_schema.py` — `SCHEMA_VERSION = "0.8"`.
- `MANUAL` runbook string — describe the extra -> top-level severity move for
  operators (what changes on disk, that it's automatic, and the one-line
  what-if-you-hand-edited note), consistent with the existing runners' manual
  entries. Also add the changelog index entry per the `sq migrate` runbook.

## Done criteria

- `SCHEMA_VERSION` is `"0.8"`; the root CLI callback's current-schema gate
  passes only after `sq migrate up` on a 0.7 squad.
- `sq migrate up` on a squad with pre-migration bugs (severity in
  `extra[X.SEVERITY]`) moves every bug's severity to the top-level `severity:`
  key, leaving priority and finding severity untouched; `sq check` and
  `sq repair` are clean after.
- The runner uses inline frozen local constants for its severity vocabulary,
  never the live spec.
- A migration test reproduces the move on a fixture 0.7 squad and asserts the
  resulting frontmatter (top-level `severity:`, no `extra` severity, values
  preserved exactly).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

Depends-on the enum-deletion/generic-storage task: the model there already
reads/writes top-level `severity:` and tolerantly backfills the legacy `extra`
location at load, so this migration normalizes disk to match a model that
already understands both. Lands **last** on the feature (it stamps the 0.8
schema). Independent of the CLI task — can land before or after it. Coordinate
the changelog/manifest bookkeeping with the release owner (Pierre owns the tag;
agents only prep).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 343 add-subtask "<title>"`; track with `sq task 343 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Bug severity migration preserves data
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add _v0_7_to_v0_8.py (bug extra[X.SEVERITY] -> top-level severity:, one-way, frozen vocab), wire the Migration record into MIGRATIONS (to_schema 0.8) with MANUAL runbook + changelog index, and bump SCHEMA_VERSION 0.7->0.8. First 0.8 change on the line.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
