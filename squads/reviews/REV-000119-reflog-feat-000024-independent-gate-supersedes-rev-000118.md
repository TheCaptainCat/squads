---
id: REV-000119
sequence_id: 119
type: review
title: Reflog (FEAT-000024) — independent gate, supersedes REV-000118
status: Approved
author: reviewer
refs:
- TASK-000112
- TASK-000113
- FEAT-000024
- REV-000118
- ADR-000117
description: Independent re-review of TASK-112 (core) + TASK-113 (read) against ADR-000117;
  supersedes REV-000118 as the trustworthy gate (same lineage produced 118).
subentities:
- local_id: F1
  title: Stale 'no-op until TASK-112' docstrings now factually wrong (two sites)
  status: Fixed
  severity: low
- local_id: F2
  title: Inaccurate actor-reset comment in _cli/__init__.py
  status: Fixed
  severity: low
- local_id: F3
  title: 'op/delta double-key: outer op=''subentity''/''migrate'' with inner delta[''op'']'
  status: Open
  severity: low
- local_id: F4
  title: No autouse actor-reset fixture in conftest (test hygiene)
  status: Fixed
  severity: low
- local_id: F5
  title: Reflog 'v' reuses index SCHEMA_VERSION (coupled bumps)
  status: Open
  severity: low
created_at: '2026-06-15T10:13:51Z'
updated_at: '2026-06-15T10:21:30Z'
---
<!-- sq:body -->
Independent verification of the FEAT-000024 reflog (TASK-000112 core + TASK-000113 read) against ADR-000117 and ADR-000114. Every claim of REV-000118 was re-checked against the actual code and verified empirically; 118 is not treated as authoritative because the same agent lineage designed, implemented, and reviewed it.

## Verdict: APPROVE

The implementation is correct and faithful to ADR-000117 on every load-bearing guarantee. Gate is fully green. The only findings are cosmetic (stale docstrings, one inaccurate comment) and minor test hygiene — none block.

## Guarantees — confirmed to actually hold

**Write ordering (ADR-000117 §1) — HOLDS.** In `_store.py::transaction()` the sequence is: `yield ctx.db` (mutation) -> `self._atomic_write(ctx.db)` whose final act is `tmp.replace(self.index_path)` (the os.replace commit) -> THEN the buffered reflog append loop, all inside `with self._lock:`. The append is strictly after the commit and inside the lock. If the body raises, `_atomic_write` never runs and neither does the append. **Logged-without-applied is impossible by construction; applied-without-logged is the only reachable failure** and it is contained: `append_line` swallows OSError/TypeError/ValueError to a stderr warning, and the append loop is additionally wrapped in `except Exception` so nothing can propagate past the committed mutation. Empirically confirmed: monkeypatching the appender to raise OSError leaves the created item durable (test_failed_reflog_append_does_not_rollback_mutation, and re-derived by reading the guard).

**Append atomicity (§2) — HOLDS.** One `json.dumps(...)+"\n"` written in a single `fh.write` under `open(path,"a")` (O_APPEND); no per-line fsync. Serialization is INSIDE the try/except (the REV-118 F6 fix), so a non-serializable delta warns rather than propagating. Reader (`read_lines`) drops a trailing non-newline-terminated line silently and warn-skips interior bad lines; a missing file returns []. Verified empirically: a reflog seeded with a garbage interior line + a partial trailing line is read back correctly, skipping both.

**Actor threading (§3) — HOLDS, no leak.** `_actor.py` mirrors `_clock` exactly (module global, default "system", set/clear). The root callback calls `actor.set_actor("system")` on every invocation BEFORE the command runs; `comment --as`, sub-entity `comment --as`, and `create --author` override it (`_cli/_items.py:209,677`, `_cli/_create.py:60`). Leak prevention is the unconditional per-invocation re-set at the callback (same mechanism as `apply_timestamp`), not a try/finally. Verified empirically over the real CLI: create logs actor=manager (from --author), status logs actor=system (no actor flag), comment logs actor=manager (from --as), and `--at 2020-01-01` flows into the line `ts`.

**Invariant 1 (NOT a source of truth) — HOLDS, verified in code AND empirically.** `load`, `repair`, and `check` never reference `_reflog`/`.reflog.jsonl`. `repair()` rebuilds `db` purely from `_iter_item_files()` (frontmatter) + the previous index counter/padding floor, then appends its reflog line AFTER `store.overwrite(db)`. Empirical proof: a reflog containing a forged `create` line for TASK-999999 plus garbage was placed before `sq repair`; after repair the index still held exactly the real items, no 999999, counter unchanged, and `sq check` was clean.

