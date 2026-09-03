---
id: TASK-819
sequence_id: 819
type: task
title: Close the hygiene scans' import evasion and pin their literal lists
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-817:addresses
- TASK-809
description: The migration import guard misses a module import plus attribute access,
  and both new AST scans carry hand-maintained vocabularies unpinned to their sources
subentities:
- local_id: ST1
  title: Walk module imports and attribute access in the migration guard
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST2
  title: Pin the wire-encoding primitive names to _models._item
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST3
  title: Pin the ref-kind literal set to the bundled spec's ref_kinds
  status: Done
  assignee: python-dev
  story: US2
created_at: '2026-08-25T22:58:35Z'
updated_at: '2026-08-26T08:53:16Z'
---
<!-- sq:body -->
## Scope

FEAT-790 US2 — the two AST hygiene scans that protect the declared-vocabulary boundary, and
nothing they scan.

Both scans are new and both are sound in what they check. What is wrong is what they cannot see:
one has an import form it does not walk, and both hold a hand-typed copy of a vocabulary that lives
somewhere else in the tree.

## Verified against the tree

### The migration import guard

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py::_imported_forbidden_names`
(`:87-99`) walks the AST and inspects `ast.ImportFrom` only. A plain module import plus attribute
access reaches the same primitive and is invisible:

    import squads._models._item as _item
    def use(): return _item.make_ref("X", "related")

is not flagged, and neither is `from squads import _models` followed by `_models._item.make_ref(...)`.
An aliased `ImportFrom` **is** caught, so the aliasing case was considered and the module-import case
was not. Both are one line a developer writes without thinking, and both reopen the exact defect the
guard exists to prevent: a frozen runner whose on-disk bytes move when the live tree is refactored
under it, with a green suite.

The file's docstring claims the forbidden set applies unconditionally with no per-name exemption.
That is true of names and false of import forms, so the docstring overstates the guarantee.

### The two hand-maintained lists

- `_WIRE_ENCODING_PRIMITIVES` (same file, `:71-81`) names six identifiers. Nothing asserts they
  resolve in `squads._models._item`. All six do today, so this is latent — but the file's whole
  premise is that a future refactor moves things, and a rename makes the guard silently vacuous for
  the renamed name.
- `_REF_KIND_LITERALS` (`tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py:32-44`)
  lists the ten bundled kinds as literals. Nothing asserts it equals the bundled spec's declared
  `ref_kinds`. An eleventh bundled kind gets no literal-scan coverage, silently — and stopping a
  bundled kind name being consulted as a literal in the engine is the scan's entire purpose.
  `grep "def test_"` over the file confirms no such pin exists.

`squads._workflow.bundled_spec()` is the source to pin against and is already importable from tests.

## Acceptance

1. A migration module that reaches a forbidden primitive through a module import plus attribute
   access is flagged, for both the `import squads._models._item as X` and the
   `from squads import _models` + `_models._item.make_ref` shapes.
2. A module import of `squads._models[...]` that never touches a forbidden name is **not** flagged.
   A false positive here would push a future author toward suppressing the guard.
3. `_WIRE_ENCODING_PRIMITIVES` is asserted to resolve, name by name, in `squads._models._item`.
4. `_REF_KIND_LITERALS` is asserted to equal the bundled spec's declared ref-kind codes.
5. Each new assertion is falsified before handover: break it, watch it go red, restore it, watch it
   go green, and report both.
6. The migration guard's docstring states the guarantee it actually gives — which import forms it
   walks — rather than asserting an unconditional one.
7. `uv run --all-extras pyright`, `ruff check .` and `ruff format --check .` stay clean.

## Out of scope

Widening either scan's reach beyond Python source. The ref-kind literal scan reads `*.py` under
`src/squads/` and does not parse Jinja templates; that boundary is unchanged here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 819 add-subtask "<title>"`; track with `sq task 819 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Walk module imports and attribute access in the migration guard | US2 |
| ST2 | Done | python-dev | Pin the wire-encoding primitive names to _models._item | US2 |
| ST3 | Done | python-dev | Pin the ref-kind literal set to the bundled spec's ref_kinds | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Walk module imports and attribute access in the migration guard

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Extend `_imported_forbidden_names` past `ast.ImportFrom`. Two shapes have to be caught:

- `import squads._models._item as _item` (or unaliased) anywhere in the module, combined with an
  `ast.Attribute` access whose attribute name is in the forbidden set.
- `from squads import _models` combined with `_models._item.make_ref(...)` — the attribute chain is
  longer but the attribute name is the same.

The simplest correct rule is: if the module imports anything under `squads._models`, every
`ast.Attribute` in the file whose `attr` is a forbidden name is a hit. That over-approximates
slightly and that is the right direction for a guard on the integrity core — but it must not fire on
a module that imports `squads._models` and never names a forbidden attribute, so cover that case
explicitly.

The existing planted-runner tests are the pattern to follow: plant each shape in a tmp tree, call
`_scan`, assert the hit. Falsify by reverting the scan change and watching the new legs go red.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Pin the wire-encoding primitive names to _models._item

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add an assertion that every name in `_WIRE_ENCODING_PRIMITIVES` resolves in `squads._models._item`,
with a failure message saying what a miss means: the name was renamed or moved, and the guard is now
silently vacuous for it, so the set has to be updated rather than the failure suppressed.

The point is not that a missing name is a bug in `_models._item` — it is that the guard stops
protecting a primitive nobody notices it stopped protecting.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Pin the ref-kind literal set to the bundled spec's ref_kinds

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Add an assertion that `_REF_KIND_LITERALS` equals the set of codes the bundled workflow spec
declares under `[ref_kinds]` (`squads._workflow.bundled_spec().ref_kinds`).

Failure message names the consequence: a bundled kind absent from the literal set gets no
literal-scan coverage at all, so an engine branch comparing against that kind's name would ship
unflagged.

Do not relax the set to a superset check. An extra literal that the spec no longer declares is also
a defect — it means the scan is guarding a name that no longer exists while the real one goes
unguarded.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T08:43:50Z] Elias Python:
  - F5 fixed: guard now flags a module import (import squads._models._item / from squads import _models) plus an attribute access naming a forbidden primitive, aliased or not — matches the reviewer's two driven bypasses. No-false-positive leg covered (module import naming no forbidden attribute stays unflagged).
  - F5/F9 pin: _WIRE_ENCODING_PRIMITIVES now asserted to resolve in squads._models._item (hasattr per name); _REF_KIND_LITERALS now asserted == frozenset(bundled_spec().ref_kinds), exact equality not superset.
  - All new assertions falsified: broke the ST1 fix (disabled the trigger) -> 3 tests red -> restored -> green; broke ST2 (added a fake primitive name) -> red -> restored -> green; broke ST3 (renamed a bundled ref_kinds table in workflow.toml, i.e. moved the real source) -> red -> restored -> green.
  - Docstring corrected: states the actual walked forms (direct from-import of a forbidden name; module-reach-plus-attribute as an over-approximation) instead of the prior unconditional claim.
  - Known remaining exposure, not closed by this task: a bare 'import squads' followed by a fully-dotted attribute chain (squads._models._item.make_ref) is still unflagged, since the trigger only fires on imports that name something under squads._models specifically (per ST1's two stated shapes). Dynamic dispatch (getattr(module, 'make_ref')) is also unflagged — inherent to any static AST name/attribute scan. Neither shape appears in the current migrations tree.
  - tests/meta: 244 passed. Targeted (both files): 18 passed. Gates: pyright 0 errors, ruff check clean, ruff format clean, sq check clean.
  - @reviewer ready for review.
- [2026-08-26T08:47:53Z] Elias Python:
  - Addressed feedback: widened the trigger from 'reaches squads._models' to 'reaches squads at all' (any import naming squads or squads.<anything>, at any depth). Closes the bare 'import squads' + fully-dotted 'squads._models._item.make_ref(...)' chain, which was open in the first pass and reproduced the same shape of defect the task exists to fix.
  - Falsified the same way: reproduced the bare-import bypass, confirmed it passed under the narrower (first-pass) trigger, then confirmed the widened trigger catches it; reverted and re-confirmed green. Added the matching no-false-positive leg (bare 'import squads' reaching only Item/SubEntity, never a forbidden attribute, stays unflagged) and re-verified against the real migrations tree, which has several bare 'from squads import _discussion/_sections/_aio/_clock' imports today -- none trip the widened scan.
  - Docstring updated to state the guard's actual boundary: it catches every statically-named reach for a forbidden primitive however the reimport is phrased (module-level, package-level, or bare-squads-plus-dotted-chain); it explicitly does not and cannot catch dynamic dispatch (getattr(module, 'make_ref')) -- recorded as a stated limit of the mechanism, not left implicit.
  - tests/meta (excluding test_override_kind_uniformity.py, the other dev's in-flight file): 223 passed. Targeted (both touched files): 20 passed. Gates: pyright 0 errors, ruff check/format clean on both touched files (the only failures in a full-repo run are in test_override_kind_uniformity.py, outside this task's scope), sq check clean.
  - No further known evasion of the statically-named kind remains open. Dynamic dispatch remains the one documented, out-of-mechanism limit.
  - @reviewer updated, still InReview.
<!-- sq:discussion:end -->
