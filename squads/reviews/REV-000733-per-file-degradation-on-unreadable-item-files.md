---
id: REV-733
sequence_id: 733
type: review
title: Per-file degradation on unreadable item files
status: Approved
author: reviewer
refs:
- TASK-674
- ADR-663
subentities:
- local_id: F1
  title: repair loses the counter high-water mark of an unreadable file
  status: Fixed
  severity: high
- local_id: F2
  title: repair aborts board-wide on valid YAML with no id, misdiagnosed
  status: Fixed
  severity: high
- local_id: F3
  title: Type-invalid frontmatter crashes repair with a pydantic traceback
  status: Fixed
  severity: high
- local_id: F4
  title: FileNotFoundError on a present dirent still crashes every command
  status: Fixed
  severity: medium
- local_id: F5
  title: The --json listings silently drop the unreadable-file messages
  status: Fixed
  severity: medium
- local_id: F6
  title: board list and repair exit 0 while reporting an error
  status: Fixed
  assignee: tech-writer
  severity: low
- local_id: F7
  title: check never names an unreadable file as on-disk-but-not-indexed
  status: WontFix
  severity: info
- local_id: F8
  title: The widened load boundary misses TypeError and ValueError
  status: Fixed
  severity: high
- local_id: F9
  title: A malformed frontmatter id still aborts the whole check scan
  status: Fixed
  severity: medium
- local_id: F10
  title: repad diagnoses a broken symlink differently from check
  status: Fixed
  severity: low
- local_id: F11
  title: The boundary catches KeyError wider than its three required reads
  status: Fixed
  severity: info
- local_id: F12
  title: Two of four empty-string list fields lost their compatibility
  status: Fixed
  severity: low
- local_id: F13
  title: check and repair contradict each other on a malformed id
  status: Fixed
  severity: medium
- local_id: F14
  title: The per-file message for a bad field is a raw pydantic dump
  status: Fixed
  severity: low
- local_id: F15
  title: The (got type) suffix misdescribes an absent field
  status: Fixed
  severity: low
created_at: '2026-08-03T11:01:43Z'
updated_at: '2026-08-03T15:47:23Z'
---
<!-- sq:body -->
Independent review of the per-file degradation work (TASK-674, commits `d3d41c1` / `29cb656`).
Reviewer was outside the build lineage. Everything claimed below was driven against throwaway
squads, not read off the implementation report.

## What holds

- `sq check` completes and names the bad file with its byte offset; the other items still list.
- `sq repair` carries the previous index entry forward for an unreadable file whose stem seq
  resolves against the previous index; the item stays resolvable by `show` and present in
  `list -a`. `missing_ids` is not polluted.
- `sq migrate repad` and `sq repair --renumber` still refuse, cleanly, with the file named and
  no partial rename — the `_scan_records()` preflight does its job.
- The scan's third state works: an unreadable file is not reported as
  "indexed but no markdown file found".
- `sq board list` / `sq memory list` degrade per file on the human surface.
- `sq check` exits 3 (error level) with an unreadable file — no new exit code, as scoped.

## Where it does not hold

The three shapes the build falsified against (permission-denied, invalid UTF-8,
malformed-but-closed YAML) all reach the read/parse guard, so they all pass. Every shape that
fails *one step outside* that guard still takes the command down board-wide, and two of them do
it with a raw traceback. The findings carry the reproductions.

The load-bearing property — "no item whose file exists may be silently dropped" — is broken in
two ways that a reader of the tests would not expect: once by a lost counter high-water mark
(F1), once by a frontmatter that parses but carries no `id` (F2).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 733 add-finding "…" --severity medium`; track with `sq review 733 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | repair loses the counter high-water mark of an unreadable file |
| F2 | 🟠 high | Fixed |  | repair aborts board-wide on valid YAML with no id, misdiagnosed |
| F3 | 🟠 high | Fixed |  | Type-invalid frontmatter crashes repair with a pydantic traceback |
| F4 | 🟡 medium | Fixed |  | FileNotFoundError on a present dirent still crashes every command |
| F5 | 🟡 medium | Fixed |  | The --json listings silently drop the unreadable-file messages |
| F6 | 🟢 low | Fixed | tech-writer | board list and repair exit 0 while reporting an error |
| F7 | 🔵 info | WontFix |  | check never names an unreadable file as on-disk-but-not-indexed |
| F8 | 🟠 high | Fixed |  | The widened load boundary misses TypeError and ValueError |
| F9 | 🟡 medium | Fixed |  | A malformed frontmatter id still aborts the whole check scan |
| F10 | 🟢 low | Fixed |  | repad diagnoses a broken symlink differently from check |
| F11 | 🔵 info | Fixed |  | The boundary catches KeyError wider than its three required reads |
| F12 | 🟢 low | Fixed |  | Two of four empty-string list fields lost their compatibility |
| F13 | 🟡 medium | Fixed |  | check and repair contradict each other on a malformed id |
| F14 | 🟢 low | Fixed |  | The per-file message for a bad field is a raw pydantic dump |
| F15 | 🟢 low | Fixed |  | The (got type) suffix misdescribes an absent field |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — repair loses the counter high-water mark of an unreadable file

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Reproduced.** Violates the global-counter invariant and then silently deletes a real item.

`_rebuild_index_from_disk` computes `max_n` only from files that parsed. On the unreadable
branch it computes `_stem_seq(md, item_type, self.spec)` — the sequence number recovered from the
filename — uses it to look up a carried entry, and then throws it away. It never feeds `max_n`.

So when an unreadable file has **no** entry in the previous index — the case the task body
explicitly enumerates as supported ("leave it unindexed and report it") — that file's sequence
number stops contributing to the counter high-water mark. `db.counter = max(previous_counter,
max_n)` cannot recover it, because the previous index never knew about it either.

Driven (throwaway squad, tasks 9/10/11):

1. `TASK-000011-three.md` made unreadable (invalid UTF-8), `.squads.json` removed.
2. `sq repair` -> `rebuilt index: 10 items, counter=10`, and the file is correctly reported.
3. `sq create task "collide"` -> `created TASK-11 -> tasks/TASK-000011-collide.md`.

Two files now claim `TASK-11`. `sq check` reports only the UTF-8 error and never mentions the
collision.

The punchline is the recovery path. After the operator fixes the UTF-8 — the remedy the message
tells them to perform — `sq repair` succeeds and `sq check` prints `no issues`, while
`sq list -a` shows only `three`. The item the operator authored as `collide` has vanished from
the index, its file is an orphan, and nothing reports it. That is exactly the
disappearance-with-no-report this release closed, manufactured by the repair path itself.

The fix is one line at a site that already holds the value: fold `stem_seq` into `max_n` on the
unreadable branch (and, for the same reason, its digit-run width into `max_filename_width`).
Please also add a test that a repair over an unreadable, never-indexed file leaves a counter no
lower than that file's own sequence number.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-03T11:46:16Z] Elias Python:
  - Fixed: _rebuild_index_from_disk now folds the unreadable file's filename-derived seq/digit-run into max_n/max_filename_width on every third-state branch (_report_third_state), not just the read/parse one -- so the counter/padding floor accounts for it even with no previous index entry to carry from. Falsified both halves (counter value AND no reissue) with known_corpus removed entirely, matching the repro.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — repair aborts board-wide on valid YAML with no id, misdiagnosed

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Reproduced.** `sq repair` is still unavailable board-wide for a whole family of one-bad-file
inputs, and the refusal names a file that does not exist.

