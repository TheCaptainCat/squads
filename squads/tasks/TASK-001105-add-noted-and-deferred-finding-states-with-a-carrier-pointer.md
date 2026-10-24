---
id: TASK-1105
sequence_id: 1105
type: task
title: Add Noted and Deferred finding states with a carrier pointer
status: Draft
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
- ADR-1102:implements
description: The finding lifecycle of ADR-1102 (REV-1099 F7).
subentities:
- local_id: ST1
  title: Declare Noted, Deferred and the deferred role flag, and refuse the flag on
    item lifecycles
  status: Todo
  story: US6
- local_id: ST2
  title: 'Store deferred_to: update and add flags, refusals, head line, JSON row and
    import op'
  status: Todo
  story: US6
- local_id: ST3
  title: Remap deferred_to on retype, type rename and renumber, and sever it on remove
  status: Todo
  story: US6
- local_id: ST4
  title: Add the subentity_deferral_resolved check, with the retired-carrier warning
  status: Todo
  story: US6
- local_id: ST5
  title: Add the Noted and Deferred line to the bundled reviewer guidance
  status: Todo
  story: US6
- local_id: ST6
  title: Refresh the stability and workflow docs for the finding lifecycle, and write
    the CHANGELOG entry
  status: Todo
  assignee: tech-writer
  story: US6
created_at: '2026-10-24T10:04:03Z'
updated_at: '2026-10-24T10:08:04Z'
---
<!-- sq:body -->
## Goal

Deliver ADR-1102 (REV-1099 F7). Findings gain a terminal `Noted` (role `done`) and a terminal `Deferred` (a new `deferred` role). A deferred finding stores a `deferred_to` pointer to the item that carries the work, and `sq check` verifies it. ADR-1102 is the specification; where this body and the ADR disagree, the ADR wins.

## Approach

- **Spec and role catalog** (`src/squads/_specs/workflow.toml`, `src/squads/_workflow/_models.py`, `src/squads/_workflow/_loader.py`).
  - Lifecycle: `Open = ["Fixed", "WontFix", "Noted", "Deferred"]`. The two new states are targets only, with no table key of their own.
  - Statuses: `Noted` with role `done` and badge 🔵; `Deferred` with role `deferred` and badge 🟣.
  - The role model gains `deferred: StrictBool = False`, beside `blocked`. A new bundled role `deferred` sets `settled = true`, `hidden = true`, `color = "info"`, `deferred = true`.
  - Plane-1 refusal: the loader refuses a spec in which an item lifecycle reaches a status whose role sets `deferred`.
  - `sq workflow roles --json` rows gain `deferred`.
  - Every behaviour keys on the flag, never on the word `Deferred`.
- **The pointer** (`src/squads/_models/_subentity.py`, `src/squads/_services/_subentities.py`, `src/squads/_cli/_items.py`, `src/squads/_discussion.py`, `templates/subentities/head.md.j2`).
  - `SubEntity` gains a typed `deferred_to: str | None`, written to frontmatter only when set.
  - `update --deferred-to <ID|number>` resolves like a ref and refuses an item that does not exist.
  - Moving into a deferred-flagged status with no pointer, given or already stored, is refused. `--force` waives only an illegal edge, never the missing pointer.
  - `--deferred-to` is refused on a sub-entity not in (or not moving into) a deferred-flagged status, and on a kind whose lifecycle reaches none. Given without `--status` on an already-deferred sub-entity, it moves the pointer.
  - Leaving the status clears the pointer.
  - The `:head` line shows "Deferred to `<ID>` — `<title>`" (resolved in `_refresh_head`).
  - Sub-entity `--json` rows carry `deferred_to`, `null` when absent.
  - `add-<kind> --status <deferred status>` follows the same rule and takes `--deferred-to`.
  - The import model's `sub-status` op (`src/squads/_services/_import_model.py`) gains an optional `deferred_to` field under the same rules, so an import can defer a finding.
- **Remapping** (`src/squads/_services/_retype.py`, `src/squads/_services/_rename.py`, `src/squads/_services/_maintenance.py` `renumber`, `src/squads/_services/_duplicate_ids.py`, and `remove_work_item` in `src/squads/_services/_items.py`). Remap `deferred_to` wherever `parent` and `refs` are remapped. Removing the carrying item severs the pointer the way it severs incoming refs.
- **The check: `subentity_deferral_resolved`** (warn). Add it to `VALIDATOR_NAMES`, `CATALOG`, `SUBENTITY_VALIDATOR_NAMES` and the `work` entry of `CATEGORY_BUNDLES`. It reports:
  - a deferred-flagged sub-entity with no pointer, or with a pointer that does not resolve to an indexed item;
  - a carrier resting in a status with the `retired` role (bundled `Cancelled`, and `WontFix` on a bug), keyed on the role name and never on a status name, while a `superseded` carrier is not reported;
  - a pointer stored on a sub-entity that is not in a deferred-flagged status.
- **Settled reads.** `Noted` and `Deferred` are settled, so existing openness reads (default sub-entity listings, roll-ups, `sq mine` sub-item rows) need no name-based change. Grep for any read of the literal finding status names and fix it if one exists. TASK-1104's rule depends on this.
- **Bundled reviewer guidance** (`src/squads/_specs/playbook.toml`, `[[types.review.roles]]` reviewer). One line: close an info finding as `Noted`; hand work to another item with `--status Deferred --deferred-to <ID>`.
- **No migration** and no `SCHEMA_VERSION` bump (ADR-1102).

