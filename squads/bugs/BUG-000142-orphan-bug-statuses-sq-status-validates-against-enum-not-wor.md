---
id: BUG-142
sequence_id: 142
type: bug
title: Orphan bug statuses; sq status validates against enum not workflow
status: Verified
author: qa
refs:
- FEAT-13
created_at: '2026-06-16T11:55:12Z'
updated_at: '2026-06-16T13:49:37Z'
---
<!-- sq:body -->
**Problem — two defects in the status vocabulary / workflow validation.**

(1) The `Status` enum carries bug-flavored values — `Open`, `Fixed`, `Verified`, `WontFix` — that NO workflow uses. Bugs currently run the generic work-item machine (Draft→Ready→InProgress→InReview→Done/Blocked/Cancelled), so those four are orphan/dead vocabulary.

(2) `sq <type> status <X>` validates X against the global `Status` enum, not against that type's workflow. So an out-of-workflow status is ACCEPTED at set-time and only rejected later by `sq check`. Concretely: BUG-134 was set to `Fixed` (a real enum value), committed, then failed `sq check` (`status 'Fixed' invalid for bug`).

**Decision (op-pierre, 2026-06-16): give bugs a real lifecycle.** Wire `Open → InProgress → Fixed → Verified` (with `WontFix` as a terminal) into the bug workflow so those statuses become valid for bugs, AND tighten `sq status`/set-status to reject any value outside the type's workflow at set-time (not just at `sq check`).

**Scope notes:** the bug workflow + status vocabulary are stability-contract surface that freezes at 1.0 (FEAT-13), so this is pre-1.0 and needs an ADR — including a back-compat/migration plan for existing bugs already in generic-machine statuses (e.g. BUG-134 is now `Done`). Discovered via BUG-134 during FEAT-16 QA.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T12:00:08Z] Robert Architect:
  - Ruling in ADR-143 (Accepted). @python-dev implement per its body.
  - Bug workflow (_BUG): initial=Open. Edges: Open→{InProgress,WontFix,Cancelled}; InProgress→{Fixed,Blocked,WontFix,Cancelled}; Fixed→{Verified,InProgress}; Verified→{InProgress}; Blocked→{InProgress,WontFix,Cancelled}; WontFix→{Open}; Cancelled→{Open}. Terminal-for-scoping: Verified, WontFix, Cancelled (all already in _workflow.TERMINAL — no TERMINAL edit needed). No enum additions; Draft/Ready/InReview/Done/Todo are NOT bug states.
  - Set-time validation: add a membership check in _services/_items.py::_apply_status — reject status not in workflow_for(item.type).states BEFORE the can_transition check and INDEPENDENT of --force (force only relaxes the edge rule, never the vocabulary). New StatusNotInWorkflowError(SquadsError) in _errors.py. Keeps sq check's membership rule as defence-in-depth.
  - Back-compat: bugs on disk are all Done (9 of them) except this one (Draft). Remap via migration on type:bug frontmatter: Done→Verified, Draft→Open, Ready→Open, InReview→Fixed; InProgress/Blocked/Cancelled unchanged. Idempotent. No superset workflow (keeps 1.0 contract clean).
  - Schema/sequencing: needs a bump. FEAT-138 owns 0.3→0.4 (already in the working tree, runner _v0_3_to_v0_4 registered). So THIS migration is 0.4→0.5 and MUST land AFTER FEAT-138 merges — bump SCHEMA_VERSION to 0.5, add _v0_4_to_v0_5.py + registry entry, and add a v0_5 corpus fixture wired into test_migration_corpus._CORPUS_CASES (FEAT-17 rule). Do not collide on _schema.py/_registry.py while FEAT-138 is in flight.
  - FEAT-13 flag: the final bug lifecycle is stability-contract surface freezing at 1.0; it must be recorded in the FEAT-13 doc before freeze. @manager files the deferral comment during the loop.
- [2026-06-16T12:43:46Z] Catherine Manager:
  - Override (op-pierre, 2026-06-16): ADR-143's 0.4→0.5 bump + _v0_4_to_v0_5 migration for the bug-status remap are NOT applied — no new schema version while 0.3 is in development. The existing-bug status remap (Done→Verified, etc.) becomes a one-time in-place data fix on the bug .md files, not a versioned migration. ADR-143's bug-workflow design + set-time validation fix stand.
- [2026-06-16T13:34:27Z] Elias Python:
  - Implementation complete and gate-green. Summary of changes:
  - 1. Bug workflow (_BUG): Added Open→InProgress→Fixed→Verified lifecycle in src/squads/_workflow.py. Initial=Open; terminals: Verified/WontFix/Cancelled (all already in TERMINAL, no edit needed). WontFix and Cancelled both have a re-open edge back to Open. Blocked sits on the active path (InProgress→Blocked→InProgress).
  - 2. Set-time validation: Added vocabulary membership check in _apply_status() in src/squads/_services/_items.py, evaluated BEFORE the transition edge check and INDEPENDENT of --force. New StatusNotInWorkflowError(SquadsError) in src/squads/_errors.py. --force only relaxes the transition edge, never the vocabulary.
  - 3. In-place remap (no migration runner, schema stays 0.3): 9 repo bugs in Done status remapped to Verified via direct frontmatter edit + sq repair. BUG-11/21/22/25/30/56/80/120/134: Done→Verified. BUG-142: Draft→Open→InProgress (via sq with --force). Corpus fixtures (v0_1/v0_2/v0_3) had InProgress bugs which is valid in the new workflow — no changes needed.
  - 4. Test updates: test_retype.py — task→bug now resets status to Open (different workflows, correct semantics); updated test_retype_task_to_bug_resets_status and added test_cli_retype_feat_to_epic_status_carried to prove feature↔epic still carries. Golden files regenerated (bug initial status is now Open, not Draft). New test file tests/test_bug_workflow.py: 16 tests covering workflow unit tests, set-time rejection, --force vocabulary enforcement, full lifecycle, regression reopen.
  - Gate: uv run pytest (all pass), uv run pyright (0 errors), uv run ruff check + format --check (all pass), uv run sq check (no issues). @reviewer please verify. @qa please run the suite and confirm the bug lifecycle behaves end-to-end.
- [2026-06-16T13:49:37Z] Paul Reviewer:
  - APPROVED (REV-145). Independent review complete; fix conforms to ADR-143 with the op-pierre override (schema stays 0.3, no migration runner — 9 bugs remapped Done→Verified in place).
  - Key fix verified empirically: --force no longer bypasses status-vocabulary validation. In a scratch squad, 'sq bug N status Done' AND 'sq bug N status Done --force' are BOTH rejected with StatusNotInWorkflowError (exit 1); 'sq bug N status Verified --force' still succeeds (force relaxes only the edge, never the vocabulary). This closes the exact hole that let BUG-134 reach Fixed. No collateral on other types — task/feature force edge overrides still work.
  - Remap files intact: git diff shows only the status line changed per bug; markers/bodies preserved; 'sq repair' rebuilds the index identically from frontmatter (Invariant 1) and 'sq check' is clean. Goldens reflect bug initial Open; no stray tests/tests/ dir. Gate green: pytest exit 0, pyright 0 errors, ruff clean, SCHEMA_VERSION still 0.3. Moving BUG-142 → Verified.
<!-- sq:discussion:end -->
