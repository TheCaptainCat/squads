---
id: FEAT-694
sequence_id: 694
type: feature
title: Retire the sub-entity summary and head as computed views
status: Ready
author: product-owner
refs:
- FEAT-693:depends-on
- MILE-836:targets
description: Retire the materialized sub-entity summary and head regions (and the
  role Skills section) and reissue all three as computed derived views
subentities:
- local_id: US1
  title: Retire the sub-entity summary as a computed view
  status: Todo
- local_id: US2
  title: Retire the head badge line as a computed view
  status: Todo
- local_id: US3
  title: Retire the role Skills section and extra.skills cache
  status: Todo
- local_id: US4
  title: Migrate the corpus to remove the retired regions
  status: Todo
created_at: '2026-07-29T13:52:49Z'
updated_at: '2026-09-01T08:09:47Z'
---
<!-- sq:body -->
## The problem

The sub-entity roll-up summary and the head badge line are both materialized regions: text
written into a marker-delimited body region and left there until the next mutation re-renders it.
Nothing reads either region except a person or an agent opening the raw file — every computed
surface (the `show` table, the pane title, the kind meta line, the `--raw` badge line) already
derives its own rendering from frontmatter and never looks at the stored text. The head is worse
than merely redundant: it resolves an assignee's display name and a parent story's title from
*other* files, so renaming either leaves the stored region wrong with no verb that heals it, and
`sq check` reports nothing. A merge across two branches can also leave the frontmatter correct and
the region silently disagreeing with it, and no command re-derives it from the resolved state.

The derived-view mechanism this work rides now ships: `[views]` is a declared workflow-spec
section (source/projection/presentation), `_views.py` resolves and projects it, and `sq workflow
views` / `sq workflow view <name> <id>` reads one. A `subentity`-kind source already exists and
already projects exactly the summary's own shape — one record per member of a parent's declared
sub-entity collection, base fields resolved off the record itself (`id`, `status`, `assignee`,
`title`, `story`) plus any field the kind declares. `milestone_rollup` ships as the one bundled
view and is the worked precedent for attaching a view to a type via `items.<type>.views`, so an
adopter's `[selected]` deselect takes the view with it for free.

These two regions are not an example of the pattern — they are the two places it was proven to
fail as a materialized output, and the mechanism proven to replace it now exists.

## Shape

Both regions retire. Neither is converted onto a declared body sink — there is no such sink, and
none is being added. The summary becomes a declared derived view: a `subentity`-source projection
over the parent's own sub-entity collection, following the `milestone_rollup` pattern (one
`[views.<name>]` entry per hosting sub-entity kind, attached via `items.<type>.views`), presented
through the existing `subentities/summary.md.j2` template. The head is computed the same way on
every read instead of written once and left to go stale, resolving the assignee's display name and
the mapped story's title exactly as the retired `_refresh_head` did, through
`subentities/head.md.j2`. The bespoke assembly code (`ensure_summary`, `set_head`, `_refresh_head`
and the refresh-on-mutation obligation they impose on every sub-entity write) is deleted, not left
in place beside the general mechanism.

The column derivation and badge resolution that already exist stay: they become the projection
logic and the bundled presentation templates behind the views, the same two templates
(`subentities/summary.md.j2`, `subentities/head.md.j2`) reused rather than replaced.

**A third region retires with them, in the same change.** A role's `## Skills` section in the
rendered role body is a materialized projection over other items' `scopes` edges — foreign-sourced
in exactly the same way the head is — and it goes computed too, as one more row in `sq role
<slug> show`'s existing computed card (beside the `creates:` row it already prints), resolved
through the existing skill-resolution helper. `role.md.j2` loses its `## Skills` block. The stored
`extra.skills` cache that mirrors this into frontmatter is retired with it — it is a cache of a
value that costs nothing to recompute (the roster is small), and it is the only field carrying a
dedicated skew-guard exemption to allow it to be written outside the normal transaction path. This
consumer belongs here, not with any other 0.14 work: the pointer's own resolved skills list is a
different value — the preload set a backend materializes into an agent's `.claude/` pointer file,
which stays materialized because a host consumes it at spawn — and that value is untouched by this
feature. What retires here is the role *item's own rendered body section*, which has no
host-consumption reason to stay written down: the generated pointer no longer names a local file
path an agent reads directly, so an agent's route to a role's or skill's content already runs
through `sq`, which is what makes computing it possible in the first place.

