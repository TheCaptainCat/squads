---
id: TASK-729
sequence_id: 729
type: task
title: Make mine/workload/inbox and show --json sub-entity-aware
status: Done
parent: FEAT-642
author: tech-lead
refs:
- BUG-727:fixes
description: Route by sub-entity assignee and carry sub-entity discussion into JSON
subentities:
- local_id: ST1
  title: 'mine: surface items whose sub-entity is assigned to the slug'
  status: Done
  story: US1
- local_id: ST2
  title: 'workload: count sub-entity assignments per assignee'
  status: Done
  story: US2
- local_id: ST3
  title: 'inbox: attribute each hit to the region it matched'
  status: Done
  story: US3
- local_id: ST4
  title: 'show --json: discussion on every sub-entity entry'
  status: Done
  story: US4
- local_id: ST5
  title: 'sub-entity show --json: standalone machine-readable surface'
  status: Done
  story: US5
created_at: '2026-08-03T07:56:37Z'
updated_at: '2026-08-03T14:37:00Z'
---
<!-- sq:body -->
A sub-entity (story/subtask/finding) carries its own `assignee` and its own discussion, but the
read surfaces treat it as second-class: the work-queue views filter on `item.assignee` only, and
the machine-readable item payload drops sub-entity discussion. An actor who owns a subtask and not
its parent is routed nothing, and a JSON consumer cannot see a decision recorded on a finding.

Close both halves across the Python read surfaces: assignment routing (`mine` — US1, `workload` —
US2), hit attribution (`inbox` — US3), and the sub-entity JSON payload (item-level — US4,
standalone — US5).

## Established behaviour — verified, do not re-derive

Reproduced against a seeded squad with one task, one subtask `ST1` assigned to `manager`, and one
`@manager` comment on `ST1`'s discussion:

- `sq mine manager --json` returns `[]`. The subtask assignment is invisible.
  Site: `mine` in `src/squads/_cli/_main.py` calls `svc.list_items(assignee=slug)` — an item-level
  filter with no sub-entity scan. There is no `mine` service method at all today; the filtering
  lives in the CLI.
- `sq workload --json` reports a single `assignee: null` row (2 items). `manager` gets no row
  despite owning `ST1`. Site: `workload` in `src/squads/_services/_roster.py` buckets on
  `it.assignee` only.
- `sq inbox manager --json` **does** already return the hit — `inbox` in
  `src/squads/_services/_collab.py` reads the whole `.md` text and extracts mentions from it, so a
  mention inside a sub-entity discussion region is detected. What it cannot say is *where*: the hit
  is reported as a bare item-level entry (`{id, title, lines}`) with no locator naming `ST1`.
  The gap on this surface is attribution, not detection. Do not add assignee scanning here.
- `sq <type> <n> show --json` emits each `subentities` entry with
  `local_id/title/status/assignee/severity/story/extra/body/badges` and **no** `discussion`.
  Site: `build_item_json` in `src/squads/_cli/_common.py` fetches a full `SubentityDetail` per
  sub-entity via `svc.get_block`, and that object carries **both** `.body` and `.discussion`
  (`src/squads/_services/_results.py`) — only `.body` is copied onto the payload. A one-field
  omission in the builder, not new plumbing.
- `sq <type> <n> <kind> <k> show --json` exits 2 with `No such option: --json`. The dedicated
  sub-entity show verb (`_register_sub_verbs` in `src/squads/_cli/_items.py`) has no `--json` at
  all, so there is no machine-readable single-sub-entity surface at any level.
- `sq search --json` is **not** affected — it already surfaces sub-entity comment text with region
  `<kind>:<local_id>:discussion#<n>` and a snippet. Out of scope; change nothing there.
- The status-to-role catalog is **one table shared by items and sub-entity kinds** (`sq workflow
  statuses`), and `hidden_by_default` is purely role-derived — it takes an `item_type` argument and
  does not read it (`src/squads/_workflow/_models.py`). So the existing predicate already works at
  sub-entity granularity; there is nothing new to introduce. Worth knowing which way the roles fall
  for sub-entity states: `Todo` is `pending` (visible/open), `Done` is `done` (hidden), `Open` is
  `attention`, `Fixed` is `active` (**still open and visible**), `WontFix` is `retired` (hidden),
  `Verified` is `done` (hidden).

