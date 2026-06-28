---
id: TASK-000228
sequence_id: 228
type: task
title: Playbook loader with cross-spec slug validation; rewire _interactions onto
  loaded spec
status: Done
parent: FEAT-000220
author: tech-lead
subentities:
- local_id: ST1
  title: load_playbook via importlib.resources/tomllib; rewire _interactions onto
    spec
  status: Done
  story: US1
- local_id: ST2
  title: Cross-spec slug validation against RoleCatalogSpec (*dev exempt), non-meta-only
  status: Done
  story: US2
created_at: '2026-06-26T08:04:10Z'
updated_at: '2026-06-26T09:27:31Z'
---
<!-- sq:body -->
## Goal

Implement `load_playbook(catalog)` (reads bundled `playbook.toml`, validates fail-closed against the
already-loaded role catalog, caches a singleton) and rewire `_interactions.py` consumers onto the
loaded spec — behavior BYTE-IDENTICAL, zero call-site churn. This task also establishes the
**cross-spec slug-validation contract** that a future custom-type playbook entry (US2 motivation /
FEAT-000210) must satisfy.

Sequence: **second** — depends on TASK-000227 (models + TOML) and on FEAT-000219's `RoleCatalogSpec`
being the slug authority. TASK-000229 (golden-lock) gates on this being behavior-preserving.

## What to build

- **Loader** `load_playbook(catalog: RoleCatalogSpec) -> PlaybookSpec`: read via
  `importlib.resources.files("squads._interactions") / "playbook.toml"` + stdlib `tomllib`, parse into
  the models, validate against the **already-loaded role catalog** (passed in so the cross-spec check
  has its authority), cache a module-level singleton (same lifecycle as the other specs). Invalid
  bundled playbook raises `SquadsError` — fail closed.
- **Fail-closed validation** (ADR §3, raises `SquadsError`):
  1. **valid item-type keys** — every key in `types` is a real `ItemType`;
  2. **cross-spec referential integrity (CRITICAL):** every `RoleGuideSpec.slug` in any entry must
     exist in the `RoleCatalogSpec` (FEAT-219 slug authority) — EXCEPT the `*dev` (`DEV`) sentinel,
     which is allowed and resolved at render time. Unknown slug → spec error.
  3. **non-meta-only requirement:** entries required only for the 7 work types (epic, feature, task,
     bug, decision, review, guide); the meta types role/skill/operator are deliberately absent and
     validation MUST NOT require them. A playbook entry for a non-work type is rejected; a missing
     entry for a meta type is fine.
  4. **required text present:** each entry has non-empty `overview` and `lifecycle`.
- **Consumer rewiring** — preserve the `_interactions.py` public surface as thin shims over the loaded
  spec so call sites do not churn:
  - `PLAYBOOK` → `spec.types`; `managed_item_types()` → `list(spec.types)`;
  - `item_skill_name()` unchanged (pure string function);
  - `skills_for_role(slug)` reads the spec to compute which item-type skills a role interacts with
    (today's scan of `PLAYBOOK` role slugs now scans `spec.types`);
  - `SKILL_DESCRIPTIONS` derived from `spec.types` (as today from `PLAYBOOK`); the per-type
    description template unchanged;
  - the backend `_write_item_skills` reads `pb = spec.types[item_type]` instead of
    `interactions.PLAYBOOK[item_type]` — its rendering logic (DEV→"developers", active-role filtering
    against the roster, the `agents/item_skill.md.j2` render call) is UNCHANGED.
  - `CREATE_LANES` / `LANED_TYPES` stay in Python (out of scope for FP); their pinning test against
    the playbook continues to hold.
- Retire the `PLAYBOOK` dict (no remaining literal outside the TOML). Keep the import graph acyclic;
  no `from __future__ import annotations`.

## Design constraints (ADR-000226)

- §3 loader/validation/rewiring; data moves out, rendering logic stays. No backend/renderer change —
  `agents/item_skill.md.j2` and skill-writing logic untouched; only the source of playbook data moves.
- The cross-spec slug check (rule 2) is the contract a custom-type entry (FEAT-000210) will satisfy;
  FP ships only the bundled playbook + this validation, not project-supplied entries.

## Acceptance

1. `load_playbook(catalog)` loads + validates the bundled playbook; an unknown role slug (non-`*dev`)
   raises `SquadsError`; an entry for a meta/non-work type is rejected; a missing meta entry is fine.
   (FEAT-000220 AC#6; US2's validation contract.)
2. `_interactions.py`'s `PLAYBOOK` dict is retired; `managed_item_types()`, `skills_for_role()`,
   `SKILL_DESCRIPTIONS`, and `_write_item_skills` route through the loaded spec. (AC#3, US1.)
3. All existing tests pass unchanged; `sq sync` output unchanged (byte-identity proven in
   TASK-000229). (AC#4/#7.)
4. `uv run pyright && uv run ruff check . && uv run pytest` green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 228 add-subtask "<title>"`; track with `sq task 228 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | load_playbook via importlib.resources/tomllib; rewire _interactions onto spec | US1 |
| ST2 | Done |  | Cross-spec slug validation against RoleCatalogSpec (*dev exempt), non-meta-only | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — load_playbook via importlib.resources/tomllib; rewire _interactions onto spec

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content lives in data not code
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Cross-spec slug validation against RoleCatalogSpec (*dev exempt), non-meta-only

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Project admin can add playbook entries for custom types so generated skills have role guidance
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
- [2026-06-26T09:04:58Z] Elias Python:
  - Implementation in working tree: src/squads/_interactions/ package with _models.py (PlaybookSpec/ItemPlaybookSpec/RoleGuideSpec), _loader.py (load_playbook with cross-spec slug validation), and playbook.toml. The _interactions/__init__.py rewires all public shims (PLAYBOOK, managed_item_types, item_types_for_role, skills_for_role, SKILL_DESCRIPTIONS) onto the loaded singleton.
  - Layer-B golden-lock (TASK-000229) passed on first run — byte-identical output confirmed for all 7 work types with the fixed pinned roster. The rewiring is behavior-preserving.
  - @manager ready for review alongside TASK-000229.
<!-- sq:discussion:end -->