**Nothing about what the computed renderings show changes.** Anyone running `sq task N show`,
`sq role <slug> show`, or any of the other three computed renderers of the sub-entity projection
sees exactly the same output before and after this feature, because none of them ever read the
regions this feature removes.

**A migration is owed, and rides the shared 0.11 → 0.14 runner already in the tree
(`_v0_11_to_v0_14.py`).** That runner already carries the milestone and contract types into the
schema bump; this feature is its third claimant, extending the same deterministic step and the
same manual entry rather than authoring a second runner or a second schema bump. It strips the
`sq:summary` and `sq:<kind>:<id>:head` marker regions (and the role body's `## Skills` block) from
every existing file, leaving every other byte — including the authored `:body` and `:discussion`
regions inside each sub-entity block — untouched. The runner's own frozen-literal discipline
applies here too: no vocabulary-folded primitive is imported from `_models` (the standing
`tests/meta` guard covers this).

## Acceptance

- The four computed renderings of the sub-entity projection that ship today (the `show` summary
  table, the pane title under `show --full`, the meta line under `sq <kind> show`, and the
  `--raw` dossier badge line) are byte-identical before and after this change.
- `sq role <slug> show`'s computed card gains a skills row that is byte-identical to what the
  role body's `## Skills` section rendered before this change.
- The `sq:summary` and `sq:<kind>:<id>:head` marker regions are absent from every item file after
  migration, and the role body's `## Skills` block is absent from every role file after migration.
  No authored `:body` or `:discussion` content moves or changes.
- Refresh-on-mutation is gone as an obligation: `ensure_summary`, `set_head` and `_refresh_head`
  are deleted, and no sub-entity write path calls anything in their place, because there is
  nothing left to refresh.
- `extra.skills` is deleted as a stored field; `PERMITTED_EXTRA_SKEW` narrows to drop it, and the
  test pinning that frozenset's exact membership is updated in the same change with a docstring
  explaining the narrowing.
- The migration step is written as an extension of `_v0_11_to_v0_14.migrate()`, covers the whole
  corpus (existing item files' summary/head regions and existing role files' skills block), and
  ships behind the same registry entry as the milestone and contract halves — no second
  schema-version call, no second runner.
- Marker-safe editing stays intact throughout: the migration touches only the regions it is
  chartered to remove, never an authored region, and `sq check` is clean on a migrated corpus.

## Consequences worth stating up front

- `sq search` narrows: it currently matches sub-entity status, assignee and story text because
  those values sit as text inside the two regions it scans. After removal, a search matches a
  sub-entity block's heading/title but not its derived fields. The existing per-kind list and its
  `--json` output are the replacement for that kind of lookup; this feature does not attempt to
  claw the matched text back into search.
- A raw file opened directly (a person resolving a merge conflict, or reading on a forge) no
  longer shows the roll-up or the badge line inline. That capability is what this feature removes,
  by design — a computed value cannot silently disagree with the state it is computed from, and a
  materialized one already has, twice, without any verb catching it.
- `role.md.j2` loses its `## Skills` block, and the item templates carrying a `:summary` region
  lose it too — a bundled-template edit, which places this behind the release's stated ordering:
  the version bump before any template-manifest regeneration.

## Risk

This touches load-bearing rendering with a migration behind it. The bar is not "the new mechanism
looks right" — it is that the enumerated computed renderings produce the exact same bytes they did
before, and that the migration leaves every authored byte in the corpus untouched. A rendering
mismatch found here is a defect in the projection/presentation split, not a reason to keep either
region materialized to paper over it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 694 add-story "As a <role>, I want … so that …"`; track with `sq feature 694 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Retire the sub-entity summary as a computed view |
| US2 | Todo |  | Retire the head badge line as a computed view |
| US3 | Todo |  | Retire the role Skills section and extra.skills cache |
| US4 | Todo |  | Migrate the corpus to remove the retired regions |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Retire the sub-entity summary as a computed view

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
The sub-entity roll-up summary retires from the body and becomes a declared derived view, on the
mechanism `_views.py` and `[views]` already ship: a `subentity`-source projection over the
parent's own sub-entity collection, following the shape `milestone_rollup` already demonstrates
(one `[views.<name>]` entry, attached to its hosting type(s) via `items.<type>.views` so a
`[selected]` deselect takes the view with it). One entry per hosting sub-entity kind
(subtask/story/finding, or whatever a project's own spec declares), each presented through the
existing `subentities/summary.md.j2` template.

The `subentity` source kind already resolves exactly this region's data: one record per member,
carrying the local id, the declared per-kind fields, status, assignee and (for a kind that maps a
parent story) the story's *local id* — never a resolved label. That is the correct shape: the
retired region was itself local, storing the assignee's slug and the story's id rather than their
resolved names (`| ST1 | Todo | architect | Do the thing | US1 |`). No new field-resolution
capability is needed for this story; declaring the view(s) and wiring the presentation is the
whole of the work.

`ensure_summary` and the refresh-on-mutation call it imposes on every sub-entity write are
deleted. The four computed renderings that already derive their own view of this data (the `show`
table, the pane title, the kind meta line, the `--raw` badge line) are unaffected — none of them
ever read the materialized region — and each stays byte-identical after the change; whether they
end up sharing the new view's projection internally or keep their own existing derivation
(`summary_columns`/`summary_row`) is an implementation choice for the breakdown, not a behavior
change either way. The `sq:summary` marker region is removed from every item file in the corpus by
the migration in the sibling story, not authored back in a different form.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Retire the head badge line as a computed view

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The head badge line retires from the body and is computed on every read instead of written once
and left to go stale, resolving the assignee's display name and the mapped story's title the same
way the old `_refresh_head` did. The badge resolution logic it used
(`status_badge`/`badge_render`/`resolve_collection`/`field_label`) stays and becomes the
projection's field resolution, and `subentities/head.md.j2` stays as the bundled presentation
template. `set_head` and `_refresh_head` are deleted. The `sq:<kind>:<id>:head` marker region is
removed from every item file by the migration in the sibling story.

**Flagged for the breakdown, not resolved here.** The shipped `subentity` source projects one
record per *whole collection*, and its base fields resolve off the sub-entity's own record —
`assignee` is the stored slug, `story` is the mapped story's local id, neither a foreign lookup
(see `VIEW_BASE_FIELDS_BY_SOURCE`/`_record_from_subentity` in `_views.py`). The head needs two
things the mechanism doesn't yet do anywhere: resolve a *single* named sub-entity rather than its
whole collection, and follow two foreign hops off that record — the assignee's display name
through the ROLE item, and the mapped story's title through the parent's own *story*-kind
sub-entities. Whether that lands as a genuinely declared `[views]` entry with a widened field
vocabulary, or as a dedicated computed renderer that reuses the same badge-resolution helpers
without going through `[views]` at all, is an open implementation question the tech lead should
settle before assigning this story — either way the observable requirement is the same: no stored
region, resolved fresh on every read, byte-identical to what `_refresh_head` used to write.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Retire the role Skills section and extra.skills cache

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
A role's `## Skills` section retires from the rendered role body and becomes one more computed
row in `sq role <slug> show`'s existing card, beside the `creates:` row it already prints,
resolved through the existing skill-resolution helper on read with no new I/O. `role.md.j2` loses
its `## Skills` block. The stored `extra.skills` cache is deleted along with the save-and-restore
write path that maintained it outside the normal transaction boundary. `PERMITTED_EXTRA_SKEW`
narrows to drop the skills exemption, and the test pinning its exact membership is updated in the
same change with a docstring stating the narrowing is intended. This is the role-side counterpart
to the item-side stories in this feature, not a separate concern: same retirement of a
materialized, foreign-sourced region for the same reason.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Migrate the corpus to remove the retired regions

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
A migration step strips the `sq:summary` and `sq:<kind>:<id>:head` marker regions from every
existing item file and the `## Skills` block from every existing role file, leaving every other
byte untouched — including the authored `:body` and `:discussion` regions inside each sub-entity
block, and the rest of each role body.

This does not author a new runner. `_migrations/_v0_11_to_v0_14.py` already ships, carrying the
milestone and contract types into schema 0.14 under one registry entry (`SCHEMA_VERSION` already
bumped to `"0.14"`); this feature is that runner's third claimant, exactly as its own docstring
and the tracking task's body already record. Add this region-strip as one more deterministic step
inside `migrate()`, and one more section of the shared `MANUAL` runbook — no second
`from_schema`/`to_schema` pair, no second registry entry. The runner's existing discipline applies
unchanged: no vocabulary-folded primitive imported from `_models` (`tests/meta`'s
`test_migrations_never_import_a_vocabulary_folded_primitive.py` covers this already and needs no
new carve-out), and every value the step acts on (folder, prefix, marker tags) read from the
active spec at call time.

`sq check` and `sq repair` are clean on a migrated corpus, and a dry run against this repository's
own corpus — which still carries both regions today — is part of proving the step before it ships.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T14:22:17Z] Pierre Chat:
  - Parked with FEAT-693; both land in 0.14.
- [2026-08-24T20:15:55Z] Pierre Chat:
  - Rides 0.14: the region-strip migration folds into the same runner as the PRD and MILE types, so the release does not cut until this lands.
- [2026-09-01T07:41:27Z] Nina Product:
  - Refreshed against ADR-776 (incl. amendments) and what's since shipped — the `[views]` mechanism,
    `_views.py`, milestone_rollup as the bundled precedent, and the shared 0.11->0.14 migration runner
    (`_v0_11_to_v0_14.py`, TASK-813, already carrying the milestone/contract types).
    
    - Feature body: grounded the shape in the concrete mechanism (subentity source kind, `[views]`
      section, `milestone_rollup` pattern) instead of describing a mechanism not yet built. No change
      to the problem/acceptance framing — ADR-776 SS6's inversion (retire, don't convert onto a sink)
      was already reflected correctly.
    - US1 (summary): confirmed fully buildable on the shipped `subentity` source as-is — its base
      fields already resolve slug/local-id, matching the retired region's own local shape. No gap.
    - US2 (head): flagged a real gap rather than silently designing around it. The shipped mechanism
      resolves a whole sub-entity collection with base-record fields only; the head needs single-record
      addressing plus two foreign hops (assignee display name via the ROLE item, mapped story title via
      a sibling sub-entity) that nothing in `_views.py` does today. Left as an open implementation
      question for the tech lead rather than picking `[views]` vs. a dedicated renderer myself.
    - US3 (role Skills / extra.skills): unchanged in substance -- confirmed still unbuilt and still
      this feature's; nothing shipped since touches it.
    - US4 (migration): named the actual runner it extends (`_v0_11_to_v0_14.py`, one registry entry,
      third claimant per TASK-813) instead of describing a migration in the abstract.
    
    No reauthor needed -- ADR-776's ruling already inverted this feature once; what changed here is
    grounding it in code that has since landed, not a further inversion of any story's subject.
    
    Left Draft, not promoted. @tech-lead for breakdown once ready -- US2 in particular needs an
    architecture call before it can be scoped into a task.
