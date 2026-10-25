---
id: TASK-1137
sequence_id: 1137
type: task
title: Resolve init --roles against the project role catalog
status: Ready
author: tech-lead
priority: low
refs:
- MILE-1051:targets
- BUG-1045:fixes
- TASK-1125
- ADR-1151
- TASK-1153
description: 'BUG-1045: sq init --roles accepts bundles and roles declared in .overrides/roles.toml'
subentities:
- local_id: ST1
  title: Keep a stored default designation on a catalog-less role
  status: Cancelled
- local_id: ST2
  title: Apply a stored model on any role
  status: Cancelled
- local_id: ST3
  title: Resolve init --roles against the project role catalog
  status: Todo
- local_id: ST4
  title: Refuse reserved slugs in override scaffold --new
  status: Cancelled
created_at: '2026-10-25T05:39:18Z'
updated_at: '2026-10-25T22:06:39Z'
---
<!-- sq:body -->
## Goal

`sq init --roles` resolves bundles and role slugs against the squad's own role catalog, so a bundle or role declared in `.overrides/roles.toml` is accepted. One defect (BUG-1045), carried by ST3.

## Scope

ST1, ST2 and ST4 moved to TASK-1153, which implements ADR-1151: the stored default and model are its "stored values win" step (TASK-1153 ST2), and the reserved-slug refusal lands on `sq role add` (TASK-1153 ST3) as `sq override scaffold --new` is retired. They are Cancelled here.

## Read on release/0.17 HEAD (2026-10-25)

`resolve_roles` / `role_by_slug` (`_roles/_catalog.py`) read the module-level bundled `BUNDLES` / `_BY_SLUG`; `init` and `adopt` (`_services/_service.py`) and `_cli/_main.py` call them. TASK-1125 (Done) folded the two constructions into one composition function; ST3 builds on it.

## Ordering

Independent of TASK-1153. If TASK-1153 ST1 lands first, the project catalog ST3 resolves against also carries `[templates]`; `--roles` names bundles and catalog slugs only, so no template enters it.

## Gates

pyright, ruff check, ruff format --check, `tests/meta`, `tests/integration`, `tests/cli`; grep the changed role messages across `tests/`. Falsify each new row.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1137 add-subtask "<title>"`; track with `sq task 1137 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Keep a stored default designation on a catalog-less role

<!-- sq:subtask:ST1:body -->
**Defect (BUG-1075).** `sq role <slug> set-default` on a project role (a `.overrides/roles/<slug>.toml` with no catalog entry) stores `is_default: true`, but the role resolves with `is_default: false`: `sq role list` shows no default, `show --json` says false, and the generated CLAUDE.md drops the default-role line.

**Expected.** The stored designation wins over the resolved one for every role, catalog-backed or not, through the one seam `resolve_role_for_item` uses.

**Test: stored default designation** (one table)

| Role | Action | `role list` Default | `show --json` | CLAUDE.md line |
|---|---|---|---|---|
| project role, file only | `set-default` | ticked | true | present |
| project role, previous default archived | `set-default` | ticked | true | present |
| bundled role | `set-default` | ticked | true | present |
| project role, default moved away | `set-default` on another | not ticked | false | names the other |
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-25T22:04:35Z] `tech-lead` Olivia Lead:
  - Moved to TASK-1153 ST2 (stored values win, ADR-1151 decision 1); its test table is carried there.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Apply a stored model on any role

<!-- sq:subtask:ST2:body -->
**Defect (BUG-1065).** `model` stored on a non-developer role (through `sq import`, the only path that sets it today) is written to the role item and then ignored: `sq role show`, the `.claude/agents` pointer and `sq check` keep the catalog model.

**Expected.** A model stored on any role takes effect wherever the role resolves, as it already does for a developer (op-pierre's ruling on the bug). Precedence: the stored model over the per-slug file over the catalog. An invalid stored model is refused at the write, with the resolver's own whitelist message.

**Test: stored model on any role** (one table)

| Role | Stored model | `role show` | pointer `model:` |
|---|---|---|---|
| bundled reviewer | haiku | haiku | haiku |
| project role, file says sonnet | haiku | haiku | haiku |
| developer | haiku | haiku (unchanged behaviour) | haiku |
| bundled reviewer | none | catalog model | catalog model |
| bundled reviewer | `opuss` via import | refused, nothing written | catalog model |
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-25T22:04:36Z] `tech-lead` Olivia Lead:
  - Moved to TASK-1153 ST2 (stored values win, ADR-1151 decision 1); its test table is carried there.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Resolve init --roles against the project role catalog

<!-- sq:subtask:ST3:body -->
**Defect (BUG-1045).** `sq init --roles <name>` resolves bundles and slugs against the bundled catalog only, so a bundle or role declared in `.overrides/roles.toml` is refused ("no predefined role 'ops'"). Reachable with `sq init --force` on a project that has the override, or a checkout where the override is committed and `.squads.toml` is not.

**Expected.** When `.overrides/roles.toml` is present, `--roles` accepts its bundles and role slugs, resolved through the squad-aware catalog `sq role` and `sq sync` use. With no override, behaviour is unchanged. An invalid override is refused with the loader's own message, not "no predefined role".

**Ordering.** After TASK-1125: build on its composition function rather than the two `init`/`adopt` constructions it replaces.

**Test: init --roles against a project catalog** (one table)

| `.overrides/roles.toml` | `--roles` | Expected |
|---|---|---|
| declares bundle `ops = [manager, sre]` | `ops` | manager and sre created |
| declares role `sre` | `manager,sre` | both created |
| extends `all` with `sre` | `all` | sre among them |
| absent | `sre` | "no predefined role 'sre'", exit 1 (unchanged) |
| malformed TOML | `ops` | loader's malformed-override error, exit 1 |
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse reserved slugs in override scaffold --new

<!-- sq:subtask:ST4:body -->
**Defect (BUG-1030).** `sq override scaffold --new <slug>` writes `.overrides/roles/<slug>.toml` for reserved slugs (`squads`, `operator`, any `op-` slug) that `sq role activate` then refuses, leaving a dead file.

**Expected.** The scaffold refuses a reserved slug up front with the same message `role activate` gives, exit 1, and writes nothing. Share `reserved_role_slug_reason`; do not copy the rules. The role-group verb names `group_verb_problem` refuses at activation get the same treatment.

**Test: scaffold --new refuses what activate refuses** (one table)

| Slug | Expected |
|---|---|
| `squads` | activate's message, exit 1, no file |
| `operator` | same |
| `op-foo` | same |
| a role-group verb name | same |
| `sre` (control) | file written, exit 0 |
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-25T22:04:37Z] `tech-lead` Olivia Lead:
  - Moved to TASK-1153 ST3: ADR-1151 retires sq override scaffold --new, and the reserved-slug refusal lands on sq role add, which shares activate's check.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:50Z] `tech-lead` Olivia Lead:
  - Drafted from the MILE-1051 bug triage; each bug re-read against release/0.17 HEAD, subtask bodies carry defect, expected behaviour and the falsifying table. Ordering and composition-root dependencies are in the body and on MILE-1051. Promote to Ready at dispatch.
- [2026-10-25T22:06:39Z] `tech-lead` Olivia Lead:
  - Narrowed to ST3 (BUG-1045). ST1, ST2 and ST4 moved to TASK-1153, which implements ADR-1151; their bug refs moved with them. TASK-1125 is Done, so ST3 is unblocked.
<!-- sq:discussion:end -->
