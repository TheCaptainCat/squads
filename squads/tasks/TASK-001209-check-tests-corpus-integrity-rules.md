---
id: TASK-1209
sequence_id: 1209
type: task
title: 'Check tests: corpus integrity rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Reconciliation and duplicate-id tests
  status: Done
  story: US7
- local_id: ST2
  title: Raw-text scan tests
  status: Done
  story: US7
- local_id: ST3
  title: File load and orphaned skill tests
  status: Done
  story: US7
- local_id: ST4
  title: Falsify each test two ways
  status: Done
  story: US7
created_at: '2026-10-28T08:38:03Z'
updated_at: '2026-10-28T10:41:12Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US7: breach tests in `tests/check/test_corpus_integrity_rules.py` for 18 rules: 2 always-on `SQUAD_GLOBAL_CATALOG` reconciliation members and 16 `BINDING_RULES`.

- Reconciliation members: `index_reconciled`, `backend_reconciled`.
- Raw-text scan: `markers_balanced`, `view_target_resolves`, `view_tag_in_region`, `seeded_view_resolves`, `body_regions_present`, `block_in_container`.
- File load: `file_readable`, `frontmatter_parses`, `id_present`, `id_well_formed`, `fields_valid`, `timestamps_present`.
- Orphaned skills: `skill_type_declared`.
- Duplicate ids: `ids_unique`, `numbers_unique`.
- Cross-source: `frontmatter_matches_index`.

Drift breaches (`index_reconciled`, `backend_reconciled`, `frontmatter_matches_index`, `ids_unique`, `numbers_unique`) are arranged by the file write alone, without `sq repair`. `skill_type_declared` is arranged by an override that drops the type a skill is bound to.

## Cases

- 18 breach cases.
- No param or level case: always-on members and binding rules cannot be selected.

## Acceptance

- Each of the 18 rules has a breach test asserting the whole array and exit code, with its clean pre-state.
- For a binding rule, the breach falsification removes its emission in `_services/_check.py`.
- The guard reports none of these 18 rules as undeclared.

## Ground rules (every check rule task)

- Rulebook: ADR-1201, with ADR-1172 rules 4 and 5 for in-process runs on a copied squad under the frozen clock. Read it first; its rules are cited here, not restated.
- Every breach test runs `check_json` twice: on the arranged pre-state, asserting `[]`, then after the one breaching change, asserting the whole JSON array (rule, level, message, item) and the exit code (3 when the list holds an error, 0 otherwise). Where the member has a boundary, a sibling item left at the boundary stays in the arranged state as a near-miss.
- Declare with `@pytest.mark.breaches(...)` using literal strings: `"<rule>"`, `"<rule>:param"`, `"<rule>@<level>"`. Param and level cases are never crossed with each other or with other members.
- Opt-in members are enabled only through `select_validators` (a minimal override that selects the one member on one type and keeps the bundled selection by splat reference).
- Gated breaches are arranged by writing the item file and running `sq repair`; drift breaches by the file write alone. Only `sq check --json` output honours a declaration.
- Falsify each test three ways when written (breach, clean, param or level), restore, and record in the handback which edit turned each case red.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `ruff format --check .`, `tests/check` and `tests/meta` green, `sq check` clean. Test names describe behaviour; no ticket ids in code; docstrings of one or two sentences.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1209 add-subtask "<title>"`; track with `sq task 1209 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reconciliation and duplicate-id tests

<!-- sq:subtask:ST1:body -->
In `tests/check/test_corpus_integrity_rules.py`: breach tests for `index_reconciled`, `backend_reconciled`, `frontmatter_matches_index`, `ids_unique` and `numbers_unique`, each arranged by the file write alone, without `sq repair`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Raw-text scan tests

<!-- sq:subtask:ST2:body -->
In the same module: breach tests for `markers_balanced`, `view_target_resolves`, `view_tag_in_region`, `seeded_view_resolves`, `body_regions_present` and `block_in_container`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — File load and orphaned skill tests

<!-- sq:subtask:ST3:body -->
In the same module: breach tests for `file_readable`, `frontmatter_parses`, `id_present`, `id_well_formed`, `fields_valid`, `timestamps_present` and `skill_type_declared`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Falsify each test two ways

<!-- sq:subtask:ST4:body -->
No param or level case applies, so each test is shown red on breach (the emission removed, or the member's detection broken) and on clean (reported unconditionally). Restore and record each edit in the handback.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T10:00:24Z] `python-dev` Elias Python:
  - Implemented in 4b36f876: tests/check/test_corpus_integrity_rules.py (21 tests, 18 rules; second branch tests for index_reconciled, backend_reconciled, seeded_view_resolves); _arrange gains CRLF-aware file-edit and copy helpers. tests/check+meta 770 passed after merge; each rule falsified breach+clean, src restored.
<!-- sq:discussion:end -->
