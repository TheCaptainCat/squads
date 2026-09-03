---
id: TASK-842
sequence_id: 842
type: task
title: Refuse incoherent view and ref-rule declarations at spec load
status: Done
parent: FEAT-693
author: tech-lead
priority: urgent
refs:
- REV-840:addresses
- BUG-837:fixes
- BUG-838:fixes
- FEAT-321:addresses
description: ItemSpec.views is unvalidated on four axes, each bricking a type's read
  path while lint stays clean; plus two adjacent declaration-floor gaps in the same
  functions
subentities:
- local_id: ST1
  title: Validate ItemSpec.views on its three spec-resolvable axes
  status: Done
  story: US1
- local_id: ST2
  title: Missing presentation template raises a SquadsError
  status: Done
  story: US2
- local_id: ST3
  title: Repair the spec fixtures and the six [selected] enumerations
  status: Done
  story: US1
- local_id: ST4
  title: Refuse a paramless ref_rule_target_present at load
  status: Done
- local_id: ST5
  title: A [selected] drop strips the declarations targeting that type
  status: Done
- local_id: ST6
  title: Scaffolded view example says it needs its own template
  status: Done
  story: US1
- local_id: ST7
  title: Let a ref source project a badge some declared type carries
  status: Done
  story: US1
created_at: '2026-08-26T17:03:38Z'
updated_at: '2026-08-26T17:48:10Z'
---
<!-- sq:body -->
## Problem

The workflow spec refuses an incoherent declaration in every place but one. `ItemSpec.views` — the
reverse binding that attaches a declared view to a type's `show` surface — is not validated at all,
on any of four independent axes. Each unvalidated axis turns `show`, `show --json` and `show --raw`
into a hard exit-1 failure for **every item of that type**, while `sq workflow lint` and `sq check`
both report the spec clean. Two adjacent declarations in the same layer have the mirror problem: one
loads clean and does nothing, one refuses a declaration the resolver handles fine.

## Why `views` is the one-off, and why that is good news

`items.<type>.views` is the only attached-by-name list on `ItemSpec` that `WorkflowSpec._validate`
does not check reciprocally. Every sibling is checked both ways, and each is a pattern to match:

- `parents` and `lifecycle` — `_check_item_refs`
- `validators` — `_check_validators_assignment`
- `ref_rules` targets — `_check_ref_rule_targets`
- field `collection` — `_check_field_collections`
- sub-entity-kind `lifecycle` — `_check_subentity_kinds`

So this is an omission in new code, not a systemic hole, and there are five existing checks to
pattern-match against. `_check_views` already validates the `[views]` *mapping* (source vocabulary,
field codes, `group_by`/`order_by`); nothing validates the attachment side.

## The declined check, and why the trade does not hold

TASK-831 chose not to add spec-build-time validation for `ItemSpec.views`, because
`WorkflowSpec._validate` fires on ~30 hand-built partial specs across the suite that spread
`bundled.items` without carrying `bundled.views` (reported as 73 failures, 14 errors), relying on
refusal at first use instead. `ItemSpec.views`' own docstring records that reasoning. Three things
undo it:

- Refusal at first use is not what happens on the missing-template axis — that tracebacks.
- The blast radius is a whole type, not a view: attached views render unconditionally on every
  `show` of the attaching type (`_print_attached_views`, `src/squads/_cli/_common.py:657-682`,
  deliberately not gated on `--full`).
- Thirty partial specs that spread `bundled.items` but not `bundled.views` are thirty specs that are
  internally inconsistent by construction — `items.milestone` carries `views = ["milestone_rollup"]`
  in every one of them. Two fixture edits already in the tree do the right thing
  (`tests/unit/test_identity.py:129`, `tests/unit/test_workflow_spec_artifact.py:86`): they add
  `"views": dict(bundled.views)`. The remedy for the rest is the same one line.

If the fixture cost proves genuinely unacceptable, the load-time check for the three spec-resolvable
axes can be scoped to `load_workflow_spec` — the merged-document path every real squad takes, which
no hand-built partial spec goes through. The render-boundary refusal is needed either way.

## Acceptance criteria

- A spec attaching a view name that no `[views]` entry declares — because it was dropped through
  `[selected]`, or because the name is a typo — is refused at load with a message naming the type,
  the view name and, where applicable, the `[selected]` provenance.
