---
id: TASK-674
sequence_id: 674
type: task
title: Unreadable files degrade per file instead of aborting the command
status: Done
author: tech-lead
assignee: python-dev
refs:
- TASK-673:depends-on
- ADR-663:implements
- REV-671:addresses
description: check keeps scanning, repair rebuilds from what it can read and carries
  the unreadable item's existing entry forward, and the board and memory listings
  show every entry they can read.
subentities:
- local_id: ST1
  title: Third scan state and the reconciliation predicates
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Tests that the scan continued and no phantom appeared
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Repair rebuilds and carries the unreadable item forward
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Board and memory listings degrade per file
  status: Done
  assignee: python-dev
created_at: '2026-07-27T22:26:00Z'
updated_at: '2026-08-03T15:47:38Z'
---
<!-- sq:body -->
One unreadable file currently takes down a whole command — `sq check` stops at the first bad file and
never reports the other 650 items, `sq repair` refuses to rebuild anything at all, and `sq board
list` / `sq memory list` show nothing. Make each of them degrade per file instead: report what it
could not read, and do its job on everything else.

Targets **0.13**. It changes what these commands do on a board that has a corrupt file — a run that
previously stopped now completes and reports.

Addresses REV-671 F16. The `check` half was scoped first; F16 added `repair`, and the listing readers
came from the same observation.

## Why per-file, and why `repair` is the important half

`check` is a reporter. Its job is to tell you everything wrong with the board in one pass, and a
reporter that stops at the first problem fails at exactly the moment it is most needed. ADR-663 §3
already classifies **single-source** issues — derived from one file's own text — as reported as-is;
an unreadable file is squarely that, so this is the case nobody enumerated, handled the way §3
already says its category should be.

`repair` matters more, because **blocking `repair` blocks the remedy**. It is the documented fix for
every skew this line of work is about, and one bad file makes it unavailable board-wide. The
realistic trigger is not exotic: squad data is committed to git and this tool is explicitly
multi-user, so an unresolved merge conflict inside one item's `---` block produces exactly this — at
the moment an adopter most wants repair to work. Their only remaining move is to hand-edit an
sq-managed `.md`, which this project's own instructions forbid. That is a recovery story with a hole
in it.

## How `repair` continues without dropping the item

The reason `repair` was originally scoped to keep aborting is real and must not be lost: it rebuilds
the index **from** the markdown, so "skip what you cannot read and rebuild from the rest" drops the
unreadable item out of the index entirely — it stops resolving by `show`, disappears from `sq list
-a`, and its file becomes an orphan. That is the same disappearance this release spent its whole
effort closing, and simply reporting it afterwards does not undo it.

Neither aborting nor dropping is necessary, because **repair already holds the previous index**. It
loads it before rebuilding, to preserve the counter high-water mark and the padding floor and to
compute its missing-items report. So the third option is available and is the one to build:

> Rebuild from every file that parses. For each file that does not, **carry forward that item's
> entry from the previous index** unchanged, and report the file as unreadable.

Nothing disappears, nothing is fabricated — the carried entry is exactly what was already there, and
a stale entry is strictly better than a deleted one. When the user fixes the file, the next `repair`
picks up the real values.

Two cases where there is nothing to carry, both of which must be reported rather than papered over:

- the file is unreadable **and** has no entry in the previous index (never indexed, or the index was
  rebuilt since) — leave it unindexed and report it as unreadable. `check` does not additionally
  claim it is on-disk-but-not-indexed: that claim would have to guess the file's id from its
  filename, and reporting a guess as fact is exactly what this design otherwise refuses to do;
- the previous index is itself missing or unreadable — `repair` already tolerates that and starts
  from nothing, so the same applies.

**`repair --renumber` and `sq migrate repad` still refuse**, and the narrower reason is sharper than
the old blanket one: they rewrite identity across every file, and a file whose id cannot be read
cannot be correctly renumbered or repadded. Pin that by test — the asymmetry is now subtle enough
that someone will otherwise "finish the job".

## The listing readers

