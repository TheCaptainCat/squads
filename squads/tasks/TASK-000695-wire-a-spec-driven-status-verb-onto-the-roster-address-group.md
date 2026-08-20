---
id: TASK-695
sequence_id: 695
type: task
title: Wire a spec-driven status verb onto the roster address groups
status: Done
parent: FEAT-691
author: tech-lead
description: Register the status verb on the role/skill/operator addressed subgroups,
  driven by the addressed type's declared lifecycle
subentities:
- local_id: ST1
  title: Register the status verb on all three roster address subgroups
  status: Done
  story: US1
- local_id: ST2
  title: Match the work-item status verb's --force and error shape
  status: Done
  story: US1
- local_id: ST3
  title: Derive allowed targets from the addressed type's lifecycle
  status: Done
  story: US2
- local_id: ST4
  title: Add the verb to the addressed-verb help and grammar blocks
  status: Done
  story: US3
- local_id: ST5
  title: Add the verb to the roster grammar lines in README and docs
  status: Done
  story: US3
- local_id: ST6
  title: Cover the verb with a service test and a CLI smoke test
  status: Done
  story: US1
created_at: '2026-07-29T14:43:04Z'
updated_at: '2026-07-31T12:41:19Z'
---
<!-- sq:body -->
## Context

`sq role`, `sq skill`, and `sq operator` each build their own addressed subgroup — the hidden
`_addr` Typer app in `_cli/_role.py`, `_cli/_skill.py`, `_cli/_operator.py` — and register
`show`/`regen`/`rm` (operator: `show`/`rm`) by hand. None registers `status`, so
`sq role manager status Archived` dies on Click's `No such command 'status'` and a roster entity
can never leave the status it was created with.

The engine side needs no work, and that was verified rather than assumed. `Service.set_status` →
`_set_status_core` → `_apply_status` (`_services/_items.py`) reads
`spec.workflow_for(item.type).states` and `spec.can_transition(item.type, …)`, so it is already
type-agnostic. Driven directly against a throwaway squad, for role, skill and operator alike:
`set_status(<role-id>, "Archived")` succeeds; an off-lifecycle target raises
`StatusNotInWorkflowError` (`'InProgress' is not a valid status for role (allowed: Active,
Archived, Draft)`); a disallowed edge raises `InvalidTransitionError` (`role cannot move
Archived → Draft (use --force to override)`); `force=True` overrides the edge check. This is a
CLI registration gap and nothing more.

## Scope

Register a `status` verb on all three addressed subgroups from **one** shared implementation, not
three copies. `_cmd_status` in `_cli/_items.py` is the shape to match: a `STATUS` positional, a
`--force` flag, and the `{id} → {status}` confirmation line. The three modules do not share a ctx
convention, and both conventions must be honoured:

- `_cli/_role.py` stores `{"addr": <raw>, "id": <id-or-None>}` — a slug that exists only in the
  bundled catalog resolves to `None`. The new verb must read the id through that module's existing
  `_require_id`, so `sq role <bundled-but-not-activated-slug> status Active` produces the existing
  "activate it first" error rather than a traceback.
- `_cli/_skill.py` and `_cli/_operator.py` store `{"id": <id>}` and always resolve strictly.

Allowed targets come from the addressed type's declared lifecycle, via the spec-driven core that
already enforces it. No roster status name may appear as a literal in the new code: the verb must
not add a second, narrower gate on top of the spec's.

Every help surface that already enumerates the addressed verb set must gain the new verb:

- `AddressDispatchGroup._ADDR_VERBS` in `_cli/_common.py` (the shared default behind `sq role` and
  `sq skill`) and `_OperatorDispatchGroup._ADDR_VERBS` in `_cli/_operator.py` (`show|rm` —
  operators carry no pointer, so they have no `regen` and must not gain one here).
- the `epilog=` string on `role_app`, `skill_app`, and `operator_app`.
- the grammar block in each of the three module docstrings.
- the adopter docs that spell the grammar out: `README.md` (the roster command lines),
  `docs/roles.md`, and `docs/stability.md` (the item-first roster grammar). Grammar-line edits
  only — no new prose sections, no restructuring.