- A spec attaching a `subentity`-source view to a type that declares no `subentity_kind` is refused
  at load, with a message naming both.
- A view whose presentation template is missing raises a `SquadsError` carrying the expected path,
  never a `jinja2.TemplateNotFound` traceback.
- A type declaring `ref_rule_target_present` with no `:<T>` parameter is refused at load.
- Dropping a non-reserved bundled type through `[selected].items` leaves the squad usable without a
  second edit in another type's block.
- A `ref` source may project a badge code that at least one declared item type carries; a code no
  declared type carries is still refused.
- `sq workflow lint` and `sq check` report each of the above before any item is read, not on the
  first `show`.
- Every spec fixture in the suite is internally consistent — a fixture spreading `bundled.items`
  carries the matching `views`, and a `[selected].items` enumeration lists every type it does not
  deliberately drop.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite clean; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 842 add-subtask "<title>"`; track with `sq task 842 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Validate ItemSpec.views on its three spec-resolvable axes

<!-- sq:subtask:ST1:body -->
Validate `ItemSpec.views` reciprocally, on the three axes a spec can resolve without touching the
filesystem. Pattern-match `_check_ref_rule_targets` and `_check_field_collections`, which do exactly
this shape for the sibling attached-by-name lists.

**Axis 1 — the named view survived `[selected]`.** With `[selected] views = []` alone,
`sq workflow lint` reports `workflow spec OK`, `sq check` reports `no issues`, and
`sq milestone <n> show` exits 1 with `no declared view 'milestone_rollup'`. This is BUG-837. The
message should carry the `[selected]` provenance the same way the dropped-type diagnostics already
do.

**Axis 2 — the named view exists at all.** `items.milestone.views = ["milestone_rollup",
"typo_view"]` lints clean and exits 1 on the first `show`. A typo in an attachment name is
unreachable until an item of that type is read.

**Axis 3 — the source is compatible with the attaching type.**
`items.guide.views = ["story_summary"]`, where `story_summary` has a `subentity` source of kind
`story`, lints clean and then exits 1 on `sq guide <n> show` with `view 'story_summary' projects
'story' sub-entities, but GUIDE-<n> is a 'guide' item, which hosts none`. Fully determinable at load:
`ViewSource.kind == "subentity"` plus `spec.item_subentity_kind(attaching_type)`.

Placement: `WorkflowSpec._validate` alongside its five siblings is the natural home. If the fixture
cost proves unacceptable, scope it to `load_workflow_spec` instead — the merged-document path every
real squad takes, which no hand-built partial spec goes through — and say in a comment which was
chosen and why.

Done when: each of the three axes is refused at load with a message naming the type and the view,
and driving `show`/`--json`/`--raw` on the affected type is no longer how an adopter discovers it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Missing presentation template raises a SquadsError

<!-- sq:subtask:ST2:body -->
Turn the missing-presentation-template case into a `SquadsError` at the render boundary. This is
BUG-838, and it is the one axis a load-time spec check cannot cover on its own: an override's
template lives on the filesystem, so the spec can be coherent and the template still absent.

Today a view attached to a type with no `templates/views/<name>.md.j2` produces a raw
`jinja2.exceptions.TemplateNotFound` traceback and exit 1 for every item of that type.
`render_view` (`src/squads/_views.py`) is the single funnel — it renders `views/<view_name>.md.j2`
through the one Jinja engine every path already uses, so one boundary catches every caller.

The refusal must name the path the adopter is expected to create — both the bundled location and
the `.overrides/templates/views/<name>.md.j2` shadow — because the adopter reaching this is
mid-authoring a view, and the message is the whole remedy. `docs/workflow.md` already carries the
sentence to mirror: a view you declare needs a template of its own at that path before it can be
rendered; until you write one, resolve it with `--json`.

Done when: the failure is a clean `SquadsError` + exit 1 with the expected path in the message, no
traceback reaches the user, and a test drives it through the CLI rather than through the engine.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Repair the spec fixtures and the six [selected] enumerations

<!-- sq:subtask:ST3:body -->
Repair the spec fixtures the new load-time check exposes, and the six `[selected]` enumerations that
have quietly stopped being complete. One owner touches all the test fixtures, because these two sets
overlap.

