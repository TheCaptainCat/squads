---
id: TASK-849
sequence_id: 849
type: task
title: Strip the retired regions corpus-wide in the repair sweep
status: Ready
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
- TASK-847:depends-on
- TASK-848:depends-on
- TASK-813
- TASK-851:depends-on
- TASK-852:depends-on
- TASK-853:depends-on
description: A sweep inside Service.repair()'s corpus walk removes both retired marker
  region families, every role and system-skill body, and the retired role extra keys
  — no migration record, no schema change, no version bump
subentities:
- local_id: ST1
  title: Strip both retired marker region families in the repair sweep
  status: Todo
  story: US4
- local_id: ST2
  title: Empty every role body and strip the role extra mirror
  status: Todo
  story: US4
- local_id: ST3
  title: Write the MANUAL section and the changelog announcement
  status: Todo
  story: US4
- local_id: ST4
  title: Prove the sweep on the fixtures and through the bare verb
  status: Todo
  story: US4
- local_id: ST5
  title: Strip this repository's own squad corpus
  status: Todo
  story: US4
- local_id: ST6
  title: Empty every system skill body, keyed on is_system_skill
  status: Todo
  story: US4
- local_id: ST7
  title: Record the ordering prohibition the verb placement satisfies
  status: Todo
  story: US4
created_at: '2026-09-01T08:04:14Z'
updated_at: '2026-09-01T11:20:32Z'
---
<!-- sq:body -->
## Scope

FEAT-694 US4 plus the corpus half of ADR-776's fourth 2026-09-01 amendment: remove the two
retired marker regions, the contents of every role and system-skill body, and the retired role
frontmatter keys, from every file that already carries them.

**The vehicle is `Service.repair()`'s corpus walk.** There is no second `Migration` record, no
`SCHEMA_VERSION` change, no version bump, no new corpus fixture, and no strip step inside any
runner. `_migrations/_v0_11_to_v0_14.py` is not edited by this task at all, and
`scripts/bump_version.py` is not run.

## Why repair, and why the stamp cannot be the axis

Three facts decide it, each verified in the tree:

- **`repair` reaches both populations with one implementation.** `run_pending_migrations`
  (`_services/_maintenance.py`) applies the ordered runners, then calls `repair()`, then stamps.
  A squad at 0.11 or below therefore gets the sweep on its way up with nothing declared for it,
  and a squad already stamped current gets it from the ordinary verb.
- **A corpus can arrive at the current stamp with no runner ever visiting it.** `adopt` over a
  folder carrying no `.squads.toml` writes a fresh config whose `schema_version` defaults to the
  build's own `SCHEMA_VERSION` (`_models/_config.py`) and then rebuilds from disk. That is a
  property of how a squad can reach a stamp, not a consequence of this release's staging — so a
  stamp-keyed vehicle would keep missing a population that keeps being manufactured.
- **The ordering prohibition stops being a rule and becomes a property.**
  `require_current_schema` (`_cli/_common.py`) refuses every subcommand but `migrate` on a
  mismatched stamp, so `sq repair` can only ever run against a corpus already at the current
  schema; the one call on a behind-schema corpus is the tail of `run_pending_migrations`, after
  every runner has finished. A surface regeneration therefore always reads a mirror that is
  still there.

## The seam

`MaintenanceMixin._rebuild_index_from_disk`'s per-file loop already rewrites file **content**,
not only the index: `_record_pending_canonicalization` queues `(path, new_text, item_id)` onto
`pending_canonicalization` for every file whose on-disk ref encoding is stale, and that list is
written **after** the corpus-alignment refusal check, markdown strictly before the index commit,
and reported back as `canonicalized`.

The sweep is one more recorder in that same per-file loop, on that same deferred list. It
inherits the idempotence the method already documents in place: a corpus needing no correction
writes no file at all, and a second pass over a corrected corpus is byte-identical to the first.

**Two couplings, and they are the part to review twice.**

1. **The index entry is built from the same frontmatter the sweep rewrites.** The loop ends each
   iteration with `db.add(item)`, where `item` came from `Item.from_frontmatter(data, ...)`. A key
   the sweep removes from a role file must also be removed from that `Item` **before** `db.add`,
   or the file and the index disagree on exactly the key just deleted — and the frontmatter skew
   guard is the only thing standing between that and a silent divergence.
2. **Two writers, one file, one text.** `_record_pending_canonicalization` builds its replacement
   from the file's original `text`. A sweep that independently builds its own replacement from
   that same original `text` and appends a second entry for the same path means whichever entry
   is written last silently discards the other's edit. Compose instead: at most one queued entry
   per path, carrying both transformations applied in sequence. A file needing ref
   canonicalisation **and** a region strip is the case that proves it.

## What the sweep removes

Corpus-wide, from every `.md` file under the squad directory:

