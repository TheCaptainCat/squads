---
id: TASK-1135
sequence_id: 1135
type: task
title: Make sq check name the real cause of a damaged file
status: InProgress
author: tech-lead
assignee: python-dev
priority: medium
refs:
- MILE-1051:targets
- BUG-993:fixes
- BUG-987:fixes
- BUG-1022:fixes
- BUG-1014:fixes
- BUG-999:fixes
- TASK-1126
description: Number clash, stray skill file, missing sub-entity regions, scaffold
  after a field change, import finding order
subentities:
- local_id: ST1
  title: Check each indexed item against its own file's text
  status: Todo
- local_id: ST2
  title: Name the remedy for a stray stripped skill file
  status: Todo
- local_id: ST3
  title: Refuse and report missing sub-entity and discussion regions
  status: Todo
- local_id: ST4
  title: Read an untouched scaffold as unwritten after a field change
  status: Todo
- local_id: ST5
  title: Order import findings the way sq check does
  status: Todo
created_at: '2026-10-25T05:39:16Z'
updated_at: '2026-10-25T16:02:39Z'
---
<!-- sq:body -->
## Goal

`sq check` and the writes it guards name the real cause of a damaged or ambiguous file, and never lose a finding or crash on one. Five defects on one surface: the per-file scan in `src/squads/_services/_check.py`, the validator engine in `src/squads/_services/_validators.py`, the stray-file remedy in `src/squads/_services/_base.py` / `_skill_files.py`, and the import findings that reuse the same engine.

## Read on release/0.17 HEAD (2026-10-25)

- `_check.py` fills `bodies[seq] = text` per file, keyed by sequence number, so a second file carrying the same number (another id) overwrites the text the indexed item is checked against.
- `_base.py` `_skill_remedy` returns `None` for a stamped file whose slug is not a managed slug, so a renamed stripped skill file gets the bare "file has no `id` in frontmatter".
- `_subentities.py` `_block_body_mutate` calls `sections.replace_section`, which raises `KeyError` on a missing region; no validator reports a missing sub-entity block, body region or discussion region (the item `sq:body` region already has one, `_check.py` around line 323).
- `scaffold_body` (`_rendering/_engine.py`) re-renders the creation template from the item's current fields; the review template interpolates `target_ref`, the default template the type.
- `_import.py` `_board_debt_findings` returns `engine.report(...)` in catalog order; `sq check` sorts with `_check_issue_sort_key` (`_cli/_main.py`).

## Ordering

Land before TASK-1126: that task gives every `CheckIssue` a registered rule, so the new findings here (ST3) are then registered with the rest instead of retrofitted. Nothing here touches the composition root.

## Gates

`uv run --all-extras pyright`, `ruff check`, `ruff format --check`, `tests/meta`, and the tests derived from the diff (grep the changed messages across `tests/`). Falsify each new row: break the fix, see it red, restore.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1135 add-subtask "<title>"`; track with `sq task 1135 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Check each indexed item against its own file's text

<!-- sq:subtask:ST1:body -->
**Defect (BUG-993).** When a second item file carries a number the index already holds under another id, `sq check` runs the indexed item's validators against the other file's text. A task then gets "no 'subtasks' container section ... revert subentity_kinds.subtask.plural", a remedy for an override that does not exist.

**Expected.** Body-reading validators see only the text of the file whose frontmatter id is the indexed item's id. The squad gets the shared-number error BUG-994 added, naming both files, and no finding derived from the wrong file.

**Where.** `_check.py`, where `bodies` and `on_disk` are filled; key the text by the item id, or drop it when the file's id differs from the indexed one.

**Test: body text per number clash** (one table)

| Index holds | Extra file | Expected findings |
|---|---|---|
| TASK-21 | BUG-21 file, valid | shared-number error only |
| BUG-21 | TASK-21 file, valid | shared-number error only |
| TASK-21 with a real container rename | none | container finding still reported |
| TASK-21 | FEAT-21 file with a status banner | shared-number error, no banner finding on TASK-21 |
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Name the remedy for a stray stripped skill file

<!-- sq:subtask:ST2:body -->
**Defect (BUG-987).** A managed skill file renamed off its canonical name and stripped of its frontmatter is reported only as "file has no `id` in frontmatter". `sq sync` has already written a healthy canonical file, `sq repair` says "fix the file", and no command clears it, so `check` stays at exit 3.

**Expected.** The finding says the file is a stray copy of a skill that is healthy elsewhere, names that file, and says to delete the stray one. A stripped file at its canonical name keeps today's "run `sq sync`" remedy.

