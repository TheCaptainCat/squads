---
id: REV-1163
sequence_id: 1163
type: review
title: 'Review: confirm duplicate-id groups in check'
status: Approved
author: reviewer
refs:
- BUG-1154
description: Review of 0f92eca7, the BUG-1154 fix
subentities:
- local_id: F1
  title: 'Shared-number report in check has the same rename race: a retype during
    the scan reports a false numbers_unique error'
  status: Verified
  severity: medium
- local_id: F2
  title: Confirmation drops a real duplicate when one copy is renamed between the
    listing and the re-read
  status: Verified
  severity: low
- local_id: F3
  title: repair --renumber number scan globs folders lazily; a retype mid-scan aborts
    it with a raw FileNotFoundError
  status: Verified
  severity: low
- local_id: F4
  title: repair --renumber rewrites files without the index lock; a concurrent retype
    is half-applied or resurrected
  status: Verified
  severity: medium
- local_id: F5
  title: The write-guard change stops the autouse write rule from observing repair's
    index rebuild
  status: Verified
  severity: medium
- local_id: F6
  title: repad writes the padding from the read-scope snapshot, so a counter bumped
    before the lock regresses
  status: Verified
  severity: low
created_at: '2026-10-26T10:10:16Z'
updated_at: '2026-10-26T12:03:40Z'
---
<!-- sq:body -->
Review of commit 0f92eca7 (release/0.17): `check()` now re-reads each duplicate-id group (`confirmed_groups` in `src/squads/_services/_duplicate_ids.py`) before reporting it, so a file renamed during the scan is not counted twice.

Scope: the diff, the scan/listing/confirm read paths, `sq repair` and `repair --renumber` scans, the two tests, the CHANGELOG entry.

Driven on a scratch squad (121 milestones + 1 task), dev build 0.17:
- Bug repro, retitle loop vs `sq check`: fixed build 0 false reports in 63 runs; the same build with the confirmation removed 13 in 62.
- Retitle loop vs `sq repair` (113 runs, with and without `--renumber`): no false duplicate, no renumber, no missing item.
- Shape table (in-process, fixed vs unconfirmed): same-id copies with padded id, unpadded file name, other type's folder, other prefix in the name, CRLF endings, and a parent with subtasks are all still reported; broken frontmatter, an unreadable copy and a lowercase-prefix id are skipped the same way before and after. The re-read uses the same parser and normalization as the scan.
- Mutation: removing the confirmation makes the rename test fail; a confirmation that drops every group makes the real-duplicate test fail.
- Targeted pytest (`-k "duplicate or same_id or renumber"`, -n 4): 175 passed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1163 add-finding "…" --severity medium`; track with `sq review 1163 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Shared-number report in check has the same rename race: a retype during the scan reports a false numbers_unique error

<!-- sq:finding:F1:body -->
`check()` builds the shared-number report from the same scan-plus-listing pairs as the duplicate-id report (`shared_number_groups(carriers)`, `_check.py` right after the new `confirmed_groups` call), but only the duplicate-id groups are re-read. The scan globs each type folder when it reaches it, so a `retype` that moves a file to a folder scanned later (task to bug, feature to task) is read once in each folder under two different ids with the same number.

Failure scenario, driven on the fixed build: one process runs `sq task 123 retype bug` / `sq bug 123 retype task` 120 times while another loops `sq check`. 17 of 106 runs reported `error #123: 2 files carry number 123 under different ids (bugs/BUG-000123-flip.md, tasks/TASK-000123-flip.md); run sq repair --renumber ...`, exit 3. Reproduced deterministically in-process by retyping inside `_scan_text` right after the task file is read. The shared-number branch also pops the number from `on_disk`, so the per-item checks for that item are skipped in that run.

This is the same race as BUG-1154 on the sibling rule; the CHANGELOG entry reads as if the rename race is closed for check.

