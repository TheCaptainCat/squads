---
id: TASK-708
sequence_id: 708
type: task
title: Regenerate a reactivated roster entry through one projection path
status: Done
parent: FEAT-691
author: tech-lead
priority: high
refs:
- REV-706:addresses
- ADR-697:implements
description: One materialise-or-withdraw helper for sync and the transition path,
  so reactivation regenerates in full
subentities:
- local_id: ST1
  title: Collapse the two projections into one helper
  status: Done
  story: US4
- local_id: ST2
  title: Regenerate a reactivated entry with its full preload list
  status: Done
  story: US4
created_at: '2026-07-31T09:36:35Z'
updated_at: '2026-07-31T12:41:30Z'
---
<!-- sq:body -->
## Context

One projection has two implementations. `_services/_base.py::_project_roster_transition` applies
the materialise-or-withdraw predicate and hands the backend a context built as
`BackendContext(paths=..., spec=...)` — no `role_skills`. `sq sync`'s roster sweep in
`_services/_maintenance.py` applies the same predicate over the same `spec.live_statuses` read,
but builds its context from `_role_skills_map()` first. The two agree on the predicate and
disagree on the inputs, so reactivating a role writes a pointer whose preload list is missing
every skill the role holds through a `scopes` edge.

ADR-697 §2 is explicit that there is nothing to repair here: "Reactivate — materialise again, in
full. Because the artifact is a projection there is no partial-regeneration or repair path to
design." §6 calls `sq sync` "the total convergence point for the projection". What ships is a
partial regeneration whose repair path is `sq sync`.

## Evidence

```
$ sq skill add "Custom Helper"; sq skill custom-helper link-role qa
$ grep -c custom-helper .claude/agents/qa.md
1
$ sq role qa status Archived; sq role qa status Active
$ grep -c custom-helper .claude/agents/qa.md
0
$ sq check
✓ no issues
$ sq sync; grep -c custom-helper .claude/agents/qa.md
1
```

The role item's own record lists the skill throughout — `extra.skills` and the body's `## Skills`
region both name it — so the generated pointer and the item it projects from silently disagree
until the next sync. Nothing surfaces it: no currency check exists for this projection by design
(ADR-697 §6), and the agent host reads the pointer, so the only visible symptom is an agent that
has quietly lost a skill.

## Scope

Extract one helper that takes a roster item and performs materialise-or-withdraw plus the managed
region recompile, and have both `_project_roster_transition` and `sq sync`'s roster sweep call it.
One predicate, one context construction, one code path. The duplication is what the defect cost;
fixing only the missing `role_skills` argument leaves the two implementations free to diverge
again on the next input either of them grows.

Keep the existing division of labour intact while doing it:

- The projection write stays **after** the transaction commits — a generated file is regenerable
  cache, not a markdown item, so it sits outside the markdown-ahead-of-index durability rule.
- Both directions keep fanning out over every deduped entry of `active_backends`, and a backend
  absent from that list keeps being left untouched.
- Withdrawal keeps going through the existing `remove_artifacts` (missing-tolerant and idempotent
  by its own contract), and every transition in either direction keeps ending with the managed
  regions recompiled, because withdrawal changes generated prose beyond the roster table.
- `sq sync` keeps refreshing an item's own sq-managed state (the catalog-extra merge, the
  resolved-skills cache, the rendered body) unconditionally regardless of liveness — only the
  backend projection is gated on the predicate. Whatever the helper covers, it must not pull that
  unconditional refresh under the liveness gate.
- Resolving the preload map is one index read for the whole roster (`_role_skills_map`), not one
  read per role; a single-entry transition must not regress into the per-role path.

## Out of scope

`_services/_config_integrity.py` and `_services/_retirement.py` — the clause family and its
enforcement, including the generated prose that names the default role, are a separate item and
must not be touched here. The adopter-facing changelog entry for withdrawal.

## Acceptance

- The evidence sequence above ends with the skill still in the pointer, with no `sq sync` in
  between: retire a role holding a scoped skill, reactivate it, and its regenerated pointer
  preloads exactly what a first creation would.
