---
id: TASK-959
sequence_id: 959
type: task
title: Delete the view projection layer, its grammar, and type-attachment
status: Done
parent: FEAT-904
author: tech-lead
priority: urgent
refs:
- ADR-880:implements
description: Rip out the projection middle layer, fields/group_by/order_by, its validators
  and ItemSpec.views; rebuild milestone_rollup as source plus template
subentities:
- local_id: ST1
  title: Relation sources resolve to real items; delete the record layer
  status: Done
  story: US1
- local_id: ST2
  title: Collapse the render and --json seams onto one source shape
  status: Done
  story: US1
- local_id: ST3
  title: Delete fields/group_by/order_by and the validators that proved them
  status: Done
  story: US2
- local_id: ST4
  title: Delete ItemSpec.views type-attachment and its orphan pruning
  status: Done
  story: US3
- local_id: ST5
  title: Rebuild milestone_rollup as a one-line source plus a Jinja template
  status: Done
  story: US4
- local_id: ST6
  title: Update the view reference docs to the reduced declaration
  status: Done
  story: US2
created_at: '2026-09-21T16:48:35Z'
updated_at: '2026-09-24T08:49:22Z'
---
<!-- sq:body -->
## Scope

Rip out the projection middle layer FEAT-693 built, the TOML grammar that fed it, the
validators that existed only to prove that grammar resolved, and the type-attachment axis —
then rebuild `milestone_rollup` as a one-line source plus a Jinja template. ADR-880 is the
ruling; its scope list is authoritative and reproduced per subtask below.

One task, not several: every subtask edits `_views.py`, `_workflow/_models.py` or both, and a
half-deleted middle layer does not typecheck. This is a single coherent dev pass for one
Python developer.

## The shape after the change

A view declaration is `source` and nothing else. `resolve_source` returns each kind's own
native shape — for the three relation kinds, real `Item` / `SubEntity` objects, not a
normalised record — and the presentation template receives that shape directly, plus the host
item and the active spec. Grouping and ordering are Jinja (`groupby`, `sort`, `selectattr`)
under `StrictUndefined`. Badges reach a template through the already-registered `badge`
filter; the settled-versus-delivered distinction is already on `WorkflowSpec`
(`is_delivered`, `first_settled_status`, `status_role`) and stays there.

## Acceptance for the whole task

- Every construct named in ADR-880's deletion list is gone from the source tree — not
  unreachable, gone — and a grep for each name returns hits only in history and the changelog.
- `sq workflow view milestone_rollup <id>` and the tag-driven render both produce, for a fixed
  fixture milestone, output identical to the pre-change render.
- Loading a spec that still declares `fields`, `group_by`, `order_by` or `items.<type>.views`
  fails at load with an error naming the offending key.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and `sq check` clean.

## Out of scope

- The adopter-facing upgrade narrative for the retired grammar — FEAT-908 owns that. This task
  owns only the reference docs that would otherwise describe a grammar the code no longer
  accepts.
- REV-920 F10 (`self --json` spec identity). See the task discussion for the ruling.
- The `required` view flag and the write refusal — TASK-942, which must not run concurrently
  with this one. See the task discussion.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 959 add-subtask "<title>"`; track with `sq task 959 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Relation sources resolve to real items; delete the record layer

<!-- sq:subtask:ST1:body -->
Delete the middle layer named in ADR-880: `_RawRecord`, `Cell`, `ViewFieldMeta`, `ViewRecord`,
`ViewGroup`, `Projection`, `project`, `_cell`, `_badge_cell`, `_sort_key`, `_BASE_RESOLVERS`,
`projection_json`, and the `_record_from_item` / `_record_from_subentity` normalisers that
exist only to feed them.

The three relation resolvers survive verbatim in what they *join* — ref inversion, the subtree
walk, the sub-entity collection read — and change only in what they *return*:
`_resolve_ref_source` and `_resolve_subtree_source` return `list[Item]`,
`_resolve_subentity_source` returns the host's own `SubEntity` objects (carry the kind
alongside if a template needs it, rather than reintroducing a wrapper record).
`SourceResult` narrows accordingly and `RELATION_KINDS` keeps its meaning.

