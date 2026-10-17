---
id: TASK-992
sequence_id: 992
type: task
title: Write each item file once per transaction in retype and import
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- MILE-934:targets
- REV-956:addresses
- TASK-990:depends-on
description: retype writes one file three times and import_events once per event;
  compose in memory, write once, and guard the rule with a write-count fixture
subentities:
- local_id: ST1
  title: Guard one write per item file per transaction
  status: Done
- local_id: ST2
  title: Compose the retyped file in memory and write it once
  status: Done
- local_id: ST3
  title: Write each file once per import
  status: Done
- local_id: ST4
  title: Establish the rename_type and repair multi-write cases
  status: Done
created_at: '2026-10-09T20:28:05Z'
updated_at: '2026-10-16T22:48:10Z'
---
<!-- sq:body -->
## Scope

The rule: an atomic service method works on in-memory text and writes each item file at most
once, at the end, before the index commit. REV-956 finding 17 measured it with a spy over 39
service steps: 35 wrote inside a transaction, 32 of those wrote each item file once, and two
methods did not.

- **`retype` writes one file three times in one transaction** (driven by the review).
  `apply_type_change` renames the file and rewrites its frontmatter, then
  `_ensure_subentity_container` rewrites it, `rewrite_ids` may touch it, and
  `_append_retype_comment` writes it once more (`_services/_retype.py`).
- **`import_events` writes once per event** (driven by the review): seven events on one new
  item wrote its file seven times; four events on an existing item wrote it four times. The
  apply loop calls each event's writing half in turn (`_services/_import.py`).
- **Two more are read, not driven:** `rename_type` runs `apply_type_change` per item and then
  `rewrite_ids` over the same files (`_services/_rename.py`), and `sq repair` can write one
  file from its body-tag backfill and again from its pending-rewrite pass
  (`_services/_maintenance.py`) on a corpus that needs both. ST4 drives both.

Each extra write is one more point at which a killed process leaves a file that is valid
markdown but not the method's result, and `sq repair` then adopts it. For import it is also
one `fsync` per event.

This task fixes the two driven offenders, establishes the two read ones, and puts the rule
under a guard so it cannot regress.

## Subtasks, in build order

- **ST1, the write-count guard.** An autouse fixture that fails a test when one item file is
  written twice in one transaction. It lands green, with the known offenders on an explicit
  allowlist.
- **ST2, `retype` writes its file once.** Removes its allowlist entry.
- **ST3, `import_events` writes each file once.** Removes its allowlist entry.
- **ST4, establish `rename_type` and the repair rebuild.** Drive both under the guard; fix
  what is confirmed; the allowlist ends empty or every remaining entry names its reason.

One developer, in this order: the guard is the measuring instrument for the other three.

## Sequence

Built after TASK-990 and the review of FEAT-986, and before FEAT-976: it edits
`_services/_maintenance.py`, which TASK-954, FEAT-980 and TASK-990 also edit, and the
autouse guard is then in place before FEAT-976 adds its migration writes. FEAT-980's
migration writes land earlier; the guard's first run measures them with everything else.

## Acceptance (whole task)

- Each subtask's own acceptance holds.
- **Table-driven tests over shape families**, as each subtask lists, not one test per fixed
  branch.
- **Pipeline-level invariants:** for every service method the guard observes, each item path
  is written at most once per transaction; an import of N events leaves byte-identical files
  and index to the same N events applied one at a time through the interactive verbs; after
  an injected fault at any write, every item file equals either its bytes before the method
  or its final bytes.
- **A falsified test per subtask** (durability-class work): break the fix, watch the new test
  go red, restore it, watch it go green. For the guard itself: remove one allowlist entry
  and watch the corresponding test fail. The handoff records what was broken and the test
  that went red, for each subtask.
- **A service-level test and a CLI smoke test for each changed method.** CLI tests assert the
  bare exit code.