- [2026-09-01T07:51:44Z] Robert Architect:
  - - US2 ruled, and it is neither option: **the head has no successor to build**. ADR-776 amended in place (2026-09-01 note). No `[views]` widening, no bespoke renderer — the region and its refresh-on-mutation write path retire and nothing replaces them.
    - Why: `_subentity_badge_line` is already the head, computed, and already ships — driven, `sq review 11 show --full`'s pane title is `=== F1 — Something wrong  🔴 Open  🔴 Critical  architect ===`, same badges, same fields. The only delta is the two foreign hops, and those are the defect ADR-776 §5 retires the region for ("read by nothing"), not a capability to carry forward. Building a successor for them means building a rendering with no reader, since US4 removes the region's one reader.
    - §6 **narrows**: one projection is reissued as a declared view (the roll-up), not two. Its other clauses — subject inversion, acceptance bar, owed migration — stand.
    - Widening refused on cost, not taste: cross-item resolution makes a field code no longer answerable from the declaration, reopens the 2026-08-26 amendment's one-absence contract (a dangling join would render `null` like an unset value), and has nothing in the catalog for the load-time refusal to check. An adopter could only use it via a declared join grammar; the narrow `assignee_name` version is a bespoke renderer wearing a declaration.
    - **US1 unaffected in substance** — the `subentity` source resolves the roll-up exactly. One correction: US1 says sharing the projection with the shipped renderings is "not a behavior change either way"; driven, it is one direction — a badge field projects emoji+**label** (`🔴 Critical`), `summary_row` renders emoji+**code** (`🔴 critical`). Sharing it changes the summary table's bytes, which acceptance clause 1 forbids.
    - Two more for the breakdown: (a) `set_head` cannot literally be deleted — `_migrations/_v0_2_to_v0_3.py` calls it, so it and `subentities/head.md.j2` stay reachable as migration-only machinery; (b) separately from the head, no view can render a **status** badge at all — `status` is a base attribute typed `text`, so a status column is the bare name. Deliberate (`status_role` is the styling axis), but worth knowing before anyone scopes byte-identity against a view.
    - @tech-lead US2 is unblocked and is now a deletion story, not a build story. @product-owner FYI on the US1 wording and the `set_head` acceptance clause.
