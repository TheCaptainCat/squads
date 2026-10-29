---
id: TASK-1230
sequence_id: 1230
type: task
title: Roster commands on operations
status: Done
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
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: skill verbs
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST3
  title: operator and dev verbs
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST4
  title: Roster display names and columns
  status: Done
  assignee: python-dev
  story: US4
- local_id: ST5
  title: JSON output on the 24 roster keys
  status: Done
  assignee: python-dev
  story: US2
created_at: '2026-10-28T22:12:39Z'
updated_at: '2026-10-29T05:27:32Z'
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
- [2026-10-29T00:35:40Z] `python-dev` Elias Python:
  - - Roster commands on operations, commit 5f156cc1 on branch worktree-agent-adac611660ae546f2 (base 77fac31d). 35 operations in the roster section of `_api/_ops.py`, bound in `_services/_bindings.py` to `RosterOpsMixin` (`_services/_roster_ops.py`, projections in `_services/_roster_dto.py`); DTOs in `_api/_dto/_roles.py`, `_skills.py`, `_operators.py` plus `_roster.py` for the shared address and requests; renderers in `_cli/_render/_roster.py`; shared verbs (body, remove/rm, status) and the address parse in `_cli/_roster.py`.
    - Routes: `/v1/roles[/{addr}]`, `/v1/skills[/{addr}]`, `/v1/operators[/{addr}]` with `…/body` (PUT), `…/status`, `…/regen`, `…/set-default`, `…/link-role`, `…/unlink-role` (POST), `…/views` and `…/views/{name}/disable`, `…/refs[/{target}]`; `GET /v1/roles/catalog` and `POST /v1/roles/activate` (literals under `/v1/roles/` only for `sq role` group verbs, which no role can be addressed by); `dev add` is `roles.activate`; `dev list` is `GET /v1/developers`, outside `/v1/roles/` so it shadows no addressable slug.
    - `--json` on the 24 keys; `role catalog`, `role list`, `operator list` keep their bare arrays through `json_field="items"`. Display: `display` appended to role/operator/developer rows (name with pronouns per `[display] pronouns`, the shown pronouns, `live` on roles) and to the three shows (body with view tags expanded, empty-body hints, change hint, discussion); `columns` on role catalog, role list, operator list and dev list. Skills have no listing table, so no skill `columns`.
    - Proof: scratch squad (core roles, a role override, a self-defined role from a file, dev roles, an archived dev, operators with and without pronouns, an archived operator, comments, `[display] pronouns` both ways, styled and piped, outside a squad), 276 command lines before/after: 234 byte-identical, 33 JSON documents differ only by appended keys (old keys in order, values equal), 2 differ (below), 1 differs by the capture directory name only. The generated tree after all writes (CLAUDE.md, AGENTS.md, `.claude/`, every item file and the index) is byte-identical (`diff -r` empty).
    - Tests: +24 surface cases (one per new key, whole document compared as text). Existing expectations edited, keys added only: role list --json, role add's show --json (display, body as ANY), skill add's show --json, operator add's list, operator list --json, operator show --json. Bare-key markers dropped where the key gained `--json` and so stopped being a parameterless leaf: three `covers("dev list")`, two `covers("role regen")`, two `covers("skill regen")`. Guards: `json_field` allow-list gains the three roster arrays (one line each); edge table gains `_roles -> _api top` and loses `_cli -> _views top`; the roster body guard now checks `register_write_verbs` and the one `set_body` in `_roster_ops.py`.
    - Deviations: (1) `role catalog` outside a squad: no operation can compose a service without one, so the CLI answers `NotInitializedError` with the packaged catalog built by `_roles/_listing.bundled_catalog()` (package data, as ADR-1224 3a does for `docs`), not through a composition mode. (2) Parse refusals now come before address resolution: `sq skill nobody status` exits 2 (missing STATUS) instead of 1 (unknown skill); likewise a `--file` read error or a bad `--can-spawn` now precedes an address or actor error. (3) The comment verbs (TASK-1229's) still need a resolved id: the `_addr` callback only parses, except when the verb is `comment`/`comments`, where it resolves through the old path as before; TASK-1229 removes that branch. (4) The comment and body rendering helpers are copied into the roster renderer rather than shared with `_render/_items.py`, to keep the parallel tasks off each other's modules; worth folding together in TASK-1232. (5) Role shows now read the body and discussion in `--json` mode too, so a role whose item file is missing fails `show --json` where it used to print.
    - Gates: pyright 0 errors, ruff check and format clean, `pytest -n 2 tests/meta tests/cli tests/check` 1596 passed (+25: 24 cases, 1 guard test). Falsified: dropping one key from each roster DTO turns all 24 cases red; a second `set_body` call in the roster operations turns the body guard red.
    - Dead in `_cli/_common.py` for TASK-1232: `register_status_verb`, `register_remove_verb`, `register_body_verb`, `named_markup`, `origin_json`.
    - Adopter-visible, for @tech-writer: `--json` on the 24 roster keys; `display` on role list, operator list and role/skill/operator show documents; `dev list --json` prints an object (`items`, `columns`, `template_available`).
- [2026-10-29T05:27:32Z] `manager` Catherine Manager:
  - Done 2026-10-29: its REV-1235 findings are Verified or deferred with a home; full suite 1634 passed on ed499a68.
<!-- sq:discussion:end -->