1. the `sq:summary` marker region — open marker through close marker, and the blank line the
   region was inserted with;
2. every `sq:<kind>:<local-id>:head` marker region;
3. the **contents** of a role item's `sq:body` region — emptied, markers kept;
4. the **contents** of a **system (template-owned)** skill item's `sq:body` region — emptied,
   markers kept;
5. from a role item's frontmatter `extra`: `full_name`, `title`, `mission`, `responsibilities`,
   `agreements`, `color`, `can_spawn`, `description`, `skills`, and `model` for a non-dev role.

Everything else stays byte-for-byte: the authored `:body` and `:discussion` regions inside each
sub-entity block, the `### ST1 — title` headings, the container regions, every **custom
(authored)** skill body, the top-level `title` and `description` fields on a role item, its
retained `extra` keys (`slug`, `is_default`, `is_dev`, `tech`, a dev role's `model`), and every
other frontmatter key on every other item.

Emptying is removal under the governing rule: a role body and a system-skill body lose their
contents and keep their `sq:body` markers. `role_body()`'s absent-region branch is what
`sq role show` renders as "no active item for this slug" — a *removed* region prints a false and
alarming message for a role that is active. The same holds for a system skill's region.

## The frozen list, and the rule that governs what may join it

Repair is not thereby a place to put content deletions. The sweep may remove only a **named
retired region or key** for which, in this same build: no live write path produces it; no read
path consumes it as authoritative, its computed replacement having already shipped; and its
content is derived, never authored. The five names above are that list, and it is frozen.
Adding to it is a decision, not a developer's choice, and a name may not be added before its
writer retires.

The guard that keeps the list honest is falsifiable: for every name on it, a fresh squad driven
through the write path produces none of them. Restore a writer and the assertion reddens. A name
added early does not merely leave dead bytes behind — it puts the sweep and the writer into a
loop where each undoes the other on alternate commands.

## Measured scale on this corpus

Counted with a tag scan **first validated against a file known to carry both region families**,
then run over the whole corpus:

- `sq:summary`: **632 files**, 632 opens and 632 closes.
- `sq:<kind>:<local-id>:head`: **436 files**, **1545 opens and 1545 closes**. Kinds present:
  `subtask` (632), `finding` (593), `story` (320). Local ids are **uppercase** — `ST1`, `F1`,
  `US1` — so a scan whose character class assumes lowercase finds nothing.

**The head tag is not a declared constant, and this is where a scan goes wrong.**
`_models/_markers.py` declares `SUMMARY` and no head constant; `_discussion._head_tag` composes
`<kind>:<local-id>:head` at write time. A probe that concludes "no head regions" from the absent
constant is answering a question about one module, not about the corpus. Count the corpus, and
validate any scan against a known positive before trusting its number.

## Finding the regions: match by shape, not by declared vocabulary

Scan for the fixed `sq:summary` pair and for marker tags ending in `:head`. A shape scan is
vocabulary-blind: it strips a head belonging to a sub-entity kind a project declared and later
dropped, and it does not make the sweep depend on the live spec's kind list.

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` constrains runners,
not this seam, but its discipline is worth keeping here anyway: do not import `_discussion`'s
private `_head_tag`, and do not read `spec.subentity_kinds` to build the tag set.
`markers.SUMMARY`, `markers.BODY` and the marker open/close helpers are the right vocabulary.

Removal must be **marker-safe**: cut from a region's own open marker through its own close marker
using `_sections`, never a line-range guess, and never a regex that could run from one region's
opener to a different region's closer. A file whose summary region is already gone, a block whose
`:head` is absent, a role body already empty, an `extra` carrying none of the removed keys — each
is a no-op.

## Choosing the skill files: `is_system_skill`, and nothing else

**Not the folder, not the item type, not the `sq-` prefix.** In this repository 22 of the 23
generated-looking roster files are in class and the 23rd is `releasing-squads` — `kind: custom
(authored)`, ~10 KB of authored runbook sitting in the same folder with the same item type and
the same frontmatter shape as the system skills beside it. Each of those three cheaper keys
destroys it.

`is_system_skill(slug, spec)` (`_interactions/__init__.py`) is a pure function of the slug and
the active spec, already ships, and already backs `set_body`'s refusal of exactly these writes.
It is the one correct discriminator, and the authored-content risk in this task is not inside a
region — it is choosing the wrong files.

`is_system_skill` reads the **live** spec, which is what makes it correct for an adopter who
renamed or dropped a type; a frozen slug list would mistake that adopter's custom skill for a
system one. State that in a comment beside the call so the next reader does not "fix" it back to
a literal.

## The announced diff

`repair`'s advertised job is the index, and it now rewrites content as well. An operator who runs
it to reconcile an index gets a content diff they did not ask for — on this corpus, over a
thousand regions across 632 and 436 files. The answer is announcement, not prevention: the sweep
reports the files it touched the way `canonicalized` already does, in the `RepairResult` and in
the reflog delta, so the diff is stated rather than discovered. An adopter running `sq repair`
over a dirty working tree cannot separate the sweep's changes from their own; that is the stated
price, not a defect to engineer around.

## Stripping this repository's own corpus

Run `uv run sq repair`, read the diff, commit it narrowly. **No stamp rewind.** Hand-editing
`.squads.toml`/`.squads.json` back to `"0.11"` to make a runner fire inverts invariant 1's
direction and is a procedure that can be handed to no adopter.

Do it **after every sibling task has landed**. If the live write path still materialises a head
or a roll-up, or still regenerates a role or system-skill body on sync, the very next mutation
re-materialises what the sweep just removed.

## The `v0_14` fixture stays frozen

`run_pending_migrations` calls `repair()` only when a runner applied, so a corpus already at the
current stamp still migrates to nothing and still carries its regions. That remains the right
proof that the read path tolerates them, and it is the same tolerance an un-migrated adopter file
needs.

## Acceptance

- The strip is a sweep inside `Service.repair()`'s corpus walk, recorded on the same deferred
  list as the existing ref canonicalisation and written markdown-before-index, after the
  corpus-alignment refusal check. No new `Migration` record, no `SCHEMA_VERSION` change, no new
  corpus fixture, no strip step in any runner, and `_migrations/_v0_11_to_v0_14.py` unmodified.
  `scripts/bump_version.py` was not run.
- Both retired region families are stripped: the fixed `sq:summary` pair and every
  `sq:<kind>:<local-id>:head` pair, matched by tag shape and with uppercase local ids, proven on
  a corpus carrying both.
- A head region belonging to an **adopter-declared** sub-entity kind is stripped too, proven with
  a constructed corpus carrying one — the shape scan, not a declared-kind list.
- Every `sq:body` marker pair survives. No region is deleted, only emptied.
- A **custom (authored)** skill body is byte-identical before and after, proven on a fixture
  carrying one **and** on a custom skill whose slug starts with `sq-`. Falsify it: key the step on
  the folder instead, watch that assertion go red, restore `is_system_skill`, watch it go green.
- A dev role keeps `is_dev`, `tech` and `model`; a non-dev role loses `model`. Both proven.
- **File and index agree after the sweep.** A role file whose `extra` the sweep strips produces an
  index entry without those keys in the same rebuild — asserted directly, not inferred from a
  clean `sq check`.
- **A file needing both ref canonicalisation and a region strip gets both**, in one write, proven
  by a constructed case. Neither transformation discards the other.
- The sweep is idempotent: `sq repair` twice over the same corpus produces no second diff, and a
  squad that never carried any of the named regions or keys is byte-unchanged by it.
- The frozen-list guard is falsifiable and present: a fresh squad driven through the write path
  produces none of the listed names, and restoring a writer reddens the assertion.
- `sq repair` reports the files the sweep touched in its result and in the reflog delta.
- Migrating each of the `v0_1` … `v0_11` corpus fixtures to current leaves **no** `sq:summary`
  region, **no** `:head` region, **no** content inside any role item's or system skill's
  `sq:body` region, and **none** of the removed role `extra` keys — asserted per fixture, not
  spot-checked. And `sq repair` alone, on a corpus stamped current that carries the regions,
  strips them and is a no-op on a second run.
- For at least one fixture, the authored content is proven untouched: every sub-entity `:body`
  and `:discussion` region's bytes, every sub-entity heading, every container region, every role
  item's top-level `title`/`description`, its retained `extra` keys and every other item's
  frontmatter are compared before and after and are identical.
- The compiled `CLAUDE.md`/`AGENTS.md` regions and backend pointers after a 0.11 → current
  migration are **byte-identical** to what the same squad renders with the mirror intact —
  proven by outcome on a fixture whose role items carry the mirror, not by asserting call order.
- `sq check` and `sq repair` are clean on every migrated corpus, and the frozen `v0_14` fixture
  still migrates to nothing and still checks clean while carrying its regions and its mirror.
- `sq role <slug> show` and `sq skill <slug> show` render their full definitions on a swept
  corpus — the shrink costs the reader nothing.
- `sq migrate chlog` prints one manual entry covering the retirement and the shrink, worded so it
  attributes the removal to the rebuild at the end of `sq migrate up` rather than to the runner.
  The registry `summary` line and the runner's module docstring are unchanged.
- This repository's own squad carries no `sq:summary` region, no `:head` region, no role or
  system-skill body content and none of the removed role `extra` keys; `releasing-squads` is
  byte-identical; every role item's top-level `title:` and `description:` are byte-identical;
  and `sq check` is clean on it.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 849 add-subtask "<title>"`; track with `sq task 849 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Strip the summary and head marker regions corpus-wide | US4 |
| ST2 | Todo |  | Strip the role Skills block and skills frontmatter key | US4 |
| ST3 | Todo |  | Correct the runner docstring, registry summary and MANUAL | US4 |
| ST4 | Todo |  | Prove the step on the frozen corpus fixtures | US4 |
| ST5 | Todo |  | Strip this repository's own squad corpus | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip both retired marker region families in the repair sweep

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add one more recorder to `MaintenanceMixin._rebuild_index_from_disk`'s per-file loop that removes
the two retired marker regions from every `.md` file under the squad directory:

- the fixed `sq:summary` region, and the blank line it was inserted with;
- every `sq:<kind>:<local-id>:head` region.

Queue the rewrite onto the same deferred list the existing ref canonicalisation uses, so it is
written after the corpus-alignment refusal check and markdown-before-index, exactly as
`_record_pending_canonicalization` already is.

**One queued entry per path.** The canonicalisation recorder builds its replacement text from the
file's original `text`. A second, independent entry for the same path built from that same
original text means whichever is written last discards the other's edit. Compose the two
transformations into one write. A file needing both is the case that proves it.

**Find them by tag shape, not by declared vocabulary.** Scan for marker tags ending in `:head` and
for the fixed summary pair. A shape scan is vocabulary-blind, so it also strips a head belonging
to a sub-entity kind a project declared and later dropped. Do not import `_discussion`'s private
`_head_tag`, and do not read `spec.subentity_kinds` to build the tag set; `markers.SUMMARY` and
the marker open/close helpers are the right vocabulary.

**Local ids are uppercase.** The live corpus carries `sq:subtask:ST1:head`, `sq:finding:F1:head`,
`sq:story:US1:head`. A character class that assumes lowercase matches nothing, and an absent
`HEAD` constant in `_models/_markers.py` proves nothing about the corpus — the tag is composed at
write time. Validate any scan against a file known to carry the region before trusting a count.
The corpus census this is measured against: 632 files carry a balanced `sq:summary` pair, and 436
files carry 1545 balanced `:head` pairs.

Removal must be **marker-safe**: cut from a region's own open marker through its own close marker
using `_sections`. Never a line-range guess, and never a regex that could run from one region's
opener to a different region's closer.

Everything else stays byte-for-byte: the authored `:body` and `:discussion` regions inside each
sub-entity block, the `### ST1 — title` headings, the container regions, and every frontmatter key.

Idempotent: a file with no summary region, or a block with no `:head`, is a no-op; a second
`sq repair` produces no diff; a squad that never carried either region is byte-unchanged.

Done when the sweep strips both region families across a corpus, composes cleanly with the
canonicalisation writer on a file needing both, leaves every other byte untouched (proven by a
before/after comparison of the authored regions on at least one fixture), and is a no-op on a
second run.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Empty every role body and strip the role extra mirror

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The **whole** `sq:body` region of every role item is emptied — contents removed, markers kept —
and the retired mirror keys are removed from its frontmatter `extra`, in the same repair sweep.

Keep the markers. `role_body()`'s absent-region branch is what `sq role show` renders as "no
active item for this slug"; a removed region prints a false and alarming message for a role that
is active, and the marker pair is the shape every item file shares.

From a role item's frontmatter `extra`, remove: `full_name`, `title`, `mission`,
`responsibilities`, `agreements`, `color`, `can_spawn`, `description`, `skills`, and `model`
**for a non-dev role only**. A dev role is the one identified by `extra.is_dev`; its `model` is
operator-settable and stays, along with `tech`.

Retained on every role item, and not to be touched: the top-level `title` and `description`
fields — the uniform record other surfaces read, not part of the mirror — and the `extra` keys
`slug`, `is_default`, `is_dev` and `tech`.

**The index must be stripped with the file, in the same pass.** This is the coupling the repair
vehicle introduces that a runner step did not. The rebuild loop ends each iteration with
`db.add(item)`, where `item` was parsed from the very frontmatter this sweep rewrites. Remove the
key from the `Item` before it is added, or the file and the index disagree on exactly the key
just deleted and the frontmatter skew guard is all that stands between that and a silent
divergence. Assert the agreement directly — a clean `sq check` does not prove it, because
`PERMITTED_EXTRA_SKEW` exempts these very keys.

Removing keys from `extra` is a frontmatter rewrite, not a region edit: preserve every other key
and the file's key ordering, and do not re-serialise values the sweep is not removing.

An `extra` already carrying none of the removed keys is a no-op, and so is a body already empty.
A role file must survive two `sq repair` runs with no second diff.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Write the MANUAL section and the changelog announcement

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Write the adopter-facing prose the sweep owes. **No runner, registry or docstring change.**

With the strip in `repair` rather than in `_v0_11_to_v0_14.migrate()`, the runner's module
docstring stays true ("no existing item data is rewritten" is still a correct statement about the
runner) and the registry `summary` line stays about the two new types. Both are explicitly out of
scope; do not edit them.

Two pieces are owed, for two different populations:

- **`MANUAL` gains one more section**, inside the same shared runbook string, for an adopter
  migrating from 0.11 — they do experience the removal, and the sentence has to be true about
  *where*: it happens in the **index rebuild at the end of `sq migrate up`**, not in the runner.
  What they need, in their terms: the sub-entity roll-up table and badge line no longer live in
  the file (they are computed on every read); a role's definition and a template-owned skill's
  body are no longer stored in their item files and are rendered by `sq role <slug> show` /
  `sq skill <slug> show` on every call; a **custom** skill's body is untouched and stays authored
  storage; and a role's mission and responsibility text is no longer matched by `sq search` —
  `sq role list` / `sq role catalog` / `sq role <slug> show` answer instead.
- **A CHANGELOG line**, because the already-stamped population has no runbook path at all: `chlog`
  is keyed to a schema transition they will never perform. Their announcement is the release note
  saying `sq repair` removes the retired regions and the role mirror, and that it therefore
  produces a content diff on any corpus still carrying them.

Nothing about ref encoding belongs in either; that remains ruled out. No note about overriding
`roles/role.md.j2` is owed: the whole region is emptied, so the shape of an overridden template
no longer matters.

There is **no** new corpus fixture: a fixture is owed per schema bump and this adds none.

Done when `sq migrate chlog` prints one manual entry covering the retirement and the shrink and
attributing the removal to the rebuild rather than the runner; the CHANGELOG carries the line for
the already-stamped population; the registry still holds exactly one 0.14 record; and neither the
registry `summary` nor the runner docstring has changed.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prove the sweep on the fixtures and through the bare verb

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Prove the sweep on the frozen corpus fixtures, and prove it through the bare verb.

**Through `migrate up`.** `v0_1` … `v0_11` all migrate forward and end in the `repair()` call at
the tail of `run_pending_migrations`. Assert per fixture, after migrating to current:

- no `sq:summary` region anywhere;
- no `:head` region anywhere;
- no content inside any role item's `sq:body` region, and none inside any system skill's;
- every `sq:body` marker pair still present — emptied, never deleted;
- none of the removed role `extra` keys (`full_name`, `title`, `mission`, `responsibilities`,
  `agreements`, `color`, `can_spawn`, `description`, `skills`, and `model` on a non-dev role);
- the retained ones still present: `slug`, `is_default`, and `is_dev`/`tech`/`model` on a dev role;
- the rebuilt index carries the same `extra` the files now carry — the key removed from the file
  is absent from the index entry too, asserted directly rather than inferred from a clean check;
- `sq check` and `sq repair` clean.

**Through `sq repair` alone.** On a corpus stamped current that still carries the regions, the
bare verb strips them and is a no-op on a second run. This is the case the migration path cannot
reach and the whole reason the vehicle moved.

**A squad that never carried them is byte-unchanged** by `sq repair` — the negative case that
stops the sweep becoming a reformatter.

For at least one fixture, compare the authored content before and after: every sub-entity `:body`
and `:discussion` region's bytes, every sub-entity heading, every container region, every role
item's top-level `title` and `description`, and every other item's frontmatter identical. That is
the clause that actually proves "no authored content moves"; an absence assertion alone does not.

Four cases the frozen fixtures do not supply and that must be constructed:

- an **adopter-declared** sub-entity kind carrying a head region, to prove the shape scan rather
  than a declared-kind list;
- a **custom (authored)** skill, asserted byte-identical after the sweep — including one whose
  slug starts with `sq-`, the case a prefix-keyed implementation passes everything else while
  getting wrong;
- a **dev** role beside a non-dev one, to prove `model` survives on the first and not the second;
- a file needing **both** ref canonicalisation and a region strip, to prove the two writers
  compose into one write instead of one discarding the other.

Prove the ordering by its outcome, not by asserting call order: migrate a fixture whose role items
carry the mirror and compare the resulting `CLAUDE.md`/`AGENTS.md` managed regions and backend
pointers against what the same squad renders with the mirror intact. Byte-identical, not merely
present.

Assert the reader is whole on a swept corpus: `sq role <slug> show` and `sq skill <slug> show`
render their full definitions from files that no longer store them.

**Leave `tests/fixtures/corpus/v0_14` frozen.** `run_pending_migrations` calls `repair()` only
when a runner applied, so a corpus already at the current stamp migrates to nothing, still carries
its regions and its mirror, and must still pass `sq check`. Assert that explicitly — it is the
same tolerance an un-migrated adopter file needs, and it is why `markers.SUMMARY` stays in
`_validators`' structural tag set.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Strip this repository's own squad corpus

<!-- sq:subtask:ST5:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Strip this repository's own squad corpus. **This is the step a developer will otherwise skip while
reporting the sweep verified.**

Our squad is already stamped `"0.14"`, so `uv run sq migrate up` here is a no-op and the sweep
never runs through the migration path. It runs through the ordinary verb instead.

1. Land **every** sibling task first. If the live write path still materialises a head or a
   roll-up, or still regenerates a role or system-skill body on sync, the next mutation
   re-materialises what the sweep just removed.
2. Run `uv run sq repair`. **No stamp rewind.** Hand-editing `.squads.toml`/`.squads.json` back to
   `"0.11"` to make a runner fire inverts invariant 1's direction and is a procedure that can be
   handed to no adopter.
3. Read the diff before committing. Measured census: 632 files carry a `sq:summary` region; 436
   carry 1545 `:head` regions; the role files carry a body and the `extra` mirror; the system
   skill files carry a body. The diff must contain **only** region removals, role and
   system-skill body emptying, and role `extra` key removals — nothing else. In particular the
   `releasing-squads` skill file is byte-identical, and every role item's top-level `title:` and
   `description:` are byte-identical. Any other change is a defect in the sweep, not something to
   accept because the tests pass.
4. Confirm `sq check` clean, a second `sq repair` producing no diff, the schema still stamped
   `"0.14"`, and `sq role <slug> show` / `sq skill <slug> show` still rendering full definitions.

Stage the corpus diff narrowly and separately from the source change, so the review can read the
mechanical diff apart from the logic. Stage named paths — a repository-wide `add` sweeps whatever
else is in the tree into it.

Done when this repository's squad carries no `sq:summary` region, no `:head` region, no role or
system-skill body content and none of the removed role `extra` keys; `releasing-squads` is
byte-identical; `sq check` is clean; and the diff was read rather than assumed.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Empty every system skill body, keyed on is_system_skill

<!-- sq:subtask:ST6:body -->
Every **system (template-owned)** skill item's `sq:body` region is emptied by the repair sweep —
contents removed, markers kept. Every **custom (authored)** skill file is untouched.

The discriminator is `is_system_skill(slug, spec)` (`_interactions/__init__.py`), a pure function
of the slug and the active spec that already ships and already backs `set_body`'s refusal of
exactly these writes. **Not the folder, not the item type, not the `sq-` prefix.** In this
repository 22 of the 23 generated-looking roster files are in class and the 23rd is
`releasing-squads` — roughly 10 KB of authored runbook in the same folder, with the same item type
and the same frontmatter shape as the system skills beside it. Each of those three cheaper keys
destroys it.

`is_system_skill` reads the **live** spec, which is what makes it correct for an adopter who
renamed or dropped a type — a frozen slug list would mistake that adopter's custom skill for a
system one. State that in a comment beside the call so the next reader does not "fix" it back to
a literal.

Keep the markers, for the same reason as on the role side. A system skill item carries no
discussion region today and gains none.

A body already empty is a no-op; the sweep runs clean twice.

The proof that matters is the negative one: assert `releasing-squads` (and a constructed custom
skill whose slug starts with `sq-`) is byte-identical after the sweep. Falsify it — key the sweep
on the folder instead, watch that assertion go red, restore `is_system_skill`, watch it go green.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Record the ordering prohibition the verb placement satisfies

<!-- sq:subtask:ST7:body -->
**A strip must never run ahead of a surface regeneration that reads what it removes, and must
regenerate nothing itself.**

State it that way — as a constraint on where a stripping step may sit relative to a
surface-touching one, not as an instruction to put one call after another. The local phrasing
survives until someone reorders two adjacent lines for tidiness; the prohibition is a property a
future step inherits without being told.

**On the repair vehicle the prohibition is satisfied by construction, and that is worth recording
rather than re-engineering.** `require_current_schema` refuses every subcommand but `migrate` on a
mismatched stamp, so `sq repair` can only ever run against a corpus already at the current schema.
The single call on a behind-schema corpus is the tail of `run_pending_migrations`, which runs
every ordered runner — `_regenerate_surface` included — before it. The regeneration therefore
always reads a mirror that is still there. What was a rule someone could break by tidying two
lines is now a consequence of where the verb sits.

What it protects: `_regenerate_surface` calls `write_managed` for every active backend and builds
its roster from `_live_roster`, the runner's frozen local copy of the roster projection, which
reads the `extra` mirror. Strip first and the compiled managed regions and every pointer
regenerate with a role's *title* replaced by the person's name and its responsibilities empty —
silently, with nothing near the cause failing.

**Do not teach `_live_roster` to resolve.** Its docstring records why it is local — `_services`
imports the migration registry, so calling `Service` from a runner is a real cycle — and the
general rule sits above that: a runner is frozen against the corpus vocabulary of the version it
transforms, and that corpus still carries the mirror.

Prove it by outcome rather than by asserting call order: migrate a fixture whose role items carry
the mirror, then compare the resulting `CLAUDE.md`/`AGENTS.md` regions and backend pointers
against what the same squad renders with the mirror intact. Byte-identical, not merely present.
That assertion is what fails if the property is ever broken.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T08:32:10Z] Olivia Lead:
  - Grew to carry the corpus half of ADR-776's second 2026-09-01 amendment, rather than a sibling task editing the same `migrate()` step: one pass over 630 files, same runner, same registry entry, same bump. Still Ready, still unstarted.
    
    - Scope/acceptance widened: role bodies and system-skill bodies are emptied (markers kept) and the role `extra` mirror keys are removed, alongside the two marker regions.
    - ST2 retitled from the `## Skills` block cut to the whole role body + `extra` mirror — the heading-boundary surgery, its discussion-heading scoping and the overridden-`role.md.j2` caveat all disappear when the region is emptied wholesale.
    - ST6 added: system skill bodies, keyed on `is_system_skill` and nothing cheaper. 22 of 23 files in class; `releasing-squads` (10.1 KB, authored) is the 23rd and a folder/type/prefix key destroys it.
    - ST7 added: the strip step runs **after** `_regenerate_surface`. That call renders the compiled managed regions and the pointers from `_live_roster` (`_v0_11_to_v0_14.py:136-176`), the runner's frozen local copy of the roster projection, which reads the mirror. Strip first and the surface regenerates with role titles replaced by person names and empty responsibilities — silently. Do not teach the frozen copy to resolve; order the step last.
    - ST3/ST4/ST5 updated for the wider scope. ST5 now waits on all four sibling tasks, not two.
    
    Now carries `depends-on` on TASK-851 and TASK-852 as well as TASK-847/848. TASK-813's `depends-on` edge here is unchanged and its acceptance still grows with this rather than a second registry entry appearing.
