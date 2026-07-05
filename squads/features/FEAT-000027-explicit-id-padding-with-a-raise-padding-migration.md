---
id: FEAT-27
sequence_id: 27
type: feature
title: Explicit ID padding with a raise-padding migration
status: Done
parent: EPIC-12
author: product-owner
priority: medium
refs:
- FEAT-13
- FEAT-19:depends-on
- ADR-104
description: 'padding: 6 stored in the index; create errors when the counter would
  overflow it; a one-way repad command renames all files to the new width; ID parsing
  tolerant of any width since file contents are never rewritten'
subentities:
- local_id: US1
  title: Index-full error with fix instructions at sequence cap
  status: Done
- local_id: US2
  title: Single command renames all files to new padding width
  status: Done
- local_id: US3
  title: ID parsing tolerates any padding width for old refs
  status: Done
created_at: '2026-06-10T15:04:04Z'
updated_at: '2026-06-23T10:01:00Z'
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
  padding is presentation. This lands naturally in FEAT-19's shared resolver. Display always
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
  (FEAT-13).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 27 add-story "As a <role>, I want … so that …"`; track with `sq feature 27 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Index-full error with fix instructions at sequence cap |
| US2 | Done |  | Single command renames all files to new padding width |
| US3 | Done |  | ID parsing tolerates any padding width for old refs |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Index-full error with fix instructions at sequence cap

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** with padding 6, allocating sequence 1,000,000 raises a SquadsError stating the index is full and naming the raise-padding command; no wider ID is ever emitted.

As a squad owner whose counter hits the cap, I want create to fail with a clear index-full error naming the fix, so that the format never silently grows a digit.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Single command renames all files to new padding width

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the raise command (design picks the name/home, near migrate/repair) bumps padding one-way, renames ALL item files to the new width, rebuilds the index, and leaves file contents byte-untouched; sq check clean afterwards.

As a squad owner raising the padding, I want one command that renames every file to the new width and rebuilds the index, so that the squad stays uniform without hand-work.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — ID parsing tolerates any padding width for old refs

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** TASK-000007 and TASK-0000007 resolve to the same item everywhere an ID is read (refs, parent, prose mentions, CLI args, backrefs); display always uses the current padding; covered by mixed-width fixture tests. Lands in FEAT-19's shared resolver.

As a teammate whose items hold old-width refs and mentions, I want ID parsing tolerant of any padding, so that content written before the raise keeps resolving forever.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T20:56:21Z] Olivia Lead:
  - DESIGN DECISION (deferred item from the spec) — raise-padding command name & home: **`sq migrate repad <width>`**, a new command under the existing `sq migrate` Typer app (sibling of `up`/`help`/`chlog`), NOT under `sq repair`.
  - Rationale: (1) Grammar fit — repad is a one-way, whole-squad on-disk rewrite that bumps a stored format parameter and rebuilds the index; that is exactly the shape of a migration, not the idempotent integrity-restore that `sq repair` is. `sq repair` must stay safely re-runnable; repad is a deliberate, irreversible format bump. (2) `sq migrate` already owns 'change the on-disk format, then rebuild the index' and already prints manual-step / sync follow-ups. (3) Verb 'repad' reads as repad-to-width and won't be confused with the schema-version `up`. Signature: `sq migrate repad <new-width>` (positional int), refuses when new-width <= current padding with a clear error, leaves file *contents* byte-untouched, renames every item file to the new width, rebuilds the index, stamps padding into the index.
  - Built-in default width stays **6** — unchanged, so golden-file tests keyed to width-6 IDs stay green. Existing squads get padding=6 backfilled via repair/migration.
  - @architect — one point for your eye, recorded on the task too: `padding` is authoritative index state but is NOT reconstructable from item frontmatter (every item would just re-derive to its filename's width). So `sq repair` must *preserve* the stored padding across a rebuild (like it preserves the counter high-water mark) rather than recompute it. Flagging because it bends invariant 1 slightly: padding is index state that repair carries forward, not derives. I think that's correct and intended by the spec ('padding stored in the index'), but want your confirmation.
- [2026-06-14T20:59:15Z] Robert Architect:
  - RULING (architect, design gate for FEAT-27 / TASK-101) — storing `padding` as authoritative index state is ACCEPTABLE under invariant 1. It does not bend the invariant; it follows the existing counter precedent exactly.
  - Reframing the concern: ADR-71's 'reconstructable from the files' has never meant 'stored in one item's frontmatter'. The global counter (ADR-72) is already squad-wide state that NO single item's frontmatter holds — repair reconstructs it as max(ID numbers across the corpus) with the previously-stored counter carried forward as a floor (`db.counter = max(previous_counter, max_n)`, _maintenance.py:192). Padding is the same category of state: a squad-wide on-disk-format parameter, reconstructable from the corpus as a whole, not from any one file. So 'frontmatter is the source of truth' is unviolated — the durable item state ADR-71 protects (status/parent/refs/sub-entities) still lives in frontmatter; padding is a format parameter, like the counter is an allocation parameter.
  - What repair MUST do — derive-from-filenames with the stored value as the FLOOR (validated combination, NOT pure carry-forward and NOT pure recompute). Concretely, mirroring the counter: padding = max(previous_padding, max filename width across all item files), where previous_padding is the value loaded from the prior index (default 6 if absent), and 'filename width' is the digit-run width of each PREFIX-<digits>-<slug>.md name.
  - Why filenames, not frontmatter, are the content-side signal: repad leaves file CONTENTS byte-untouched, so frontmatter `id`/`sequence_id` keep the OLD width forever. Deriving padding from frontmatter id width would silently re-shrink it after every repad — wrong. The filename is the only in-corpus record that a repad happened. Hence filenames are the recompute source and the stored value is the floor.
  - Why the floor is required (Olivia's edge cases, both handled): (a) EMPTY squad — no files, max-width is undefined/0; the stored floor keeps padding at its real value. (b) MID-RENAME / partial corpus — some files renamed to new width, some not; max-width already reflects the widest, and the floor guarantees we never regress below what was stored even if the widest file is the one that didn't get scanned. The floor makes repair monotonic in padding, exactly as it is monotonic in the counter (never regress).
  - Backfill: a pre-existing index without `padding` reads as 6 via the model default; repair must WRITE padding into the rebuilt SquadsDB (don't rely on the default at read time only) so the field is materialised. `sq repair` stays idempotent and re-runnable — running it twice yields the same padding.
  - One guard for Elias on TASK-101: filename-width derivation must read the DIGIT-RUN width (rpartition the trailing number), not naive string length, and must ignore non-item files. Use the same number-parsing path the scan already uses; do not invent a second parser.
  - Net: TASK-101's line 'repair must PRESERVE the stored padding (like the counter)' is correct in spirit but should be implemented as max(stored_floor, max_filename_width), NOT a blind carry-forward — the floor is the carry-forward, the filename max is the recompute, and repair takes the higher. This is consistent with how repair already treats the counter. Cleared to implement. @tech-lead
<!-- sq:discussion:end -->
