---
id: TASK-1214
sequence_id: 1214
type: task
title: Fix the final check rule review findings
status: Done
parent: FEAT-1202
author: tech-lead
priority: high
refs:
- REV-1213:addresses
description: Near-miss, malformed override, stderr, oracle and helper fixes for the
  REV-1213 findings
subentities:
- local_id: ST1
  title: 'Override stamp and drift near-misses: F1'
  status: Done
  story: US8
- local_id: ST2
  title: 'Harness: malformed override and stderr: F2, F3'
  status: Done
  story: US8
- local_id: ST3
  title: 'Independent oracles for corpus rules: F4, F6'
  status: Done
  story: US7
- local_id: ST4
  title: 'One _arrange helper per job: F5'
  status: Done
  story: US7
created_at: '2026-10-28T10:20:38Z'
updated_at: '2026-10-28T10:31:46Z'
---
<!-- sq:body -->
## Goal

Fix REV-1213 findings F1 to F6 in the check rule test modules and their harness before FEAT-1202 closes. Test-side only: no change under `src`. F7 is a product question outside this task.

## Scope

- F1: `override_stamped` gains a near-miss pre-state, an unstamped add-only override (a new type, no shadowing key) asserting `[]`, whose breach adds one shadowing key to the same file. `override_current` gains a pre-state stamped at an older release whose recorded workflow is unchanged, asserting `[]`, picked by a new `unchanged_base(key)` helper beside `stale_base`; the breach restamps at `stale_base(WORKFLOW_KEY)`.
- F2: `params_in_override` returns `{}` for an override that does not decode, `select_validators` fails with a clear message when its base override does not decode, and a TOML syntax error in the workflow override is pinned as a `workflow_loads` case (beside the semantic one, or replacing its breach).
- F3: `check_json` asserts stderr instead of dropping it. `CheckRun` carries `stderr`, the harness fails on non-empty stderr unless the test states the stderr it expects, and the stdout parse stays.
- F4: the `frontmatter_parses` test builds its expected message from `yaml.safe_load` on the broken frontmatter, `f"malformed frontmatter in {path}: {exc}"`, keeping the whole-array equality.
- F5: one helper per job in `tests/check/_arrange.py`. `rewrite` folds into the byte-preserving `edit_item_file` built on `item_path`; `write_override` and `write_override_as_is` become one helper with a `stamp: str | None` argument (default the running version) that also covers the hand-built stale stamp; `address` and `copy_item_file` resolve through the squad's active spec; the hand-rolled sites in `corpus_scans` and `skill_type_declared` go through the helpers; the `add_roster` docstring says why it parses human output.
- F6: the `backend_reconciled` tests use literal paths (`CLAUDE.md`, `.claude/agents/tech-lead.md`) and the literal backend name; `managed_paths` and its production imports go away.

## Acceptance

- F1 is shown as a hole: the reviewer's two mutations (the shadowing condition of `workflow_stamp_finding` replaced by `True`; the content gate cut to `stamp != __version__`) leave the module green before the near-miss tests land and turn it red after. Report each mutation and its red output in the handback.
- F2: a real TOML syntax-error override (for example `[items.task` with no closing bracket) reaches `sq check` and the test pins the `workflow_loads` issue it reports.
- F3: a stderr assertion that would have caught the duplicate working-language warning. The test may pin today's output; QA files the duplicate as a bug.
- F4: the expected text comes from `yaml.safe_load`, not from PyYAML's message copied verbatim.
- F5: one helper per job, no hand-rolled file edit or noun resolution left in a rule module, no change to what any test asserts.
- F6: literal expected paths, independent of the backend under test.
- Test names describe behaviour; no ticket IDs in code, names or docstrings. Docstrings one or two sentences.
- `git diff src` is empty.

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

_Add with `sq task 1214 add-subtask "<title>"`; track with `sq task 1214 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Override stamp and drift near-misses: F1

<!-- sq:subtask:ST1:body -->
F1 from REV-1213: `override_stamped` gets an unstamped add-only pre-state asserting `[]` whose breach adds one shadowing key; `override_current` gets a pre-state stamped at an older release with an unchanged recorded workflow, picked by a new `unchanged_base(key)` helper, whose breach restamps at `stale_base(WORKFLOW_KEY)`. Done when both reviewer mutations stay green before the near-miss tests and go red after.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Harness: malformed override and stderr: F2, F3

<!-- sq:subtask:ST2:body -->
F2 and F3 from REV-1213: `params_in_override` returns `{}` for an override that does not decode, `select_validators` fails clearly on an undecodable base, and a TOML syntax-error workflow override is pinned as a `workflow_loads` case. `CheckRun` carries `stderr` and `check_json` fails on non-empty stderr unless the test states what it expects. Done when the syntax-error case reaches `sq check` and a stderr assertion would have caught the duplicate working-language warning.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Independent oracles for corpus rules: F4, F6

<!-- sq:subtask:ST3:body -->
F4 and F6 from REV-1213: the `frontmatter_parses` expected message is built from `yaml.safe_load` on the broken frontmatter, and the `backend_reconciled` tests use the literal paths and backend name instead of asking the backend under test. Done when neither test imports production code to compute its expected value and `managed_paths` is gone.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — One _arrange helper per job: F5

<!-- sq:subtask:ST4:body -->
F5 from REV-1213: fold `rewrite` into the byte-preserving `edit_item_file`, merge the two override writers into one with a `stamp: str | None` argument, resolve `address` and `copy_item_file` through the active spec, route the hand-rolled edits in `corpus_scans` and `skill_type_declared` through the helpers, and document why `add_roster` parses human output. Done when no rule module hand-rolls a file edit or noun resolution and no assertion changes.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
