---
id: FEAT-000027
sequence_id: 27
type: feature
title: Explicit ID padding with a raise-padding migration
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
refs:
- FEAT-000013
- FEAT-000019:depends-on
description: 'padding: 6 stored in the index; create errors when the counter would
  overflow it; a one-way repad command renames all files to the new width; ID parsing
  tolerant of any width since file contents are never rewritten'
subentities:
- local_id: US1
  title: As a squad owner whose counter hits the cap, I want create to fail with a
    clear index-full error naming the fix, so that the format never silently grows
    a digit
  status: Todo
- local_id: US2
  title: As a squad owner raising the padding, I want one command that renames every
    file to the new width and rebuilds the index, so that the squad stays uniform
    without hand-work
  status: Todo
- local_id: US3
  title: As a teammate whose items hold old-width refs and mentions, I want ID parsing
    tolerant of any padding, so that content written before the raise keeps resolving
    forever
  status: Todo
created_at: '2026-06-10T15:04:04Z'
updated_at: '2026-06-11T07:54:55Z'
---
<!-- sq:body -->
## Problem

IDs are formatted with a hard-coded 6-digit zero padding (`TASK-000007`). At sequence 1,000,000
the format silently breaks: IDs grow a digit, filenames stop sorting lexicographically, and every
assumption about the shape of an ID — in scripts, in golden files, in the contract we're about to
freeze — quietly becomes wrong. Nobody expects a squad to get there (this is a we-doubt-it-happens
feature), but 1.0's durable-format promise must state what happens at the boundary rather than
leave it as undefined behaviour.

## Value

The padding becomes an **explicit, owned part of the on-disk format**: stored, enforced, and
raisable through a sanctioned migration instead of overflowing into inconsistency. The squad's
files stay uniform-width forever, old references keep resolving forever, and the contract doc gets
a clean sentence instead of a shrug.

## Scope

- **`"padding": 6` stored in the index** (default for existing squads via migration/repair); ID
  formatting derives from it everywhere instead of a hard-coded `:06d`.
- **Exhaustion guard**: when the counter would exceed the padding's capacity (999999 at width 6),
  `sq create` raises a clear error — *the index is full; raise the padding with `sq …`* — rather
  than emitting a wider ID ad hoc.
- **Raise-padding command** (name per design; lives near `sq migrate`/`repair`): bumps the padding
  to 7 (or more) and performs the big rename — **every item file in the squad** is renamed to the
  new width, and the index is rebuilt accordingly. One-way: padding can only ever go up (lowering
  could collide and re-shrink is pointless).
- **Width-tolerant ID parsing**: file *contents* are deliberately never rewritten by the repad —
  refs, parent fields, prose mentions and frontmatter keep whatever width they were written with.
  Therefore everything that *reads* an ID (`split_ref`, resolvers, backref inversion, `sq check`)
  must treat `TASK-000007` and `TASK-0000007` as the same item — the number is the identity, the
  padding is presentation. This lands naturally in FEAT-000019's shared resolver. Display always
  uses the current padding.

## Acceptance

- The padding lives in the index, defaults to 6 for every existing squad, and drives all ID
  formatting (no hard-coded width remains).
- Creating past capacity fails with the index-full error naming the raise command; nothing wider
  than the configured padding is ever emitted.
- The raise command renames all item files to the new width, rebuilds the index, refuses to lower,
  and leaves file contents untouched; `sq check` is clean and every old-width ref still resolves
  afterwards (test on a fixture squad).
- ID parsing is width-tolerant everywhere, covered by tests (mixed-width refs resolve, backrefs
  invert, tree/show address correctly).
- The padding scheme and the exhaustion behaviour are documented in the stability contract
  (FEAT-000013).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 27 add-story "As a <role>, I want … so that …"`; track with `sq feature 27 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a squad owner whose counter hits the cap, I want create to fail with a clear index-full error naming the fix, so that the format never silently grows a digit |
| US2 | Todo |  | As a squad owner raising the padding, I want one command that renames every file to the new width and rebuilds the index, so that the squad stays uniform without hand-work |
| US3 | Todo |  | As a teammate whose items hold old-width refs and mentions, I want ID parsing tolerant of any padding, so that content written before the raise keeps resolving forever |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a squad owner whose counter hits the cap, I want create to fail with a clear index-full error naming the fix, so that the format never silently grows a digit

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** with padding 6, allocating sequence 1,000,000 raises a SquadsError stating the index is full and naming the raise-padding command; no wider ID is ever emitted.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a squad owner raising the padding, I want one command that renames every file to the new width and rebuilds the index, so that the squad stays uniform without hand-work

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the raise command (design picks the name/home, near migrate/repair) bumps padding one-way, renames ALL item files to the new width, rebuilds the index, and leaves file contents byte-untouched; sq check clean afterwards.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a teammate whose items hold old-width refs and mentions, I want ID parsing tolerant of any padding, so that content written before the raise keeps resolving forever

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** TASK-000007 and TASK-0000007 resolve to the same item everywhere an ID is read (refs, parent, prose mentions, CLI args, backrefs); display always uses the current padding; covered by mixed-width fixture tests. Lands in FEAT-000019's shared resolver.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
