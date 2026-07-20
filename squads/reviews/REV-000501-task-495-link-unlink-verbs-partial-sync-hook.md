---
id: REV-501
sequence_id: 501
type: review
title: 'TASK-495: link/unlink verbs + partial-sync hook'
status: Approved
author: reviewer
refs:
- TASK-495:addresses
subentities:
- local_id: F1
  title: 'Test gap: multi-role scoping + unlink selectivity unproven'
  status: Fixed
  severity: low
created_at: '2026-07-20T10:16:06Z'
updated_at: '2026-07-20T10:22:18Z'
---
<!-- sq:body -->
Independent review of the UNSTAGED src/squads Python changes for TASK-495 (link-role/unlink-role verbs + partial-sync hook). Staged TASK-493/494 and clients/vscode excluded per scope.

Verdict: APPROVE. Implementation is correct and matches ADR-492 Pillar 3. Gates clean on the changed files (pyright, ruff check, ruff format); 15 targeted tests pass.

Hook isolation (_resync_role_skills): confirmed only the affected role is touched — loads that one role, resolves via resolved_skills_for_role, refreshes {slug: resolved} extra.skills, generates that role's pointer, regens that role's body. Other roles left byte-untouched (proven by test_only_the_linked_roles_pointer_and_body_are_touched comparing read_bytes). Full sync() still works: _refresh_role_skills_extra/_regen_role_body moved from MaintenanceMixin to ServiceCore and are inherited by both MaintenanceMixin (sync) and RefsMixin (hook) — no broken cross-mixin call; the hook's BackendContext mirrors sync()'s role_ctx exactly.

unlink precision: the filter removes only refs where kind=='scopes' AND ref_id_matches the role — other ref kinds to the same role and scopes edges to other roles survive. rm_ref was correctly NOT reused (it is kind-agnostic and would over-remove). Idempotent; non-role target raises SquadsError (defended at both CLI resolve_agent_addr and service type check).

Bug fix (drop stale-index comparison in _refresh_role_skills_extra): CORRECT. The old early-return compared resolved against item.extra[skills], which is loaded from the rebuildable .squads.json index; these methods write only .md frontmatter (never the index), so a second same-session resync (link then unlink) would compare against the stale index value and wrongly no-op, leaving the .md stale. Always-write is right. Non-thrashing: no updated_at bump in this path and to_frontmatter_dict is deterministic, so unchanged content re-serializes byte-identically; _regen_role_body was already unconditional, so sync's write pattern is unchanged in kind.

Parity: test_a_raw_ref_add_writes_the_edge_but_leaves_the_pointer_stale_until_sync proves the raw ref add skips the hook (pointer stale until sync) while the verb updates immediately. Scope clean: no SCHEMA_VERSION/migration, no clients/vscode, no ticket IDs in source/tests.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 501 add-finding "…" --severity medium`; track with `sq review 501 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Test gap: multi-role scoping + unlink selectivity unproven |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Test gap: multi-role scoping + unlink selectivity unproven

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Implementation is correct by inspection, but two acceptance-named cases lack a direct assertion. (1) One skill scoped to SEVERAL roles at once — the ADR-492 release-runbook case (manager/devops/tech-writer) and the task's own test plan — is not exercised at the verb level; the resolver test (tests/service/test_role_skill_scope_resolution.py) only covers one role per skill. (2) unlink_role selectivity (src/squads/_services/_refs.py:378-386): the filter correctly keeps a non-'scopes' edge to the same role and 'scopes' edges to OTHER roles, but no test asserts either survives an unlink — the only unlink tests remove the sole edge. Low severity: the code paths are independent-per-role and the filter predicate is exact, so risk is low; adding a one-skill-to-two-roles link test and a mixed-edge unlink test would close the gap against stated acceptance.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:17:09Z] Paul Reviewer:
  - @manager REV-501 verdict: APPROVE. TASK-495 (link/unlink verbs + partial-sync hook) is correct and matches ADR-492 Pillar 3. 1 finding, all LOW: F1 is a test-coverage gap (multi-role scoping + unlink selectivity unproven) — advisory, not a blocker; no code defects. Gates clean on changed files; 15 targeted tests pass. Hook isolation and the 'always write' bug fix both verified correct. No edits made.
- [2026-07-20T10:22:18Z] Elias Python:
  - @manager F1 addressed: added regression tests for both gaps (test-only, no source changes).
  - Multi-role: test_one_skill_scoped_to_several_roles_at_once_preloads_all_and_only_those (tests/service/test_skill_role_scope_link_unlink_hook.py) + test_link_role_run_for_several_roles_preloads_all_and_only_those (tests/cli/test_skill_role_scoping_verbs.py) — release-runbook scoped to manager+devops+tech-writer via the verb, asserted in resolver/pointer/body for all three, and absent from python-dev's.
  - Unlink selectivity: test_unlink_leaves_a_different_kind_edge_to_the_same_role_intact + test_unlink_leaves_a_scopes_edge_to_a_different_role_intact (tests/service/test_skill_role_scope_link_unlink_hook.py).
  - All passed on first run (QA's confirmation held) — no defect, pure coverage gap as scoped. Gates: pyright + ruff clean, tests/meta clean, tests -k 'scope or role or link or unlink' -> 179 passed.
<!-- sq:discussion:end -->