## Out of scope

- `sq workflow types --json` type→lifecycle→states introspection, which the parent feature
  explicitly excludes.
- Any change to `show`/`regen`/`rm`/`list`/`activate`/`add` behaviour or output.
- Filtering managed or generated output by roster status. `Service.roster()` and
  `Service.operators()` deliberately ignore status, so an archived role keeps its `.claude`
  pointer, stays in CLAUDE.md's roster section, and stays a valid `--as`/`--assignee` slug. Leave
  all of that alone; a change there is a separate decision with its own consequences.
- The generated agent-facing surfaces. The `squads` skill and the CLAUDE.md/AGENTS.md managed
  region do not enumerate the roster addressed verbs at all, so there is nothing to update there —
  do not add new roster grammar to those templates, and do not add a roster-type item skill.

## Acceptance

- `sq role <slug|id|n> status <S>`, `sq skill <slug|id|n> status <S>`, and
  `sq operator <slug|id|n> status <S>` transition the entity's frontmatter `status` and print the
  same confirmation shape as the work-item verb.
- A target outside the addressed type's lifecycle and a target the lifecycle does not allow from
  the current status both exit 1 carrying the `StatusNotInWorkflowError` / `InvalidTransitionError`
  messages quoted above. `--force` overrides the transition check and not the vocabulary check,
  exactly as it does for a work item.
- `sq role <bundled-but-not-activated-slug> status <S>` gives the existing "activate it first"
  error: exit 1, no traceback.
- A wrong-type address (e.g. `sq operator <a-role-number> status <S>`) gives the existing clean
  wrong-type error: exit 1, no traceback.
- No roster status name appears as a literal in the new code.
- `sq role --help`, `sq skill --help`, `sq operator --help`, and the "missing verb after address"
  error all list the new verb.
- `sq list -t role --all --json`, `sq role list --json`, and `sq operator list --json` report the
  new status with no change to those commands — they already read `Item.status`.
- `sq check` is clean and `sq repair` is a no-op after a transition, and `sq sync` does not revert
  it.
