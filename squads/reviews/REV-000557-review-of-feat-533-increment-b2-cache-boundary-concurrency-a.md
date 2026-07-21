---
id: REV-557
sequence_id: 557
type: review
title: 'Review of FEAT-533 Increment B2: cache boundary, concurrency acceptance, AST
  guard'
status: Approved
author: reviewer
refs:
- FEAT-533
subentities:
- local_id: F1
  title: AST guard blind to non-literal mutable caches (OrderedDict/defaultdict/helper)
    mutated in place
  status: Verified
  severity: medium
- local_id: F2
  title: Acceptance test's uncommitted-write / cross-squad-DATA isolation claims exceed
    what it exercises
  status: Verified
  severity: medium
- local_id: F3
  title: env_cache LRU dict mutations are not thread-safe (safe only under the single-thread
    asyncio model)
  status: Verified
  severity: low
- local_id: F4
  title: Plant tests prove the detector function, not the wired guard's file-walk
    + allowlist diff
  status: Verified
  severity: low
created_at: '2026-07-21T23:00:37Z'
updated_at: '2026-07-21T23:11:36Z'
---
<!-- sq:body -->
Independent review of FEAT-533 Increment B2 — TASK-554 (code-vs-data cache boundary, LRU-bounded Jinja env_cache, US4 concurrency-isolation acceptance test + backend-stateless guard) and TASK-549 (AST guard against module-level mutable state). Reviewer did not author the code. Read-only pass; no source edits.

Verdict: APPROVE WITH FINDINGS. Correctness for shipped one-shot CLI is sound: env_cache LRU semantics are correct, the backend-stateless guard is real, REV-556 F1 is genuinely resolved (both spec-resolution paths now share one client_cwd), and no DATA hides in the guard allowlist (every entry is bundled/definitional CODE or a compiled-template/package-data cache). Two Medium rigor gaps, neither a runtime defect: the AST guard has an exploitable false-negative class, and the acceptance test's data-isolation claims are broader than what it exercises.

Is the US4 proof rigorous? For the property that matters most — YES. The ambient-state isolation (clock/actor/dir must not bleed between concurrent requests) is genuinely proven: A binds and HOLDS its context live (parked on b_checked) while B samples, and A re-reads its own context AFTER B has rebound. A plain-module-global regression would make A write to squad B and the read-back at line 110 would fail — so the test has real teeth against the core FEAT-533 break. The weaker part is the DATA-isolation claim (F2).

Is the guard rigorous? Sound for the common case, but NOT durable against the obvious variant (F1). It catches dict/list/set literals + dict()/list()/set() ctors + comprehensions + every 'global' statement (which covers scalar ex-globals like clock._override, actor._override, _manifest_cache). It MISSES a module cache built via OrderedDict()/defaultdict()/Counter()/deque() or any helper function, and mutated in place (in-place mutation needs no 'global'). That is exactly how one would write the next cache — verified empirically.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 557 add-finding "…" --severity medium`; track with `sq review 557 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | AST guard blind to non-literal mutable caches (OrderedDict/defaultdict/helper) mutated in place |
| F2 | 🟡 medium | Verified |  | Acceptance test's uncommitted-write / cross-squad-DATA isolation claims exceed what it exercises |
| F3 | 🟢 low | Verified |  | env_cache LRU dict mutations are not thread-safe (safe only under the single-thread asyncio model) |
| F4 | 🟢 low | Verified |  | Plant tests prove the detector function, not the wired guard's file-walk + allowlist diff |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — AST guard blind to non-literal mutable caches (OrderedDict/defaultdict/helper) mutated in place

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The detector (`_is_mutable_binding`) flags a module-scope assignment only when the value is a dict/list/set literal, a dict/list/set COMPREHENSION, or a Call whose func name is literally `dict`/`list`/`set`; plus any `global` statement. Verified empirically against the shipped detector: `_leak = {}`, `_leak: dict = {}`, `_leak = dict()`, `_leak = []`, and the scalar-reassigned-via-`global` pattern are all CAUGHT — but `OrderedDict()`, `defaultdict(list)`, `Counter()`, and `_leak = _helper()` (any factory returning a mutable) are all MISSED.

Why it bites: a mutable container built by a non-{dict,list,set} factory and mutated IN PLACE needs no `global` statement, so it evades BOTH constructs entirely. That is a natural way to write a cache — ironically, the very env_cache this increment bounds could have been written `OrderedDict()` and sailed past its own guard.

Failure scenario: a later author adds `_item_cache = defaultdict(dict)` at module scope in a service module, keyed by squad dir, and fills it per request. It is a genuine per-request DATA cache — exactly the class FEAT-533 exists to forbid — yet the guard stays green and the build never goes red. The durable-enforcement promise (US1: 'a guard, not a one-time sweep') is quietly false for this variant.

