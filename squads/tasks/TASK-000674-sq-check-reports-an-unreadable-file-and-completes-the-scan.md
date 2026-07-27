---
id: TASK-674
sequence_id: 674
type: task
title: sq check reports an unreadable file and completes the scan
status: Draft
author: tech-lead
refs:
- TASK-673:depends-on
- ADR-663:implements
description: Report a corrupt item file as a per-file issue and keep scanning, without
  inventing a phantom reconciliation error; repair and renumber keep aborting.
subentities:
- local_id: ST1
  title: Third scan state and the reconciliation predicates
  status: Todo
- local_id: ST2
  title: Tests that the scan continued and no phantom appeared
  status: Todo
created_at: '2026-07-27T22:26:00Z'
updated_at: '2026-07-27T22:26:41Z'
---
<!-- sq:body -->
Today one unreadable file aborts `sq check`'s whole scan, so the rest of the board stays unseen —
the operator learns about file 1 of 400 and nothing else. Report it as a per-file issue and keep
scanning.

Targets **0.13**. It changes `check`'s contract: a run that previously stopped at the first bad file
now completes and reports every issue it found, including that one.

## Why `check` and not `repair`

The asymmetry is the point, and it is not an oversight to be tidied up later:

- **`check` should continue.** It is a reporter. Its job is to tell you everything wrong with the
  board in one pass, and a reporter that stops at the first problem is failing at exactly the moment
  it is most needed. A corrupt file is *one more finding*, not a reason to stop counting.
- **`repair` must keep aborting.** It rebuilds the index *from* the markdown, so continuing past a
  file it cannot read means rebuilding from a board it cannot fully read — and the file it skipped
  drops out of the index, which is the silent item-loss shape this whole line of work exists to
  close. Refusing to rebuild is the safe response, and it stays.

Anyone reading this later will be tempted to make the two consistent. Don't. `renumber` and
`repad` sit with `repair` for the same reason: they rewrite identity across the whole board and
cannot do that correctly with a file they cannot read.

## How it fits the existing model

ADR-663 §3 partitions `check`'s issues into **single-source** (derived from one file's own text —
reported as-is, "exactly as true as the one read that produced them") and **cross-source**
(candidates confirmed by one re-read). An unreadable file is squarely single-source: one file, one
read, one certain fact. So this is not a new category — it is the case nobody enumerated, handled the
way §3 already says its category should be.

## The part that is not contained

`_scan_for_check` has exactly one consumer, so *continuing* is safe for the caller. But the scan's
**output** is consumed by more than the scan, and a naive "skip the bad file and carry on" is wrong:

`_confirm_cross_source` computes `missing_seqs = set(index.items) - set(on_disk)`, and
`index_reconciled` turns that into **"in index but no markdown file found"** at error level. If an
unreadable file is simply omitted from `on_disk`, `check` invents a phantom error claiming the file
is gone — when it is right there, merely unparseable. That is a worse report than the crash it
replaces: it points the operator at the wrong problem, and `sq repair` is the documented remedy for
it, which in this case would drop the item.

It also breaks the confirm round. That claim is cross-source, so it goes to the confirm pass, which
re-reads the candidate at the path the fresh index gives — the same unreadable file. Either it raises
again (the crash returns, just later) or it swallows the failure and *confirms* the phantom.

**So the scan needs a third state, not a skip:** *present but unparseable*, distinct from both
*present and parsed* and *absent*. Reconciliation must treat it as **present** — the file exists, so
"no markdown file found" is false — while every predicate that needs the file's *content* (drift,
and the body-reading validators) skips it, because there is no content to compare.

**Keying it is the wrinkle worth deciding up front.** `on_disk` is keyed by sequence number taken
from the frontmatter `id` — which is exactly what cannot be read here. The filename stem carries the
same number (`TASK-000673-…`), and `repad` already parses stems for this reason, but a filename is a
weaker source than frontmatter and the two can disagree. The call:

- key the unparseable entry by the sequence number parsed from its **filename**, and treat it as
  present for reconciliation;
