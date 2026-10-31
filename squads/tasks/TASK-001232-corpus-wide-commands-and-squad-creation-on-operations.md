---
id: TASK-1232
sequence_id: 1232
type: task
title: Corpus-wide commands and squad creation on operations
status: Done
parent: FEAT-1226
author: tech-lead
assignee: python-dev
refs:
- ADR-1224:implements
- TASK-1228:depends-on
- TASK-1229:depends-on
- TASK-1230:depends-on
- TASK-1231:depends-on
description: repair, renumber, migrate, import, init and adopt on operations with
  --json; get_service and the CLI-side JSON builders deleted
subentities:
- local_id: ST1
  title: repair, renumber and the migrate operations
  status: Done
  maps_to: US1
- local_id: ST2
  title: import
  status: Done
  maps_to: US1
- local_id: ST3
  title: init and adopt, local only
  status: Done
  maps_to: US1
- local_id: ST4
  title: Delete get_service, CLI gates and JSON builders
  status: Done
  maps_to: US3
- local_id: ST5
  title: JSON output on the 8 corpus and creation keys
  status: Done
  maps_to: US2
created_at: '2026-10-28T22:12:41Z'
updated_at: '2026-10-29T10:14:55Z'
priority: high
---
<!-- sq:body -->
## Goal

Move the corpus-wide commands and squad creation onto operations (ADR-1224 point 8, increment 5) and give the 8 that lack it `--json`: `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `import`, `init` and `adopt`. Then remove what no command needs any more: the `_services` pending list empties, and `get_service`, its memo on the Click root, the double bridge crossing, the CLI-side gates and the CLI-side JSON builders are deleted. After this task the CLI imports `_services` in exactly one function.

## What it builds

- One operation per command in the corpus-wide section of `_api/_ops.py`, bound in `_services/_bindings.py`. Routes `POST /v1/squad/repair`, `…/renumber`, `…/migrate`, `…/repad`, `…/rename-type`, `…/rename-status`, `…/import` (ADR-1225 section 1). Timeout class `long` for all seven (ADR-1225 section 3, "Timeouts"); `migrate` composition mode and `grant` on each (ADR-1224 point 4), replacing the `Ground`/`past_the_gate` declarations in `_cli/_migrate.py` and `_cli/_main.py`.
- `init` and `adopt` are operations with `local_only` true: they create the squad a daemon is keyed on and never go through a daemon. `init --json` asks for no role names and keeps the defaults, as `--default-names` does (ADR-1224 point 3a). The role-name prompt of `init` sits before the call.
- `import` reads its file (or `-`) in the CLI and sends the text in the request DTO (ADR-1225 section 2); its report carries the findings that give exit 3.
- **`--json` on 8 keys** (ADR-1224 point 3a): `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `init`, `adopt`. Each prints its report.
- **Removal sweep** (ADR-1224 point 4 and point 8): the pending list of the `_services` import guard is empty and removed; `get_service`, `get_service_bypassing_index_cross_check`, the root-context memo and the second bridge crossing go; the root callback's schema gate (`require_current_schema`, `apply_gate`) gives way to each operation's `grant`; the grant guard reads the operation table only; the CLI-side JSON builders (`build_item_json`, `build_item_row_json`, `build_subentity_json`, `build_role_json_payload`, `_view_json_payload` and any left) and every `_cli/_common.py` helper the earlier tasks left without a caller are deleted; `Service` parameters disappear from `_cli`. Also deleted: `_VERBS_ON_OPERATIONS` in `_cli/_items.py` and the `_resolve_in_store` branch of the item group callback, so the callback only parses (ADR-1224 point 1); and, once the CLI gates are gone, the bridge copy of the gate, so one remains: `Ground`/`Grant` in `_api/_api.py` and `check_grant` in `_services/_local_api.py` against `_cli/_common.py`'s `Ground`, `GateGrant` and `apply_gate`, and `_api.Mode` against `_services._service.Mode`, which ends with only `_api.Mode` visible outside `_service.py`, `ServiceMode` private there (REV-1235 F10, F16 ruling). Keep the operation-side gate and drop the CLI one; the refusal texts stay today's. Also removed, the duplicates and dead helpers the earlier command-group moves left for this sweep: `_DUPLICATE_READ_NOTE` defined in both `_services/_roster_ops.py` and `_services/_item_ops.py` (keep the `_item_ops.py` one, which `RosterOpsMixin` inherits), `_print_body` in both `_cli/_render/_roster.py` and `_cli/_render/_items.py` (keep one, shared), the stale registrar names in `tests/_cli_surface.py` lines 36-37 (now `register_write_verbs` and `register_roster_status_verb` in `_cli/_roster.py`) (REV-1235 F26 items 2-3), and the `_cli/_common.py` helpers left without a caller (`register_status_verb`, `register_remove_verb`, `register_body_verb`, `named_markup`, `origin_json`, `get_squad_paths`).
- **Response warnings in `--json` mode** (REV-1235 F11). Today the root callback prints the working-language notice on stderr for every command, `--json` included; once it stops, the notice reaches a command only as a response `warnings` entry, which `--json` mode does not print. Decision: in `--json` mode the CLI prints the response's `warnings` on stderr, one line each, as human mode does, so stdout stays one JSON document; this matches how `omitted` already goes to stderr in `--json` mode. The change is in the one call helper every command uses, so every moved command gets it.
- DTOs in `_api/_dto/_squad.py`; renderers in `_cli/_render/_squad.py`.

