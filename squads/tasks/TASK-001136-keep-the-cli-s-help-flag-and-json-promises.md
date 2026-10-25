---
id: TASK-1136
sequence_id: 1136
type: task
title: Keep the CLI's help, flag and JSON promises
status: Done
author: tech-lead
priority: medium
refs:
- MILE-1051:targets
- BUG-1094:fixes
- BUG-1042:fixes
- BUG-1085:fixes
- BUG-1043:fixes
- BUG-1038:fixes
- BUG-1021:fixes
description: Verb help without resolving N, clearing an assignee, override diff --json,
  ref-add hint, per-squad custom-type cache
subentities:
- local_id: ST1
  title: Render verb help without resolving the address
  status: Done
- local_id: ST2
  title: Clear an assignee with --clear-assignee, refuse an empty one
  status: Done
- local_id: ST3
  title: Print JSON from override diff --json when nothing drifted
  status: Done
- local_id: ST4
  title: Name the real ref add form in the bundled ref-kind hints
  status: Done
- local_id: ST5
  title: Build custom-type commands from the invoked squad's spec
  status: Done
created_at: '2026-10-25T05:39:17Z'
updated_at: '2026-10-25T11:06:16Z'
---
<!-- sq:body -->
## Goal

The CLI keeps the promises its own help and flags make: `--help` always renders, an empty `--assignee` never reports a change it did not make, `--json` always prints JSON, a hint names a command that exists, and a command built from one squad's spec never answers for another. Six defects: five in `src/squads/_cli/`, one in a bundled hint string.

## Read on release/0.17 HEAD (2026-10-25)

- The type-group callback `_resolve` (`_cli/_items.py`, inside the type-group builder) resolves `N` before any subcommand parses, so `sq task 1 show --help` resolves 1 first; the root schema gate exempts `--help`, so a behind-schema squad reaches that resolution against its stale index. `_role.py` and `_skill.py` address callbacks have the same order.
- Item `update` passes `assignee=... if assignee else None`, so `""` is "not passed"; the service has no `clear_assignee`. The sub-entity update has `--clear-assignee` and reports "nothing to update" for `""`.
- `override diff --json` (`_cli/_override.py`) prints "no drifted overrides found" and returns before the JSON branch.
- `_specs/workflow.toml` ref-kind hints for `fixes` and `addresses` spell `sq ref add <task> <id> ...`; there is no `ref` group.
- `_CustomTypeGroup._custom_cmd_cache` (`_cli/__init__.py`) and the create group's cache (`_cli/_create.py`) are class-level dicts keyed by type name, never invalidated.

## Ordering

No dependency on TASK-1125 or TASK-1126. ST5 must not grow the startup memo TASK-1123 added; key or scope the cache, do not extend it.

## Gates

pyright, ruff check, ruff format --check, `tests/meta`, `tests/cli` (the goldens pin help and error text) and `tests/integration`, since ST4 edits `_specs/` and the template manifest (`_rendering/content_store.json`) holds a copy of `workflow.toml`. Falsify each new row.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1136 add-subtask "<title>"`; track with `sq task 1136 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Render verb help without resolving the address

<!-- sq:subtask:ST1:body -->
**Defect (BUG-1094, BUG-1042).** `--help` on a per-item verb resolves the address first. `sq task 1 show --help` fails with "1 is ROLE-1 (role), not a task" and `sq task 999999 show --help` with "no item with number". On a behind-schema squad the gate lets `--help` through, so the same resolution runs on the stale index and prints an unrelated error instead of help or the migrate hint.

**Expected.** Help on a leaf under an addressed group renders, exit 0, without resolving the address: in a squad with no item of the type, with a number of another type, and on a behind-schema squad. One shared helper skips resolution when help is requested, used by the item, role and skill address callbacks.

**Test: verb help without a resolvable address** (one table)