Fix direction: confirm shared-number groups the same way before reporting them and before dropping the number from `on_disk` (re-read the group's files and regroup by number), and add a test that retypes during the scan.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T10:23:29Z] `python-dev` Elias Python:
  - check now confirms shared-number groups too: files are re-read and regrouped by number before the report and before the number leaves the per-item checks. Deterministic retype test added; a real shared number is still reported.
- [2026-10-26T10:41:11Z] `reviewer` Paul Reviewer:
  - Verified on b921ce72. Retype loop against `sq check` (CLI, 122-item squad): 0 false reports in 108 runs (17/106 before). In-process retype right after the scan reads the task file: no `numbers_unique` or `ids_unique` error. Making `confirmed_shared_numbers` return its input fails the new retype test.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Confirmation drops a real duplicate when one copy is renamed between the listing and the re-read

<!-- sq:finding:F2:body -->
`confirmed_groups` re-reads only the paths already in the group. When a real duplicate's copy is renamed after the listing and before the re-read (a retitle of the indexed copy), the renamed copy's old path is gone, its new path is not in the group, and the group falls below two files. The duplicate is silently not reported for that run. Before this change it was reported (with the stale name).

Failure scenario, driven in-process on the fixed build: two files carry TASK-2 (`TASK-000002-alpha.md`, `TASK-000002-copy.md`); `alpha` is renamed to `gamma` between `_id_carriers` and `confirmed_groups`; `check()` returns no `ids_unique` issue. The same holds for two renames in a row (old to mid during the listing, mid to new before the re-read) when a real copy exists.

Impact is a transient false negative: the next `sq check` reports it. Low severity, but it is the inverse of the bug the change fixes and nothing pins it.

Fix direction (simple): when a group member is gone on the re-read, also read the files in that member's folder whose name carries the group's number (`name_number`) before regrouping, so a renamed copy is found under its new name. Add a test for a real duplicate renamed between listing and confirmation.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T10:23:30Z] `python-dev` Elias Python:
  - Confirmation re-lists the type folders (no extra reads) and reads the group plus files whose name carries the number, so a copy renamed after the listing is found by its new name. Test added.
- [2026-10-26T10:41:13Z] `reviewer` Paul Reviewer:
  - Verified on b921ce72. In-process, a real duplicate whose copy is renamed during the carrier read, or moved old to mid during the carrier read and mid to new before the fresh listing, is reported under its new name. Dropping the re-list from `_candidates` fails the new test. A rename after the fresh listing and before the re-read still drops the group for one run. That window is now a single folder glob followed directly by the reads, and the next check reports the duplicate; accepted as residual. Cost: `sq check` on a 2003-item squad took 24.9/24.7 s (pre) vs 26.3/23.9 s (post) per 5 runs, which is within noise.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — repair --renumber number scan globs folders lazily; a retype mid-scan aborts it with a raw FileNotFoundError

<!-- sq:finding:F3:body -->
The handoff says `sq repair` reads its carriers once, so it does not have the check race. That holds for the same-id path (`_id_carriers` lists every folder eagerly; a rename seen under both names fails the read of the old name and is skipped; 113 CLI runs against a retitle loop gave no false duplicate). It does not hold for the number-collision pass of `repair --renumber`: `_renumber()` scans through `_scan_records`, which globs each type folder lazily, so a `retype` between the tasks and bugs folder globs yields the file under both ids with one number.

Failure scenario, driven in-process (retype fired at the second read of the task file): `_renumber_plan` plans to renumber one of the two records, `_apply_remap` then reads the moved path and the run aborts with a raw `FileNotFoundError`, which `@handle_errors` does not catch, so the CLI prints a traceback. No file content was changed in the probe (the vanished path sorts first in scan order). Not hit in 96 CLI runs of retype vs `repair --renumber`, so the window is narrow.

Pre-existing and outside the diff; recorded because the handoff states repair is not exposed. Fix direction: list the folders once before reading in `_scan_records` (as `_all_item_files` does) and turn a vanished path into the existing `missing_dirent_message` refusal, or drop records whose file vanished before planning.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T10:23:31Z] `python-dev` Elias Python:
  - The renumber scan lists the folders once and skips a file that vanished before its read (a dangling symlink still refuses as before). Test added.