- Gate clean: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run
  --all-extras ruff format --check .`. The `--all-extras` is mandatory on each — a bare `uv run`
  prunes the optional `tui` extra and pyright then reports hundreds of false unresolved-import
  errors under `_tui/`.
- Full suite green, `tests/meta/` included: the docs-resolve-against-the-CLI drift guard scans
  `docs/*.md` and will exercise the new doc lines.

## Tests

- **Service level** — `tests/service/test_status_vocabulary_enforcement.py`: each roster type
  transitions through its declared lifecycle, rejects an off-lifecycle target and a disallowed
  edge with the two named error types, and honours `force`. This belongs with the existing
  per-type vocabulary enforcement rather than in a new file.
- **CLI smoke** — `tests/cli/test_roster_type_address_verbs.py`: the new verb resolves an address
  by bare number, full ID, and slug for all three types; the bundled-only-slug and wrong-type
  paths stay clean; `--force` works; the help and missing-verb text list the verb. That module's
  docstring currently describes the mutating verb set as `regen`/`rm` — extend it.
- Name tests by behaviour. No ticket ID in any file name, test name, or source comment.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 695 add-subtask "<title>"`; track with `sq task 695 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Register the status verb on all three roster address subgroups | US1 |
| ST2 | Done |  | Match the work-item status verb's --force and error shape | US1 |
| ST3 | Done |  | Derive allowed targets from the addressed type's lifecycle | US2 |
| ST4 | Done |  | Add the verb to the addressed-verb help and grammar blocks | US3 |
| ST5 | Done |  | Add the verb to the roster grammar lines in README and docs | US3 |
| ST6 | Done |  | Cover the verb with a service test and a CLI smoke test | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Register the status verb on all three roster address subgroups

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a manager, I can set a role's/skill's/operator's status from the CLI
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
One shared registration used by all three `_addr` subgroups in `_cli/_role.py`, `_cli/_skill.py`,
and `_cli/_operator.py` — not three copies of the same closure. `_cmd_status` in `_cli/_items.py`
is the reference shape: a `STATUS` positional, a `--force` flag, `svc.set_status(...)`, and the
`{id} → {status}` confirmation line.

The two ctx conventions both have to work. `_cli/_role.py` stores `{"addr": <raw>, "id":
<id-or-None>}` and needs the id read through its existing `_require_id`, so a bundled-but-not-yet-
activated slug still yields the "activate it first" error. `_cli/_skill.py` and
`_cli/_operator.py` store `{"id": <id>}` and resolve strictly. Pick the seam that expresses that
difference without leaking role's fallback logic into the other two — a registration helper taking
an id-extraction callable is one way; the layering rule is that the shared piece lives in
`_cli/_common.py` alongside `AddressDispatchGroup`, not in `_cli/_items.py` (the work-item factory).

Done when all three verbs exist, resolve an address by bare number, full ID, and slug, and write
the frontmatter `status` through `Service.set_status`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Match the work-item status verb's --force and error shape

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a manager, I can set a role's/skill's/operator's status from the CLI
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Behaviour parity with the work-item `status` verb, verb-for-verb:

- `--force` present and doing the same thing it does for a work item — overriding the transition
  check, never the vocabulary check.
- An off-lifecycle target surfaces `StatusNotInWorkflowError` and a disallowed edge surfaces
  `InvalidTransitionError`, both as the CLI's clean `error:` line with exit 1 and no traceback.
  Both errors already come out of `_apply_status` with the right text and both already subclass
  `SquadsError`, so the requirement here is to not intercept, re-wrap, or reword them.
- The success line matches the work-item verb's shape.
- A wrong-type address keeps the existing clean wrong-type error from `resolve_agent_addr`.

Done when the exit code, stderr/stdout shape, and message text for each failure mode are
indistinguishable from the work-item verb's, modulo the type and status names in them.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Derive allowed targets from the addressed type's lifecycle

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an adopter, a custom roster lifecycle gets the same command for free
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
The allowed target set is read from the addressed type's own declared lifecycle —
`WorkflowSpec.machine_for` / `can_transition`, which the spec-driven core already consults. The new
verb must add no gate of its own: no membership test against a roster status name, no branch on the
type being a roster type, nothing that would have to be edited if a project renamed or extended the
lifecycle its roster types are bound to.

Concretely: no `Draft`, `Active`, or `Archived` string literal in the new code, and no import of
the `STATUS_*` constants into the new verb. `parse_status` (which validates against the whole
spec's status vocabulary) stays the CLI-side parse step exactly as it is for work items; the
per-type narrowing is the service's job and must be left there.

The observable proof needs no override file: because the error text enumerates the addressed type's
own states (`'InProgress' is not a valid status for role (allowed: Active, Archived, Draft)`), an
assertion on that enumeration demonstrates the set is derived per type rather than fixed. Worth
knowing while doing this: the workflow override loader is additive-only and refuses to redefine a
built-in type or lifecycle, so a project cannot today rebind the bundled roster types to a
lifecycle of its own — which is why the proof is structural plus error-text derivation rather than
an end-to-end run against a renamed roster lifecycle.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Add the verb to the addressed-verb help and grammar blocks

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a team, the generated CLI help and skill text teach the new verb
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Every in-CLI surface that already enumerates the addressed verb set gains the new verb, so the
command is discoverable rather than merely present:

- `AddressDispatchGroup._ADDR_VERBS` in `_cli/_common.py` — the shared default (`show|regen|rm`)
  behind `sq role` and `sq skill`, used in the "missing verb after address" error.
- `_OperatorDispatchGroup._ADDR_VERBS` in `_cli/_operator.py` — `show|rm`; operators carry no
  Claude pointer and must not gain a `regen` here.
- the `epilog=` string on `role_app`, `skill_app`, and `operator_app`, including the "Address a
  …" line and the examples.
- the grammar block in each of the three module docstrings.

Keep the epilogs within the pinned help width — `sq <group> --help` renders through Rich at
COLUMNS=80 in the suite.

Done when `sq role --help`, `sq skill --help`, `sq operator --help`, and the missing-verb error
each name the new verb.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Add the verb to the roster grammar lines in README and docs

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a team, the generated CLI help and skill text teach the new verb
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
The adopter-facing docs that already spell out the roster address grammar gain the new verb.
Grammar-line edits only — no new prose sections, no restructuring, and nothing about how the change
was made:

- `README.md` — the roster command lines that read `sq role <slug|id|n> show|regen|rm [--purge]`
  and the `sq skill` equivalent.
- `docs/roles.md` — the roster command cheatsheet block.
- `docs/stability.md` — the item-first roster grammar list. Adding a verb is additive under that
  document's own evolution rule, so this is an extension of the documented surface, not a change
  to it.

`tests/meta/test_documented_commands_resolve_against_cli.py` walks every `sq …` invocation in
`docs/*.md` against the live command tree, so a doc line citing the verb only passes once the verb
is registered. README is outside that scan — check its lines by hand.

Done when the three files describe the verb and the meta suite is green.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Cover the verb with a service test and a CLI smoke test

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a manager, I can set a role's/skill's/operator's status from the CLI
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
Two homes, both existing files, tests named by behaviour with no ticket ID anywhere in a file name,
test name, or comment.

**Service level** — `tests/service/test_status_vocabulary_enforcement.py`: each roster type moves
through its declared lifecycle, rejects a status outside that lifecycle and an edge the lifecycle
does not allow (asserting the two error types, and that the message enumerates that type's own
states), and honours `force`. This sits with the existing per-type vocabulary enforcement rather
than in a new file.

**CLI smoke** — `tests/cli/test_roster_type_address_verbs.py`: the verb resolves an address by bare
number, full ID, and slug for role, skill, and operator; a bundled-but-not-activated role slug
gives the activate-first error; a wrong-type address stays clean; `--force` overrides a disallowed
edge; the help and missing-verb text name the verb. Extend that module's docstring, which currently
describes the mutating verb set as `regen`/`rm`.

Also confirm, once, that a transitioned roster entity leaves the board consistent: `sq check`
clean, `sq repair` a no-op, `sq sync` not reverting the status, and the status visible in
`sq list -t role --all --json`. Fold whatever of that is cheap to assert into the CLI module rather
than adding a third test file.

Run the fast selectors while iterating; the full suite and the `--all-extras` gate are the parent
task's acceptance.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T14:45:03Z] Olivia Lead:
  - Broken down from FEAT-691 as a single task: the wiring, the help/epilog text and the docs grammar lines all live in the same three CLI modules (plus `_ADDR_VERBS` in `_cli/_common.py`), so splitting them would put two devs in the same files for a ~3-line docs delta.
  - Verified the seam before writing: the three `_addr` subgroups register show/regen/rm by hand and no status verb; `Service.set_status` → `_apply_status` is already fully type-agnostic (driven off `spec.workflow_for(item.type).states` + `can_transition`) and produces the right error shapes for role/skill/operator as-is. CLI registration only.
  - Subtask→story: ST1/ST2/ST6 → US1, ST3 → US2, ST4/ST5 → US3.
- [2026-07-29T14:58:43Z] Elias Python:
  - Implemented: shared `register_status_verb` helper in _cli/_common.py (id_from_ctx seam), registered on role/skill/operator addressed subgroups; `_ADDR_VERBS` and epilogs/docstrings updated in all three modules + _OperatorDispatchGroup.
  - No status literal in the new code — allowed targets come from Service.set_status → _apply_status (spec.workflow_for/can_transition), unchanged.
  - Tests: tests/service/test_status_vocabulary_enforcement.py (+6 roster tests) and tests/cli/test_roster_type_address_verbs.py (+9 tests: resolution by number/id/slug, activate-first fallback, wrong-type, off-lifecycle, disallowed-edge+force, help/missing-verb, check/repair/sync consistency). Falsified: commenting out the three registration calls turned all 9 new CLI tests red (Click 'No such command status'); restored → green.
  - Docs: README.md, docs/roles.md, docs/stability.md grammar lines extended (ST5).
  - Gates clean: pyright, ruff check, ruff format --check (--all-extras); sq check clean.
<!-- sq:discussion:end -->
