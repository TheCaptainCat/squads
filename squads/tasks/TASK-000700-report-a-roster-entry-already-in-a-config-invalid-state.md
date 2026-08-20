---
id: TASK-700
sequence_id: 700
type: task
title: Report a roster entry already in a config-invalid state
status: Done
parent: FEAT-691
author: tech-lead
priority: urgent
refs:
- BUG-698:fixes
- ADR-697:implements
- TASK-699:depends-on
description: A sq check validator for a roster entry sitting in a state the transition
  clauses would refuse
subentities:
- local_id: ST1
  title: Build the config-integrity clause predicates
  status: Done
  story: US6
- local_id: ST2
  title: Register the roster config-integrity validator in the closed catalog
  status: Done
  story: US6
- local_id: ST3
  title: Name the dependants and the implicating types in each finding
  status: Done
  story: US6
- local_id: ST4
  title: Cover the reporter against the recorded repro
  status: Done
  story: US6
created_at: '2026-07-30T07:47:16Z'
updated_at: '2026-07-31T12:41:23Z'
---
<!-- sq:body -->
## Context

BUG-698's reporter half, and the urgent one: the roster status verb ships without its guards, so
a squad can already be sitting in the state the transition-time clauses exist to prevent. Those
clauses gate transitions and cannot see existing state, so a squad transitioned before they land
keeps the invalid state and `sq sync`'s convergence sweep faithfully projects the breakage. Per
ADR-697's consequences this needs a report-mode validator, not a gate, and it can land
independently of the gate.

The clause definitions are shared with the gate. This task **owns** them: build C1-C3 as pure
predicates over an already-loaded snapshot, and consume them here from a `sq check` validator.
The gate task then calls the same predicates from the transition's pure half. Two copies of this
logic is the failure mode to avoid.

## Scope

A clause module of pure functions taking the loaded index snapshot, the active spec and the
active backend list, returning zero or more findings, each naming the entry and its dependants:

- **C1 — last live role.** No entry of the `role` type resolves to the live role while at least
  one backend is active.
- **C2 — default role.** The entry carrying `is_default` is not live, and no live role carries it.
- **C3 — depended-on skill.** A non-live skill is still named by a live role's resolved preload
  list, whether by a stored `scopes` edge, by system membership, or by a declared item type's
  `sq-<type>` implication.

Liveness is `role_statuses(item_type, "active")` from the foundation task — never a status
literal, and never a per-entry stored flag. The tier-3 floor is the property "whatever
`skills_for_role` implies for every role", derived from the resolver, never a blocklist of skill
names.

C3's live-role set is computed inside the clause module by filtering role items on that
predicate. Do not reach for `Service.roster()`: its active-only semantics land in the projection
task and this module must be correct both before and after that change.

Registering the validator: the name goes in the closed registry in `_workflow/_models.py` and the
implementation in `_services/_validators.py`, where the import-time assert keeps catalog and names
in lockstep. C1 needs `paths.config.active_backends`, which `ValidatorContext` does not carry and
`SquadGlobalContext` does — a squad-global validator is the seam that fits without widening the
per-item context. It reads the index and the config only, never the on-disk scan, so it carries
none of the cross-source single-item-evaluability obligation stated on `SquadGlobalValidator`.

Each finding names the same specifics a refusal would: the dependent entity or entities, and for
a `sq-<type>` implication the implicating type or types, capped and summarised the way a
collected conflict report caps its tail. State the mechanism, never a recommendation to drop a
live type. Findings surface through `sq check`'s existing collected report — one line per issue,
the existing severity and exit-code convention, not a separate command.

## Out of scope

Refusing anything. No transition gate, no `--unlink`, no change to `sq check`'s present-only
backend reconciliation, and no currency check for the projection (ADR-697 §6).

## Acceptance

- Each of C1, C2 and C3 is reported by `sq check` for a squad currently in that state, one line
  per issue, at the severity its exit-code convention implies.
- Verified against the repro recorded on BUG-698: a fresh squad where the always-on skill was
  retired while the guard did not exist is caught afterwards.
- With `active_backends` empty, C1 reports nothing — the sq-only squad stays blessed (ADR-141).
- A C3 finding on a type-implied skill names the implicating type; a widely-implicated skill
  produces a capped, summarised tail rather than an unbounded list.
- A clean squad produces no new findings, and `sq check` stays clean on this repository.
- The clause predicates are callable against a snapshot with no I/O, so the gate task can reuse
  them unchanged.
