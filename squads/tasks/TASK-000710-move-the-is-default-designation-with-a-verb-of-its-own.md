---
id: TASK-710
sequence_id: 710
type: task
title: Move the is_default designation with a verb of its own
status: Done
parent: FEAT-691
author: tech-lead
priority: low
refs:
- ADR-697:implements
- REV-706
description: 'A role designation verb with move semantics: one live holder, every
  other cleared, non-live refused'
subentities:
- local_id: ST1
  title: Designate by moving, refusing a non-live target
  status: Done
- local_id: ST2
  title: Expose it as its own verb and document it
  status: Done
created_at: '2026-07-31T09:36:45Z'
updated_at: '2026-07-31T12:41:34Z'
---
<!-- sq:body -->
## Context

`is_default` marks the role a generated agent host routes to when no agent is named. Nothing
interactive writes it: `_roles/_catalog.py::RoleDef.to_extra` sets it from the bundled catalog at
`sq role activate`, and after that the key is only ever read. `sq role --help` and `sq role <addr>
--help` offer `catalog`, `list`, `activate`, `show`, `regen`, `rm`, `status` — no designation verb,
and no `update`. The one path that writes the key today is the bulk importer's `update` event
reaching it through `coerce_extra`, which is history replay rather than a designation and must
never be named as the way to do this.

ADR-697 §9 specifies the verb. It is not a prerequisite for any retirement: the clause that once
refused retiring the designated role is withdrawn, so the missing verb costs an adopter a
capability rather than blocking an action.

## The verb is a move, not a set

The projection resolves the designation by **first match** over the roster, and nothing validates
a single holder at item level — the role-catalog loader's "at most one `is_default`" check governs
the *spec*, not activated items. So a plain set silently produces two holders and an arbitrary
winner; the architect reproduced exactly that. The verb must therefore designate one live role and
clear every other holder in a single transaction.

Two further rules from §9:

- **Designating a non-live role is refused rather than stored.** A designation the projection
  cannot read is not a designation.
- **It is its own verb, not a flag on `status`.** Moving a designation and retiring an entry are
  unrelated acts; a status flag doing both is the overloading `--force` and `--unlink` are kept
  apart to avoid.

## Scope

A designation verb on the `role` surface, with move semantics, refusing a non-live target, and
projecting the result — the generated default-role line and the surrounding orchestration prose
read the same value, so both refresh after the move. It reports what it changed, including the
holder it cleared, and reflogs the designation move.

Because the generated prose omits the default-role line entirely when no live role carries the
designation, this verb is also the way back from that state: worth saying so in the adopter-facing
text.

## Exposure this makes visible

Two live roles can already carry the designation today — the importer's `update` path reaches the
key, and the projection then picks by roster order with nothing reporting the ambiguity. A `sq
check` reporter for that state is exposure made **visible**, not created, and is a candidate for
whoever next works this surface. It is deliberately not part of this item: a verb with move
semantics is what stops the state being reachable through the sanctioned path, and a reporter for
a state only history replay can produce is a smaller, separable question.

## Out of scope

The config-integrity clause family and its enforcement. A reporter for the two-holder state, per
above. Any change to how the projection resolves the designation — first match stays, because a
move-semantics verb makes a second holder unreachable through the verb.

## Acceptance

- One command designates a live role as default; the previous holder is cleared in the same
  transaction, and the command names both.
- Designating a non-live role is refused, naming why.
- After the move, the generated default-role line and the orchestration prose both name the new
  role, in every active backend.
- Running the verb against a squad where two roles carry the designation leaves exactly one.
- Designating the role that already holds it is a reported no-op, not an error.
- With `active_backends = []` the designation is still recorded; there is simply nothing to
  project.
- `uv run sq check` clean, `sq repair` a no-op.
- `uv run --all-extras` clean on each of `pyright`, `ruff check .`, `ruff format --check .`.
- Full suite green, plus a service test and a CLI smoke test.
- Adopter-facing: a changelog entry and a `docs/roles.md` line, both naming this as the way back
  from a squad with no designated role.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 710 add-subtask "<title>"`; track with `sq task 710 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Designate by moving, refusing a non-live target

<!-- sq:subtask:ST1:body -->
One transaction designates a live role and clears every other holder, because the projection resolves by first match and nothing validates a single holder at item level — a plain set silently yields two holders and an arbitrary winner. Designating a non-live role is refused rather than stored: a designation the projection cannot read is not a designation. Re-designating the current holder is a reported no-op.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Expose it as its own verb and document it

<!-- sq:subtask:ST2:body -->
A verb on the role surface, not a flag on status — moving a designation and retiring an entry are unrelated acts. It reports what changed including the holder it cleared, reflogs the move, and refreshes the generated default-role line and the orchestration prose that reads the same value. Adopter-facing text names it as the way back from a squad with no designated role.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T09:54:25Z] Catherine Manager:
  - Confirmed in scope for FEAT-691 rather than reparented. It maps to no story because US1-US6 predate it; acceptance for the feature therefore includes this task explicitly. Sequenced after the projection fix and before the adopter docs, so the docs can cover the new verb in one pass.
- [2026-07-31T11:00:39Z] Elias Python:
  - Verb: sq role <addr> set-default (Service.set_default_role). Moves the designation: clears every other holder (not just one — repairs a pre-existing two-holder state too) in the same transaction as designating the target.
  - Already-holds-it -> reported no-op (changed=False), unless a stray second holder exists, in which case that holder is still cleared and the result reports changed=True.
  - Non-live target -> refused (SquadsError, 'is not live'): a designation the projection can't present isn't a designation.
  - Projection: is_default never appears in a role's own pointer file, only in the compiled CLAUDE.md/AGENTS.md region, so refresh_managed() (the same path set_roster_status already uses) is sufficient — no per-entry regen needed.
  - One reflog line per move: op=default_role, delta={cleared:[...]}; skipped entirely on a true no-op.
  - Updated lost_default_designation_warning's text to name the new verb as the way back, now that it exists.
  - Tests: tests/service/test_default_role_designation_move.py, tests/cli/test_role_set_default_command_cli.py — falsified each behaviour (clearing loop, non-live refusal, no-op flag, projection refresh) red then green.
  - Docs: CHANGELOG.md (0.13.0 Added) + docs/roles.md; not building the two-holder sq check reporter per the task's explicit scope.
<!-- sq:discussion:end -->