**Where.** `_base.py` `_skill_remedy` / `_missing_id_message`, using the skill folder state in `_skill_files.py`. Detect by number: a stamped `SKILL-<n>-<slug>.md` whose number another file carries with full frontmatter.

**Test: remedy for a skill file with no id** (one table)

| File state | Expected remedy |
|---|---|
| canonical name, frontmatter stripped | run `sq sync` (unchanged) |
| renamed suffix, stripped, canonical file healthy | names the canonical file, says delete this one |
| renamed suffix, stripped, no canonical file | a remedy that restores one (not "fix the file") |
| user-authored skill, stripped | no managed-skill remedy |
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refuse and report missing sub-entity and discussion regions

<!-- sq:subtask:ST3:body -->
**Defect (BUG-1022).** On a task whose subtask block or `sq:subtask:ST1:body` region was removed, `sq task <n> subtask 1 body -m x` (and `--append`) ends in a raw `KeyError` traceback. `sq check` reports nothing for either shape, nor for a work item whose `sq:discussion` region is missing.

**Expected.** The write fails with one `error:` line naming the missing region and the remedy, exit 1, file and index unchanged. `sq check` reports, as an error, a declared sub-entity whose block or body region is missing and a work item whose discussion region is missing, in the wording family of the existing missing `sq:body` finding.

**Where.** `_subentities.py` `_block_body_mutate` (raise `SquadsError` before `replace_section`); a new per-item validator next to `_subentity_container_marker`. Check every other `replace_section`/`get_section` caller on a sub-entity region for the same shape.

**Test: missing region, write and check** (one table)

| Removed | Command | Expected |
|---|---|---|
| `subtask:ST1:body` pair | `subtask 1 body -m x` | error line, exit 1, file bytes unchanged |
| same | `subtask 1 body --append -m x` | same |
| whole `subtask:ST1` block | `subtask 1 body -m x` | same |
| `subtask:ST1:body` pair | `sq check` | error naming ST1's body region |
| `discussion` pair | `sq check` | error naming the discussion region |
| nothing (control) | `sq check` | no region finding |
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Read an untouched scaffold as unwritten after a field change

<!-- sq:subtask:ST4:body -->
**Defect (BUG-1014).** The body overwrite guard and the unwritten-body check compare the stored body with the scaffold re-rendered from the item's current fields. After `update --set target_ref=...` on a review, or a retype, the re-render differs from the untouched stored scaffold, so `body -m` refuses ("already has a body") and `sq check` stops reporting the unwritten body.

**Expected.** A body still equal to the scaffold the item was created with reads as unwritten, whatever fields changed since. An authored body still reads as authored.

**Where.** `scaffold_body` (`_rendering/_engine.py`), `pristine_body` (`_services/_base.py`) and the `body_written` validator. The approach is open. Prefer one that derives the answer (for example, accepting the scaffold rendered with the interpolated fields absent as well as present) over storing a creation fingerprint; if only a stored value works, raise it with the architect before building it.

**Test: untouched scaffold after a field change** (one table)

| Created | Then | `body -m x` | `sq check` |
|---|---|---|---|
| review, no target_ref | set target_ref | replaces | unwritten-body finding |
| review with target_ref | change target_ref | replaces | unwritten-body finding |
| review with target_ref | unset target_ref | replaces | unwritten-body finding |
| default-template item | retype | replaces | unwritten-body finding |
| review, body authored | set target_ref | refuses | no finding |
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Order import findings the way sq check does

<!-- sq:subtask:ST5:body -->
**Defect (BUG-999).** `sq import` prints one item's board-debt warnings in the order of the type's effective validator list, so selecting a validator changes the order of its output; `sq check` sorts the same findings. Scripts read import output.

**Expected.** Import findings are ordered by the same key `sq check` uses, so the order is independent of the validator list and identical between the two commands.

**Where.** `_import.py` `_board_debt_findings`, sorting with the key `_cli/_main.py` uses (`_check_issue_sort_key`). Move the key below the CLI so the service can use it. The `--json` findings array follows the same order.

**Test: import findings order** (one table)

| Selection on the type | Expected order for one item |
|---|---|
| bundled list only | check's order |
| `no_status_banner` selected after the bundled members | check's order (same as above) |
| same selection, `--json` | same order in `findings` |
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:47Z] `tech-lead` Olivia Lead:
  - Drafted from the MILE-1051 bug triage; each bug re-read against release/0.17 HEAD, subtask bodies carry defect, expected behaviour and the falsifying table. Ordering and composition-root dependencies are in the body and on MILE-1051. Promote to Ready at dispatch.
<!-- sq:discussion:end -->