- [2026-10-26T10:41:15Z] `reviewer` Paul Reviewer:
  - Reopened. The change covers a file that vanishes between the eager listing and its read, and the new test pins that (it fails without the skip). It does not cover this finding's own scenario: the retype fires after `_scan_records` has read the file. Driven in-process on b921ce72, with a real TASK-2/BUG-2 collision plus TASK-3 referring to TASK-2, and TASK-3 retyped to bug at its second read: `repair --renumber` still aborts with a raw `FileNotFoundError` on `tasks/TASK-000003-xref.md`. It now does so after `rewrite_ids` has already rewritten `tasks/TASK-000002-alpha.md` to `id: TASK-4`. The corpus is left half-renumbered: the file is still named 000002, and BUG-3 still says TASK-2. Not hit in 94 CLI runs of retype against `repair --renumber`; that run had 44 retype refusals. Root cause and fix direction are in F4.
- [2026-10-26T10:53:33Z] `python-dev` Elias Python:
  - Closed by the lock in F4: no writer can move a file between the scan and the apply. The vanished-file skip stays as a guard.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — repair --renumber rewrites files without the index lock; a concurrent retype is half-applied or resurrected

<!-- sq:finding:F4:body -->
`repair --renumber` reads every item file, plans the remap, then rewrites and renames files (`_renumber` → `_scan_records` → `_apply_remap`) without holding the index lock that `retype` and every other writer take. A writer that moves or rewrites a file between the scan and the apply invalidates what the apply writes.

Driven in-process on b921ce72, with a real TASK-2/BUG-2 collision and TASK-3 referring to TASK-2:
- retype of TASK-3 at its second read (inside `_scan_records`): a raw `FileNotFoundError` after `TASK-000002-alpha.md` was rewritten to `id: TASK-4` but not renamed (F3).
- retype of TASK-3 at its third read (inside the apply): the run succeeds, but the rewrite writes the old path back. Both `tasks/TASK-000003-xref.md` (id TASK-3) and `bugs/BUG-000003-xref.md` (id BUG-3) now exist, so the retype is partly undone and a number is shared.

Fix direction (simple): hold the store lock (`transaction()` or the same lock layer) from the start of `_renumber`'s scan through the apply, so a concurrent writer waits instead of interleaving. That also closes F3 without the per-file skip. Test: a writer that retypes a file at each read point of the renumber pass; the corpus must end consistent (one file per id, file names matching ids, references rewritten).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T10:53:31Z] `python-dev` Elias Python:
  - New IndexStore.exclusive() holds the three-layer lock; repair and renumber run their whole pass (first file read to the index commit) inside it, and overwrite() does not re-take the lock there. A concurrent retype now waits (tests start one at the scan, the apply and the rebuild and assert it has not run until the pass returns; all red without the lock). A plain repair had the same gap and is covered; the test write guard now opens a unit only once its lock is held.
- [2026-10-26T11:16:19Z] `reviewer` Paul Reviewer:
  - Verified on cc28a330. In-process, with a real TASK-2/BUG-2 collision and TASK-3 referring to TASK-2, another service retyped TASK-3 at its 1st, 2nd, 3rd and 4th read during `repair --renumber`. The retype waits every time. Every run ends with the same consistent board: BUG-3 says TASK-4, TASK-000004-alpha.md carries id TASK-4, and check reports no error. CLI, retype loop vs `repair --renumber`: no failed repair and no refused retype in 120 runs (44 retypes were refused before). Removing the `exclusive()` wrapping fails all four new tests.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The write-guard change stops the autouse write rule from observing repair's index rebuild

<!-- sq:finding:F5:body -->
`tests/_write_guard.py` now pushes a unit onto the stack only after `inner` is entered. For a transaction that is right: a transaction waiting for the lock is not yet the writing unit. For the rebuild unit it removes the check entirely. `inner` there is `_Awaited(real_rebuild(...))`, whose `__aenter__` runs the whole rebuild, so the unit is pushed only after every rebuild write and the `overwrite` have happened. The autouse rule (one write per item file per unit, no item write after the index commit) therefore no longer observes `_rebuild_index_from_disk`, the one unit that is not a transaction.

Failure scenario, driven in a scratch copy at cc28a330: moving the rebuild's pending-file loop after `await self.store.overwrite(db)` (markdown behind the index, invariant 8). With the old guard, 24+ tests report `_rebuild_index_from_disk: ... written after the index commit`. With the new guard, 2 of 2232 repair/write tests fail. A double write in the same loop is still caught, but only by the dedicated `ledger.seen` asserts in `test_repair_and_sync_write_each_item_file_once.py`, not by the autouse rule.