| Squad | Command | Expected |
|---|---|---|
| fresh, no task | `sq task 1 show --help` (1 is a role) | `show` help, exit 0 |
| fresh | `sq task 999999 show --help` | `show` help, exit 0 |
| fresh | `sq task 1 comment --help` | `comment` help, exit 0 |
| fresh | `sq skill 999999 show --help` | `show` help, exit 0 |
| behind schema | `sq task 1 comment --help` | help, exit 0 |
| behind schema | `sq task 1 show` | schema-gate error, exit 1 (unchanged) |
| fresh | `sq task 1 show` (1 is a role) | wrong-type error, exit 1 (unchanged) |
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Clear an assignee with --clear-assignee, refuse an empty one

<!-- sq:subtask:ST2:body -->
**Defect (BUG-1085).** `sq <type> <n> update --assignee ""` prints "updated" and changes nothing, so no CLI verb can remove an item's assignee and the `assignee_present` clearing refusal cannot be reached. On a sub-entity, `--assignee ""` says "nothing to update" although a field was passed.

**Expected.** Item `update` gains `--clear-assignee`, as the sub-entity verb has, threaded through `Service.update` and the import update event's path. An empty `--assignee ""` is refused on both verbs with a message naming `--clear-assignee`, the way `--parent ""` already names `--no-parent`. `--assignee x --clear-assignee` is refused on both.

**Test: clearing an assignee** (one table)

| Target | Flags | Expected |
|---|---|---|
| item with assignee | `--clear-assignee` | assignee removed, "updated" |
| item with no assignee | `--clear-assignee` | exit 0, file unchanged, output does not say "updated" |
| item | `--assignee ""` | error naming `--clear-assignee`, exit 1, file unchanged |
| item | `--assignee qa --clear-assignee` | refused, exit 1 |
| subtask | `--assignee ""` | same error as item, exit 1 |
| item, `assignee_present@error` selected, InProgress | `--clear-assignee` | refused by the validator |
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Print JSON from override diff --json when nothing drifted

<!-- sq:subtask:ST3:body -->
**Defect (BUG-1043).** `sq override diff --json` with nothing drifted prints the text line "no drifted overrides found", which a caller cannot parse.

**Expected.** With `--json`, stdout is always one JSON value: `[]` when nothing drifted. The text line stays for the human output. Check the other `--json` commands in `_cli/_override.py` for the same early-return shape.

**Test: override diff --json** (one table)

| Squad | Command | Expected stdout |
|---|---|---|
| no overrides | `override diff --json` | `[]`, exit 0 |
| overrides, none drifted | `override diff --json` | `[]`, exit 0 |
| no overrides | `override diff` | text line (unchanged) |
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Name the real ref add form in the bundled ref-kind hints

<!-- sq:subtask:ST4:body -->
**Defect (BUG-1038).** The bundled ref-kind hint for `fixes` and `addresses` on task tells the operator to run `sq ref add <task> <id> --kind fixes|addresses`; `sq ref` does not exist. Every adopter sees it on the task-parent refusal.

**Expected.** The hint names the real form, `sq task <n> ref add <id> --kind fixes|addresses`, as `_specs/roles.toml` already does. Regenerate the template manifest entry for `workflow.toml` the way the manifest script does; do not touch the previous release's key.

**Test: refusal hints name a real command** (one table)

| Command | Expected |
|---|---|
| `sq create task --parent TASK-n ...` | hint contains `sq task <n> ref add` |
| every bundled ref-kind hint | each `sq <word>` it names is a registered command or group |
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Build custom-type commands from the invoked squad's spec

<!-- sq:subtask:ST5:body -->
**Defect (BUG-1021).** The custom-type command caches in `_cli/__init__.py` and `_cli/_create.py` are class-level and keyed by type name only. In one process, a run against squad A builds `widget` with A's aliases; a later run against squad B, which declares `widget` with other aliases, gets A's command and `No such command 'wb'`. A one-shot `sq` cannot hit it; tests and the daemon this milestone builds can.

**Expected.** Each invocation resolves custom types and aliases from the spec of the squad `-C` names. Scope the cache to the invocation, or key it on the spec it was built from.

**Test: custom types across in-process runs** (one table)

