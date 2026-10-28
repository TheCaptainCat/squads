---
id: TASK-1212
sequence_id: 1212
type: task
title: Fix the check rule harness review findings
status: Done
parent: FEAT-1202
author: tech-lead
priority: high
refs:
- REV-1211:addresses
description: Teardown, guard, select_validators, helper API and production table fixes
  for the REV-1211 findings
subentities:
- local_id: ST1
  title: 'Teardown and guard holes: F1, F4, F5, F7, F10'
  status: Done
  story: US1
- local_id: ST2
  title: 'select_validators: F2, F3'
  status: Done
  story: US1
- local_id: ST3
  title: 'Shared helpers and CLI arrangement: F8, F9'
  status: Done
  story: US1
- local_id: ST4
  title: 'Required-param table entry: F6'
  status: Done
  story: US2
created_at: '2026-10-28T09:10:36Z'
updated_at: '2026-10-28T10:19:17Z'
---
<!-- sq:body -->
## Goal

Fix all ten REV-1211 findings before the next check rule module is built, since every later module copies the harness and helper API. Test-side changes, plus one production table entry (F6). The ADR-1201 §4 amendment that F1 needs is the architect's; the harness change follows the amended wording.

## Scope

- F1: a `rule:param` declaration is honoured only when the member's param selection is still in the override at the run that reported the rule, and that run came after the selection (selections recorded with a run counter or an effective-selection snapshot per run).
- F2: `select_validators` substitutes an entry whose selection key matches a bundled entry by writing the bundled list out explicitly with that entry replaced, no splat; otherwise it keeps the splat. The `no_parent@warn` level case moves back to epic, `subentities_settled_with_parent@error` back to review, and `type_has_live_author@error` becomes selectable in `[squad]`.
- F3: `select_validators` keeps selections per table across calls and rewrites the whole file each time, preserves an override already in the squad, accepts extra per-type keys (such as `ref_rules=[...]`) rendered with a TOML writer, and takes the squad from the `project` fixture instead of `Path.cwd()`. The union test stops concatenating `ref_rules` onto the file.
- F4: the marker reader reads `ClassDef.decorator_list` and a class-level `pytestmark` into `runs`, reports a shadowed duplicate test name as an ignored marker, and the `_marker_ast` docstring states the remaining blind spots (aliased or imported marks, parametrize `marks=`, runtime skips). Each new shape is a row in both guards' "does not run" tables.
- F5: the guard requires a required-param member's `rule` and `rule:param` (and the squad-global param minimum) on the same marker; the teardown requires at least two distinct params for a multi-selection member's `:param` declaration.
- F6: `ref_rule_target_present` joins `REQUIRED_PARAM_VALIDATOR_NAMES`, after checking the bare entry is not reported twice by `_check_validator_param` and `check_ref_rule_targets`; the two ref tests fold into one case declaring both `ref_rule_target_present` and `ref_rule_target_present:param`.
- F7: the teardown requires at least two runs for a `rule` or `rule@level` declaration, the rule absent from the first and present in a later one.
- F8: breaches the CLI can arrange go through the CLI (`body -m`, `update --desc`, `update --title`, `ref rm`, `ref add`, status transitions); the file write plus `sq repair` stays only for error-level variants the gate refuses, and each such test says so.
- F9: one `_arrange` API (`ok`, `issue`, `create` returning the id, status and ref helpers taking the id and resolving the noun from the spec, `rewrite` by id with one documented replace semantic); the sub-entity and prose modules drop their local `_ok`/`_rewrite`/`_issue` and literal ids and paths, and every pre-state asserts `([], 0)`.
- F10: the covers guard calls `_marker_ast.string_arguments`; `covers_arguments` is deleted.

## Acceptance

- Each hole is shown red then green: F1 (the reviewer's probe: param selection overwritten, member never reported, teardown passes), F2 (`subentities_settled_with_parent@error` on review and `type_has_live_author@error` in `[squad]` load and report), F4 (class-level skip, class `pytestmark`, shadowed redefinition), F5 (separate `item_title_max` and `item_title_max:param` markers; a one-param multi-selection case), F7 (a single run on an already-breached state). Report each seed and its red output in the handback.
- The TASK-1204 and TASK-1205 modules use the shared helpers, with no hard-coded item ids or item paths.
- Test names describe behaviour; no ticket IDs in code, names or docstrings. Docstrings one or two sentences.
- `git diff src` holds only the F6 table entry.

## Gates

```bash
uv run --all-extras pyright
uv run --all-extras ruff check src tests
uv run --all-extras ruff format --check src tests
uv run --all-extras pytest tests/check tests/meta -n 3
~/.local/bin/sq check
```

The main loop runs the full suite.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1212 add-subtask "<title>"`; track with `sq task 1212 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Teardown and guard holes: F1, F4, F5, F7, F10

<!-- sq:subtask:ST1:body -->
F1, F4, F5, F7 and F10 from REV-1211: the teardown honours `rule:param` only on a report after a still-effective param selection, requires a clean first run for `rule` and `rule@level`, and requires two params for a multi-selection member; the guard puts a required-param member's `rule` and `rule:param` on one marker; the marker reader sees class-level skips and shadowed redefinitions and documents its blind spots; the covers guard reuses `string_arguments`. Done when each hole is red on its seed and green after.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — select_validators: F2, F3

<!-- sq:subtask:ST2:body -->
F2 and F3 from REV-1211: `select_validators` substitutes an already-bundled entry in a written-out list instead of splatting it, keeps selections per table across calls, preserves an existing override, accepts extra per-type keys through a TOML writer, and takes the squad from `project`. Move the epic and review level cases back to their shipping types and drop the `ref_rules` string concatenation. Done when `subentities_settled_with_parent@error` on review and `type_has_live_author@error` in `[squad]` load and report.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Shared helpers and CLI arrangement: F8, F9

<!-- sq:subtask:ST3:body -->
F8 and F9 from REV-1211: settle one `_arrange` API (`ok`, `issue`, `create` returning the id, spec-resolved status and ref helpers, `rewrite` by id with one documented replace semantic), migrate the parent, ref, sub-entity and prose modules onto it with returned ids and `([], 0)` pre-states, and arrange every breach the CLI accepts through the CLI, keeping the file write only where the gate refuses it. Done when no rule module holds a local helper copy or a literal item id or path.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Required-param table entry: F6

<!-- sq:subtask:ST4:body -->
F6 from REV-1211: add `ref_rule_target_present` to `REQUIRED_PARAM_VALIDATOR_NAMES`, after checking the bare entry is not reported twice at load, and fold the two ref tests into one case declaring both `ref_rule_target_present` and `ref_rule_target_present:param`. Done when the derived declarations require no separate bare breach case for the member.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:22:00Z] `python-dev` Elias Python:
  - All ten findings fixed; tests/check + tests/meta green (704 passed); src holds only the F6 table entry and its single-report guard.
- [2026-10-28T09:40:06Z] `python-dev` Elias Python:
  - F8, F9 and F11 fixed; tests/check + tests/meta 716 passed.
<!-- sq:discussion:end -->
