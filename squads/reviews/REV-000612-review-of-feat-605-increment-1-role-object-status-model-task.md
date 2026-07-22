---
id: REV-612
sequence_id: 612
type: review
title: 'Review of FEAT-605 increment 1: role-object status model (TASK-606..610)'
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: Fallback role existence not validated at load; role_for KeyErrors if pending
    absent
  status: Verified
  severity: medium
created_at: '2026-07-22T16:31:32Z'
updated_at: '2026-07-22T16:37:10Z'
---
<!-- sq:body -->
Independent review of FEAT-605 increment 1 (TASK-606..610): ADR-604's role-object status model — status `role` becomes a first-class object carrying settled/hidden/color; terminal/is_open dropped and derived from the referenced role.

Scope: RoleSpec + role_for/is_open/terminal_set/hidden_by_default derivation, the Plane-1 role validation, default_workflow.toml role catalog, sq workflow roles --json + statuses-catalog terminal drop, goldens, and the ~30 test-fixture migrations. CLI is_open field-drop across list/tree/mine is TASK-611 (Draft) — out of this increment.

Gate (independent): pyright 0 errors, ruff check clean, ruff format clean. Targeted pytest over all scrutinised files green (66 tests). Full suite run by the manager (not re-run here).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 612 add-finding "…" --severity medium`; track with `sq review 612 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Fallback role existence not validated at load; role_for KeyErrors if pending absent |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Fallback role existence not validated at load; role_for KeyErrors if pending absent

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
role_for() resolves a role-less status via a direct index: self.roles[self.statuses[status].role or FALLBACK_ROLE_NAME] — a KeyError if 'pending' is not declared. _check_role_references only validates EXPLICIT status.role references; it never asserts the fallback role (FALLBACK_ROLE_NAME) exists. So _validate does NOT guarantee the implicit fallback resolves — yet role_for's docstring claims 'validate guarantees every referenced role resolves', which is false for the fallback.

Reachability: the manager's 'adopter override without pending -> KeyError' framing is REFUTED for the supported path — _merge_override starts merged_roles = dict(bundled.roles), so an additive override can never remove bundled 'pending'; every loaded spec keeps it. The gap is only reachable by a directly-constructed WorkflowSpec (or a future full-replacement override) that has a role-less status and omits 'pending'. Bundled spec unaffected.

Why it still matters: ADR-604 §1 frames absent-role -> bundled pending as a guarantee, and Plane-1 is meant to fail closed at LOAD, not KeyError at runtime. Fix is ~2 lines in _check_role_references: if any status has role=None (or unconditionally), require FALLBACK_ROLE_NAME in roles -> append a SquadsError. Also correct role_for's docstring. Makes the stated invariant real and future-proofs a replacement-override path.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-22T16:35:10Z] Elias Python:
  - Fixed: _check_role_references now errors if FALLBACK_ROLE_NAME ('pending') isn't declared in roles; role_for's docstring corrected to state _validate guarantees both explicit-role resolution and the fallback role's presence. One hand-built fixture (test_type_spec_capability_flags.py's parent_hint test) needed a 'pending' role added to its custom roles dict — everything else already carried it via dict(base.roles). Gate green (pyright/ruff/format); targeted workflow/validation tests green.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:32:11Z] Paul Reviewer:
  - Lead #1 (fallback fail-closed): CONFIRMED as a code/contract gap, REFUTED as an adopter-reachable crash. Additive merge keeps bundled 'pending' in every loaded spec, so no adopter override path KeyErrors. Filed F1 (Medium) for the latent gap + false role_for docstring.
  - Lead #2 (fixture integrity): CLEAN. Sampled the reachability-lint floor (terminal=True->settled 'done', False->'pending' — faithful), semantic-role, artifact golden-lock, and terminal-status CLI diffs. No weakened assertions; the deleted 'no other status gained a role' test is genuinely obsolete under the new model. Goldens (workflow_statuses drop terminal + populate role; new workflow_roles) faithfully match the ADR §2 table and are consumed by test_json_output_shape.
  - Lead #3 (behaviour-preservation): CONFIRMED. settled is byte-identical to old terminal for all 23 statuses; hidden matches the ADR table. Accepted/Published stay settled-but-visible (in_force), Done/Verified/Approved hide (done), Rejected->retired hides (deliberate). tree_view's candidate gate moved is_open->hidden_by_default — the intended in-force/records visibility contract, tested. No unexpected flips.
  - Lead #4 (single derivation site): CONFIRMED. is_open/terminal_set/hidden_by_default + services (_roster/_refs/_collab) + template all route through role_for/spec.is_open. No lingering .terminal reads or hardcoded role/terminal sets. _main.py still EMITS is_open (now spec.is_open-derived) — that field-drop is TASK-611 (Draft), correctly out of this increment.
  - Conventions: clean — no ticket IDs, no 'meta', no bare (non-PEP695) type aliases in the new code; SquadsError-family used; no SCHEMA_VERSION bump (spec-format + --json-contract only). Gate green: pyright/ruff/format clean, targeted tests pass.
- [2026-07-22T16:32:19Z] Paul Reviewer:
  - Verdict: ChangesRequested — one Medium finding (F1). Everything else is clean and faithful to ADR-604. F1 is a latent Plane-1 fail-closed gap (not adopter-reachable today) plus a false docstring guarantee; ~2-line fix in _check_role_references + a docstring correction closes it. @tech-lead / @python-dev.
- [2026-07-22T16:35:25Z] Elias Python:
  - F1 fixed (see finding comment) — back in InReview for re-verification.
- [2026-07-22T16:37:09Z] Paul Reviewer:
  - F1 verified: fallback-role load check added to _check_role_references (fails closed if 'pending' undeclared); role_for docstring corrected. Full suite green.
<!-- sq:discussion:end -->
