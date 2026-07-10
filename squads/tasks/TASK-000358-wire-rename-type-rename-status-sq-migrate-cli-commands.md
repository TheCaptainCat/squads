---
id: TASK-358
sequence_id: 358
type: task
title: Wire rename-type/rename-status sq migrate CLI commands
status: Done
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: sq migrate rename-type CLI command
  status: Todo
  story: US1
- local_id: ST2
  title: sq migrate rename-status CLI command
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:35Z'
updated_at: '2026-07-10T01:27:21Z'
---
<!-- sq:body -->
Implements US1+US2 CLI surface. Add two sq migrate sub-commands in src/squads/_cli/_migrate.py, siblings of 'repad' (NOT registry migrations): 'sq migrate rename-type <old-type> <new-type>' and 'sq migrate rename-status <type> <old-status> <new-status>'.

Follow the repad command shape exactly: @migrate_app.command + @common.command (async), get_service(), call svc.rename_type(...) / svc.rename_status(...), print a green summary from the returned RenameResult (count renamed, e.g. 'TASK -> TICKET, N item(s) renamed; index rebuilt'), and advise 'run sq check' after. Validation/refusal errors are raised as SquadsError by the service and rendered cleanly (exit 1) by the existing handler.

These are on-demand, project-invoked data rewrites (re-baseline #4) — do NOT touch SCHEMA_VERSION and do NOT add an entry to _migrations/_registry.py; nothing to add to 'sq migrate help'/chlog (repad is the precedent: a migrate sub-command absent from the changelog). Extend the module docstring's command list at the top of _migrate.py to mention the two new commands.

CLI smoke tests: rename-type happy path (with a target type declared via a test .overrides/workflow.toml fixture), rename-status happy path, and the reserved-meta / invalid-new-status rejection paths surfacing a clean exit 1. Watch the FORCE_COLOR harness gotcha — assert on plain text, conftest strips ANSI.

Files owned: src/squads/_cli/_migrate.py, tests/test_cli_migrate.py (or the existing migrate CLI test module — extend it). Depends on TASK-356 and TASK-357 (both service methods must exist).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 358 add-subtask "<title>"`; track with `sq task 358 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq migrate rename-type CLI command | US1 |
| ST2 | Todo |  | sq migrate rename-status CLI command | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq migrate rename-type CLI command

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq migrate rename-status CLI command

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T01:16:56Z] Elias Python:
  - Starting: wiring rename-type/rename-status as sq migrate sub-commands per repad's shape.
- [2026-07-10T01:20:19Z] Elias Python:
  - Added sq migrate rename-type/rename-status, siblings of repad (no registry/schema/help/chlog changes).
  - rename-type prints: 'task -> ticket, N item(s) renamed; index rebuilt'.
  - rename-status prints: 'task: Draft -> Ready, N item(s) renamed' (never renders RenameResult.ids as old->new — those pairs are (id,id) for a status rename).
  - CLI smoke tests in tests/test_cli.py: rename-type happy path (declares 'ticket' via a test .overrides/workflow.toml, mirroring test_rename.py's _TICKET), rename-status happy path, reserved-meta-type and invalid-new-status rejections (exit 1).
  - Gates green: pyright, ruff check/format, tests/test_cli.py, tests/test_rename.py, tests/test_squad_ref_hygiene.py. Full suite not run (main loop's job). Leaving InProgress for review/close.
- [2026-07-10T01:25:19Z] Paul Reviewer:
  - Reviewed uncommitted TASK-358 diff (independent). VERDICT: APPROVE. Clean repad-shaped CLI wiring; gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures), no ticket IDs in source. One LOW cosmetic finding (arrow glyph).
  - Shape/errors correct: both commands are @migrate_app.command + @common.command async -> get_service() -> svc.rename_type/rename_status -> green summary -> 'run sq check' advice, matching repad (_migrate.py:120,143). @common.command turns SquadsError into a clean 'error:' message + Exit(1) (it subsumed the old @handle_errors), so the service's fail-closed refusals surface as exit 1 — proven by the reserved-meta and invalid-new-status tests.
  - Status output avoids the id-pair pitfall (Q2): YES. rename-status prints '{type}: {old_status} -> {new_status}, N item(s) renamed' (_migrate.py:159) — the status transition, never RenameResult.ids; test asserts f'{item_id} -> {item_id}' NOT in output. rename-type likewise prints the type transition, not ids. e() wraps every user arg (_migrate.py:134,159); tests assert plain text (conftest strips ANSI). 
  - Raw-json-read test (Q4) is SOUND, not papering over: the CLI's get_service() loads the .overrides spec (so rename-type accepts 'ticket' and exits 0 — asserted), but the test's own helper Service(project) defaults to the bundled-only spec which post-rename can't load() a 'ticket'-typed item; reading .squads.json raw to assert entry['type']=='ticket' is the right workaround (mirrors the index-full test). rename-status can use svc.store.load() because type is unchanged — consistent.
  - Flags: (a) LOW/cosmetic — the summaries use ASCII '->' while repad uses Unicode '→' (_migrate.py:114 vs 134/159); recommend matching repad's '→' for family consistency. (b) rename-status omitting '; index rebuilt' is fine (no structural/id change; defensible difference from rename-type). (c) CONFIRMED correct per re-baseline #4: no SCHEMA_VERSION bump, no _registry.py entry, absent from 'sq migrate help'/chlog — exactly repad's precedent (a @migrate_app.command not in MIGRATIONS); the module docstring command list was extended as required. Smoke tests cover both happy paths + reserved-meta + invalid-new-status rejections.
- [2026-07-10T01:26:49Z] Elias Python:
  - Cosmetic fix per review: both summaries now use the Unicode arrow (→), matching repad. Updated matching test assertions.
- [2026-07-10T01:27:20Z] Catherine Manager:
  - Reviewer-approved; F1 (ASCII -> vs repad's Unicode →) fixed — both summaries now use → matching repad, test assertions updated (incl. the negative id-pair check). Migrate CLI tests green (9). Cosmetic glyph change, targeted-verified. Landing.
<!-- sq:discussion:end -->