- The pointer a reactivated role gets is byte-identical to the one `sq sync` writes for it
  immediately afterwards — the sync is a no-op, and a test asserts that rather than asserting a
  substring.
- One helper is the only place the materialise-or-withdraw predicate and its backend context are
  expressed; neither caller reconstructs either.
- A skill entry reactivates in full the same way, and an operator transition still skips straight
  to the region refresh with no per-entry file involved.
- With `active_backends = []` both directions are a clean no-op; with two active backends both
  fan out.
- `sq sync` stays idempotent, and still converges a squad whose entry was retired before any of
  this landed, with no migration.
- `uv run sq check` clean, `sq repair` a no-op.
- `uv run --all-extras` clean on each of `pyright`, `ruff check .`, `ruff format --check .`.
- Full suite green.
- Falsify the regeneration test: revert the context to the skill-less one, watch it go red,
  restore it, watch it go green, and report both.

## Tests

`tests/service/test_roster_projection_predicate.py` already owns this surface — extend it rather
than adding a parallel module. Cover the round trip (retire, reactivate, compare against what a
sync would write), the single-helper claim through observable behaviour rather than by asserting
on private names, and the skill/operator variants. Name every test by behaviour; no ticket ID or
finding label in a file name, test name or comment.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 708 add-subtask "<title>"`; track with `sq task 708 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Collapse the two projections into one helper

<!-- sq:subtask:ST1:body -->
One helper takes a roster item and performs materialise-or-withdraw plus the managed-region recompile; both the transition path and the sync sweep call it. One predicate, one backend-context construction, one code path — fixing only the missing argument would leave the two free to diverge again on the next input either grows. The sweep's unconditional refresh of an item's own sq-managed state must not move under the liveness gate.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Regenerate a reactivated entry with its full preload list

<!-- sq:subtask:ST2:body -->
Reactivation currently writes a pointer missing every skill the role holds through a scoping edge, because the transition path hands the backend a context with no resolved preload map. The pointer a reactivated role gets must be byte-identical to the one a sync writes immediately afterwards, and the sync a no-op. Resolve the map in one index read for the whole roster, not one per role.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T10:42:46Z] Elias Python:
  - Extracted one helper, _project_roster_item(item, ctx), that owns the materialise-or-withdraw predicate + backend dispatch; both _project_roster_transition (base.py) and sync's roster sweep (maintenance.py) call it with a ctx whose role_skills came from one _role_skills_map() index read. Neither caller reconstructs the predicate or the context separately anymore.
  - F1 root cause confirmed: _project_roster_transition previously built ctx = self._ctx (empty role_skills), so ctx.resolved_skills_for() fell back to system-only skills, dropping every scopes-derived skill on reactivate. Fixed by resolving _role_skills_map() before the single-item projection call, same as sync already did.
  - Kept the managed-region recompile (refresh_managed/write_managed) as a separate call from the per-item helper, not folded into it: sync still recomputes/writes the region once for the whole sweep (not once per item), preserving the one-index-read-per-sync shape; the single-item transition path still ends with its own refresh_managed() call, unchanged.
  - New tests in tests/service/test_roster_projection_predicate.py (TestReactivationRestoresAScopedSkill, TestOperatorTransitionHasNoPerEntryFile): scoped-skill round trip with no sync in between, a falsification test reconstructing the old empty-role_skills context to prove it drops the skill, a byte-identical-to-post-sync assertion, the AGENTS.md backend equivalent, the skill-entry variant, and the operator no-per-entry-file case.
  - Falsified: stashed the base.py/maintenance.py fix, ran the 4 new regression tests -> 4 failed, 10 passed (exact AssertionErrors showing custom-helper missing from the pointer / sync not a no-op). Restored the fix -> all 25 in the file green.
  - Gates: uv run --all-extras pyright (0 errors), ruff check . (all checks passed), ruff format --check . (416 files formatted), uv run sq check (no issues). Full suite left to the integrator per brief.
<!-- sq:discussion:end -->
