---
id: TASK-000083
sequence_id: 83
type: task
title: Document and test the CLI exit-code table
status: Done
parent: FEAT-000015
author: tech-lead
priority: high
refs:
- REV-000092:addresses
subentities:
- local_id: ST1
  title: Documented exit-code table asserted in tests
  status: Done
  story: US2
created_at: '2026-06-12T15:27:48Z'
updated_at: '2026-06-12T21:07:53Z'
---
<!-- sq:body -->
## Goal
Document the CLI exit-code table and assert every code in tests (US2), so CI can gate on commands like `sq check`.

## Current exit-code reality (audited)
- **0** — success (implicit on normal return).
- **1** — `SquadsError` via `@handle_errors` (_common.py ~391-400); also the schema-version mismatch hard-stop in `require_current_schema` (_common.py ~425-450); also the missing-verb dispatch error in `AddressDispatchGroup` (_common.py ~617).
- **2** — invalid `--at` timestamp format (_common.py:61), and Typer/Click's own usage errors (unknown option, missing required arg).
- **3** — `check` when any error-level issue is found (see decision below).

## Decision — settled (2026-06-12, op-pierre)
`check` failures get a **distinct exit code 3**; **1 stays the generic squads runtime error code**. The earlier open question (distinct code vs generic 1) is resolved — no open question remains.

The frozen table:
- **0** — success
- **1** — squads runtime error (incl. schema mismatch)
- **2** — usage error (bad `--at`, Typer/Click usage errors)
- **3** — `check` found error-level issues

This is frozen contract material (FEAT-000013 deferral).

## Work
1. **Implement** the distinct exit code: `check` (_main.py:458) must `raise typer.Exit(3)` (was 1) when any error-level issue is found. Keep the schema-mismatch and `SquadsError` paths at 1.
2. **Document** the table. Where the table lives: a section in the stability docs is FEAT-000013's job — here, document it inline (command help / a short `docs/` note) and link. Coordinate so we don't double-own it.
3. **Tests**: assert each code path — exit 0 on a clean `check`, **exit 3 on `check` with a seeded error-level issue**, exit 1 on a `SquadsError` (e.g. unknown id), exit 1 on schema mismatch, exit 2 on a bad `--at`. Use `CliRunner`; assert `r.exit_code`.

## Done when
- The exit-code table (0/1/2/3 as above) is documented and linked from the CLI surface.
- `check` raises exit 3 on error-level issues.
- A test asserts each documented code, including exit 3 for check failures.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 83 add-subtask "<title>"`; track with `sq task 83 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Documented exit-code table asserted in tests | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Documented exit-code table asserted in tests

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a CI pipeline author, I want documented exit codes, so that I can gate builds on commands like sq check
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T20:42:44Z] Elias Python:
  - Note: the check exit-3 implementation (table path) landed early via REV-000086 F2. The table path of sq check now raises typer.Exit(3) on any error-level issues, matching the --json path. The existing test test_check_cli_flags_index_item_with_no_file was updated to assert exit 3. TASK-000083's remaining scope is: document the exit-code table (0/1/3) and add comprehensive exit-code tests — the implementation itself is already done.
- [2026-06-12T21:00:12Z] Elias Python:
  - Implementation complete. Here is what landed:
  - **Code**: Updated the `check` command docstring in `src/squads/_cli/_main.py` to state the exit-0 / exit-3 contract and point at `sq docs faq`.
  - **Docs**: Added an exit-code table FAQ entry to `docs/faq.md` covering codes 0, 1, 2, and 3 with a forward-link to FEAT-000013 for the formal stability doc. The entry also notes that warnings-only results exit 0.
  - **Tests** (8 new in `tests/test_cli.py`, section TASK-000083): exit 0 on a clean squad, exit 0 on check with no issues, exit 0 on check with warnings only, exit 1 on SquadsError (unknown ID), exit 1 on schema-version mismatch, exit 2 on invalid --at timestamp, exit 3 on check with error-level issue (table path), exit 3 on check --json with error-level issue.
  - Suite: 395 passed, 1 skipped. pyright clean, ruff clean. @reviewer ready for review.
- [2026-06-12T21:03:38Z] Paul Reviewer:
  - Reviewed under REV-000092 — **Approved**, no findings.
  - Contract verified end-to-end: exit 0 (success / clean check / warnings-only), 1 (SquadsError + schema mismatch), 2 (bad --at), 3 (sq check error-level, both table and --json paths). The key invariant — exit 3 fires for error-level issues but NOT warnings-only — is directly proven by test_exit_code_0_check_warnings_only (asserts a warn is present yet exit_code == 0).
  - Docs accurate: FAQ four-row table matches the frozen contract incl. the warnings-exit-0 note and FEAT-000013 forward-link; the docstring's `sq docs faq` cross-ref resolves (verified live).
  - Suite green locally: uv run pytest → 395 passed, 1 skipped; pyright 0 errors; ruff check + format clean. The 8 new tests pass in isolation.
  - Non-blocking nicety (not a finding): code 2's Typer/Click usage-error path (unknown option/missing arg) is documented but only the --at path is asserted — acceptable, since Typer owns that exit-2 guarantee. @tech-lead this task is good to move to Done.
<!-- sq:discussion:end -->
