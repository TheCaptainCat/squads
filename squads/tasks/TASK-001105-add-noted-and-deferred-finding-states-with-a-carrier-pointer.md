---
id: TASK-1105
sequence_id: 1105
type: task
title: Add Noted and Deferred finding states with a carrier pointer
status: Done
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
  status: Done
  maps_to: US6
- local_id: ST2
  title: 'Store deferred_to: update and add flags, refusals, head line, JSON row and
    import op'
  status: Done
  maps_to: US6
- local_id: ST3
  title: Remap deferred_to on retype, type rename and renumber, and sever it on remove
  status: Done
  maps_to: US6
- local_id: ST4
  title: Add the subentity_deferral_resolved check, with the retired-carrier warning
  status: Done
  maps_to: US6
- local_id: ST5
  title: Add the Noted and Deferred line to the bundled reviewer guidance
  status: Done
  maps_to: US6
- local_id: ST6
  title: Refresh the stability and workflow docs for the finding lifecycle, and write
    the CHANGELOG entry
  status: Done
  assignee: tech-writer
  maps_to: US6
created_at: '2026-10-24T10:04:03Z'
updated_at: '2026-10-28T12:11:18Z'
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

One table per behaviour. A row exists only if breaking the fix turns it red, so check each one that way. Rows are boundaries and failures, never a cross product. Service level unless stated; one CLI row where the CLI adds an option. Run `tests/meta`, `tests/integration` and `tests/cli`.

- **Finding lifecycle edges**. Rows: Open to Noted allowed; Noted to Open refused without `--force`; Noted to Open allowed with `--force`. Open to Deferred is covered by the pointer table; the existing edges keep their tests.
- **The pointer on update**. Rows: Deferred with no pointer refused; the same refused with `--force`; a full ID stored; a bare number resolved; a nonexistent ID refused; `--deferred-to` on a finding not moving into a deferred status refused; `--deferred-to` on a story (a kind reaching no deferred status) refused; `--deferred-to` without `--status` on a deferred finding moves the pointer; leaving Deferred (with `--force`) clears it.
- **Other entry points to the same rule** (one row each): `add-finding --status Deferred --deferred-to` stores it; an import `sub-status` with `deferred_to` stores it; an import `sub-status` to Deferred without it is refused. One CLI row: `finding <k> update --status Deferred --deferred-to <n>` stores the pointer.
- **Rendering**. Rows: the `:head` line reads "Deferred to `<ID>` — `<title>`"; the `--json` row carries `deferred_to`, and `null` when absent.
- **Loader and flag keying**. Rows: an override redeclaring `Open = ["Fixed", "WontFix"]` loads with its own machine; an item lifecycle reaching a deferred-flagged status is refused at load; a project status `Postponed` with a deferred-flagged role gets the missing-pointer refusal.
- **Remapping** (one row per code path): retype, type rename, `sq renumber`, `sq repair --renumber` (`_duplicate_ids.py`) each rewrite the pointer; removing the carrier severs it.
- **`subentity_deferral_resolved`**. Rows: a deferred finding with no pointer (hand edit) warns; an unresolved pointer warns; a Cancelled carrier warns; a bug carrier at WontFix warns (another status name with the `retired` role); a Superseded carrier is silent; an active carrier is silent; a pointer on a finding not in a deferred status warns.
- **Invariant 1**: `sq repair` rebuilds the index with the pointer intact.

## Generated output

The bundled `workflow.toml` and `playbook.toml` change. Regenerate the goldens pinning `sq workflow` output, the `sq-review` skill and the lifecycle renderings, plus the template manifest (`scripts/gen_template_manifest.py`).

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
- [2026-10-24T19:46:24Z] `tech-lead` Olivia Lead:
  - Rechecked against ADR-1102 (Accepted) and the code; Tests rewritten as one table per behaviour, boundary and failure rows only. Moved to Ready.