Fix direction: keep the late push for transactions and give the rebuild unit the old shape (push, then await the rebuild), for example by making `_Awaited` a pass-through and wrapping the rebuild call itself. Pin it with a guard self-test that a rebuild writing after the index commit is reported.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T11:27:05Z] `python-dev` Elias Python:
  - Write guard: a unit now opens after its lock is held for transactions, and before its work for the repair rebuild (after_enter=False). Self-test added: a write after the rebuild commit is reported (red under the late push). Also repad: its renames, padding write and rebuild now run inside exclusive(); a retype started during its scan waits (test added, red without the lock).
- [2026-10-26T11:38:55Z] `reviewer` Paul Reviewer:
  - Verified on 92859d65. Re-ran the mutation that moves the rebuild's file writes after the index commit: 36 guard errors ("written after the index commit") and 2 failures, against 2 failures with the previous guard. Setting the rebuild unit back to `after_enter=True` fails the new guard self-test.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — repad writes the padding from the read-scope snapshot, so a counter bumped before the lock regresses

<!-- sq:finding:F6:body -->
`_repad_held` now writes the new padding with `stored = await self.store.load()` followed by `overwrite(stored)`. The transaction it replaced always read the index from disk. `load()` instead returns the invocation's read-scope snapshot when one is filed. Every `@common.command` binds a read scope, and `sq migrate repad` calls `svc.store.load()` before `svc.repad()`, outside the lock. So the index written under the lock is the snapshot taken before the lock: a writer that committed in between is overwritten. The rebuild that follows restores items from their files, but it takes the counter from that stale index, so a number allocated in the window and then freed is lost (invariant 2, global counter).

Driven in-process at 92859d65, with a read scope bound as the CLI does: the svc loads (counter 2); another service creates TASK-3 and removes it (counter 3 on disk); `svc.repad(7)`; the counter after repad is 2, so the next create reissues 3. With `self.store.load(fresh=True)` in that line the same probe ends at counter 3. The other repad tests pass with or without the change.

Fix: `load(fresh=True)` for the padding write (and preferably for the padding comparison at the top of `_repad_held`), plus a test like the probe above.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T11:50:05Z] `python-dev` Elias Python:
  - Every index read inside repair, renumber and repad (repad padding check and write, renumber counter and padding, the collision pass padding, the no-op return) now uses load(fresh=True); the repair previous-index read already bypassed the cache and the rebuild reads none. Test: a counter advanced by another writer after a cached read survives repad (red with the cached read); the same probes for repair and renumber pass either way.
- [2026-10-26T11:58:54Z] `reviewer` Paul Reviewer:
  - Re-checked on e0f74aa3; reopened for the renumber test only.
    - Repad: the counter probe now ends at 3 (it was 2 before the fix). The new repad test pins it.
    - Renumber: the cached read can roll the counter back, so it must be pinned. `_renumber_held` validates `--by` and computes the `--onto` offset against the counter it read, then passes that counter to the rebuild as `previous_counter`. Driven with the cached read restored: the svc caches counter 2, another service creates and removes TASK-3, and `renumber(from_seq=2, by=1)` is accepted and remaps TASK-2 to TASK-3. That reissues the freed number. With two numbers freed in the window (actual counter 4), the counter after renumber is 3. With the fix, the same calls are refused as unsafe ('--by 1 is unsafe') and the counter stays at the actual value.
    - The new renumber test cannot see this because `by=expected + 10` clears any counter. Fix: use the minimal offset judged against the cached counter (`by = cached + 1 - from_seq` on the top item), and assert that the call is refused, or that no remap target is at or below the actual counter and that the counter does not drop.
    - The collision-pass padding read only matters if a repad ran in the window. Padding only grows, and the rebuild takes the widest file name as its floor, so I accept it without a test.
- [2026-10-26T12:02:47Z] `python-dev` Elias Python:
  - Renumber test rewritten: with the cached counter equal to the top item, by=1 looks safe against the cache but is refused as unsafe against the real counter; it goes red with the cached read restored.
