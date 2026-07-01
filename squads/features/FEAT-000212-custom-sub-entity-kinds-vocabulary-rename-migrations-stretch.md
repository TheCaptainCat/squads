---
id: FEAT-000212
sequence_id: 212
type: feature
title: Custom sub-entity kinds + vocabulary rename migrations (stretch / split candidate)
status: Ready
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000210:depends-on
- FEAT-000211:depends-on
subentities:
- local_id: US1
  title: As a project admin, I want to define custom sub-entity kinds for my custom
    types in TOML
  status: Todo
- local_id: US2
  title: As a project admin, I want sq migrate rename-type to safely rename a built-in
    type across my whole squad
  status: Todo
created_at: '2026-06-25T13:21:20Z'
updated_at: '2026-07-01T08:27:49Z'
---
<!-- sq:body -->
## Status: stretch goal / strong candidate to split into its own epic

**Before committing F6 to this epic, the team must draw an explicit scope line.** The architecture study and EPIC-000206 both flag this as the boundary decision for L3 v1. Custom sub-entity kinds and vocabulary rename migrations are each a second deep coupling surface — comparable in blast radius to F1+F2 together. The recommendation is to treat F6 as a named placeholder in this epic's roadmap and, after the spike result is known, record a deliberate decision (ADR or comment) on whether F6 stays here or becomes EPIC-000213.

This feature is created Draft so it can be sequenced and re-evaluated; **do not proceed to implementation until the F6 scope decision is recorded.**

## What custom sub-entity kinds would deliver

Today the three sub-entity kinds — story (feature), subtask (task), finding (review) — are hardcoded: their machines, summary columns, `add-<kind>` CLI verbs, and the `_SUBENTITY` parent→kind map in `_items.py` and `_common.py` are fixed Python. A custom type today can reuse an existing sub-entity kind or have none. F6 would let a custom type declare a brand-new sub-entity kind (e.g. `action` items on an `incident` type with their own `Open → InProgress → Resolved` machine and summary columns).

This is a second deep surface: the coupling spans `SUBENTITY_WORKFLOWS`, the `_SUBENTITY` map, `_discussion.py` summary-column definitions, the `add-<kind>` CLI verbs, and `_print_subentity_summary`. It is **not** a free extension of F4 — it is a comparable engineering investment.

## What vocabulary rename migrations would deliver

Today, renaming a built-in type or status (e.g. renaming `task` → `ticket` project-wide) is not supported. Additive-only overrides intentionally forbid silent mutation of built-in vocabulary. Safe renames would use the existing `retype` machinery (which already rewrites IDs, parent links, and prose mentions atomically) as a migration primitive, exposing a `sq migrate rename-type <old> <new>` or equivalent command. This is the audited migration path referenced in the compatibility contract.

## Scope (when this feature proceeds)

### Custom sub-entity kinds
- Extend `WorkflowSpec` to include `subentity_kinds: dict[str, SubentityKind]` — each kind declares its machine, summary columns, and the parent type(s) that carry it.
- Make `_items.py` / `_common.py` `_SUBENTITY` map spec-driven; `add-<kind>` CLI verbs built dynamically from the spec for each type that declares a custom sub-entity kind.
- `_discussion.py` summary rendering and `_print_subentity_summary` read column definitions from the spec.
- All sub-entity mutations (`update`, `body`, `comment`) route through the spec for kind resolution.

### Vocabulary rename migrations
- `sq migrate rename-type <old-type> <new-type>`: rewrites all IDs, parent links, folder layout, and prose `@mentions` of the old type atomically. Additive-override additive-only constraint is relaxed for the migration path only. Requires schema bump.
- `sq migrate rename-status <type> <old-status> <new-status>`: rewrites all items of the given type with the old status to the new status. Fail-closed if the new status is not in the spec for that type.
- Both are `sq migrate`-style data rewrite events (with runbook + `manual` string), not config edits.

## Dependencies

Requires F4 (FEAT-000210) for custom types and F5 (FEAT-000211) for custom statuses. Effectively the last feature in the epic.

## Non-goals (within F6)

- Rich per-role playbook sections for custom sub-entity kinds (stretch goal beyond F6 itself).
- Renaming squads' own internal types (`skill`, `role`, `operator`) — those are meta-types with special semantics; rename support for meta-types is not in scope.

## Acceptance criteria (indicative — to be tightened before implementation)

1. A custom type can declare a new sub-entity kind with its own machine; `sq <type> <n> add-<kind> "…"` works; the summary table renders with declared columns.
2. `sq migrate rename-type task ticket` rewrites all TASK-… IDs to TICKET-…, moves the folder, updates refs and parent links atomically; `sq check` and `sq repair` are clean after.
3. `sq migrate rename-status <type> <old> <new>` transitions all open items of that type from old to new status; fails cleanly if new status is not valid for the type.
4. The F1 golden test and all existing tests remain green.
5. The scope decision (in-epic or own-epic) is recorded as an ADR or decision comment before implementation begins.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 212 add-story "As a <role>, I want … so that …"`; track with `sq feature 212 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project admin, I want to define custom sub-entity kinds for my custom types in TOML |
| US2 | Todo |  | As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want to declare a custom sub-entity kind (e.g. `action` on an `incident` type) in `.overrides/workflow.toml` with its own machine and summary columns, so that my custom types can have structured nested work items beyond reusing the built-in story/subtask/finding kinds.

**Acceptance:** `sq incident <n> add-action "…"` works for a type that declares `subentity_kind = 'action'`; the summary table renders with declared columns; `add-action` CLI verb is built dynamically from the spec.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq migrate rename-type <old> <new>` to safely rename a type across my entire squad — rewriting all IDs, folders, refs, and prose mentions atomically — so that I can evolve my team's vocabulary without manual file surgery or broken refs.

**Acceptance:** `sq migrate rename-type task ticket` rewrites all TASK-… IDs to TICKET-…, moves the folder, updates all parent/ref links and frontmatter; `sq check` and `sq repair` are clean after; the operation is logged as an audited migration event.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T08:27:49Z] Catherine Manager:
  - Ownership note (from the FEAT-210/REV-265/ADR-266 work): FEAT-212 owns retiring _SUBENTITY_PLURAL (_cli/_items.py) — the last static per-type vocabulary artifact. ADR-000266 established the Item.prefix + reserved-vocab resolver pattern and retired the prefix/folder/alias/meta statics in the FEAT-210 corrective; _SUBENTITY_PLURAL was deliberately deferred here because it needs FEAT-212's subentity_kinds schema addition (sub-entity plural vocab). When scoped, add a subentity_plural accessor to the resolver and delete _SUBENTITY_PLURAL. op-pierre confirmed this boundary.
<!-- sq:discussion:end -->