Shape: an item file whose frontmatter is valid YAML but carries no `id` — a partial patch, a
badly resolved conflict that kept YAML validity, a truncated write, a stripped frontmatter
block. `_rebuild_index_from_disk`'s `if not data.get("id"): continue` drops it with no
`unreadable` entry and no carry-forward, so the item is absent from the rebuilt `db` while still
present in `known_corpus`. `_corpus_alignment_refusals` then reads that as a re-foldered corpus
and raises.

Driven (throwaway squad, no overrides anywhere):

    $ python3 -  # strip the `id:` and `sequence_id:` lines from TASK-000011-three.md
    $ sq check
    error TASK-000011-three.md: file has no `id` in frontmatter
    $ sq repair
    error: refusing to rebuild the index: the active workflow spec has re-foldered or
    re-prefixed a type against a corpus that still has files where it used to be ...
      - type 'task' has 1 item(s) still on disk at their previously recorded location ...
      ['TASK-11'] - revert the change in .overrides/workflow.toml, or make it only while
      the type has no items

There is no `.overrides/workflow.toml` in this squad. The operator is told to revert a change
they never made, in a file that is not there, and `sq repair` — the documented remedy for
everything in this line of work — does nothing at all.

The refusal itself predates `d3d41c1`; what is unmet is this task's own acceptance, which is
that one unparseable file must not take `repair` down. This shape is one step outside the three
that were falsified and it lands in the same branch of the same function.

Two things to fix, in order of weight. Give the no-`id` file the same third-state treatment the
read/parse failures get: report it, carry the previous entry forward, do not drop it. And make
`_corpus_alignment_refusals` state its evidence honestly — it should not claim a
prefix/folder change when it has not observed one.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-03T11:46:24Z] Elias Python:
  - Fixed: a valid-YAML-no-id file now gets the same third-state carry-forward/report treatment as an unreadable file in _rebuild_index_from_disk, instead of a silent 'continue' that dropped it from db and made _corpus_alignment_refusals misdiagnose a re-foldered corpus. The misdiagnosis disappears as a side effect -- the item is no longer missing from the rebuilt db to compare against. Kept the pre-migration legacy-skill-body exemption (no id ever, not an error) via a shared _is_legacy_skill_body helper so I didn't regress that case while fixing this one.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Type-invalid frontmatter crashes repair with a pydantic traceback

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Reproduced.** The fourth shape I was asked to attack. The per-file guard wraps
`_aio.read_text` + `read_frontmatter`, but `Item.from_frontmatter` sits *outside* it, and pydantic
raises `ValidationError`, which is not a `SquadsError`.

Shape: frontmatter that parses as YAML but carries a type-invalid value for a modelled field.
Trivially reachable from any hand-edit or merge artifact that keeps YAML valid.

Driven (throwaway squad, `title: three` replaced by a YAML list):

    $ sq check
    ✓ no issues
    $ sq repair
    ... ValidationError: 1 validation error for Item
    title
      Input should be a valid string [type=string_type, input_value=['a', 'b'], input_type=list]

Two separate defects in that transcript.

`sq repair` aborts the whole rebuild with a **raw traceback** — no `SquadsError`, no clean
message, and the offending file is never named. That breaches the standing "user-facing errors
subclass `SquadsError`" rule as well as this task's per-file contract.

`sq check` says `no issues` about a file that cannot be loaded at all. `check` only ever reads
`on_disk`'s raw frontmatter dicts, so nothing in it ever tries to construct the `Item` and
nothing notices. A gate that passes clean on a corpus `repair` cannot rebuild is worse than a
gate that fails: the operator has no signal until the next repair.

Suggested shape: catch `ValidationError` alongside `SquadsError` in both `_scan_for_check` and
`_rebuild_index_from_disk` and route it into the same third state (report + carry forward). If
`Item.from_frontmatter` is meant to be the load boundary, having it raise a `SquadsError` naming
the file would fix both sites at once and remove the need for a second `except` clause per
call site.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-03T11:46:32Z] Elias Python:
  - Fixed at the load boundary you named: Item.from_frontmatter now catches pydantic ValidationError/KeyError and raises SquadsError naming the path, so both repair's rebuild loop and check's scan (which now also calls from_frontmatter to validate) catch it with the same except SquadsError already in place -- no second except clause needed. check now reports the type-invalid file instead of 'no issues'; repair carries its previous entry forward instead of a raw traceback.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — FileNotFoundError on a present dirent still crashes every command

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**Reproduced** (via a broken symlink). Realistic trigger is a race, which I did not reproduce
and label a hypothesis.

`_aio.read_text` deliberately re-raises `FileNotFoundError` rather than wrapping it. Every
per-file guard added by this work catches `SquadsError` only, so a directory entry that the
glob sees but the read cannot open escapes all of them.

Driven (throwaway squad):

    $ ln -s /nonexistent/target squads/tasks/TASK-000012-ghost.md
    $ sq check   -> FileNotFoundError traceback
    $ sq repair  -> FileNotFoundError traceback
    $ ln -s /nonexistent/x squads/board/ghost.md
    $ sq board list -> FileNotFoundError traceback

The pre-existing behaviour was also a crash, so this is not a regression — it is the new
contract being incomplete for a shape in the same family as the three that were tested. Three
of the four commands this task exists to make resilient are still taken down by one dirent,
and now they fail with a traceback rather than a message.

**Hypothesis, not reproduced:** the same code path covers the glob-then-read race. Between
`_iter_item_files()`'s glob and the read, a concurrent agent's `sq <type> <n> remove`, a
`git checkout`, or a branch switch removes the file and the command dies. This project runs
multiple agents against one tree by design, and `sq check` is the pre-handoff gate, so that is
where it would bite.

Deciding what the right answer is matters more than the catch: a file that vanished mid-scan is
genuinely absent (skip it, and let the missing-direction reconciliation report it), whereas a
broken symlink or a permission-shaped `FileNotFoundError` on a present dirent is the
"present but unparseable" state. Please rule on that rather than blanket-catching, and either
way stop emitting a traceback.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-03T11:46:45Z] Elias Python:
  - Fixed, with the ruling you asked for: a FileNotFoundError on a dirent the scan's own glob just saw is decided by Path.is_symlink() (lstat, doesn't follow the link) -- present-but-broken (is_symlink() true) gets the same third-state report+carry-forward as any other unreadable file; genuinely vanished (is_symlink() false, truly gone) is skipped with nothing reported, on the theory that a real deletion is the missing-direction reconciliation's claim to make (from the previous index), not a second, competing claim invented by the scan that raced it. Applied at all four sites you drove: check's scan, repair's rebuild, board list, memory list -- plus repad/renumber's _scan_records preflight, which previously would have propagated a raw FileNotFoundError instead of refusing cleanly. New tests cover both branches, including a simulated glob-then-read race (monkeypatched delete) for the genuinely-vanished half, which isn't otherwise reproducible on demand.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The --json listings silently drop the unreadable-file messages

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**Reproduced.** The human surface reports the unreadable file; the machine surface hides it.

`_cli/_board.py::list_notices` and `_cli/_memory.py::list_memories`/`search_memories` all take
the `(entries, unreadable)` tuple, and all three `return` from the `--json` branch **before**
the `for msg in unreadable: console.print(...)` loop. So the JSON consumer gets a silently
shortened collection with nothing to distinguish it from a genuinely shorter one.

Driven (throwaway squad, one notice made invalid UTF-8):

    $ sq board list
    error: .../squads/board/bd3bc0297f.md is not valid UTF-8: byte 0xff at offset 0 ...
    no current notices
    $ sq board list --json
    []

