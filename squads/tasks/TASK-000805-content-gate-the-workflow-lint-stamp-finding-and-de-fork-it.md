---
id: TASK-805
sequence_id: 805
type: task
title: Content-gate the workflow lint stamp finding and de-fork it
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-777:implements
- TASK-799:depends-on
- TASK-797:depends-on
description: Content-gate workflow_stamp_finding so sq workflow lint stops warning
  on stamp age alone, and collapse the forked gated copy back to one implementation
subentities:
- local_id: ST1
  title: Gate the workflow stamp finding on content
  status: Done
  story: US2
- local_id: ST2
  title: Retire the duplicate gated copy and guard the agreement
  status: Done
  story: US2
created_at: '2026-08-25T15:48:22Z'
updated_at: '2026-08-25T23:39:50Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US2, completing the content-gating for the one surface it could not reach.
`_workflow/_loader.py::workflow_stamp_finding` still warns on **stamp age alone**:

```
if stamp != __version__:
    return ("warn", f"workflow override may be stale: stamp v{stamp} predates running v{__version__}; …")
```

So `sq check`, `sq override list` and `sq override diff` are content-gated correctly, while
`sq workflow lint` still produces exactly the false positive the manifest widening exists to
remove — an add-only `.overrides/workflow.toml` with no bundled change behind it is told its
override may be stale.

## This is a fork, not just an ungated branch

The manifest-widening work could not edit `_workflow/`, so it added a second, gated copy of the
same obligation — `_overrides/_service.py::_workflow_stamp_finding_gated` — with a docstring
saying in place that the loader's version "still does stamp-only". One obligation now has two
implementations that disagree, and `workflow_stamp_finding`'s own docstring still claims it is
"evaluated once so `sq check` and `sq workflow lint` always agree", which is no longer true.

So the fix is not a one-line gate. It is: gate the canonical function, delete the duplicate,
re-point its callers, and make the single-evaluation property something a test holds rather than
a docstring asserts.

## Why its own task rather than folded into the semantic-binding task

The semantic-binding task owns `_workflow/` and would avoid the file collision, but it is
parented to the ref-kinds feature, and its stories are the vocabulary ones. This work implements
**US2 of this feature** — content-gated drift — and a subtask cannot be mapped to a story its
task's parent does not carry. Directory ownership is a concurrency constraint; it is not a
reason to file work under a feature it does not implement.

The concurrency constraint is real and is recorded as a `depends-on` instead: this must not run
while the semantic-binding task has `_workflow/_loader.py` open.

## Acceptance

- An add-only `.overrides/workflow.toml` stamped several releases back, with no change to the
  bundled `workflow.toml` since that stamp, produces **no** finding from `sq workflow lint` —
  matching what `sq check` and `sq override list` already report for it.
- The same override with a real bundled change behind it still warns from `sq workflow lint`,
  and the message names the bundled document changing rather than the stamp being old.
- A shadowing override with no stamp is still an error from `sq workflow lint`, unchanged.
- An unrecorded base version stays silent — unknown history treated as unchanged, never a
  warning — with no new `sq check` finding at any severity.
- `_overrides/_service.py` carries no private duplicate of the workflow stamp obligation, and
  every caller reads the one function.
- A test drives both surfaces over the same squad and asserts they agree, so a future fork fails
  rather than being caught by reading two docstrings.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 805 add-subtask "<title>"`; track with `sq task 805 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Gate the workflow stamp finding on content | US2 |
| ST2 | Done |  | Retire the duplicate gated copy and guard the agreement | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Gate the workflow stamp finding on content

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Content-gate workflow/playbook/role drift
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Gate `workflow_stamp_finding` (`_workflow/_loader.py`) on content rather than stamp age, using
the same helper every other kind already uses: `artifact_changed_since(WORKFLOW_KEY, stamp)`.

The three outcomes keep their shape and only the middle one changes:

- shadowing and unstamped → error, unchanged.
- stamped, older than the running version, **and the bundled `workflow.toml` actually changed
  since that stamp** → warn. Today the content clause is missing.
- stamped at the running version, content unchanged since the stamp, or add-only and unstamped
  → nothing.

The warn message changes with it: it currently says the stamp "predates running v<x>", which
describes the stamp rather than the document. It should say the bundled document changed since
the stamp, matching the wording the gated copy already uses.

Unknown history stays silent — `artifact_changed_since` returns `False` for an unrecorded base,
and that is the rule this must not disturb.