**The ~30 partial specs.** Fixtures that spread `bundled.items` without carrying `bundled.views` are
internally inconsistent by construction: `items.milestone` carries `views = ["milestone_rollup"]` in
every one of them. Two edits already in the tree show the remedy —
`tests/unit/test_identity.py:129` and `tests/unit/test_workflow_spec_artifact.py:86` add
`"views": dict(bundled.views)` to the payload. Apply the same line rather than weakening the check.

**The six `[selected].items` enumerations.** Each gained `"contract"` and none gained `"milestone"`:

- `tests/cli/test_create_refuses_a_dropped_built_in_type.py:25` (`_DROP_GUIDE_AND_BUG`)
- `tests/cli/test_read_path_refuses_a_dropped_built_in_type.py:17` (`_DROP_GUIDE`)
- `tests/integration/test_a_skill_body_appearing_after_init_is_seeded_by_the_next_sync.py:35` (`_KEPT`)
- `tests/integration/test_playbook_guide_dropped_for_a_non_live_role_is_reported.py:370` (`kept`)
- `tests/integration/test_playbook_prose_survives_a_dropped_type_as_a_bounded_limitation.py:32`
- `tests/integration/test_workflow_override_service_integration.py:652` (`_DROP_GUIDE_SELECTED`)

The asymmetry was forced, not chosen: `contract` **had** to be added or the spec stops loading,
because `[items.feature]` declares a `ref_rules` entry targeting it and
`validators = ["ref_rule_target_present:contract"]`, and `_check_ref_rule_targets` refuses a target
naming an undeclared type. Nothing referenced `milestone`, so nothing forced it. The result is that
each fixture now drops one more type than its own comment says it does — `_DROP_GUIDE_AND_BUG`'s
comment still claims it keeps every other type — and five tests with nothing to do with views now
silently exercise `_prune_orphaned_type_owned_views`. No assertion is currently wrong; the trap is
for the next person to edit one of these lists.

Add `"milestone"` to all six and correct any comment that becomes false. If one is deliberately left
dropping `milestone`, say so in its comment.

Two smaller corrections found in the same sweep, both comment-level:
`tests/unit/test_declared_ref_rules_are_not_inert.py:126` sets `entry["validators"] = []` for every
type and also strips `epic`'s `no_parent`, under a comment describing only `feature`'s entry;
`tests/cli/test_help_text_follows_spec_vocabulary.py:60` now asserts a truncated prefix because nine
types no longer fit the pinned 80-column help width — that weakening is deliberate and documented,
leave it, but note that declared-order coverage of the last two types is genuinely lost.

Done when: no fixture spreads `bundled.items` without its matching `views`, every `[selected]`
enumeration is complete or says why it is not, and no fixture comment describes an edit that is no
longer what the code does.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse a paramless ref_rule_target_present at load

<!-- sq:subtask:ST4:body -->
Refuse a `ref_rule_target_present` declaration that carries no `:<T>` parameter. It currently loads
clean, lints clean, and is permanently inert — nothing ever fires, and nothing tells the adopter why.

Repro: an override declaring `[items.bug] validators = ["ref_rule_target_present"]` gives
`sq workflow lint` -> `workflow spec OK` and `sq check` -> `no issues`, with a settled bug and a
contract both in the corpus.

Three guards each let it through for the same reason:
`_check_validators_assignment` (`src/squads/_workflow/_models.py:1140-1147`) accepts the bare name
because `ref_rule_target_present` is in `VALIDATOR_NAMES`; `_check_ref_rule_targets`
(`src/squads/_workflow/_models.py:1150-1189`) skips it with `if bare != "ref_rule_target_present"
or not sep: continue`; and the validator itself builds its target set behind the same `and sep`
guard (`src/squads/_services/_validators.py:485-490`), so `targets` is empty and it returns
immediately.

This is the mirror image of a case the same code deliberately refuses. `_check_ref_rule_targets`'
own docstring says a type selecting `ref_rule_target_present:<T>` must declare a `ref_rules` entry
targeting `<T>`, because otherwise the accepted set is empty by construction and the check would
warn forever at runtime — refused at load rather than warning forever. A missing parameter produces
the opposite empty set by the same reasoning: an inert declaration is a lie about what the spec does.