## Modules touched

Edited: `_cli/_main.py` (`repair`, `renumber`, `init`, `adopt`), `_cli/_migrate.py`, `_cli/_import.py`, `_cli/_common.py` (the deletions), `_cli/__init__.py` (root callback), the corpus-wide section of `_api/_ops.py` and `_services/_bindings.py`, `_services/_results.py` (what is left), `tests/meta/` (the `_services` guard without pending list, the grant guard, the import-edge table, the mutable-state inventory), `tests/cli/test_repair.py`, `test_renumber.py`, `test_migrate.py`, `test_import.py`, `test_init.py`, `test_adopt.py`. Depends on TASK-1228, TASK-1229, TASK-1230 and TASK-1231, because the deletions need every caller gone. Runs beside TASK-1233, which touches only `_tui/` and `_cli/_ui.py`.

## Acceptance

- FEAT-1226 US1 for every command listed: one call (`init`/`adopt` local only), exit 3 on import findings, the schema hard stop with today's text, output and error text unchanged.
- FEAT-1226 US2: the 8 flags print their report; `init --json` never prompts.
- FEAT-1226 US3: no CLI-side JSON assembly is left anywhere; every `--json` prints `data`, or the field its operation names. None of this task's operations sets `json_field`.
- ADR-1224 points 2, 3a, 4 and 8 (increment 5): no `_cli` module other than the `LocalApi` factory imports `squads._services`, guard green with no pending list.

## Test approach (ADR-1172)

- Existing surface suite as the proof, including the arranged-corpus cases rule 5 allows for `repair`, `migrate`, `adopt` and `renumber`; only additive `--json` expectation edits.
- New surface cases: 9. One whole-document case per new flag with its `covers` marker (8); the `init --json` case asserts that no prompt reaches stdout. One case for the `--json` warnings: `show --json` on a squad with an unrecognised `working_language` prints the notice on stderr and only the document on stdout (1).
- Guards: the `_services` guard loses its pending list; the grant guard reads the table only.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1232 add-subtask "<title>"`; track with `sq task 1232 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — repair, renumber and the migrate operations

<!-- sq:subtask:ST1:body -->
`repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status` on one operation each under `/v1/squad/`, timeout class `long`, with their composition mode and `grant` on the operation, replacing the `Ground`/`past_the_gate` declarations. Existing cases pass, including the arranged-corpus cases ADR-1172 rule 5 allows.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — import

