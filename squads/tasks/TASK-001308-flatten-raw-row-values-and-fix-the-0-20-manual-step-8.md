---
id: TASK-1308
sequence_id: 1308
type: task
title: Flatten raw row values and fix the 0.20 MANUAL step 8
status: Done
parent: FEAT-1290
author: tech-lead
assignee: python-dev
refs:
- REV-1307:addresses
description: Raw rows on one line; step 8 names both required keys
subentities:
- local_id: ST1
  title: Print each raw row value on one line
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Name both required keys in the 0.20 MANUAL step 8
  status: Done
  assignee: python-dev
created_at: '2026-11-05T03:17:05Z'
updated_at: '2026-11-05T03:55:25Z'
---
<!-- sq:body -->
Two defects left on FEAT-1290 after REV-1307 and the writer's pass on TASK-1298.

- ST1: under `--raw`, a panel row whose value holds a line break ends the metadata list mid-row (REV-1307 F3).
- ST2: the 0.20 MANUAL step 8 misstates what 0.19 requires of a custom type's playbook entry.

Gates: `uv run --all-extras pyright`, `ruff check`, `ruff format --check` clean on the touched files; the touched test modules and `tests/meta` pass; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1308 add-subtask "<title>"`; track with `sq task 1308 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Print each raw row value on one line

<!-- sq:subtask:ST1:body -->
`raw_lines` in `src/squads/_cli/_render/_rows.py` writes `row.plain` verbatim, so a value with a newline (a `--desc` of `line one<newline>line two`, a string attribute) prints `- **summary:** line one`, then `line two` as a bare line. Markdown readers, the VS Code preview among them, see the list end there, and the rows after it (`author`, `refs`, `file`) read as body.

Rule (the manager's call): under `--raw`, each row's value prints on one line, its line breaks joined by a single space. Do it in `raw_lines`, so every caller gets it: `raw_head` (item show, roster entry show) and the role show's header in `_cli/_render/_roster.py`. The styled panel is out of scope.

Acceptance:
- `show --raw` of an item whose `--desc` holds a newline prints the summary row on one line, and every later row is still a list bullet before the blank line.
- One test per show kind that can carry a multi-line row value (the item show at least; each roster show whose rows include an authored string, e.g. a role's title, if one can hold a newline). Each test fails with the join reverted.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Name both required keys in the 0.20 MANUAL step 8

<!-- sq:subtask:ST2:body -->
Step 8 of the 0.20 MANUAL in `src/squads/_migrations/_v0_19_to_v0_20.py` says 0.19 "still requires `lifecycle`" on a custom type's playbook entry. 0.19 requires both `lifecycle` and `commands` there (checked against the 0.19 `ItemPlaybookSpec` in the writer's TASK-1298 handback; `docs/migration.md` and the CHANGELOG already say both keys).

Acceptance:
- Step 8 says 0.19 requires both `lifecycle` and `commands` on a custom type's entry, matching the `docs/migration.md` wording.
- The frozen `migrate help` document in `tests/cli/_bundled_documents.py` is regenerated, not hand-patched, and `tests/cli/test_migrate.py` passes.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T03:48:45Z] `python-dev` Elias Python:
  - @reviewer ST1 and ST2 are done in the working tree, uncommitted. ST1: raw_lines in _cli/_render/_rows.py joins a row value line breaks with single spaces; tests: item show (test_show.py) and skill show when-to-use (test_skill.py), both fail with the join reverted, on bundled and override squads. ST2: step 8 of the 0.20 MANUAL names both lifecycle and commands; the frozen migrate help document was updated to the live output and test_migrate passes, failing when the wording is reverted. Added 2 tests. Gates: pyright, ruff check and ruff format clean; main run 2286 passed, 4 skipped; override run 1207 passed, 180 skipped. REV-1307 F3 is Fixed.
- [2026-11-05T03:55:25Z] `manager` Catherine Manager:
  - Done: verified by the reviewer (REV-1307 F3 Verified). REV-1307 F4 (refuse line breaks in titles at input) and F5 (splitlines and strip before the raw join) are deferred to FEAT-1290 for a follow-up task.
<!-- sq:discussion:end -->
