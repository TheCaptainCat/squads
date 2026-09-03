---
id: TASK-828
sequence_id: 828
type: task
title: Bound the undeclared-ref-kind refusal; repair canonicalises the file
status: Ready
author: tech-lead
priority: medium
refs:
- BUG-827:fixes
- ADR-775:implements
description: An undeclared ref kind refuses at the write and lint boundary only, and
  repair normalises the encoding it rests on
subentities:
- local_id: ST1
  title: Bound the refusal to the write and lint boundary
  status: Todo
- local_id: ST2
  title: Repair canonicalises the file, not only the index
  status: Todo
- local_id: ST3
  title: Correct the three refusal and hint messages
  status: Todo
- local_id: ST4
  title: Drive the recovery sequence end to end in tests
  status: Todo
created_at: '2026-08-26T11:51:47Z'
updated_at: '2026-08-26T11:53:06Z'
---
<!-- sq:body -->
## What is wrong

An undeclared ref kind on a live edge refuses at the **load** boundary, so every ordinary
command in the squad stops. ADR-775 A5 rules that radius wrong: measured against the
decision's own Context, an undeclared kind on an existing edge is a `sq check` finding, not
a load failure. Section 5 borrowed ADR-696 section 5a's terms and took its blast radius
along with them, and 5a earns that radius only because a re-prefixed type makes the corpus
vanish from the on-disk scan. Nothing vanishes here: every item is still found and every
edge still readable.

The refusal also names a remedy no command performs. It says "restore the entry in the
override, or remove those refs first", and the instant it fires the removal verb is refused
by the refusal that names it. That half is general, not a legacy-map artefact — a natively
spelled kind that is dropped locks a squad identically, with no legacy map anywhere.

Two facts the bug as filed gets the wrong way round, and the fix aims at the wrong surface
if they are carried over. `sq repair` is **not** locked out: it takes the documented bypass
(`get_service_bypassing_index_cross_check`, `_cli/_main.py:674`) and exits 0. It is the verb
that **creates** the locked state, by folding a legacy map under the renamed spec and storing
the spelled kind. `sq check` also still runs, through its documented bundled-spec fallback.

## Where it lives, verified

- The refusal: `_collect_ref_kind_alignment_errors` (`src/squads/_workflow/_loader.py:704`),
  reached through `validate_against_index` (`:1005-1008`) and its fail-closed wrapper
  (`:1328`). Three call sites bind it: `_cli/_common.py:138`, `_cli/_common.py:296`, and
  `_services/_service.py:343`. Dropping the ref-kind family from `validate_against_index`
  bounds all three at once.
- Lint keeps it independently: `lint_workflow_spec` calls the four collectors directly
  (`_loader.py:1213-1227`) rather than through `validate_against_index`, so the lint half
  survives the removal untouched.
- The fold: `fold_legacy_kinds` (`_models/_item.py:124`) resolves a legacy-map entry against
  the caller-supplied live default, so after a default-kind rename the map's recorded name no
  longer equals the default and is preserved literally.
- Repair: `_services/_maintenance.py:1498`, rebuilding through `_rebuild_index_from_disk`.

## The delivered behaviour

**1. The refusal is bounded to write and lint.**

- Refuses: `sq workflow lint`, and any command that would write a ref *of* an undeclared kind.
- Keeps running: every read command; `sq check`, reporting the stale kind as the bounded
  finding; `sq repair`; and the ref-removal verb.

Two halves of this are already built and only the load-time lock stops them being exercised,
so the work here is mostly subtractive:

- The **write** gate exists. `_add_ref_model` (`_services/_refs.py:411-414`) raises "unknown
  ref kind …" for any spelled kind the merged spec does not declare, `create()` runs the same
  check, and the bulk importer's `_resolve_refs` (`_services/_import.py:132-134`) repeats it.
  No new write gate is needed; confirm the three agree rather than adding a fourth.
- The **finding** exists. `_ref_kind_valid` (`_services/_validators.py:241-254`) already emits
  the warn the Context promised, and skips a bare edge by construction.
- The **read** path exists. `_edge_semantic` (`_services/_refs.py:171-178`) resolves through
  `spec.ref_kinds.get(...)`, so an undeclared kind traverses and reports a null semantic
  exactly as A3 ruled.

"Writes a ref of an undeclared kind" means introducing or spelling such an edge — not
persisting one the corpus already holds. An ordinary mutation of an item that carries a stale
edge must keep working: A5's own recovery depends on it ("mutate the affected item once so
its file is rewritten canonical"). The two paths that rewrite existing refs wholesale —
`_services/_retype.py:308`'s remap and `_services/_retirement.py:124-130`'s unlink — must not
be caught by the gate either.