- [2026-10-26T12:03:38Z] `reviewer` Paul Reviewer:
  - Verified at 381fa371: test_renumber_refuses_an_offset_only_safe_against_a_cached_counter passes, and fails with the cached read restored in _renumber_held.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T10:11:10Z] `reviewer` Paul Reviewer:
  - Verdict: changes requested. The fix closes the reported race: retitle vs check went from 13/62 false reports to 0/63, the tests fail when the confirmation is removed, and no same-id shape is dropped by the re-read.
  - F1 (medium): the shared-number rule in the same check has the same two-read race; a retype loop gave 17/106 false numbers_unique errors on the fixed build.
  - F2 (low): a real duplicate is not reported for one run when its copy is renamed between the listing and the re-read.
  - F3 (low, pre-existing): repair --renumber number scan sees a retyped file twice and aborts with a raw FileNotFoundError (in-process only).
  - @python-dev F1 and F2 belong to this fix; F3 can be split off if preferred.
- [2026-10-26T10:41:24Z] `reviewer` Paul Reviewer:
  - Re-review of b921ce72: F1 and F2 are verified. Retype vs check gave 0 of 108 runs, retitle vs check 0 of 62, and check is no slower on 2003 items. All three fix mutants were killed.
  - F3 is reopened: the scenario still aborts repair --renumber when the retype lands after the scan reads the file, now after part of the renumber is written. F4 (medium, new) is the root cause: renumber rewrites files without the index lock, and a retype during the apply is resurrected. Verdict stays changes requested. @python-dev F3+F4: hold the store lock across the renumber pass.
- [2026-10-26T11:16:21Z] `reviewer` Paul Reviewer:
  - Re-review of cc28a330: F3 and F4 are verified. The races still hold at 0 hits: retype vs check 0/71, retitle vs check 0/62, retype vs repair --renumber 0 failures in 120 runs.
    
    New F5 (medium, test harness): the write-guard change stops the autouse rule from observing the repair rebuild, so moving its markdown writes after the index commit goes from 24+ guard violations to 2 failing tests. Verdict stays changes requested on F5 alone. @python-dev
- [2026-10-26T11:16:23Z] `reviewer` Paul Reviewer:
  - Lock judgment (driven unless marked):
    - Deadlock: none of repair's callers hold the lock when they call it (migrate up runs it after the runners, repad after its transaction closes, init/adopt/sync outside any transaction; read, not driven). A transaction opened inside the pass fails loudly on the non-reentrant anyio lock instead of hanging. Two concurrent `sq repair` runs serialize: 4003 items, the second waited and succeeded.
    - Context variable: it is set and reset in the same task and compared by store identity. A child task inherits it only while the pass holds the lock, and `overwrite` is never called from a thread. Sound for the current code.
    - Hold time: a writer started during repair waits. At 4003 items it waited about 4 s and succeeded. At 12003 items repair held the lock about 15 s, and the writer failed after the 10 s timeout with 'the index lock ... is held by another sq process; nothing was written, retry the command'. It is a clean, retryable refusal and repair is an admin command, so acceptable; noting the threshold, which is around 8k items on this box.
    - Read, not driven: `repad` renames every item file before its transaction and outside the lock, the same shape as F4. It is pre-existing and not part of this change.
- [2026-10-26T11:38:57Z] `reviewer` Paul Reviewer:
  - Re-review of 92859d65: F5 is verified. Repad holds the lock with no deadlock: it uses `_repair_held` inside the pass, and the retype-during-repad test and every existing repad test pass. The reflog entry has the same op, target, delta and session fields as before, and `append_line` keeps the never-raise contract. The padding write still comes after the renames (markdown first, then the index).
    
    New F6 (low): the padding write reads the index through the invocation's read scope instead of from disk, so a counter bumped between the CLI's pre-lock load and the lock regresses (driven: 3 back to 2). The fix is one argument (`fresh=True`). Verdict stays changes requested until F6 lands. @python-dev
- [2026-10-26T11:58:55Z] `reviewer` Paul Reviewer:
  - Re-review of e0f74aa3: the code is correct for repad and renumber, and the repad test pins it. F6 stays open because the renumber fresh read is unpinned and a cached read there reissues a freed number (driven). Once a minimal-offset renumber test pins it, this is approvable. @python-dev
- [2026-10-26T12:03:39Z] `reviewer` Paul Reviewer:
  - Verdict: approved. F1 to F6 are all verified.
<!-- sq:discussion:end -->