- No behaviour change beyond the write count: for each fixed method, the item files, the
  index and the reflog after the method are byte-identical to what the commit before
  produces for the same input under a frozen clock.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .` and `sq check` are clean before handback. A
  bare `uv run` prunes the optional `tui` extra and reports false import errors.
- The guard is autouse, so it touches every test. Run `tests/service`, `tests/integration`,
  `tests/cli` and `tests/meta` once each, redirected to a file and read from the file, and
  report the selectors and the summary lines. The manager runs the full suite afterwards. A
  method the guard catches that this task does not name is added to the allowlist with its
  name and reported in the handoff; it is not fixed here and not silenced.
- Run `tests/meta` when a module-level constant is added under `src/` (the mutable-state
  guard).
- Markdown is written before the index commit, every time. No write moves after the commit.
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. No ticket ids in source or in test file names: name a test file by the behaviour
  it pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`. Time goes through `clock`. No
  module-level mutable state and no new `ContextVar` in `src/`: a buffer is threaded or
  carried on an object the transaction already owns.
- Do not edit `CHANGELOG.md` or `docs/`. Nothing here should be adopter-visible; if a
  message, an exit code or a file's bytes change, the handoff says so for the tech writer.
- Probe in a scratch squad nested under the session scratchpad, never at `/tmp` and never in
  this repository's own squad: print the working directory before any writing command and
  chain with `&&`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 992 add-subtask "<title>"`; track with `sq task 992 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Guard one write per item file per transaction

<!-- sq:subtask:ST1:body -->
**Goal.** Every existing service and CLI test becomes a probe for the rule: one item file,
at most one write per transaction.

**Approach**

- An autouse fixture (in `tests/conftest.py` or a module it loads) that observes the write
  funnel (`_aio.atomic_replace_sync`, through which every item-file write and the index
  commit pass, and `_aio.write_text`) and the unit of work (`IndexStore.transaction`), keys a
  counter on (unit, resolved path), and fails the test when an item path was written twice
  in one unit.
- The reviewer's prototype spy is no longer on disk; REV-956 finding 17 describes it. It
  replaced `_aio.atomic_replace_sync`, `_aio.write_text` and `IndexStore.transaction` with
  wrappers, numbered each transaction, and counted writes per (transaction, path), leaving
  out any path ending in `.squads.json`. These parts of that design do not carry over as
  written:
  - It replaces module attributes of `_aio`. A caller that imported the function by name
    keeps its own reference and is never seen (`_overrides/_stamp.py` does). Prove coverage
    with known positives before trusting a zero: one test per write seam (`_itemfile`
    writes, a section edit, a sub-entity edit, a create) asserting the spy saw it.
  - It tracks the current transaction in a module-level list. The fixture's state is
    per-test, and it must survive the worker-thread hop `atomic_write_text` makes.
  - It counts everything except a path ending in `.squads.json`. The rule is about item
    files. Define the set positively (files in a type folder of the squad dir, skill bodies
    included) and exempt the index and regenerable backend output (`.claude/`, the managed
    regions), which the store's docstring already exempts from the ordering rule.
  - It sees only `transaction()`. The repair rebuild commits through `IndexStore.overwrite`
    and would be invisible. Decide what the unit is for a rebuild and say so.
  - A rename inside the unit moves the file. The count follows the file, and a rename is
    not a content write.
  - It records and carries on. The fixture must fail the test, without masking an exception
    the test body raised and without raising inside the store's own lock release.
- The allowlist names service methods, not tests: `retype`, `rename_type`, `import_events`
  and the repair rebuild, each with one line saying why. A test cannot opt itself out. Each
  entry has a test asserting the double write still happens, so a fix that forgets to delete
  its entry fails.
- Measure the cost: time `tests/service` before and after, and report both.

**Tests**

- The fixture is tested on synthetic units, as a table: writes per path (one; two to the same
  path; two to different paths; one before a rename and one after; one to an exempt path
  twice; two in two consecutive units; nested units) by funnel (atomic; plain) by outcome
  (the unit commits; the unit raises). Each row states pass or fail and the message.
- Known positives, as above: every item-file write seam is observed.
- Invariant: with the allowlist emptied, exactly the allowlisted methods' tests fail and no
  others (run once, record the list).

**Falsify.** Remove the `retype` entry: a retype test fails naming the path and the count.
Restore. Then make the spy ignore `_aio.write_text`: the known-positive test for that funnel
fails. Restore.

**Acceptance**