`PARAMETERIZED_VALIDATOR_NAMES` already makes a *surplus* parameter an error on every other catalog
name. Add the opposite direction — a required-parameter set, or one more clause in
`_check_ref_rule_targets`' second loop.

Done when: the bare name is refused at load with a message that names the type and says the
parameter is required, and the surplus-parameter refusal on other catalog names is unchanged.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — A [selected] drop strips the declarations targeting that type

<!-- sq:subtask:ST5:body -->
Make dropping a bundled type through `[selected].items` a single edit, the way the same release
already decided it should be for the other new type.

Dropping `contract` — a supported customisation of a non-reserved type — bricks the squad. Every
command exits 1 until the adopter also edits `[items.feature]`, because `[items.feature]` declares
`ref_rules = [{ kind = "implements", target = "contract" }]` and
`validators = ["ref_rule_target_present:contract"]`, and both checks refuse a target naming an
undeclared type. Driven across every bundled non-roster type: `task`, `bug`, `decision`, `milestone`,
`review` and `guide` all drop cleanly; `epic` and `feature` fail on pre-existing `parents` couplings.

The diagnostics are good — both name the exact key and both carry `[selected]` provenance — and the
`parents` precedent means this is not a new class of coupling. What makes it worth closing is the
asymmetry inside one release: `_prune_orphaned_type_owned_views`
(`src/squads/_workflow/_loader.py:625-666`) exists precisely so dropping `milestone` needs no second
edit, and the bundled spec's own comment states the rationale — no view left declared over a type
that no longer exists, and no second `selected.views` line for an adopter to remember. `contract`
gets no such courtesy.

The remedy is the same shape and the same layer: when `[selected].items` drops a type, strip any
surviving type's `ref_rules` entries whose `target` is the dropped type, and any
`ref_rule_target_present:<dropped>` validator entry, at the raw-mapping layer the prune already
operates at. `tests/unit/test_workflow_reserved_vocab.py::_spec_without_type` already implements
exactly that filter, in the test suite, doing the loader's job for it — reuse its partition logic
rather than reinventing it, and consider whether the helper should now come from the loader.

Scope note: this strips declarations that *target* a dropped type. It does not touch `parents`, so
`epic` and `feature` keep failing on their own coupling — that pre-existing behaviour is out of
scope here and should not be quietly widened.

Done when: dropping any non-reserved bundled type through `[selected].items` leaves every command
working with no second edit, and the `parents` coupling on `epic`/`feature` is unchanged.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Scaffolded view example says it needs its own template

<!-- sq:subtask:ST6:body -->
Make the scaffolded view example teach the whole shape. `sq override scaffold workflow` writes a
commented `[views.related_incidents]` example (`src/squads/_overrides/_service.py:530-539`). An
adopter who uncomments it gets a view that loads and lints clean and then fails the moment anything
renders it, because no `templates/views/related_incidents.md.j2` exists and the scaffold says
nothing about needing one.

`docs/workflow.md` already carries the sentence to mirror: a view you declare needs a template of
its own at that path before it can be rendered; until you write one, resolve it with `--json`. The
fix is one comment line in the scaffold body saying the same thing, naming the exact path the
example would need.

The meta test added alongside it,
`tests/meta/test_scaffolded_override_examples_load_against_the_live_models.py:76-88`, asserts only
that the example *loads*, and its docstring frames the risk as teaching a shape
`sq workflow lint` rejects on the next run — which is precisely the failure this example does not
have. Widen it, or add a sibling, so the check is that a scaffolded example is usable end to end,
not merely parseable.

Done when: an adopter who uncomments the example knows from the scaffold alone what else they must
write, and the meta test would catch the next example that loads but cannot render.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Let a ref source project a badge some declared type carries

<!-- sq:subtask:ST7:body -->
Narrow the `ref`-source field check so it refuses what it is actually reaching for.

A `ref`-source view may currently project only base attributes; naming any badge field is refused at
load. `_resolve_view_source` (`src/squads/_workflow/_models.py:1558-1584`) returns an empty
declared-field set for a `ref` source by construction, so no badge code can ever resolve for one.
That makes the bundled `milestone_rollup` structurally unable to show a member's priority, and
blocks every adopter view over a membership edge from carrying any collection value.