- [2026-09-01T08:09:47Z] Olivia Lead:
  - Broken down against ADR-776's 2026-09-01 amendment, not the older text. Three tasks, all Ready:
    TASK-847 (US1+US2, one surface), TASK-848 (US3), TASK-849 (US4). Feature moved to Ready.
    
    Calls made in the breakdown, all recorded in the task bodies:
    
    - **US1+US2 are one task.** Same files: one write sequence in `_services/_subentities.py`, the same
      two templates, the same manifest regeneration. Splitting them would put two devs in one file.
    - **The head is a deletion with no successor**, per the amendment. Nothing is built in its place;
      `_subentity_badge_line` already ships and is frozen by acceptance clause 1.
    - **The badge label/code conflict resolves by not sharing.** Verified: `_views.py::_badge_cell`
      renders emoji+label, `_discussion.summary_row` renders emoji+code (`badge_render`'s default).
      The five shipped renderings keep `summary_columns`/`summary_row` untouched; the declared views
      project through `_views.py`. The divergence is documented at both ends rather than reconciled —
      reconciling moves the frozen bytes.
    - **The roll-up views are declared freestanding, not attached to `items.<type>.views`.**
      `_print_item_content` already renders the built-in summary table for any item with sub-entities
      and then renders every attached view, so attaching would print the same table twice on
      `sq feature|task|review <n> show`. Freestanding still buys both things §4 names: an override
      template at `templates/views/<name>.md.j2` and a `selected.views` drop (`views` is in
      `WORKFLOW_TOP_LEVEL_SECTIONS`, which doubles as `[selected]`'s accepted section set). US1's
      parenthetical repeats the milestone mechanic; the milestone had no competing built-in table.
      @architect @product-owner — if you want the attached form with the built-in table removed, that
      is a different acceptance bar (it moves the frozen `show` bytes) and needs a ruling first.
    
    Two corrections found while verifying, beyond the ones the architect flagged:
    
    - **`ensure_summary` is pinned too**, not just `set_head`: `_migrations/_v0_1_to_v0_2.py` calls it
      twice. So `set_head`, `ensure_summary`, `render_summary` and both `subentities/` templates all
      stay as migration-only machinery. Scoped that way in TASK-847 ST4.
    - **US3's "byte-identical" acceptance clause is not literally achievable.** The body rendered a
      heading + preamble + bullet list; a card row is one line. Restated as: the resolved list has the
      same membership and order. TASK-848 ST1.
    
    US4 landed as its own task under this feature rather than a subtask of TASK-813: the work maps to
    US4, and TASK-813 is parented to FEAT-693 whose stories it cannot map to. TASK-849 extends
    `_v0_11_to_v0_14.py` and its single registry entry — no second runner, no second bump, no new
    corpus fixture. TASK-813 now carries `depends-on TASK-849` so the board shows it cannot close
    first.
<!-- sq:discussion:end -->
