---
id: TASK-354
sequence_id: 354
type: task
title: Vulture ignore-names reconcile + full-suite/golden/lint verification
status: Done
parent: FEAT-212
author: tech-lead
refs:
- TASK-351:depends-on
- TASK-353:depends-on
created_at: '2026-07-09T21:31:33Z'
updated_at: '2026-07-10T00:25:22Z'
---
<!-- sq:body -->
Closeout: reconcile the vulture ignore_names against the retired CLI dispatch, and run the authoritative full-suite/golden/lint gates for FEAT-212 (AC4/AC5). No product-source change beyond pyproject config.

## Scope

The per-kind service wrappers survive as delegators (TASK-351) but the CLI's per-kind getattr dispatch is gone (TASK-353). Update the vulture [tool.vulture].ignore_names block in pyproject.toml accordingly: the list_stories/list_subtasks/list_findings/get_subtask/get_story/get_finding/set_*_body entries were justified by CLI getattr dispatch, which is now stale. Reconcile: if the wrappers are now referenced only from tests (vulture scans src/squads only), keep the entries but correct the comment to 'test-only public service API'; if TASK-351 dropped any wrapper, remove its entry. Add ignore_names for any NEW generic public methods only if vulture flags them and they are genuinely reached dynamically (prefer a real static reference over a suppression).

Run vulture and confirm near-pure signal (no genuinely-dead symbol left un-triaged).

Run the authoritative gates once, redirected to a file per CLAUDE.md (pyright, then ruff check, then ruff format --check, then the full test suite). Confirm AC4 (built-in behaviour byte-identical, all prior tests green incl. the F1 golden) and AC5 (sq workflow lint catches a custom-kind machine referencing an out-of-vocabulary status).

## Files owned

- pyproject.toml ([tool.vulture].ignore_names reconcile)

## Acceptance

- vulture reports no untriaged dead symbol from this feature; ignore_names comments are accurate.

- pyright + ruff clean; full suite green; sq workflow lint AC5 demonstrated.

## Depends on