`sq board list` and `sq memory list` fail wholesale on one bad notice or entry: the corrupt file
takes the entire listing with it. Same reporter-stops-at-the-first-problem shape, and it matters more
than its size suggests — this project's own agents run both at the start of every session, so one bad
notice greets an agent with nothing at all.

Same treatment: skip the unreadable file, name it in the output, list the rest.

## The part that is not contained

`_scan_for_check` has exactly one consumer, so *continuing* is safe for the caller. But the scan's
**output** is consumed by more than the scan, and a naive "skip the bad file and carry on" is wrong:

`_confirm_cross_source` computes `missing_seqs = set(index.items) - set(on_disk)`, and
`index_reconciled` turns that into **"in index but no markdown file found"** at error level. If an
unreadable file is simply omitted from `on_disk`, `check` invents a phantom error claiming the file
is gone — when it is right there, merely unparseable. That is a worse report than the crash it
replaces: it points the operator at the wrong problem, and its documented remedy is `sq repair`.

It also breaks the confirm round. That claim is cross-source, so it goes to the confirm pass, which
re-reads the candidate at the path the fresh index gives — the same unreadable file. Either it raises
again (the crash returns, just later) or it swallows the failure and *confirms* the phantom.

**So the scan needs a third state, not a skip:** *present but unparseable*, distinct from both
*present and parsed* and *absent*. Reconciliation must treat it as **present** — the file exists, so
"no markdown file found" is false — while every predicate that needs the file's *content* (drift,
and the body-reading validators) skips it, because there is no content to compare.

**Keying it is the wrinkle worth deciding up front.** `on_disk` is keyed by sequence number taken
from the frontmatter `id` — which is exactly what cannot be read here. The filename stem carries the
same number (`TASK-000674-…`), and `repad` already parses stems for this reason, but a filename is a
weaker source than frontmatter and the two can disagree. The call:

- key the unparseable entry by the sequence number parsed from its **filename**, and treat it as
  present for reconciliation;
- if the stem does not parse either, fall back to suppressing the missing-direction reconciliation
  claim for the whole run rather than emitting one that might be false. Coarse, but a suppressed
  true claim is recoverable — the parse issue is still reported and still names the file — while a
  phantom error sends the operator to `sq repair`.

Whether a present-but-unparseable file counts as "present" for `index_reconciled` is a small
extension to §3's reconciliation model; worth the architect's nod if he is in this seam, but it does
not block — the fallback above is specified either way.

## Dependency

Lands after the read-path guard work, which turns raw parser and decode exceptions into a
`SquadsError` naming the file. That is the precondition for catching the failure *by a type the
service layer is allowed to catch* and converting it into a per-file report. Without it this task
would be catching third-party exceptions in the service layer.

## Out of scope

- **Recovery.** No quarantine, no partial parse, no lenient decode. The commands say which file and
  why; the user fixes it.
- **The exit-code contract.** An unreadable file is an error-level issue, so `check` exits non-zero
  exactly as it does for any other error. No new exit code.

## Acceptance

- **`check` completes.** A board with one unreadable item file reports it as an error-level issue
  naming it **and** reports every other issue on the board in the same run. Assert a second,
  unrelated issue elsewhere is present in the output — that is what proves the scan continued rather
  than stopping politely. Two unreadable files are both reported, not just the first.
- **No phantom** "in index but no markdown file found" for the unreadable file, in the first pass or
  after the confirm round; the confirm round does not re-raise on it and does not confirm a phantom.
  Drift and the body-reading validators stay silent for that item rather than guessing.
- **`repair` rebuilds.** On the same board it rebuilds from every readable file, reports the
  unreadable one, and **the unreadable item is still in the index afterwards, with its previous
  entry intact** — still resolvable by `show`, still in `sq list -a`. This is the criterion that
  distinguishes the fix from the naive version; without it the command "succeeds" by losing the item.
- The no-previous-entry case leaves the item unindexed and reports it, rather than inventing one.
- **`repair --renumber` and `sq migrate repad` still refuse**, pinned by test with the reason in a
  comment, so the remaining asymmetry cannot be "fixed" into unsafety.