The resolver already handles the case the check refuses. Calling `squads._views.project` directly
with the refused declaration, against a milestone holding a feature, a task, a bug and a decision,
groups correctly and emits a uniform payload: `_cell` resolves the collection **per record**
(`resolve_collection(rec.kind, code, spec)`, `src/squads/_views.py:229-245`), so a type that declares
the field renders its badge and a type that does not renders `null` — already the shape for an unset
badge, so the `--json` contract is unchanged.

The documented rationale — a ref source's records can be items of any type, so there is no single
type whose declared fields apply to all of them — argues for refusing a code **no** declared type
carries, not for refusing every badge code outright. The bundled `priority` field is declared by
every bundled work type, and a roll-up of what is left is exactly where you want it.

**Gated on an architect ruling.** This is a spec-vocabulary question, not a correctness fix: whether
a `ref` source may name a badge code that only *some* of its records can carry. Do not land the
relaxation before that ruling exists; the shape above is the recommendation to put in front of it,
not a decision already taken.

Done when: the ruling is on the record, and — if it goes this way — a `ref` source may name a badge
code at least one declared item type carries, a code no declared type carries is still refused with
its current message, and the projection's uniform shape is proven unchanged for heterogeneous members.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T17:19:55Z] Robert Architect:
  - - **ST7 is unblocked.** Ruled and recorded as an amendment at the end of ADR-776 ("Amendment note — 2026-08-26: what field codes a `ref` source may project"). A `ref` source may name a field code **at least one declared item type carries**; a code no declared item type carries stays refused. Read the amendment before starting — the reasoning is not the finding's.
    - **ST7 can proceed, but three of its lines need rewording first.**
    - 1) Its Done-when says a code no declared type carries "is still refused **with its current message**". That is now wrong. The current message's second clause — "nor a field 'targets' declares" — asks the author to make a **ref kind** declare a field, which no spec grammar expresses, and its fix hint tells an adopter to add back a key they have already written (driven, against an override declaring `impact` on `feature` alone). The `ref` branch needs its own text: name the view and the code, say no declared item type declares it, and give the two remedies that exist (declare the field on a type, or name a base attribute — list them). `subtree` and `subentity` keep the existing clause unchanged; there it names a type/kind that can genuinely declare a field.
    - 2) "at least one declared item type" needs pinning on two axes it currently leaves open. **Item types only, never sub-entity kinds** — a `ref` source's records are always items (`_record_from_item`), so a code declared solely by a sub-entity kind stays refused. **Every declared item type, roster included** — do not reach for `field_badge_codes`/`non_roster_types()`; that precedent backs a filter door over work items, whereas a `ref` source may legitimately project roster records (a skill's edge to the role that preloads it), so excluding roster would refuse an adopter's field on `role` while it resolves fine.
    - 3) "the projection's uniform shape is proven unchanged for heterogeneous members" should name the assertion that makes the ruling durable: one projection containing **both** a record of a type that declares the field but has it unset **and** a record of a type that does not declare it, asserting the two cells are identically `null`. That is the payload ruling — there is one absence, not two — and without that test the next contributor is free to add a per-record "not declared" marker, which §2 refuses.
    - **`subtree` is out of scope and must not be touched.** Driven: `_resolve_subtree_source` filters descendants to `source.name`'s own type, so a subtree source's records are homogeneous and its declared-field set is already exactly right — `subtree`-over-`task` naming `severity` stays correctly refused, as does `subentity`. A patch that generalises across all three source kinds has misidentified the defect; the change belongs in the `ref` branch of `_resolve_view_source`/`_check_view_fields` alone.
    - **A doc edit rides with it**, and the wording is load-bearing: `docs/workflow.md` currently states "A `ref` source projects base attributes only … refused at load rather than rendered blank", and its base-field table row `any declared badge field` shows `—` for `ref`. Both become false. The blank a `ref` record renders for a field its type does not declare is the same blank an unset declared field already renders everywhere in squads — that identity is the point, so say it rather than dropping the sentence.
    - No ruling on whether the bundled `milestone_rollup` should now project `priority`. That is a presentation call for its owners, not a consequence of this.
    - @python-dev ST7 is yours once the wording above lands; @tech-lead the three rewordings are on the subtask, not on the acceptance criteria — the task-level criterion ("A `ref` source may project a badge code that at least one declared item type carries") already reads correctly.
