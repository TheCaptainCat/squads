---
id: TASK-1230
sequence_id: 1230
type: task
title: Roster commands on operations
status: InProgress
parent: FEAT-1226
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1224:implements
- TASK-1227:depends-on
description: role, skill, operator and dev verbs on one operation each, with --json
  and resolved display names
subentities:
- local_id: ST1
  title: role verbs and the shared roster registrars
  status: Todo
  story: US1
- local_id: ST2
  title: skill verbs
  status: Todo
  story: US1
- local_id: ST3
  title: operator and dev verbs
  status: Todo
  story: US1
- local_id: ST4
  title: Roster display names and columns
  status: Todo
  story: US4
- local_id: ST5
  title: JSON output on the 24 roster keys
  status: Todo
  story: US2
created_at: '2026-10-28T22:12:39Z'
updated_at: '2026-10-28T23:59:04Z'
---
<!-- sq:body -->
## Goal

Move the roster commands onto one operation each (ADR-1224 point 8, increment 3) and give the 24 that lack it `--json`: the `role`, `skill`, `operator` and `dev` groups. Roster lookups, managed-file regeneration and pronoun handling move into the operations, so the roster renderers read neither the role catalog nor `.squads.toml`.

## What it builds

- One operation per command in the roster section of `_api/_ops.py`, bound in `_services/_bindings.py`. Routes per ADR-1225 section 1: `POST /v1/roles`, `GET`/`PATCH`/`DELETE /v1/roles/{addr}`, `PUT …/body`, `POST …/status`, `…/activate`, `…/regen`, `…/set-default`, the views sub-resource, and the same shapes under `/v1/skills/{addr}` and `/v1/operators/{addr}`; `addr` is a slug, an id or a number, resolved by the operation. `dev add`/`dev list` follow the role routes the table assigns them. Timeout class `standard`.
- The roster address callbacks (`_addr` in `_cli/_role.py`, `_skill.py`, `_operator.py`) only parse; `_require_id` and the slug resolution move into the operations (ADR-1224 point 1). The comment verbs on these hosts are TASK-1229's, which takes the parsed `addr` from the start.
- Writes that regenerate managed files (pointers, the `CLAUDE.md`/`AGENTS.md` sections) do so inside the operation (ADR-1224 point 1). `role catalog` keeps working outside a squad through the operation's composition mode (bundled fallback).
- `--file` text (`role add`, `role update`) is read by the CLI and sent as text in the request DTO (ADR-1225 section 2), with today's read-error wording.
- Display (ADR-1224 point 5): role and operator names with pronouns applied or left out according to `[display] pronouns`; `columns` on `role list`, `role catalog`, `operator list`, `dev list` and the skill listings, whose column sets come from the spec today.
- **`--json` on 24 keys** (ADR-1224 point 3a): `role add`, `activate`, `update`, `body`, `status`, `set-default`, `regen`, `remove`, `rm`, `view add`, `view disable`; `skill add`, `update`, `link-role`, `unlink-role`, `ref add`, `ref rm`, `regen`, `view add`, `view disable`; `operator add`, `update`; `dev add`, `dev list`. A write prints the roster row it wrote. `body`, `status` and `remove` come from the shared roster registrars, so `skill` and `operator` get the flag through the same registration; the coverage keys fold those hosts onto `role` (`tests/_cli_surface.py`), so they need no cases of their own.
- **`json_field`** (ADR-1224 points 3 and 4, amended 2026-10-29): `role catalog`, `role list` and `operator list` keep their bare-array `--json` by setting `json_field = "items"`, so their `columns` reach human mode and HTTP only. The 24 new flags, `dev list` included, print `data` whole, an object, and set none.
- DTOs in `_api/_dto/_roles.py`, `_skills.py`, `_operators.py`; renderers in `_cli/_render/_roster.py`. `build_role_json_payload` stops being called here (TASK-1232 deletes it).

## Modules touched

Edited: `_cli/_role.py`, `_cli/_skill.py`, `_cli/_operator.py`, `_cli/_dev.py`, the roster registrars of `_cli/_common.py` (`register_status_verb`, `register_remove_verb`, `register_body_verb`, which only roster hosts use), the roster sections of `_api/_ops.py` and `_services/_bindings.py`, the roster classes of `_services/_results.py`, `tests/cli/test_role.py`, `test_skill.py`, `test_operator.py`, `test_dev.py`. Disjoint from TASK-1228 and TASK-1231, which run beside it.

## Acceptance