`_delivery_target` / `_is_delivered` do not delete with the column they backed: the
settled-versus-delivered distinction is real logic and already lives on `WorkflowSpec`
(`is_delivered`, `first_settled_status`, `status_role`). Use the spec methods from templates;
remove the `_views.py` private copies once nothing calls them. Verify no other caller first.

`_badges.py` survives whole and is already registered as the `badge` filter in
`_rendering/_engine.py` — no new registration needed, but confirm a template can resolve a
badge for a heterogeneous record set (the per-type collection resolution is what the deleted
`_badge_cell` was doing).

Rewrite the `squads._views` module docstring: the "three parts and no fourth" framing and the
two-family projection split are the shape being deleted.

Acceptance: none of the listed constructs is reachable from `sq workflow view`, `sq check` or
any render path; a grep for each name returns nothing outside history and the changelog;
`tests/unit/test_view_projection_engine.py` and
`tests/unit/test_view_expresses_the_subentity_summary_shape.py` are deleted or rewritten
against the new shape rather than left asserting the retired one.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Collapse the render and --json seams onto one source shape

<!-- sq:subtask:ST2:body -->
With the projection gone, `render_resolved_source` no longer branches between two families:
every kind renders through one path that hands the template the resolved source under a single
fixed context name, plus `item`, `spec` and `squad_dir` — the contract
`render_source_view` already implements for `role`/`playbook`/`self`. Collapse
`render_view` into it rather than keeping two entry points, and keep the
`ViewTemplateMissingError` pre-check exactly as it is (it is the clean refusal for a declared
view with no template, and every caller's catcher depends on the subtype).

`ViewsMixin.resolve_view` returns a `Projection` today and has no meaning after this;
`resolve_view_source` is the surviving resolution entry point. Fold the callers onto it and
delete the dead one, including its "the projection this view produces" docstring.

`sq workflow view <name> <id> --json` already dispatches per source kind in
`_cli/_workflow_cmd._view_json_payload`. The relation kinds join that rule instead of standing
outside it: a `ref` or `subtree` source emits what `sq tree --json` / `sq list --json` already
emit, a `subentity` source emits what the per-kind sub-entity list already emits. No `{fields,
group_by, groups}` envelope survives anywhere.

Before landing, re-run ADR-880's client check rather than trusting it: grep
`clients/vscode/src` for `workflow view`, `milestone_rollup`, `projection` and a view `groups`
payload, and report the counts. The envelope is a documented JSON shape
(`docs/stability.md`), so its removal is a breaking change that needs a changelog entry even
with zero consumers.

Acceptance: one render entry point, one resolution entry point; `--json` for all six kinds
emits an existing per-source shape; the grep over the client is run and its result reported in
the handoff comment, not assumed.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Delete fields/group_by/order_by and the validators that proved them

<!-- sq:subtask:ST3:body -->
Delete `ViewSpec.fields`, `group_by` and `order_by`, so a `[views.<name>]` entry accepts
`source` and nothing else. Delete the validators that existed only to prove that grammar
resolved: `_check_view_fields`, `_check_item_views`, and `VIEW_BASE_FIELDS_BY_SOURCE`.
`_check_view_source` survives unchanged — a source's `name` resolving against its `kind`'s
vocabulary is real and cheap, and it is the one referential check the reduced grammar still
needs.

Removal must be loud. A spec (bundled, project override, or a hand-written
`.overrides/workflow.toml`) that still declares `fields`, `group_by`, `order_by` or
`items.<type>.views` fails at load with an error **naming the key it found**, not a silent
drop into an unknown-key sink. Check how `_workflow/_loader.py` currently treats unknown keys
in a view table before adding the rule — if unknown keys are already rejected generically, the
work is to make the message name these four specifically, because a generic "unknown key" does
not tell an adopter their 0.14 declaration was retired. FEAT-908 documents the upgrade against
exactly this error text, so the wording is a contract: keep it stable and tell the writer what
it says.

Downstream surfaces that carry the retired keys and must lose them: the `sq workflow views`
listing and its `--json` payload columns (`_cli/_workflow_cmd.py`), and whatever `sq workflow
lint` reports about field/`group_by`/`order_by` resolution.

Acceptance: `_check_view_fields`, `_check_item_views` and `VIEW_BASE_FIELDS_BY_SOURCE` are
gone; `_check_view_source` still validates a source's `name` against its `kind`'s vocabulary;
each of the four retired keys, declared on its own, produces a load-time error naming that
key, covered by a test per key rather than one test for the family;
`tests/unit/test_view_declaration_referential_checks.py` is updated to the surviving checks.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Delete ItemSpec.views type-attachment and its orphan pruning

<!-- sq:subtask:ST4:body -->
Delete `ItemSpec.views` and `_prune_orphaned_type_owned_views` with it. The pruner exists
solely to un-brick a squad whose `[selected]` deselection orphaned a type-attached view the
adopter never wrote; removing the attachment removes the coupling that made it necessary. No
bundled view carries a type attachment today, so the bundled spec needs only its explanatory
comments rewritten, not a declaration removed.

Consumers to follow through:

- `build_item_json`'s `views` key (`_cli/_common.py`) — the one remaining caller of
  `projection_json`. It goes with the attachment; `sq <type> <n> show --json` stops carrying a
  `views` key at all.
- `_workflow/_loader.py`'s deselection handling, where `owned_by_dropped` and the surviving-
  items scan read `items.<type>.views`.
- The `[selected].views` interaction as described in the bundled spec comments and in
  `_overrides` scaffold text — dropping a view stays supported, but it no longer has a
  type-attachment cascade to reason about.
- `tests/unit/test_milestone_view_deselect_cascade.py` and any test asserting the pruner's
  courtesy behaviour.

Acceptance: `items.<type>.views` is gone from the spec model and a spec declaring it fails at
load naming the key (the error rule lands with the grammar subtask — verify the type-attachment
key is covered by it); `_prune_orphaned_type_owned_views` is deleted, not merely unreachable;
`sq <type> <n> show --json` carries no `views` key; `projection_json` has no callers left
before it is deleted in the record-layer subtask.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Rebuild milestone_rollup as a one-line source plus a Jinja template

<!-- sq:subtask:ST5:body -->
`[views.milestone_rollup]` reduces to its one line, `source = { kind = "ref", name =
"targets" }`. The join is the source and it is untouched; what goes is the step after it.
`templates/views/milestone_rollup.md.j2` is rewritten against a list of real `Item` objects.

Read the current template before the current declaration — they disagree about what the view
does, and the template wins. The declared `group_by = "status_role"` produces no visible
heading: the template ignores `group.key` and re-partitions every record into Delivered /
Outstanding / Settled-without-delivering off the `delivered` and `settled` cells. Reproduce
those three partitions from the spec (`is_delivered`, `status_role`,
`first_settled_status`), not from a literal status name.

`order_by = ["type", "id"]` is applied in `project` as a reversed stable sort: records are
ordered by **sequence number** first (`number_for_id`, with the id prefix breaking a tie
between two types sharing a number), then stably by the `type` cell's text. The visible result
is type-ascending, sequence-ascending within a type, and that is what the Jinja `sort` must
reproduce — sorting on the formatted id string would silently change the order for any corpus
past nine items.

Method: capture the pre-change rendered output for a fixture milestone whose members span
several types, several statuses, and at least one member in each of the three partitions.
Rewrite, then diff against the capture. The test asserts that diff, not a hand-written
expectation of what the output ought to look like.

Rewrite the bundled spec's view comment block too — it describes a three-part declaration and
a type-attachment axis that no longer exist.

Acceptance: the declaration is one `source` line; rendered output for the fixture milestone is
byte-identical to the capture; `sq workflow view milestone_rollup <id>` and the tag-driven
render through the body-read boundary both produce it; the `badge` filter is what supplies any
status emoji, never a hand-written one in the template.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Update the view reference docs to the reduced declaration

<!-- sq:subtask:ST6:body -->
The reference docs describe a grammar the code will no longer accept. Update them to the
reduced declaration — `source`, and a template resolved by the view's own name.

Known surfaces (re-grep rather than treating this list as complete):

- `docs/workflow.md` — the "projection" part of the three-part view description, the
  `fields`/`group_by`/`order_by` reference entries, the worked `[views.…]` example, the
  "template receives `fields`, `group_by` and `groups`" contract, and the load-time
  cross-reference paragraph.
- `docs/overrides.md` — the same worked example, the "changing a bundled view's `group_by`"
  guidance, the `fields = ["$(*self)", …]` splat note as it applies to a view, and the
  dropping-a-view section where it leans on type attachment.
- `docs/stability.md` — the `sq workflow views --json` row (`fields`, `group_by`, `order_by`)
  and the `{fields, group_by, groups}` projection payload entry. Both are documented JSON
  shapes being removed, so the change is a stability-surface change, not a wording fix.

What the docs must now say about the template contract: it receives the source's own
unflattened shape, the host item and the active spec, and it does its own grouping and
ordering with Jinja's `groupby` / `sort` / `selectattr` under `StrictUndefined`.

Two boundaries to respect. These are adopter-facing docs: no sq item ids, no repo or
build-process content. And the upgrade narrative for an adopter carrying a 0.14 declaration
belongs to FEAT-908 — say what the grammar *is*, and leave what to do about an old one to the
feature that owns it.

Acceptance: `rg 'group_by|order_by'` over `docs/` returns nothing describing a view
declaration; the three-part framing is gone from every doc that carried it; a CHANGELOG entry
records the removed declaration keys and the removed `--json` shapes, drafted by the technical
writer rather than spliced from this brief.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-21T16:50:22Z] Olivia Lead:
  - Breakdown of FEAT-904 into TASK-959, six subtasks: ST1/ST2 → US1, ST3/ST6 → US2, ST4 → US3, ST5 → US4. One task, not several — every subtask edits `_views.py`, `_workflow/_models.py` or both, and a half-deleted middle layer does not typecheck.
    
    Three things the dev must know before starting:
    
    1. **Textual collision with TASK-942 — they must not run in the same tree.** TASK-942 (required views) adds a `required` key to the same `ViewSpec` model this task strips three keys from, and edits the same view-grammar sections of `docs/workflow.md` / `docs/overrides.md` / `docs/stability.md`. Sequence them: TASK-959 lands first, TASK-942 rebases onto the reduced declaration. Running them concurrently in one worktree produces a merge conflict on the one file that defines the grammar.
    
    2. **ADR-880's bundled `views = ["milestone_rollup"]` type-attachment line is already gone** — dropped by an earlier ruling. ST4 deletes the `ItemSpec.views` *mechanism* and its pruner; there is no bundled declaration left to remove, only explanatory comments to rewrite. Do not go looking for it.
    
    3. **The current milestone_rollup declaration and its template disagree**, and the template wins. `group_by = "status_role"` produces no visible heading — the template ignores `group.key` and re-partitions on `delivered`/`settled`. ST5 carries the detail. Capture the pre-change output before touching anything; the acceptance is a diff against that capture, not a hand-written expectation.
