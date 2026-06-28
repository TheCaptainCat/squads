---
id: TASK-000234
sequence_id: 234
type: task
title: Reify the ~22 is-ItemType/is-Status identity checks onto capability flags (byte-identical)
status: Done
parent: FEAT-000208
author: tech-lead
subentities:
- local_id: ST1
  title: Reify the ~22 is-ItemType/is-Status checks onto flags across engine + backends
  status: Todo
  story: US2
- local_id: ST2
  title: Replace WORK_TYPES/_SUBENTITY maps/parent_hint with spec-derived flag queries
  status: Todo
  story: US2
created_at: '2026-06-26T09:48:48Z'
updated_at: '2026-06-26T15:17:15Z'
---
<!-- sq:body -->
## Goal

Reify the ~22 hardcoded `is ItemType.X` / `is Status.X` identity checks to consult the capability
flags introduced in TASK-000233 — behavior BYTE-IDENTICAL. After this task no behavioral type/status
identity `is` check remains hardcoded in the engine; the engine asks `spec.type_spec(t).<flag>`
instead of comparing to an enum member. The characterization tests from TASK-000233 are the proof of
equivalence.

Sequence: **second** — depends on TASK-000233 (flags exist + values encoded + characterization tests
pinning today's behavior). The fields are still enum-typed at this point (de-typing is TASK-000235);
this task only changes HOW the engine branches, not the field types.

## What to build — reify each check per the ADR §2 inventory

Touch these files (EXCLUDE `_migrations/_vN_*.py` — frozen historical code, left as-is per ADR §6):
- `_services/_base.py`, `_items.py`, `_maintenance.py`, `_subentities.py`, `_service.py`
- `_cli/_common.py`
- `_workflow/__init__.py`
- both backends (`_backends/_claude_code/`, `_backends/_agents_md/`)

Mapping (ADR §2 table):
- meta-type branches (slug-keyed lookup, skill-prefix file rule, roster filtering, author-is-self) →
  **`is_meta`** (+ `subentity_kind is None`); the slug-keyed lookup keys on `spec.meta_types()`.
- `in WORK_TYPES` (which types get a `sq <type>` app + are retype-eligible) → **`not is_meta`** →
  `spec.work_types()` (replaces the `WORK_TYPES` tuple).
- parent→sub-entity-kind (`is not ItemType.FEATURE`, the `_SUBENTITY` maps in `_items.py`/`_common.py`)
  → **`subentity_kind`** (feature→story, task→subtask, review→finding).
- task spine (`is not ItemType.TASK` / `is not ItemType.FEATURE` in `_maintenance.py`) →
  **`parent_required`** + **`ref_rules`**.
- `parent_hint`'s `if child is ItemType.TASK` (`_workflow/__init__.py`) → **`ref_rules`** drive the
  hint string (the hint text becomes spec-derived).
- ADR supersede warning (`is not ItemType.DECISION` + `status is Status.SUPERSEDED`) → **`ref_rules`**
  (a `supersedes` rule) keyed off the **`StatusSpec.role == "superseded"`** marker.
- bug severity row (`is ItemType.BUG` in `_common.py`) → **`severity_field`**.
- retype `_carry_or_reset_status` stays structural (compares whole machines via
  `workflow_for(...).states`) — no change.

## Design constraints (ADR-000232)

- §2: no behavioral type/status-identity `is` check left hardcoded in the engine; each becomes a typed
  spec-method/flag query. Migrations excluded (§6). Field types unchanged in this task (str widening is
  TASK-000235).
- Behavior byte-identical — the characterization tests from TASK-000233 must stay green WITHOUT being
  edited; that is the equivalence proof.

## THE STANDING GATE (every task in F2)

The entire existing test suite + all THREE golden-locks (workflow ADR-214, role-catalog ADR-221,
playbook ADR-226 incl. its byte-identical skill-output layer) MUST pass UNCHANGED — byte-identical
behavior. No existing test may be edited to accommodate F2; if one needs editing, that is a behavioral
change to be justified, not absorbed. Watch specifically for hazards ADR §7/Consequences flags: a
missed identity check not in the grep (implicit reliance on enum ordering/membership).

## Acceptance

1. Zero behavioral `is ItemType.X` / `is Status.X` matches remain in `src/squads` outside
   `_migrations/_vN_*.py`; each semantic is a `TypeSpec`/`StatusSpec` flag query.
2. `WORK_TYPES` tuple replaced by `spec.work_types()`; `_SUBENTITY` maps replaced by `subentity_kind`;
   `parent_hint` text spec-derived from `ref_rules`.
3. The TASK-000233 characterization tests pass UNCHANGED (equivalence proof).
4. Standing gate holds: full suite + all three goldens green, unchanged. `uv run pyright` strict zero
   errors; ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 234 add-subtask "<title>"`; track with `sq task 234 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Reify the ~22 is-ItemType/is-Status checks onto flags across engine + backends | US2 |
| ST2 | Todo |  | Replace WORK_TYPES/_SUBENTITY maps/parent_hint with spec-derived flag queries | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reify the ~22 is-ItemType/is-Status checks onto flags across engine + backends

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Replace WORK_TYPES/_SUBENTITY maps/parent_hint with spec-derived flag queries

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