TASK-351 + TASK-353 (wrappers/dispatch settled). Runs last.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 354 add-subtask "<title>"`; track with `sq task 354 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T00:15:30Z] Elias Python:
  - Reconciled [tool.vulture].ignore_names: kept list_stories/list_subtasks/list_findings/get_subtask/get_story/set_subtask_body/set_story_body (test-only public service API, comment corrected — CLI getattr dispatch is gone per TASK-353).
  - Dropped get_finding and set_finding_body from ignore_names — both are genuinely 0-ref (no src, no test call sites), not just test-only; leaving them flagged rather than re-hiding them.
  - Added entries for add_story/add_subtask/add_finding/set_subtask_status/set_story_status/set_subtask_done/set_subtask_assignee/update_subtask/update_finding — confirmed test-only (0 src refs, nonzero test refs).
  - update_story is ALSO genuinely 0-ref (src+tests) — left unsuppressed, vulture flags it, not silenced.
  - vulture: 14 flagged (11 pre-existing test-only/dynamic debt from TASK-333, unchanged, out of this task's scope) + the 3 newly-surfaced genuinely-dead symbols above (get_finding, set_finding_body, update_story) — near-pure signal, nothing untriaged.
  - AC5 demonstrated: added test_lint_reports_custom_subentity_kind_completion_off_vocab + test_cli_workflow_lint_exits_1_on_subentity_completion_off_vocab in tests/test_workflow_lint.py — a custom 'action' subentity kind with completion='Verified' (a real global status, unreachable on action's own machine) fails sq workflow lint closed via _check_completion_status.
  - Fast gates green: pyright/ruff check/ruff format --check clean; targeted workflow+ref-hygiene tests green. Full suite NOT run here per instructions — leaving that to the main loop's FEAT-212 closeout gate. Tree left dirty for review (pyproject.toml, tests/test_workflow_lint.py, + this task's own status/comment bookkeeping).
- [2026-07-10T00:18:23Z] Elias Python:
  - Coordinator follow-up: deleted the 3 genuinely-dead per-kind delegators from src/squads/_services/_subentities.py — set_finding_body (:220), update_story (:225), get_finding (:303). Zero call sites anywhere, confirmed again post-delete via grep.
  - Confirmed pyproject.toml [tool.vulture].ignore_names never listed the three (I never added them) — nothing to remove there.
  - Re-ran uv run vulture: now exactly the 11 pre-existing TASK-333-debt flags, the 3 new FEAT-212 flags are gone. Left those 11 untouched (documented, out of scope).
  - Re-ran fast gates: pyright clean, ruff check clean, ruff format --check clean (167 files formatted).
  - Re-ran targeted sub-entity/service/CLI/workflow tests + test_squad_ref_hygiene.py: all green (one unrelated pre-existing Windows-only skip in test_cli.py). Full suite not run (main loop owns it).
  - Tree still dirty for review, no commit: pyproject.toml, src/squads/_services/_subentities.py, tests/test_workflow_lint.py + this task's own bookkeeping.
- [2026-07-10T00:23:49Z] Paul Reviewer:
  - Reviewed uncommitted TASK-354 diff (independent, on committed TASK-361). VERDICT: CHANGES-REQUESTED — one trivial, in-scope miss on the task's sole deliverable (vulture reconcile). Everything else is clean: the 3 deletions are safe, the wrapper reconcile is honest, the AC5 tests are genuine, gates clean, full suite green (exit 0, 0 failures).
  - F1 (the blocker, LOW impact / trivial fix): vulture reconcile is INCOMPLETE. The task AC is 'no untriaged dead symbol FROM THIS FEATURE', but 4 new flags from TASK-353's dynamic-signature builder are untriaged: _cli/_items.py:583/584 (_add.__doc__/__signature__) and :693/694 (_update.__doc__/__signature__). Confirmed NEW — absent before FEAT-212 (git show pre-feature _items.py: 0 hits). They're false positives (Typer consumes both), so per CLAUDE.md vulture policy add '__signature__' (and '__doc__') to [tool.vulture].ignore_names with a one-line reason. NB coordinator: your premise that all 11 flags are pre-existing TASK-333 debt is off — 4 are FEAT-212's; the other 7 (create_empty/get_playbook_spec/invalidate_cache/folder_for/type_for_id/link/list_operators) are the genuine out-of-scope pre-existing debt.
  - Deletions SAFE: set_finding_body / update_story / get_finding have ZERO refs in src AND tests (grep-confirmed); TASK-353 retired the getattr dispatch so no dynamic caller. Reconcile HONEST: all 16 kept ignore_names entries are genuinely test-only — each has 0 src callers (the lone add_finding 'src hit' is a comment/docstring mention, not a call) and >=1 test caller (add_story 9, add_subtask 11, add_finding 7, ... update_finding 1), so nothing genuinely-dead is silenced and nothing live is wrongly flagged.
  - AC5 tests GENUINE (not stubs): both declare a custom incident/action kind with completion='Verified' (a real global status, but off the action machine's own vocab) and assert (a) lint_workflow_spec yields an error containing action+Verified+'not a reachable' and (b) sq workflow lint exits 1 with 'action'+'1 error'. AC4 holistic: full suite + all 6 regenerated goldens green — built-in behaviour byte-identical across 349-361. Ticket IDs: only the test docstring cites ADR-000348 §6 / FEAT-000212 AC5 (provenance, matches the repo's established test-docstring convention e.g. test_workflow_lint's ADR-000232 refs); no IDs in pyproject/service source.
- [2026-07-10T00:24:52Z] Elias Python:
  - Coordinator follow-up: added __signature__/__doc__ to [tool.vulture].ignore_names (one-line reason: Typer reads both off the dynamically-built generic sub-entity command functions in _cli/_items.py).
  - Re-ran uv run vulture: now exactly the 7 genuinely pre-existing flags (create_empty, get_playbook_spec, invalidate_cache, folder_for, type_for_id, link, list_operators) — no FEAT-212 flags left.
  - uv run ruff check . — all checks passed. pyproject-config-only change, no source touched.
- [2026-07-10T00:25:21Z] Catherine Manager:
  - Reviewer-approved (after the __signature__/__doc__ triage fix); full suite green; vulture now reports only the 7 pre-existing TASK-333-debt items, no FEAT-212 flags. AC4 (byte-identical built-ins) and AC5 (lint fails closed on off-vocab custom-kind completion) confirmed. Landing — closes FEAT-212.
<!-- sq:discussion:end -->
