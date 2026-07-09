---
id: TASK-350
sequence_id: 350
type: task
title: Retire global StatusSpec.completion; per-kind completion + rehome tests
status: Done
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
created_at: '2026-07-09T21:31:27Z'
updated_at: '2026-07-09T22:37:46Z'
---
<!-- sq:body -->
The ADR-348-blessed StatusSpec.completion retirement (ADR-348 §2, resolves REV-337 F3). Isolated as its own step because it re-homes TASK-330's blessed code + its 5 regression tests onto the per-kind validator — the single decision that touches recently-blessed work.

## Scope

Add `completion: str` to `SubentityKindSpec` — names the done-toggle target status inside that kind's own machine.

Remove the global `StatusSpec.completion: bool` field (TASK-330's mechanism).

Rewrite `_check_completion_status`: iterate declared `self.subentity_kinds` (not kinds derived from ItemSpec.subentity_kind); assert each kind's `completion` names a **reachable, non-initial** state of that kind's `lifecycle`. This is FEAT-212 AC5's catch — a custom kind whose done-target falls outside its machine fails closed at load / `sq workflow lint`.

Rewrite `subentity_completion(kind)` to an O(1) `self.subentity_kinds[kind].completion` lookup (was a scan for the flagged status). Keep the same signature so _workflow/__init__.py re-export and callers are unchanged.

In default_workflow.toml move the two `completion = true` flags out of `[statuses.Done]`/`[statuses.Fixed]` and onto `[subentity_kinds.*].completion`: subtask=Done, story=Done, finding=Fixed (same targets TASK-330 encoded, relocated). Golden regenerates.

Re-home TASK-330's 5 regression tests in tests/test_workflow_spec.py (currently ~L518-560: no-completion-status, two-completion-status for subtask/story + finding, and the bundled resolves-one-per-kind assertion) onto the per-kind validator — e.g. a kind whose completion is unset / points at an undeclared or initial-only status now fails; the bundled resolves subtask/story=Done, finding=Fixed via the O(1) lookup.

## Files owned

- src/squads/_workflow/_models.py (StatusSpec.completion removal, _check_completion_status rewrite, subentity_completion rewrite)

- src/squads/_workflow/default_workflow.toml (relocate completion flags; golden regenerates)

- tests/test_workflow_spec.py (re-home the 5 TASK-330 tests)

## Acceptance

- No item-data migration (spec-schema-only change); bundled subentity_completion returns Done/Done/Fixed for subtask/story/finding.

- The 5 re-homed tests pass against the per-kind validator; a custom kind with an out-of-machine completion fails load (AC5).

- Golden regenerated; full suite green.

## Depends on

TASK-349 — needs subentity_kinds carrying the other keys first; shares _models.py + default_workflow.toml, so runs strictly after 349 (no parallel collision on the core files).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 350 add-subtask "<title>"`; track with `sq task 350 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T22:24:07Z] Elias Python:
  - Changed: src/squads/_workflow/_models.py (SubentityKindSpec gains required completion: str; StatusSpec.completion removed entirely; _check_completion_status rewritten to iterate self.subentity_kinds and require completion be a reachable, non-initial state of that kind's own lifecycle, via lifecycles.get(ks.lifecycle) — no longer scans items/statuses; subentity_completion(kind) is now the O(1) self.subentity_kinds[kind].completion lookup, same signature).
  - default_workflow.toml: moved completion=true off [statuses.Done]/[statuses.Fixed] onto subentity_kinds.{story,subtask}.completion="Done" and .finding.completion="Fixed".
  - Dedup: yes, collapsed story+subtask's identical lifecycle tables into one [lifecycles.subentity] (finding keeps its own, unchanged) — safe now that nothing resolves a sub-entity machine by kind-name-as-lifecycle-name (that was the last blocker I flagged in TASK-349). Also had to fix src/squads/_workflow/__init__.py's _make_subentity_workflows, which still did the old positional spec.lifecycles[kind] lookup for the SUBENTITY_WORKFLOWS shim — switched it to spec.subentity_workflow(kind) iterating spec.subentity_kinds, and deleted the now-dead _SUBENTITY_KINDS frozenset. Not in TASK-350's formally owned files but a 1-line, clearly-correct fix required for the dedup to stay byte-identical (SUBENTITY_WORKFLOWS would otherwise silently lose the 'story' key).
  - Re-homed the 5 TASK-330 tests in tests/test_workflow_spec.py onto the per-kind validator, porting intent rather than deleting: the two 'no completion status' tests -> completion-points-at-own-initial-status (subtask/story and finding, separately, since completion is now a required scalar not a flag-scan); the two 'two completion statuses' tests -> completion-names-a-status-outside-the-kind's-own-machine (subtask/story vs 'WontFix', finding vs 'Cancelled'); the bundled-resolves-one-per-kind test kept as-is (now via the O(1) lookup). Removed the now-dead _spec_with_status_override helper and the StatusSpec(completion=...) constructions.
  - Also updated 3 TASK-349 tests that assumed lifecycle==kind-name or lifecycle=='story'/'subtask' literally: test_golden_subentity_lifecycles + test_bundled_subentity_kinds_declare_machine_and_vocab + test_subentity_accessors_resolve_via_kind_spec_lifecycle now resolve the machine via spec.subentity_workflow(kind)/spec.subentity_kinds[kind].lifecycle instead of spec.lifecycles[kind] directly. Fixed 2 fixtures in tests/test_workflow_badges.py that construct a SubentityKindSpec without the new required completion field (the custom-kind override test, and the reject-unknown-key test).
  - Golden diff beyond completion relocation: [lifecycles.story]/[lifecycles.subtask] merged into [lifecycles.subentity] (byte-identical transitions); subentity_kinds.story/subtask.lifecycle changed from 'story'/'subtask' to 'subentity'. No SCHEMA_VERSION bump, no item-data migration — spec-schema only.
  - Gates: pyright clean, ruff check + format clean. Green: test_workflow_spec.py (39 tests), test_workflow_badges.py, test_workflow_override.py, test_squad_ref_hygiene.py, plus the same wider sweep as TASK-349 (capability_flags, reserved_types_invariants, renderer_261, prefix_resolver, custom_type_skill/create/cli/paths, authoring_prose, spine_characterization), test_migration_corpus.py, test_migrations.py, and — since this task's core change is the completion/done-toggle runtime path — also test_service.py, test_collab.py, test_workflow_rules.py, test_unwritten_subentity_body_check.py. Did not run the full suite.
  - Reviewer/full-suite should scrutinize: the [lifecycles.subentity] rename (grep for any stray reference to the old [lifecycles.story]/[lifecycles.subtask] names outside this repo's own tests — none found in src or docs); and that _make_subentity_workflows' switch to iterating spec.subentity_kinds (vs the old hardcoded 3-kind frozenset) doesn't change SUBENTITY_WORKFLOWS' key set for a project override that adds a 4th kind (it now would include it, which is more correct, but worth a second look since that shim's docstring says it's 'kept for the golden-lock tests').
- [2026-07-09T22:31:29Z] Paul Reviewer:
  - Reviewed uncommitted TASK-350 diff (independent, builds on the landed TASK-349). VERDICT: CHANGES-REQUESTED — the source change is correct and clean, but the acceptance 'full suite green' is NOT met: the lifecycle rename story/subtask→subentity was not swept through all test consumers.
  - F1 (BLOCKER) tests/test_linearize_lifecycle.py:241 — the parametrize list still names the removed lifecycle keys 'subtask' and 'story'; both cases now fail at line 248 (assert lifecycle_name in spec.lifecycles). Full suite = 2 failed (only these). Fix: replace 'subtask','story' with 'subentity' in the parametrize list. This is the sole breakage; every other file is green. (Handoff claimed suite green — it wasn't; only the touched files were run.)
  - Source logic CORRECT: StatusSpec.completion removed cleanly (no lingering consumers in src — grep confirms); completion: str added to SubentityKindSpec; subentity_completion is now O(1) subentity_kinds[kind].completion (_models.py:820); _check_completion_status rewritten to iterate declared kinds and reject completion==initial or completion not in machine.states (_models.py:358). AC5 reachability holds — machine.states is guaranteed reachable-only by the separate _check_reachability (_models.py:307), so 'in states' + non-initial correctly implies reachable+non-initial.
- [2026-07-09T22:31:44Z] Paul Reviewer:
  - Flagged call (a) — [lifecycles.subentity] collapse + subentity_kinds.*.lifecycle rename: YES, byte-identical. The subentity machine's initial/transitions are identical to both former subtask AND story tables (which were themselves duplicate); completion relocated Done/Done/Fixed matches the old statuses.Done/Fixed completion=true targets exactly. Golden subentity snapshot (test_workflow_spec.py:116) unchanged and still passes via subentity_workflow(kind).
  - Flagged call (b) — _make_subentity_workflows deriving keys from spec.subentity_kinds vs the deleted _SUBENTITY_KINDS triple (_workflow/__init__.py:56): YES, correct. For the bundled spec subentity_kinds={story,subtask,finding}, so SUBENTITY_WORKFLOWS's keyset is identical; test_golden_subentity_lifecycles asserts set(_SUBENTITY_SNAPSHOT)==set(SUBENTITY_WORKFLOWS) (line 327) and passes. Dropping the old 'if kind in spec.lifecycles' guard is safe — subentity_workflow resolves via subentity_kinds[kind].lifecycle and _check_subentity_kinds guarantees that lifecycle exists. Genuinely better (reflects custom kinds too).
  - The 5 re-homed tests assert the right thing: two initial-status-as-completion rejections (subtask=Todo, finding=Open), two out-of-own-machine rejections (subtask←WontFix, finding←Cancelled — nicely cross-checks the machine split), and the bundled resolves subtask/story=Done, finding=Fixed. Behavior-named, intent-preserved not just deleted. No ticket IDs leaked into source (provenance headers match the file's existing ADR-322 §N style).
  - Optional nit (not blocking, pre-existing, not in this diff): tests/_helpers.py:115 comment still says statuses are 'bound by machine role (start state / completion flag)' — the per-status completion flag is gone (now per-kind), so that phrase is mildly stale. Worth a one-word touch-up whenever _helpers is next edited.
- [2026-07-09T22:34:57Z] Elias Python:
  - Fixed the 2 full-suite misses from the story/subtask->subentity lifecycle rename: tests/test_linearize_lifecycle.py:241 parametrize list ['work','adr','review','bug','guide','agent','subtask','story','finding'] -> ['work','adr','review','bug','guide','agent','subentity','finding'] (dropped the now-removed duplicate entry); tests/_helpers.py:115 comment reworded from '(start state / completion flag)' to '(start state / per-kind completion target)' to match the per-kind completion field.
  - Grep sweep result: searched src/ + tests/ + docs/ for lingering 'story'/'subtask' AS LIFECYCLE keys (lifecycles.story/subtask, lifecycles['story'/'subtask'], lifecycles.get(...)). Found 2 more occurrences beyond the two you flagged, both false positives I verified by running: tests/test_workflow_capability_flags.py (a from-scratch raw-TOML fixture in test_loader_unknown_toml_key_in_item_raises_squads_error with [lifecycles.subtask]/[lifecycles.story] sections) and tests/test_workflow_lint.py (_build_spec's synthetic lifecycles dict with 'subtask'/'story' keys). Both are fully self-contained synthetic specs that never set subentity_kind on any item and never pass a subentity_kinds table, so nothing resolves those lifecycle names via SubentityKindSpec.lifecycle -- they're just two of several arbitrarily-named dangling lifecycles present only to satisfy the generic reachable/terminal checks. Ran both files individually to confirm: all pass, unaffected by the rename. No other references found; the bundled-default rename is otherwise fully swept.
  - Files touched this round: tests/test_linearize_lifecycle.py, tests/_helpers.py.
  - Gates: pyright clean, ruff check + format clean. tests/test_linearize_lifecycle.py and tests/test_squad_ref_hygiene.py both green, plus re-ran test_workflow_spec.py/test_workflow_badges.py/test_workflow_lint.py/test_workflow_capability_flags.py as a sanity check on the two synthetic-fixture files -- all green. Did not run the full suite. Left TASK-350 InProgress.
- [2026-07-09T22:37:45Z] Catherine Manager:
  - Blocker F1 (linearize parametrize list still naming the removed story/subtask lifecycles) fixed; stale _helpers.py completion-flag comment corrected; grep confirmed no other live references (two remaining are self-contained synthetic-fixture lifecycles). Full parallel suite green. Paul's review concerns (both flagged calls confirmed byte-identical) resolved. Landing.
<!-- sq:discussion:end -->