## Scope per surface

**`sq mine <slug>` (US1)** — surface an item when the slug owns the item **or** owns one of its
sub-entities. The `--json` payload is a homogeneous array of item objects and the shape contract is
additive-only, so a matched sub-entity cannot become an array element of its own: it goes on the
item object as a new key listing the sub-entities of that item assigned to the slug (`local_id`,
`title`, `status`, plus enough state to route the work). The parent therefore appears as the row —
a roll-up — and the human table must name which sub-entities matched rather than showing the item
alone, or the view is indistinguishable from a plain item assignment.

Default (non-`--all`) visibility follows **whichever assignment matched, evaluated independently per
matched entity**: an item-level match is judged on the item's own status, a sub-entity-level match on
that sub-entity's own status, and the row shows when at least one matching reason is open.
Concretely:

- Settled parent, open sub-entity assigned to the slug: **shows** (the slug still has open work).
- Open parent, the slug's assigned sub-entity settled, parent not itself assigned to the slug:
  **does not show** (the slug's piece is done; someone else's open parent is not their queue).
- Parent open *and* assigned to the slug: shows, exactly as today.
- `--all` bypasses the predicate, exactly as it does for item-level matches today.

Implement this by reusing `spec.hidden_by_default` at sub-entity granularity — pass the sub-entity's
kind and status. Do **not** build a parallel visibility concept: it is the same predicate applied to
a second entity, which is why the rule composes as "at least one open reason".

The matched-sub-entity key lists every sub-entity of that item assigned to the slug, each with its
status, regardless of which one satisfied the visibility predicate. The predicate governs whether
the **row** appears; it does not prune the reason list, so a consumer can always see the full set of
reasons the row is theirs.

**`sq workload` (US2)** — count sub-entity assignments per assignee, so an actor who owns only
sub-entities gets a row. These land as **separate additive columns/keys**, never folded into
`open`/`closed`/`total`: those keep meaning item counts exactly as published today. An actor owning
both a parent and one of its sub-entities is counted once in the item columns and once in the
sub-entity columns — merging them would double-count that actor and silently change the meaning of
an already-stable column. Same open/settled derivation as the item counts, resolved through the
spec rather than a status list; roster-category items stay excluded as they are today.

**`sq inbox <slug>` (US3)** — attribute each hit to the region it matched, so a consumer can tell an
item-level mention from a mention on a specific sub-entity. Additive to the existing
`{id, title, lines}` entry. `sq search`'s `<kind>:<local_id>:discussion#<n>` region string is the
established locator vocabulary in this codebase — reuse it rather than inventing a second spelling.
Attribution only: inbox stays mention-driven ("who was called out", not "who owns this"). An
assignment-queue inbox is a different view with its own spec and is out of scope — do not add
assignee scanning to this surface.

**`build_item_json` sub-entity `discussion` (US4)** — add an additive `discussion` array on each
`subentities` entry, mirroring the item-level shape (`{author, ts, body}`, same ordering, split with
the same helper). Generic across every sub-entity kind — sub-entity discussion is not per-kind.
Added unconditionally, preserving the existing invariant that `show --json` is byte-identical across
`--raw`/`--comments`/`--full`. US4's client-render half is tracked on the companion client task.

**`sq <type> <n> <kind> <k> show --json` (US5)** — a machine-readable single-sub-entity surface. It
must emit **exactly** the object shape a `subentities` entry carries in the item payload (including
the new `discussion`), from one shared construction path, so the two surfaces cannot drift into two
different sub-entity shapes. It is in scope here precisely because it is the same shape decision as
the item-level payload: settling it twice is how they diverge.

## Constraints

- **Additive only.** These `--json` shapes are a frozen Tier-3 contract (`docs/stability.md`):
  fields may be added, never removed, renamed or retyped. No envelope-wrapping an existing array, no
  changing an existing key's type or meaning.