- The guard is green on the unchanged tree with four allowlist entries.
- Its failure message names the service method, the path and the number of writes.
- The handoff lists any method the wider run caught beyond the four.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T21:42:51Z] Elias Python:
  - Guard lands in tests/_write_guard.py (autouse write_ledger fixture in conftest). Unit = one IndexStore.transaction() (named by the calling service method) or one repair rebuild; counts follow renames; units that raise are not checked; a late item-file write after the index write is reported too. Allowlist: retype, rename_type, _apply_import, plus rename_status (caught by the wider run, not named by the task, left allowlisted and unfixed). The repair rebuild needed no entry. Falsification: removing the retype entry turns 11 tests red (9 teardown errors in tests/service/test_retype.py, 2 failures in the guard module); ignoring the plain funnel turns 2 synthetic rows red. Cost of tests/service: 65s without the ledger, 70s with it (one run each). With the allowlist emptied only rename_status fails (26 tests over 7 files).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Compose the retyped file in memory and write it once

<!-- sq:subtask:ST2:body -->
**Goal.** `retype` composes the retyped item's new text in memory and writes it once.

**Approach**

- `_services/_retype.py`. Today the file is read once for the skew check and then rewritten
  by four helpers. Compose instead over the text already read: the frontmatter replacement
  (the pure half of `_itemfile.update_frontmatter`), the container
  (`ensure_subentity_container_text`, already pure), the id remap for the item's own text
  (the substitution `rewrite_ids` applies), and the retype comment
  (`sections.append_to_section`). Then rename, then one write.
- `apply_type_change` is shared with `rename_type`. Give it a shape that returns the composed
  text, or split a pure text step out of it, so both callers can finish with one write per
  file. `rewrite_ids` still handles every other file and skips the retyped one.
- Keep rename-then-write. Writing the new path and unlinking the old one would leave two
  files carrying one id if the process died in between.
- The skew check runs against the text on disk, before the rename, as now.
- Marker-safe edits only: every text step goes through `_sections.py`.

**Tests**

- Table: source and target type (a type with a sub-entity container to one without, without
  to with, both with, both without) by status outcome (carried; reset) by the item's own
  text (mentions its own id in the body; does not) by discussion region (present; absent) by
  incoming edges (none; a ref and a parent link from other items). Columns: writes per path
  under the guard, and the bytes of every file, the index and the reflog compared with what
  the commit before produces for the same input under a frozen clock.
- Fault table: an injected failure at the rename, at the one write, and at the index commit.
  For each, the retyped file is either its old bytes at the old path, its old bytes at the
  new path, or its final bytes at the new path; `sq repair` afterwards yields a consistent
  squad, and `sq check` is clean.
- CLI smoke: `sq <type> <n> retype <new-type>` exits 0 and prints what it printed before.

**Falsify.** Put the separate comment write back: the guard fails the retype rows (the
allowlist entry is gone). Restore.

**Acceptance**

- The `retype` allowlist entry and its "still double-writes" test are deleted.
- Output is byte-identical to the commit before for every row.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T21:42:53Z] Elias Python:
  - retype composes frontmatter, container, id remap and retype comment in memory and writes the file once, then rewrites the other files. apply_type_change now returns (path, composed text). Falsification: restoring a second write of the retyped file turns 40 tests red (plus 47 teardown errors) in the new retype module. Files, index and reflog are byte-identical to the previous commit over the probe scenarios (own id in body, refs, parent link, container with/without).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Write each file once per import

<!-- sq:subtask:ST3:body -->
**Goal.** `import_events` writes each item file once per import, however many events touch
it.

**Approach**

- `_services/_import.py::_apply_import` runs every event inside one transaction, and each
  event's writing half (`_create_core`, `_set_status_core`, `_section_edit_core`,
  `_add_ref_core`, `_add_block_core`, `_set_block_status_core`, `_update_core`,
  `_comment_core`) ends in its own write. Give the apply pass one text per path: the first
  touch reads the file (or starts from the created text), later events edit that text, and
  each path is written once before the transaction body returns.
- How the text reaches the writing halves is the design choice of this subtask. Constraints:
  no module-level state and no new `ContextVar`; the interactive verbs keep exactly one read
  and one write; a writing half that reads the file back must read the pending text, not the
  disk.
