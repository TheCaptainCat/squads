---
id: TASK-349
sequence_id: 349
type: task
title: 'SubentityKindSpec: machine + vocab keys; toml declares all kinds'
status: Done
parent: FEAT-212
author: tech-lead
subentities:
- local_id: ST1
  title: Declare custom-kind machine/vocab in TOML; bundled kinds byte-identical
  status: Todo
  story: US1
created_at: '2026-07-09T21:31:26Z'
updated_at: '2026-07-13T09:27:33Z'
---
<!-- sq:body -->
Realizes ADR-348 §1/§2/§6 schema foundation. Everything else in FEAT-212 derives from this — land first.

## Scope

Extend `SubentityKindSpec` (currently only `fields`) with the stored keys ADR-348 §1 blesses: `lifecycle: str` (explicit machine ref, mirrors `ItemSpec.lifecycle`), `plural: str` (list verb + container marker name), `local_prefix: str`, `placeholder: str | None = None`, `maps_parent_story: bool = False`. (The per-kind `completion` field is TASK-350's, not this task.)

Fully declare `[subentity_kinds.story]`, `[subentity_kinds.subtask]`, `[subentity_kinds.finding]` in default_workflow.toml with the new keys (finding already carries `fields`). Bundled values must reproduce today's behaviour byte-identically: subtask plural=subtasks/local_prefix=ST, story plural=stories/local_prefix=US, finding plural=findings/local_prefix=F; maps_parent_story=true for subtask only; placeholders match _discussion.py's current _PLACEHOLDER strings.

Rewire the three accessors `subentity_workflow`/`subentity_initial`/`subentity_can_transition` to read `self.lifecycles[kind_spec.lifecycle]` instead of `self.lifecycles[kind]` — retiring the kind-name==lifecycle-name convention. Optionally dedup the duplicated story/subtask lifecycles onto one machine (behaviour-identical; see open question).

Add validation (ADR-348 §6, part 1): a kind's `lifecycle` names a declared lifecycle (mirror the ItemSpec.lifecycle check); `plural` and `local_prefix` are non-empty and unique across kinds (dup plural collides list verb/marker; dup local_prefix collides local ids). The completion validation rewrite is TASK-350.

## Files owned

- src/squads/_workflow/_models.py (SubentityKindSpec, subentity_workflow/initial/can_transition, new validators)

- src/squads/_workflow/default_workflow.toml (declare all three kinds; golden regenerates)

- tests/test_workflow_spec.py (new lifecycle-ref + plural/local_prefix-uniqueness tests)

## Acceptance

- Bundled spec loads; subentity_workflow/initial/can_transition for story/subtask/finding return identical machines to before.

- A kind referencing an undeclared lifecycle, or a duplicate plural/local_prefix, fails spec load with a clear message (also surfaced by sq workflow lint).

- default_workflow.toml golden regenerated; full suite green (built-in behaviour byte-identical, FEAT-212 AC4).

## Depends on

None — foundation. TASK-350 sequences immediately after (same two core files).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 349 add-subtask "<title>"`; track with `sq task 349 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Declare custom-kind machine/vocab in TOML; bundled kinds byte-identical | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare custom-kind machine/vocab in TOML; bundled kinds byte-identical

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Extended `SubentityKindSpec` with the stored machine/vocab keys (`lifecycle`, `plural`, `local_prefix`, `placeholder`, `maps_parent_story`) and fully declared story/subtask/finding in `default_workflow.toml`, rewiring the three accessors to resolve the machine via `kind_spec.lifecycle` instead of the kind-name convention. Bundled kinds reproduce prior behaviour byte-identically, and a kind referencing an undeclared lifecycle or a duplicate plural/local_prefix now fails spec load.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T21:58:31Z] Elias Python:
  - Changed: src/squads/_workflow/_models.py (SubentityKindSpec +lifecycle/plural/local_prefix/placeholder/maps_parent_story; subentity_workflow/initial/can_transition now resolve via self.lifecycles[self.subentity_kinds[kind].lifecycle] through a new _subentity_machine() helper; new _check_subentity_kinds validator: lifecycle-ref + non-empty/unique plural+local_prefix).
  - default_workflow.toml: fully declared [subentity_kinds.story/subtask/finding] (lifecycle/plural/local_prefix/placeholder matching _discussion.py's _LOCAL_ID_PREFIX/_PLACEHOLDER byte-for-byte; maps_parent_story=true on subtask only).
  - Dedup decision: did NOT collapse the story/subtask lifecycle machines. subentity_completion() and _check_completion_status still hardcode self.lifecycles[kind] (kind-name==lifecycle-name), which is explicitly TASK-350's territory — collapsing now would silently break that completion check (lifecycles.get('story')/('subtask') would miss) and subentity_completion would KeyError. Kept lifecycle='story'/'subtask'/'finding' (same value as the kind name) so the binding is explicit but the value is unchanged; real dedup is a natural TASK-350 byproduct once completion also moves onto the kind spec.
  - Also fixed 2 pre-existing tests broken by fully declaring story/subtask (SubentityKindSpec's new required fields, and the override-merge additive-only guard now correctly rejects 'subtask' as a built-in): tests/test_workflow_badges.py (renamed/reworked test_override_can_add_a_new_subentity_kind_field -> ..._kind, using a genuinely new custom kind; fixed 2 bare SubentityKindSpec(...) constructions missing required fields).
  - Added thin tests to tests/test_workflow_spec.py: bundled kinds' new keys match _discussion.py vocab; accessors resolve via kind_spec.lifecycle; 3 fail-closed tests (undeclared lifecycle, duplicate plural, duplicate local_prefix).
  - Gates: pyright clean, ruff check + format clean. Targeted: test_workflow_spec.py (39 passed), test_workflow_badges.py, test_workflow_override.py, test_squad_ref_hygiene.py, plus a wider sweep of every test file that constructs subentity_kinds/SubentityKindSpec (capability_flags, reserved_types_invariants, renderer_261, prefix_resolver, custom_type_skill/create/cli/paths, authoring_prose) — all green. Did not run the full suite (per instructions).
  - Open question for reviewer/TASK-350: an ItemSpec.subentity_kind value not present in subentity_kinds now KeyErrors inside subentity_workflow/initial/can_transition instead of a clean SquadsError (previously harmless since fields_for() degrades gracefully but the machine was looked up by kind name directly). I did not add a fail-closed check for this since the task scope listed exactly 2 validations (lifecycle-ref, plural/local_prefix uniqueness) — flagging in case it should be closed here or in TASK-350/351.
  - No SCHEMA_VERSION bump — this is workflow-spec schema, not item frontmatter.
- [2026-07-09T22:04:55Z] Paul Reviewer:
  - Reviewed uncommitted TASK-349 diff (independent). VERDICT: APPROVE. Byte-identical bundled behaviour verified, accessor rewiring + validator correct, gates green (pyright/ruff/format clean; test_workflow_spec, test_workflow_badges, golden_json, custom_type_cli, reserved_types, load_boundary + full subent/workflow/discussion sweep all pass).
  - Byte-identical CONFIRMED: toml placeholders match _discussion.py:33-38 char-for-char; plurals stories/subtasks/findings match _models/_markers.py:20-22; local_prefix US/ST/F match _discussion.py:27; maps_parent_story=true only on subtask (matches _meta_compat story-on-subtasks-only). Golden lifecycle snapshot (test_workflow_spec.py:45) unchanged — machines untouched, change is purely additive vocab keys.
  - Validator _check_subentity_kinds (_models.py:392) fails closed as required: undeclared lifecycle ref, empty/dup plural, empty/dup local_prefix — each tested (test_workflow_spec.py:735-739) and passing; extra=forbid on the model catches typo'd keys at parse.
- [2026-07-09T22:05:08Z] Paul Reviewer:
  - Flagged call (a) — NOT deduping story/subtask lifecycles: ACCEPTABLE/correct. Confirmed subentity_completion (_models.py:828) and _check_completion_status (_models.py:379) still read lifecycles[kind] via the kind-name==lifecycle convention; collapsing the machines now would break both. Legit deferral to TASK-350.
  - Flagged call (b) — raw KeyError for an item.subentity_kind naming an absent kind: ACCEPTABLE to defer, one caveat. Verified empirically: an item with subentity_kind='ghost' loads with NO validation error and only raw-KeyErrors at runtime in subentity_workflow. This is pre-existing (same observable behaviour before the change relocated the KeyError from lifecycles[kind] to subentity_kinds[kind]).
  - F1 (LOW, only actionable item): the comment at _models.py:381 ('missing lifecycle is caught by _check_item_refs') is factually wrong — nothing validates item.subentity_kind membership against subentity_kinds/lifecycles (_check_item_refs only checks item.lifecycle/parents/prefix). Either add the one-line check (assert every ItemSpec.subentity_kind is a declared subentity_kind, raise SquadsError — fits this task's ADR-348 §6 validation mandate) or fix the comment so it doesn't ship claiming coverage that doesn't exist. Fine to route to TASK-350, but don't leave the false comment.
  - Scope/hygiene clean: no completion-validation touched (TASK-350's); the test_workflow_badges edits are necessary+correct (story/subtask are now protected built-in subentity_kinds, so the old 'extend subtask via override' test rightly became 'add a new action kind'); no improper ticket IDs in source (the one provenance header matches the file's existing style at test_workflow_spec.py:40). Tests thin but real and behavior-named.
- [2026-07-09T22:09:24Z] Elias Python:
  - Closed Paul's REV finding: added the missing fail-closed check. src/squads/_workflow/_models.py: _check_subentity_kinds now takes items too and raises 'item type references undeclared subentity kind ...' for any ItemSpec.subentity_kind not present in self.subentity_kinds; call site updated. Replaced the false '# missing lifecycle is caught by _check_item_refs' comment in _check_completion_status with an accurate one (it's a positional kind-name==lifecycle-name lookup, not subentity_kinds[kind].lifecycle; a custom kind with a differently-named lifecycle silently skips that scan — separate, still-open gap for the per-kind completion rewrite; the undeclared-kind case itself is now caught by _check_subentity_kinds).
  - Fixture sweep before adding the check: grepped every test file + corpus fixture for subentity_kind usage (test_custom_type_*, test_workflow_*, test_reserved_types_invariants, test_spine_characterization, tests/fixtures/corpus/*/.squads.toml) — nothing sets ItemSpec.subentity_kind to a value absent from subentity_kinds; the only real declaration site is default_workflow.toml, which TASK-349 already fully declares (story/subtask/finding). No ripple, so added the check directly rather than deferring.
  - New test: test_item_referencing_undeclared_subentity_kind_fails_closed in tests/test_workflow_spec.py.
  - Gates re-run: pyright clean, ruff check + format clean. Green: test_workflow_spec.py, test_workflow_badges.py, test_workflow_override.py, test_squad_ref_hygiene.py, plus the same wider sweep as before (capability_flags, reserved_types_invariants, renderer_261, prefix_resolver, custom_type_skill/create/cli/paths, authoring_prose, spine_characterization) and test_migration_corpus.py/test_migrations.py. Did not run the full suite.
- [2026-07-09T22:14:10Z] Catherine Manager:
  - Review finding F1 (false validation-coverage comment) closed by adding the fail-closed check: an ItemSpec.subentity_kind referencing an undeclared kind now raises SquadsError at load (ADR-348 §6), not a runtime KeyError. Full parallel suite green (verified twice — post-impl and post-F1-fix). Reviewer-approved. Landing.
<!-- sq:discussion:end -->
