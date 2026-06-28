---
id: REV-000230
sequence_id: 230
type: review
title: 'FEAT-220 review: playbook externalized to bundled spec'
status: Approved
author: reviewer
refs:
- FEAT-000220
- TASK-000227
- TASK-000228
- TASK-000229
subentities:
- local_id: F1
  title: Loader bypasses extra='forbid' — typo'd TOML keys silently dropped
  status: Open
  severity: low
- local_id: F2
  title: Layer-B snapshot comment says 'verbatim from playbook.toml' — misleading
    provenance
  status: Open
  severity: low
created_at: '2026-06-26T09:19:18Z'
updated_at: '2026-06-26T09:27:29Z'
---
<!-- sq:body -->
## Scope
Independent review of FEAT-000220 — externalizing the team playbook into a bundled `src/squads/_interactions/playbook.toml` loaded as a validated `PlaybookSpec` (ADR-000226), enums-intact era. Third of the externalization trio (after FEAT-207 workflow / FEAT-219 role-catalog). Review-only; no code modified.

## What I verified independently (against pre-FEAT-220 HEAD)
HEAD still carries the original `src/squads/_interactions.py` (the deletion is unstaged), so I anchored everything to it rather than to the new artifacts.

1. **TOML fidelity to HEAD (Layer A, the real concern).** Extracted HEAD's original `PLAYBOOK` literal into a standalone module and compared it field-for-field against the live TOML-loaded spec: **0 structural mismatches** across all 7 work types (overview/lifecycle/commands + every ordered role guide's slug/enter/do/handoff/watch).
2. **Rendered-output fidelity (Layer B).** Rendered every `sq-<type>` skill from HEAD's PLAYBOOK and from the live TOML spec through the real `agents/item_skill.md.j2` path with a dev-bearing roster: **0 byte mismatches**. Confirms the externalization is behavior-preserving at the output layer.
3. **Test snapshot non-circularity (the flagged concern).** The `_SNAPSHOT` literal in `tests/test_playbook.py` is a frozen Python dict embedded in the test file — it does NOT read `playbook.toml` at runtime. I compared it directly against HEAD's PLAYBOOK: **0 mismatches**. So although its comment says 'verbatim from playbook.toml', the snapshot content is byte-identical to pre-FEAT-220 HEAD (because TOML==HEAD, proven in #1). The Layer-B test compares snapshot-render (expected) vs TOML-shim-render (actual) — both sides are real, the snapshot is an independent frozen literal, so a future TOML drift from HEAD WOULD be caught. **Verdict: the test is NOT circular and does not need re-anchoring.** See finding F1 for a documentation nit on the misleading comment.
4. **Loader & fail-closed validation.** All five rules fire and raise `SquadsError`: unknown item-type key, unknown role slug (`*dev` correctly exempt), meta-type entry rejected, missing work-type rejected, empty overview/lifecycle rejected. Models carry `extra='forbid'`, frozen. See F2 for a defense-in-depth gap.
5. **Rewire fidelity.** `PLAYBOOK`/`managed_item_types()`/`item_skill_name()`/`skills_for_role()`/`SKILL_DESCRIPTIONS` all route through the loaded spec; `CREATE_LANES`/`LANED_TYPES` stayed in Python; backend `_write_item_skills` is byte-identical to HEAD and still reads the `PLAYBOOK` shim. `get_catalog()` added cleanly to `_roles/_catalog.py`.
6. **Invariants.** No import cycle (`_roles` does not import `_interactions`); no `from __future__`; no `is`/`is not` identity landmines (grep hits were all prose); pyright + ruff check + ruff format all clean on the new package and test; full suite green (exit 0, one harmless skip — the wheel-build test when uv path differs).

## Conclusion
Behavior-preserving, golden-locked at both layers, validation fail-closed. Two low-severity findings (one doc nit, one defense-in-depth gap that matches the sibling FEAT-219 loader pattern). No blocking issues.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 230 add-finding "…" --severity high`; track with `sq review 230 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Loader bypasses extra='forbid' — typo'd TOML keys silently dropped |
| F2 | 🟢 low | Open |  | Layer-B snapshot comment says 'verbatim from playbook.toml' — misleading provenance |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Loader bypasses extra='forbid' — typo'd TOML keys silently dropped

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**File:** `src/squads/_interactions/_loader.py` — `_parse_role_guide` (lines 101-112) and `_build_spec` (lines 70-82).

**Issue.** The models carry `model_config = ConfigDict(extra='forbid')`, but the loader constructs them by cherry-picking named keys (`slug=str(data['slug'])`, `enter=[... for s in data.get('enter', [])]`, etc.) instead of passing the raw TOML table through pydantic. So a typo'd TOML key never reaches the `extra='forbid'` gate — it is silently dropped.

**Reproduced** (independent probe):
- A role-guide table with `doo = [...]` (typo of `do`) and `entr = [...]` (typo of `enter`) loads with no error; the typo'd entries are lost (`do`/`enter` come back without them).
- A type entry with `commandz = [...]` (typo of `commands`) loads with no error; the value is dropped.