- **Layering.** The sub-entity scan belongs in the service layer, not in the CLI command bodies
  (`_cli` depends on `_services`, never the reverse). `mine` currently filters in the CLI; give it a
  service method rather than growing the CLI function.
- **Spec-driven, not hardcoded.** Resolve the sub-entity kind via `spec.item_subentity_kind` and
  statuses via the spec's predicates. A custom kind on a custom type must work with no code change.
- **Escaping.** Wrap every dynamic string printed to the console or a table with `_cli._common.e()`.
- **Goldens.** `tests/cli/test_json_output_shape.py` pins each `--json` shape. Affected goldens:
  `mine_manager`, `workload`, `inbox_manager`, `feature_show`, `task_show`. Regenerate with
  `UPDATE_GOLDENS=1` per that module's docstring and commit the diff; add a golden entry for the new
  sub-entity `show --json`. Review each diff as a contract change — an unexpected key removal in a
  golden diff is a broken Tier-3 promise, not noise.
- **Naming.** No ticket or item IDs anywhere in source or test names — name tests by the behaviour
  they pin.
- Docs: `docs/stability.md`'s Tier-3 list and the `sq mine`/`inbox`/`workload` references in
  `docs/` describe these surfaces to adopters; update what the new fields make stale, in adopter
  terms only.

## Acceptance

Traceable to US1 through US5:

1. **US1** — an actor assigned only a sub-entity (parent assigned to someone else, or unassigned)
   sees that work in `sq mine <slug>`, in both the table and `--json`, with the matched sub-entity
   named.
2. **US1** — a settled parent with an open sub-entity assigned to the slug appears without `--all`;
   an open parent whose only match is a settled sub-entity does not; `--all` shows both.
3. **US2** — an actor assigned only sub-entities appears in `sq workload` with a non-zero count in
   the sub-entity columns, and `open`/`closed`/`total` still report item counts unchanged.
4. **US3** — a `sq inbox <slug>` hit on a mention inside a sub-entity discussion names the
   sub-entity region it matched; an item-level mention is distinguishable from it.
5. **US4** — every `subentities` entry in `sq show <id> --json` and `sq <type> <n> show --json`
   carries a `discussion` array with the sub-entity's comments in order, for every kind
   (story/subtask/finding), matching what the human render shows for the same sub-entity.
6. **US5** — `sq <type> <n> <kind> <k> show --json` exits 0 and emits the same object shape as that
   sub-entity's entry in the item payload; a nonexistent local id fails cleanly.
7. No existing key is removed, renamed or retyped on any `--json` surface; each affected golden
   diff is additive.
8. Operator slugs (`op-<slug>`) work identically to role slugs on every one of these surfaces —
   an operator can own a sub-entity.
9. Every behaviour above is pinned by a test at the service level and a CLI smoke test, exercised
   across at least two sub-entity kinds rather than subtasks alone. The visibility rule in
   acceptance 2 is table-driven over the parent-status, sub-entity-status and which-side-is-assigned
   combinations, not one example per direction.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 729 add-subtask "<title>"`; track with `sq task 729 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — mine: surface items whose sub-entity is assigned to the slug

<!-- sq:subtask:ST1:body -->
`sq mine <slug>` returns only items whose own `assignee` matches: the command calls
`svc.list_items(assignee=slug)` directly in the CLI, so an actor owning a subtask under someone
else's task sees nothing.

Give the view a service-level method that matches an item when the slug owns the item **or** owns
one of its sub-entities, and carry the matched sub-entities through to both renders. The `--json`
payload is a homogeneous array of item objects under an additive-only contract, so matched
sub-entities go on the item object as a new key — the item is the row (a roll-up), never a
sub-entity element in the same array. The table must name which sub-entities matched, otherwise a
roll-up row is indistinguishable from a direct item assignment.

Default visibility is per-match, not per-item: an item-level match is judged on the item's status, a
sub-entity match on that sub-entity's status, and the row shows when at least one matching reason is
open. Reuse `spec.hidden_by_default` at sub-entity granularity — it is purely role-derived and
already ignores its type argument, so no parallel visibility concept is needed. The full rule and its
two directional cases are in the parent task body.

