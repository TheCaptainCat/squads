---
id: TASK-846
sequence_id: 846
type: task
title: Make the CLI test harness start from a real process's ambient state
status: Done
author: tech-lead
priority: high
refs:
- BUG-845:fixes
subentities:
- local_id: ST1
  title: Reset both leaking ambient values at the invoke boundary
  status: Done
- local_id: ST2
  title: 'Permanent falsification: a broken render path must fail the suite'
  status: Done
- local_id: ST3
  title: Enumerate and guard the set of values the harness must reset
  status: Done
- local_id: ST4
  title: Retire the workarounds the fix subsumes, keep the load-bearing ones
  status: Done
created_at: '2026-09-01T07:47:01Z'
updated_at: '2026-09-01T08:12:38Z'
---
<!-- sq:body -->
## Problem

The CLI test harness cannot see a whole class of defect: one where correct behaviour depends
on **process-startup state that a real invocation must establish itself, and that a fixture
already establishes as a side effect of building its own test squad**.

`tests/conftest.py`'s `project` fixture calls `service.init(...)` in-process. That runs
`ServiceCore.__init__`, which calls `set_active_squad_dir(paths.squad_dir)`
(`src/squads/_services/_base.py:374`) in the *test function's own* ambient context. The
`invoke` fixture then drives the CLI through `_aio.to_thread(...)`, which copies the calling
`contextvars.Context` into the worker — so every `invoke()` starts from a context that already
carries the right value, whether or not the code under test put it there.

A real `sq` process starts with `_active_squad_dir` at its declared default, `None`.

BUG-845 has the full mechanism and QA's driven proof. This task is the harness fix.

## What was measured before scoping this (driven, not estimated)

A probe on a `project`+`invoke` test, reading state immediately before the first `invoke()`:

- `_active_squad_dir` — already the correct squad dir. **Leaked.**
- `_env_cache` — already primed with an Environment keyed to that squad dir. **Leaked.**
- `RequestContext` — `actor_override`, `session_id`, `active_spec`, `active_dir`,
  `client_cwd` all unset; only `clock_override` set, by `frozen_time`, deliberately.
  **Not leaked.**

## The ContextVar is not the only one — but the set is small and closed

Two ambient values leak, both in `_rendering/_engine.py`:

1. `_active_squad_dir` (the `ContextVar` BUG-845 names).
2. `_env_cache` — the per-squad-dir compiled-template cache. A real process starts it empty.
   `_make_env` decides the loader (`ChoiceLoader` with the override dir, or bundled-only) once
   at Environment construction and caches the result, and `init` does not create
   `.overrides/`. So a fixture that inits a squad primes a **bundled-only** Environment for
   that dir, and a test that later writes an override by hand keeps resolving bundled.
   `invalidate_squad_dir` exists as the manual escape hatch and **12 CLI-driven test files
   already call it by hand** — against exactly 1 that hand-resets the ContextVar. The second
   leak is the more load-bearing of the two in practice.

`RequestContext` is structurally immune and needs no change. The root callback
(`src/squads/_cli/__init__.py:294-313`) binds one **fresh, wholly-computed** `RequestContext`
per invocation — every field recomputed, not merged into whatever was ambient — so a
pre-seeded value cannot survive into a command body. The single deliberate exception is
`clock_override`, carried forward via `_resolve_clock_override(at, prior)`, which is the seam
`frozen_time` is built on. Do not disturb it.

**The generalisable rule this yields, and the thing worth building:** the root callback is
where a real process establishes its ambient state. Any per-request value it does *not*
freshly compute is one a fixture can silently substitute for. Today that set is exactly
`{_active_squad_dir, _env_cache}`. Make the set enumerable and enforced, so a third one cannot
be added silently — that is the durable output here, not the two resets.

## Blast radius — measured, not estimated

Both values were reset at the top of the `invoke` fixture and the suite run:

| Scope | Result |
|---|---|
| `tests/cli`, `tests/integration`, `tests/service`, `tests/unit` | 4014 passed, 2 skipped, **0 failed** |
| `tests/meta`, `tests/tui` | 311 passed, **0 failed** |
| **Total** | **4325 tests, 0 behaviour changes** |

Exposed population, for context: 93 of 104 `tests/cli` files use `project`/`svc` + `invoke`,
plus 42 in `tests/integration` and 7 in `tests/service`.

**No test was found to be relying on the leak.** The "some tests may silently depend on this"
risk was the main thing to size, and it measured at zero. Treat this as a contained change.

If the dev's own run does surface a failure, it is a **finding, not collateral**: report it —
item, name, and what it was actually asserting — and do not quietly adjust the test until it
passes. A test that only passed because the fixture supplied the value under test was not
testing what its name claims. That is the whole defect, appearing one level down.