**Why it matters.** TASK-000227 explicitly asked for this: 'Apply extra=forbid on every model from the start — this is the FEAT-219 nit lesson; a typo'd TOML key must error, not be silently dropped.' The models satisfy the letter of that, but the loader defeats it in practice for hand-edited TOML.

**Severity rationale — low.** Not a current bug: the *bundled* TOML is correct (Layer-A/B golden + my HEAD comparison prove byte-fidelity), and the golden lock catches any drift in the shipped file. It only bites future hand-edits — which is exactly the FEAT-210 custom-type scenario this work is meant to unblock, so it is worth closing eventually. Also note this **matches the existing FEAT-219 `_roles/_loader.py` pattern** (same hand-mapped style, same gap) — so it is a pattern-wide limitation, not a FEAT-220 regression. Consistency with the siblings is a fair reason to defer.

**Recommendation (non-blocking).** Either route the raw dict through the model (`RoleGuideSpec.model_validate(data)` / `ItemPlaybookSpec.model_validate(...)`) so `extra='forbid'` actually fires, or accept the gap consciously and align all three loaders (207/219/220) in a follow-up. Do not block FEAT-220 on it.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Layer-B snapshot comment says 'verbatim from playbook.toml' — misleading provenance

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**File:** `tests/test_playbook.py` line 26 — `# ruff: noqa: E501  — snapshot strings are verbatim from playbook.toml; wrapping obscures diffs.`

**Issue.** The comment frames `_SNAPSHOT` as derived FROM `playbook.toml`. As a HEAD-characterization regression gate, the snapshot's protective value comes from being an *independent* frozen copy of pre-FEAT-220 behavior, not a copy of the very artifact it guards. If a future reader believes the snapshot tracks the TOML, they might 'fix a failing test' by re-copying drifted TOML into the snapshot — defeating the gate.

**Assessment — not actually circular.** I verified `_SNAPSHOT` is byte-identical to HEAD's original `PLAYBOOK` literal (0 mismatches, independent probe). Because TOML==HEAD (proven), 'verbatim from TOML' and 'verbatim from HEAD' are the same content here, and the snapshot is a real frozen Python literal that does NOT read the TOML at runtime. So Layer A and Layer B genuinely would catch a TOML that drifts from HEAD. **The test does NOT need re-anchoring.**

**Severity — low (documentation only).** No behavioral or coverage defect.

**Recommendation (non-blocking nit).** Reword the comment to state the snapshot is frozen from the pre-FEAT-220 `_interactions.py` PLAYBOOK literals (the independent source of truth), and add a one-line note: 'on a Layer-A/B failure, re-derive from the original Python literals, never by copying the current TOML.'
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:20:34Z] Paul Reviewer:
  - **Verdict: APPROVE-WITH-NITS.**
  - FEAT-000220 is behavior-preserving and well-locked. I anchored the review to pre-FEAT-220 HEAD (which still carries the original _interactions.py): the bundled playbook.toml is byte-identical to HEAD's PLAYBOOK both structurally (0 mismatches, all 7 work types, ordered role guides) and at rendered sq-<type> skill output (0 byte mismatches with a dev-bearing roster). Loader fail-closed validation fires on all five rules; *dev exempt; extra='forbid'/frozen on models; rewire faithful; backend byte-identical; no cycle / no future-import / no identity landmines; pyright + ruff + full suite green.
  - On the flagged Layer-B non-circularity concern: the _SNAPSHOT is a frozen Python literal embedded in the test (it does NOT read the TOML at runtime), and I confirmed it is byte-identical to HEAD's original PLAYBOOK. So it IS independently anchored to pre-FEAT-220 HEAD and is a valid regression gate — **it does NOT need re-freezing from HEAD.** The only issue is the misleading 'verbatim from playbook.toml' comment (F2, doc nit).
  - Two LOW findings, neither blocking: F1 — the loader cherry-picks named keys so a typo'd TOML key bypasses extra='forbid' and is silently dropped (defense-in-depth; matches the existing FEAT-219 loader pattern, so a pattern-wide follow-up, not a FEAT-220 regression). F2 — reword the snapshot-provenance comment. Both are safe to land as-is or fix in a quick follow-up.
  - @tech-lead — no changes required; the two nits are your call to fold in now or defer. Not setting task/feature status per review scope.
- [2026-06-26T09:27:27Z] Catherine Manager:
  - F1+F2 verified fixed. F1: _interactions/_loader.py + _roles/_loader.py now route raw TOML through model_validate so extra='forbid' fires — confirmed an unknown key (commandz/entr) fails closed with two new negative tests; bundled playbook.toml/roles.toml still load. Workflow loader correctly left unchanged (its models lack extra='forbid' — separate gap, tracked on FEAT-209/ADR-214). F2: snapshot comment reworded to cite the pre-FEAT-220 PLAYBOOK literals (HEAD) as the source of truth. Non-circularity of Layer-B independently confirmed by reviewer + manager. pyright/ruff clean, 45 targeted tests green. Approving.
<!-- sq:discussion:end -->