Done when: an actor assigned only a sub-entity sees the parent item in the table and in `--json` with
the matched sub-entity named; a settled parent with the slug's open sub-entity still appears without
`--all` while an open parent whose only match is settled does not; operator slugs behave identically;
the `mine_manager` golden diff is additive.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-03T09:04:52Z] Elias Python:
  - Landed: mine now surfaces sub-entity-only assignments via Service.mine (visibility follows whichever match is open); mine --json carries additive matched_subentities. Table-driven visibility matrix + falsification in tests/service/test_subentity_aware_assignment_views.py. Golden mine_manager updated additively.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — workload: count sub-entity assignments per assignee

<!-- sq:subtask:ST2:body -->
`workload` buckets on `it.assignee` alone (`src/squads/_services/_roster.py`), so an actor who owns
only sub-entities gets no row at all — verified: a subtask assigned to `manager` leaves `manager`
absent from the table and `--json`.

Count sub-entity assignments per assignee so those actors appear, honouring the existing exclusions
(roster-category items stay out) and the same open/settled derivation the item counts use, resolved
through the spec rather than a status list.

These counts are **separate additive columns/keys**. `open`/`closed`/`total` keep meaning item counts
exactly as published today — folding sub-entities in would change the meaning of stable columns and
double-count an actor who owns both a parent and its sub-entity. That actor gets one count in the
item columns and one in the sub-entity columns, never merged.

Done when: an actor assigned only sub-entities appears with a non-zero sub-entity count; the existing
columns are unchanged for every actor; no key is removed, renamed or retyped; the `workload` golden
diff is additive.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-03T09:05:06Z] Elias Python:
  - Landed: Service.workload adds separate additive subentity_open/subentity_closed/subentity_total keys; existing open/closed/total untouched. An actor owning both a parent and its sub-entity is counted once in each set (falsified: folding them together broke the independence test).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — inbox: attribute each hit to the region it matched

<!-- sq:subtask:ST3:body -->
`inbox` already detects a mention placed inside a sub-entity discussion — it reads the whole `.md`
text and extracts mentions from all of it — but reports the hit as a bare item-level entry
(`{id, title, lines}`) with no locator, so a consumer cannot tell an item-level mention from one on
a specific sub-entity. Verified: an `@manager` comment on `ST1` surfaces as a plain `TASK-3` hit.

Attribute each hit to the region it matched, additively. `sq search --json` already publishes the
locator vocabulary for exactly this — `<kind>:<local_id>:discussion#<n>` — so reuse that spelling
instead of inventing a second one.

This surface is attribution only. Inbox stays mention-driven: it answers "who was called out", not
"who owns this". Do not add assignee scanning here — an assignment-queue inbox is a different view
with its own spec, out of scope.

Done when: a hit on a sub-entity mention names the sub-entity region; an item-level mention is
distinguishable from it; the `inbox_manager` golden diff is additive.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-03T09:05:15Z] Elias Python:
  - Landed: inbox attributes each hit to the region it matched, reusing search's <kind>:<local_id>:discussion#<n> locator; item-level hits keep region=null. Additive 'regions' key alongside the existing 'lines'. Falsified by nulling the region-detection branch; the new cross-kind attribution test went red.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — show --json: discussion on every sub-entity entry

<!-- sq:subtask:ST4:body -->
`build_item_json` (`src/squads/_cli/_common.py`) fetches a full `SubentityDetail` per sub-entity via
`svc.get_block` — that object carries both `.body` and `.discussion` — and copies only `.body` onto
the payload. So every `subentities` entry in `sq show <id> --json` and `sq <type> <n> show --json`
lacks a `discussion` key even though the data is already in hand and renders correctly for humans.
A one-field omission in the builder; no new plumbing.

Add an additive `discussion` array on each entry mirroring the item-level shape
(`{author, ts, body}`, same ordering, split with the same helper). Generic across every kind —
sub-entity discussion is not per-kind, so story, subtask and finding all gain it from one code path.
Add it unconditionally, preserving the invariant that `show --json` is byte-identical across
`--raw`/`--comments`/`--full`.

