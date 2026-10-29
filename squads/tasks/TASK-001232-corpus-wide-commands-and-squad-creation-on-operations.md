---
id: TASK-1232
sequence_id: 1232
type: task
title: Corpus-wide commands and squad creation on operations
status: Ready
parent: FEAT-1226
author: tech-lead
priority: high
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
  status: Todo
  story: US1
- local_id: ST2
  title: import
  status: Todo
  story: US1
- local_id: ST3
  title: init and adopt, local only
  status: Todo
  story: US1
- local_id: ST4
  title: Delete get_service, CLI gates and JSON builders
  status: Todo
  story: US3
- local_id: ST5
  title: JSON output on the 8 corpus and creation keys
  status: Todo
  story: US2
created_at: '2026-10-28T22:12:41Z'
updated_at: '2026-10-28T22:28:28Z'
---
<!-- sq:body -->
## Goal

Move the corpus-wide commands and squad creation onto operations (ADR-1224 point 8, increment 5) and give the 8 that lack it `--json`: `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `import`, `init` and `adopt`. Then remove what no command needs any more: the `_services` pending list empties, and `get_service`, its memo on the Click root, the double bridge crossing, the CLI-side gates and the CLI-side JSON builders are deleted. After this task the CLI imports `_services` in exactly one function.

## What it builds

- One operation per command in the corpus-wide section of `_api/_ops.py`, bound in `_services/_bindings.py`. Routes `POST /v1/squad/repair`, `…/renumber`, `…/migrate`, `…/repad`, `…/rename-type`, `…/rename-status`, `…/import` (ADR-1225 section 1). Timeout class `long` for all seven (ADR-1225 section 3, "Timeouts"); `migrate` composition mode and `grant` on each (ADR-1224 point 4), replacing the `Ground`/`past_the_gate` declarations in `_cli/_migrate.py` and `_cli/_main.py`.
- `init` and `adopt` are operations with `local_only` true: they create the squad a daemon is keyed on and never go through a daemon. `init --json` asks for no role names and keeps the defaults, as `--default-names` does (ADR-1224 point 3a). The role-name prompt of `init` sits before the call.
- `import` reads its file (or `-`) in the CLI and sends the text in the request DTO (ADR-1225 section 2); its report carries the findings that give exit 3.
- **`--json` on 8 keys** (ADR-1224 point 3a): `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `init`, `adopt`. Each prints its report.
- **Removal sweep** (ADR-1224 point 4 and point 8): the pending list of the `_services` import guard is empty and removed; `get_service`, `get_service_bypassing_index_cross_check`, the root-context memo and the second bridge crossing go; the root callback's schema gate (`require_current_schema`, `apply_gate`) gives way to each operation's `grant`; the grant guard reads the operation table only; the CLI-side JSON builders (`build_item_json`, `build_item_row_json`, `build_subentity_json`, `build_role_json_payload`, `_view_json_payload` and any left) and every `_cli/_common.py` helper the earlier tasks left without a caller are deleted; `Service` parameters disappear from `_cli`.
- DTOs in `_api/_dto/_squad.py`; renderers in `_cli/_render/_squad.py`.

## Modules touched

Edited: `_cli/_main.py` (`repair`, `renumber`, `init`, `adopt`), `_cli/_migrate.py`, `_cli/_import.py`, `_cli/_common.py` (the deletions), `_cli/__init__.py` (root callback), the corpus-wide section of `_api/_ops.py` and `_services/_bindings.py`, `_services/_results.py` (what is left), `tests/meta/` (the `_services` guard without pending list, the grant guard, the import-edge table, the mutable-state inventory), `tests/cli/test_repair.py`, `test_renumber.py`, `test_migrate.py`, `test_import.py`, `test_init.py`, `test_adopt.py`. Depends on TASK-1228, TASK-1229, TASK-1230 and TASK-1231, because the deletions need every caller gone. Runs beside TASK-1233, which touches only `_tui/` and `_cli/_ui.py`.

## Acceptance

- FEAT-1226 US1 for every command listed: one call (`init`/`adopt` local only), exit 3 on import findings, the schema hard stop with today's text, output and error text unchanged.
- FEAT-1226 US2: the 8 flags print their report; `init --json` never prompts.
- FEAT-1226 US3: no CLI-side JSON assembly is left anywhere; every `--json` is an operation's `data`.
- ADR-1224 points 2, 3a, 4 and 8 (increment 5): no `_cli` module other than the `LocalApi` factory imports `squads._services`, guard green with no pending list.

## Test approach (ADR-1172)

- Existing surface suite as the proof, including the arranged-corpus cases rule 5 allows for `repair`, `migrate`, `adopt` and `renumber`; only additive `--json` expectation edits.
- New surface cases: 8, one whole-document case per new flag with its `covers` marker; the `init --json` case asserts that no prompt reaches stdout.
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
The removal sweep (ADR-1224 points 4, 8): the `_services` guard's pending list is empty and removed; `get_service`, `get_service_bypassing_index_cross_check`, the root-context memo and the second bridge crossing are deleted; the root callback's schema gate (`require_current_schema`, `apply_gate`) gives way to each operation's `grant`, and the grant guard reads the operation table only; the CLI-side JSON builders (`build_item_json`, `build_item_row_json`, `build_subentity_json`, `build_role_json_payload`, `_view_json_payload` and any left) and every `_cli/_common.py` helper left without a caller are deleted; no `_cli` function takes a `Service`. Afterwards, `uv run vulture` on `_cli/` shows no new dead code. Held by the guards and the whole surface suite.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — JSON output on the 8 corpus and creation keys

<!-- sq:subtask:ST5:body -->
`--json` on 8 keys (ADR-1224 point 3a): `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `init`, `adopt`, each printing its report. Tests: one whole-document case per key with its `covers` marker; the `init --json` case also asserts no prompt reaches stdout. Falsify each once. 8 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
