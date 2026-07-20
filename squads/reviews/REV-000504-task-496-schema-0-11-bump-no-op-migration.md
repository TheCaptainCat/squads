---
id: REV-504
sequence_id: 504
type: review
title: 'TASK-496: schema 0.11 bump + no-op migration'
status: Approved
author: reviewer
refs:
- TASK-496:addresses
created_at: '2026-07-20T10:47:06Z'
updated_at: '2026-07-20T10:47:42Z'
---
<!-- sq:body -->
Independent review of TASK-496 (schema 0.10->0.11 bump + no-op stamp migration). Reviewed the unstaged Python changes only; staged TASK-493/494/495 and clients/vscode excluded from scope.



Verdict: APPROVED — no findings. The migration is a correct schema-stamp-only no-op that still gates pre-0.11 clients, and the US5 acceptance test genuinely proves an authored custom-skill body + scopes edges + resolved role-skill sets survive the upgrade unchanged.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 504 add-finding "…" --severity medium`; track with `sq review 504 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:47:42Z] Paul Reviewer:
  - @manager Review complete for TASK-496 (schema 0.11 bump + no-op migration). Verdict: APPROVED, 0 findings.
  - Migration correctness: verified. The 0.10->0.11 runner returns 0 and touches no files (file-snapshot test proves it); MANUAL empty; registry entry correct (from_schema 0.10, to_schema 0.11, ordered last, _wrap_sync-lifted). run_pending_migrations applies it via schema_tuple comparison, then repair + stamp 0.11; the v0.3 chain test confirms the whole chain reaches 0.11. Hard-stop uses schema_tuple (never raw string <), yielding a clean 'run sq migrate up' + exit 1 — proven by a CLI test.
  - US5 acceptance: the integration test is genuine, not hollow — it authors a custom-skill body + scopes edges to manager & tech-writer (with a devops negative control), snapshots body/scope-refs/resolved-skill-sets, restamps to 0.10, runs the real migration path, then asserts the body is byte-identical, scope refs identical, all three resolved skill sets unchanged, and sq check clean. v0_11 corpus fixture is byte-identical to v0_10 bar the stamp and is registered in the parametrize list.
  - Stale-fix sweep verified: reflog golden bump is required (test asserts == SCHEMA_VERSION); chain-test assertions correctly extended; the memory-skill test's '>= 0.10' is appropriate (exact-current pin lives in the chain test, so no coverage lost). Scope clean: no pyproject/manifest/vscode changes, no ticket IDs in source/tests.
<!-- sq:discussion:end -->