**The import direction needs a deliberate answer, and the facts are already established.**
`_overrides/_service.py` imports from `_workflow/_loader`, so `_workflow` → `_overrides` is a
cycle at package granularity. At module granularity it is not: `_overrides/_manifest.py`, where
`artifact_changed_since` lives, imports nothing internal beyond `squads._util`. There is no
automated cycle test — the acyclic graph is a stated convention — so this is a judgment to make
and record, not one a gate will make for you.

Two shapes that both work: import `artifact_changed_since` from `_overrides/_manifest.py` and
justify the module-granular edge in the docstring, or thread the answer in from the caller. Do
**not** paper over it with a function-local runtime import; a `TYPE_CHECKING` annotation does not
help either, since this is a value read at call time.

Done when the lint surface reports nothing for an add-only override with no bundled change,
still warns when there is one, and the import decision is stated where the next reader will
find it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Retire the duplicate gated copy and guard the agreement

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Content-gate workflow/playbook/role drift
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Delete `_overrides/_service.py::_workflow_stamp_finding_gated` and re-point
`_check_workflow_override_issues` at the now-gated `workflow_stamp_finding`, so the obligation
has one implementation again.

Correct `workflow_stamp_finding`'s docstring: it currently claims the finding is "evaluated once
so `sq check` and `sq workflow lint` always agree", which the duplicate made false. Once the
duplicate is gone the claim is true again — and the point of the next paragraph is that it stops
being only a claim.

Add the test that holds the property: drive **both** surfaces over the same squad fixture and
assert they return the same finding, across the cases that distinguish them — add-only unstamped,
shadowing unstamped, stamped with a bundled change, stamped without one, and an unrecorded base
version. A future fork then fails a test instead of being discovered by reading two docstrings
that disagree.

This is the same reasoning the uniformity guard in the severity task applies to the override
registry: the axis that is uniform is the axis with a guard.

Done when one function serves both surfaces, no private copy remains, and the agreement test
fails if either surface is changed alone.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T15:49:41Z] Olivia Lead:
  - Split out rather than folded into TASK-797, and the deciding argument is the story mapping, not the file layout. This is FEAT-791 US2 work - content-gated drift. TASK-797 is parented to FEAT-790 and carries only the ref-kinds vocabulary stories, so a subtask there could not be mapped to US2 at all; it would have to be misfiled under a semantics story it does not implement, or left unmapped. Directory ownership is a concurrency constraint, not a scope definition.
  - Recorded the concurrency constraint as depends-on TASK-797 instead, so sq blocked carries it: this must not run while TASK-797 has _workflow/_loader.py open. depends-on TASK-799 is a genuine logical dependency - it needs artifact_changed_since and WORKFLOW_KEY to exist.
  - Verified before writing: _workflow/_loader.py workflow_stamp_finding still returns a warn on stamp != __version__ with no content clause, while _interactions/_loader.py playbook_stamp_finding and every path in _overrides/_service.py are gated on artifact_changed_since. So this is the single remaining ungated surface, not a class of them.
  - Scope is larger than the missing gate, and that is why it is two subtasks. TASK-799 could not edit _workflow/, so it added a second gated copy - _overrides/_service.py _workflow_stamp_finding_gated - with a docstring recording that the loader version still does stamp-only. One obligation, two implementations that disagree, and the canonical docstring still claims it is evaluated once so the two surfaces always agree. ST2 collapses the fork and puts a test on the agreement.
- [2026-08-25T21:45:16Z] Elias Python:
  - Gated workflow_stamp_finding (_workflow/_loader.py) on artifact_changed_since(WORKFLOW_KEY, stamp); message now names the bundled document changing, not the stamp age.
  - Import decision recorded in-place as a comment above the new import in _workflow/_loader.py: package-granular cycle only, module-granular is a DAG (_overrides/_manifest imports nothing beyond squads._util), and _interactions/_loader.py already takes this identical edge for the playbook obligation.
  - Deleted _overrides/_service.py::_workflow_stamp_finding_gated; _check_workflow_override_issues now calls the canonical workflow_stamp_finding directly.
  - Added a parametrized agreement test (tests/unit/test_workflow_lint_merge_errors.py) driving lint_workflow_spec and check_override_issues over the same override content across add-only-unstamped / shadowing-unstamped / stamped-with-change / stamped-without-change / unrecorded-base-version, asserting identical (level, message) sets.
  - Updated one lint test whose fixture (an unrecorded-base stamp) predated content-gating and would now assert the old false positive; split it into a real-drift case (v0.13.1) and a new unrecorded-history case.
  - tests/meta: 227 passed. Targeted (workflow lint + override lifecycle + workflow service integration + manifest freshness): 138 passed. pyright/ruff/ruff format clean. sq check clean.
<!-- sq:discussion:end -->
