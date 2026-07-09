---
id: TASK-351
sequence_id: 351
type: task
title: 'Service layer: spec-derived kind maps + public kind-taking surface'
status: Done
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
created_at: '2026-07-09T21:31:27Z'
updated_at: '2026-07-09T22:55:23Z'
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
- [2026-07-09T22:49:06Z] Elias Python:
  - Implemented: _base.py replaces the bundled-pinned SUBENTITY_PARENT/SUBENTITY_KIND/SUBENTITY_CONTAINER module dicts with subentity_parent_map/subentity_kind_map/subentity_container_map(spec) free functions + ServiceCore instance properties (subentity_parent/subentity_kind/subentity_container) resolved from self.spec — a project-declared type/kind is now visible with no code change.
  - _subentities.py: promoted add_block/list_blocks/get_block/update_block/set_block_body/set_block_status to public methods (dropped leading underscore); the per-kind wrappers (add_story/get_finding/etc., ~112 test call sites) are now thin delegators, unchanged signatures. _check_type went from @staticmethod to instance method (needs self.spec). Added _check_maps_parent_story, called from add_block/update_block instead of the old 'kind == "subtask"' literal, gating story-mapping by the maps_parent_story capability flag.
  - Call-site fix required outside the owned files: _retype.py's _ensure_subentity_container was a bundled-spec-pinned free function; now takes spec explicitly and retype() passes self.spec, so retyping into a custom type with a custom kind also resolves correctly.
  - Updated the two spine-characterization tests that imported the old module dicts directly (mechanical: now call subentity_kind_map/subentity_parent_map(bundled_spec()) — same assertions, same bundled behaviour).
  - Added tests/test_subentity_kind_spec_driven.py: a service constructed with a spec declaring a custom item type + custom subentity kind resolves subentity_parent/subentity_kind/subentity_container for it, while a plain-bundled-spec service never sees it.
  - Fast gates green: pyright 0 errors, ruff check clean, ruff format clean. Targeted tests green: test_service.py test_collab.py test_spine_characterization.py test_subentity_kind_spec_driven.py test_unwritten_subentity_body_check.py test_retype*.py test_workflow_capability_flags.py test_workflow_spec.py test_squad_ref_hygiene.py. Did not run the full suite (per instructions).
  - For reviewer/full-suite: (1) discussion.py's _SUMMARY_COLS is still a static per-kind dict, so add_block on a genuinely custom kind will KeyError at the summary-render step — that's TASK-352's job, not fixed here, and I didn't add an end-to-end add_block test for a custom kind for that reason. (2) _retype.py's _CONTAINER_HEADINGS is still story/subtask/finding-only, same latent gap for retype-into-a-custom-kind — pre-existing, out of scope. (3) I added a story-mapping capability check to add_block (previously silently ignored story for non-subtask kinds); confirm no existing caller relied on that silence.
  - Left TASK-351 InProgress for review.
- [2026-07-09T22:54:23Z] Paul Reviewer:
  - Reviewed uncommitted TASK-351 diff (independent, on committed TASK-350). VERDICT: APPROVE. Active-spec correctness verified, delegators intact, gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures). One LOW untracked-debt note below.
  - Active-spec CORRECT: SUBENTITY_PARENT/KIND/CONTAINER module dicts (pinned to bundled_spec()) replaced by subentity_parent_map/kind_map/container_map(spec) free fns + ServiceCore properties resolving from self.spec (_base.py:52-75,257-273). Every consumer switched to self.subentity_* (_subentities.py) and _retype.py:156 passes self.spec explicitly — no path still pins bundled where it should be active. container derives from ks.plural = stories/subtasks/findings, byte-identical to the old markers.STORIES/SUBTASKS/FINDINGS. New test proves per-service isolation (a custom 'ticket' kind on 'gadget' resolves; a plain-spec service never sees it).
  - Delegators intact: all per-kind wrappers (add_story/get_finding/list_*/set_*/update_*) preserved with unchanged signatures, now thin delegators over the public add_block/list_blocks/get_block/update_block/set_block_body/set_block_status. Only update_subtask/add_subtask forward story= (verified _subentities.py:227-285), so the new gating never fires on the story/finding wrappers.
- [2026-07-09T22:54:38Z] Paul Reviewer:
  - Flag (a) _SUMMARY_COLS still static (_discussion.py:255): YES, legitimately TASK-352 — that task's scope explicitly names _SUMMARY_COLS/_summary_cells for field-driven derivation. This task's acceptance is map+container resolution only; new test correctly does NOT claim end-to-end custom-kind add. Fine to defer.
  - Flag (b) _CONTAINER_HEADINGS still static (_retype.py:26): acceptable to defer for THIS task (pre-existing; retype-to-a-custom-kind-hosting-type isn't a wired path yet), BUT — F1 (LOW): it is NOT tracked in TASK-352/353/354 (grep-confirmed). _ensure_subentity_container now spec-derives kind+container_tag but line 210 still does _CONTAINER_HEADINGS[kind] → KeyError for a custom kind on retype. Ask tech-lead to fold its retirement into TASK-352 (or file a follow-up) so it doesn't fall through the cracks; heading can derive from ks.plural like the container does.
  - Flag (c) add_block/update_block now RAISE via _check_maps_parent_story when story is passed to a non-mapping kind (was: silent-ignore in add_block; unconditional _validate in update_block): YES, correct and safe. Fail-loud beats silently dropping a caller's story arg. Safe for all current callers — only the subtask path forwards story, and subtask has maps_parent_story=true; add_story/add_finding/update_story/update_finding never pass it. maps_parent_story flag correctly replaces the kind=='subtask' literal.
  - _check_type static→instance (_subentities.py:486): sound — needed because the parent map is now per-service spec-derived; all 3 call sites use self._check_type, no unbound SubentitiesMixin._check_type callers in src/tests. No ticket IDs in added source (grep clean). Scope-disciplined: didn't touch _discussion rendering (TASK-352) or CLI dispatch (TASK-353). test_spine_characterization updates are intent-preserving (constant imports → map fns on bundled_spec()).
- [2026-07-09T22:55:23Z] Catherine Manager:
  - Reviewer-approved, full suite green. F1 (LOW: _retype._CONTAINER_HEADINGS still a static kind→heading dict, would KeyError on retype into a custom kind — an unwired path) accepted and routed to TASK-352, which owns the parallel rendering derivation from ks.plural. Landing.
<!-- sq:discussion:end -->