**op=remove wiring (ADR-000114 §2) — REAL.** `remove_work_item` calls `self.store._log("remove", item.id, {type,title,status,severed_refs})` inside the transaction; emitted post-commit. The file is unlinked before the index commit (safe failure direction). Confirmed by test_remove_emits_reflog_line and the unlink-before-commit comment.

## Gate
- `uv run pytest` — green (reflog suite: 45 passed; full suite passes).
- `uv run pyright` — 0 errors.
- `uv run ruff check .` — clean.
- `uv run ruff format --check .` — clean (103 files).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 119 add-finding "…" --severity high`; track with `sq review 119 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Stale 'no-op until TASK-112' docstrings now factually wrong (two sites) |
| F2 | 🟢 low | Fixed |  | Inaccurate actor-reset comment in _cli/__init__.py |
| F3 | 🟢 low | Open |  | op/delta double-key: outer op='subentity'/'migrate' with inner delta['op'] |
| F4 | 🟢 low | Fixed |  | No autouse actor-reset fixture in conftest (test hygiene) |
| F5 | 🟢 low | Open |  | Reflog 'v' reuses index SCHEMA_VERSION (coupled bumps) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stale 'no-op until TASK-112' docstrings now factually wrong (two sites)

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Two docstrings still claim the reflog writer is unwired, which is now false:

(1) src/squads/_services/_items.py:249-251 (remove_work_item): 'the writer is a no-op until TASK-000112 wires the FEAT-000024 reflog seam'. The seam IS wired and self.store._log('remove', ...) fires at line 312.

(2) src/squads/_services/_results.py:77 (RemoveResult): 'The reflog op/delta hook is a no-op until TASK-000112 wires the FEAT-000024 writer.'

Impact: documentation only; misleads the next reader into thinking removal is untraced. Recommendation: update both docstrings to state the writer is live (op=remove appended post-commit).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Inaccurate actor-reset comment in _cli/__init__.py

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_cli/__init__.py:67-68 comment: 'The try/finally in the hook clears it per-invocation so state never leaks between calls (same hygiene as the clock).'

There is no try/finally that clears the actor. The try/finally in _store.transaction() clears _current_ctx (the reflog buffer), NOT the actor. Leak prevention actually comes from the unconditional set_actor('system') re-set at the START of every callback invocation — exactly how apply_timestamp re-sets the clock each invocation.

Impact: misleading comment; the behaviour is correct (verified: no leak across CLI invocations). Recommendation: reword to 'the callback re-sets the actor to system at the start of every invocation, so state never carries over (mirrors apply_timestamp for the clock).'
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — op/delta double-key: outer op='subentity'/'migrate' with inner delta['op']

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
subentity and repad log lines carry an outer op (op='subentity' or op='migrate') plus a nested delta['op'] (delta={'op':'add'|'status'|'update'|'body'|'repad', ...}).

Impact: a reader scanning for 'the op' must know to read the outer key for the category and the inner key for the sub-kind; the overloaded name is slightly confusing in --json. Not a bug — the semantics are well-defined and tested. Recommendation (optional, defer to FEAT-000013 freeze): rename the inner key to 'kind'/'action' or fold subentity sub-kinds into distinct outer ops before the schema is frozen.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — No autouse actor-reset fixture in conftest (test hygiene)

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
test_reflog_core.py has an autouse _reset_actor fixture, but test_reflog_read.py::test_read_reflog_filter_by_actor sets the ambient actor to 'python-dev' then 'system' with no reset, and conftest.py has autouse resets only for the clock and engine state — not the actor.

Impact: the global actor override is left at 'system' (not None) after that test. Observably harmless because 'system' is the default, but it relies on ordering and contradicts the ADR's own no-leak hygiene argument. Recommendation: move the autouse _reset_actor fixture into tests/conftest.py so it covers the whole suite.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Reflog 'v' reuses index SCHEMA_VERSION (coupled bumps)

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
The reflog line 'v' field is set to the index SCHEMA_VERSION ('0.3') in src/squads/_index/_reflog.py. ADR-000117 §4 says v should be 'consistent with the SCHEMA_VERSION dotted-string convention', which this satisfies, but reusing the same constant couples the reflog line version to the index schema version — they bump together even when only one format changes.

Impact: none today; a defensible reading of the ADR. Flagging for the FEAT-000013 freeze: decide whether the reflog line deserves an independent version constant so the two surfaces can evolve separately. Recommendation: confirm intent at the freeze; no code change required now.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
