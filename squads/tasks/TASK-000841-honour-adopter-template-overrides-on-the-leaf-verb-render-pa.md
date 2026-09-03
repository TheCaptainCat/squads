---
id: TASK-841
sequence_id: 841
type: task
title: Honour adopter template overrides on the leaf-verb render path
status: Done
parent: FEAT-693
author: tech-lead
priority: urgent
refs:
- REV-840:addresses
description: A view's presentation template is ignored on sq <type> <n> show because
  the active squad dir is a ContextVar lost between the two bridge crossings
subentities:
- local_id: ST1
  title: Carry the active squad dir across both bridge crossings
  status: Done
  story: US2
- local_id: ST2
  title: CLI-level override proof for the milestone roll-up on show
  status: Done
  story: US2
- local_id: ST3
  title: Guard every leaf-verb render site against the same seam
  status: Done
  story: US2
created_at: '2026-08-26T17:02:39Z'
updated_at: '2026-08-26T17:48:09Z'
---
<!-- sq:body -->
## Problem

A view's presentation template is not adopter-overridable on `sq <type> <n> show`, which is the
only surface a normal user meets a view on. `sq workflow view <name> <id>` honours the override;
`sq <type> <n> show` and `sq <type> <n> show --raw` silently render the bundled template.

FEAT-693 states the overridability as an acceptance criterion and names the exact proof it
wanted — overriding the bundled milestone roll-up in a test squad and confirming the override
renders. `docs/workflow.md` repeats it and the CHANGELOG entry states that presentation is
adopter-overridable the day it ships. None of that holds on `show`.

## Mechanism (isolated by a direct probe, not inferred from the symptom)

`render()` resolves its override loader from `_active_squad_dir`, a **ContextVar**
(`src/squads/_rendering/_engine.py:38`), set once in `ServiceCore.__init__`
(`src/squads/_services/_base.py:374`).

`sq <type> <n> <verb>` crosses the sync/async bridge **twice** for one user-facing invocation —
the Typer group's id-resolving callback and the leaf verb — as two *sequential* `anyio.run`
calls, not one nested inside the other. `command`'s own docstring
(`src/squads/_cli/_common.py:1129`) states it: a scope opened inside the first call's coroutine
is already closed before the second call's coroutine starts. `get_service()` memoizes the
`Service` on the Click root context's `meta` (`src/squads/_cli/_common.py:995-1021`), so
`__init__` — and therefore `set_active_squad_dir` — runs only inside the *first* bridge. A
ContextVar set inside `anyio.run` does not propagate back to the caller, so the leaf verb sees
`None` and `_make_env` builds the bundled-only loader.

Single-bridge commands are unaffected, which is why this went unnoticed: `sq create milestone`
under an overridden `items/milestone.md.j2` writes the override, and `sq workflow view` resolves
it.

## Fix the seam, not the view

The defect is in the ContextVar / two-bridge interaction, which predates the derived-view work.
Views are simply the first thing rendered through `render()` on the leaf-verb path. Fixing it
inside `_views` alone would leave the identical trap for FEAT-694, which moves the sub-entity
summary and the head badge line onto this same `render()` path — so this is a prerequisite for
work already scoped into this release, not only a view defect.

The `Service` memo already survives both crossings (it hangs off the Click root context, which
Click builds once per dispatch). The active squad dir needs to reach the leaf verb by the same
route, or `render()` needs to resolve it from something that is not per-call-stack state.

## Acceptance criteria

- `sq <type> <n> show`, `show --raw` and `show --json` render an adopter's
  `.overrides/templates/views/<name>.md.j2` for every view the type attaches, on the same
  invocation shape a user types.
- `sq workflow view <name> <id>` keeps resolving the override (no regression on the surface that
  already worked).
- Every other overridable template rendered from a leaf verb resolves the override on that path —
  proven by enumeration, not by spot-checking the roll-up.
- A CLI-level test drives the FEAT-693 acceptance proof end to end: scaffold the override, edit
  it, assert the edited text appears in `sq milestone <n> show` output.
- A guard fails if the active squad dir is not visible to `render()` from a leaf verb, so the
  seam cannot silently reopen.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite clean; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 841 add-subtask "<title>"`; track with `sq task 841 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Carry the active squad dir across both bridge crossings

<!-- sq:subtask:ST1:body -->
Carry the active squad directory across both `anyio.run` crossings of one invocation, so the leaf
verb's `render()` resolves the same override loader the group callback's `Service` construction
established.

`ServiceCore.__init__` calls `set_active_squad_dir(paths.squad_dir)`
(`src/squads/_services/_base.py:374`) and `get_service()` memoizes the `Service` on the Click root
context's `meta` (`src/squads/_cli/_common.py:995-1021`), so the setter fires inside the first
bridge only. The Click root `Context` is the one object both crossings genuinely share — the same
anchor `_READ_SCOPE_META_KEY` and `_SERVICE_META_KEY` already use.