- [2026-10-24T21:34:59Z] `python-dev` Elias Python:
  - Implemented ADR-1102; ST1 to ST5 Done, ST6 left to the tech writer. Not committed.
    
    **Per subtask**
    - ST1: finding `Open` gains target-only `Noted` (done role, blue) and `Deferred` (new `deferred` role, purple). `RoleSpec.deferred` is a TOML-boolean-only flag; the loader refuses an item lifecycle that reaches a deferred-role status; `sq workflow roles` (json and table) gains `deferred`. New `WorkflowSpec.subentity_deferred_statuses(kind)`; everything keys on the flag.
    - ST2: typed `SubEntity.deferred_to`, written to frontmatter only when set. `update --deferred-to` and `add-<kind> --status ... --deferred-to` exist only on kinds that reach a deferred status; the service refuses the missing pointer even with `--force`, a nonexistent item, and a wrong status or kind. The pointer moves without `--status` and leaving the status clears it. `sub-status` import events take `deferred_to` (handles resolve). Display: `Deferred to <ID> — <title>` on the finding line in `show --full` and `--raw`, `deferred to:` on `finding <k> show`; every sub-entity JSON row (`show`, `<kind>s --json`, view rows) carries `deferred_to` (null when absent). The `:head` region and `_refresh_head` the task names no longer exist, so the line lives in `_cli/_common._subentity_badge_line`, with the carrier title resolved in `get_block` (`SubentityDetail.carrier_title`).
    - ST3: `resync_edges` (retype, type rename) remaps the pointer in the index; `renumber` and `repair --renumber` rewrite it through the whole-word id rewrite they already do. `remove_work_item` counts a deferred_to as an incoming reference: refused without `--force`, cleared with it. Same-id groups in `repair --renumber` are listed, not rewritten, by design; the pointer shows up in that list through the generic frontmatter scan.
    - ST4: `subentity_deferral_resolved` (warn) in VALIDATOR_NAMES, CATALOG, DEFAULT_VALIDATOR_LEVEL, SUBENTITY_VALIDATOR_NAMES and the `work` bundle: missing or unresolved pointer, carrier with the `retired` role (superseded exempt), stray pointer on a non-deferred sub-entity.
    - ST5: one line in the reviewer guidance (`playbook.toml`).
    
    **Generated output**: manifest and content store via `gen_template_manifest.py` then `seed_content_store.py --rebuild` (dropped the one stale 0.17.0 blob; `--release-gate` passes). Goldens via UPDATE_GOLDENS=1 (json shapes, workflow, migrated corpus indexes, cheatsheet, agents section) plus the sq-review skill body and playbook_spec goldens, which have no update switch, regenerated from the test module's own render functions. Note: the stored index now carries `deferred_to: null` on every sub-entity, like `story: null`.
    
    **Tests**: 5 new files (service: pointer/lifecycle/entry points, loader flag, remapping, check table; cli: display and json). 21 hand-applied mutations of the source each turn a new test red. Existing tests adjusted: roles flag test, validator-set table, custom-kind json row, and the forced-status walk now skips a deferred status (it needs a carrier). Ran green: tests/meta, integration, cli, unit (8752 passed), plus tests/service by keyword. Full suite not run. `~/.local/bin/sq check` clean; pyright, ruff check and format clean.
    
    **CHANGELOG substance (0.17.0)**, as in the task body, plus:
    - `sq <type> <n> <kind>s --json` and `show --json` rows gain `deferred_to`; `sq workflow roles --json` rows gain `deferred`; the index file gains a `deferred_to: null` per sub-entity.
    - Removing an item that is a carrier needs `--force`, which clears the pointers.
    - Import `sub-status` accepts `deferred_to`; import `add-sub`/`add-finding` do not, so a finding added as Deferred through an import is refused.
    
    `git status --short`: 24 modified (src 18, tests 6 incl. goldens summarized below), 5 new test files, plus squads/ board files and the untracked .claude/worktrees (not mine). Goldens modified: ~27 files under tests/goldens.
- [2026-10-24T21:58:23Z] `tech-writer` Theo Writer:
  - ST6 done: CHANGELOG 0.17.0 entries plus docs, every claim driven on the dev build in a scratch squad. Not committed.
    
    - CHANGELOG.md: five Added entries (Noted/Deferred with `--deferred-to` and the display; the `deferred` role flag; `deferred_to`/`deferred` in JSON and import `sub-status`; `subentity_deferral_resolved`; carrier removal needing `--force`), plus a Changed entry telling teams to upgrade together.
    - docs/workflow.md: a new "Closing a finding as Noted or Deferred" section; the finding row, the settled-status list and the role table/attribute list gain the new states and the flag.
    - docs/overrides.md: the `deferred` flag bullet with the load refusal and a `Postponed` example; the role table gains the column and the `deferred` row; nine bundled roles.
    - docs/stability.md: the sub-entity state paragraph (the pointer), the sub-entity JSON object (`deferred_to`), and the `sq workflow roles --json` row (`deferred`).
    - README.md: the finding lifecycle line and `--deferred-to` among the update options.
    
    Measured, and it differs from the ADR's Consequences: released 0.16.0 does not just report undeclared statuses and drop `deferred_to`. Once one review holds a Noted or Deferred finding, 0.16 fails on every command that loads the board (`sq list`, an unrelated `sq task <n> show`, `sq repair`) with "sub-entity F1 has status 'Noted', which the active spec no longer declares". The CHANGELOG states that measured behaviour. @architect the ADR's Consequences line may want a dated correction.
    
    Docs guard to run: tests/meta/test_documented_commands_resolve_against_cli.py (new `sq review … update --status Deferred --deferred-to` and `add-finding --status Deferred --deferred-to` invocations). @manager
