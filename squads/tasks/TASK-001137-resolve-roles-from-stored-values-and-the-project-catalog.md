---
id: TASK-1137
sequence_id: 1137
type: task
title: Resolve roles from stored values and the project catalog
status: Draft
author: tech-lead
priority: low
refs:
- MILE-1051:targets
- BUG-1075:fixes
- BUG-1065:fixes
- BUG-1045:fixes
- BUG-1030:fixes
- TASK-1125
description: Stored default and model on any role, init --roles over overrides, scaffold
  --new reserved slugs
subentities:
- local_id: ST1
  title: Keep a stored default designation on a catalog-less role
  status: Todo
- local_id: ST2
  title: Apply a stored model on any role
  status: Todo
- local_id: ST3
  title: Resolve init --roles against the project role catalog
  status: Todo
- local_id: ST4
  title: Refuse reserved slugs in override scaffold --new
  status: Todo
created_at: '2026-10-25T05:39:18Z'
updated_at: '2026-10-25T05:40:50Z'
---
<!-- sq:body -->
## Goal

A role resolves from what its item stores and what the squad's own role documents declare: a designation or model set on any role takes effect, `sq init --roles` sees the project catalog, and a scaffold never writes a role file that activation refuses. Four defects in `src/squads/_roles/` and the override scaffold.

## Read on release/0.17 HEAD (2026-10-25)

- `role_base_from_item` (`_roles/_resolver.py`) returns `None` for a role with no catalog entry (a per-slug override file only), so `resolve_role_with_base` builds it from the file and the stored `is_default` is dropped. For a bundled role it swaps in the stored `is_default` but never the stored `model`; only `dev_base_from_item` reads `attrs.model(item)`.
- `resolve_roles` / `role_by_slug` (`_roles/_catalog.py`) read the module-level bundled `BUNDLES` / `_BY_SLUG`; `init` and `adopt` (`_services/_service.py`) and `_cli/_main.py` call them.
- `scaffold_new_role` (`_overrides/_service.py`) checks path safety and bundled slugs, not `reserved_role_slug_problem` (`_models/_participants.py`), which `sq role activate` uses.

## Ruling in force

BUG-1065, op-pierre 2026-10-16: every role needs its model, not only developers; a model set on any role must take effect. ST2 implements that, not the refusal the bug body suggests.

## Ordering

ST3 changes what `init` and `adopt` resolve, the two constructions TASK-1125 folds into one composition function. Run ST3 after TASK-1125 lands, on its composition function. ST1, ST2 and ST4 do not touch the composition root and can run first.

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
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:50Z] `tech-lead` Olivia Lead:
  - Drafted from the MILE-1051 bug triage; each bug re-read against release/0.17 HEAD, subtask bodies carry defect, expected behaviour and the falsifying table. Ordering and composition-root dependencies are in the body and on MILE-1051. Promote to Ready at dispatch.
<!-- sq:discussion:end -->