- if the stem does not parse either, fall back to suppressing the missing-direction reconciliation
  claim for the whole run rather than emitting one that might be false. Coarse, but a suppressed
  true claim is recoverable — the parse issue is still reported and still names the file — while a
  phantom error sends the operator to `sq repair`.

Worth the architect's nod if he is already in this seam: whether a present-but-unparseable file
counts as "present" for `index_reconciled` is a small extension to §3's reconciliation model, not
just an implementation detail. It does not block — the alternative (suppress) is specified above.

## Dependency

Lands after TASK-673. That work turns the raw `yaml.YAMLError` into a `SquadsError` naming the file,
which is the precondition for catching it *by a type the scan is allowed to catch* and turning it
into a `CheckIssue`. Without it this task would be catching a third-party parser exception in the
service layer.

## Out of scope

- **Recovery.** No quarantine, no partial parse, no repair attempt. `check` says which file and why.
- **`repair`, `renumber`, `repad`.** They keep aborting, for the reason above.
- **The exit code contract.** An unreadable file is an error-level issue, so `check` exits non-zero
  exactly as it does for any other error — that is unchanged, and no new exit code is introduced.

## Acceptance

- A board with one unreadable item file produces a complete `check` run: the corrupt file is
  reported as an error-level issue naming it, **and** every other issue on the board is reported in
  the same run. Assert a second, unrelated issue elsewhere on the board is present in the output —
  that is what proves the scan continued rather than stopping politely.
- No phantom "in index but no markdown file found" for the unreadable file.
- The confirm round does not re-raise on the unreadable file, and does not confirm a phantom.
- Drift and the body-reading validators stay silent for that item rather than guessing.
- Two unreadable files are both reported, not just the first.
- `sq repair`, `sq renumber` and `sq migrate repad` still refuse on the same board, cleanly — pinned
  by test, so the asymmetry cannot be "fixed" by accident.
- `check`'s exit code on a board whose only problem is the unreadable file is the ordinary
  error-level exit, asserted bare rather than through a pipe.
- A clean board is byte-identical in output and exit code to before.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 674 add-subtask "<title>"`; track with `sq task 674 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Third scan state and the reconciliation predicates |  |
| ST2 | Todo |  | Tests that the scan continued and no phantom appeared |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Third scan state and the reconciliation predicates

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The third state in the scan, and the reconciliation predicates that consume it.

These are one unit of work, not two: adding the state without teaching reconciliation about it
produces a phantom "in index but no markdown file found" — a worse report than the crash it
replaces. There is no useful intermediate to land.

**In `_scan_for_check`.** Catch the parse failure per file (a `SquadsError` once TASK-673 lands —
not a bare `yaml` exception), record an error-level `CheckIssue` naming the file, and continue to the
next one. The failing file goes into neither `on_disk` nor `bodies`: there is no frontmatter and no
usable content. Instead it is recorded in a third collection the scan returns — present, unparseable,
keyed by the sequence number parsed from its **filename** stem (`repad`'s stem parsing is the
precedent; the frontmatter `id` is precisely what cannot be read).

**In reconciliation.** `_confirm_cross_source` computes `missing_seqs = set(index.items) -
set(on_disk)`. An unparseable file must not land in that set — the file exists, so the claim would be
false. Subtract the unparseable set as well. The same applies to the orphan direction: an unparseable
file is not evidence of an unindexed item, because its real id is unknown.

**In the confirm round.** The re-read of a candidate must tolerate the same parse failure without
re-raising — otherwise the crash comes back, one pass later. A candidate whose file cannot be parsed
on the confirm read is not confirmed: the run already reports the parse issue for that file, and
stacking a speculative second claim on top of it helps nobody.

**Everywhere else.** Drift and the body-reading validators (`subentity_body_written`,
`no_status_banner`) need the file's content, which does not exist here — they stay silent for that
item. `bodies.get(seq)` already returns `None` and they already degrade to silence, so verify that
rather than adding branches.

**If the filename stem does not parse either**, fall back to suppressing the missing-direction
reconciliation claim for the whole run. A suppressed true claim is recoverable — the parse issue
still names the file — while a phantom error sends the operator to `sq repair`, which for an
unreadable file drops the item.

Acceptance:
- The scan returns a distinct present-but-unparseable set; the file is in neither `on_disk` nor
  `bodies`.