## The shape, and why the alternatives were rejected

**Chosen: reset both values at the CLI-invocation boundary, unconditionally.** `invoke()`
should start from the blank slate a fresh process does. Cheapest, measured safe, and it puts
the correction where the fidelity gap is — the sync/async bridge crossing — rather than
distributing it across test authors.

**Rejected — driving `invoke` through a subprocess.** Ruled out on evidence, not instinct.
The full in-process suite runs 4014 tests in ~79s; a subprocess per invocation across 2000+
invocations adds interpreter startup to each, an order-of-magnitude regression. It also
removes what a large share of CLI tests legitimately do — monkeypatch and assert against
in-process objects. Subprocess coverage already exists in the suite where end-to-end fidelity
genuinely earns its cost (the conftest header notes the env pins are exported for exactly
those); it should stay the exception, not the default.

**Rejected — a narrower opt-in reset in render-focused fixtures only.** This is already the
status quo, and it is what failed. 13 test files hand-roll one of these two workarounds today,
and TASK-841's defect still shipped and was caught by a reviewer driving a real squad rather
than by the suite. An opt-in rule requires the author to already suspect the leak; anyone who
suspects it does not need the rule. Leaving it opt-in leaves the blind spot open by default.

## Acceptance criteria

- `invoke()` starts each CLI invocation with `_active_squad_dir` unset and `_env_cache` empty,
  matching a fresh `sq` process.
- **The proof is a false pass turning into a failure, permanently.** A committed test breaks
  the leaf-verb render path and asserts the harness catches it. Asserting the fix works is not
  acceptance here — a fix asserted rather than falsified is precisely what let this survive.
- The set of ambient values the harness must reset is **enumerated and guarded**, so adding a
  per-request value that the root callback does not establish fails a test until it is either
  handled or consciously listed.
- `frozen_time`'s `clock_override` carry-forward still works — it depends on context
  propagating into `invoke()`, and must not be collateral damage of the reset.
- Workarounds the fix subsumes are removed; ones that are load-bearing for non-CLI paths stay.
  The 10 direct-render files (`tests/service`, `tests/unit`) call `render()` without crossing
  the CLI boundary and their `invalidate_squad_dir` calls remain necessary. Do not sweep those.
- Any test that changes behaviour under the reset is reported as a finding, not adjusted.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` clean; the full
  `uv run --all-extras pytest` suite green; `sq check` clean.

## Out of scope

`_active_squad_dir` is per-request DATA living outside `RequestContext`, which `_context.py`'s
own triage rule says is where such values belong. Folding it in would make the root callback
establish it and would close this class at the source rather than in the harness. That is a
production-design change and an architect call — worth raising separately, and deliberately
not bundled here, because the harness gap is real whatever that decision turns out to be.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 846 add-subtask "<title>"`; track with `sq task 846 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reset both leaking ambient values at the invoke boundary

<!-- sq:subtask:ST1:body -->
Make `invoke()` begin each CLI invocation from the ambient state a fresh `sq` process has:
`_active_squad_dir` unset, `_env_cache` empty.

The leak enters because `_aio.to_thread` copies the *calling* context, and the calling context
is the test function's — already primed by `project`'s in-process `service.init(...)` via
`ServiceCore.__init__` (`src/squads/_services/_base.py:374`). Resetting inside the worker is
too late and resetting in a plain autouse fixture is too early (the fixture ordering leaves
`project` free to re-prime afterward). The reset belongs at the invocation boundary itself, so
it holds for the second and third `invoke()` in a test as well as the first — several existing
tests scaffold an override *between* two invocations, and only a per-invocation reset covers
that.

`tests/conftest.py`'s existing `_reset_engine_state` autouse fixture already resets both values
but only *after* the test, as inter-test leak protection. This is the intra-test counterpart;
consider whether the two should be expressed once rather than as two similar-looking blocks.

Watch the interaction with `frozen_time`: it works precisely *because* context propagates into
`invoke()` (it rebinds `RequestContext.clock_override`, and the root callback deliberately
carries that field forward via `_resolve_clock_override(at, prior)`). A reset that clears the
whole context instead of these two specific values would break every frozen-time assertion in
the suite. Reset the two named values, not the context.

Done when: a `project`+`invoke` test observes `_active_squad_dir is None` and an empty
`_env_cache` at the moment a command body begins, and the frozen-time tests stay green.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Permanent falsification: a broken render path must fail the suite

<!-- sq:subtask:ST2:body -->
Commit the falsification. The acceptance for this task is a false pass becoming a failure, and
that transition has to be permanently defended or it decays the moment someone refactors the
fixture.

Shape, already driven and confirmed to work: disable TASK-841's fix without editing production
source, by monkeypatching `squads._cli._common.set_active_squad_dir` to a no-op — this
reintroduces exactly the pre-fix seam (crossing 1 still sets it via `ServiceCore.__init__`,
crossing 2 no longer re-asserts it). Then run the FEAT-693 acceptance shape: scaffold
`views/milestone_rollup.md.j2`, replace its body with a marker keeping the override stamp, and
assert the marker renders through `sq milestone <n> show`. With the harness fixed and **no
manual reset in the test**, this must fail.

Confirmed both directions before this task was written, on the real tree:

- harness fixed, no manual reset, break applied → **FAILED** (the bundled `## Outstanding` /
  `## Settled without delivering` headings rendered instead of the marker)