- **`sq board list` and `sq memory list`** each list every readable entry and name the unreadable one.
- Exit codes asserted on a bare invocation (`cmd >/dev/null 2>&1; echo $?`); a pipeline masks them.
- A clean board is byte-identical in output and exit code to before, across every command touched.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 674 add-subtask "<title>"`; track with `sq task 674 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Third scan state and the reconciliation predicates |  |
| ST2 | Done | python-dev | Tests that the scan continued and no phantom appeared |  |
| ST3 | Done | python-dev | Repair rebuilds and carries the unreadable item forward |  |
| ST4 | Done | python-dev | Board and memory listings degrade per file |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Third scan state and the reconciliation predicates

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
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
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Pin that each command actually continued, that no phantom appeared, and that the refusals that remain
are deliberate.

**`check` continues.** The load-bearing test is not "the corrupt file is reported" — it is that
*everything else still is*. Seed a board with one unreadable item file **and** a second, unrelated
issue on a different item (an unwritten sub-entity body, or a real status drift), then assert both
appear in one run. A test that only asserts the corrupt file is reported would pass against an
implementation that reports it and then stops. Two unreadable files, both reported.

**No phantom.** Assert the output carries no "in index but no markdown file found" for the unreadable
item, in the first pass and after the confirm round. This is the regression that matters most: it is
the failure mode that would send an operator to `sq repair` for a file that is right there.

**The confirm round survives it.** Drive a run with a real drift on item A and an unreadable item B,
so the candidate set is non-empty and the confirm round runs with B present on disk. Assert A's drift
is still confirmed and reported, and that B produces only its unreadable-file issue.

**`repair` keeps the item.** On the same board, assert repair completes, names the unreadable file,
**and** that the unreadable item is still resolvable by `show` and still present in `sq list -a`
afterwards with its previous values. Without this assertion the naive implementation — skip it and
rebuild from the rest — passes every other test in this set while silently dropping the item. Add the
no-previous-entry case too: unindexed and reported, nothing invented.

**The remaining refusals are deliberate.** Assert `repair --renumber` and `sq migrate repad` still
refuse on the same board, and say in a comment on the test what it protects: they rewrite identity
across every file and cannot do that for a file whose id they cannot read. The asymmetry is now
subtle — `repair` continues, `repair --renumber` does not — so without a test carrying its reason,
someone will reconcile them.

**Listings.** A folder with one unreadable notice still lists the rest and names the bad one; same for
memory entries in both list and search; ordering of survivors unchanged.

**Exit codes and the clean board.** `check`'s exit code with only the unreadable file as a problem is
the ordinary error-level exit — asserted bare (`cmd >/dev/null 2>&1; echo $?`), since a pipeline masks
it. A clean board produces byte-identical output and exit codes to before, across every command this
task touches.

Name tests by the behaviour they pin, never by a ticket id.

**Changelog.** Behaviour changes visibly on four commands, so it needs an adopter-facing line under
the unreleased section: a file `sq` cannot read no longer stops the whole command — `sq check` reports
it and keeps checking the rest of the board, `sq repair` rebuilds from every file it can read while
leaving the unreadable item's existing entry in place, and the board and memory listings show every
entry they can read. Adopter wording only — no ticket ids, no repo-process detail.

Acceptance:
- A `check` run with an unreadable file and a second unrelated issue reports both; two unreadable
  files are both reported.
- No reconciliation phantom, before or after the confirm round; a real drift elsewhere is still
  confirmed.
- `repair` completes and the unreadable item survives in the index, asserted through `show` and
  `list -a`.
- `repair --renumber` / `repad` refusal pinned with its reason recorded.
- Listings degrade per file, ordering intact.
- Exit codes asserted bare; clean board unchanged.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Repair rebuilds and carries the unreadable item forward

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`sq repair` rebuilds from what it can read, and carries forward what it cannot.

Today one unreadable file makes repair refuse board-wide — which blocks the documented remedy for
every skew in this line of work, at the moment an adopter most needs it.

**The naive version is wrong** and must not be built: "skip the unreadable file and rebuild from the
rest" drops that item out of the index — it stops resolving by `show`, disappears from `sq list -a`,
and its file becomes an orphan. Reporting it afterwards does not undo the disappearance. That is the
loss shape this whole line of work closed.

