---
id: FEAT-694
sequence_id: 694
type: feature
title: Retire the sub-entity summary and head as computed views
status: Draft
author: product-owner
refs:
- FEAT-693:depends-on
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
updated_at: '2026-08-24T20:15:55Z'
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

Once derived views exist as a mechanism, these two regions are not an example of the pattern —
they are the two places the pattern was proven to fail as a materialized output.

## Shape

Both regions retire. Each becomes a declared derived view, computed on every read and never
written to a body: the summary as a table projection over the parent's sub-entity collection, the
head as a single-record projection over one sub-entity. The bespoke assembly code
(`ensure_summary`, `set_head`, `_refresh_head` and the refresh-on-mutation obligation they impose
on every sub-entity write) is deleted, not left in place beside the general mechanism.

The column derivation and badge resolution that already exist stay: they become the projection
logic and the bundled presentation templates behind the two declared views, the same two
templates (`subentities/summary.md.j2`, `subentities/head.md.j2`) reused rather than replaced.

**A third region retires with them, in the same change.** A role's `## Skills` section in the
rendered role body is a materialized projection over other items' `scopes` edges — foreign-sourced
in exactly the same way the head is — and it goes computed too, as one more row in `sq role
<slug> show`'s existing computed card (beside the `creates:` row it already prints), resolved
through the existing skill-resolution helper. `role.md.j2` loses its `## Skills` block. The stored
`extra.skills` cache that mirrors this into frontmatter is retired with it — it is a cache of a
value that costs nothing to recompute (the roster is small), and it is the only field carrying a
dedicated skew-guard exemption to allow it to be written outside the normal transaction path. This
consumer belongs here, not in the pointer-decision feature: the pointer's own resolved skills list
is a different value — the preload set a backend materializes into an agent's `.claude/`
pointer file, which stays materialized because a host consumes it at spawn — and that value is
untouched by this feature. What retires here is the role *item's own rendered body section*, which
has no host-consumption reason to stay written down.

**Nothing about what the computed renderings show changes.** Anyone running `sq task N show`,
`sq role <slug> show`, or any of the other three computed renderers of the sub-entity projection
sees exactly the same output before and after this feature, because none of them ever read the
regions this feature removes.

**A migration is owed, and is part of this feature's scope.** The two regions are on-disk format,
present across the whole corpus of existing item and role files. A migration runner strips the
`sq:summary` and `sq:<kind>:<id>:head` marker regions (and the role body's `## Skills` block) from
every existing file, leaving every other byte — including the authored `:body` and `:discussion`
regions inside each sub-entity block — untouched. This rides the same schema bump and migration
runner as the `MILE-`/`targets` change, per the note both features already carry.

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
- The migration runner is written, covers the whole corpus (existing item files' summary/head
  regions and existing role files' skills block), and ships as part of the schema bump shared
  with FEAT-693 — the schema-version call for that bump is made once, deliberately, for both
  features together.
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
The sub-entity roll-up summary becomes a declared derived view: a table projection over the
parent's own sub-entity collection, presented through the existing `subentities/summary.md.j2`
template. `ensure_summary` and the refresh-on-mutation call it imposes on every sub-entity write
are deleted. The four computed renderings that already derive their own view of this data (the
`show` table, the pane title, the kind meta line, the `--raw` badge line) are unaffected — none of
them ever read the materialized region — and each stays byte-identical after the change. The
`sq:summary` marker region is removed from every item file in the corpus by the migration in the
sibling story, not authored back in a different form.
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
The head badge line becomes a declared derived view: a single-record projection over one
sub-entity, resolving the assignee's display name and the mapped story's title the same way the
old `_refresh_head` did, but computed on every read instead of written once and left to go stale.
`set_head` and `_refresh_head` are deleted. The badge resolution logic they used
(`status_badge`/`badge_render`/`resolve_collection`/`field_label`) stays and becomes the
projection's field resolution, and `subentities/head.md.j2` stays as the view's bundled
presentation template. The `sq:<kind>:<id>:head` marker region is removed from every item file by
the migration in the sibling story.
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
A migration runner strips the `sq:summary` and `sq:<kind>:<id>:head` marker regions from every
existing item file and the `## Skills` block from every existing role file, leaving every other
byte untouched — including the authored `:body` and `:discussion` regions inside each sub-entity
block, and the rest of each role body. It rides the same schema bump and the same migration
runner as FEAT-693's `MILE-` type and `targets` ref kind: one schema-version call, one runner, for
both features' on-disk format changes together. `sq check` and `sq repair` are clean on a
migrated corpus, and a dry run against this repository's own corpus is part of proving the
runner before it ships.
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
<!-- sq:discussion:end -->
