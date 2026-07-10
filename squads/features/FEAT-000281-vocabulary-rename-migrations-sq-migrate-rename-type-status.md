---
id: FEAT-281
sequence_id: 281
type: feature
title: Vocabulary rename migrations (sq migrate rename-type/status)
status: Done
parent: EPIC-280
author: product-owner
refs:
- FEAT-210:depends-on
- FEAT-211:depends-on
- FEAT-326:depends-on
subentities:
- local_id: US1
  title: As a project admin, I want sq migrate rename-type to safely rename a built-in
    type across my whole squad
  status: Todo
- local_id: US2
  title: As a project admin, I want sq migrate rename-status to safely rename a status
    across all items of a type
  status: Todo
created_at: '2026-07-02T09:25:53Z'
updated_at: '2026-07-10T01:56:00Z'
---
<!-- sq:body -->
## What this delivers

Two on-demand, audited `sq migrate` data-rewrite commands so a project can evolve its own
vocabulary after adopting it, without manual file surgery or broken refs:

- `sq migrate rename-type <old-type> <new-type>` — bulk-moves every item of `<old-type>` to
  `<new-type>`: IDs, folder, refs, and prose `@mentions` rewritten atomically, one item at a
  time, using the ID/ref/prose-rewrite primitives `_services/_retype.py` already has (`rewrite_ids`,
  the frontmatter+file-move sequence, `_resync_edges`).
- `sq migrate rename-status <type> <old-status> <new-status>` — bulk-moves every item of
  `<type>` currently at `<old-status>` to `<new-status>`.

