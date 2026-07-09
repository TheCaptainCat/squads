---
id: FEAT-326
sequence_id: 326
type: feature
title: Remove the ItemType + Status enums — generic item engine
status: InProgress
parent: EPIC-325
author: product-owner
refs:
- ADR-322:implements
description: Delete ItemType/Status enums; spec becomes sole type+status vocabulary;
  reserved floor = meta-types + agent-lifecycle only
subentities:
- local_id: US1
  title: Full self-service type vocabulary in spec
  status: Todo
- local_id: US2
  title: Statuses become ordinary spec vocabulary
  status: Todo
- local_id: US3
  title: Playbook + CLI register types generically
  status: Todo
- local_id: US4
  title: Unmodified default squad behaves identically
  status: Todo
created_at: '2026-07-07T14:37:36Z'
updated_at: '2026-07-08T08:25:48Z'
---
<!-- sq:body -->
## What this delivers

Implements ADR-322 (Accepted): deletes the `ItemType` and `Status` enums and
every duplicate hardcoded vocabulary map that shadows the loaded workflow
spec, so the spec's `[items.*]`/`[statuses.*]` tables become the **sole**
type and status vocabulary. This is the precondition for FEAT-281's rename
migrations — you can't safely rename a type or status while a hardcoded enum
still enumerates the built-ins.

## Scope

