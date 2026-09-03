---
id: TASK-824
sequence_id: 824
type: task
title: 'Rebuild reporting and durability: honest counts, atomic writes'
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: low
refs:
- REV-823:addresses
- TASK-822
- MILE-836:targets
description: Report restorations and drops as two counts rather than a net delta,
  write both documents atomically, and let the release gate's success line say what
  only it verified
subentities:
- local_id: ST1
  title: Report restored and dropped as two counted sets
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Write both documents atomically in both scripts
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST3
  title: Let the release gate's success line state what it verified
  status: Done
  assignee: python-dev
  story: US1
created_at: '2026-08-26T00:11:27Z'
updated_at: '2026-08-26T16:01:08Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US1 — REV-823's three remaining findings (F6, F7, F8), all in the content-store rebuild's
reporting and write path.

**Read the current shape, not the reviewed one.** REV-823 was driven against `2a81c06`. Its F1
through F5 are fixed and landed in `3fb7c38`, which reworked both scripts substantially — the
rebuild's discriminator became publication rather than "is this the running version", and line
numbers moved. Every citation below was re-verified against the tree as it stands after `3fb7c38`.

## Why these three are one task

They are the same surface: what the rebuild writes and what it tells the operator it did. F6 and F7
are adjacent lines in the same function; F8 is the success line in the sibling script that the same
operator reads in the same release step, immediately after. One dev pass, one set of tests, no file
collisions. Splitting F7 out would put a second developer inside
`scripts/seed_content_store.py:355-366` while F6's is already there.

## 1. The drop count is a net delta (F6)

`scripts/seed_content_store.py:360` computes `dropped = store_before_size - len(new_store)` and
`:363-366` reports it as `(N dropped — not in the closure of any index entry)`. That is a net size
change labelled as a count of deletions.

A rebuild that inserts — which is what recovery *is* — reports a negative drop. A rebuild that
restores one blob and drops another in the same run reports `0 dropped`, having just corrected a
shipped release's entry back to its tag and restored the blob behind it. The correction log carries
it; the summary line an operator reads at a release cut says nothing happened.

Count the two sets rather than the delta: blobs in the closure that were absent from the old store
(restored), and blobs in the old store outside the closure (dropped). Each on its own.

## 2. The two writes are neither atomic nor rolled back (F7)

`_write_json` (`:124-125`) is a bare `path.write_text`. The rebuild calls it twice in succession at
`:361-362` with nothing between them, and `_seed_version`'s own write pair at `:433-434` has the
same shape. So the docstring's `writes nothing at all, for any version` (`:50`) describes the
refusal path and not an interrupted run.

**Severity: keeping the reviewer's low, correcting the reason.** Two of the stated mitigants hold
and one does not:

- Holds: both documents are tracked in git, so `git checkout` is a complete recovery, and this is a
  dev-time script writing source files rather than a runtime path.
- Holds: the manifest-written/store-not state is diagnosable — it is an index naming hashes the
  store lacks, which is exactly what the whole-index `--check` widening catches, at exit 1, naming
  each `version:artifact` and pointing at `--rebuild`.
- **Does not hold:** "the store is a superset of the closure, not a subset, and no blob is lost" is
  true of the drop half only. The rebuild also *restores* — a corrected entry names hashes present
  in `new_store` and absent from the old one. Interrupt between the two writes on a recovery run and
  the index is rewritten to the corrected hashes while the store still lacks the blobs behind them.
  Nothing is lost from git, but the tree is left in the broken state the operator ran the rebuild to
  leave.

The genuinely undiagnosed state is narrower than "a half-written pair": a **truncated** JSON
document. `write_text` truncates before writing, and `_load_json` in both scripts parses with no
error handling, so a partial `content_store.json` (364 KB on this branch) surfaces as an unhandled
`JSONDecodeError` traceback rather than a diagnosis. That is the piece worth adding scope for.

Low is the right label and the fix should not wait on the label: the repository already has the
pattern in `src/squads/_index/_store.py` (temporary file plus `os.replace`), it is a few lines, and
it removes truncation entirely. Writing both documents to temporaries and replacing them one after
another is still not a single transaction — it narrows the window to two adjacent renames, which is
the honest claim to make and the one the docstring should then state.

## 3. The release gate's success line is indistinguishable from an ordinary check's (F8)

Driven against the current tree — the two lines are byte-identical:

    $ python3 scripts/gen_template_manifest.py --check
    manifest v0.14.0 is current (29 artifacts); store coverage verified across all 16 indexed
    version(s) (416 hash(es))
    $ python3 scripts/gen_template_manifest.py --release-gate
    manifest v0.14.0 is current (29 artifacts); store coverage verified across all 16 indexed
    version(s) (416 hash(es))

