---
id: TASK-1073
sequence_id: 1073
type: task
title: Check field values against their declared collections
status: Cancelled
parent: FEAT-900
author: tech-lead
refs:
- ADR-864:implements
description: 'The field_value_declared member: error level, work and records bundles,
  item and sub-entity fields'
subentities:
- local_id: ST1
  title: Add field_value_declared to the catalog and the work and records bundles
  status: Todo
  story: US1
- local_id: ST2
  title: Pin CLI writes as clean and the fix-a-stale-value way out at the gate
  status: Todo
  story: US1
- local_id: ST3
  title: Prove no new finding on a scratch copy of this repository's squad
  status: Todo
  story: US1
created_at: '2026-10-16T19:56:44Z'
updated_at: '2026-10-16T20:07:09Z'
---
<!-- sq:body -->
## Scope

Deliver FEAT-900 US1: a per-item validator, `field_value_declared`, that reports a stored badge
field value outside the collection its field declares, on items and sub-entities.

- `error` by default, in the `work` and `records` category bundles (ADR-864's ruled tier), so it
  runs on every type of those categories and on no `roster` type.
- Covers every declared field that names a collection: an item's fields
  (`spec.fields_for(type)`, core `priority` and `severity` and any custom badge code stored as a
  top-level attribute, ADR-1007 decision 4) and a sub-entity's fields
  (`spec.fields_for(kind)`, read through `SubEntity.badge_value`). The collection is resolved
  through `_badges.resolve_collection`, never by a field or collection name literal.
- An empty or absent field is not a finding. Status is out of scope (`item_status_valid`,
  `subentity_status_valid` own it).
- Reads only the item and the spec, so it runs at the create/update gate like the other
  frontmatter-only members. That gate is the way out the story asks for: a write that sets a
  valid value passes, an unrelated write on an item still carrying a stale value is refused.
- Message names the item (or `ID` plus sub-entity address), the field label and code, the value
  and the collection.

Binding: ADR-864 (tier and bundles), ADR-1007 decision 5 (the value is reported, never changed or
removed; badge membership is this check), FEAT-900's 2026-10-12 note (no project selection: the
member ships in the bundles; this repository's override is not edited).

Before writing it, confirm no existing member already reports a collection-membership failure on
a field; if one does, stop and raise it on this task rather than ship a duplicate.

## New state

None. No stored key, no spec key, no index field.

## Migration

None. The member reads existing values and writes nothing. No contribution to
`_migrations/_v0_15_to_v0_16.py` and no POSTCONDITIONS row.

## Order and dependencies

No depends-on: it can start now, in a worktree, because TASK-990 is in progress in the main tree.
Overlap, all additive:

- `_workflow/_models.py`: `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL`, `CATEGORY_BUNDLES`.
  TASK-990 ST8 and TASK-1069 ST2 edit `PINNED_ROSTER_ATTRIBUTES` and the bundles' neighbours in
  the same module.
- `_services/_validators.py`: the `CATALOG` table. TASK-990 ST5 and TASK-1069 ST2 each add a rule.
- The FEAT-902 task depends on this one: both edit the same catalog tables and guard tests, so
  they go to one developer in sequence.

## Files

`_workflow/_models.py`, `_services/_validators.py`, possibly `_badges.py` (a read helper only).
Tests under `tests/integration`, `tests/cli`, `tests/meta` (catalog and default-level guards).

## Acceptance

- Every acceptance bullet of FEAT-900 US1 is pinned by a named test; the handoff maps bullet to
  test.
- **Table-driven shape tests**, one backbone table. Rows (position): item `priority`; item
  `severity` on a type that declares it; item custom badge field declared by a project; sub-entity
  `severity` (a finding); sub-entity custom field. Columns (value shape): a member; outside the
  collection; a member removed by an override that narrows the collection after the item was
  written; wrong case (`High`); surrounding whitespace; a non-string (list, integer, mapping);
  empty string; absent. Third axis (type category): work, records, roster (never checked). Per
  cell: finding or none, level, exact message.
- **Gate rows:** `update` setting a valid value on an item carrying a stale one succeeds; an
  unrelated `update` on that item is refused until the value is fixed; what `comment`, `body` and
  `status` do there is pinned and listed in the handoff; a CLI write that the field parser
  accepts never produces a finding.
- **Invariant:** for every row where the CLI can write the value, write it through the CLI and
  assert `sq check` reports nothing from this member.
- A falsified test per subtask, recorded in the handoff.

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright/ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant; test selection derived from
the diff, the manager runs the full suite; one-or-two sentence comments with no versions or ticket
ids; no ticket ids in test file names; no edits to `CHANGELOG.md`, `docs/`, the hand-written
`CLAUDE.md` or `squads/.overrides/`; probing only in a scratch squad under the session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1073 add-subtask "<title>"`; track with `sq task 1073 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add field_value_declared to the catalog and the work and records bundles

<!-- sq:subtask:ST1:body -->
**Goal.** `field_value_declared` exists in the per-item catalog at `error`, is bundled for `work` and `records`, and reports any stored field value outside its declared collection on an item or a sub-entity.

**Approach**

- `_workflow/_models.py`: the name joins `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL` (`error`) and both `CATEGORY_BUNDLES` entries for `work` and `records`.
- `_services/_validators.py`: the member iterates `spec.fields_for(item.type)` and, for each sub-entity, `spec.fields_for(kind)`; reads the stored value by code; skips empty or absent; resolves the collection through `_badges.resolve_collection`; reports a value that is not a member. Level through `_resolved_level`. A non-string value is a finding, not a crash.
- No field, collection, type or kind name literal in the member.

**Tests**

- The backbone table of the task body (position by value shape by category).
- A project-declared custom field and collection in a scratch override fire the same way as `priority`.
- `tests/meta` catalog guards (names, default levels, bundles) pass.

**Falsify.** Skip sub-entities: the finding rows go red. Compare case-insensitively: the `High` row goes red. Restore each.

**Acceptance.** FEAT-900 US1: error level and exit 3, message content, runs on every work and records type for item and sub-entity fields, custom fields included, status not reported.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Pin CLI writes as clean and the fix-a-stale-value way out at the gate

<!-- sq:subtask:ST2:body -->
**Goal.** CLI writes never trip the member, and the way out works: setting a valid value on an item with a stale one succeeds while an unrelated update is refused until it is fixed.

**Approach**

- No new code expected: the member runs at the create/update gate because it reads only the item and the spec. If the gate does not run it there, find out why before changing anything and record it on this subtask.

**Tests**

- Invariant: for each field position of the task body where the CLI can write a value, every member of the collection written through the CLI leaves `sq check` without a finding from this member.
- Way out: an item carrying a value an override has since removed. `update --priority <valid>` (or the field's own option) succeeds; `update --title x` is refused with exit 1 naming the field and value; after the fix the same title update succeeds.
- Sub-entity: a finding with a stale `severity`; setting a valid one through the sub-entity update succeeds.
- Pin, and list in the handoff, what `comment`, `body` and `status` do on an item with a stale value.

**Falsify.** Exclude the member from the gate: the refused-update row goes red. Restore.

**Acceptance.** FEAT-900 US1: CLI writes unaffected; the way-out bullet.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove no new finding on a scratch copy of this repository's squad

<!-- sq:subtask:ST3:body -->
**Goal.** On a scratch copy of this repository's squad, adopting the member adds no finding, and the live board and this repository's override stay untouched.

**Method**

- Copy `squads/` and `.squads.toml` into a folder under the session scratchpad (outside the repository). If its schema differs from the build under test, migrate the copy with the dev build (`uv run --project <repo> sq -C <copy> migrate up`), never the repository.
- Run `sq check --json` on the copy with the dev build, and again with the member removed from the bundles in a local patch; diff the two issue lists. Record both counts and the diff on this subtask.
- Any finding the member produces on the copy is a real stale value: list it for @manager rather than fixing it here.

**Acceptance.** FEAT-900 US1 last bullet. `git status` shows no change under `squads/` from this subtask. The handoff gives the tech writer: the member name, level, bundles, what it checks and the way out.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:58:49Z] Olivia Lead:
  - Broken down into ST1-ST3. No migration, no new state. No depends-on: can start now in a worktree; overlap with TASK-990/TASK-1069 is additive catalog rows. TASK-1074 depends on this one (same tables), so one dev for both, in sequence. @manager
- [2026-10-16T20:06:37Z] Elias Python:
  - Stopped before shipping, as the task requires: a collection-membership check already exists at the index load boundary (_index/_store.py _validate_badge_codes / _check_field_codes, plus the workflow loader live-index cross-check). It covers items and sub-entities, custom fields included, via badge_value, on every ordinary load.
  - Consequence, measured: with field_value_declared implemented and bundled, a stale priority written into frontmatter and indexed by sq repair makes svc.check() itself raise "TASK-2 field priority has code huge, which the active workflow spec collection does not declare" before any validator runs. So the member can never report, and the stated way out (update --priority valid on a stale item) cannot run either, because the load fails first. Only repair (validate_vocab=False) survives.
  - Decision needed: (a) drop the member, the load check is the membership check; (b) keep the member and relax the load boundary so check/update/repair-style paths read stale values (changes the fail-closed contract and corpus_fit/workflow lint); (c) something else. Work is uncommitted in worktree agent-a4a6de4545a741fbd. @manager
- [2026-10-16T20:07:08Z] Catherine Manager:
  - Option (a): drop the member; the load check is the membership check. Cancelled with FEAT-900.
<!-- sq:discussion:end -->
