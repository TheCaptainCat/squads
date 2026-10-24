---
id: TASK-1114
sequence_id: 1114
type: task
title: Rebuild the engine, services and CLI tests and retire old files
status: Ready
parent: FEAT-1096
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-1112:depends-on
- TASK-1113:depends-on
description: Spec loading, sq check, -C and gate, views, comments, items and roster
  services; parity then deletion.
subentities:
- local_id: ST1
  title: Rebuild spec, override and vocabulary loading at the load boundary
  status: Todo
  story: US7
- local_id: ST2
  title: Rebuild the sq check rules as one boundary table per check
  status: Todo
  story: US7
- local_id: ST3
  title: 'Rebuild the CLI spine: -C, schema gate, exit codes and clean --json'
  status: Todo
  story: US7
- local_id: ST4
  title: Rebuild views, view tags, comments and discussion tests
  status: Todo
  story: US7
- local_id: ST5
  title: Rebuild items, sub-entities, refs and roster lifecycle service tests
  status: Todo
  story: US7
- local_id: ST6
  title: Prove engine, services and CLI parity and delete their old files
  status: Todo
  story: US9
created_at: '2026-10-24T13:42:16Z'
updated_at: '2026-10-24T19:48:45Z'
---
<!-- sq:body -->
Rebuild the spec engine, services and CLI in the new root (US7), then prove parity and delete the old files this area covers (US9). This is the bulk of the suite and the bulk of the duplicate coverage. It runs after the integrity-core increment and before the backend one.

**Measured** (2026-10-24, by filename): about 8,650 old tests in 384 files fall here. The hot spots:

- `sq check` rules: 72 files, 2,358 tests. Several are check by type by level cross products, for example `tests/service/test_a_check_reports_only_on_the_types_that_select_it.py` (488 rows), `tests/service/test_item_title_max_selected_at_error_refuses_exactly_what_check_reports.py` (208) and `tests/service/test_a_selected_check_loads_or_is_refused_on_every_type_row.py` (141).
- The `-C` differential and the schema gate: 11 files, about 980 tests. `tests/cli/test_c_runs_exactly_as_cd_into_the_folder_would.py` is 477 rows (layouts from `tests/_gate_layouts.py` by command by schema direction); `tests/cli/test_the_gate_lets_past_by_command_and_direction.py` is 291.
- Views and view tags: 45 files, 1,515 tests, of which `tests/unit/test_place_view_tags_fuzz_idempotence_and_invertibility.py` alone is 1,001.
- Comments and discussion: 28 files, 969 tests, including `tests/unit/test_comment_splice_by_line_span.py` (363) and `tests/unit/test_console_escape_round_trip.py` (246).
- Override, spec and vocabulary loading: about 105 files, 1,630 tests by a looser filename match that overlaps the check files.
- 17 behaviours are tested under the same name at two layers (service and CLI, or CLI and unit), for example `status_banner_advisory_check`, `view_tag_placement` and `unreadable_files_degrade_per_file`.

Ledger classes owned here: enum identity against value equality in retype and type or status comparisons; invalid or unknown vocabulary at the load boundary; cardinality and liveness by set membership (REV-706); the config-integrity gate (`--unlink` abort leaves the file byte-identical, `--force` never overrides a clause); `FORCE_COLOR` and ANSI in `--json`.

Boundaries with the other areas: the effect of reactivation and retirement on generated files (pointers, compiled regions) belongs to the backend area; this area owns the roster lifecycle's service behaviour. The CLI output goldens in `tests/goldens` (the `--json` shapes of list, tree, show, refs, inbox, mine, blocked, workload, search, workflow and override) are ported here; the rendered-artifact goldens (CLAUDE.md and AGENTS.md sections, skill bodies, workflow cheatsheet, role, skill and operator shows) belong to the backend area.

**Parity proof before deletion.** For every ledger entry of this area, apply its recorded break in a scratch worktree, run only the old test ids the ledger lists and the new test that owns the entry, and record that both go red (or that the old suite had a gap). Only then are the old files covering the area deleted, in this increment, in one reviewed commit. An old file that still covers an entry outside this area stays until that area lands.

**Acceptance**

- Generic engine behaviour is tested once on a spec, not per type; a check is tested by one table of its boundary rows, with type selection and level tested once for all checks.
- The `-C` property is held by the boundary layouts the audit names, not the full layout by command by direction product.
- Bad-vocabulary and override-conflict failure rows exist at the load boundary.
- A thin CLI spine proves exit codes, `--json` free of ANSI under `FORCE_COLOR`, and the CLI output goldens; no behaviour is asserted at both the service and CLI layers.
- Every entry owned here is red when its seam breaks (recorded in the ledger); the old files covering only this area are deleted; CI time per OS after the increment is recorded and not above the time before it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1114 add-subtask "<title>"`; track with `sq task 1114 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rebuild spec, override and vocabulary loading at the load boundary

<!-- sq:subtask:ST1:body -->
Rebuild spec, override and vocabulary loading once on a spec: the merge and splat-ref engine, reserved vocabulary, unknown keys failing closed, corrupt frontmatter type or status at the load boundary, and override-merge conflicts. Failure rows at the boundary, not one row per bundled type.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rebuild the sq check rules as one boundary table per check

<!-- sq:subtask:ST2:body -->
Rebuild the `sq check` rules: one boundary table per check, plus one test that type selection and level (warn or error) apply the same way for every check. This replaces the check by type by level products (2,358 tests in 72 files today), and the refuse-on-write rows that mirror what the check reports become one shared assertion.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Rebuild the CLI spine: -C, schema gate, exit codes and clean --json

<!-- sq:subtask:ST3:body -->
Rebuild the CLI spine: the `-C` property on the boundary layouts the audit names (not every layout by command by direction), the schema gate by grant and direction, exit codes, `--json` with no ANSI under `FORCE_COLOR`, `@handle_errors` clean messages, and the CLI `--json` output goldens. Only what an operator sees; no seam already owned by a service test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Rebuild views, view tags, comments and discussion tests

<!-- sq:subtask:ST4:body -->
Rebuild views, view tags, comments and discussion: placement, expansion at read time, the prose guard, comment splice by line span, header-forging separators and console escaping. Keep the fuzz idempotence and invertibility property, with its row count set by what the audit shows the 1,001 rows actually kill.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Rebuild items, sub-entities, refs and roster lifecycle service tests

<!-- sq:subtask:ST5:body -->
Rebuild items, sub-entities, refs, retype, rename, the board and the roster lifecycle services: set-membership cardinality and liveness (REV-706), enum identity in retype, and the config-integrity gate with `--unlink` leaving the file byte-identical and `--force` never overriding a clause. What reactivation and retirement write to generated files is the backend area's.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Prove engine, services and CLI parity and delete their old files

<!-- sq:subtask:ST6:body -->
Apply each entry's recorded break for this area in a scratch worktree, show the listed old tests and the new owner both red, record it in the ledger, then delete the old files this area alone covers in one reviewed commit. Record CI time per OS after the increment.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:45Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: -C differential now 477 rows, full paths for the check files, CLI --json goldens owned here, reactivation and retirement effects on generated files left to TASK-1115; now depends on TASK-1113. Moved to Ready.
<!-- sq:discussion:end -->