- [2026-09-21T16:50:23Z] Olivia Lead:
  - **REV-920 F10 — ruled OUT of this task's scope.**
    
    F10: `self --json`'s spec identity (`{schema_version, override}`) reports override-*file existence*, not merge outcome, and cannot distinguish two different override documents. My earlier note on FEAT-904 flagged this feature as the natural place to reconsider it, because this feature touches view `--json`. On reading the scope, it is not:
    
    - What this task changes about `--json` is the *relation* kinds — deleting the `{fields, group_by, groups}` envelope so they join the per-source dispatch every other kind already uses. The `self` payload is `build_item_json` plus a spec-identity block, and neither is a projection-layer surface. It would come out of the rip-out untouched.
    - Fixing it is a semantic decision, not a deletion: identity has to become a function of the *merged* spec (a digest over the merge result, or the override document's own hash), and what a client is entitled to compare with it is a contract question. That deserves its own ruling and its own acceptance, not a rider on a task whose gate is "the named constructs are gone".
    
    So F10 stays open on REV-920 and needs a home of its own. @manager — worth a follow-up item under EPIC-897 or a bug, your call; I have not created one (out of my brief here).
    
    For the record, the two findings this feature's own scope *does* resolve, deliberately and not by accident: F9 (inert `fields`/`group_by`/`order_by` on a non-relation view — the keys stop existing) and the ST2 half of F11 (`ViewsMixin` repeating the resolve-a-view preamble — `resolve_view` collapses into `resolve_view_source`). Close those against this task when it lands; do not close F10.
- [2026-09-21T16:51:25Z] Catherine Manager:
  - Dispatched to Elias Python. Sequencing ruled: TASK-959 lands first, TASK-942 rebases onto it — not concurrent, not in one tree. REV-920 F10 stays open on its review; out of scope here per the tech lead, and it needs its own ruling before it gets a home.
- [2026-09-21T19:11:05Z] Elias Python:
  - All six subtasks landed in one pass (ST1-ST6). Deleted per ADR-880's list: _RawRecord, Cell, ViewFieldMeta, ViewRecord, ViewGroup, Projection, project, _cell, _badge_cell, _sort_key, _BASE_RESOLVERS, projection_json, _record_from_item/_record_from_subentity, ViewSpec.fields/group_by/order_by, ViewField, VIEW_BASE_FIELDS_BY_SOURCE, _check_view_fields, ItemSpec.views, _check_item_views, _prune_orphaned_type_owned_views. Relation resolvers now return list[Item]/list[SubEntity] directly; render_view+render_resolved_source collapsed into render_source_view (one render entry point); ViewsMixin.resolve_view (Projection) deleted, resolve_view_source is the sole resolution entry point.
  - Load-time error wording (ST3): extra="forbid" + describe_spec_error already name the offending key generically -- e.g. unknown key 'fields' in 'views.milestone_rollup', accepted keys ['source'] -- for a view, and unknown key 'views' for items.<type>.views. No custom message needed; verified against a real load in tests/unit/test_retired_view_grammar_keys_fail_at_load.py.
  - ST2 client check (re-run, not assumed): grep clients/vscode/src for 'workflow view'/'milestone_rollup'/'projection'/a groups-key payload -- 0 hits on all four, matching ADR-880's own finding.
  - ST5: captured pre-change render from a clean HEAD worktree (not the working tree) for both the direct render and the tag-driven render against MILE-867 (12 members spanning bug/feature types and Verified/Done/Open/InProgress/Draft statuses). Rebuilt template's output is byte-identical on both paths. Chose plain status text (no badge filter) specifically to preserve byte-identity, since the pre-change output carried no status emoji; noted that choice in the bundled workflow.toml comment.
  - Bundled artifacts changed (workflow.toml, milestone_rollup.md.j2) -- regenerated templates_manifest.json/content_store.json; release-gate passed.
  - @tech-writer FEAT-908's stability-surface CHANGELOG entry (removed view declaration keys + removed --json envelope shapes) is not drafted -- changelog prose goes through the writer, not spliced from this brief. The existing 0.15.0 CHANGELOG entry describing the now-deleted three-part grammar as newly shipped is also stale and needs a pass.
- [2026-09-24T07:38:58Z] Catherine Manager:
  - All six subtasks Done and committed (36f19ab0). TASK-959 and FEAT-904 moved to InReview; @reviewer dispatched for a batch review of FEAT-904.
- [2026-09-24T07:55:32Z] Catherine Manager:
  - Back to InProgress for REV-960: @python-dev takes F1-F7 (F1 = pin the accepted new order with a snapshot test, not restore the old order), @tech-writer takes F8 (CHANGELOG).
- [2026-09-24T08:32:56Z] Catherine Manager:
  - REV-960 F1-F8 marked Fixed (uncommitted working tree). Full suite 5083 passed / 0 failed; sq check clean. Back to @reviewer for re-review.
- [2026-09-24T08:39:11Z] Catherine Manager:
  - REV-960 re-review: F1-F7 Verified; F8 reopened (@tech-writer), F9/F10 new (@python-dev). Back to InProgress for those three.
- [2026-09-24T08:45:25Z] Catherine Manager:
  - REV-960 F8 (tech-writer), F9 + fields reason and F10 (python-dev) marked Fixed. Back to @reviewer to verify those three.
<!-- sq:discussion:end -->