- FEAT-1226 US1 for every roster command: one call, a slug not on the roster answered by the operation with today's message, managed files regenerated as today; output, exit codes and error text unchanged.
- FEAT-1226 US2: the 24 flags, each printing the roster row or report the command produces.
- FEAT-1226 US3: `--json` prints `data`, or the field its operation names.
- FEAT-1226 US4: names with pronouns per `[display]`, columns on the roster listings; roster renderers pass the `_cli/_render/` guard.
- ADR-1224 points 1, 3a, 5 and 8 (increment 3); ADR-1225 sections 1 and 2.

## Test approach (ADR-1172)

- Existing surface suite as the proof, including the generated-file reads rule 5 allows for regeneration; only additive `--json` expectation edits.
- New surface cases: 24, one whole-document case per new flag in the group's module, with `covers` markers, each running the smallest write the command accepts.
- Guards: none new; the `_services` pending list loses the four roster modules.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1230 add-subtask "<title>"`; track with `sq task 1230 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — role verbs and the shared roster registrars

<!-- sq:subtask:ST1:body -->
The `role` verbs on one operation each: `catalog`, `list`, `activate`, `add`, `show`, `update`, `body`, `status`, `set-default`, `regen`, `remove`, `rm`, `view add`, `view disable`, under `/v1/roles` and `/v1/roles/{addr}`. The `_addr` callback only parses; `_require_id` and slug resolution move into the operations. Managed-file regeneration runs inside the operation. `role catalog` works outside a squad through the operation's composition mode. `--file` text sent in the request. The shared roster registrars (`register_status_verb`, `register_remove_verb`, `register_body_verb`) move here for all three roster hosts. Existing cases pass.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — skill verbs

<!-- sq:subtask:ST2:body -->
The `skill` verbs on one operation each: `add`, `show`, `update`, `link-role`, `unlink-role`, `refs`, `ref add`, `ref rm`, `regen`, `view add`, `view disable` (body, status and remove through the shared registrars), under `/v1/skills` and `/v1/skills/{addr}`. The `_addr` callback only parses. Pointer regeneration inside the operation. Existing cases pass.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — operator and dev verbs

<!-- sq:subtask:ST3:body -->
The `operator` verbs (`add`, `list`, `show`, `update`, body, status and remove through the shared registrars) under `/v1/operators[/{addr}]`, and `dev add`/`dev list`, on one operation each. The `_addr` callback only parses. Existing cases pass.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Roster display names and columns

<!-- sq:subtask:ST4:body -->
Display for the roster (ADR-1224 point 5): role and operator names with pronouns applied or left out according to `[display] pronouns`; `columns` on `role list`, `role catalog`, `operator list`, `dev list` and the skill listings. The roster renderers in `_cli/_render/_roster.py` read neither the role catalog nor `.squads.toml`, held by TASK-1227's guard and the existing human-output cases.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — JSON output on the 24 roster keys

<!-- sq:subtask:ST5:body -->
`--json` on 24 keys (ADR-1224 point 3a): `role add`, `activate`, `update`, `body`, `status`, `set-default`, `regen`, `remove`, `rm`, `view add`, `view disable`; `skill add`, `update`, `link-role`, `unlink-role`, `ref add`, `ref rm`, `regen`, `view add`, `view disable`; `operator add`, `update`; `dev add`, `dev list`. A write prints the roster row it wrote. Tests: one whole-document case per key with its `covers` marker, smallest write, in `test_role.py`, `test_skill.py`, `test_operator.py`, `test_dev.py`. Falsify each once. 24 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:36:26Z] `tech-lead` Olivia Lead:
  - Roster comment address switch removed from the body and ST3 (now titled operator and dev verbs), since TASK-1229 takes addr from the start (architect 3f2b004 on TASK-1229). Test count unchanged (24).
- [2026-10-28T23:13:22Z] `architect` Robert Architect:
  - @tech-lead ADR-1224 amended 2026-10-29 (comment ad65a70), points 3 and 4. For this task: `role catalog`, `role list` and `operator list` keep their bare-array `--json` by setting the operation's new `json_field` (`items`), so their `columns` reach human mode and HTTP only. The 24 new flags (`dev list` included) print `data` whole, an object, and set none. The US3 acceptance line should read "`data`, or the field its operation names".
- [2026-10-28T23:32:34Z] `tech-lead` Olivia Lead:
  - Body updated per the architect (ADR-1224 amended 2026-10-29): the json_field share for this task and the US3 acceptance line ("data, or the field its operation names"). Test count unchanged.
<!-- sq:discussion:end -->