- harness unfixed, same test, same break → **passed** — the false pass

Do not write this as "assert the override renders" with the break absent. That test already
exists and is green; it is not what is being proven. What is being proven is that the harness
can *see* the break, so the deliberate break has to be part of the committed test.

`tests/cli/test_leaf_verb_render_honours_overrides.py` is the natural home — its module
docstring already explains the leak at length and would need rewriting anyway once ST4 removes
its manual resets.

Done when: the test is committed, fails if the harness reset is reverted, and passes with it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Enumerate and guard the set of values the harness must reset

<!-- sq:subtask:ST3:body -->
Close the class rather than the two instances. The durable output of this task is that the set
of ambient values the harness must reset is **enumerable and enforced**, not that two specific
resets exist.

The rule to encode: the root callback (`src/squads/_cli/__init__.py:294-313`) is where a real
process establishes its per-invocation ambient state, and it binds one freshly-computed
`RequestContext` — so every field on that dataclass is safe by construction. A per-request
value that lives *outside* that binding is one a fixture can silently substitute for. Today
that set is exactly `{_rendering._engine._active_squad_dir, _rendering._engine._env_cache}`.

`tests/meta/test_no_unallowlisted_module_level_mutable_state.py` is the model and probably the
place: it already walks `src/squads` with `ast`, already encodes the DATA-vs-CODE triage rule
from `squads._context`'s docstring, and already has the enumerate-exhaustively-then-diff shape
plus planted-leak tests that redden the real guard path. Reuse that structure rather than
inventing a second one; note that `_env_cache` is *already on its allowlist* as a sanctioned
CODE cache, which is correct for its purpose and precisely why it needs a second guard aimed
at the harness question — being legitimate process-wide CODE and being fixture-primed startup
state are not mutually exclusive, and this task exists because the second property went
unnoticed.

Include the planted-leak test: a synthetic third value must redden the guard automatically, the
way that module's existing plant tests do. A guard that has never been observed failing is the
same category of unproven as the tests this task is fixing.

Done when: adding a per-request ambient value outside `RequestContext` that the harness does
not reset fails a test, and that failure has been observed rather than assumed.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Retire the workarounds the fix subsumes, keep the load-bearing ones

<!-- sq:subtask:ST4:body -->
Remove the hand-rolled workarounds the harness fix makes redundant, and leave the ones that are
load-bearing. Getting this split wrong in either direction is a real risk, so the classification
is given here rather than left to judgement.

**Subsumed — remove.** `tests/cli/test_leaf_verb_render_honours_overrides.py`, the only file
that hand-resets the ContextVar: two `engine._active_squad_dir.set(None)` lines (with the
comment explaining why) plus the long paragraph in the module docstring describing the leak.
Once the harness resets by default, that prose describes a condition that no longer exists and
becomes actively misleading. Rewrite the docstring to describe what the module *proves*.

**Candidates — verify individually, do not bulk-remove.** 12 CLI-driven test files call
`invalidate_squad_dir` by hand. Many are guarding the `_env_cache` leak and become redundant;
some may be evicting mid-test after writing an override *between* invocations, which the
per-invocation reset also covers — but confirm per file by removing the call and observing the
test still passes for the right reason, not by pattern-matching.

**Load-bearing — keep.** The 10 files in `tests/service` and `tests/unit` that call
`invalidate_squad_dir` drive `render()`/`Service.render_view` directly and never cross the CLI
boundary, so the `invoke`-level reset never runs for them. Their calls stay necessary. Do not
sweep them.

Removing a workaround must not be verified by "the suite is still green" alone — that is the
same weak signal this whole task is about. For each removal, confirm the test still fails when
the behaviour it covers is broken.