This project's convention puts decisions in discussions rather than bodies, so a JSON-driven
consumer is blind to every finding- and story-level decision until this lands.

Done when: every sub-entity entry carries its comments in order, matching the human render, across
at least story/subtask/finding; `feature_show` and `task_show` golden diffs are additive.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-08-03T09:05:25Z] Elias Python:
  - Landed: build_subentity_json (src/squads/_cli/_common.py) is the one shared shape-building function; build_item_json now calls it per sub-entity, adding an additive discussion array (author/ts/body, same order as the item-level one) generic across story/subtask/finding. Fixes BUG-727. Falsified by zeroing the discussion field; the discussion tests went red.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — sub-entity show --json: standalone machine-readable surface

<!-- sq:subtask:ST5:body -->
`sq <type> <n> <kind> <k> show --json` exits 2 with `No such option: --json` — the dedicated
sub-entity show verb (`_register_sub_verbs`, `src/squads/_cli/_items.py`) never got one, so there is
no machine-readable surface for a single sub-entity at any level.

Add `--json` to that verb, emitting **exactly** the object shape a `subentities` entry carries in
the item payload, including the new `discussion` key, built from one shared construction path used
by both sites. Two independently-built sub-entity shapes would drift; deciding the shape once is the
reason this belongs with the item-payload work rather than on its own.

Registration is spec-driven and generic over kinds, so the option must appear for every declared
sub-entity kind including a project's custom one, with no per-kind branch.

Done when: the command exits 0 and its payload is shape-identical to that sub-entity's entry in the
parent item's `show --json`; a golden pins it; a nonexistent local id still fails cleanly.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-08-03T09:05:33Z] Elias Python:
  - Landed: sq <type> <n> <kind> <k> show --json (generic, spec-driven, no per-kind branch) built from the same build_subentity_json path as ST4, so the two payloads cannot drift. A test asserts byte-for-byte equality against the item payload's matching subentities entry across story/subtask/finding; a nonexistent local id still fails cleanly (existing _find error).
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T07:59:47Z] Olivia Lead:
  - One task, five sub-entity-aware read surfaces: mine, workload, inbox attribution, sub-entity discussion in the item JSON payload, and a standalone sub-entity --json. Same owner, same shipping increment, and the sub-entity JSON shape must be decided once — hence one task, not five.
  - Three open design questions in the body (mine cross-status visibility, workload granularity, inbox semantics) need a product-owner ruling; the inbox premise in the parent feature is off — inbox already detects sub-entity mentions, it just cannot say which sub-entity. @product-owner
- [2026-08-03T08:10:14Z] Olivia Lead:
  - Subtasks mapped ST1-ST5 to US1-US5. The three rulings are folded into the body: mine visibility is now per-match with both directional cases spelled out (reusing spec.hidden_by_default at sub-entity granularity, not a new predicate), workload gets separate additive columns with the existing three unchanged, inbox stays attribution-only. The open-questions section is gone; acceptance is now numbered against US1-US5.
  - One residual the rulings did not cover, specified rather than left open: the matched-sub-entity key lists every sub-entity assigned to the slug with its status, even the settled ones — the visibility rule governs whether the row appears, not what the reason list contains. Say so if you read it the other way.
- [2026-08-03T09:06:07Z] Elias Python:
  - All five subtasks done, mapped 1:1 to US1-US5. Falsification per behaviour, table-driven visibility matrix (parent-status x sub-entity-status x which-side-assigned), goldens regenerated additively (mine_manager, workload, inbox_manager, feature_show, task_show, + new subtask_st1_show). Gates green: pyright/ruff/ruff-format/tests-meta. Leaving InProgress for your review.
- [2026-08-03T14:36:59Z] Catherine Manager:
  - Review approved (REV-734), all five subtasks Done, full suite green at 2950 passed. Closing on delegation: non-visual work, reviewed and independently verified.
<!-- sq:discussion:end -->
