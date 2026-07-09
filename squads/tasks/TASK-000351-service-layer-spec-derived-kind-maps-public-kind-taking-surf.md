---
id: TASK-351
sequence_id: 351
type: task
title: 'Service layer: spec-derived kind maps + public kind-taking surface'
status: Draft
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
created_at: '2026-07-09T21:31:27Z'
updated_at: '2026-07-09T21:33:36Z'
---
<!-- sq:body -->
ADR-348 §5 service half: make the kind<->type maps active-spec-driven and expose the generic sub-entity methods as a public kind-taking surface the CLI can call directly.

## Scope

In _services/_base.py: `SUBENTITY_PARENT`/`SUBENTITY_KIND` are currently module-level dicts pinned to `bundled_spec()` — a project-declared kind is invisible to them. Make them resolve from the **active** spec (invert `ItemSpec.subentity_kind` on the live spec, invariant #4 forward-edges-only). Derive `SUBENTITY_CONTAINER` from `kind_spec.plural` rather than the static kind->marker dict.

In _services/_subentities.py: promote the generic `_add_block`/`_list_blocks`/`_get_block`/`_update_block`/`_set_block_body`/`_set_block_status` to a public kind-taking surface the CLI calls directly (replacing the CLI's `getattr(svc, f"...{kind}")` dispatch, wired up in TASK-353).

KEEP the per-kind named wrappers (add_story/add_subtask/add_finding, list_*, get_*, update_*, set_*_body) as thin delegators over the generic surface — they are a real service API with ~112 test call sites; deleting them is out of scope (see open question). ADR-348 only removes them from the *CLI dispatch path*, not from the service.

`subentity_completion` is already O(1) after TASK-350; no service change needed for it here. Story-mapping validation `_validate_subtask_story` stays wired to the built-in story kind, now gated by the `maps_parent_story` capability (ADR-348 §7).

## Files owned

- src/squads/_services/_base.py (SUBENTITY_PARENT/SUBENTITY_KIND active-spec-derived; SUBENTITY_CONTAINER from plural)

- src/squads/_services/_subentities.py (public kind-taking surface; wrappers become delegators; maps_parent_story gating)

## Acceptance

- A custom type declaring a custom kind resolves parent<->kind and the container marker with no code change.

- The public generic methods accept an arbitrary declared kind; per-kind wrappers still pass their existing tests.

- Full suite green.

## Depends on

TASK-349 (kind_spec fields: plural, maps_parent_story). Runs in parallel with TASK-352 (disjoint files).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 351 add-subtask "<title>"`; track with `sq task 351 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