Done when: the redundant workarounds are gone, the necessary ones documented as necessary, and
no removal rests on a green run alone.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T07:49:04Z] Olivia Lead:
  - Scoped per the operator's call to land before the 0.14 cut. Shape decided: reset at the `invoke` boundary. Subprocess harness rejected on measured cost (4014 tests in ~79s in-process; a subprocess per invocation across 2000+ calls is an order-of-magnitude regression) and because it removes the in-process monkeypatching most CLI tests rely on. Narrow opt-in rejected because it is the status quo that already failed — 13 files hand-roll a workaround today and TASK-841 still shipped.
    
    Two answers I drove rather than assumed, both in the body: (1) the ContextVar is **not** the only leaking value — `_env_cache` in the same module leaks identically and has 12 hand-rolled workarounds to the ContextVar's 1; `RequestContext` is structurally immune because the root callback rebinds it wholesale per invocation. (2) Blast radius measured, not estimated: both values reset at the boundary, **4325 tests, 0 behaviour changes**. The "tests may be relying on the leak" risk sized at zero, so this is a contained change.
    
    Falsification confirmed both directions before writing the acceptance: with the harness fixed and no manual reset, a monkeypatched break **fails**; without the fix, the same test **passes**. That pair is ST2 and must be committed.
    
    No architect ruling needed to start — the fix is harness-only, zero production source. Flagged as out of scope in the body: `_active_squad_dir` is per-request DATA living outside `RequestContext`, against `_context.py`'s own triage rule; folding it in would close this at the source and is an architect call worth raising separately, but it does not block this.
    
    Nothing committed; `tests/conftest.py` was patched only to take the measurement and is back to its committed state. @python-dev when dispatched.
- [2026-09-01T08:10:11Z] Elias Python:
  - Implemented all four subtasks.
    
    ST1 — reset: tests/conftest.py gained `_AMBIENT_RESET_TARGETS` + `_reset_ambient_render_state()` (calls `set_active_squad_dir(None)` and `_env_cache.clear()`), called at the top of `invoke`'s `_invoke()` before every call (not once per test), and reused by `_reset_engine_state`'s post-test backstop so both resets share one implementation.
    
    ST2 — falsification, in `tests/cli/test_leaf_verb_render_honours_overrides.py`: new test monkeypatches `_cli._common.set_active_squad_dir` to a no-op (reintroducing the pre-fix seam without touching production code) and asserts the override marker is absent / bundled heading renders. Confirmed both directions by hand: with the harness reset active, the assertion **passes** (break is observed); with it temporarily disabled, the assertion **fails** (override renders despite the break — the false pass reproduces). Restored the reset afterward; `git diff` on conftest.py is clean of the probe.
    
    ST3 — guard, new file `tests/meta/test_ambient_render_state_reset_is_exhaustive.py`. Walks src/squads for module-level `ContextVar` declarations (minus a reasoned `CONTEXTVAR_EXEMPTIONS` list — RequestContext's own var, rebound wholesale every invocation; `_active_transaction`/`_read_scope` in `_index/_store.py`, set/reset-token paired, never survive past their own call) plus any mutable cache sharing a file with a non-exempt ContextVar. Diffs the derived set against a closed `RESET_TARGETS`, and separately checks `RESET_TARGETS` against conftest's own `_AMBIENT_RESET_TARGETS` (parsed via ast, not imported) so the two can't drift. Planted-leak tests (bare ContextVar, ContextVar+companion cache, exempted case, cache-with-no-ContextVar) redden/stay-green as expected — 6/6 pass.
    
    ST4 — workaround sweep. Removed 3 of 13: the 2 `engine._active_squad_dir.set(None)` lines in test_leaf_verb_render_honours_overrides.py (rewrote the docstring to describe what the module proves now) and 1 `invalidate_squad_dir` call in test_workflow_views_cli.py's `_place_view_template_override` (proven redundant: 15/15 pass with it removed, and only the one test that depends on it fails when the harness reset is disabled — restored afterward). Left the other 10 CLI-driven `invalidate_squad_dir` call sites (across 8 files writing `.overrides/workflow.toml` spec overrides, not templates) untouched after checking: removing all of them plus disabling the harness reset caused zero failures in those 8 files — they were never tied to this leak (they don't render a template override afterward), so touching them is a different, out-of-scope cleanup, not something this task's fix subsumes. The 10 tests/service+tests/unit files that call `render()`/`Service.render_view` directly (never crossing the CLI boundary) are untouched, confirmed load-bearing by inspection.
    
    Verification: tests/meta 266 passed, 0 failed. Targeted tests/cli+integration+service+unit: 4015 passed, 2 skipped, 0 failed (4014 baseline + 1 new falsification test — no behaviour change elsewhere). pyright/ruff check/ruff format clean (`--all-extras`). `sq check` clean.
    
    Nothing left undone in ST1-ST4's scope. Out of scope per the task body: folding `_active_squad_dir` onto `RequestContext` (a production-design/architect call, not touched).
<!-- sq:discussion:end -->