- Gate clean with `--all-extras` on each of pyright, `ruff check .` and `ruff format --check .`.
- Full suite green. A new module-level constant means running `tests/meta` and allowlisting it as
  a CODE constant rather than restructuring the code.
- Falsify: break each clause, watch its test go red, restore it, watch it go green, report both.

## Tests

Service level plus a CLI smoke, named by behaviour. No ticket ID in any file name, test name, or
source comment.

- Service — a new `tests/service/` module following its neighbours' naming
  (`test_check_flags_unregistered_participant.py` is the shape): one case per clause, plus the
  empty-`active_backends` case and a clean-squad negative.
- CLI smoke — a new `tests/cli/` module, or an extension of
  `tests/cli/test_check_deterministic_sort_order.py` if the finding text belongs in its ordering
  assertions: the finding renders through `sq check` with the right exit code and names the
  dependants.
- Unit — the clause predicates directly against a hand-built snapshot, including the
  tier-classification of a C3 dependant.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 700 add-subtask "<title>"`; track with `sq task 700 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Build the config-integrity clause predicates | US6 |
| ST2 | Done |  | Register the roster config-integrity validator in the closed catalog | US6 |
| ST3 | Done |  | Name the dependants and the implicating types in each finding | US6 |
| ST4 | Done |  | Cover the reporter against the recorded repro | US6 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Build the config-integrity clause predicates

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US6 — As a team, sq check reports a roster entry already in a broken config state
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
C1, C2 and C3 as pure functions over an already-loaded index snapshot plus the active spec and the active backend list — no I/O, so the gate task can call the identical predicates from the transition's pure half. This is the shared definition; nothing else may restate it.

C1: no entry of the `role` type resolves to the live role while at least one backend is active. With `active_backends` empty there is no generated config to break, so the clause is silent — ADR-141 blessed the sq-only squad and this must not quietly un-bless it.

C2: the entry carrying `is_default` is not live and no live role carries it. The Claude backend picks the default from the roster and falls back to a hardcoded slug when it finds none, which would put a slug in the managed region that need not exist.

C3: a non-live skill is still named by a live role's resolved preload list — by a stored `scopes` edge, by system membership, or by a declared item type's `sq-<type>` implication.

Liveness is `role_statuses(item_type, "active")`, never a status literal and never a per-entry stored flag: "required" is a property of what the generated config needs, not of the entry, and no per-entry flag can express C1's last-live-role case at all. The tier-3 floor is the property "whatever `skills_for_role` implies for every role", read off the resolver — not a blocklist of skill names, which would pin the floor to three literals and be free to disagree with the derivation.

Compute C3's live-role set inside this module by filtering role items on the liveness predicate. Do not reach for `Service.roster()`: its active-only semantics land in the projection task, and these predicates must be correct both before and after that change.

Each clause additionally declares the set of ref kinds whose stored edges constitute the dependency it detects — `scopes` for C3's tier 1, empty for C1 and C2. The gate task consumes that declaration; declaring it here keeps the data next to the detection it describes.

Done when each clause is callable against a hand-built snapshot and returns findings carrying the entry plus its dependants.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Register the roster config-integrity validator in the closed catalog

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US6 — As a team, sq check reports a roster entry already in a broken config state
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Register one report-mode validator that runs the clauses and emits their findings through `sq check`'s existing collected report — one line per issue, the existing severity and exit-code convention, not a separate command.

The name belongs in the closed registry in `_workflow/_models.py`; the implementation belongs in `_services/_validators.py`, where the import-time assert keeps the catalog and the declared names in lockstep. Adding to one without the other fails at import, which is the intended guardrail.

C1 needs `paths.config.active_backends`. `ValidatorContext` does not carry paths and `SquadGlobalContext` does, so a squad-global validator is the seam that fits without widening the per-item context for one clause. It reads the index and the config only — never the on-disk scan — so it carries none of the cross-source single-item-evaluability obligation stated on `SquadGlobalValidator`, and needs no counterpart in `check`'s confirm pass.

This is a state-validity question about an item's own status, which is what the report-mode plane is for. It is explicitly not the currency check ADR-697 §6 declined: do not probe per-entry backend files and do not touch the present-only backend reconciliation.

Done when `sq check` reports the clauses on an affected squad and stays silent on a clean one.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Name the dependants and the implicating types in each finding

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US6 — As a team, sq check reports a roster entry already in a broken config state
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Each finding names the same specifics a transition-time refusal would, because an operator reading it has to be able to act on it: the dependent entity or entities, and where the dependency is a `sq-<type>` implication, the implicating type or types.