**2. `sq repair` canonicalises the file, not only the index.** Repair writes back every file
whose folded frontmatter differs from its raw frontmatter, markdown before the index as
always, and converges: a second repair is byte-identical. A3 declined this write on the
ground that nothing downstream distinguishes the two encodings; A5 withdraws that ground,
because after a default-kind rename the fold resolves the two encodings to two different
kinds. This stays clear of the frozen-runner constraint for A3's own reason — repair is not
schema-keyed, resolves the default from the live spec by construction, and is reachable on
every arrival path that stays open.

**3. Three message corrections.**

- `spec_refusal` (`_loader.py:131`) closes with "`sq workflow lint` … is the one command that
  still runs while this stands". False, and disproved in one line by running repair or check.
  The sentence goes. Note the radius: `spec_refusal` is the shared text for *every* unloadable
  override, not the ref-kind axis — correcting it changes what the adopter reads for the
  type/status, prefix/folder and badge families too. That is intended (the claim is false for
  all of them), and it is the only thing those families change: their own load-boundary radius
  stays exactly as it is.
- The refusal itself (`_loader.py:743-747`) states an ordering it never completes. It states
  the sequence instead, and may now name `sq repair` as what canonicalises a legacy-map edge,
  because a command performs it.
- The same disprovable claim sits a third time in lint's own fix hint (`_loader.py:1206-1211`,
  "no command rewrites a corpus's ref kinds"). It travels with the other two.

**4. What the adopter is told they can do**, performable end to end with shipped verbs and no
hand-edited file: revert the override edit, `sq repair`, mutate the affected item once so its
file is rewritten canonical, re-apply the rename. Under the bounded refusal the revert is not
even needed, because the removal verb is not locked.

Out of scope, ruled and not to be reopened: folding against a frozen historical `related`
(rejected in A5 on the merits), and narrowing A1 to a normalised corpus (declined — A1 is
restored, not narrowed). The other alignment families keep their current radius.

## Acceptance criteria

- With a live edge spelling an undeclared kind: read commands, `sq check`, `sq repair` and
  `sq <type> <n> ref rm` all run and exit on their own contract; `sq workflow lint` refuses,
  and writing a *new* ref of that kind refuses by name.
- `sq check` reports the stale kind as a per-item warn finding, and no longer emits the
  "workflow config invalid" line for this cause — the bundled-spec fallback is not what is
  answering any more.
- `sq graph` traverses the stale edge and reports a null semantic rather than dropping it.
- Mutating an item that carries a stale edge succeeds and rewrites its file canonically;
  retype's remap and the retirement unlink are likewise unaffected.
- `sq repair` rewrites a file whose folded frontmatter differs from its raw frontmatter, writes
  markdown before the index, and a second repair is byte-identical.
- The end-to-end sequence in point 4 leaves lint clean, check clean, and both a legacy-folded
  and a natively bare edge reading as the new default — with no item `.md` touched by hand.
- No refusal or fix hint claims a command no longer runs, and none names a remedy no command
  performs.
- The other alignment families (type/status, prefix/folder, badge) still refuse at the load
  boundary, unchanged.
- Full suite green; `pyright` and `ruff` clean under `--all-extras`; `sq check` clean.

## Coordination

Nothing pins the ref-kind family at the fail-closed boundary today: no test in the suite
exercises that axis through `validate_against_index`. The removal will therefore not surface
as a failing test, and the bounded behaviour needs its own coverage or it regresses silently
in both directions.

Sequence this with the rest of the 0.14 ref-kind work rather than ahead of it. Nothing is
lost, nothing is silent, the state is fully recoverable with shipped verbs, and this
repository's own corpus carries no data that can reach it.

A developer is working in `src/squads/_backends/` and on the check validators; the validator
module is a shared surface with this work, so confirm before starting rather than assuming
it is free.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 828 add-subtask "<title>"`; track with `sq task 828 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Bound the refusal to the write and lint boundary |  |
| ST2 | Todo |  | Repair canonicalises the file, not only the index |  |
| ST3 | Todo |  | Correct the three refusal and hint messages |  |
| ST4 | Todo |  | Drive the recovery sequence end to end in tests |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bound the refusal to the write and lint boundary

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Drop the ref-kind family from the fail-closed load path: `validate_against_index`
(`src/squads/_workflow/_loader.py:1005-1008`) stops calling
`_collect_ref_kind_alignment_errors`, which bounds all three binding sites at once
(`_cli/_common.py:138`, `_cli/_common.py:296`, `_services/_service.py:343`). Leave the other
three families exactly as they are — their radius is not in question.

The collector itself stays, and stays wired into `lint_workflow_spec`, which already calls the
four collectors directly (`_loader.py:1213-1227`) rather than through `validate_against_index`,
so the lint half needs no change to survive the removal.