| First run | Second run | Expected second result |
|---|---|---|
| A: `wa 2 show` | B: `wb 2 show` | exit 0, B's WID-2 |
| A: `wa 2 show` | B: `wa 2 show` (A's alias) | no such command, exit 2 |
| A: `create widget ...` | B: `create widget ...` | created in B with B's spec |
| A: `wa 2 show` | A: `wa 2 show` | exit 0 (cache still serves the same squad) |
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:48Z] `tech-lead` Olivia Lead:
  - Drafted from the MILE-1051 bug triage; each bug re-read against release/0.17 HEAD, subtask bodies carry defect, expected behaviour and the falsifying table. Ordering and composition-root dependencies are in the body and on MILE-1051. Promote to Ready at dispatch.
- [2026-10-25T05:41:43Z] `manager` Catherine Manager:
  - Promoted to Ready at dispatch; tech-lead body read, no dependency on the composition-root work.
- [2026-10-25T06:00:29Z] `python-dev` Elias Python:
  - Implemented ST1-ST5, subtasks Done, nothing committed.
    
    - ST1: `HelpAwareGroup` (`_cli/_common.py`) records, in `resolve_command`, whether `--help` is an option of the verb below it, using the existing `help_requested(argv, root)` so `-m --help` is still a value. `verb_help_requested(ctx)` is read by the item, role, skill and operator address callbacks, which skip resolution (ctx.obj stays a dict so nested callbacks still merge).
    - ST2: item `update --clear-assignee`, threaded through `Service.update`, `_update_core`, `_update_model` and the import `UpdateEvent.clear_assignee`. `_guard_assignee` refuses an empty `--assignee` and `--assignee` with `--clear-assignee` on item and sub-entity. Clearing an unassigned item with nothing else asked prints "has no assignee to clear" and writes nothing.
    - ST3: `override diff --json` no longer returns early; prints `[]`. `override list --json` had no such early return.
    - ST4: workflow.toml hints now `sq task <n> ref add <id> --kind fixes|addresses`. Ran `gen_template_manifest.py` (only the 0.17.0 `_specs/workflow.toml` hash changed, other keys untouched), then `seed_content_store.py --rebuild` to drop the superseded 0.17.0 blob (tests/meta orphan check needs it); `--release-gate` passes.
    - ST5: `SpecKeyedCache` (one value per name, valid only for the spec object it was built from) replaces both class-level dicts; the alias branch now returns the canonical command. No change to the root-context memo.
    
    Falsification reds (seam broken, new row red): ST1 hook off -> 7 of 9 rows red (the 2 unchanged-behaviour rows stay green); ST2 service clear removed -> import row, clear row and validator row red; empty-assignee guard off -> empty-assignee item and subtask rows red; no-op check off -> unassigned row red; ST3 early return restored -> both `[]` rows red; ST4 old hint -> both rows red; ST5 cache ignoring the spec -> subtask-verbs row for squad B red; old dict cache code -> the "A wa then B wb" row red. Not red: the create-command cache has no observable row (create commands are spec-agnostic at build), so only its keying is changed.
    
    CHANGELOG: four lines under 0.17.0 Fixed (ST1-ST4); ST5 unreachable from a one-shot sq, no line.
    
    Gates: pyright 0 errors, ruff check and format clean, tests/cli + tests/integration + tests/meta 5127 passed (-n 4), sq check clean. conftest still clears both caches after each test (SpecKeyedCache.clear).
- [2026-10-25T10:00:40Z] `python-dev` Elias Python:
  - REV-1139 F1-F6 fixed, findings marked Fixed; uncommitted. Targeted suites (meta, cli, unit, service, integration) 14047 passed at -n 4.
- [2026-10-25T10:33:55Z] `python-dev` Elias Python:
  - REV-1139 F7 and F8 fixed, marked Fixed; uncommitted. Targeted suites 14068 passed at -n 4.
- [2026-10-25T11:06:16Z] `manager` Catherine Manager:
  - Accepted: REV-1139 Approved; full suite green at d7927710. Bugs await QA verification.
<!-- sq:discussion:end -->