- [2026-08-26T17:45:35Z] Elias Python:
  - ST1 done: WorkflowSpec._validate now checks ItemSpec.views reciprocally via a new _check_item_views (placed alongside its five siblings, so it fires from the merged mapping on both load_workflow_spec and sq workflow lint). Axis 1 (view dropped from [selected].views while items.<type>.views still names it) and axis 2 (typo'd attachment) both refuse with 'views entry X does not name a declared [views] entry', axis-1 automatically annotated with [selected] provenance by the existing _annotate_deselections. Axis 3 (subentity-source view attached to a type hosting no/a different subentity kind) refuses naming both the type and the view. All three driven end-to-end in a scratch squad: lint refuses at exit 1 before any item exists.
  - ST2 done: render_view (src/squads/_views.py) now calls has_template before rendering and raises SquadsError naming both templates/views/<name>.md.j2 and the .overrides shadow; --json is unaffected. Driven through sq workflow view <name> <id>: clean error: line, exit 1, no traceback.
  - ST3 done: fixture sweep, two parts. (a) 27 hand-built partial specs that spread bundled.items/base.items without the matching views now carry it (2 already had it correctly). (b) all six [selected].items enumerations named in the task now carry milestone, plus corrected the two stale comments (_DROP_GUIDE_AND_BUG's claim, test_declared_ref_rules_are_not_inert's under-described validators clear). Restoring milestone into test_playbook_prose_survives_a_dropped_type_as_a_bounded_limitation's fixture surfaced a real, previously-hidden second bound member (sq-milestone's own 'sq task <n> ref add MILE-… --kind targets' example) — widened that assertion to match, not suppressed. Left test_help_text_follows_spec_vocabulary's truncated-prefix weakening untouched per the task's own note (deliberate, documented).
  - ST4 done: _check_ref_rule_targets now refuses a bare ref_rule_target_present (no :<T>) at load, same clause family as the surplus-parameter check on other catalog names.
  - ST5 done: new _strip_ref_rule_targets_of_dropped_types in the loader strips a surviving type's ref_rules/ref_rule_target_present:<T> entries that target a type [selected].items just dropped — wired into both load_workflow_spec and lint_workflow_spec (lint didn't get the analogous existing view-prune either; needed here so lint and load agree). Driven: dropping contract now leaves every command working with no second edit, lint clean. epic/feature's parents coupling on dropping epic is unchanged (out of scope).
  - ST6 done: the scaffold's [views.related_incidents] example now carries a comment naming the exact template path it needs; widened the existing meta test with a sibling that drives the render failure end to end (SquadsError, not a load-only check).
  - ST7: was blocked at start, unblocked mid-task by the architect's ruling (ADR-776 amendment + REV-840 F7 comment + TASK-842 comment). Implemented as ruled, not as the finding originally reasoned: _resolve_view_source's ref branch now returns the union of every declared item type's own fields (roster included, never non_roster_types()); _check_view_fields carries a rewritten ref-specific message (never 'make a ref kind declare a field'); subtree/subentity untouched. Added the payload-uniformity test the ruling asked for (declared-but-unset vs never-declared render identically null in one heterogeneous projection) and docs/workflow.md's base-attributes section rewritten to match. F7 is NOT left pending — it is fully implemented per the ruling.
  - Fixtures: 27 files gained the missing views key (test_identity.py and test_workflow_spec_artifact.py already had it), 6 files gained milestone in their [selected] enumeration, 2 files got comment corrections, 1 file's assertion widened to match a real surfaced fact, plus a new tests/unit/test_dropped_type_ref_rule_target_cascade.py (9 tests) for ST5. Made explicit rather than just green: every one of the 27 now states in its own payload that it carries the matching views, not just bundled.items.
  - Gates: pyright/ruff check/ruff format clean. tests/meta full: 260 passed. Targeted (unit+cli+integration+service+meta+tui): 4318 passed, 2 skipped, 0 failed — stable across two runs. sq check clean. Did not run the full suite (per brief); did not touch _cli/_common.py, _rendering/_engine.py, _services/_base.py, or _migrations/_v0_11_to_v0_14.py.
  - Marked REV-840 F6/F7/F9/F11/F12/F13 and BUG-837/BUG-838 Fixed, each citing this task. @reviewer for re-verification.
<!-- sq:discussion:end -->
