---
id: TASK-818
sequence_id: 818
type: task
title: Uniformity guard derives its kind set and checks CLI reachability
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-817:addresses
- TASK-801
description: Replace the guard's hand-written kind registry with one derived from
  scan_overrides, and add CLI reachability as its fifth element
subentities:
- local_id: ST1
  title: Derive the guard's kind set from scan_overrides
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST2
  title: Add CLI reachability as the fifth uniformity element
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST3
  title: Correct the dispatcher claim in _uniformity_gaps' docstring
  status: Done
  assignee: python-dev
  story: US5
created_at: '2026-08-25T22:57:39Z'
updated_at: '2026-08-26T08:53:15Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US5 — the guard itself, not the kinds it guards.

`tests/meta/test_override_kind_uniformity.py` is the gate that is supposed to make a new
override kind impossible to ship half-wired. It did not stop the roles catalog kind shipping
with a manifest entry, a state classifier, both diff deltas and a stamp finding while being
unreachable from `sq override scaffold|diff|update`. Two separate reasons, both fixed here.

## Verified against the tree

- `_KIND_FIXTURES` (`tests/meta/test_override_kind_uniformity.py:181-227`) is a hand-written
  literal dict, one row per kind. Its own comment calls adding a row the price of a sixth kind.
- `test_the_registry_covers_every_kind_the_docstring_names` (`:295`) cross-checks it against a
  regex scrape of `OverrideEntry.kind`'s field comment (`_overrides/_service.py:87-90`). Both
  sides are hand-maintained prose. Pinning one hand-written list to another does not detect a
  kind absent from both — they go stale together.
- There is no registry in code to derive from: `scan_overrides` (`_overrides/_service.py:278-332`)
  is five open-coded blocks, and `check_override_issues` / `diff_override` are likewise per-kind
  branches.
- `_uniformity_gaps` (`:238-283`) drives `override_service.scan_overrides` /
  `.check_override_issues` / `.diff_override` through the module object. Its docstring calls that
  "the same top-level dispatcher every `sq override` command uses". That is true of the service
  layer and false of the CLI layer, and the CLI layer is exactly where the gap was.

## Why the derivation is sound

A kind that does not reach `scan_overrides` is not an override kind at all — nothing lists it,
nothing classifies its state, nothing diffs it. So `scan_overrides` over a squad carrying one
override of every kind is a legitimate lower bound on the kind set, and unlike the field comment
it cannot be updated in prose without the code changing. It is a derivation, not a second copy.

## Acceptance

1. The expected kind set is computed at run time from `{e.kind for e in scan_overrides(squad_dir)}`
   against a squad carrying one override of every kind, and `_KIND_FIXTURES` is asserted to cover
   exactly that set — neither more nor less. A kind wired into `scan_overrides` and nowhere else
   fails this file.
