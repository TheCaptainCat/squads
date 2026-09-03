---
id: TASK-844
sequence_id: 844
type: task
title: Migrate leaves role pointers drifted against its own runbook
status: Done
parent: FEAT-693
author: tech-lead
priority: medium
refs:
- REV-840:addresses
- FEAT-321:addresses
description: sq migrate up leaves three role pointers drifted and sq check says so,
  while the runner's MANUAL tells the operator no action is required
subentities:
- local_id: ST1
  title: 'Decide and apply: runbook step or a role-pointer pass'
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Close the parity test's .claude/agents blind spot
  status: Done
  assignee: python-dev
created_at: '2026-08-26T17:06:57Z'
updated_at: '2026-08-26T17:48:11Z'
---
<!-- sq:body -->
## Problem

After `sq migrate up`, every role whose preload list gained one of the two new item skills still
carries the pre-0.14 list in its backend pointer. `sq check` reports the drift. The runner's own
MANUAL runbook tells the operator "No action is required."

Driven as a migrate-vs-init parity check with the full bundled roster: two squads from one
`sq init --roles all`, squad B stripped back to a pre-0.14 shape — including the `sq-contract` /
`sq-milestone` lines in the `.claude/agents/*.md` preload lists, which is what a squad generated
before the types existed actually looks like — then `_v0_11_to_v0_14.migrate` run and the trees
diffed:

```
diff -r a/.claude/agents/architect.md b/.claude/agents/architect.md
<   - sq-contract
diff -r a/.claude/agents/product-owner.md b/.claude/agents/product-owner.md
<   - sq-contract
<   - sq-milestone
diff -r a/.claude/agents/tech-lead.md b/.claude/agents/tech-lead.md
<   - sq-contract
<   - sq-milestone
```

`sq check` in the migrated squad reports managed-pointer drift on all three. `sq sync` converges the
two trees exactly — `diff -r a/.claude b/.claude` is empty afterwards.

## The contradiction to resolve

The runner's module docstring is internally consistent with the behaviour: it states plainly that the
runner does not touch any existing role's own per-entry pointer, and that convergence is an ongoing
`sq sync` responsibility. The MANUAL runbook the operator reads says the opposite.

MANUAL is a durable, adopter-facing promise — it is what `sq migrate chlog` prints for a release
range, long after anyone remembers the runner's internals. So one of the two has to move, and the
decision is which: add a `sq sync` step to the runbook, or add a `generate_role_entry` pass over the
live roster to `_regenerate_surface`. Reason from an adopter migrating their own squad, not from this
repository: they run the runbook, read "no action is required", and their next `sq check` is dirty.

## Acceptance criteria

- Immediately after `sq migrate up` on a pre-0.14 squad with the full bundled roster, either
  `sq check` is clean, or the runbook the operator just followed told them the step that makes it
  clean.
- The chosen direction is recorded with its reasoning, and the runner's module docstring and MANUAL
  no longer contradict each other.
- The parity test would fail today and passes after the change.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite clean; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 844 add-subtask "<title>"`; track with `sq task 844 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Decide and apply: runbook step or a role-pointer pass |  |
| ST2 | Done | python-dev | Close the parity test's .claude/agents blind spot |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Decide and apply: runbook step or a role-pointer pass

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Settle the contradiction between the runner's behaviour and the runbook it hands the operator, then
apply whichever side moves.

Two options, both small:

- **Runbook.** Add the `sq sync` step to MANUAL in `src/squads/_migrations/_v0_11_to_v0_14.py`,
  replacing "No action is required." Cheapest and most honest about what the runner does — the module
  docstring already says convergence is an ongoing `sq sync` responsibility, so this makes the two
  agree without changing what migration means.
- **Runner.** Add a `generate_role_entry` pass over the live roster to `_regenerate_surface`, so
  migration converges the pointers itself. Costs more and widens what a migration touches, but leaves
  the adopter with a clean `sq check` and no remembered step.

Reason from an adopter migrating their own squad, not from this repository: they run the runbook,
read that no action is required, and their next `sq check` is dirty on three files they did not
touch. Weigh that against the principle that generated pointers are regenerable and never migrated.