State the mechanism, never a recommendation. "This skill is implied by declared type X" is a fact; "drop X to retire this skill" is advice, and it is usually terrible advice — a live work type with items under it is not something to drop so one skill can retire. The wording must not nudge toward it.

Bound the enumeration. A widely-mapped skill can implicate many types, so cap and summarise the tail the way a collected conflict report does rather than printing an unbounded list.

For a tier-3 dependant, state the floor in one line as the property that defines it and offer no remedy, because none exists. Offering one would be a lie.

Done when each finding is specific enough to act on and no finding recommends dropping a live type.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Cover the reporter against the recorded repro

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US6 — As a team, sq check reports a roster entry already in a broken config state
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Two homes, tests named by behaviour, no ticket ID in any file name, test name or source comment.

Service level — a new module named for what it asserts, following its neighbours (`tests/service/test_check_flags_unregistered_participant.py` is the shape): one case per clause, the empty-`active_backends` case where C1 stays silent, and a clean-squad negative proving no new noise.

CLI smoke — the finding renders through `sq check` with the right exit code and names the dependants. A new module under `tests/cli/`, unless the finding text belongs in `tests/cli/test_check_deterministic_sort_order.py`'s ordering assertions, in which case extend that.

Unit — the clause predicates directly against a hand-built snapshot, including the tier classification of a C3 dependant.

The specific case to reproduce is the one recorded on BUG-698: a fresh squad where the always-on skill was retired while nothing refused it. That squad must be caught by the validator afterwards.

Falsify each clause: break it, watch its test go red, restore it, watch it go green, and report both.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T10:09:06Z] Olivia Lead:
  - ADR-696 was amended after this task was cut, and the amendment changes vocabulary this body names. Body left as written; read this comment alongside it. TASK-703 carries the reshape and blocks this task.
  - Liveness is no longer `role_statuses(item_type, "active")` — the two places this body says that (the overview and ST-level restatement) should be read as the offered-statuses predicate on the spec. The materialisation axis is now an `offered` boolean on the status-role object, defaulting false; it is not keyed off the role name `active`, and no role-name-keyed status accessor survives TASK-703.
  - Where this body says "live role" / "live status" (C1's last-live-role clause, C2's default-role clause, C3's live-role preload set), read "offered". The clauses themselves are unchanged in substance — C1 still counts entries of the role type that are on offer, C2 still asks whether the default designation sits on one, C3 still asks whether an unoffered skill is named by an offered role's resolved preloads.
  - One knock-on worth knowing before implementing: R1 relaxes to "at least one offered status", so a project may declare several. "This entry is on offer" no longer implies a single status, which means C1's cardinality check must count entries whose status is in the offered set rather than comparing against one status name.
  - @python-dev do not start this until TASK-703 lands; the accessors this body names will not exist.
- [2026-07-30T12:56:57Z] Elias Python:
  - Implemented: squads/_services/_config_integrity.py (pure C1/C2/C3 predicates, filtering offered roles/skills from the index snapshot directly, no Service.roster() call) + a new roster_config_integrity squad-global validator wired into _workflow/_models.py's VALIDATOR names and _services/_validators.py's SQUAD_GLOBAL_CATALOG.
  - Vocabulary followed the amendment, not the body: offered_statuses/offered_initial membership throughout, R1's relaxation honored (C1 tests membership in the offered set, not equality) — covered by a dedicated two-offered-statuses test.
  - active_backends sourced from SquadGlobalContext.paths.config.active_backends, per the breakdown; C1 silent when empty (ADR-141 sq-only squad), confirmed by tests.
  - Tests: tests/unit/test_roster_config_integrity_predicates.py (16, pure predicates incl. BUG-698 tier-3 shape, tier-1/tier-2 classification, cap-and-summarise), tests/service/... (7, incl. the recorded repro + active_backends=[] + two-offered-statuses negative), tests/cli/... (3, exit code + dependant naming). All three clauses individually falsified (broke -> red -> restored -> green) at unit/service/CLI layers.
  - sq check stays clean on this repo (all roster entries offered).
  - pyright/ruff check/ruff format all clean with --all-extras; tests/meta green (had to scrub ADR/TASK/BUG/§N references I'd put in docstrings — the ticket-hygiene scan flags those in src/ and in test docstrings/filenames).
<!-- sq:discussion:end -->