- [2026-09-01T10:41:02Z] Robert Architect:
  - Vehicle ruled — ADR-776, fourth 2026-09-01 amendment. This task's scope is rewritten against it; I have not touched the body.
    
    **The strip is a sweep inside `Service.repair()`'s corpus walk.** No second `Migration` record, no `SCHEMA_VERSION` change, no version bump, no new corpus fixture — and **no strip step inside `_v0_11_to_v0_14.migrate()`**. `run_pending_migrations` runs the runners and then calls `repair()` before stamping, so a squad at 0.11 gets the sweep on its way up with nothing declared for it, and a squad already stamped 0.14 gets it from the ordinary verb.
    
    What changes here:
    
    - **ST1/ST2/ST6 move** from a runner step to a recorder in `_rebuild_index_from_disk`'s per-file loop, on the same deferred `pending` list the existing ref canonicalization uses (written markdown-before-index, after the corpus-alignment refusal). Everything else in those subtasks holds unchanged: shape-scan the marker tags, marker-safe cuts, empty-not-delete `sq:body`, `is_system_skill` and nothing cheaper.
    - **ST7's prohibition stands and is now satisfied by construction.** `require_current_schema` refuses every subcommand but `migrate` on a mismatched stamp, so repair only ever runs at the current schema, and the one call on a behind-schema corpus is the migration tail — after `_regenerate_surface`. Prove it by the same outcome comparison the subtask already specifies; do not engineer an order.
    - **ST5's stamp rewind is withdrawn.** Strip this corpus with `uv run sq repair`, read the diff, commit it narrowly. Hand-editing `.squads.toml`/`.squads.json` back to "0.11" inverts invariant 1 and can be handed to no adopter. Everything else in ST5 holds: land the siblings first, and `releasing-squads` byte-identical.
    - **ST3 narrows.** The runner docstring correction is withdrawn — with no strip step, "no existing item data is rewritten" stays true of the runner, and the registry `summary` line stays about the two types. Still owed: the `MANUAL` section, worded so it attributes the removal to the rebuild at the end of `sq migrate up`, not to the runner. The already-stamped population gets no `chlog` path at all; their announcement is a CHANGELOG line saying `sq repair` removes the retired regions and the role mirror.
    - **ST4 keeps its fixture proofs** (they still run through `migrate up`, which ends in repair) and gains one: `sq repair` alone, on a corpus stamped current that carries the regions, strips them and is a no-op on a second run. The frozen `v0_14` fixture stays frozen — `repair()` is called only when a runner applied, so it still migrates to nothing and still carries its regions.
    - **One new coupling, and it is the one to review twice.** The walk builds each index entry from the same frontmatter the sweep rewrites, so a key removed from a role file must also be removed from the `Item` before `db.add` — otherwise file and index disagree on exactly the key just deleted.
    - **The governing rule on what the sweep may remove** is amendment §3: a named retired region or key that no live write path produces, that no read path consumes as authoritative, and whose content is derived. Guard it with a driven assertion that a fresh squad exercised through the write path produces none of the listed names; falsify it by restoring a writer.
    
    Two corrections to the record that change the acceptance:
    
    - **The `:head` half is real.** 436 files carry 1545 balanced `<kind>:<local-id>:head` regions here, already contradicting their own frontmatter — this task's own file has ST1 `Cancelled` / ST3 `Done` in frontmatter and `Todo` in both stored heads. The report of zero head regions came from looking for a `HEAD` constant in `_models/_markers.py`; the tag is built by `_discussion._head_tag`. Strip both halves.
    - **`adopt` manufactures the stranded population by design** — over a folder with no `.squads.toml` it stamps the build's own `SCHEMA_VERSION` and rebuilds, so no runner ever visits that corpus. That, not this release's staging, is why the vehicle cannot key on the stamp.
    
    @tech-lead this is the rewrite; no schema or version change is authorised by it, and nothing is to be bumped or tagged. @reviewer F1 and F2 are answered on their own discussions.