- Delete `ItemType` and `Status` (`_models/_enums.py`) and the duplicate
  reserved-vocab maps in `_models/_vocab.py` (`RESERVED_PREFIX`,
  `RESERVED_FOLDER`, `RESERVED_TYPE_BY_PREFIX`, `TYPE_ALIASES`,
  `is_reserved()`'s short-circuit). `prefix_for(t, spec)` reads the spec only;
  an unknown type is a load-time error, not a silent fallback.
- `Item.prefix` is written to frontmatter for **every** item, built-in or
  custom (today it's written only for custom types, with built-ins
  re-derived from the reserved map). `Item.id`/`from_frontmatter` format from
  the stored `prefix` so a file round-trips **without a spec in hand** (`sq
  repair` today relies on the hardcoded map for this — this feature replaces
  that mechanism, it must not regress the spec-free round-trip).
- `WorkflowSpec._validate`'s completeness floor narrows from "all ten
  `ItemType` members must be present" to **only the three `is_meta` types**
  (`role`/`skill`/`operator`); the status floor narrows from the current
  `_RESERVED_FLOOR` frozenset to **only the agent-lifecycle statuses**
  (`Draft`/`Active`/`Archived`). Every other built-in type/status becomes
  ordinary, omittable/renamable spec vocabulary.
- Sub-entity and finding statuses stop being hardcoded floor members. The
  done-toggle and sub-entity `create` stop referencing `Status.DONE`/
  `Status.TODO` literals: `create` sets whichever status the sub-entity
  kind's declared machine names as its start state; the done-toggle resolves
  the status the machine flags with the new **`completion`** flag (layered
  onto FEAT-211's `terminal` flag — terminal-but-not-done states, e.g.
  `WontFix`, must not satisfy the toggle). The bundled default workflow flags
  each machine's completion status so this is byte-identical to today's
  `Status.DONE` behavior with no spec override.
- The playbook (`_interactions.py`) and CLI per-type command registration
  (`_cli/__init__.py`, `_cli/_create.py`) both key off `spec.items` with a
  **deterministic iteration order** instead of the enum — every registered
  type, built-in or custom, goes through one code path (today's static-vs-
  dynamic split is removed). A type missing from the playbook still gets a
  thin auto-generated skill rather than failing.
- `_services/_maintenance.py`, `_roster.py`, `_base.py`: meta-type references
  (`ItemType.ROLE`/`SKILL`/`OPERATOR`) become named string constants resolved
  against `spec.items[...]`/`item_is_meta()`, not enum members.
- `_migrations/*` runners (`_v0_1_to_v0_2`, `_v0_2_to_v0_3`, `_v0_4_to_v0_5`,
  `_v0_5_to_v0_7`) get **inline frozen local constants** in place of the
  live enums — a migration is a point-in-time snapshot of the vocabulary at
  the schema version it targets and must never track live vocabulary that
  can change after the migration ships.
- Result dataclasses / model fields typed `ItemType`/`Status` become `str`
  (they're already stored as strings on disk).

## Non-goals

- Badge axes (priority/severity) — ADR-323's feature, sequenced after this
  one.
- Custom sub-entity kinds — FEAT-212, which depends on this landing first.
- Rename migrations — FEAT-281, which depends on this landing first.

## Acceptance criteria

1. `ItemType` and `Status` no longer exist anywhere in `src/squads/`; `grep
   -rn 'ItemType\|\bStatus\b' src/squads` returns no vocabulary-enum hits
   (aside from unrelated identically-named locals, if any — verify by hand).
2. `RESERVED_PREFIX`/`RESERVED_FOLDER`/`RESERVED_TYPE_BY_PREFIX`/
   `TYPE_ALIASES` are deleted; `prefix_for` resolves solely from
   `spec.items[type].prefix`.
3. Every `Item`, built-in or custom, carries its `prefix` in frontmatter; a
   `.md` file round-trips through `from_frontmatter`/`to_frontmatter_dict`
   with no spec loaded (spec-free round-trip preserved).
4. `WorkflowSpec` load-time validation requires only the three `is_meta`
   types and only the agent-lifecycle statuses (`Draft`/`Active`/`Archived`)
   — a spec that omits, renames, or re-prefixes `task`/`bug`/`feature`/…
   loads successfully.
5. Sub-entity/finding `create` sets the declared machine's start state; the
   done-toggle resolves via the new `completion` flag, not a `Status.DONE`
   literal; the bundled default spec's behavior is byte-identical to today
   for every built-in sub-entity/finding kind.
6. The playbook and CLI register every type in `spec.items` (built-in and
   custom) through one generic code path, in deterministic order; a type
   absent from the playbook still gets a working thin auto-generated
   `sq-<type>` skill.
7. Every `_migrations/*` runner uses inline frozen local constants for the
   vocabulary it targets, never the live spec or a removed enum.
8. A no-override squad (default bundled spec, no project overrides) behaves
   identically to pre-change squads: same IDs, same statuses, same CLI
   surface, same generated skills — verified by the existing golden test(s).
9. `uv run pyright && uv run ruff check . && uv run ruff format --check .`
   all clean.

## Provenance

Implements ADR-322 (Accepted). Precondition for FEAT-281 (rename migrations)
and for the ADR-323 badge-collections feature, which needs this feature's
generic string-keyed item/type model.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 326 add-story "As a <role>, I want … so that …"`; track with `sq feature 326 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Full self-service type vocabulary in spec |
| US2 | Todo |  | Statuses become ordinary spec vocabulary |
| US3 | Todo |  | Playbook + CLI register types generically |
| US4 | Todo |  | Unmodified default squad behaves identically |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Full self-service type vocabulary in spec

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want to omit or rename any built-in work type in my spec and have squads load it without complaint.

**Acceptance:** a spec that drops, renames, or re-prefixes any of the seven built-in work types (task/bug/feature/decision/review/guide/epic) loads successfully; the load-time completeness floor checks only for the three is_meta types (role/skill/operator). RESERVED_PREFIX/RESERVED_FOLDER/RESERVED_TYPE_BY_PREFIX/TYPE_ALIASES are deleted; prefix_for resolves solely from spec.items[type].prefix, erroring on an unknown type rather than silently falling back.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Statuses become ordinary spec vocabulary

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want every built-in status to be ordinary spec vocabulary so I can rename or drop one without hitting a hardcoded floor.

**Acceptance:** the Status enum is deleted; the load-time status floor narrows from the current broad frozenset to only the agent-lifecycle statuses (Draft/Active/Archived). Sub-entity/finding create sets the declared machine's start state and the done-toggle resolves via a new completion flag (layered on FEAT-211's terminal flag) instead of a Status.DONE/Status.TODO literal; the bundled default spec's behavior is byte-identical to today for every built-in sub-entity/finding kind.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Playbook + CLI register types generically

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a developer extending squads, I want the playbook and CLI to register every type from one generic code path so adding a type never means touching a static dispatch table.

**Acceptance:** _interactions.py and the CLI's per-type command registration (_cli/__init__.py, _cli/_create.py) key off spec.items with deterministic iteration order; today's static-vs-dynamic split is removed — built-in and custom types go through the same path. A type missing from the playbook still gets a working thin auto-generated sq-<type> skill.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Unmodified default squad behaves identically

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an existing squads user, I want my unmodified default squad to behave identically after this change.

**Acceptance:** a no-override squad (bundled default spec, no project overrides) produces the same IDs, statuses, CLI surface, and generated skills as before this feature — verified by the existing golden test(s); migrations get inline frozen local constants instead of the live spec/enum so historical runs stay reproducible; pyright/ruff/ruff-format all clean.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T14:58:59Z] Catherine Manager:
  - Recommended dispatch order (soft — a sequencing preference, not a hard block, so no depends-on refs between these tasks): TASK-329 → TASK-328 → TASK-330 → TASK-331.
  - Why: TASK-329 (generic playbook + CLI registration, str-keyed) can land BEFORE the enum deletions — it makes consumers spec-generic while ItemType/Status still exist, de-risking the ~245-site cut. Then TASK-328 deletes the type enum, TASK-330 deletes the status enum + adds the completion-flag machine binding, and TASK-331 (frozen migration constants + prefix-line normalization + SCHEMA_VERSION assessment) lands last since it depends on the final shape of both axes.
  - Pickup: this chain is the first build step of EPIC-325. Promote each task Draft→Ready at dispatch; one python-dev per task, scoped to edits + fast gates; keep the reviewer independent of the build lineage (worktree isolation); the main loop runs the full ~4-min suite as the authoritative gate between steps. FEAT-327 (badges) follows FEAT-326; FEAT-212 must be re-baselined onto ADR-323's shared Field schema before its own dispatch.
<!-- sq:discussion:end -->