Then confirm, rather than rebuild, the three surfaces the ruling relies on already having:
the write gate in `_services/_refs.py:411-414` plus its twins in `create()` and the importer's
`_resolve_refs` (`_services/_import.py:132-134`); the warn finding in `_ref_kind_valid`
(`_services/_validators.py:241-254`); and the null-semantic read in `_edge_semantic`
(`_services/_refs.py:171-178`). If the three write sites disagree on wording or on which kinds
they accept, reconcile them; do not add a fourth gate.

Hold the line between introducing an edge of an undeclared kind (refused) and persisting one
the corpus already holds (permitted). An ordinary item mutation, the retype ref remap
(`_services/_retype.py:308`) and the retirement unlink (`_services/_retirement.py:124-130`) all
rewrite existing refs and must keep working, or the recovery sequence this whole change exists
to enable cannot be performed.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Repair canonicalises the file, not only the index

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Make `sq repair` (`src/squads/_services/_maintenance.py:1498`, rebuilding through
`_rebuild_index_from_disk`) write back every file whose folded frontmatter differs from its raw
frontmatter, so the encoding invariant A1's safety rests on is enforced by a command the
adopter already runs rather than asserted.

The fold keeps its single implementation and its resolved-default argument
(`fold_legacy_kinds`, `_models/_item.py:124`) — nothing new is stored, and `_models/` gains no
vocabulary. This is a write the rebuild already holds the data to make.

Two invariants are not negotiable here: markdown is written before the index commit, as
everywhere else in the store; and the operation converges — a second repair over the same
corpus is byte-identical. A run over a corpus that needs no correction must write no file at
all.

Repair keeps its documented bypass and stays runnable in every state the remaining
cross-checks can refuse over. It is the verb that creates the locked state today by folding a
legacy map under a renamed spec and storing the spelled kind; after this it is the verb that
prevents it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct the three refusal and hint messages

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Three messages state something a reader disproves by running a command.

1. `spec_refusal` (`_loader.py:131`) closes with "`sq workflow lint` … is the one command that
   still runs while this stands". Both `sq repair` (through its bypass) and `sq check` (through
   its bundled-spec fallback) run. The sentence goes; the file, cause and fix-hint structure the
   message exists for stays. This text is shared by every unloadable-override family, so the
   correction reaches the type/status, prefix/folder and badge refusals too — that is the whole
   of what those families change.
2. The ref-kind refusal (`_loader.py:743-747`) ends "remove those refs first (no command
   rewrites a corpus's ref kinds)" — an ordering it never completes, and a claim repair now
   disproves. State the sequence, and name `sq repair` as what canonicalises a legacy-map edge.
3. Lint's own fix hint for the same family (`_loader.py:1206-1211`) repeats that claim
   verbatim. It travels with the other two, or the two surfaces disagree about the same file.

The adopter-facing recovery, driven and performable with shipped verbs and no hand-edited
file: revert the override edit, `sq repair`, mutate the affected item once so its file is
rewritten canonical, re-apply the rename. Under the bounded refusal the revert is not needed at
all, because the removal verb is not locked — say the shorter thing where the shorter thing is
true.

Check whether any generated or adopter-facing text repeats the retired claims (the workflow
cheatsheet, the override docs) and correct it there too; regenerate any golden the wording
change touches.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Drive the recovery sequence end to end in tests

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
No test in the suite exercises the ref-kind axis through `validate_against_index` — grepped
across `tests/`, the three files that touch that function do not reach this family. The lock
therefore lifts without a single test turning red, and the bounded behaviour will regress in
either direction unless it is pinned here.

Pin the boundary from both sides, table-driven over the two shapes rather than one example
each: a natively spelled kind that the override drops, and a pre-0.2 legacy-mapped edge whose
recorded name stops equalling the default after a rename. The lock is not legacy-specific and
the coverage must show that.

Per shape assert what refuses (`sq workflow lint`; adding a *new* ref of the undeclared kind)
and what runs (a read command, `sq check` reporting the per-item warn with no "workflow config
invalid" line, `sq repair`, `sq <type> <n> ref rm`, an ordinary mutation of the affected item,
and `sq graph` traversing the edge with a null semantic).

Then drive the whole recovery as one test: revert, repair, mutate, re-apply the rename — lint
clean, check clean, both edges reading as the new default, no item file touched by hand. Add
repair's own convergence case: a corpus needing correction is rewritten once, a second repair
is byte-identical, and a corpus needing none is not written at all.

Name the files by behaviour, not by ticket.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T11:53:06Z] Olivia Lead:
  - Standalone: FEAT-790 is Done with every child Done, so parenting a Ready task under it would reopen a closed feature to carry sequencing. The ADR-775 implements ref and the BUG-827 fixes ref carry the context; medium priority sequences it with the rest of the 0.14 ref-kind work rather than ahead of it.
  - Scoping note for whoever picks it up: the write gate, the check finding and the null-semantic read already exist and were verified in place. The delivered change is mostly subtractive at the load boundary, plus repair writing the file back and three message corrections.
<!-- sq:discussion:end -->