That matters here specifically: `--json` is the surface the clients and the orchestrating agents
read. A board that lost a notice reads as an empty board, and the reader has no way to know.
It also misses this task's own acceptance ("names the unreadable one in the output") on the
surface most likely to be consumed unattended.

Fix additively — the JSON shapes are a frozen Tier-3 contract, so a bare array cannot become an
object. The precedent this release already set is `sq inbox --json`'s parallel additive key; a
sibling `unreadable` key is not available on a top-level array, so this needs a ruling rather
than a mechanical patch. Options worth weighing: emit the messages on stderr (leaves the JSON
document untouched and keeps the array shape), or accept an envelope as a new, separately
versioned surface. Whichever way it goes, please state it — a machine surface that is quieter
than the human one about a data-integrity failure is the wrong default.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-03T11:46:53Z] Elias Python:
  - Fixed via the additive-safe option you weighed: board list/memory list/memory search's --json branches now print each unreadable-file message to stderr before returning, leaving the JSON array shape untouched (no envelope, no new key -- the Tier-3 contract stays frozen). A machine consumer that only reads stdout still gets a bare array, but the exit code (see F6) plus stderr now say the read was degraded rather than genuinely empty/short.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — board list and repair exit 0 while reporting an error

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Assignee:** Theo Writer
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**Reproduced.** Measured without a pipe (a pipeline reports the last element's status, not the
command's).

    $ sq board list >/dev/null 2>&1; echo $?   -> 0   (while printing `error: ... not valid UTF-8`)
    $ sq check >/dev/null 2>&1; echo $?        -> 3   (correct — error level)
    $ sq repair >/dev/null 2>&1; echo $?       -> 0   (with an unreadable file reported)

`check` is right. The other two are worth a ruling rather than a silent zero.

`board list` prints at `error:` level and exits 0, so a wrapper script cannot tell a degraded
listing from a clean one — the same blindness as F5, one layer out.

`repair` exiting 0 is the more arguable of the two: it did rebuild, and it did report. But what
it returns is an index it knows contains a carried-forward, possibly-stale entry, and the
message tells the operator to fix the file and repair again. A caller that gates on `$?` will
treat that as a completed repair. The task put the exit-code contract out of scope for `check`
only; these two were not considered.

Not a defect on its own — recorded so the contract is decided rather than inherited.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-03T11:47:04Z] Elias Python:
  - Fixed: board list and repair now exit 1 when they report at least one unreadable file/notice, mirroring check's existing error-level-issue-means-nonzero contract rather than the old bare 0. Decided both the same way for consistency: repair did succeed at everything it safely could (nothing lost, carried forward), but what it returns is an index it knows contains a stale entry and its own message tells the operator to fix the file and repair again -- a caller gating on $? needs to see that as not-clean, same as board list's printed error: line. Updated the two pinned exit-0 CLI tests (test_malformed_frontmatter_and_config_fail_cleanly.py, test_undecodable_squad_files_fail_cleanly.py) that encoded the old contract; the clean-board parametrized tests are unaffected (still 0). Noting for visibility: this changes an existing shipped CLI exit code, which the VS Code client (clients/vscode/, out of my scope) may also observe -- flagging in case its repair/board-list handling assumes the old contract.
- [2026-08-03T12:38:31Z] Catherine Manager:
  - Code half is Fixed. Assigning the writer the adopter-facing half: the exit-code move from 0 to 1 on board list and repair needs a Changed entry, since the published exit-code table is a frozen contract and the VS Code client branches on it.
- [2026-08-03T13:07:25Z] Theo Writer:
  - Adopter-facing half done. Wrote the exit-code move as a **Changed — action required** entry under 0.13.0 (board list + repair 0→1, and check 1→3 for the same unreadable-file case, which moved with the per-file degradation work), naming the wrapper-script/CI/editor-integration branches as the thing to re-check, and stating plainly that reporting an error at status 0 was itself the contract violation.
  - Also corrected the published table: docs/faq.md code `1` now reads "squads could not complete what you asked" and covers a command that finished only partly and named what it could not read, plus a short "A degraded read is a non-zero exit" note covering check exiting 3 and board list --json keeping its bare-array stdout with names on stderr. Measured every code without a pipe before writing it.
  - Inconsistency left standing, not written into the notes: `sq memory list` degrades and names the unreadable file but still exits 0, in both output modes — the ruling on this finding covered board list and repair only. @manager worth a ruling so the three degrade-and-report surfaces agree.
- [2026-08-03T13:12:52Z] Catherine Manager:
  - Ruling on the memory list inconsistency raised by the writer: sq memory list should exit 1 on a degraded read too. The condition is identical and the published table treats a non-zero status as the signal, so leaving one of three commands at 0 makes the contract depend on which command you happened to run. Queued as code work, not a docs change — the release notes correctly name only the two commands that behave that way today.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — check never names an unreadable file as on-disk-but-not-indexed

<!-- sq:finding:F7:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🔵 Info
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**Reproduced.** Body/behaviour mismatch, no code defect.

TASK-674's body says, of an unreadable file with no previous index entry: "leave it unindexed and
report it; `check` will then name it as on-disk-but-not-indexed, which is the honest state."

It does not. Driven: unreadable `TASK-000011-three.md`, index removed, `sq repair` (leaves it
unindexed — confirmed, the rebuilt index holds seqs 1-10 only), then `sq check` reports only:

    error TASK-000011-three.md: ... is not valid UTF-8: byte 0xff at offset 0 ...

There is no on-disk-but-not-indexed claim, and structurally there cannot be: the file lands in
neither `on_disk` (so `orphan_seqs` cannot see it) nor `index.items`, and its stem seq goes into
`unparseable_seqs`, which is only ever *subtracted* from the missing direction.

The behaviour is defensible — the parse failure is reported, names the file, and is the actionable
thing. What is wrong is the written claim, which a future reader will use as the spec for a
reconciliation check that does not exist. Either add the claim to `check` or correct the body.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-03T11:47:17Z] Elias Python:
  - WontFix-the-behaviour, fixed-the-claim: check does NOT invent an on-disk-but-not-indexed claim for an unreadable file, and I judged that correct rather than a gap to close. That claim would have to guess the file's id from its filename and report the guess as fact -- exactly the kind of unconfirmed claim this whole task family (suppress_missing, the stem-vs-frontmatter keying decision) already refuses to make elsewhere. Corrected TASK-674's body and its ST3 subtask body instead (both had this same inaccurate claim) to say what actually happens: the file is reported as unreadable, full stop, with no additional on-disk-but-not-indexed claim layered on top.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — The widened load boundary misses TypeError and ValueError

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**Fixed.** The boundary now has exactly two failure channels and nothing can raise outside them.

`Item.from_frontmatter` was rewritten so `model_validate` is the only validator:

- the payload moved into `_frontmatter_payload`, which is **non-raising by construction** — every
  value is either passed straight through or folded by a helper that returns an unexpected shape
  *unchanged* for pydantic to reject. `list(...)`/`dict(...)`/`fromisoformat` are gone from it.
- `_read_extra` / `_read_severity` / `_read_refs` gained a shared `_extra_mapping` reader that only
  looks inside `extra` when it really is a mapping, and `_read_refs` only folds a legacy `ref_kinds`
  map when the refs are actually a list of strings.
- `SubEntity.from_frontmatter` was deleted; its two tolerated spellings (`severity: ''`,
  `extra: null`) moved into a `mode="before"` model validator, so the raw `subentities` list is
  handed to pydantic and a non-mapping element is reported by it rather than subscripted.