- [2026-10-25T10:52:59Z] `architect` Robert Architect:
  - REV-1129 F1 ruling (op-pierre, option b), now in ADR-1102 "Schema bump, with a no-op migration". What to build:
    - `SCHEMA_VERSION` in `src/squads/_models/_schema.py`: `"0.16"` to `"0.17"`.
    - New private runner `src/squads/_migrations/_v0_16_to_v0_17.py`: the release's one migration step, built as a contribution list like `_v0_15_to_v0_16.py`, with no contribution that writes. It rewrites no item file and returns a zero-count `MigrationOutcome`; `sq migrate up` does the repair and the stamp itself. `MANUAL` empty, a one-line `SUMMARY`.
    - Append `Migration(version="0.17.0", from_schema="0.16", to_schema="0.17", ...)` to `MIGRATIONS` in `_migrations/_registry.py`.
    - Tests: one table covering a 0.16 squad through `sq migrate up` (stamped 0.17, no item file changed, Noted/Deferred usable after), and the gate both ways: 0.17 code on a 0.16 squad asks for `sq migrate up`; a squad stamped 0.17 under a package at 0.16 prints the upgrade message. Then the current-schema fixtures: `tests/goldens/migrated_corpus/*/.squads.{json,toml}` carry `"0.16"` as the end state, and `test_v0_3_migration_chain_reaches_current_schema.py` plus the 0.16-step tests reference it. Update each golden's end state, do not edit an assertion to fit.
    - CHANGELOG (writer): the 0.17.0 "teams upgrade together" Changed entry becomes a migration note: run `sq migrate up` once; an older release is then refused with an upgrade message.
    - This repo: board ops run on released 0.16, which a migrated squad refuses. The squad is migrated only after the board tool is upgraded, on op-pierre's call; until then no finding here is set to Noted or Deferred.
    @tech-lead please brief @python-dev from this.
- [2026-10-25T11:15:57Z] `python-dev` Elias Python:
  - REV-1129 F1 done, not committed.
    - Schema 0.16 to 0.17 (`_models/_schema.py`); no-op runner `_migrations/_v0_16_to_v0_17.py` (zero-count outcome, empty MANUAL) plus its registry entry (0.17.0). It is not a contribution list: with nothing to write, a one-function runner was simpler.
    - Test: `tests/cli/test_a_016_squad_migrates_to_017_without_touching_an_item_file_cli.py`, one table (0.16 squad: list is refused asking for `sq migrate up`; `migrate up` stamps 0.17 with every .md hash unchanged). Falsified both rows (runner writes a file; schema left at 0.16): each went red.
    - Reverse gate driven by hand: 0.17 scratch squad under released 0.16.0 prints `error: this squad is at schema v0.17, newer than squads 0.16.0 (v0.16). Upgrade the squads package.`
    - Goldens regenerated with UPDATE_GOLDENS (only the schema_version lines changed, 16 files plus a new v0_16 pair) and reflog_shape.json; chain/step/stamp tests updated to name 0.17 as the end state.
    - CHANGELOG "teams upgrade together" entry replaced by a short migration note for the writer to polish.
    - Gates: pyright 0 errors, ruff check and format clean, `sq check` clean. Targeted pytest (meta, integration, goldens, migration and header tests) green; full suite not run.
    - This repo was not migrated.
- [2026-10-25T11:35:11Z] `manager` Catherine Manager:
  - Accepted: REV-1129 Approved (all findings Verified); schema bump at 565e1671, docs at 556b8239; full suite green.
<!-- sq:discussion:end -->