Both are precision, per-type/per-status **data** rewrites, not spec edits — the target
type/status must already exist as ordinary spec vocabulary (bundled or project-declared) before
the rewrite runs. Both are audited: a reflog entry per item (mirroring `retype`'s `self.store._log("retype", …)`)
and a system discussion comment, the same trail `_retype.py` already produces.

## Re-baseline (was drafted pre-EPIC-325; EPIC-325 is now Done, ADR-322/323 Accepted)

The original draft assumed the pre-325 world (closed `ItemType`/`Status` enums, a hardcoded
prefix/folder map, additive-only overrides read as "types can never be renamed at all"). Three
things changed underneath this feature:

1. **No constraint to relax.** Types/statuses are already ordinary spec vocabulary
   (`WorkflowSpec.items`/`.statuses`); a project can *add* a type via
   `.overrides/workflow.toml` today. The additive-only rule (`_workflow/_loader.py`) forbids
   *redefining* a built-in key, not adding a new one — this feature needs zero change to that
   rule. "Renaming task to ticket" is: (a) the project additively declares `ticket` in its
   override (ordinary, already-supported spec authoring — outside this feature's scope), then
   (b) this feature's `rename-type` bulk-moves every existing TASK item to the already-declared
   `ticket` type. The built-in `task` entry stays in the bundled spec (unremovable, per
   additive-only) but simply ends up with zero live items. Dropped "relax additive-only" from
   scope — it was solving a problem the post-325 model doesn't have.
2. **`rename-type` cannot ride `_retype.retype()` unmodified.** `retype()` is built for
   *reclassifying* one item between two genuinely different, already-coexisting types: it
   refuses outright when the item has sub-entities (`_validate_refusals`), and resets status
   when the two types' workflows differ (`_carry_or_reset_status`). A vocabulary **rename**
   means "same semantic type, new label/prefix" — every FEAT/TASK/REV with stories/subtasks/
   findings would be rejected by the sub-entity refusal, and any status drift between old/new
   lifecycles would silently reset every renamed item's status. `rename-type` needs its own
   bulk path that reuses `_retype.py`'s low-level primitives (id/ref/prose rewrite, file move,
   `_resync_edges`) but drops the single-item reclassification guardrails that don't apply to a
   rename (sub-entities carry over unchanged; status carries over unconditionally, since a
   rename target should declare a workflow-compatible machine, not an unrelated one). This is a
   real implementation-shape change from "reuse `_retype.py`" to "extract and reuse `_retype.py`'s
   primitives under new validation," flagged for the tech lead.
3. **`rename-status` is scoped per-type by construction (status names are global vocabulary).**
   A status name (e.g. `Done`) is shared across many lifecycles; renaming it in-place in the spec
   would ripple into every other type/sub-entity machine using that name — out of scope and not
   what "rename-status" should mean. The already-scoped shape (`<type> <old> <new>`, moving only
   that type's items) is correct as drafted: `<new-status>` must resolve in
   `spec.workflow_for(<type>).states` (the type's own machine), which is exactly today's
   `Workflow.states`/`can_transition` surface — no change needed there. Terminal/open
   classification (`spec.is_open`) and any `completion` badge are inherited automatically from
   whatever `<new-status>` already declares; the migration only moves the `status:` value, never
   the vocabulary.
4. **Not a schema bump.** The existing precedent for exactly this shape of command is
   `sq migrate repad` (`_cli/_migrate.py`, `_services/_maintenance.py::repad`) — a one-way,
   on-demand `sq migrate` sub-command that rewrites data and is audited, but is deliberately
   **not** wired into `_migrations/_registry.py`'s `SCHEMA_VERSION`-gated `up` chain (that chain
   is for changing the stored data *shape* uniformly across every squad on upgrade; rename-type/
   rename-status change one project's *chosen vocabulary values*, on demand, never automatically).
   Dropped "requires a schema bump" / "registered in `_migrations/_registry.py`" from the
   acceptance criteria; both commands follow the `repad` pattern instead (own `sq migrate`
   sub-command, reflog-audited, `sq check`/`sq repair` clean afterward).

## Scope

- `sq migrate rename-type <old-type> <new-type>`: `<new-type>` must already be declared in the
  active spec (bundled or project override) and be a work type (`spec.work_types()`), not a
  meta-type. Bulk-moves every item currently of `<old-type>` to `<new-type>`: rewrites IDs,
  folder, parent links, refs, and prose `@mentions` atomically per item, reusing `_retype.py`'s
  rewrite primitives under rename-specific validation (sub-entities and status carry over
  unconditionally — see re-baseline #2). Refuses if `<old-type>` still has live children whose
  parent-type constraint the new type can't satisfy (same check `_retype.py` already does per
  item).
- `sq migrate rename-status <type> <old-status> <new-status>`: `<new-status>` must resolve in
  `<type>`'s own lifecycle (`spec.workflow_for(type).states`); fails closed with no partial
  rewrite otherwise. Bulk-moves every item of `<type>` at `<old-status>` to `<new-status>`.
- Both refuse on a reserved meta-type (`role`/`skill`/`operator`) with a clear error.
- Both are on-demand `sq migrate` sub-commands (siblings of `repad`), each producing a reflog
  entry per item and a system discussion comment — audited, not silent — and leave `sq check`/
  `sq repair` clean afterward. Neither touches `SCHEMA_VERSION` or `_migrations/_registry.py`.

## Non-goals

- Renaming squads' own meta-types (`skill`, `role`, `operator`) — reserved-vocabulary semantics
  (ADR-266); out of scope.
- Removing or renaming a *bundled* type/status key in the spec itself (e.g. dropping `task` from
  the bundled default, or renaming a status name in place across every lifecycle that shares it)
  — additive-only override semantics are unchanged by this feature; only the project's own
  override-declared vocabulary and this feature's per-item data rewrite are in scope.
- Extending `rename-type`/`rename-status` to sub-entity kinds (story/subtask/finding) — those are
  FEAT-212/ADR-348 vocabulary, a separate axis.

## Dependencies

FEAT-210, FEAT-211, FEAT-326 (all Done) — the spec-as-sole-vocabulary engine this feature relies
on is complete. No outstanding dependency.

## Acceptance criteria

1. `sq migrate rename-type task ticket` (with `ticket` already declared via
   `.overrides/workflow.toml`) rewrites all TASK-… IDs to TICKET-…, moves the folder, updates refs
   and parent links atomically, and preserves every renamed item's sub-entities and status
   unconditionally; `sq check` and `sq repair` are clean after.
2. `sq migrate rename-status <type> <old> <new>` transitions all items of that type from old to
   new status; fails cleanly (no partial rewrite) if `<new>` is not a state of that type's
   lifecycle.
3. Both operations produce a reflog entry per item and a system discussion comment, consistent
   with `_retype.py`'s existing audit trail and the `repad` command's shape.
4. Renaming a reserved meta-type (`skill`/`role`/`operator`) is rejected with a clear error.
5. All existing tests remain green; no `SCHEMA_VERSION` change, no new entry in
   `_migrations/_registry.py`.

## Provenance

Split from the former FEAT-212 ("Custom sub-entity kinds + vocabulary rename migrations") per
ADR-274 (Accepted) — this feature is the rename-migrations half; the custom-sub-entity-kinds half
stayed on FEAT-212, re-parented to this feature's sibling epic EPIC-280. Re-baselined against
EPIC-325 (Done) and ADR-322/323 (Accepted) — see the re-baseline section above.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 281 add-story "As a <role>, I want … so that …"`; track with `sq feature 281 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad |
| US2 | Todo |  | As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want `sq migrate rename-type <old> <new>` to safely rename a type across my entire squad — rewriting all IDs, folders, refs, and prose mentions atomically — so that I can evolve my team's vocabulary without manual file surgery or broken refs.

**Acceptance:** `sq migrate rename-type task ticket` rewrites all TASK-… IDs to TICKET-…, moves the folder, updates all parent/ref links and frontmatter; `sq check` and `sq repair` are clean after; the operation is logged as an audited migration event.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq migrate rename-status <type> <old> <new>` to rewrite all items of a given type from an old status to a new one, so that I can evolve my status vocabulary without leaving items in a stale or invalid state.

**Acceptance:** the migration transitions all matching items atomically; it fails cleanly with no partial rewrite if the new status is not valid for the type; the operation is logged as an audited migration event.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T21:16:38Z] Pierre Chat:
  - Deferred indefinitely. Bulk rename of built-in vocabulary is a customization convenience for external adopters; squads is single-user and the retype machinery + additive overrides already cover the rare case. Kept on the backlog (not cancelled) — revisit only if squads becomes publicly adoptable, where 'evolve your vocabulary after the fact' would be part of the customization story. Not scheduled; off the active line.
- [2026-07-09T21:18:48Z] Pierre Chat:
  - Supersedes the deferral above: retracted. squads is a multi-user/adoptable product (single-user only during construction), so vocabulary rename migrations are first-class adopter scope, not hypothetical. Promoted to the active line alongside FEAT-212. Dependencies FEAT-210/211/326 all Done — unblocked.
- [2026-07-09T21:19:29Z] Pierre Chat:
  - Sequencing: hold re-baseline until Robert's FEAT-212 ADR lands — the two are design-coupled (shared spec-vocab/migration surface under EPIC-280), and the ADR may reshape the rename approach. Stays Ready; PO re-baseline + tech-lead breakdown follow with the ADR in hand.
- [2026-07-09T21:31:51Z] Nina Product:
  - Re-baselined against post-EPIC-325 world (ADR-322/323 Accepted, FEAT-326 Done).
  - Scope changed: dropped 'relax additive-only' (no such constraint applies — target type/status is added via ordinary additive override first, then this feature bulk-moves data onto it).
  - rename-type can't call _retype.retype() as-is: its sub-entity refusal + status-reset guardrails are wrong for a same-type rename (would reject every FEAT/TASK/REV with stories/subtasks/findings). Needs its own bulk path reusing _retype.py's rewrite primitives under rename-specific validation — flagged for tech-lead design.
  - rename-status stays per-type (status names are global vocabulary shared across lifecycles — renaming one in place would ripple into every other type); new-status validated against that type's own workflow_for(type).states.
  - Dropped the schema-bump / _migrations/_registry.py acceptance criteria — this is an on-demand data rewrite like sq migrate repad, not a SCHEMA_VERSION-gated auto migration. Reflog-audited instead.
  - Dependencies FEAT-210/211/326 all Done; unblocked, no outstanding dependency. Still Ready; recommend tech-lead breakdown treats rename-type as new design work (bulk-rename path), not a thin wrapper over retype().
- [2026-07-09T21:47:56Z] Pierre Chat:
  - Re-baseline shape signed off: no SCHEMA_VERSION bump (on-demand project-invoked rewrite, like sq migrate repad, outside the upgrade chain); rename-type uses new bulk-rewrite primitives that carry sub-entities/status over (NOT a retype() wrapper — retype's guardrails would reject anything with sub-entities); the target type must be declared via ordinary additive override first, then rename-type moves data onto it (never auto-declares). Proceed on this shape. Sequenced after FEAT-212.
- [2026-07-10T01:36:11Z] Mara Tester:
  - Acceptance sweep (TASK-359) found BUG-362: declaring a rename target type that mirrors an existing type's subentity_kind (as this feature's own worked example does) breaks add_subtask/add_finding/add_story on the OLD type's items while both coexist pre-rename. Doesn't block rename-type/rename-status themselves (worked around in the acceptance test by seeding before declaring the override) but blocks the feature's documented usage pattern.
- [2026-07-10T01:55:59Z] Catherine Manager:
  - FEAT-281 complete. All tasks landed and committed: TASK-355 (rename-safe retype primitive), 356 (rename-type bulk service, atomic), 357 (rename-status bulk service), 358 (sq migrate CLI wiring), 359 (independent acceptance sweep — all 5 ACs PASS). The sweep surfaced BUG-362 (sub-entity owner resolution when two types share a kind — the exact declare-then-rename pattern this feature documents); fixed and Verified. Re-baseline shape honoured: no SCHEMA_VERSION bump, on-demand rewrites like repad, rename-type carries sub-entities/status unconditionally via new bulk primitives, target type declared additively first. Reviewer-approved throughout; full suite green.
<!-- sq:discussion:end -->