Whichever way it goes, land it so the runner's module docstring and its MANUAL no longer say opposite
things, and record the reasoning in a comment on the task — MANUAL is what `sq migrate chlog` prints
for a release range long after anyone remembers the runner's internals.

Done when: a pre-0.14 squad with the full bundled roster ends `sq migrate up` either clean under
`sq check`, or told exactly which step makes it clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Close the parity test's .claude/agents blind spot

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Close the parity test's blind spot, so the next type addition cannot land in it.

`tests/integration/test_new_item_type_migration_surface_parity.py::_strip_new_type_surface` removes
the type folders, the two skill bodies, their `.claude/skills/<slug>/` pointers and their index
entries — but never touches `.claude/agents/*.md`. Squad B therefore enters the migration already
carrying the correct preload lists, so the assertion can only pass. The test's own docstring names
the defect class it exists to catch — a type addition wired into `init` but left unregenerated on
`migrate` — and the role-pointer drift is an instance of exactly that class, sitting inside its blind
spot.

It also runs `roles_spec="minimal"`, so even a strip that did cover the pointers would likely miss
this one: the affected roles are architect, product-owner and tech-lead.

Two changes: extend the strip to remove the new types' skill lines from `.claude/agents/*.md` preload
lists, so squad B genuinely looks like a squad generated before the types existed; and run the parity
assertion against a roster wide enough to contain the affected roles rather than `minimal`. Keep a
`minimal` case too if it is cheap — the point is that the wide case exists, not that the narrow one
goes away.

Falsify it before handing back: confirm the extended test fails against the current runner, then
passes after the fix, and report both.

One nearby gap the reviewer flagged but did not drive, worth covering if it is cheap: a squad
carrying `<tech>-dev` roles, where `skills_for_role`'s `*dev` sentinel now resolves `sq-contract`
(`tests/unit/test_skills_for_role_mapping.py:39-43`). The same mechanism almost certainly drifts a
dev role's pointer too. Adding a dev changes the roster mid-probe, so if it makes the two trees
incomparable, say so rather than forcing it.

Done when: the parity test would have caught this drift, and covers a roster containing the roles it
affects.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T17:20:27Z] Elias Python:
  - Resolved toward MANUAL, not the runner: replaced 'No action is required' with a 'run sq sync next' step naming the affected roles (architect, product-owner, tech-lead, every <tech>-dev) and the pre-fix sq check warning. Did not add a generate_role_entry pass to _regenerate_surface.
  - Why: doing the regen correctly needs each role's full resolved preload set including any adopter scoped-skill ref edges, which means reading corpus ref data and freezing local copies of split_ref/ref_id_matches (forbidden _models wire-encoding primitives) -- real scope growth for a runner meant to stay light, and a naive regen (empty role_skills, falling back to the pure skills_for_role) would silently drop an adopter's custom-scoped skills from an affected role's pointer, a worse defect than the one being fixed. The runner's own docstring reasoning (pointer convergence is an ongoing sq sync responsibility) holds up under that weighing; added one sentence there tying it explicitly to MANUAL so the two no longer read independently.
  - Confirmed the drift extends beyond the review's three roles to a <tech>-dev role's pointer too: constructed cleanly by adding the dev role to both comparison squads before either diverges (not mid-probe) -- python-dev's pointer gains sq-contract via the *dev sentinel and drifts exactly like the other three.
  - Driven adopter sequence (init --roles all + a python dev, faked to pre-0.14, sq migrate up): sq check warned managed pointer had drifted on architect.md/product-owner.md/tech-lead.md/python-dev.md while MANUAL still said no action required; sq sync converged all four and check went clean.
  - ST2: extended _strip_new_type_surface to also strip the two skills' lines from every .claude/agents/*.md pointer, widened the parity roster from minimal to all+dev, and added a test encoding the actual contract (drift is real only if MANUAL names sq sync as the remedy, and sq sync must actually converge it). Falsified: fails on the unmodified MANUAL text, passes after.
  - tests/meta full: 246 passed, 14 failed -- all 14 pre-existing in two other in-flight dev's files (_workflow/_models.py milestone_rollup view validation; an untracked FEAT-6 ticket-id hygiene violation in tests/cli/test_leaf_verb_render_honours_overrides.py), none in my territory. pyright/ruff clean on my two touched files. sq check clean.
<!-- sq:discussion:end -->