Pick one and record why in a comment on the change: re-establish the ContextVar at the top of each
bridge crossing from the shared root-context anchor, or move the resolution off per-call-stack
state entirely. The ContextVar's cache key into `_env_cache` must keep working either way, and the
single-thread assumption `_env()` documents must not be weakened.

Done when: a leaf verb reached through the two-crossing form sees the squad dir the group callback
established, and `sq ui` — which never passes through `command`, so no scope and no memo open for
it — keeps its current always-fresh behaviour.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — CLI-level override proof for the milestone roll-up on show

<!-- sq:subtask:ST2:body -->
Write the CLI-level proof FEAT-693's acceptance criterion names and that no existing test covers.

`tests/service/test_view_resolve_and_render.py` exercises overrides through `Service.render_view`
in-process, where construction and render share one context, which is why the suite is green while
the shipped surface is broken. The missing test drives the user-facing command.

Shape: init a squad, create a milestone, `sq override scaffold views/milestone_rollup.md.j2`,
replace the scaffolded body with a marker line keeping the override-base stamp, then assert the
marker appears in `sq milestone <n> show` and in `sq milestone <n> show --raw`, and that the
bundled Delivered/Outstanding headings do not. Assert `sq workflow view milestone_rollup MILE-<n>`
still renders the override too, so the surface that already worked is pinned.

Done when: the test fails against the current seam and passes after it, both observed and reported.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Guard every leaf-verb render site against the same seam

<!-- sq:subtask:ST3:body -->
Close the class, not the instance: enumerate every template rendered from a leaf verb and prove
each resolves an adopter override on that path.

Views are the first thing to render through `render()` from a leaf verb, but they are not the last:
FEAT-694 moves the sub-entity summary and the head badge line onto the same call. A fix proven only
against the milestone roll-up leaves the next consumer to rediscover this.

Enumerate the `render()` call sites reachable from a `command`-wrapped leaf verb, and add a guard
that fails when a leaf verb's render resolves the bundled loader while an override for that
template exists on disk. A parameterised test over the enumerated set is preferable to one test per
template — the point is that no call site is exempt.

Done when: the guard covers every enumerated leaf-verb render site, and adding a new one without
override resolution trips it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T17:26:24Z] Elias Python:
  - Fixed the seam in _cli/_common.py: get_service() and get_service_bypassing_index_cross_check() now re-call set_active_squad_dir(cached.paths.squad_dir) on every memo-hit fetch, not only at Service construction.
  - Fixed there, not at render sites: get_service() is the one call every leaf verb already makes before touching render() (each anyio.run crossing gets its own copied contextvars.Context, so ServiceCore.__init__'s set on crossing 1 never reaches crossing 2). Re-asserting on fetch covers every render() consumer uniformly — views, item-template regen, subentity block/head/summary (_discussion.py), role-body regen — with zero changes to _views.py or _discussion.py.
  - Driven proof on a real squad (bash, not CliRunner): scaffolded views/milestone_rollup.md.j2, edited it. Before fix: sq milestone 9 show and --raw rendered bundled Delivered/Outstanding; sq workflow view rendered the override. After fix: show, show --raw and workflow view all render the override.
  - Finding worth flagging: CliRunner-driven CLI tests using the invoke fixture do NOT reproduce this bug by default — the project/svc fixtures build a Service directly in-process (service.init), which sets the ContextVar in the test's own ambient context; asyncio.to_thread then copies that already-correct value into every invoke() call, masking the seam. My new tests reset engine._active_squad_dir to None before driving commands to strip that leak; without the reset both tests pass whether or not the fix is present.
  - New file tests/cli/test_leaf_verb_render_honours_overrides.py: (1) the FEAT-693 acceptance proof — override renders through show/show --raw, workflow view pinned; (2) a guard that instruments _env()/get_template to record every leaf-verb render call's active squad dir across a view command and add-subtask + subtask update (block/head/summary), asserting none see None. Falsified against the pre-fix code (fails), passes after.
  - tests/meta: 260 passed, 0 failed. Targeted: tests/cli + tests/service: 2305 passed, 1 skipped, 0 failed. pyright/ruff check/ruff format clean on my four touched files (_cli/_common.py, _rendering/_engine.py untouched, _services/_base.py untouched, the new test file); did not touch _workflow/_loader.py or fixtures the other dev is sweeping. sq check clean.
  - Nothing left undone in scope. Did not touch _services/_base.py or _rendering/_engine.py — the fix needed neither.
<!-- sq:discussion:end -->