`release_gate` reaches the failure path (`:206-207`) and never the success path (`:222-228`); the
`orphan_note` clause only fires when orphans exist, and under the gate an orphan is a failure. So a
clean gate run never says it verified the one property only the gate adds. Pasted into a release
thread the two lines are the same evidence — the same defect class as F3, fixed one finding above.

The runbook compounds it: `SKILL-000508` §2 tells the operator what each *failure* means but never
what a clean gate line looks like, so an operator who typed `--check` by mistake reads a passing
line and concludes the gate ran.

Second half, same line: `416 hash(es)` is `sum(len(entry) for entry in manifest.values())` — index
references, not blobs. The store holds 85. Verified both numbers against the shipped documents.
Nothing in the wording lets an operator reconcile 416 with 85.

## Acceptance

1. The rebuild reports restored and dropped as two independently computed counts, each derived from
   set membership against the closure rather than from a size difference. A run that only restores
   reports a restore and zero drops; a run that does both reports both.
2. No reported count can be negative. Assert that directly — a negative count is the signature of
   the delta returning.
3. `_write_json` writes via a temporary file in the same directory plus `os.replace`, in **both**
   scripts. A crash mid-write leaves the previous document intact and never a truncated one.
4. Both documents are written to temporaries first and replaced one after the other, so an
   interruption cannot leave either file partially written.
5. The docstring's durability claim states what the implementation gives — no partial document, a
   two-rename window — rather than an unqualified "writes nothing at all", which describes the
   refusal path.
6. A truncated or unparseable manifest or store is diagnosed by name and path rather than raising a
   bare `JSONDecodeError` traceback, and names the recovery (`git checkout` on the two documents,
   then `--rebuild`).
7. Under `--release-gate`, a clean run's success line states the property only the gate verifies —
   orphan-free, over N stored blobs — and is distinguishable at a glance from `--check`'s.
8. The count is worded as what it is: index references over stored blobs, e.g.
   `416 index reference(s) over 85 stored blob(s)`.
9. `SKILL-000508` §2 shows what a clean `--release-gate` line looks like, so an operator can tell
   from the output which command actually ran.
10. `--check` and `--release-gate` still write nothing; assert both documents are byte-identical
    after each.
11. `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` clean; the full suite
    green; `python3 scripts/gen_template_manifest.py --check` clean and both documents unchanged
    against git afterwards.

## Ordering

No blocking dependency: TASK-822 is closed and the code these findings describe is landed.

One scheduling note rather than a dependency. The atomicity fix protects the exact step where the
runbook has the operator commit both documents together, so it is worth landing before the `v0.14.0`
tag rather than after — the priority here reflects severity, not the deadline.

## Out of scope

REV-823's F1 through F5 — fixed in `3fb7c38`. Any change to the rebuild's discriminator, its
all-or-nothing refusal, or which versions it sources from where: this task changes what is reported
and how it is written, never what is computed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 824 add-subtask "<title>"`; track with `sq task 824 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Report restored and dropped as two counted sets

<!-- sq:subtask:ST1:body -->
`scripts/seed_content_store.py:360` is `dropped = store_before_size - len(new_store)` — a size
delta wearing the label of a deletion count. Replace it with two set computations against the
closure the rebuild already has in hand:

- **restored**: hashes in `new_store` that were absent from the old store;
- **dropped**: hashes in the old store that are absent from `new_store`.

That needs the old store's keys, not just its length, so `store_before_size` at `:344` becomes the
loaded mapping (or its key set). Report both on the summary line at `:363-366`, each named for what
it is.

The case that motivates this is a run that does both at once — a shipped release's entry corrected
back to its tag, the blob behind it restored, and a stale dev-tree blob dropped in the same pass.
Today that prints `0 dropped` and reads as "nothing happened" at the exact moment the tool did its
headline job.

Test the three shapes separately: restore-only, drop-only, and both in one run. Assert on the two
counts, and assert neither can be negative — a negative count is the delta's signature and the
regression this subtask exists to prevent.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-26T09:07:32Z] Elias Python:
  - Replaced the net-delta drop count with two set computations (restored = new_store - old_store, dropped = old_store - new_store), reported independently on the summary line. Added restore-only, drop-only, and both-in-one-run tests plus a real --rebuild no-op run against the shipped documents.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write both documents atomically in both scripts

<!-- sq:subtask:ST2:body -->
`_write_json` is a bare `path.write_text` in both scripts —
`scripts/seed_content_store.py:124-125` and `scripts/gen_template_manifest.py:131-132`. Every
caller inherits it: the rebuild's pair at `seed_content_store.py:361-362`, the seed path's at
`:433-434`, and the generator's write mode at `gen_template_manifest.py:252-253`.

Use the pattern the repository already has in `src/squads/_index/_store.py`: write to a temporary
file in the **same directory** (so the replace stays on one filesystem), then `os.replace`. Same
directory matters — a temp file elsewhere makes the replace a cross-device copy and reintroduces the
window.

