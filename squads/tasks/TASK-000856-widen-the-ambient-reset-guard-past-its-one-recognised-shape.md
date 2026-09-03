---
id: TASK-856
sequence_id: 856
type: task
title: Widen the ambient-reset guard past its one recognised shape
status: Ready
author: tech-lead
priority: low
refs:
- REV-854:addresses
- MILE-836:targets
description: The guard derives its reset set from one syntactic shape; an import alias,
  a nested declaration or a tuple target evades it — widen what can be widened and
  make the exhaustiveness claim honest about the rest
created_at: '2026-09-01T11:25:20Z'
updated_at: '2026-09-01T11:25:47Z'
---
<!-- sq:body -->
## Scope

`tests/meta/test_ambient_render_state_reset_is_exhaustive.py` claims to re-derive the reset set
from source and to fail "if a third ambient value is added there without being listed". It holds
for the tree as it stands, and its plant tests do exercise the real walk. But the derivation
recognises exactly one syntactic shape — `name = ContextVar(...)` at module body scope — and
several realistic ways of introducing the same leak walk straight past it.

Driven against the guard's own wired walk (`_reset_target_candidates`, the function the real
assertion calls — not a re-implementation), seven planted modules gave one detection and six
evasions:

| shape | why it evades |
| --- | --- |
| `from contextvars import ContextVar as CV` then `_leak = CV(...)` | the candidate test matches on the *called name* being literally `ContextVar` |
| a `ContextVar` inside a module-level `try:` | the walk is `for node in tree.body` — statements only, never a nested body |
| a `ContextVar` inside a module-level `if` | same |
| `_a, _b = ContextVar(...), ContextVar(...)` | the target extractor returns `None` for anything but a single `ast.Name` |
| `_leak = _mk("_leak")` via a factory | the call target is the factory, not `ContextVar` |
| a module-level dict keyed by squad dir, in a file with no `ContextVar` | excluded by the companion-cache rule, by design |

The last is the shape closest to the original leak and the one most likely to recur.

## Two halves, and the second is not optional

**Widen what can be widened.** Walk with `ast.walk` rather than `tree.body`; resolve the import
alias so `ContextVar` imported under any name is recognised; accept a tuple target. Each is a few
lines, and the existing plant tests are the right place to pin them — one plant per shape, each
asserted to be *detected* now, and each falsifiable by reverting its half of the widening.

**Make the docstring honest about what remains.** The factory shape cannot be caught by an AST
name match without type inference, and the bare-cache shape is excluded deliberately: the
companion-cache rule is a *proxy* for "keyed off ambient state", and that property can exist with
no `ContextVar` in the same module. Neither is a bug to hide behind a claim of exhaustiveness. The
guard is exhaustive over `ContextVar` bindings reachable by an AST walk, under any import alias,
in single or tuple assignment — say exactly that, and say what it does not cover and why.

State the companion-cache judgment either way, explicitly. If the rule stays a companion
heuristic, record that the sibling guard
(`tests/meta/test_no_unallowlisted_module_level_mutable_state.py`) is what catches a bare cache,
and record the gap that leaves: it routes the decision to a human answering "is this CODE?" rather
than "is this fixture-primable?".

## Severity, and why it is still worth doing in this release

Low, argued down rather than up: the tree has exactly one module-level mutable cache and it is
correctly listed, and the sibling mutable-state guard independently reddens on a new bare one. The
cost of the fix is small and the cost of leaving it is a guard whose stated contract is wider than
its actual one — which is the failure mode a meta-guard exists to prevent.

## Acceptance

- Each of the alias, nested-in-`try`, nested-in-`if` and tuple-target shapes is detected by
  `_reset_target_candidates`, pinned by its own plant test, and each plant is proven to fail when
  its half of the widening is reverted.
- The guard's real assertion still passes over the tree unchanged, and the reset set it derives
  today is unchanged — the widening finds no new candidate in current source.
- The docstring states the derivation's actual coverage and names the two shapes outside it, with
  the reason each is outside.
- The companion-cache rule's status is stated as a judgment, with the sibling guard named as the
  control for a bare cache and the residual gap written down.
- No item ID appears in any touched file.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean, and `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 856 add-subtask "<title>"`; track with `sq task 856 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
