---
id: TASK-843
sequence_id: 843
type: task
title: View projection ordering, payload and the bundled roll-up
status: Done
parent: FEAT-693
author: tech-lead
priority: high
refs:
- REV-840:addresses
- TASK-841:depends-on
- TASK-842:depends-on
description: order_by destroys both resolvers' numeric ordering, the roll-up files
  settled members as outstanding forever, and the template context disagrees with
  its own docs
subentities:
- local_id: ST1
  title: order_by on a badge field follows the declared badge order
  status: Done
  story: US1
- local_id: ST2
  title: order_by on id sorts by sequence number
  status: Done
  story: US1
- local_id: ST3
  title: A projected group exposes count in the template context
  status: Done
  story: US2
- local_id: ST4
  title: Roll-up separates settled-not-delivered from outstanding
  status: Done
  story: US4
- local_id: ST5
  title: Resolve the two unreachable bundled view templates
  status: Done
  story: US2
- local_id: ST6
  title: Show a milestone's target date on its panel
  status: Done
  story: US3
created_at: '2026-08-26T17:05:27Z'
updated_at: '2026-08-26T18:24:17Z'
---
<!-- sq:body -->
## Problem

The view mechanism's uniform projection contract holds — records are identically shaped across all
three sources, field metadata and grouping travel with the payload, membership is never written to
the milestone file. What sits around that contract is wrong in four small ways that compound on the
one view that actually ships: the bundled milestone roll-up mis-orders its members, files settled
work as outstanding forever, hides the type's one distinguishing attribute, and disagrees with its
own documentation about the shape of a group.

## What is wrong

**Ordering.** `_sort_key` (`src/squads/_views.py:247-253`) reduces every cell to a string. A badge
sorts alphabetically by code, ignoring the collection's `ordered = true`; an `id` sorts
lexicographically, so FEAT-15 precedes FEAT-9 and FEAT-100 precedes FEAT-99. The bundled
`milestone_rollup` declares `order_by = ["type", "id"]`, and both source resolvers already sort
numerically (`_resolve_ref_source` at `src/squads/_views.py:154` and `_resolve_subtree_source` at
`:196`, both keying on `number_for_id`) before `order_by` undoes it — so declaring `order_by = ["id"]`
makes the bundled view strictly worse ordered than declaring none.

**Outstanding never reaches zero.** The roll-up template splits on `group.key == "done"` with a bare
`else` (`src/squads/_rendering/templates/views/milestone_rollup.md.j2:5`) — a two-way split over a
multi-valued axis, where `else` is doing the work of "not delivered" and silently absorbing "not work
any more". `sq workflow roles` declares `settled = yes` for `done`, `in_force`, `retired` and
`superseded`, so a Cancelled bug, an Accepted decision and a Superseded ADR are all filed as
Outstanding permanently.

**The payload does not carry the axis the template needs.** `status_role` is projected as a plain
text cell, so the `settled` / `live` flags the `[roles]` catalog declares do not travel with it. The
template cannot currently do better on its own.

**The two documented consumers disagree.** `docs/workflow.md` tells adopters a group has `key`,
`count` and `records`. `ViewGroup` (`src/squads/_views.py:59-66`) declares only `key` and `records`;
`count` exists in `projection_json` (`:296`) alone. Under `StrictUndefined` a template following the
documentation fails loudly. Both bundled templates write `group.records | length`, which is why
nobody noticed.

**Two templates ship unreachable, and a milestone hides its target date.** Detail in the subtasks.

## Severity note on the settled-member bucket

Filed 🟡 medium by the reviewer; treat it as **high**. The milestone type's stated job is answering
what is left, and this makes that answer permanently wrong in the one direction that never resolves:
an adopter who cancels a single scoped item gets a milestone that can never report zero outstanding.
It is silent and plausible-looking — a number that is simply wrong, not a render that visibly fails —
and it falsifies the same acceptance line the type was built against.

## Acceptance criteria

- `order_by` on a badge field follows the collection's declared badge order for an `ordered`
  collection, falling back to the code for an unordered one or an unrecognised value.
- `order_by` on `id` orders by sequence number, so FEAT-9 precedes FEAT-15 and FEAT-99 precedes
  FEAT-100 in the bundled roll-up.
- A projected group exposes `count` in the template context and in `--json`, with the same value.
- The roll-up distinguishes delivered, outstanding and settled-not-delivered members off declared
  role properties, never a literal status name — a milestone whose remaining members are all settled
  reports zero outstanding.
- A milestone's `target_date` is readable on a human surface, not only through `--json`.
- Every view template in the wheel is reachable from a bundled declaration, or is not in the wheel.
- The template manifest matches the tree and its freshness check passes; `pyproject.toml` still
  reads `0.14.0` and only the `0.14.0` manifest entry moves.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite clean; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 843 add-subtask "<title>"`; track with `sq task 843 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — order_by on a badge field follows the declared badge order