- [2026-09-01T11:20:32Z] Olivia Lead:
  - - Rewritten against ADR-776's fourth 2026-09-01 amendment. The vehicle is now a sweep inside `Service.repair()`'s corpus walk: no second `Migration` record, no `SCHEMA_VERSION` change, no version bump, no new corpus fixture, and **no strip step in any runner** — `_migrations/_v0_11_to_v0_14.py` is untouched by this task. Title and summary follow.
    
    - **Both retired region families are in, and the numbers are re-driven, not inherited.** I validated the tag scan against a known positive (this feature's own `TASK-000847` file, which carries seven `sq:subtask:STn:head` regions and one `sq:summary`) before running it over the corpus: **632 files** carry a balanced `sq:summary` pair; **436 files** carry **1545** balanced `sq:<kind>:<local-id>:head` pairs, split `subtask` 632 / `finding` 593 / `story` 320. Local ids are **uppercase** (`ST1`, `F1`, `US1`) — ST1 now says so, because a lowercase character class matches nothing and that is one of the two ways this count has already been got wrong. The other is looking for a `HEAD` constant in `_models/_markers.py`: the tag is composed by `_discussion._head_tag` at write time, so an absent constant is an answer about one module, not about the corpus.
    
    - **`is_system_skill` and nothing cheaper**, unchanged and restated in ST6 with the falsification drill: key the sweep on the folder instead, watch the `releasing-squads` byte-identity assertion redden, restore, watch it green.
    
    - **Two couplings the repair vehicle introduces that the runner step did not**, both now in the acceptance:
      - the loop builds each index entry from the same frontmatter the sweep rewrites (`db.add(item)` with the parsed `Item`), so a key removed from a role file must be removed from the `Item` before it is added — and this must be asserted directly, because `PERMITTED_EXTRA_SKEW` exempts exactly those keys and so a clean `sq check` does not prove it;
      - `_record_pending_canonicalization` builds its replacement from the file's original `text`, so a second independent entry for the same path silently discards one of the two edits. One queued entry per path, both transformations composed, with a constructed both-needed file as the proof case.
    
    - **ST3 narrowed, ST5's stamp rewind withdrawn, ST7 re-framed.** The runner docstring correction and the registry `summary` widening are gone (with no strip step, "no existing item data is rewritten" stays true of the runner). What is still owed: the `MANUAL` section worded to attribute the removal to the index rebuild at the end of `sq migrate up`, plus a CHANGELOG line, because the already-stamped population has no `chlog` path at all. ST5 strips this repo with `uv run sq repair`. ST7's prohibition now holds by construction via `require_current_schema`, and is recorded rather than engineered.
    
    - **One consequence for TASK-813, flagged not changed.** This task's old body asserted that TASK-813's acceptance "grows to include this work rather than a second registry entry appearing". That is now false in its runner half — nothing about the runner grows. The `depends-on` edge still stands, but for a narrower reason: ST3's `MANUAL` section lands in the shared runbook string TASK-813 owns. @architect @manager if TASK-813's own acceptance text still carries the wider claim, it wants the same narrowing.
    
    - Preserved acceptance discipline: idempotent (second `sq repair` produces no diff), markdown written before the index (same deferred list, after the corpus-alignment refusal check), and a squad that never carried the regions is byte-unchanged.
    
    - Still **Ready** — the prose is dispatchable — but genuinely blocked on TASK-851/852/853 landing first: ST5's own first step is that the live write path must have stopped producing what the sweep removes.
<!-- sq:discussion:end -->