- `_parse_dt` no longer parses-or-invents: absent/`null` still defaults to now (the legacy-file
  case), a `datetime` or ISO string is normalised to tz-aware UTC, and **anything else is returned
  unchanged** for pydantic to judge.
- a non-string `id` now raises inside `_derive_prefix_from_id` (so it surfaces as a
  `ValidationError`, not an `AttributeError` from `prefix_from_id`). Left unguarded it would have
  minted an item whose prefix never resolved and whose `.id` rendered as the UNRESOLVED sentinel.

The docstring no longer asserts a guarantee wider than the code: it names the two channels
(missing required key, type-invalid value), says which one reports what, and states that
`_frontmatter_payload` must never iterate, subscript, index or parse an untrusted value.

Ten shapes tracebacked before, not six: the sweep also found `extra: [1, 2]`, `subentities: oops`,
`updated_at: not-a-date`, `id: 5` and `id: [a, b]`.

`created_at: 5` is deliberately **outside** the refusal contract and pinned as such: a number is a
shape pydantic accepts for a datetime (a Unix epoch), so it loads as 1970-01-01T00:00:05Z. That is
the better of the two tolerant options — the value is at least derived from what the file says,
where the old `else: return now()` made a corrupt timestamp indistinguishable from a fresh one.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — A malformed frontmatter id still aborts the whole check scan

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
**Fixed.** Both `number_for_id` sites in `_scan_for_check` now route through
`_seq_from_frontmatter_id`, which returns `None` for either unreadable shape — a non-integer
trailing segment (`InvalidIdError`) or a non-string value (`AttributeError`, which an
`except InvalidIdError` alone would not have covered). The file is reported at error level, keyed
into `unparseable_seqs` by its filename stem via the `_unparseable_seq_or_suppress` that was
already sitting right there, and the scan continues.

The report itself (`_malformed_id_message`) says the two things the file cannot tell you: that the
value is being **ignored** — identity is `sequence_id` plus the type's prefix, and `id` is a
computed field regenerated from those — and hence that `sq repair` will rebuild the index from this
same file without complaint. Both ways out are named.

On the "should repair report it as a repair action" question: **no**, and the disagreement is
resolved in the other direction. Repair never rewrites the `id:` line at all (it rebuilds the
*index*; the file is untouched), so there is nothing silently rewritten to report — the line simply
is not read. Repair proceeding is correct; `check` is the reporter and now always says so. Pinned
both ways so neither side gets "fixed" into the other.

A non-string `id` is a genuinely different case and is not folded in: there is nothing left to
derive a prefix from, so the load boundary refuses it and repair third-states the file. Test asserts
no `UNRESOLVED-*` id can reach the rebuilt index.

Also closed the same family's sibling hole in `_scan_records` (the `repad`/`renumber` path), which
still threw a raw `AttributeError` on `id: 5` via `prefix_from_id`. Those verbs rewrite identity
across the whole corpus, so they **refuse** — but as a clean `SquadsError` naming the file, which
is what that function's own `FileNotFoundError` branch already promises in prose.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — repad diagnoses a broken symlink differently from check

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
**Reproduced.** F4's disposition gave one dirent two different diagnoses depending on which
command you run.

`_scan_records`'s new `FileNotFoundError` wrapper (the `repad`/`renumber` preflight) reports:

    $ sq migrate repad 8
    error: .../squads/tasks/TASK-000012-ghost.md could not be read: [Errno 2] No such file or
    directory: '/.../squads/tasks/TASK-000012-ghost.md'

while `check` and `repair`, on the identical dirent, correctly say:

    error TASK-000012-ghost.md: .../TASK-000012-ghost.md is a broken symlink (its target does
    not exist)

Three small things, one message:

- **"No such file or directory" is the wrong claim** — the dirent is right there. That is
  precisely the distinction `_aio.path_is_symlink` was added to draw, and the refusal path is
  the one place it is not drawn. An operator reading the repad message will look for a missing
  file.
- **The path is printed twice**, once from the wrapper's own f-string and once inside the
  errno's `str()`. Elsewhere this codebase names the file once.
- The raw errno text leaks into a user-facing message, where the sibling paths phrase it.

Both refusals are otherwise correct: `repad` and `renumber` do refuse, before any rename, with a
clean `SquadsError` and no traceback — that half of the disposition holds. This is message
quality on a path the fix created.

Suggested: reuse the same present-vs-absent test in `_scan_records` and emit the same
"is a broken symlink (its target does not exist)" sentence, falling back to a single-path
"could not be read" for a genuinely vanished dirent. One shared message helper for all four
call sites would keep them from drifting again.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-03T15:21:16Z] Elias Python:
  - Fixed as you suggested, including the shared helper: `_missing_dirent_message(md, *, is_symlink)` in `_services/_maintenance.py` is now the single wording for a FileNotFoundError on a dirent the caller's own glob just saw, used by check, repair and the repad/renumber preflight.
  - All three of your points, driven on one broken-symlink dirent: repad and renumber now say `<path> is a broken symlink (its target does not exist) — refusing to rewrite ids while a file in the corpus cannot be read` — same sentence as check and repair, the path named once, no errno text. The refusal itself is unchanged (both still refuse before any rename).
  - Pinned in `tests/service/test_unreadable_files_degrade_per_file.py::test_every_command_gives_a_broken_symlink_the_same_diagnosis`: one dirent through all four commands, asserting the shared sentence in each and — for the two refusals — no "No such file or directory", no "Errno", and `message.count(path) == 1`. Falsified: restoring the errno wrapper reddens it alone.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The boundary catches KeyError wider than its three required reads

<!-- sq:finding:F11:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
**Fixed** by the narrower of the two shapes you offered, taken together with F8's fix so both land
in one change.

The three required keys (`type`, `sequence_id`, `status`) are now read by name up front against
`REQUIRED_FRONTMATTER_KEYS`, raising a `SquadsError` that names the missing key(s) and the path. The
`KeyError` arm is gone from the boundary entirely — `except ValidationError` is all that remains,
and it is sufficient because F8's fix made `model_validate` the only thing on the path that can
fail.

So the latent misreport you described is now unreachable rather than merely unlikely: a `KeyError`
from a spec lookup anywhere on this call graph propagates as a `KeyError` and fails loudly, instead
of being relabelled `invalid item data in <path>` and sending an operator to hand-edit a healthy
file (or being third-stated by `repair`, carrying a stale entry forward).

Pinned by a test that makes one helper on the call graph raise `KeyError` and asserts it comes back
out as `KeyError`. The simulation is deliberate — nothing there does a spec lookup today, and the
claim under test is what the boundary does with one, not that a live site exists.

Also a better message for free: a missing `status` now reads `missing required frontmatter
'status'` rather than a bare `KeyError` repr.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Two of four empty-string list fields lost their compatibility

<!-- sq:finding:F12:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
**Reproduced.** The compatibility rule stated in `_empty_list_if_unset` — "a file that loaded
yesterday must load today" — is right, and it was applied to two of the four fields the old
coercion covered.

The replaced code coerced four fields with an `or`-default that swallowed `""` as well as `None`.
Evaluating the removed expressions literally, from this commit's own diff:

    list({"labels": ""}.get("labels", []) or [])        -> []      loaded
    list({"refs": ""}.get("refs", []) or [])            -> []      loaded
    [s for s in ({"subentities": ""}.get("subentities") or [])]  -> []   loaded
    dict({"extra": ""}.get("extra", {}) or {})          -> {}      loaded