<!-- sq:subtask:ST2:body -->
`import` on one operation (`POST /v1/squad/import`, timeout `long`): the CLI reads the import file or `-` and sends its text in the request DTO; the report gives exit 3 on findings. Its existing `--json` keeps printing the report. Existing cases pass.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — init and adopt, local only

<!-- sq:subtask:ST3:body -->
`init` and `adopt` as `local_only` operations: they create the squad a daemon is keyed on and never go through one. `init`'s role-name prompt sits before the call; `init --json` asks for no role names and keeps the defaults, as `--default-names` does. Existing cases pass, including the generated agent-file reads ADR-1172 rule 5 allows.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Delete get_service, CLI gates and JSON builders

<!-- sq:subtask:ST4:body -->
The removal sweep (ADR-1224 points 4, 8): the `_services` guard's pending list is empty and removed; `get_service`, `get_service_bypassing_index_cross_check`, the root-context memo and the second bridge crossing are deleted; the root callback's schema gate (`require_current_schema`, `apply_gate`) gives way to each operation's `grant`, and the grant guard reads the operation table only; the CLI-side JSON builders (`build_item_json`, `build_item_row_json`, `build_subentity_json`, `build_role_json_payload`, `_view_json_payload` and any left) and every `_cli/_common.py` helper left without a caller are deleted; no `_cli` function takes a `Service`. Also deleted (REV-1235 F10): `_VERBS_ON_OPERATIONS` and the `_resolve_in_store` branch of the item group callback in `_cli/_items.py`, so the callback only parses; and the bridge copy of the schema gate, keeping the operation-side one (`Ground`/`Grant` in `_api/_api.py`, `check_grant` in `_services/_local_api.py`) and dropping `_cli/_common.py`'s `Ground`, `GateGrant` and `apply_gate`, with only `_api.Mode` visible outside `_services/_service.py`, where `ServiceMode` stays private as the document choices the fallback tables step through (REV-1235 F16 ruling, ADR-1224 point 4); refusal texts unchanged. Also removed, the duplicates and dead helpers the earlier command-group moves left for this sweep: `_DUPLICATE_READ_NOTE` defined in both `_services/_roster_ops.py` and `_services/_item_ops.py` (keep the `_item_ops.py` one, which `RosterOpsMixin` inherits), `_print_body` in both `_cli/_render/_roster.py` and `_cli/_render/_items.py` (keep one, shared), the stale registrar names in `tests/_cli_surface.py` lines 36-37 (now `register_write_verbs` and `register_roster_status_verb` in `_cli/_roster.py`) (REV-1235 F26 items 2-3), and the `_cli/_common.py` helpers left without a caller (`register_status_verb`, `register_remove_verb`, `register_body_verb`, `named_markup`, `origin_json`, `get_squad_paths`). Afterwards, `uv run vulture` on `_cli/` shows no new dead code. Held by the guards and the whole surface suite.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — JSON output on the 8 corpus and creation keys