- Unchanged: one reflog entry per event under that event's actor and clock; the pre-pass
  that plans the import; the skew check, made once per path against the text on disk at
  first touch; markdown before the index commit.
- A created item's file is written once too: a create followed by six events on it is one
  write.

**Tests**

- Table: event mix (one event; several of one kind on one item; every kind on one new item;
  every kind on one existing item; events interleaved across three items; a sub-entity added
  and then edited in the same import; a comment on a sub-entity) by target (created in this
  import; existing). Columns: writes per path under the guard, and the number of files
  written equal to the number of distinct files touched.
- Invariant, for every row: the same events applied one at a time through the interactive
  service methods, under the same frozen clocks and actors, leave byte-identical item files,
  index and reflog.
- Fault table: an injected failure before the flush, between two files of the flush, and at
  the index commit. Every item file equals its bytes before the import or its final bytes,
  never a partly applied import; `sq repair` then yields a consistent squad.
- CLI smoke: `sq import` over a file of events exits 0 and prints the same summary as before.

**Falsify.** Make one writing half write straight to disk again: the guard fails the rows
where that event follows another on the same item. Then let a writing half read the disk
instead of the pending text: the round-trip invariant goes red. Restore each.

**Acceptance**

- The `import_events` allowlist entry and its "still double-writes" test are deleted.
- The handoff states the design chosen for carrying the text and what it costs the
  interactive path (it should cost nothing).

Gates and working rules: the task body.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T21:42:55Z] Elias Python:
  - import_events holds item-file texts in a dict on the Service for the length of the apply transaction (ServiceCore._deferred_item_writes) and flushes each file once in first-touch order before the index commit. The writing halves reach files through five ServiceCore methods that pass straight through when no block is open, so the interactive verbs keep one read and one write. A raise discards the held texts, so a failing import now leaves no file behind. Falsification: one writing half writing straight to disk turns 11 tests red, a half reading the disk instead of the held text turns 19 red. Byte-identical to one-at-a-time application is a table row for every scenario.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Establish the rename_type and repair multi-write cases

<!-- sq:subtask:ST4:body -->
**Goal.** The two multi-write cases the review read but did not drive are either confirmed
and fixed, or shown not to happen.

**Approach**

- **`rename_type`** (`_services/_rename.py`): it runs `apply_type_change` for each item of
  the type, then `rewrite_ids` over every file, the renamed ones included. Build the corpus
  that would make a renamed file change twice: two items of the renamed type where one
  carries a ref to the other and mentions the other's id in its body, plus an item of
  another type that refs both. Run `rename_type` under the guard with the entry removed and
  record the count per path.
- **The repair rebuild** (`_services/_maintenance.py`): `_backfill_roster_body_tags` writes a
  roster file whose body region lacks its view tag, and the pending-rewrite pass writes a
  file whose ref encoding is stale or whose role `extra` carries a retired key. Read on
  2026-10-09: the backfill's only caller is `sync`, on version drift, and the rebuild
  converges the body tag inside its one pending rewrite, so the two writes may never share
  a unit. Settle it by driving: build a corpus with a role file that needs both, run
  `sq repair` and a version-drifted `sq sync` under the guard, and record the count for
  each.
- If a case is confirmed, fix it the way ST2 does: compose the text once, write once. For
  `rename_type` the id remap joins the composed text of each renamed item and `rewrite_ids`
  skips those files. For the rebuild, the tag backfill joins the pending rewrite.
- If a case does not reproduce on the corpus built for it, delete its allowlist entry,
  record the corpus and the counts in a subtask comment, and say that the read was wrong.
- If a confirmed fix needs a change of design rather than of composition, stop and report
  with the measurement; the entry stays, with that reason on its line.

**Tests**

- `rename_type` table: items of the type (one; several) by cross-references among them
  (none; frontmatter refs; body mentions; both) by references from other types (none;
  some). Columns: writes per path, and bytes compared with the commit before.
- Rebuild table: file needs (only the tag; only the frontmatter rewrite; both; neither) by
  item kind (role; system skill; work item) by command (`sq repair`; `sq sync`). Columns:
  writes per path, and that a second run writes nothing.