<!-- sq:subtask:ST1:body -->
Make `order_by` on a badge field follow the collection's declared badge order.

`_sort_key` (`src/squads/_views.py:247-253`) returns `(1, v.get("code", ""))` for a badge cell, so
sorting is alphabetical by code. The bundled `priority` collection declares `urgent, high, medium,
low` with `ordered = true` — the flag exists precisely to say that order is meaningful — and
alphabetical gives `high, low, medium, urgent`. Driven: four tasks created low / urgent / medium /
high, a subtree view with `order_by = ["priority"]`, and `sq workflow view` returns them in exactly
that wrong order.

The engine already ranks the same badges correctly elsewhere.
`squads._services._base.ItemFilter._meets_min` (`src/squads/_services/_base.py:173-185`) indexes into
`[b.code for b in coll.badges]`. A badge cell's sort key should resolve the same way — index into the
declared badge list for an ordered collection, falling back to the code for an unordered collection
or an unrecognised value, matching `_meets_min`'s own graceful-non-match discipline.

`_sort_key` currently takes only a `Cell`, so it cannot see the field or the spec; it will need the
field's type and the resolved collection threaded in from `project()`.

Every `order_by` in the suite names a text field (`tests/unit/test_view_projection_engine.py:170,274,
302`, `tests/unit/test_view_declaration_referential_checks.py:212`,
`tests/service/test_view_resolve_and_render.py:198`), so the badge branch has no coverage of its
result. Add table-driven coverage across ordered and unordered collections, an unrecognised code, and
a null cell — not one test per branch.

Done when: an `order_by` on any ordered collection's field returns declared order, and an unordered
collection or unresolvable value degrades to today's behaviour rather than crashing.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — order_by on id sorts by sequence number

<!-- sq:subtask:ST2:body -->
Make `order_by` on `id` sort by sequence number instead of by the formatted string.

`_sort_key`'s text branch (`src/squads/_views.py:253`, `return (1, str(v))`) compares the formatted
id, because `_record_from_item` sets `identity=it.id`. Driven: a milestone with FEAT-9 and FEAT-15 as
members renders

```
## Outstanding (2)

- **FEAT-15** (feature) Draft — Second feature
- **FEAT-9** (feature) Draft — Parent
```

The same shape gives FEAT-100 before FEAT-99 and FEAT-1000 before FEAT-2. This repository's own corpus
is four digits wide, so a milestone spanning the current range and anything below TASK-100 reads
scrambled.

The perverse part: both source resolvers already sort numerically — `_resolve_ref_source`
(`src/squads/_views.py:154`) and `_resolve_subtree_source` (`:196`) both key on `number_for_id` — and
`project()`'s `order_by` pass then re-sorts and destroys it. The bundled `milestone_rollup` declares
`order_by = ["type", "id"]`, so it is strictly worse ordered than if it declared no `order_by` at all.

`id` should sort on `number_for_id`, not on the string. Same fix site as the badge-order subtask, so
land them together: `_sort_key` needs to know the field's type either way.

Note the prefix question explicitly when you fix it: with mixed types in one group, sorting purely on
the number interleaves prefixes. `order_by = ["type", "id"]` already handles that for the bundled
view by sorting on type first; decide and record whether `id` alone should tie-break on prefix, and
cover the mixed-type case in the test.

Done when: a roll-up over a corpus crossing a digit boundary lists members in sequence order, and a
mixed-type group's ordering is deliberate rather than incidental.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — A projected group exposes count in the template context

<!-- sq:subtask:ST3:body -->
Give `ViewGroup` a `count`, so the two documented consumers of one projection agree about the shape
of the same object.

`docs/workflow.md` tells adopters the template receives groups with `key`, `count` and `records`.
`ViewGroup` (`src/squads/_views.py:59-66`) declares `key` and `records` only; `render_view` passes the
dataclasses straight through (`:316-321`) and the Jinja environment runs under `StrictUndefined`, so
a template written from the documentation raises
`UndefinedError: 'squads._views.ViewGroup object' has no attribute 'count'`. Driven through
`sq workflow view` with an override template containing `{{ group.count }}`.

`count` exists only in `projection_json` (`src/squads/_views.py:296`). A `--json` client sees
`{key, count, records}`; a template sees `{key, records}` and has to write `group.records | length`,
which both bundled templates do — which is why nobody noticed.

Add `count` as a property on `ViewGroup` rather than correcting the doc line: it closes the gap for
every adopter template, and `projection_json` should then read the property instead of recomputing
`len(g.records)`, so the two can never drift.