2. Every kind's `scaffold`, `diff` and `update` are driven through the CLI runner, by the argument
   form a human types, and each is asserted to exit 0 and to resolve to the intended kind (not to
   fall through to another kind's branch). The five forms differ — a template-relative path, a
   `--role <slug>` flag, and three bare positional names — so the fixture row has to carry the
   invocation, not guess it.
3. Removing any one of the three CLI wirings for any one kind fails the new element. Demonstrate
   this by breaking each in turn and reporting the red, then restoring it.
4. `_uniformity_gaps`' docstring no longer claims the service entry points are the dispatcher the
   CLI uses; it says which layer each element drives and why both are needed.
5. The docstring cross-check against `OverrideEntry.kind` either goes away as redundant or is kept
   with its purpose restated — a documentation-accuracy check, not the registry. It must not
   remain the thing standing in for a derivation.

## Out of scope

The refactor that would give `_overrides/_service.py` a real per-kind registry and collapse the
three open-coded dispatchers. That is a design change to the override service; this task only
stops the guard depending on a hand-maintained copy of a list the service already implies.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 818 add-subtask "<title>"`; track with `sq task 818 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Derive the guard's kind set from scan_overrides | US5 |
| ST2 | Done | python-dev | Add CLI reachability as the fifth uniformity element | US5 |
| ST3 | Done | python-dev | Correct the dispatcher claim in _uniformity_gaps' docstring | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Derive the guard's kind set from scan_overrides

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US5 — Uniform unstamped-shadowing severity plus the uniformity guard
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Build a squad carrying one override of each kind (the existing `place_shadowing` fixtures already
do this), call `override_service.scan_overrides(squad_dir)`, and assert
`set(_KIND_FIXTURES) == {e.kind for e in entries}`.

The assertion message must say what to do: a kind reported by `scan_overrides` with no fixture row
means the kind is wired into the service but has no uniformity coverage; a fixture row with no
scanned entry means the fixture's placement no longer produces a scannable override.

Falsify it before handing back: add a sixth kind to `scan_overrides` alone (a throwaway branch) and
watch this test go red without touching `_KIND_FIXTURES`, then remove it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add CLI reachability as the fifth uniformity element

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US5 — Uniform unstamped-shadowing severity plus the uniformity guard
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Give `_KindFixture` a field carrying the CLI argument form for the kind — the exact argv a human
types — because the five forms are not uniform: a template is a positional path
(`items/task.md.j2`), a per-slug role override is a flag (`--role architect`), and `workflow`,
`playbook` and `roles` are bare positional names.

Then, for every kind, drive `sq override scaffold <form>`, `sq override diff <form>` and
`sq override update <form>` through the CLI runner fixture and assert two things per invocation:
exit code 0, and that the output identifies the intended kind rather than another kind's branch.
The second half is the load-bearing one — `roles` was reachable-shaped and would have mis-routed to
the `template` kind, which an exit-code-only check does not catch.

Report the element as a gap string alongside the existing four so a failure names the missing part
and the kind together.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct the dispatcher claim in _uniformity_gaps' docstring

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US5 — Uniform unstamped-shadowing severity plus the uniformity guard
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`_uniformity_gaps`' docstring says each check goes "through the same top-level dispatcher every
`sq override` command uses". The service functions it calls are one layer below the CLI dispatcher,
and that distinction is the reason the four-part guard passed an unreachable kind.

Restate it: name the service entry points as what the first four elements drive, name the CLI runner
as what the fifth drives, and say why the file needs both — a kind can satisfy the service contract
and still be unreachable from the command line.

Same pass: `_KIND_FIXTURES`' own comment currently instructs a future author to add a row by hand and
calls the docstring cross-check what keeps the two honest. Once the set is derived that is no longer
true, so the comment has to stop saying it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T08:50:59Z] Elias Python:
  - Kind set is now derived at run time from scan_overrides (test_the_kind_set_is_derived_from_scan_overrides): places one shadowing override of every kind, then diffs {entry.kind} against set(_KIND_FIXTURES) both ways, naming which side is stale.
  - CLI reachability is the new 5th element in _uniformity_gaps, driven per kind via the invoke fixture through sq override scaffold/diff/update with each kind's own argv form (_KindFixture.cli_argv). Checks exit 0 AND the resolved kind: scaffold via the scanned entry's .kind, diff via the printed '(kind: X)' line, update via the on-disk stamp actually advancing -- not exit code alone.
  - Falsified both: (1) added a throwaway 6th kind to scan_overrides alone -- the derivation test went red naming it, _KIND_FIXTURES untouched; (2) reverted the three 'roles' CLI elif branches in _cli/_override.py, ran the suite -- failed with: override kind wiring gaps (kind -> missing part): {'roles': ["CLI reachability (scaffold exited 1: 'error: no bundled template ...roles... )")]}. Restored both files, re-ran clean (diff confirmed byte-identical).
  - _uniformity_gaps' docstring now names which layer each element drives (service dispatch for 1-4, the actual CLI runner for 5) instead of claiming one dispatcher backs all of them; the docstring cross-check against OverrideEntry.kind is kept but restated as a documentation-accuracy check against the derived set, not the registry.
  - tests/meta full: 247 passed, 0 failed. Targeted (test_override_kind_uniformity.py): 24 passed. pyright/ruff check/ruff format --check all clean. sq check clean.
<!-- sq:discussion:end -->