<!-- sq:subtask:ST5:body -->
`--json` on 8 keys (ADR-1224 point 3a): `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `init`, `adopt`, each printing its report. Tests: one whole-document case per key with its `covers` marker; the `init --json` case also asserts no prompt reaches stdout. In `--json` mode the CLI prints the response's `warnings` on stderr, one line each, as human mode does and as `omitted` already goes, so the working-language notice survives the root callback no longer printing it (REV-1235 F11); one case: `show --json` on a squad with an unrecognised `working_language` prints the notice on stderr and only the document on stdout. Falsify each once. 9 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:32:38Z] `tech-lead` Olivia Lead:
  - Body, ST4 and ST5 updated for REV-1235: F10 adds _VERBS_ON_OPERATIONS, the _resolve_in_store branch and the bridge gate copy to the deletions; F11 prints response warnings on stderr in --json mode. New cases 8 -> 9. The US3 line reads "data, or the field its operation names".
- [2026-10-29T01:29:55Z] `tech-lead` Olivia Lead:
  - ST4 updated: Mode per the REV-1235 F16 ruling (only _api.Mode visible outside _service.py); added the roster duplicate-id note, the roster body renderer copy and the dead _common.py helpers from the TASK-1230/1231 handbacks. Test count unchanged (9).
- [2026-10-29T06:16:36Z] `python-dev` Elias Python:
  - - Done in b6c623f3 (branch worktree-agent-a232e83de3106c3f0, rebased on release/0.18 678b063d, after TASK-1233). Task left InProgress for review.
    - `repair`, `renumber`, `migrate up`/`repad`/`rename-type`/`rename-status` and `import` are one operation each under `/v1/squad/` (timeout `long`), in `_services/_corpus_ops.py`. `init` and `adopt` are `local_only` operations: a second binding table (`LOCAL_BINDINGS`) holds them, and `LocalApi` runs them without a service, after the grant check when a squad already resolves. `--json` on the 8 keys prints the report. `init --json` asks for no role names.
    - Modes: `INDEX_CHECK_SKIPPED` (repair) and `MIGRATE` (migrate up) are ladders in `_service.py` beside the fallback tables: normal first, then the rungs in order. `Documents` stays private there, and `compose_first_of` is now private too.
    - Deleted: `get_service`, `get_service_bypassing_index_cross_check`, the memo, `command`, `require_current_schema`, `apply_gate`, `Ground`/`GateGrant`/`past_the_gate`, the root callback's notice, every `_common.py` builder and printer left without a caller (vulture is clean on `_cli/`), the second `_print_body` (now `print_body` in `_render/_style.py`) and the roster copy of the duplicate-id note. `_VERBS_ON_OPERATIONS`, `_resolve_in_store`, the `register_*` helpers and the `tests/_cli_surface.py` names were already gone. The import guard has no pending list.
    - Warnings: in `--json` mode `print_json` prints the response's warnings on stderr. Human mode prints them per command as before, so the order of roster write notices is unchanged.
    - Parity: 83 command lines on scratch squads, baseline 62022d8e against this commit (piped, `FORCE_COLOR`, exit codes), with the squad tree hashed after each of 27 sequences. The 15 new `--json` lines were checked by hand. Output, exit codes and all 27 trees are identical, except four expected cases. The working-language notice no longer prints before an exit-2 vocabulary refusal, nor on `docs` and `migrate help`, which make no call.
    - Behind squad: a command run with missing arguments now answers with its exit-2 usage error before the schema gate. `docs` now runs. Every full command line is refused as before.
    - Gates: pyright 0 errors, ruff check and format clean, `pytest -n 2 tests/meta tests/cli tests/check` 1642 passed. That is +9 cases and -1 guard test (the pending list). All 9 cases and the reshaped guards were falsified.
    - @tech-lead for review. @tech-writer, adopter-visible: `--json` on the 8 keys; `--json` prints notices on stderr; usage errors before the schema gate; `docs` runs on a mismatched squad. CLAUDE.md (lines 27, 248) and docs/internals.md (463, 475) still name `get_service`/`require_current_schema`.
- [2026-10-29T07:02:14Z] `python-dev` Elias Python:
  - Round 2 in 6d1facf3 on release/0.18 e0a97f6d: REV-1235 F46-F51 fixed and marked; F48 asks @architect whether the HTTP error envelope should carry warnings. Gates green; +2 guard tests, CLI case count unchanged.
- [2026-10-29T07:18:58Z] `python-dev` Elias Python:
  - Round 3 in 95083231: F47 guard derives writers from the source; F46 and F48 pinned by surface cases; all falsified, gates green.
- [2026-10-29T10:14:55Z] `manager` Catherine Manager:
  - Done: all subtasks Done; REV-1235 F46, F47, F48, F52 and F53 verified across five rounds (head e64ef26f, suite 1650 passed, pyright 0). The write guard's remaining limits (writers passed as values, renamed io.open, importlib/getattr/exec, shutil read helpers counted as writes) are recorded on F53.
<!-- sq:discussion:end -->