## Tests

Service-level plus CLI smoke. Run `tests/meta`, `tests/integration` and `tests/cli`. Falsify each test.

- Table over transitions: Open → each of the four targets; Noted/Deferred → Open refused without `--force` and allowed with it; Deferred without a pointer refused, also with `--force`.
- Table over `--deferred-to` shapes: full ID, bare number, nonexistent ID, on a non-deferred finding, on a story (kind reaching no deferred status), pointer move without `--status`, leaving the status clears it.
- Head line and `--json` row with and without a pointer.
- Remapping: retype, type rename and renumber of the carrier each rewrite the pointer. Removing the carrier severs it and check then reports nothing stale.
- The check: table over carrier status roles (pending, active, done, retired, superseded, missing) plus the hand-edited stray pointer.
- Overrides: a project override that redeclares `Open = ["Fixed", "WontFix"]` loads and keeps its own machine. A project status `Postponed` with a `deferred`-flagged role gets the refusal, the pointer and the check. An item lifecycle reaching a deferred-flagged status is refused at load.
- Import: a `sub-status` event with and without `deferred_to`.
- Round-trip: `sq repair` rebuilds the pointer from frontmatter (invariant 1).

## Generated output

The bundled `workflow.toml` and `playbook.toml` change. Regenerate the goldens pinning `sq workflow` output, the `sq-review` skill and the lifecycle renderings, plus the template manifest (`scripts/gen_template_manifest.py`). TASK-1103 (F6) and TASK-1106 (F17) also edit these two TOML files, so sequence them.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST6).

- Added: findings can be closed as **Noted** (an info finding with nothing to fix) or **Deferred** (the work moved to another item): `sq review <n> finding <k> update --status Deferred --deferred-to <ID>`. `sq check` warns on a deferred finding whose pointer is missing or broken, or whose carrier was cancelled. Reopening either takes `--force`.
- Added: a `deferred` flag on status roles, so a project can give its own status this behaviour.
- **Upgrade the whole team together.** There is no schema bump. An older squads release reads a review written by 0.17 as having undeclared statuses, and drops `deferred_to` the next time it writes that review.
- If your override redeclares the finding `Open` list, add `"Noted"` and `"Deferred"` to it to adopt the new states. Otherwise your lifecycle is unchanged.
- No migration.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1105 add-subtask "<title>"`; track with `sq task 1105 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare Noted, Deferred and the deferred role flag, and refuse the flag on item lifecycles

<!-- sq:subtask:ST1:body -->
Part of REV-1099 F7, per ADR-1102. Lifecycle `Open` gains `Noted` and `Deferred` as target-only states, with statuses, badges and roles as the ADR tables them. The role model gains `deferred`, the bundled `deferred` role is added, and the loader refuses an item lifecycle that reaches a deferred-flagged status. `sq workflow roles --json` rows gain `deferred`. Test an override that redeclares `Open`, and a custom `Postponed` status.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Store deferred_to: update and add flags, refusals, head line, JSON row and import op

<!-- sq:subtask:ST2:body -->
Part of REV-1099 F7, per ADR-1102. Add a typed `deferred_to` slot on `SubEntity`, written only when set. `update --deferred-to` and `add-<kind> --status … --deferred-to` take it, with the ADR's refusals (missing pointer even with `--force`, wrong status or kind, nonexistent item). The pointer moves without `--status`, and leaving the status clears it. The head line reads Deferred to <ID> — <title>, the `--json` row carries `deferred_to`, and the import `sub-status` op takes it too.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Remap deferred_to on retype, type rename and renumber, and sever it on remove

<!-- sq:subtask:ST3:body -->
Part of REV-1099 F7, per ADR-1102. Wherever `parent` and `refs` are remapped (`_retype.py`, `_rename.py`, `renumber`, `_duplicate_ids.py`), remap `deferred_to` too. Removing the carrying item severs the pointer the way it severs incoming refs. One test per path, plus `sq repair` rebuilding the pointer from frontmatter.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Add the subentity_deferral_resolved check, with the retired-carrier warning

<!-- sq:subtask:ST4:body -->
Part of REV-1099 F7, per ADR-1102. A warn rule in the `work` bundle and the sub-entity validator set. It reports a deferred sub-entity with no pointer or an unresolved one, a carrier at a status with the `retired` role (keyed on the role, never on `Cancelled`, with `superseded` carriers exempt), and a stray pointer on a sub-entity not in a deferred-flagged status. Table over carrier roles.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Add the Noted and Deferred line to the bundled reviewer guidance

<!-- sq:subtask:ST5:body -->
Part of REV-1099 F7, per ADR-1102 Consequences. One line in the reviewer guide on the review type in `playbook.toml`: close an info finding as `Noted`, and hand work to another item with `--status Deferred --deferred-to <ID>`. Regenerate the `sq-review` skill golden and the manifest.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Refresh the stability and workflow docs for the finding lifecycle, and write the CHANGELOG entry

<!-- sq:subtask:ST6:body -->
Part of REV-1099 F7, per ADR-1102 Consequences. In `docs/stability.md`, update the sub-entity state paragraph (the pointer), the `sq workflow roles --json` row (`deferred`) and the finding lifecycle wherever it is shown, and do the same in `docs/workflow.md`. Write the 0.17.0 CHANGELOG entry from this task's substance, including that a team upgrades together because an older release drops `deferred_to`.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
