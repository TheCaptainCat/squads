---
id: TASK-699
sequence_id: 699
type: task
title: Key roster lifecycle semantics off status roles, drop Draft
status: Done
parent: FEAT-691
author: tech-lead
priority: high
refs:
- ADR-696:implements
description: Derived role-keyed status accessors, the roster lifecycle floor, and
  the bundled two-state roster lifecycle
subentities:
- local_id: ST1
  title: Add the role-keyed status accessors to WorkflowSpec
  status: Done
- local_id: ST2
  title: Convert the nine literal call sites and retire the reserved surface
  status: Done
- local_id: ST3
  title: Enforce the roster lifecycle floor at spec load
  status: Done
- local_id: ST4
  title: Guard the no-status-literal rule with a meta scan
  status: Done
- local_id: ST5
  title: Collapse the bundled roster lifecycle to two states
  status: Done
- local_id: ST6
  title: Keep a squad holding the dropped status operable and remappable
  status: Done
created_at: '2026-07-30T07:47:11Z'
updated_at: '2026-07-31T12:41:21Z'
---
<!-- sq:body -->
## Context

`_workflow/_models.py` binds the roster's status names by literal: `STATUS_DRAFT` /
`STATUS_ACTIVE` / `STATUS_ARCHIVED` plus `_RESERVED_FLOOR`, which `WorkflowSpec._validate`
requires every spec to declare. Nine sites consume the literal — the four creates in
`_services/_roster.py` (`activate_role`, `add_dev`, `add_skill`, `add_operator`), the four
skill-seed sites in `_services/_maintenance.py`, and the active tick in `_cli/_role.py:124`.
`WorkflowSpec` exposes no role-keyed status accessor at all, so nothing else can ask "is this
entry live" without naming a status.

ADR-696 §2, §3 and §5. Its §4 (declared-override merge, `override_base`) is deliberately
excluded — that lift reaches every item type's lifecycle and is scheduled as its own feature.

This also carries the vocabulary ruling recorded on FEAT-691: the bundled roster lifecycle
collapses to the live status plus one settled retired status, dropping the unreachable third
state. One correction to the rationale as recorded, established by reading the code rather than
assumed: the drop does **not** require the reserved-floor retirement, because `_RESERVED_FLOOR`
tests membership in the spec's *global* status set and the dropped name stays declared there for
the work and guide lifecycles. The two are grouped here because they edit the same three
surfaces (`_workflow/_models.py`, `_bundled/workflow.toml`, the generated goldens and grammar
tables) and because the floor clauses below are exactly the guardrail the resulting two-state
machine has to satisfy.

## Scope

Two derived accessors on `WorkflowSpec`, computed from `machine_for(item_type).states` and the
existing role resolution — no new stored field, nothing declared twice:

- `role_statuses(item_type, role) -> frozenset[str]` — the read predicate.
- `sole_role_status(item_type, role) -> str` — the write target; raises a clean `SquadsError`
  when there is not exactly one, never an `IndexError`/`StopIteration`.

Convert the nine sites per ADR-696 §2's table: a read becomes `role_statuses(..., "active")`, a
write becomes `sole_role_status(..., "active")`. Retire `STATUS_*` and `_RESERVED_FLOOR` from
`_workflow`'s surface, including `_workflow/__init__`'s re-exports and `__all__`.

The two private `_STATUS_ACTIVE = "Active"` constants in `_migrations/_v0_4_to_v0_5.py` and
`_v0_8_to_v0_10.py` are correct and must not be touched. A runner transforms a corpus written at
a pinned schema version, so it reads that version's vocabulary, never the live spec.

The roster floor at load (ADR-696 §3), for every type declaring `category = "roster"`: exactly
one status whose role is `active`, and at least one settled non-active status reachable from it.
Collected alongside the loader's existing violations — fail-closed for `open_service`, one
finding per violation for `sq workflow lint`.

The lifecycle drop edits the bundled roster machine's `initial` and `transitions` and every
downstream surface that enumerates it: the generated goldens, the lifecycle table in the
cheatsheet partial, `sq workflow statuses` output, and the adopter-facing grammar lines. The
dropped status stays a declared status of the spec (work and guide own it), so nothing about the
global status vocabulary changes.

## Out of scope

The override lift. The backend projection, the config-integrity clauses, and the `sq check`
reporter — each has its own task under this feature. Any change to how a status renders.

## Acceptance

- No bundled roster status name appears as a literal anywhere in `src/squads/` outside
  `_bundled/workflow.toml` and `_migrations/`, proven by a `tests/meta` scan in the shape of the
  existing meta guards.
