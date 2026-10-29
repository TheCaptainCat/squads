---
id: TASK-1246
sequence_id: 1246
type: task
title: 'Fix item verb bugs: guide options, ref rm, sub-entities, view ID'
status: InReview
author: tech-lead
priority: medium
refs:
- BUG-1183:fixes
- BUG-1184:fixes
- BUG-1185:fixes
- BUG-1186:fixes
- BUG-1240:fixes
- MILE-1241:targets
description: create guide options, truthful ref rm, sub-entity title and comment errors,
  workflow view prefix check
subentities:
- local_id: ST1
  title: Accept --priority, --label and --ref on create guide
  status: Done
- local_id: ST2
  title: Refuse ref rm for a ref the item lacks
  status: Done
- local_id: ST3
  title: Decide and apply the add-subtask empty-title rule
  status: Done
- local_id: ST4
  title: Report a missing sub-entity on comment like sibling verbs
  status: Done
- local_id: ST5
  title: Refuse a wrong ID prefix in workflow view
  status: Done
created_at: '2026-10-29T16:27:30Z'
updated_at: '2026-10-29T19:19:33Z'
---
<!-- sq:body -->
## Goal

Item and sub-entity verbs report what they did truthfully and resolve an ID the same way everywhere. Five bugs, one subtask each: `create guide` options (BUG-1183), `ref rm` on an absent ref (BUG-1184), `add-<kind>` without a title (BUG-1185), a comment on a missing sub-entity (BUG-1186) and the wrong-prefix ID in `workflow view` (BUG-1240).

## Files

- `src/squads/_cli/_create.py`: `create_guide`.
- `src/squads/_services/_refs.py`: `rm_ref`.
- `src/squads/_services/_collab.py`: the missing-discussion error (around line 325).
- `src/squads/_services/_views.py`: `resolve_view_source`, which today resolves through `require_item` (`src/squads/_index/_resolver.py`) and so skips the prefix check `resolve_any_id` (`src/squads/_services/_base.py`) applies.
- BUG-1185 only, if the ruling is to refuse: `src/squads/_services/_base.py` (`subentity_title`), `src/squads/_cli/_items.py` (`_register_add`, the TITLE argument) and the import path that shares the rule.
- Tests: `tests/cli/test_create.py`, `tests/cli/test_item_verbs.py`, `tests/cli/test_subentity_verbs.py`, `tests/cli/test_comment_verbs.py`, `tests/cli/test_workflow.py`.

## Tests

CLI surface tests per ADR-1172, one per behaviour, declared with `@pytest.mark.covers(...)`, observed through `sq` itself. Expected new tests: 5 (BUG-1240 covers both the item view and the ref view in one parametrised case only if they share one resolution path; otherwise two, for 6). Falsify each by hand before handoff: revert the fix, watch the test go red, restore, watch it go green, and report both.

## Changelog

Every bug here changes adopter-visible behaviour (new options, a refusal where there was a success line, a corrected message). Report each change and why in the handoff so the tech writer adds a line under the 0.19.0 section of `CHANGELOG.md`; do not edit `CHANGELOG.md` yourself.

## Gates

`uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the test modules above plus `tests/meta` and `tests/cli` (the floor for a change under `_cli/`), and `sq check` clean for this task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1246 add-subtask "<title>"`; track with `sq task 1246 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Accept --priority, --label and --ref on create guide

<!-- sq:subtask:ST1:body -->
Fixes BUG-1183.

**Expected.** `create guide` accepts `--priority`, `--label` and `--ref`, as `create task` does, because the guide type declares the priority field. Prefer deriving the guide command's options the way the generic `_make` commands do over hand-adding three options, so a field declared on guide in an override also reaches it.

**Test.** In `tests/cli/test_create.py` (`@pytest.mark.covers("create guide", "--priority")`, plus `--label` and `--ref`): create a guide with all three and assert they show on `sq guide N show --json`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Refuse ref rm for a ref the item lacks

<!-- sq:subtask:ST2:body -->
Fixes BUG-1184.

**Expected.** `ref rm TARGET` on an item that carries no ref to TARGET exits 1 with a message such as `TASK-21 has no ref to TASK-22`, and prints no success line. Removing a ref that exists works as today. The refusal lives in the service (`rm_ref`), so the roster routes (`sq skill ... ref rm`) get it too.

**Test.** In `tests/cli/test_item_verbs.py` (`@pytest.mark.covers("ref rm")` in the module's form): remove an absent ref, assert exit 1 and no `removed` line.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Decide and apply the add-subtask empty-title rule

<!-- sq:subtask:ST3:body -->
Fixes BUG-1185.

**Ruling needed before any code.** The current behaviour is a documented design, not an accident: the CLI help calls the title "Optional short title", `subentity_title` in `_services/_base.py` stores a blank title as none on purpose, and `docs/adoption.md` states that a sub-entity's title is optional. The bug asks to reverse that. The product owner (or op-pierre) decides: either close BUG-1185 as WontFix citing the documented rule, or make a sub-entity title required on every path (`add-<kind>`, import, update), with the docs and help changed to match.

**Expected if required.** `add-<kind>` without a title, or with a blank one, exits non-zero and adds nothing.

**Test if required.** In `tests/cli/test_subentity_verbs.py` (`@pytest.mark.covers("add-subtask")` in the module's form): `add-subtask` with no title is refused and `show --full` lists no new sub-entity.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Report a missing sub-entity on comment like sibling verbs

<!-- sq:subtask:ST4:body -->
Fixes BUG-1186.

**Expected.** A comment on a sub-entity that does not exist gives the same message as the sibling verbs, `no subtask ST9 in TASK-21`, exit 1, with no internal marker name and no "was it scaffolded?" hint. The fix belongs where the comment path resolves the sub-entity, so every kind gets it.

**Test.** In `tests/cli/test_comment_verbs.py` (sub-entity `comment` pair, in the module's `covers` form): comment on `subtask 9` of an item that has only ST1, assert exit 1 and the `no subtask ST9 in` message.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Refuse a wrong ID prefix in workflow view

<!-- sq:subtask:ST5:body -->
Fixes BUG-1240.

**Expected.** `sq workflow view NAME ID` resolves ID the way `sq show` does: a full id whose prefix is not its owner's is refused with `SKILL-2 is ROLE-2 (role)`, exit 1, for every view source kind (item views such as `memory_skill` and `role_definition`, and ref views such as `milestone_rollup`). A bare number or a correct full id resolves as today.

**Test.** In `tests/cli/test_workflow.py` (`@pytest.mark.covers("workflow view")`): one parametrised case over an item view and a ref view given a wrong-prefix id, asserting exit 1 and the `is ROLE-` message.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T16:42:43Z] `op-pierre` Pierre Chat:
  - 2026-10-29: BUG-1185 is ruled: the sub-entity title is required everywhere (see BUG-1185).
- [2026-10-29T16:52:18Z] `python-dev` Elias Python:
  - Handback: all five fixes are in c3a74531 on branch worktree-agent-a6842b5fa4632a07c. One regression test per bug in tests/regressions/ plus surface cases in tests/cli. Gates, tests/cli and tests/meta green (1558 passed). Each test fails with the src changes reverted. Sub-entity titles are now required on add, update and import. Please decide whether existing untitled sub-entities need a migration. The squads corpus has none. @manager
- [2026-10-29T17:25:44Z] `python-dev` Elias Python:
  - REV-1247 round: F3, F4, F9, F10 Fixed; F6 and F7 done for the TASK-1246 cases. Commits 36f1ec37 and 0553c825 on worktree-agent-a6842b5fa4632a07c, rebased on origin/release/0.18.1. Follow-up: playbook.toml still names the guide --tag flag; it needs --tags at the 0.18.1 version bump. @manager
<!-- sq:discussion:end -->