`_empty_list_if_unset` is wired to `labels` and `refs`. `subentities` became
`[] if subentities is None else subentities` and `_read_extra` returns a non-mapping unchanged, so
both now hand `""` to `model_validate`, which rejects it.

Driven — 46 frontmatter shapes through `Item.from_frontmatter` on a real item file:

    labels-empty-string        LOADED         labels=[]
    refs-empty-string          LOADED         refs=[]
    subentities-empty-str      SquadsError    <- regressed
    extra-empty-string         SquadsError    <- regressed
    labels-null / refs-null / subentities-null / extra-null    all LOADED

`test_an_unset_list_field_still_loads_as_empty` parametrizes `["labels", "refs"]`, so neither
regressed field is pinned in either direction.

**Why this is low and not a blocker, stated so you can disagree.** The failure is a clean
`SquadsError` naming the file; `check` reports it per-file and `repair` carries the previous entry
forward, so nothing disappears and nothing is hidden. And sq never writes either key when it is
empty (`to_frontmatter_dict` omits a falsy `subentities`/`extra`), so reaching this needs a
hand-edit or a merge artifact — exactly the same reachability as `labels: ''`, which is what makes
the asymmetry the defect rather than the behaviour.

What I would fix: route `subentities` and `extra` through the same helper (`_empty_list_if_unset`
for the list, an `_empty_dict_if_unset` sibling for the mapping) and extend the compat test's
parametrize to all four keys. Then the stated rule is true of its whole scope, and nobody later
"tidies" the asymmetry in the wrong direction.

**Separately, and I endorse it:** rejecting `labels: 'abc'` where the old `list("abc")` silently
produced three one-character labels is the right line. That old behaviour produced garbage in every
view, so no working file depends on it, and the new refusal is pinned. The compat carve-out is
correctly limited to the empty string.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-08-03T15:21:02Z] Elias Python:
  - Fixed as you suggested: all four container keys now route through one of two helpers — `_empty_list_if_unset` for `labels`/`refs`/`subentities`, a new `_empty_dict_if_unset` sibling for `extra`. Driven over 4 keys x {absent, null, empty string}: all twelve load as the right empty container.
  - Pinned in both directions and over the whole scope, not a subset: `_CONTAINER_FIELDS` in `tests/service/test_type_invalid_frontmatter_load_boundary.py` carries all four keys with their empty value, and the bare-string rejection is parametrized over the same four. Added a coverage guard that derives the container-field set from `Item.model_fields` annotations, so a fifth container field cannot be added behind the table the way the fourth slipped past.
  - Falsified: reverting `subentities`/`extra` to the pre-fix expressions reddens the compat test for exactly those two keys and nothing else.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — check and repair contradict each other on a malformed id

<!-- sq:finding:F13:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
**Reproduced. A new defect created by the F9 widening**, and the message that is wrong is the
actionable sentence.

`check` gained a dedicated, hand-written message for a malformed frontmatter `id`. `repair` has no
such pre-check and routes the same file through the load boundary. Driven on the same file
(`id: 5`):

    $ sq check
    error TASK-000011-three.md: frontmatter `id` 5 is malformed and is being ignored -- the
    item's identity comes from `sequence_id` plus its type's prefix, so `sq repair` rebuilds the
    index from this file without complaint. Fix the `id:` line (or delete it) to clear this.

    $ sq repair
    rebuilt index: 11 items, counter=11
    error: TASK-000011-three.md: invalid item data in tasks/TASK-000011-three.md: 1 validation
    error for Item
      Value error, expected str for `id`, got 'int': 5 ...
    -- its previous index entry, if any, was carried forward as-is; fix the file and repair again

`check` promises `sq repair` will rebuild from the file "without complaint". `repair` complains,
and does **not** rebuild from the file — it third-states it and carries the previous entry forward,
so the entry stays stale until the `id:` line is fixed. An operator who reads `check`'s message as
"cosmetic, repair sorts it out" runs repair, gets an error, and is told something different about
the same file.

The two halves of this fix pull against each other, which is worth naming rather than patching
blind. `_derive_prefix_from_id` now **raises** on a non-string `id`, deliberately and with a good
reason recorded in its docstring: skipping it would mint an item whose `prefix` never resolved and
whose `.id` rendered as the `UNRESOLVED_PREFIX` sentinel. That makes the item genuinely unloadable
through `from_frontmatter`, which is the only thing `repair` has. So `check`'s claim cannot be made
true just by rewording `repair` — and it cannot be made true by relaxing the raise either, because
`from_frontmatter` holds no spec and therefore cannot derive the prefix from `sequence_id` + type
the way the message says.

Two coherent resolutions, and I would take the first:

1. **Correct `check`'s message.** Say what actually happens: the `id:` line is unusable, `repair`
   will report the file and carry its previous index entry forward as-is, and the fix is to correct
   or delete the `id:` line. Cheapest, and it makes the two commands agree.
2. **Make the claim true** by having `repair` resolve the prefix from `self.spec` when the
   frontmatter `id` is unusable but `sequence_id` and `type` are good, so the entry is genuinely
   refreshed. More work, and it puts spec knowledge into a path that deliberately has none — but it
   is the behaviour the message already promises, and it is strictly better for the operator.

Either way, pin the pair: one test asserting `check`'s wording and `repair`'s behaviour on the same
file, so the two cannot drift into describing one file two ways again. This is the third message in
this review to promise a remedy the tool does not perform (F2's nonexistent
`.overrides/workflow.toml`, F10's "No such file or directory" for a present dirent, now this one) —
worth treating as a pattern rather than three separate wordings.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-08-03T15:20:42Z] Elias Python:
  - Fixed by rewording, resolution (1) — with a wider fault than reported. Driven across the shape family: `id: TASK-abc` and `id: TASK-` rebuild cleanly (exit 0, correct entry); `id: 5`, `id: -19`, `id: [a, b]` are refused by the load boundary, so repair reports the file, carries the previous entry forward and exits 1; and `id: NOTANID` (a string with no hyphen) rebuilds exit 0 but mints an entry whose id renders `UNRESOLVED-<n>`. Three outcomes, so no single sentence about repair could be true — the message now describes the file only and names no other command.
  - The neighbouring clause had the same fault and you did not name it: "Fix the `id:` line (or delete it) to clear this". Driven — deleting the line yields `error <file>: file has no `id` in frontmatter` from check (exit 3) and an error plus carry-forward from repair (exit 1). It swapped one error for another. The message now says removing the line is reported too, and the one action it names is verified to clear both check and repair.
  - Also flagged as its own defect, not fixed here (out of this finding scope): repair accepting a hyphen-less string `id` and indexing an `UNRESOLVED-<n>` entry silently is exactly the outcome `_derive_prefix_from_id`s docstring says it raises to prevent. Routing to @manager to ticket — `prefix_from_id` returns "" for a hyphen-less value and the boundary does not treat that as corrupt.
  - Pinned: `_malformed_id_message` in `_services/_maintenance.py`; tests in `tests/service/test_malformed_frontmatter_id_is_reported_per_file.py` — the wording assertion is now structural (check names no other command at all) over the whole shape family, plus a driven test that the offered remedy clears it and a driven test that deleting the line does not. Falsified: restoring the old sentence reddens 12 of them.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — The per-file message for a bad field is a raw pydantic dump

<!-- sq:finding:F14:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
**Reproduced.** F8's contract holds — no traceback, a clean `SquadsError` — but the text inside it
is a pydantic internal dump, on both commands.

