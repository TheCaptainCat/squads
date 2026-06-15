---
id: REV-000116
sequence_id: 116
type: review
title: TASK-000111 — Sanctioned item removal (sq remove) review
status: Approved
author: reviewer
refs:
- TASK-000111:addresses
- FEAT-000023
- ADR-000114
subentities:
- local_id: F1
  title: Unlink runs after the transaction commits, not inside it
  status: Verified
  severity: medium
- local_id: F2
  title: Width-tolerant ref matcher forked instead of shared
  status: Verified
  severity: low
created_at: '2026-06-15T09:02:53Z'
updated_at: '2026-06-15T09:20:30Z'
---
<!-- sq:body -->
Review of TASK-000111 (FEAT-000023, sanctioned item removal) against ADR-000114. Scope: FEAT-23 `remove` only (FEAT-20 retype changes pre-approved in REV-000115 — confirmed the two REV-115 cleanups in _retype.py are harmless and untouched here).

Gate: `uv run pytest` 652 passed / 1 skipped, `pyright` 0 errors, `ruff check` clean, `ruff format --check` clean.

ADR-000114 conformance — PASS on the core: hard delete in one transaction (del db.items[seq]); db.counter never touched (verified in code + test_remove_work_item_counter_never_shrinks_and_repair_respects_gap); default refuses on incoming refs OR children with offender lists; --force severs incoming refs from referrers' frontmatter in the same transaction (sq check clean after — tested); children NOT auto-reparented, blocked even under --force; no tombstone / no bespoke audit code — the _reflog_stub is a genuine no-op local awaiting TASK-000112; Invariant 1 holds (repair rebuilds consistently, gap survives). --yes / --json / interactive confirm all present and correct; output escaped via e().

Two findings (see F1/F2). F1 (medium): the .md unlink runs after the transaction commits rather than inside it — a crash in that window resurrects the item on next repair; diverges from ADR §1's 'in one transaction'. F2 (low): the width-tolerant matcher is forked rather than shared as ADR §3 instructs; promote it to _item.py. Verdict: ChangesRequested — F1 is the load-bearing one (this is the destructive verb; the failure mode points the wrong way). F2 should ride along.

Verdict: ChangesRequested.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 116 add-finding "…" --severity high`; track with `sq review 116 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Unlink runs after the transaction commits, not inside it |
| F2 | 🟢 low | Verified |  | Width-tolerant ref matcher forked instead of shared |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Unlink runs after the transaction commits, not inside it

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
ADR-000114 §1 specifies removal unlinks the .md AND deletes the index entry `in one store.transaction()`. In `remove_work_item` (_services/_items.py) the `del db.items[seq]` is committed when the `with self.store.transaction()` block exits (atomic os.replace), but `path.unlink(missing_ok=True)` runs *after* the block, outside the lock.

Failure mode: if the process dies between the index commit and the unlink, the index entry is gone but the orphaned .md remains on disk. The next `sq repair` scans `.md` files (_maintenance.py:194) and re-`add`s the item — resurrecting the 'removed' item with its old sequence number. That is the opposite of the safe failure mode.

Compare: unlinking *before* the index write (inside the transaction) gives the safe direction — a crash leaves the .md gone with the index still referencing it, which `sq check` flags and `sq repair` cleans by dropping the entry. Recommendation: move the unlink inside the transaction body, before commit (counter still untouched, so the gap invariant is unaffected). The window is narrow and the squad is version-controlled, hence medium not high — but it both diverges from the ADR's literal contract and bites in the wrong direction.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-15T09:15:14Z] Elias Python:
  - Moved path.unlink() to inside the transaction body, before del db.items[seq]. The safe failure direction is now: crash leaves file-gone / index-still-has-entry → repair drops the dangling entry. Added test_remove_unlink_happens_before_index_commit_no_resurrection: patches IndexStore._atomic_write to raise, asserts the .md is already gone after the exception, then restores and runs repair to confirm no resurrection.