Then write both documents to their temporaries **before** replacing either, so an interruption
during serialization cannot leave one file new and the other old. The two renames remain two
operations; that is the honest residual and the docstring should say so rather than claiming more.

Correct the durability prose at `seed_content_store.py:50`. `writes nothing at all, for any version`
is a true statement about the refusal path being read as a promise about interruption. State what
ships: a refusal writes nothing, and any completed write leaves whole documents, never a partial
one.

Separately, give truncation a diagnosis. `_load_json` in both scripts parses with no error handling,
so a partial `content_store.json` surfaces as an unhandled `JSONDecodeError` traceback. Catch it,
name the file and the path, and name the recovery — `git checkout` on the two documents, then
`--rebuild`. Both files are tracked, so recovery is complete; the operator just has to be told.

Prove it: interrupt or fault-inject a write and assert the previous document survives intact and
parses. A test that only checks the happy path proves nothing here.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-26T09:07:40Z] Elias Python:
  - Split _write_json into _stage_json (write+fsync temp) and a rename step; added _write_json_pair which stages both documents fully before replacing either, cleaning up any already-staged sibling if a later stage fails. Applied to all three write-pair call sites in both scripts. _load_json now catches JSONDecodeError and prints a named diagnosis plus git checkout + --rebuild recovery instead of raising. Corrected the durability prose in the module docstring. Proved both with fault-injection tests (staging failure, interrupted-between-renames, and a real --rebuild run interrupted mid-write against the actual tracked documents).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Let the release gate's success line state what it verified

<!-- sq:subtask:ST3:body -->
`scripts/gen_template_manifest.py` threads `release_gate` into the failure path (`:206-207`) and
never into the success path (`:222-228`). The `orphan_note` clause only appears when orphans exist,
and under the gate an orphan is a failure — so a clean gate run and a clean check print the same
line. Driven against the current tree, they are byte-identical.

Orphan-freeness is the one property the gate adds. Under `--release-gate`, a clean run says it
verified it, over how many stored blobs. Someone pasting the line into a release thread should be
able to tell which command produced it.

Same line, second half: `keys_checked = sum(len(entry) for entry in manifest.values())` at `:223` is
counted in index references and printed as `hash(es)`. It reads 416 while the store holds 85 blobs,
and nothing in the wording reconciles them. Word it as what it counts — index references over stored
blobs.

Then close the loop in the runbook. `squads/agents/skills/SKILL-000508-releasing-squads.md` §2 tells
the operator what each gate *failure* means and never what a clean gate line looks like, so someone
who typed `--check` by mistake reads a passing line and moves on. Show the clean line. Edit it
through `sq`, not by hand — it is a managed skill document.

Assert both modes' success lines in tests, and assert they differ.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-26T09:07:47Z] Elias Python:
  - --release-gate's clean line now says 'release gate passed - orphan-free' explicitly; --check's stays as coverage-only, so the two are never byte-identical (driven and asserted). Reworded the count as 'N index reference(s) over M stored blob(s)' in both modes. Updated SKILL-000508 section 2 with both exact success lines so an operator can tell which command ran.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T08:22:19Z] Pierre Chat:
  - Lands with the other follow-ups rather than being pulled ahead of the tag: recovery is a git checkout and the whole-index check already diagnoses the mismatch, so the exposure is bounded.
- [2026-08-26T09:08:11Z] Elias Python:
  - F6: rebuild reports restored/dropped as two independent set-derived counts (never a size delta); a run that only restores no longer prints '0 dropped'. Driven against the real tree: '0 restored, 0 dropped' on a clean no-op rebuild.
  - F7: _write_json split into _stage_json + _write_json_pair in both scripts — both documents are fully staged (write+fsync) before either is renamed, and a staging fault cleans up any sibling already staged. _load_json diagnoses a truncated/unparseable document by name with a git-checkout + --rebuild recovery instead of raising JSONDecodeError. Proved via fault injection: (1) a staging-time fault leaves both originals untouched with no leftover .tmp; (2) an interruption between the two renames leaves the first document new and the second document old but fully parseable, and the resulting state is exactly what --check's whole-index widening flags. Docstring corrected: refusal writes nothing, a completed write never leaves a partial document, residual is a two-rename window not a transaction.
  - F8: --release-gate's clean line now reads 'release gate passed - orphan-free, ...' and is never byte-identical to plain --check's; counts reworded as 'N index reference(s) over M stored blob(s)'. SKILL-000508 section 2 shows both exact success lines.
  - Gates: pyright/ruff/ruff-format clean (--all-extras); tests/meta 258/258 passed (35 in the touched module, including the 3 new atomicity/parse/count tests + 3 F6 shape tests + 1 release-gate-line test); sq check clean. Ran the real scripts against the shipped documents (--check, --release-gate, --rebuild) — byte-identical to git throughout, no bump_version run, nothing tagged.
  - Left undone: nothing in scope. Full pytest suite not run (per instructions).
<!-- sq:discussion:end -->
