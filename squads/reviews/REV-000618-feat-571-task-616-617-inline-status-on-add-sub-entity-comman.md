---
id: REV-618
sequence_id: 618
type: review
title: 'FEAT-571 / TASK-616-617: inline --status on add-* sub-entity commands, kind-scoped
  validation'
status: Approved
author: reviewer
created_at: '2026-07-22T18:21:55Z'
updated_at: '2026-07-22T18:22:56Z'
---
<!-- sq:body -->
Independent review of the inline `--status` addition to the `add-*` sub-entity commands (add-story/add-subtask/add-finding), scoped to the uncommitted diff. Verifies scope-validation correctness, additive/no-break behaviour, shared-builder parity, and test rigor.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 618 add-finding "…" --severity medium`; track with `sq review 618 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T18:22:15Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approved. No findings.
  - Gate: pyright 0 errors, ruff check clean, ruff format clean (355 files). Targeted pytest green — new service test (test_add_subentity_seeds_status_inline), new CLI test (test_add_subentity_status_flag_cli), extended custom-kind test, the -k subentity/subtask/story/finding slice, and tests/meta (guard clean). Full suite ran green by manager; not re-run here.
  - Focus #1 (cross-lifecycle rejection) — CONFIRMED WORKING. Two-layer check is sound: CLI parse_status validates the global vocabulary, then _resolve_add_status membership-checks against subentity_workflow(kind).states (the kind's OWN lifecycle). A globally-valid-but-out-of-kind status is genuinely rejected with a clean SquadsError (no traceback, exit 1) and no sub-entity is written — proven both directions (InProgress on a finding, WontFix on a story, Blocked on a custom action kind). Membership (not can_transition) is the correct call for creation-seeding: there is no prior state to transition from.
  - Focus #2 (additive) — clean. Flag-less add-* still seeds spec.subentity_initial(kind) unchanged; add-finding --severity and the generic per-field derivation are untouched; --status is purely additive on all three kinds and the service delegators default it to None.
  - Focus #3 (parity/wiring) — the --status keyword is appended once in the shared _register_add builder (no per-kind branching), parsed via parse_status at the CLI edge exactly like _register_update, and threaded add_block → add_story/add_subtask/add_finding. subentity_workflow/subentity_initial are the right accessors.
  - Focus #4 (test rigor) — assertions are strong: non-initial seed on all three kinds + custom kind, frontmatter round-trip, severity-default preserved under --status, additive flag-less case, and cross-lifecycle rejection in both directions asserting exit 1 + no-traceback + empty listing.
  - Conventions verified: no ticket IDs in src/tests, no 'meta' wording, no SCHEMA_VERSION bump (the diff's SCHEMA_VERSION hits are all pre-existing .squads.json index titles), PEP-695/SquadsError-family respected, and no new module-level constants in _subentities.py (mutable-state guard allowlist unchanged — dev's report confirmed).
- [2026-07-22T18:22:54Z] Catherine Manager:
  - Manager verification: two-layer status validation confirmed — CLI parse_status (global) + _resolve_add_status membership against the kind's own subentity_workflow states; cross-lifecycle seed rejected cleanly at both CLI and service entry points, no sub-entity written. Additive, parity across all three add-* kinds, tests rigorous. Approving.
<!-- sq:discussion:end -->