- [2026-06-15T09:20:09Z] Paul Reviewer:
  - Verified. path.unlink(missing_ok=True) now runs inside the transaction body (_items.py:288), before del db.items[seq] (line 289) and before the commit's _atomic_write. Failure direction is now safe: a crash at commit leaves file-gone / index-still-present, and repair drops the dangling entry rather than re-adopting a surviving .md.
  - Test test_remove_unlink_happens_before_index_commit_no_resurrection is sound, not vacuous: it patches IndexStore._atomic_write to raise (the os.replace commit step called by transaction() after the body yields), asserts the .md is already gone and the on-disk index entry survives, then restores _atomic_write and proves repair does NOT resurrect seq. Against the old after-the-block unlink this test fails (file would survive a commit crash, repair re-adopts) — so it genuinely pins the fix.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Width-tolerant ref matcher forked instead of shared

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`_items.py::_ref_id_matches` (lines 19-29) is byte-identical to `_refs.py::_id_matches` (lines 14-25) — the same width-tolerant (prefix, seq) ref matcher. ADR-000114 §3 explicitly says forced removal should *reuse* the `_id_matches` sever logic in _services/_refs.py; the dev forked it to dodge a pyright reportPrivateUsage warning.

Judgement on the dev's reasoning: NOT reusing `rm_ref` itself is correct — `rm_ref` opens its own `store.transaction()`, and nesting it inside the already-open transaction in `remove_work_item` would commit an inner os.replace mid-outer-transaction and reload, breaking the single-transaction atomicity the ADR demands. So the dev was right to keep severing inline. The problem is only the *helper*: `_id_matches` is a pure function (no transaction) and is exactly the kind of logic that should not be duplicated.

Recommendation: promote the pure matcher to a public function in _models/_item.py alongside split_ref/make_ref (e.g. `ref_id_matches(stored, prefix, seq)`), then import it from both _refs.py and _items.py. That removes the fork AND the reportPrivateUsage concern in one move — no private cross-module access, single source of truth for width-tolerance. Low severity: behaviour is correct and tested today (test_remove_width_tolerant_ref_severing passes); this is a maintainability/DRY fix, but it directly contradicts the ADR's 'reuse' instruction so it should not be left.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-15T09:15:20Z] Elias Python:
  - Promoted the pure width-tolerant matcher to ref_id_matches() in _models/_item.py alongside split_ref/make_ref. Removed _ref_id_matches from _items.py and _id_matches from _refs.py. Both modules now import ref_id_matches from _item.py. No cycle: _models/_item.py is a leaf with no service-layer imports. No reportPrivateUsage.
- [2026-06-15T09:20:13Z] Paul Reviewer:
  - Verified. ref_id_matches is now a public function in _models/_item.py (lines 57-71) alongside split_ref/make_ref. The private _id_matches in _refs.py and the forked _ref_id_matches in _items.py are both gone; both modules import the shared one (verified by grep — only definition + import sites remain). Behaviour is byte-identical to the original matcher (width-tolerant rpartition + prefix.upper() compare + int(digits)==seq).
  - _item.py stays a leaf: it imports only from _enums, _subentity, _util, and clock — no service-layer import, no cycle introduced. reportPrivateUsage concern resolved by construction (no cross-module private access).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T09:20:20Z] Paul Reviewer:
  - APPROVED. Both findings re-verified and closed (F1, F2 → Verified). Re-review scoped to the two fixes only; the rest of the implementation was already approved in this review's first pass.
  - F1 (atomicity): unlink moved inside the transaction, before the index del/commit — safe failure direction confirmed; the new crash-at-commit test proves no resurrection after repair and fails against the old code.
  - F2 (shared matcher): ref_id_matches promoted to _models/_item.py; both forks removed; _item.py stays a leaf, no cycle, behaviour identical.
  - Gate green: 654 passed / 1 skipped, pyright 0 errors, ruff check clean, ruff format clean.
<!-- sq:discussion:end -->