**Build the carry-forward instead.** `repair` already loads the previous index before rebuilding, to
preserve the counter high-water mark and the padding floor and to compute its missing-items report —
today it keeps only a `seq -> id` map from it. Keep the previous items themselves, and:

- rebuild from every file whose frontmatter parses, as now;
- for each file that does not parse or decode, carry that item's **previous index entry** forward
  unchanged;
- report every unreadable file in the result, so the operator knows the carried entries are stale.

A carried entry is exactly what was already in the index — nothing fabricated, nothing inferred — and
a stale entry is strictly better than a deleted one. The next `repair` after the user fixes the file
picks up the real values.

Two cases have nothing to carry, and both are reported rather than papered over: a file that is
unreadable *and* absent from the previous index (leave it unindexed and report it as unreadable —
`check` does not also claim on-disk-but-not-indexed, since that claim would mean guessing the
file's id from its filename and reporting the guess as fact), and a previous index that is itself
missing or unreadable (repair already tolerates that and starts from nothing).

The per-file catch goes where repair reads frontmatter during its disk scan, and it catches the
`SquadsError` the read-path guards raise — not a third-party parser or codec exception.

**`repair --renumber` and `sq migrate repad` keep refusing.** The reason is narrower than the old
blanket one and worth stating at the call site: they rewrite identity across every file, and a file
whose id cannot be read cannot be correctly renumbered or repadded. Do not extend the carry-forward
to them.

Acceptance:
- On a board with one unreadable item file, `repair` rebuilds from every readable file and completes.
- The unreadable item is still in the index afterwards with its previous entry intact — resolvable by
  `show`, present in `sq list -a`.
- Every unreadable file is named in the result.
- The no-previous-entry case leaves it unindexed and reports it; nothing is invented.
- The counter high-water mark and padding floor are preserved exactly as they are today.
- `repair --renumber` and `sq migrate repad` still refuse, with the reason recorded at the call site.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Board and memory listings degrade per file

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
The listing readers: one bad file must not empty the whole list.

`sq board list` and `sq memory list` read every notice or entry in a folder and parse each one. A
single unreadable file takes the entire listing down — the operator sees no notices at all, not "one
notice is broken".

It matters more than its size suggests: this project's own agents are instructed to run both at the
start of every session, so one corrupt notice greets an agent with nothing, on a command whose whole
purpose is to surface team-wide context.

Same treatment as the scan: catch the read/parse failure per file (a `SquadsError` from the read-path
guards), skip that entry, name it in the output, and list everything else. The listing keeps its
ordering; a skipped entry does not shift or renumber the ones around it in any way the user could
mistake for the real order.

The relevant seams are `_board/_store.py`'s all-notices read and `_memory/_store.py`'s entry
list/search reads. Derive the exact set from a fresh grep rather than this list — the read-path work
has been moving these files.

Single-item reads (`sq memory <role> show <slug>`) are a different case and stay as they are: there
is no "rest of the list" to preserve, so failing cleanly with the file named is already the right
answer.

Acceptance:
- A folder containing one unreadable notice still lists every other notice, and names the unreadable
  one.
- Same for memory entries, in both list and search.
- Ordering of the surviving entries is unchanged from a clean board.
- A single-item read still fails cleanly, unchanged.
- A clean board produces byte-identical output to before.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T22:26:41Z] Olivia Lead:
  - Cut from the scope note I left on TASK-673. The asymmetry is preserved in the body with its reasoning: check continues because it is a reporter and a reporter that stops at the first problem fails when it is most needed; repair/renumber/repad keep aborting because they rebuild identity from the markdown and cannot do that from a board they cannot fully read. An acceptance criterion pins the refusal by test so nobody later 'fixes' the inconsistency into unsafety.
  - Refs: implements ADR-663 rather than related — §3 already classifies single-source issues as reported-as-is, and an unreadable file is squarely single-source, so this handles the case nobody enumerated the way §3 says its category should be handled. depends-on TASK-673: that work turns the raw yaml error into a SquadsError, which is what makes it catchable by a type the service layer is allowed to catch.
  - It is NOT as contained as it looks. `_scan_for_check` has one consumer, so continuing is safe for the caller — but its OUTPUT feeds `_confirm_cross_source`, where `missing_seqs = set(index.items) - set(on_disk)` turns a skipped file into a phantom error-level 'in index but no markdown file found'. That is worse than the crash: it points at the wrong problem and its documented remedy is `sq repair`, which for an unreadable file drops the item. The confirm round then re-reads the same unparseable file and either re-raises or confirms the phantom. So the scan needs a third state — present-but-unparseable, treated as present for reconciliation, skipped by the content predicates — with the keying problem (no readable id; filename stem as the fallback source) decided in the body rather than left to the dev.