Done when: `group.count` renders in a template, matches the `--json` value for the same projection,
and the docs line is true as written.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Roll-up separates settled-not-delivered from outstanding

<!-- sq:subtask:ST4:body -->
Make the roll-up able to answer "what is left" with zero. Today it cannot.

The template splits members on `group.key == "done"` with a bare `else`
(`src/squads/_rendering/templates/views/milestone_rollup.md.j2:5`) — a two-way split over a
multi-valued axis, where `else` is doing the work of "not delivered" and silently absorbing "not work
any more". `sq workflow roles` declares `settled = yes` for `done`, `in_force`, `retired` and
`superseded`, so every settled-but-not-delivered member is filed as Outstanding permanently.

Driven, a milestone with FEAT-10 Done, TASK-11 Draft, BUG-12 Cancelled, ADR-13 Accepted:

```
## Delivered (1)

- **FEAT-10** (feature) Done — Alpha feature
## Outstanding (3)

- **BUG-12** (bug) Cancelled — Gamma bug
- **ADR-13** (decision) Accepted — Delta decision
- **TASK-11** (task) Draft — Beta task
```

A Cancelled bug (`retired`) delivered nothing and is not outstanding either — it is gone. An Accepted
decision (`in_force`) is terminal and, if it was aimed at this milestone, delivered.

**The payload is the real gap.** `status_role` is projected as a plain text cell (`type: "text"`), so
the `settled` / `live` flags the `[roles]` catalog declares do not travel with it, and the template
cannot do better on its own. Carry the role's declared properties in the projection: that is the
spec-driven answer, it matches the mechanism's own contract that field metadata travels with the
payload, and it gives every other client the same axis without a second `sq workflow roles` call. The
alternative — a third bucket in the template enumerating the settled-not-done roles by name — hardcodes
vocabulary into presentation and is the wrong shape here.

Whatever the bucket names end up being, resolve them off declared role properties, never a literal
status name: members span types and lifecycles, which is exactly why the view groups on `status_role`
rather than `status` in the first place.

Also in this file: the non-empty branch emits no blank line between the last list item and the
following `## Outstanding` heading, where the empty branch does (`_(none yet)_` is followed by one).
Cosmetic under CommonMark, inconsistent within one template — fix it while you are here.

Done when: a milestone whose remaining members are all settled reports zero outstanding, the
`--json` payload carries the role properties the template reads, and no literal status name appears
in the template.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Resolve the two unreachable bundled view templates

<!-- sq:subtask:ST5:body -->
Resolve the two view templates that ship in the wheel but that no bundled declaration can reach.

`src/squads/_rendering/templates/views/finding_summary.md.j2` and `finding_summary_line.md.j2` ship
as package data and are listed in `src/squads/_rendering/templates_manifest.json:285-286`, but no
bundled `[views]` entry names either. The bundled spec's own section comment says so plainly —
`milestone_rollup` is the one bundled view — and a fresh squad's `sq workflow views` lists exactly
one row.

They are reachable only if an adopter happens to declare a view with one of those two exact names,
which is what the test suite does (`tests/service/test_view_resolve_and_render.py:69,92-95`,
`tests/cli/test_workflow_views_cli.py:75`). Production package data exists to give the test suite's
own override-declared views something to render.

Two consequences worth closing:

- `sq override scaffold views/finding_summary.md.j2` succeeds on any squad, offering an adopter a
  template for a view their spec does not declare and the docs never mention.
- FEAT-693's acceptance line — at least one non-tabular presentation ships and is exercised — is
  satisfied by a template that ships but that nothing shipped can reach.