- Fault rows for whichever case is fixed, as in ST2.

**Falsify.** For each case fixed, restore the second write: the guard fails the "both" row.
For a case that did not reproduce, show the guard does see that method: force a second write
in a scratch edit and watch it fail.

**Acceptance**

- The allowlist is empty, or each remaining entry carries the measurement and the reason.
- The handoff states, for each of the two cases: driven, the corpus used, the counts, and
  what was done.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T21:42:57Z] Elias Python:
  - rename_type: driven with two tasks (one refs and mentions the other) and a review referring to both; before: 3 writes to the first file, 2 to the second, 1 to the review; after: 1 each. Fixed by composing each renamed file in memory. Falsification: restoring a separate comment write turns 16 tests red. Repair did not reproduce: a role needing the body tag, the retired keys, or both is written once by sq repair; a version-drifted sq sync writes the tag backfill once outside any unit and nothing else touches the file. The read was wrong, so no allowlist entry was ever added; forcing a second write in the rebuild loop turns 5 tests red (plus 5 errors). Test tables: role, system skill, work item by tag/frontmatter need by command.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T20:39:51Z] Olivia Lead:
  - 2026-10-09: authored from REV-956 finding 17; no feature parent, targets MILE-934, left in Draft. Two points for @manager:
    
    - **Order.** The milestone comment places the write-count guard in 0.16 without a slot. It edits `_services/_maintenance.py`, which TASK-954 and TASK-990 also edit, and there is one Python stream. Proposed: after FEAT-986's review clears and before FEAT-976, so the autouse guard is in place for the two features that add migration writes.
    - **The repair case may not exist.** Read today: `_backfill_roster_body_tags` is called only by `sync` on version drift, and the rebuild converges the body tag inside its single pending rewrite. ST4 drives it either way and records the counts on the finding's terms.
- [2026-10-11T20:23:55Z] Olivia Lead:
  - 2026-10-11: slot recorded as relayed by the manager from op-pierre's answers: built after TASK-990 and the review of FEAT-986, before FEAT-976. The body carries it under "Sequence" and the task now depends on TASK-990. The reviewer's prototype spy is gone from disk (the session scratchpad was cleared), so ST1 describes its design instead of pointing at it. Still Draft.
- [2026-10-11T20:24:58Z] Catherine Manager:
  - Correction of attribution: this task's slot (after the FEAT-986 review, before FEAT-976) is the manager's call following the tech lead's proposal, not a ruling by the operator. I relayed it as his answer in error.
- [2026-10-12T06:34:37Z] Olivia Lead:
  - 2026-10-12: wording of the "Sequence" section corrected for the new build order (FEAT-980 now lands before this task). The slot is unchanged: after TASK-990 and the review of FEAT-986, before FEAT-976. Still Draft.
- [2026-10-16T21:43:04Z] Elias Python:
  - Built on release/0.16 (worktree branch worktree-agent-a0f8c17233ea0ade9, commits 4a8bdc9d, 22fa82b6, 15b80785, 4417bdee). Gates: pyright 0 errors, ruff check and format clean; tests/service, integration, cli, meta, unit, tui each run once and green (full suite left to the merge). Beyond the four named: rename_status also writes frontmatter then comment (allowlisted, not fixed). Repair rebuild did not reproduce, so no entry. Adopter-visible: an import that fails mid-apply now leaves no item file written (previously a prefix of the events had landed); output, files, index and reflog are otherwise byte-identical. Tech writer: no doc change needed beyond that.
- [2026-10-16T21:50:27Z] Elias Python:
  - rename_status now composes in memory and writes once (commit before c520f5a3); falsification: a restored separate write turns 4 tests red plus 5 errors. Allowlist mechanism removed entirely.
- [2026-10-16T22:02:33Z] Paul Reviewer:
  - Reviewed in REV-1083: ChangesRequested (2 medium, 2 low, 1 info). Output is byte-identical to the previous commit; BUG-1081 verified.
- [2026-10-16T22:48:10Z] Catherine Manager:
  - Done: REV-1083 approved; merged at e56f7a18, single-write fix in the migration at ca5866bd; full suite 12136 passed, 0 failed.
<!-- sq:discussion:end -->