- [2026-07-27T22:46:33Z] Catherine Manager:
  - Adjacent follow-up from the read-path work: the UTF-8 decode guard means one bad byte in one notice fails the whole sq board list, and likewise sq memory list — the same reporter-stops-at-the-first-problem shape this ticket rejects for check. This ticket covers check only. Worth extending to the listings; agents run both at session start.
- [2026-07-27T23:58:06Z] Olivia Lead:
  - Amended rather than split — F16 folded in here. A second ticket would have contradicted this one outright: the previous scope carried an acceptance criterion pinning that `repair` REFUSES, by test. Same functions, same third-state machinery, same test fixtures. Retitled and rescoped: it now covers check, repair, and the board/memory listings.
  - The F16-vs-674 tension resolves to a third option neither stated. My original reason for repair aborting stands — 'skip and rebuild from the rest' DROPS the unreadable item from the index (gone from show, gone from list -a, orphan file left), which is the disappearance this release closed. But repair already loads the previous index for the counter high-water mark and padding floor, so it can carry that item's existing entry forward unchanged and report the file as unreadable. Nothing disappears, nothing is fabricated, and the next repair after the user fixes the file picks up the real values. Acceptance pins it: the naive version passes every other test in the set while silently losing the item, so there is an explicit 'still resolvable by show, still in list -a' criterion.
  - Also folded: board list and memory list degrading per file (ST4) — one bad notice currently empties the whole listing, and our own agents run both at session start. And `repair --renumber`/`repad` keep refusing, with the sharper reason (they rewrite identity across every file and cannot renumber one whose id they cannot read), pinned by a test carrying that reason in a comment — the asymmetry is subtle now that repair itself continues.
- [2026-08-03T08:32:43Z] Elias Python:
  - Implemented ST1-4: third scan state (present-but-unparseable, keyed by filename stem) + confirm-round tolerance in _services/_maintenance.py; repair carries the previous index entry forward per-file (SquadsDB carried via known_corpus lookup), never dropping an unreadable item; board/memory listings return (entries, unreadable) tuples and degrade per file; repad/renumber preserved refusal via an explicit preflight scan. Extended the read-path guard (_aio.read_text) to wrap non-decode OSError (permission denied) into a new UnreadableFileError, needed to cover the permissions falsification shape.
- [2026-08-03T08:32:44Z] Elias Python:
  - Falsified across 3 shapes (permission-denied via chmod 000, invalid UTF-8 byte, malformed-but-closed YAML) x 4 commands in tests/service/test_unreadable_files_degrade_per_file.py + tests/cli/test_unreadable_files_degrade_per_file_cli.py; updated the two TASK-673 clean-failure test files' 4 now-superseded assertions (check/repair/board-list/memory-list degrade instead of aborting; renumber/sync/memory-show/config still abort, unchanged). CHANGELOG updated. Gates clean: pyright, ruff check, ruff format --check, tests/meta + tests/service+cli+integration+unit all green (one pre-existing unrelated flaky assertion re: Rich line-wrapping in test_undecodable_squad_files_fail_cleanly.py, confirmed present before my changes via git stash).
- [2026-08-03T08:36:43Z] Catherine Manager:
  - Landed and verified by driving it, not from the report: sq check names the bad file with its byte offset and continues, both items still listed; sq repair reports it with an accurate remedy and the item count is unchanged, so the previous entry really is carried forward rather than dropped. Full suite 2414 passed / 6 skipped, all gates clean.
<!-- sq:discussion:end -->