Decide one way or the other and make the tree say it: either declare the two views for real in the
bundled spec (which then owes them an attachment or a documented freestanding role, and couples every
project that shadows `finding`'s optional `severity` field), or move the templates under the test
fixtures where their consumers already live. Weigh it against the acceptance line, which is the
reason one of them is in the wheel at all.

Whichever way it goes, correct the false statement in
`tests/unit/test_view_expresses_the_subentity_summary_shape.py:11-13`, which asserts as fact that the
two views ship bundled. The cited file declares them as test fixtures. The docstring should say
templates, not views.

If the templates move, the manifest moves with them: regenerate it, confirm the freshness check
passes, and confirm only the `0.14.0` entry changed while `pyproject.toml` still reads `0.14.0`.

Done when: nothing in the wheel is unreachable from a bundled declaration, the docstring is true, and
the manifest is consistent with the tree.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Show a milestone's target date on its panel

<!-- sq:subtask:ST6:body -->
Show a milestone's target date on a human surface.

`target_date` is settable, validated, normalised and stored, but rendered nowhere a person reads.
`sq milestone <n> show` displays id / title / status / author / file; only `--json` carries it, under
`extra`. The coercion itself is good work — `_coerce_date` (`src/squads/_models/_metadata.py:91-99`)
rejects both a non-date and an out-of-range date, names the key in the refusal, and normalises to ISO.

This is consistent with existing behaviour and not a regression: no `extra_fields` value is rendered
on `show` today — `review`'s `target_ref` and `guide`'s `tags` / `tech` are equally invisible, and
nothing in `src/squads/_cli/_common.py` reads `it.extra` for the panel. It is worth closing anyway
because a milestone's target date is the type's one distinguishing attribute — the type is a named
target for a set of work *with a target date*, per FEAT-693's own acceptance line — and
`docs/workflow.md` teaches setting it two lines after introducing the type. A field the docs teach
and the panel hides is a small trap.

Prefer the generic fix: render a type's declared `extra_fields` on the panel, which closes it for
`review` and `guide` at the same time and needs no per-type code. If the generic version turns out to
need a display vocabulary the spec does not yet carry (labels, ordering, formatting per field), say so
and fall back to the milestone panel as a one-off rather than inventing spec vocabulary inside this
subtask — that would be an architect question, not a patch.

Note the file collision: the panel lives in `src/squads/_cli/_common.py`, which the render-seam task
also edits. Sequence behind it.

Done when: `sq milestone <n> show` displays the target date when one is set and omits the line when
none is, and whichever scope was chosen — generic or one-off — is recorded with its reason.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T18:21:34Z] Elias Python:
  - F5 shape: two new generic base view fields, settled (role_for(status).settled) and delivered. delivered means the record's own kind reached its declared lifecycle's happy-path settled terminal - WorkflowSpec.first_settled_status, generalized to also resolve a sub-entity kind's own lifecycle (not just an item type), so a custom lifecycle gets a correct answer purely from its own declared spine + role.settled, no literal status name anywhere. milestone_rollup's template now buckets on record-level delivered/settled into Delivered / Outstanding / Settled without delivering; group_by stays status_role, unaffected.
  - F2/F3: _sort_key now threads the record's own kind + the active spec. id sorts on number_for_id with a prefix tie-break (a shared number can never really happen - SquadsDB.items is dict[int, Item] - but the tie-break is recorded and unit-tested as a defensive contract). A badge field on an ordered collection sorts by declared position; unordered/unrecognised falls back to code, same graceful-degrade as ItemFilter._meets_min.
  - F8: ViewGroup.count is now a property; projection_json reads it too, so template and --json can't drift.
  - F10: moved finding_summary/finding_summary_line out of the wheel entirely (deleted, not declared for real) - declaring them bundled would couple every project to finding's optional severity field, which the finding itself flagged as the wrong trade. Their two consuming test modules now write a stand-in template as a project override; corrected the false 'ships bundled' docstring claim; the override-wins-over-bundled test now targets milestone_rollup, the one view that actually is bundled.
  - F14: milestone-specific one-off on the panel + --raw dossier (target_date only). Did NOT build the generic extra_fields-on-panel renderer: it would need per-field display vocabulary (label, ordering/formatting) that ItemSpec.extra_fields (a bare list[str]) doesn't carry - flagging this as an architect question rather than inventing spec vocabulary inline, per the brief.
  - Manifest: milestone_rollup.md.j2 (F5 content) and workflow.toml (new settled/delivered fields, updated milestone_rollup view) changed hashes; finding_summary/finding_summary_line entries dropped. Regenerated - only the 0.14.0 manifest entry moved, pyproject.toml still 0.14.0, verified via git diff. Golden tests/goldens/workflow_views.json updated (2 new field rows).
  - Driven on a real squad: a milestone with a Done task, a Draft task and a Cancelled bug reports Delivered (1) / Outstanding (1) / Settled without delivering (1) - Outstanding never counts the cancelled bug. target date shows on sq milestone show. order_by on priority now returns urgent, high, medium, low.
  - Gates: pyright/ruff/ruff format clean. sq check clean. tests/meta: 255 passed, 5 failed - all five trace to 4 orphaned content-store blobs left by the template/spec content changes (the two dropped templates' blobs, the old workflow.toml hash); per the brief this residue is not mine to clear (no bump_version.py, no seed_content_store.py --rebuild run). Targeted suite (view engine, milestone, workflow-views CLI, override-render, badge/status/workflow spec, json-shape goldens): 247 passed.
  - @reviewer F2, F3, F5, F8, F10, F14 marked Fixed on REV-840 with per-finding notes. @architect flagging the extra_fields display-vocabulary question from F14 - want a ruling before any dev tries the generic renderer.
<!-- sq:discussion:end -->