Driven (`labels: 5`):

    $ sq check
    error TASK-000011-three.md: invalid item data in tasks/TASK-000011-three.md: 1 validation
    error for Item
    labels
      Input should be a valid list [type=list_type, input_value=5, input_type=int]
        For further information visit https://errors.pydantic.dev/2.13/v/list_type

and (`id: 5`) the same shape with `input_value={'id': 5, 'sequence_id': ...ion': None, 'extra': {}}`
— the whole payload repr, truncated by pydantic mid-key.

Three things an adopter should not be shown: a link to `errors.pydantic.dev`, which names a library
they did not install and cannot act on; the `[type=list_type, input_value=..., input_type=int]`
machine tail; and a truncated repr of every other field in the file, which buries the one field that
is wrong. The field name plus "Input should be a valid list" is the usable part and it is the middle
line of five.

This is a direct consequence of the fix's own (correct) design decision to make `model_validate`
the single failure channel — the message is now whatever pydantic says, where the old hand-rolled
coercions at least failed in project vocabulary. Worth paying a small formatting cost to keep the
boundary's shape: render `exc.errors()` into one line per bad field — `labels: expected a list, got
int` — rather than `str(exc)`. `Item.from_frontmatter` is the single place to do it, and it is the
same message every degrade-per-file surface now prints, so it is read often.

Low, not blocking: the information is present and correct, and F13 is the one that actually
misleads.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-08-03T15:21:04Z] Elias Python:
  - Fixed at `Item.from_frontmatter` as you scoped it: a new `_validation_message(exc)` renders `exc.errors()` instead of `str(exc)`. `labels: 5` now reads `invalid item data in <path>: labels: Input should be a valid list (got int)`; `id: 5` reads `expected str for `id`, got 'int': 5`; two bad fields join with `; `; a nested one addresses as `subentities.0.status`.
  - One thing your suggestion would have produced that I dropped: appending `(got <type>)` to a validator-raised error stutters, because our own validators already name the type. So the type suffix is added only for pydantic's own error kinds, not `value_error`/`assertion_error`.
  - Pinned as a sweep, not an example: `test_no_shape_leaks_pydantics_own_dump_into_the_message` runs the whole existing 34-shape table against four banned fragments (`errors.pydantic.dev`, `input_value=`, `input_type=`, `validation error for`) — the leak is per error *kind*, not per field, so one shape proved nothing. Plus three tests that the usable half survived (field named, type named, every bad field named, nested path addressed).
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — The (got type) suffix misdescribes an absent field

<!-- sq:finding:F15:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F15:head:end -->

<!-- sq:finding:F15:body -->
Fixed in `_validation_message` (src/squads/_models/_item.py): the (got <type>) suffix now keys on whether the pydantic error kind is a genuine type mismatch (`err["type"].endswith(("_type", "_parsing"))`), not on provenance (ours vs pydantic's).

Took the general fix over the narrow one, per the finding's own preference — verified by driving all 39 shapes plus 2 new ones (a nested missing status/local_id, an empty title) through the boundary and checking every rendered clause: every _type/_parsing kind (including subentities_int_element's model_type and the datetime *_parsing kinds) keeps its suffix, and missing/string_too_short/our own value_error/assertion_error all lose it. No shape regresses.

Test: tests/service/test_type_invalid_frontmatter_load_boundary.py — extended the existing shape table (added subentities_no_status, title_empty) and added a sweep test asserting the rendered (got ...) clause per shape (not just SquadsError), plus a test pinning the finding's exact three clauses verbatim. Falsified: reverted the predicate to the old value_error/assertion_error exclusion, watched the three new tests go red on exactly the three regressed shapes, restored, watched them go green.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T11:09:28Z] Paul Reviewer:
  - Verdict: ChangesRequested. The mechanism works and the asymmetry is preserved correctly (repad/renumber still refuse cleanly, no partial rename), but three of seven findings are high and all three are shapes one step outside the three that were falsified.
  - Blocking: F1 (repair loses an unreadable, never-indexed file\s counter high-water mark -> duplicate TASK-11 across two files, then a real item silently deleted on the next repair with sq check reporting no issues); F2 (valid YAML with no id still aborts repair board-wide, misdiagnosed as a workflow-override re-prefix pointing at a file that does not exist); F3 (type-invalid frontmatter crashes repair with a raw pydantic traceback while sq check says no issues).
  - F1 is the load-bearing property broken: "no item whose file exists may be silently dropped". F3 needs Item.from_frontmatter brought inside the per-file guard - that is the seam. F4 (FileNotFoundError on a present dirent) needs a ruling on absent-vs-unparseable, not a blanket catch.
  - Reproductions are in each finding body, all driven against throwaway squads. @python-dev for the fixes; @tech-lead for the F4 and F5 rulings (absent-vs-unparseable, and how a top-level --json array reports a degraded read).
- [2026-08-03T11:52:21Z] Catherine Manager:
  - Exit-code change needs declaring at release. F6 moves board list and repair from exit 0 to exit 1 when they report an unreadable file. Assessed against the published frozen table: code 1 covers a validation failure, so the old exit 0 while printing an error was itself the contract violation and this brings the behaviour into line rather than breaking it. But it is observable — the VS Code client branches on exit codes, and a script treating board list exit 0 as healthy will now see 1. This earns a Changed entry in the changelog, and the release notes should say plainly which two commands moved and why.
- [2026-08-03T13:18:17Z] Paul Reviewer:
  - Delta pass at 12540ce (src unchanged since ed4a41d; 1f4b721 and 12540ce are docs/board only). Verdict: still ChangesRequested, on one new high finding.
  - Dispositions that hold, driven: F1 — unreadable-with-no-prior-entry now recovers counter=11 from the filename and sq create allocates TASK-12, no collision; the no-id branch folds the floor too. F2 — carried forward, TASK-11 still in list -a, no bogus workflow-override refusal, check names the file. F4 — broken symlink third-stated across check/repair/board/memory, counter absorbed, repad and renumber still refuse before any rename. F5 — messages on stderr with the JSON array shape intact, which is the right call. The legacy pre-migration skill-body exemption holds: a slug-named body with no frontmatter is silently skipped by both check and repair, an ID-prefixed SKILL file missing its id is still an error, and a clean board is clean at exit 0.
  - Blocking F8 (high): the widened boundary catches (ValidationError, KeyError) but six helper calls inside the dict literal raise TypeError/ValueError before model_validate is reached. Swept ten type-invalid shapes — four now clean, six still traceback on BOTH check and repair (labels/refs as ints, extra as a string, subentities as a dict or a list of ints, created_at garbage). Because F3 widened the boundary the same traceback now reaches every single-item verb too. The docstring asserts the guarantee, which is what makes it worse than the pre-fix state. title-as-a-list is the one shape that happens to route through pydantic, which is why one example passed.
  - F9 medium: id: TASK-abc still aborts the whole check scan (clean SquadsError, but zero other items reported) while repair rebuilds the same file silently — number_for_id is unguarded on both the new and the original line. F10 low and F11 info are message quality and a hardening note; neither blocks.
  - On F6: I agree with your reading. Exit 0 while printing error: was the violation — the published table already defines 1 as a command that finished only partly and named what it could not read, so this is filling in a documented code, not moving a frozen one, and check staying at 3 is right. The memory-list gap the writer raised and you ruled on is the same call correctly extended; nothing to add. Note docs/faq.md now states the general rule ("A degraded read is a non-zero exit") while naming only two commands, so the code work closes a documented inconsistency, not just an internal one.
  - Not filed as a finding: _scan_for_check now builds a full Item per file purely to validate it, so sq check gains one pydantic construction per item. Fine at this size; worth a glance in the scale tests since docs/internals.md tracks check cost. @python-dev for F8 and F9.
- [2026-08-03T13:54:27Z] Elias Python:
  - F8/F9/F11 landed together — they were one change. `Item.from_frontmatter` now has exactly two failure channels: required keys read by name up front (SquadsError naming the key), then `model_validate` as the only validator. `_frontmatter_payload` is non-raising by construction; the coercions moved into pydantic or into helpers that pass an unexpected shape through untouched. `SubEntity.from_frontmatter` deleted in favour of a before-validator, so the raw subentities list goes to pydantic.
  - Your six shapes were the floor: the sweep found ten. Also tracebacking before the fix — `extra: [1, 2]`, `subentities: oops`, `updated_at: not-a-date`, `id: 5`, `id: [a, b]`. All ten now clean on check, repair and every single-item verb.
  - Tests: `tests/service/test_type_invalid_frontmatter_load_boundary.py` — 34 shapes over field × wrong type, each driven through the boundary itself, `check`, `repair` and six single-item verbs (315 cases). Its coverage guard asserts the table against `Item.model_fields`, so a new model field fails the module until a shape exists for it. Falsified: restoring the `list(labels or [])` and `dict(extra)` coercions turns 27 of them red, then green again on restore.
  - `created_at: 5` is deliberately outside the refusal contract and pinned as such — pydantic reads a number as a Unix epoch, which beats the old `else: return now()` that made a corrupt timestamp indistinguishable from a fresh one.
  - F9: repair does not rewrite the `id:` line at all, so there was nothing silently rewritten to report — the line is simply never read. Resolved the disagreement the other way: `check` always reports it (per file, scan continues, saying the value is ignored and why), `repair` rebuilds without complaint, `renumber`/`repad` refuse cleanly. All three directions pinned. Also closed the same hole in `_scan_records`, which still threw a raw AttributeError on `id: 5`.
  - F11: the `KeyError` arm is gone entirely, so an internal spec-lookup miss can no longer be relabelled `invalid item data in <path>`. @reviewer
- [2026-08-03T13:56:45Z] Catherine Manager:
  - Driven during release prep, on a throwaway squad with one chmod-000 item file: sq search exits 1 with EMPTY stdout, so a single unreadable file kills the whole result set instead of degrading per-file and returning the matches it could read. Everything else holds -- list/tree/blocked read the index and exit 0 with both items, and show on the unreadable item exits 1, which is correct.
  - Two reasons this matters for 0.13 rather than later. It is the same per-file-degradation family this review covers, so search looks like a surface the work missed. And the VS Code client calls search and turns any non-zero exit into a runtime error (sqAdapter classifyNonZeroExit), so extension search breaks entirely on a squad where the tree views keep working -- arbitrary from the user side.
  - @reviewer your call whether this is a finding here or its own bug; I have not authored one, and I would rather you re-drive it than take my probe on trust. Not sending it to @python-dev mid-round as a scope addition.
- [2026-08-03T14:17:50Z] Elias Python:
  - Adopter-visible, for routing: a corrupt frontmatter field now yields a clean `invalid item data in <path>` error instead of a traceback on every verb; `sq check` reports a malformed `id:` per file instead of aborting the scan; `sq renumber`/`sq migrate repad` refuse cleanly on one. Also a tightening worth a line: `labels: abc` (a bare string) is now rejected rather than silently split into one label per character. Not mine to document.
- [2026-08-03T14:33:57Z] Paul Reviewer:
  - Third pass on the load boundary at e59c10b. F8 itself holds — I swept it myself rather than reading his sweep. 46 frontmatter shapes through Item.from_frontmatter on a real item file, 25 of them shapes neither of us had named (a dict labels, an int-element list, a non-str id, severity/priority/parent/title/slug/author/assignee/description/created_session as wrong types, a list-of-lists subentities, a sub-entity missing status, a sub-entity with a non-dict extra, a non-str ref_kinds value, a non-dict ref_kinds): ZERO raw escapes. Every failure is a SquadsError, and BASELINE-untouched loads, so the probe is not vacuous. The design is what earns it — _frontmatter_payload never raises and model_validate is the single channel — not a wider except clause.
  - The KeyError claim holds and I traced it rather than taking it: three data[...] subscripts, all covered by the REQUIRED_FRONTMATTER_KEYS pre-check; fold_legacy_kinds uses legacy.get and is gated on _is_str_list; make_ref is an f-string so a non-str kind cannot raise; prefix_from_id and _slug_from_path only ever see a real str; _extra_mapping and _read_extra never coerce a non-mapping; and the removed SubEntity.from_frontmatter has no stale caller anywhere in src, tests or clients. One note for whoever touches it next: _frontmatter_payload documents "callers must have checked the required keys first" and has exactly one caller, so a second caller that skips the check reopens the hole — KeyError is deliberately no longer caught. Worth a one-line assert rather than a docstring, but not a finding.
  - Blocking F13 (medium, new): check tells the operator that a malformed id is being ignored and that sq repair "rebuilds the index from this file without complaint". Driven: repair DOES complain, third-states the file and carries the previous entry forward stale. The claim also cannot be made true by rewording repair — _derive_prefix_from_id now raises on a non-str id for a good reason, and from_frontmatter holds no spec, so it cannot derive the prefix from sequence_id plus type the way the message promises. Body has both coherent resolutions. That is the third message in this batch to name a remedy the tool does not perform; worth treating as a pattern.
  - F12 low, and it answers your question directly: the preserved-compat case covers only the two fields he names. subentities and extra were coerced by the same or-default and both loaded with an empty string before this commit — I evaluated the removed expressions literally to be sure. The compat test parametrizes labels and refs only, so neither regressed field is pinned either way. Low because the failure is clean, reported per-file, and carried forward, and sq never writes either key empty. On labels: abc — I endorse rejecting it; list("abc") produced three one-character labels, which was garbage in every view, so no working file depends on it.
  - F14 low: the per-file message for a type-invalid field is now whatever pydantic says, errors.pydantic.dev URL and truncated payload repr included. Direct consequence of the correct decision to make model_validate the single channel; render exc.errors() into one line per field instead of str(exc). F10 is still Open from the last round.
  - Falsification quality checked, not assumed: the sweep test carries its own coverage guard so an omitted shape reddens there rather than in someone repo; the blast-radius test exists specifically so a fix that refuses every verb on every item cannot pass; and the boundary-level assertion is ordered before the two command-level ones so they cannot pass by accident. Those fail for the stated reason. @python-dev for F13; F12 and F14 are cheap and I would take them in the same pass.
- [2026-08-03T14:34:14Z] Paul Reviewer:
  - On the search defect you left for me to classify — reproduced independently, and it is wider than your probe found. Throwaway squad, three tasks, chmod 000 on one of them.
  - sq search login: EMPTY stdout, exit 1, one clean error on stderr naming the file. The match on TASK-9 — a readable file, matched on its title from the index before any file read — is discarded with everything else. sq search login --json emits nothing at all on stdout, not even [], so a JSON consumer gets a parse failure on top of the non-zero exit.
  - It is TWO commands, not one: sq inbox reviewer behaves identically (empty stdout, exit 1) and loses the readable item mention. Same mechanism, same file: _services/_collab.py, both loops do full_text = await _aio.read_text(path) with no per-item guard, so UnreadableFileError propagates out of the loop and discards the accumulated results. Meanwhile list, tree, blocked, mine and workload all exit 0 with everything, check exits 3 and degrades per file, show on the unreadable item exits 1 which is correct.
  - Client impact confirmed at the source, not inferred: clients/vscode/src/sqAdapter.ts line 531 calls search with --json through runSqJson, which at line 426 turns any non-zero exit into classifyNonZeroExit, and 1 is neither 2 nor 3 so it becomes kind runtime-error. So extension search dies on a squad where the tree views keep working. inbox is not in the client, but every agent role definition tells the agent to run sq inbox at session start, which was TASK-674 own stated motivation.
  - My classification: its own bug, in 0.13, not a finding on this review and not 0.14. Not a finding — TASK-674 scoped itself to check, repair, board list and memory list by name, and never claimed search or inbox, so none of the six fixes regressed this and none of the eleven findings covers it. Not 0.14 — the release notes will say unreadable files degrade per file, and shipping that sentence while two read commands still die whole is a promise the product does not keep; one of the two is consumed by the VS Code client. I would file it high: total loss of results already gathered from readable files, plus a client runtime error, on a board the tree views handle fine. Bugs are the QA lane, so I am recording the reproduction here rather than authoring it. @qa @manager
- [2026-08-03T14:34:45Z] Theo Writer:
  - Release notes written for this round: four entries covering the malformed-`id` per-file report, the type-invalid frontmatter boundary (with the `labels: abc` tightening and the `created_at` change), the `sq inbox` empty-hit fix, and the new playbook-guidance warning. Each driven against `e59c10b^` as baseline rather than translated from the round's comments.
  - Corrections to what the round reported, found by driving it. (1) The old `sq check` failure on a malformed *string* id was not a traceback — it was a bare `error: malformed ID 'NOTANID'` that did not name the file, and it stopped at the first one (two broken files reported one). The traceback shape belongs to the non-string case (`id: 5` → `AttributeError: 'int' object has no attribute 'rpartition'`). Two different old symptoms, so the entry states both precisely. (2) `labels: abc` did not merely split — `sq check` reported `✓ no issues` on a corpus silently carrying the three labels `a`/`b`/`c`, which is the part worth telling an adopter. My first probe on this read the index rather than the frontmatter and showed nothing; forcing a rebuild is what surfaced it, so I am flagging the probe error too.
  - DEFECT at the seam of two fixes from this round, not documented and not mine to fix (no Python in my scope). The malformed-`id` check message asserts "so `sq repair` rebuilds the index from this file without complaint" — true for a malformed *string* id (`id: NOTANID` → repair exit 0, silent) but FALSE for a wrong-typed one (`id: 5` → repair prints `invalid item data ... expected str for id`, carries the previous entry forward, exit 1). The new type-invalid load boundary rejects the file before the id-parsing question arises, so `check` promises an outcome the adopter will not get. `sq renumber`'s refusal reuses the same sentence verbatim, where it is doubly misleading. Source: `_malformed_id_message` in `_services/_maintenance.py`, whose own docstring states the promise as intended behaviour. @manager for routing — I kept the promise out of the changelog entirely rather than repeat it.
- [2026-08-03T15:22:06Z] Elias Python:
  - F10, F12, F13, F14 all Fixed — see each finding for what was driven and what was pinned. Gates clean: pyright 0 errors, ruff check + format clean (all with --all-extras); tests/meta, unit, service, integration, cli, tui all pass (3019 tests). Every fix falsified by reverting it and watching the intended tests redden.
  - Adopter-visible, for @tech-writer to route (I did not touch CHANGELOG or docs): (1) the malformed-frontmatter-`id` report no longer promises a `sq repair` outcome and no longer offers "delete the line" as a fix — it names the required `<PREFIX>-<number>` shape and the correction; (2) a type-invalid frontmatter field now reports in project vocabulary (`labels: Input should be a valid list (got int)`) instead of a raw pydantic dump with an errors.pydantic.dev link; (3) `sq migrate repad` / `sq renumber` now diagnose a broken symlink the same way `check`/`repair` do, instead of "No such file or directory"; (4) `subentities: ''` and `extra: ''` load as empty again, matching `labels`/`refs`.
  - One new defect found while driving F13 and NOT fixed (needs its own ticket, @manager): `sq repair` accepts a hyphen-less string `id` (e.g. `id: NOTANID`), exits 0, and indexes an entry whose id renders `UNRESOLVED-<n>` — the exact outcome `_derive_prefix_from_id` raises on non-strings to prevent. `prefix_from_id` returns "" for a hyphen-less value and nothing treats that as corrupt. I deliberately did not pin the current behaviour, since a test asserting it would enshrine it.
- [2026-08-03T15:31:53Z] Paul Reviewer:
  - Targeted delta at 8473abf, scoped to what the widening created. One new low finding (F15); everything else in scope holds.
  - On the three-outcome call for F13: I accept it, and it is the right call. Drove all four id shapes. TASK-abc rebuilds cleanly as TASK-10 at exit 0; a non-string 5 is refused by the boundary so repair reports it and keeps the previous entry, exit 1; TASK and NOTANID both rebuild at exit 0 and index UNRESOLVED-10. Three outcomes, and the message is reused verbatim by renumber which refuses outright, so no sentence about another command could be true. Saying less is correct here. And it still says enough to act: the bad value, the required grammar, why the line is load-bearing, the exact action, and the two inputs to compute it (sequence_id in the same file, the type prefix). The only thing it does not name is how to look the prefix up — sq workflow types — and I would not add it; the message is already five lines.
  - The neighbouring clause he fixed unasked is correct and I verified the action clears both shapes, which is the part worth checking. Starting from id: TASK and from id: 5, correcting the line to TASK-10 gives check exit 0, repair exit 0, and the entry indexed as TASK-10 in both cases. Deleting the line instead gives error <file>: file has no id in frontmatter at exit 3 plus a repair carry-forward at exit 1 — so the old "(or delete it)" was a false remedy and removing it was right. The replacement pre-empts the obvious wrong move by saying removing the line is reported too, which is better than silence.
  - F15 (low, new): the (got <type>) suffix keys on error provenance rather than on whether the type is the missing information. Swept 39 shapes and read every clause — 36 read well, but pydantic missing carries the ENCLOSING mapping as its input, so subentities.0.status: Field required (got dict) reads as "status was given a dict" when the fault is that it is absent; and title: String should have at least 1 character (got str) is a stutter. Field path is right in all three, so it is the parenthetical only. One predicate fixes it; body has both the narrow and the general version.
  - Not re-verified: the dispositions confirmed across the three previous passes. @python-dev for F15.
- [2026-08-03T15:47:22Z] Catherine Manager:
  - Approved as second party -- the reviewer authored this, so the decision is mine. Fifteen findings, zero Open: eleven Fixed, two WontFix with reasoning that engages the evidence, one delivered by the writer, one (F7) closed as not-a-defect. Full suite 3076 passed, pyright 0 errors, ruff and format clean, sq check exit 0, all verified by me rather than taken from the reports.
  - Recording the shape of this review because it cost five rounds. Rounds one to three found defects in the mechanism; round four found a message promising a remedy the tool does not perform; round five found a parenthetical describing an omission as a value. Every round found something the previous fix created, so that pattern held throughout -- but the severity collapsed monotonically, which is convergence rather than recurrence. Two follow-ups the dev raised were dispositioned without tickets: repair minting UNRESOLVED-<n> is honest and reported at error level, and the workflow-lint false pointer was reproducible when flagged and is not now, closed by commit 2997383. Both answers came from driving, one of them from the reporter contradicting his own earlier claim.
<!-- sq:discussion:end -->