- `sole_role_status` raises a clean `SquadsError` naming the type and the role for both the zero
  and the many case.
- A spec declaring two live roster statuses, none, or no reachable settled non-live one is
  refused at load with the offending type named; `sq workflow lint` reports every violation at
  once, each with its override path and a fix hint.
- The bundled roster lifecycle has exactly two states, and `sq workflow statuses --json`, the
  cheatsheet's lifecycle row, and the goldens all agree.
- An existing squad holding the dropped status on a roster item stays fully operable — see the
  remap subtask; its two load-path claims must be asserted, not reasoned about.
- `sq check` clean, `sq repair` a no-op, `sq sync` idempotent on a fresh squad after the drop.
- Gate clean: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run
  --all-extras ruff format --check .`. The `--all-extras` is mandatory on each.
- Full suite green, `tests/meta/` included. If this adds a module-level constant, run
  `tests/meta` and allowlist the constant as a CODE constant rather than restructuring the code.
- Falsify each new refusal: break it, watch the test go red, restore it, watch it go green, and
  report both.

## Tests

Service and unit level plus a CLI smoke per surface, named by behaviour. No ticket ID in any file
name, test name, or source comment.

- `tests/unit/test_workflow_reserved_vocab.py` — the reserved surface after the retirement.
- A new `tests/unit/` module for the two accessors, both raising paths included.
- `tests/unit/test_workflow_lint_merge_errors.py` — the floor clauses in collect mode.
- `tests/integration/test_load_boundary_vocab.py` — the fail-closed path at `open_service`.
- `tests/cli/test_workflow_statuses_cli.py` — the two-state roster lifecycle as rendered.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 699 add-subtask "<title>"`; track with `sq task 699 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the role-keyed status accessors to WorkflowSpec

<!-- sq:subtask:ST1:body -->
Two derived accessors on `WorkflowSpec`, computed from `machine_for(item_type).states` and the existing per-status role resolution. No stored field, nothing an adopter declares twice.

`role_statuses(item_type, role) -> frozenset[str]` returns the states of that type's lifecycle whose resolved role is *role* — the read predicate every later caller uses for "is this entry live".

`sole_role_status(item_type, role) -> str` returns the one state with that role and raises a clean `SquadsError` naming the type and the role when there is not exactly one — never an `IndexError` or a bare `StopIteration`. It is the write target for a call site that must *set* a status, and the floor subtask is what makes the answer total for the types that have such call sites.

Done when both accessors exist, are covered for the zero, one and many cases, and no caller has been converted yet.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Convert the nine literal call sites and retire the reserved surface

<!-- sq:subtask:ST2:body -->
Convert the nine sites per ADR-696 §2's table: the four creates in `_services/_roster.py` (`activate_role`, `add_dev`, `add_skill`, `add_operator`), the four skill-seed sites in `_services/_maintenance.py`, and the roster table's active tick in `_cli/_role.py:124`. A read becomes `role_statuses(..., "active")`; a write becomes `sole_role_status(..., "active")`.

Then retire `STATUS_DRAFT`/`STATUS_ACTIVE`/`STATUS_ARCHIVED` and `_RESERVED_FLOOR` from `_workflow`'s surface, including the re-exports and `__all__` in `_workflow/__init__`, and the reserved-status clause in `WorkflowSpec._validate`.

The two private `_STATUS_ACTIVE = "Active"` constants in `_migrations/_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` are correct and must not be touched: a runner transforms a corpus written at a pinned schema version, so it reads that version's vocabulary rather than the live spec. They are already private module constants, not imports of the shared name, so this retirement does not reach them.

Done when the nine sites read through the accessors, the constants are gone from `_workflow`, and behaviour is unchanged for a bundled squad.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Enforce the roster lifecycle floor at spec load

<!-- sq:subtask:ST3:body -->
The additional floor clauses for a lifecycle bound to a `category = "roster"` type, per ADR-696 §3. The universal clauses are already enforced and need no change.

R1 — exactly one status whose role is `active`. Zero means no entry could ever be materialised; more than one leaves the write sites with no unambiguous target. Exactly one is what keeps `sole_role_status` total without storing a second "which one is canonical" field.

R2 — at least one settled status whose role is not `active`, reachable from that live status. The universal floor only requires *some* settled status reachable from `initial`, which a machine could satisfy while never letting a live entry retire.

Both derive from the role assignment the spec already carries; neither adds a field. The floor must not require the role *names* `retired` or `pending` — retirement is consumed through the role object's `settled` flag and default-hiding through `hidden`, and `active` is the only role the engine must name to pick a status. Requiring the other two would trade three reserved status names for two reserved role names.

Wire into the loader's existing two calling modes: raise for `open_service`, one finding per violation with its override path and a fix hint for `sq workflow lint`.

Done when a spec violating either clause is refused at load with the offending type named, and lint reports every violation at once.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Guard the no-status-literal rule with a meta scan

<!-- sq:subtask:ST4:body -->
A `tests/meta` scan keeping the rule true after this lands: no bundled roster status name may appear as a literal in `src/squads/` outside `_bundled/workflow.toml` and `_migrations/`.

Same shape as the existing meta guards (the stray-ticket-reference scan, the module-level mutable-state guard) — a cheap, readable scan over the source tree, not a new framework. Model it on `tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py`.

The two exempt locations are exempt for different reasons and the scan should say so: the bundled TOML is where the vocabulary is legitimately declared, and a migration runner legitimately pins the vocabulary of the version it transforms.

Done when the scan is green on the converted tree and fails when a literal is reintroduced anywhere else.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Collapse the bundled roster lifecycle to two states

<!-- sq:subtask:ST5:body -->
Collapse the bundled `role`/`skill`/`operator` lifecycle to the live status plus one settled retired status, dropping the third, unreachable state. Nothing in the bundled spec ever transitioned into it, every roster-create verb writes the live status directly, and this repository's own squad holds no roster item at it.

Edit the roster machine's `initial` and `transitions` in `_bundled/workflow.toml`. The dropped name stays a declared status of the spec — the work and guide lifecycles own it — so `spec.statuses` is unchanged and only the roster machine narrows.

Then every downstream surface that enumerates the roster lifecycle: the generated goldens, the lifecycle table in the cheatsheet partial, `sq workflow statuses` output, and the adopter-facing grammar lines that spell the three states out. Grammar and table edits only — no new prose sections.

The resulting machine satisfies R1/R2 trivially, which is the reason this rides with the floor rather than landing on its own: the floor is what stops a later spec re-opening the same hole.

Done when the bundled roster lifecycle has exactly two states and every rendered surface agrees.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Keep a squad holding the dropped status operable and remappable

<!-- sq:subtask:ST6:body -->
The dropped status is reachable today through `--force`, so an existing squad may hold a roster item at it. This subtask makes that squad's state visible and fixable in place. Two load-path claims below were established by reading the code, and both must be asserted as tests rather than trusted — if either turns out false, stop and say so before proceeding.

Claim 1: no squad hard-stops. `validate_against_index` checks `item.status not in spec.statuses` — the spec's *global* status set, not the item's own lifecycle — and the dropped name stays declared for work and guide. Separately, both `open_service` and the root CLI callback only run the cross-check when a workflow override file is present. So neither a plain squad nor an overridden one is refused at load for a roster item holding the dropped status.

Claim 2: the remap is reachable. `_apply_status` validates the *target* against the type's states and, with `force=True`, skips the transition-edge check entirely — so `sq <roster-type> <addr> status <live> --force` remaps an item whose current status is no longer declared for its type.

What the affected squad actually sees is one `sq check` error per affected item from the existing `item_status_valid` validator, which reads the type's own machine. Confirm that message is actionable as-is; if it is not, make it name the remap rather than adding a second validator.

No `SCHEMA_VERSION` bump and no `_migrations/_registry.py` entry. Nothing about the frontmatter or index shape changes and the status stays declared vocabulary, so a migration step would be the wrong instrument — migrations are keyed to schema versions and adding one would force a bump on every squad for a vocabulary narrowing. Should the assertions above show a squad in this state has no reachable command, that conclusion is void: raise it rather than working around it, because then a registry entry with a `manual` runbook is the correct answer.

Done when both claims are covered by tests, an affected squad is reported and remappable, and `sq check` is clean again after the remap.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T08:31:15Z] Elias Python:
  - Implemented ST1-ST6: role_statuses/sole_role_status accessors added; nine literal call sites converted; STATUS_DRAFT/STATUS_ACTIVE/STATUS_ARCHIVED/_RESERVED_FLOOR retired; roster lifecycle floor (R1/R2) enforced in _validate; bundled agent lifecycle collapsed to Active/Archived; meta scan added; both ST6 load-path claims asserted as tests and confirmed true (no migration needed).
<!-- sq:discussion:end -->