- No reconciliation claim, in either direction, is emitted for an unparseable file.
- The confirm round tolerates an unparseable candidate without raising and without confirming.
- The stem-unparseable fallback is implemented and its reasoning recorded at the call site.
- `repair`, `renumber` and `repad` are untouched by this change.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Tests that the scan continued and no phantom appeared

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Pin that the scan actually continued, that no phantom appeared, and that the asymmetry holds.

**It continues.** The load-bearing test is not "the corrupt file is reported" — it is that
*everything else still is*. Seed a board with one unreadable item file **and** a second, unrelated
issue on a different item (an unwritten sub-entity body, or a real status drift), then assert both
appear in one run. A test that only asserts the corrupt file is reported would pass against an
implementation that reports it and then stops.

Two unreadable files, both reported — the loop must not bail after the first.

**No phantom.** Assert the output carries no "in index but no markdown file found" for the
unreadable item, in both the first pass and after the confirm round. This is the regression that
matters most: it is the failure mode that would send an operator to `sq repair` and cost them the
item.

**The confirm round survives it.** Drive a run where the unreadable file is also a drift candidate's
neighbour — a real drift on item A, an unreadable item B — so the candidate set is non-empty and the
confirm round runs with B present on disk. Assert A's drift is still confirmed and reported, and that
B produces only its parse issue.

**The asymmetry is pinned, not assumed.** On the same board, assert `sq repair`, `sq renumber` and
`sq migrate repad` still refuse cleanly. Without these, a later change "for consistency" turns
`repair` into something that rebuilds the index from a board it cannot fully read and drops the item.
Say so in a comment on the test, so its purpose survives someone reading it cold.

**Exit code and clean board.** `check`'s exit code with only the unreadable file as a problem is the
ordinary error-level exit — asserted bare (`cmd >/dev/null 2>&1; echo $?`), since a pipeline masks
it. A clean board produces byte-identical output and exit code to before.

Name tests by the behaviour they pin, never by a ticket id.

**Changelog.** `check`'s behaviour changes visibly, so it needs an adopter-facing line under the
unreleased section: `sq check` now reports an unreadable item file and continues scanning the rest of
the board, instead of stopping at the first one. Adopter wording only — no ticket ids, no
repo-process detail.

Acceptance:
- A run with an unreadable file and a second unrelated issue reports both.
- Two unreadable files are both reported.
- No reconciliation phantom, before or after the confirm round.
- A real drift elsewhere is still confirmed and reported in the same run.
- `repair`/`renumber`/`repad` refusal is pinned by test with its reason recorded.
- Exit codes asserted bare; clean board unchanged.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T22:26:41Z] Olivia Lead:
  - Cut from the scope note I left on TASK-673. The asymmetry is preserved in the body with its reasoning: check continues because it is a reporter and a reporter that stops at the first problem fails when it is most needed; repair/renumber/repad keep aborting because they rebuild identity from the markdown and cannot do that from a board they cannot fully read. An acceptance criterion pins the refusal by test so nobody later 'fixes' the inconsistency into unsafety.
  - Refs: implements ADR-663 rather than related — §3 already classifies single-source issues as reported-as-is, and an unreadable file is squarely single-source, so this handles the case nobody enumerated the way §3 says its category should be handled. depends-on TASK-673: that work turns the raw yaml error into a SquadsError, which is what makes it catchable by a type the service layer is allowed to catch.
  - It is NOT as contained as it looks. `_scan_for_check` has one consumer, so continuing is safe for the caller — but its OUTPUT feeds `_confirm_cross_source`, where `missing_seqs = set(index.items) - set(on_disk)` turns a skipped file into a phantom error-level 'in index but no markdown file found'. That is worse than the crash: it points at the wrong problem and its documented remedy is `sq repair`, which for an unreadable file drops the item. The confirm round then re-reads the same unparseable file and either re-raises or confirms the phantom. So the scan needs a third state — present-but-unparseable, treated as present for reconciliation, skipped by the content predicates — with the keying problem (no readable id; filename stem as the fallback source) decided in the body rather than left to the dev.
<!-- sq:discussion:end -->
