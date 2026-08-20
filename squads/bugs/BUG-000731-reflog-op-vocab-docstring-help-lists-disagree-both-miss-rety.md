---
id: BUG-731
sequence_id: 731
type: bug
title: 'Reflog --op vocab: docstring/--help lists disagree, both miss retype'
status: Verified
author: qa
priority: low
severity: low
refs:
- FEAT-24:addresses
created_at: '2026-08-03T08:49:48Z'
updated_at: '2026-08-15T19:55:19Z'
---
<!-- sq:body -->
Three independent, hand-maintained enumerations of the reflog op vocabulary exist, none complete, and no code enforces any of them.

**Reproduction**

- `src/squads/_index/_reflog.py:29-32` (module docstring, calls itself "the closed vocabulary"): lists 14 ops — `create`, `status`, `update`, `body`, `comment`, `subentity`, `ref`, `link`, `remove`, `repair`, `migrate`, `renumber`, `rename-type`, `rename-status`. Omits `retype` and `default_role`.
- `src/squads/_cli/_main.py` `--op` help string (`sq reflog --help`): lists 12 ops — `create`, `status`, `update`, `body`, `comment`, `subentity`, `ref`, `link`, `remove`, `repair`, `migrate`, `default_role`. Omits `retype`, `renumber`, `rename-type`, `rename-status`.
- `docs/workflow.md`'s "Op names" table (a third, separate hand list, not mentioned in the originating audit): listed 11 ops at the time this was filed — `create`, `status`, `update`, `body`, `comment`, `subentity`, `ref`, `remove`, `retype`, `repair`, `migrate` — omitting `link`, `default_role`, `renumber`, `rename-type`, `rename-status`. **This third list was independently corrected the same day** (`ec9fb87`, a couple of hours after filing) and now carries all 16 with a per-op "triggered by" column. That leaves the two code-side lists as the live defect, and it is a demonstration of the underlying problem rather than a reduction of it: three copies drifted apart, and one of them was fixed without the other two moving.

**Actual vocabulary (verified by driving each op in a throwaway squad, plus static grep of every `store.log(...)`/`.log(op=...)` call site):** 16 ops — `create`, `status`, `update`, `body`, `comment`, `subentity`, `ref`, `link`, `retype`, `default_role`, `remove`, `repair`, `renumber`, `migrate`, `rename-type`, `rename-status`.

Driven live and observed in `.reflog.jsonl`: create, status, update, body, comment, subentity, ref, retype, default_role, repair, renumber, rename-status. `link`/`unlink` exist on `Service` (`_services/_items.py`) and are exercised by unit tests but have no CLI verb today — still genuinely reachable/emitted code, not dead. `migrate`/`rename-type` confirmed by static site inspection only (driving them needed either an already-current schema or a second declared type, out of scope for a quick repro).

Each list's *contents* are accurate — every op it names really is emitted — the defect is that the lists are independently incomplete in different ways, and no single place in the codebase names the real 16. `retype` is the sharpest case: it reaches the reflog, it filters correctly, and the two code-side lists have never named it.

**`--op` validation:** confirmed `--op` does NOT validate against any list — `_services/_maintenance.py::read_reflog` does a plain `line.op != op_filter` string compare. `sq reflog --op bogus_nonexistent_op` exits 0 and prints "no reflog entries" with no error. So this is a **documentation-accuracy defect only**, not a filtering-functionality gap: `sq reflog --op retype` already works correctly despite being undocumented in two of the three places. The flip side: a typo'd `--op` (e.g. `staus`) silently returns an empty result instead of erroring, which is a minor separate UX smell worth a mention here since it's adjacent, not a reason to raise this bug's severity.

**Fix direction:** a single shared tuple/constant (e.g. `REFLOG_OPS` next to `ReflogLine` in `_reflog.py`) that the docstring points at rather than restates, the `--op` help string interpolates, and docs/workflow.md's table is checked against would collapse this to one source of truth — and the constant itself needs pinning against the actual `store.log(...)`/`append_line(op=…)` call sites, or it is just a fourth hand-maintained list. Validating `--op` against that constant is deliberately *not* part of the fix: a read verb refusing to read a log written by a different version of squads trades a real capability for a spelling check.

**Severity:** Low. Nothing behaves incorrectly; every documented op works, and the missing-from-docs ops (`retype`, `default_role`, etc.) all work too — this is purely a "the docs/help text are missing entries" defect, with no data loss, no wrong output, no silent corruption. It affects discoverability (an operator won't know `--op retype` or `--op default_role` are valid filters) and mildly undermines the docstring's own "closed vocabulary" claim (nothing closes it).

**Affected surfaces:** `src/squads/_index/_reflog.py` (docstring), `src/squads/_cli/_main.py` (`--op` help string), `docs/workflow.md` ("Op names" table).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-15T14:38:00Z] Elias Python:
  - Established the vocabulary before fixing either list, as asked. It is 16, matching the reported set exactly: create, status, update, body, comment, subentity, ref, link, retype, default_role, remove, repair, renumber, migrate, rename-type, rename-status. Two emitter shapes, not one — the buffered store.log("<op>", ...) used inside a transaction, and append_line(..., op="<op>", ...) which the three squad-level ops (repair, renumber, migrate) use because they write outside one. A scan that only knew the first form would miss three.
  - One source, not two agreeing copies: REFLOG_OPS in _reflog.py. The module docstring now points at it instead of restating it, and the --op help string interpolates it, so both copies are gone by construction. The workflow guide keeps its table because the per-op "triggered by" column is real adopter prose, and is pinned against the constant instead.
  - The constant itself is pinned too, or it would just be a fourth hand list: tests/meta/test_reflog_op_vocabulary_has_one_source.py AST-scans src/ for both emitter shapes and asserts set equality in both directions, plus no duplicates, plus the doc table, plus the generated help text. That guard is what makes the docstring "closed vocabulary" claim true; nothing enforced it before.
  - Deliberately not done: validating --op against the constant. reflog read is a read verb over an append-only log that may have been written by another version of squads; refusing to filter an op this build no longer names would trade a real capability for a spelling check. The typo-returns-empty smell stands as reported.
  - Falsified twice: dropping "retype" from the constant (the exact omission this bug names) reddened the source-scan and doc-table tests; reverting the --op help to a hand-written list reddened the help-text test. Both reverted by exact reverse substitution, green again.
  - Body corrected on two points my own investigation contradicted. The docs/workflow.md table claim was true at filing and was overtaken the same day by ec9fb87, which brought that table to all 16 — the body now says so, and reads it as a demonstration of the drift rather than a shrinking of the bug. The "Release: 0.14" line is gone: @op-pierre put all three of these in 0.13.
- [2026-08-15T19:55:19Z] Catherine Manager:
  - Verified by driving: sq reflog --op help lists all 16 operations including retype (read at COLUMNS=500 -- Rich truncates it at normal width), REFLOG_OPS carries the same 16, and the meta guard passes 4/4, AST-scanning both emitter shapes and asserting set equality in both directions.
<!-- sq:discussion:end -->
