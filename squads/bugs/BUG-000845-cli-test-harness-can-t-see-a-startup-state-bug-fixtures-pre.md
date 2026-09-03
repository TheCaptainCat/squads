---
id: BUG-845
sequence_id: 845
type: bug
title: 'CLI test harness can''t see a startup-state bug: fixtures pre-seed the render
  ContextVar'
status: Fixed
author: qa
priority: medium
refs:
- TASK-841
- MILE-836:targets
description: project/svc build a Service in-process, leaking the correct active-squad-dir
  ContextVar into every invoke() call via asyncio.to_thread's context copy — a CLI
  test passes whether or not the code under test establishes that state itself
created_at: '2026-09-01T07:38:33Z'
updated_at: '2026-09-01T08:12:43Z'
---
<!-- sq:body -->
## Mechanism

`render()` resolves adopter overrides from `_active_squad_dir`, a `contextvars.ContextVar`
(`src/squads/_rendering/_engine.py`). Production establishes it fresh, per bridge crossing, off
`ServiceCore.__init__` and (since TASK-841) `get_service()`'s re-assertion on every memo fetch.

`tests/conftest.py`'s `project`/`svc` fixtures build a `Service` **directly, in-process**, via
`service.init(...)` — not through the CLI. That call runs `ServiceCore.__init__`, which sets
`_active_squad_dir` in the *test function's own ambient context*, and never resets it (only an
autouse fixture resets it *after* the test). The `invoke` fixture drives the CLI via
`_aio.to_thread(functools.partial(runner.invoke, app, args))` — `anyio.to_thread.run_sync`
copies the *calling* `contextvars.Context` into the worker thread it runs on (standard
`asyncio`/`anyio` semantics: a `Task`/`to_thread` call is not a fresh context, it is a snapshot
of whatever context was ambient at the call site). Every `invoke()` call in the test therefore
starts from a context that already carries the correct squad dir — inherited from the fixture's
setup, not established by the CLI code path the test claims to exercise.

A real `sq` invocation is a fresh Python process: `_active_squad_dir` starts at its declared
default, `None`. Nothing pre-seeds it. Whatever value it holds when `render()` runs was put
there by the production code under test, on that exact call stack, or it wasn't put there at
all.

## The class of defect this hides

Any bug where correct behaviour depends on **process-startup state that a real invocation must
establish itself, and that a fixture already establishes as a side effect of how it builds its
own test squad** is invisible to a CLI test written the obvious way (`project`/`svc` + `invoke`,
no manual reset) — the fixture's leaked value silently substitutes for the value the code under
test was supposed to produce. `_active_squad_dir` is the instance found; the shape is general
to any ambient/contextvar/module-global state a fixture's own setup path happens to prime
correctly as a byproduct.

## Evidence it hid a real one

TASK-841 ("Honour adopter template overrides on the leaf-verb render path", urgent, `sq show`ed
here): `sq <type> <n> show` crosses the sync/async bridge twice per invocation (the item-type
group's id-resolving callback, then the leaf verb — two sequential `anyio.run` calls, not one
nested in the other). Pre-fix, `ServiceCore.__init__` set the ContextVar on crossing 1 only;
crossing 2 saw `None` and silently fell back to the bundled template, ignoring an adopter's
`.overrides/templates/views/<name>.md.j2` on the one surface (`show`) a normal user meets a view
on — while `sq workflow view` (single-crossing) kept working, and `sq check` stayed clean
throughout. It was found by a reviewer driving a real squad from the shell, not by the suite —
the fixing dev's own comment on TASK-841 states the CLI suite was green throughout and names
this exact fixture-leak mechanism as why, independently of this report.

## The obvious-way test gives a false pass — driven

Wrote a CLI test the obvious way (`project`, `invoke`, no ContextVar reset) that scaffolds and
edits the `milestone_rollup` view override, then asserts the marker text renders through
`sq milestone <n> show` — the exact FEAT-693/TASK-841 acceptance shape. Deliberately broke the
render path first, by monkeypatching only `squads._cli._common.set_active_squad_dir` to a
no-op (disabling exactly TASK-841's fix — the crossing-2 re-assertion — while leaving
`ServiceCore.__init__`'s own crossing-1 call untouched: precisely the pre-fix seam,
reintroduced without editing a single production source line).

Ran it as a temporary file under `tests/cli/`, then deleted it — not committed, nothing left in
the tree (`git status` confirmed clean of it afterward). Two tests, same monkeypatched break,
one line of difference:

```
tests/cli/test_qa_scratch_contextvar_blindspot_demo.py .F                [100%]
=========================== short test summary info ============================
FAILED tests/cli/test_qa_scratch_contextvar_blindspot_demo.py::test_same_break_fails_once_the_ambient_leak_is_stripped
========================= 1 failed, 1 passed in 0.36s ==========================
```

(exit code checked directly, no pipe: `1` — one expected failure, the control test)

- `test_obvious_way_false_passes_on_a_broken_render_path` — fixtures only, no reset — **PASSED**
  against the deliberately broken render path. It asserted the override marker rendered through
  `sq milestone <n> show`, and it did — not because the leaf verb resolved the override
  correctly, but because the ambient context already carried the right squad dir before the
  first `invoke()` call was made.
- `test_same_break_fails_once_the_ambient_leak_is_stripped` — identical body, one extra line
  (`engine._active_squad_dir.set(None)` before driving) — **FAILED** on the same break, and the
  captured output shows exactly the pre-fix symptom: the bundled `## Delivered` / `## Outstanding`
  headings instead of the override marker.

Same fixtures, same break, same assertion — the only variable is whether the ContextVar was
reset to the value a fresh process actually starts with. One version proves nothing; the CLI
suite as written today only ever runs the version that proves nothing.

## How wide the blind spot is

Every CLI-level test that uses `project` or `svc` (which construct a `Service` in-process) and
then drives behaviour through `invoke()` (or any other `asyncio.to_thread`/`anyio.to_thread`
wrapper around `CliRunner.invoke`) inherits the leaked, already-correct `_active_squad_dir` —
not just view-rendering tests. `render()` is the shared call for every leaf-verb template:
item-file regen, sub-entity block/head/summary (`_discussion.py`, the mechanism FEAT-694 moves
onto this same path), and role-body regen, per `get_service()`'s own docstring. Any test whose
subject is one of those, written the obvious way, has the identical blind spot — TASK-841 fixed
the seam at the `_active_squad_dir` production call site, not the test-harness gap that let it
ship. `tests/cli/test_leaf_verb_render_honours_overrides.py` is the one file in the suite that
explicitly documents and works around this (the two `engine._active_squad_dir.set(None)` lines,
with a comment explaining why) — every other CLI test in the suite that touches a render-derived
surface does not, and would not catch a regression in the same seam TASK-841 just closed.

## Not prescribing a fix

Whether the remedy is resetting the ContextVar in the fixtures, driving CLI tests through a real
subprocess instead of in-process `invoke()`, or resolving `render()`'s override lookup from
something other than per-call-stack state, is a design call — it touches fixtures the whole
suite depends on and deserves scoping, not a patch bolted onto this report.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T07:39:01Z] Mara Tester:
  - Filed while verifying BUG-825/827/837/838 this release; confirmed by reading get_service()'s docstring + TASK-841's own comment trail, then reproduced independently (temp test file under tests/cli/, deleted after — not committed): same monkeypatched break, ContextVar-reset-vs-not is the only variable, 1 passed / 1 failed.
  - @tech-lead — scoping call per the operator's request to land before release; not prescribing fixtures-reset vs subprocess-harness vs a different render() lookup.
<!-- sq:discussion:end -->