Note the allowlist already enumerates every function-built singleton (_BUNDLED_SPEC, _spec, _CATALOG, _PLAYBOOK_SPEC, …), which only makes sense if Call-assignments were flagged — but the detector does NOT flag them, so those entries are decorative (the docstring admits they're listed 'anyway'). Recommend closing the loop: (a) also flag Calls to a known mutable-factory set (OrderedDict/defaultdict/Counter/deque/…), or (b) flag EVERY module-scope Call-bound name and lean on the already-populated singleton allowlist — that makes the decorative entries load-bearing and closes the helper-built hole. Medium: no current defect (migrated tree is clean), but it undercuts the feature's central deliverable.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Acceptance test's uncommitted-write / cross-squad-DATA isolation claims exceed what it exercises

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`test_a_concurrent_b_request_never_observes_as_write_or_ambient_state` docstring + line-92 comment claim B 'never observes A's data' and that B's list is 'untouched by A's concurrent (not-yet-committed) write'. Both framings overstate what runs. (1) A's write executes STRICTLY AFTER B finishes reading — B sets `b_checked`, which is what unblocks A's `await b_checked.wait()` before A calls `svc.create(...)`. There is no in-flight/concurrent write during B's read; it hasn't started. (2) B reads squad B's store while A writes squad A's store — separate dirs, files, filelocks — so B could never observe A's write regardless of any in-process isolation. The empty-list assertion is trivially true by squad separation, not by an isolation mechanism.

What IS genuinely proven (the crux of FEAT-533): AMBIENT-state isolation. A's context is bound and held live while B samples clock/actor/dir, and A re-reads its own context after B rebinds — a plain-global regression would clobber A's context, send A's write to squad B, and fail the read-back at line 110. That path has real teeth; the proof is NOT hollow for the module-global-bleed break the feature targets.

The gap: the 'no cross-request DATA cache' property is only shown as 'a fresh open_service reads committed data back' (serial, same squad) — never as 'a concurrent/retained reader on the SAME squad does not see an uncommitted write nor serve a stale cached read'. That intra-squad property is what a data-cache regression would actually violate, and is the one leaning on the async filelock (FEAT-34/ADR-153).

Recommendation: (a) add a same-squad interleave — request A holds an open write while concurrent request B reads squad A and must see the pre-write state / block on the lock — to actually exercise intra-squad isolation, or (b) soften the docstring/line-92 wording to 'cross-squad data separation' and state that intra-squad uncommitted-read isolation is owned by the lock layer, not this test. Medium per the 'call out false-confidence' bar: the claim is broader than the evidence, and a reader would trust it as proof of a property it does not test.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — env_cache LRU dict mutations are not thread-safe (safe only under the single-thread asyncio model)

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
`_env()` now mutates the shared module dict `_env_cache` with pop+reinsert on a hit and insert+`del _env_cache[next(iter(...))]` on an evicting miss. Under the project's stated concurrency model this is SAFE: anyio is pinned to asyncio (conftest `anyio_backend`), `_env()` has no `await`, so each call runs atomically to completion within its task — no interleaving.

Forward-looking (the class FEAT-533 motivates): if a long-lived server ever drives `render()` from a THREAD POOL rather than one event loop, these mutations race. The hit branch is TOCTOU (`if squad_dir in _env_cache` then `.pop(squad_dir)` — another thread can pop between them → KeyError), and two concurrent evicting misses can both read `next(iter(...))` and one `del` then KeyError the other. The pre-LRU code only ever double-built; the pop/del LRU can raise.

Not a defect in the shipped increment (async single-loop is the design per ADR-153). Flagging so the seam is explicit: guard the cache with a lock, or document that it assumes a single event loop and is not thread-safe. Low.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Plant tests prove the detector function, not the wired guard's file-walk + allowlist diff

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
The two plant tests call `_mutable_state_hits` on a synthetic tmp_path module and assert the DETECTOR flags the plant. They do not exercise the real guard's wiring — the src-tree file-walk and the `names - ALLOWLIST` set-difference in `test_module_level_mutable_state_matches_the_allowlist_exactly`. So the automated proof stops at 'the detector works'; the acceptance step 'a planted _leak in a real engine module makes the guard red' was, per the task, a manual temporary edit + revert, not an assertion.

Low: the real test reuses the same `_mutable_state_hits` + `names - ALLOWLIST`, so a real planted leak WOULD trip it (shared logic), and the manual proof satisfies the task wording. Minor gap between 'detector proven' and 'guard-path proven'. Optional hardening: run the walk against a temporary fixture dir, or assert the assembled `missing` dict directly, so the end-to-end red path is covered without a manual edit.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:02:56Z] Paul Reviewer:
  - Verdict: CHANGES REQUESTED (rigor, not correctness). One-shot CLI behavior is correct and all gates are green; the env_cache LRU, backend-stateless guard, and the REV-556 F1 client_cwd fix are all sound, and no DATA hides in the guard allowlist. But the feature's two headline deliverables — the durable guard and the acceptance proof — each fall short of what they claim: F1 (Medium) the AST guard is blind to a mutable cache built via OrderedDict/defaultdict/helper and mutated in place, so the exact forbidden pattern can be reintroduced with the build staying green; F2 (Medium) the acceptance test genuinely proves ambient (clock/actor/dir) isolation but its data/uncommitted-write claims are broader than what it exercises (A's write runs after B reads, and on a different squad's store). Address F1/F2 (or consciously accept + document the guard's factory-call gap and reword the test's data claim) before this is treated as the durable enforcement + proof FEAT-533 promises. F3/F4 are Low/forward-looking.
<!-- sq:discussion:end -->
