---
id: REV-000236
sequence_id: 236
type: review
title: TASK-233 characterization completeness gate (FEAT-208)
status: Approved
author: qa
refs:
- FEAT-000208
- TASK-000233
subentities:
- local_id: F1
  title: operator self-author bypass not characterized in spine tests
  status: Open
  severity: medium
- local_id: F2
  title: workload exclusion of role/skill items not characterized
  status: Open
  severity: low
created_at: '2026-06-26T10:21:15Z'
updated_at: '2026-06-26T10:26:17Z'
---
<!-- sq:body -->
## Scope

Completeness gate for TASK-000233's 39 characterization tests in `tests/test_spine_characterization.py`. These tests are the entire safety net for TASK-234 (reify checks to capability flags) and TASK-235 (widen Item.type/status to str). Any uncharacterized identity check that silently changes behavior under de-typing will not be caught.

## Method

1. Grepped all `is`/`is not`/`==`/`!=` comparisons against `ItemType.*` and `Status.*` across `src/squads` (excluding `_migrations/_v*.py` per ADR-000232). Found **21 direct identity checks**.
2. Audited implicit enum-dependencies: membership (`in tuple/set`), set construction, iteration (`for t in ItemType`, `for s in Status`), and WORK_TYPES/SUBENTITY_* map construction.
3. Mapped every check to either a characterization test or existing pre-TASK-233 coverage.
4. Spot-checked backend `is ItemType.SKILL` branches for characterization or golden-lock coverage.
5. Ran `uv run pytest tests/test_spine_characterization.py -v`: **39/39 passed (2.20 s)**.

## Inventory vs Tests

**Direct identity checks found: 21** across 8 files (exc. migrations).
**Characterization tests: 39** covering 23 named behavioral surfaces.

The 39 tests cover more than 21 checks because each characterization test exercises a behavior (some behaviors are gated by multiple checks working together).

## Finding Coverage Map

All 21 direct identity checks are covered as follows:

| Check | File:Line | Characterized by |
|---|---|---|
| `item.type is ItemType.SKILL` (remove_artifacts) | `_agents_md/_backend.py:143` | `test_backend_conformance.py` (generate_skill/remove_artifacts contract) |
| `if child is ItemType.TASK` (parent_hint) | `_workflow/__init__.py:108` | Test 10a/10b in spine_char |
| `item.type is ItemType.SKILL` (remove_artifacts) | `_claude_code/_backend.py:275` | `test_backend_conformance.py` (same contract) |
| `item_type is ItemType.ROLE` (template routing) | `_base.py:200` | `test_rendering.py` (parametrized over all ItemType) |
| `item_type is ItemType.SKILL` (template routing) | `_base.py:202` | `test_rendering.py` |
| `item_type is ItemType.OPERATOR` (template routing) | `_base.py:204` | `test_rendering.py` |
| `it.type is ItemType.ROLE` (_role_item lookup) | `_base.py:508` | Tests 2, 5, 22 in spine_char |
| `it.type is ItemType.SKILL` (_skill_item lookup) | `_base.py:529` | Tests 2, 3, 5 in spine_char |
| `it.type is ItemType.OPERATOR` (_operator_item lookup) | `_base.py:535` | `test_operators.py` |
| `it.type is ItemType.ROLE` (adopt slug extraction) | `_service.py:152` | `test_service.py` (repair + activate) |
| `item_type is ItemType.SKILL` (scan legacy vs convention) | `_maintenance.py:284` | Tests 3a/3b in spine_char |
| `item_type is ItemType.SKILL and not md.name.startswith(skill_prefix)` | `_maintenance.py:613` | Tests 3a/3b in spine_char |
| `item.type is not ItemType.TASK` (check_subtask_stories) | `_maintenance.py:694` | Test 18 in spine_char |
| `parent.type is not ItemType.FEATURE` (check_subtask_stories) | `_maintenance.py:700` | Test 18 in spine_char |
| `item.type is not ItemType.DECISION` (check_decisions) | `_maintenance.py:752` | Tests 15/16/17 in spine_char |
| `item.status is Status.SUPERSEDED` | `_maintenance.py:754` | Tests 15/16 in spine_char |
| `item.type is ItemType.ROLE` (regen) | `_items.py:180` | Test 5 in spine_char |
| `elif item.type is ItemType.SKILL` (regen) | `_items.py:183` | Test 5 in spine_char |
| `it.type is ItemType.BUG` (severity display) | `_cli/_common.py:142` | Test 14 in spine_char |
| `parent.type is not ItemType.FEATURE` (add_story parent check) | `_subentities.py:455` | Tests 11/12/13 in spine_char |

## Gaps Found

### GAP-1 (medium): operator self-author bypass not explicitly characterized

**Location:** `_base.py:460` — `if item_type in (ItemType.ROLE, ItemType.SKILL, ItemType.OPERATOR) and author == slug`

The characterization test #2 (`test_role_may_self_author_bootstrap`, `test_skill_may_self_author_bootstrap`) exercises role and skill self-author. The operator leg of this same tuple-membership check is NOT characterized — it exists in `test_operators.py::test_add_operator_writes_operator_item` but only as a side effect, not as a named behavioral pin.

**Risk for TASK-234/235:** When `item_type` becomes a `str`, this tuple check `(ItemType.ROLE, ItemType.SKILL, ItemType.OPERATOR)` silently becomes a comparison of a str against enum members — it will ALWAYS be False. The operator self-author path will break: `add_operator` will start throwing "not a registered agent" errors. This is a concrete regression path, not theoretical.

**Severity: medium** — The existing `test_operators.py` tests will catch this regression when TASK-235 runs (they call `add_operator` which triggers the bypass). But there is no pinned characterization test declaring "operator self-author must work" explicitly.

### GAP-2 (low): workload exclusion of role/skill items not characterized

**Location:** `_roster.py:141` — `if it.type in _NON_WORK_TYPES: continue` (where `_NON_WORK_TYPES = {ROLE, SKILL, OPERATOR}`)

`test_operators.py::test_operator_not_counted_in_workload_but_is_not_spawnable` covers the operator case. Neither the characterization file nor any other test asserts that role items and skill items are excluded from workload counts.

**Risk for TASK-234/235:** When `.type` becomes `str`, the `in _NON_WORK_TYPES` set check silently evaluates `"role" in {ItemType.ROLE, ...}` — which is False (str does not equal enum). Roles and skills will start appearing as work items in workload output. This is a concrete regression path.

**Severity: low** — workload output corruption rather than a crash; visible in golden tests if the fixture has role items.

### GAP-3 (low): _is_participant excludes skill (but not characterized as an explicit contract)

**Location:** `_base.py:454` — `it.type in (ItemType.ROLE, ItemType.OPERATOR)` (skill intentionally absent)

Test 22 (`test_skill_slug_not_valid_as_author`) characterizes the rejection. However it tests the behavior from the create path; the underlying `_is_participant` check uses a different set from the self-author check (line 460). If the two sets diverge under str-typing, the interaction could be subtle. This is already characterized by test 22 (acceptable coverage).

### GAP-4 (informational): parse_type / parse_status enum iteration not characterized

**Location:** `_cli/_common.py:697,704` — `for t in ItemType` / `for s in Status` to build choices string

These build CLI error messages listing valid types/statuses. If types/statuses become str-vocab-driven, iteration order and completeness will be spec-driven, not enum-member-order-driven. Not characterized. However, this is in the error message path only (no behavioral gate) so the risk of a silent regression is low.

## Verdict

**GAPS-FOUND** — safe to proceed to TASK-234 with one condition.

GAP-2 and GAP-4 are low risk (caught by downstream tests or informational). **GAP-1 is the actionable gate**: the operator self-author bypass (`_base.py:460`) is in a tuple-membership check that shares its structural form with the two other meta-type membership checks at line 454 and 460, but covers a different set. TASK-234 will reify capability flags; if the operator leg of line 460 is not explicitly pinned, the "meta-type self-author" refactor could silently drop operator while keeping role and skill.

**Recommended action before TASK-234 proceeds:** Add one test to `test_spine_characterization.py` explicitly asserting `add_operator` succeeds (i.e., the operator self-author bypass fires). This is a 5-line test. Once added, all behavioral gates are present.

If the team accepts the risk of operator self-author being covered only implicitly by `test_operators.py`, the verdict upgrades to COMPLETE.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 236 add-finding "…" --severity high`; track with `sq review 236 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Open |  | operator self-author bypass not characterized in spine tests |
| F2 | 🟢 low | Open |  | workload exclusion of role/skill items not characterized |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — operator self-author bypass not characterized in spine tests

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_base.py:460 checks `item_type in (ItemType.ROLE, ItemType.SKILL, ItemType.OPERATOR)` for the self-author bypass. The characterization tests cover role and skill self-author (tests 2a/2b) but do NOT explicitly pin operator self-author as a named behavioral contract.

When item_type becomes str (TASK-235), this tuple check evaluates str against enum members — always False. add_operator will throw 'not a registered agent' errors. The regression will be caught by test_operators.py but there is no dedicated characterization pin.

Fix: add a test to test_spine_characterization.py asserting that svc.add_operator() succeeds without raising — this pins the operator leg of the self-author bypass explicitly.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — workload exclusion of role/skill items not characterized

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_roster.py:141 uses `it.type in _NON_WORK_TYPES` (where _NON_WORK_TYPES = {ROLE, SKILL, OPERATOR}) to exclude meta-type items from workload counts. The operator leg is covered by test_operators.py:98, but there is no test asserting that role items and skill items are excluded from workload.

Under TASK-235 str-typing, `'role' in {ItemType.ROLE, ...}` is False — roles/skills would start appearing in workload output. Detectable by the golden workload test if the fixture seeds roles (it does via sq init).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T10:22:38Z] Mara Tester:
  - QA completeness assessment complete. 21 direct identity checks inventoried, all mapped to either characterization tests or pre-existing coverage. 39/39 characterization tests pass (2.20 s).
  - Two gaps found — GAP-1 (medium, F1): operator self-author bypass at _base.py:460 not pinned in spine tests. GAP-2 (low, F2): workload role/skill exclusion not characterized.
  - Verdict: GAPS-FOUND. Recommend adding one test for GAP-1 before TASK-234 proceeds. GAP-2 has implicit safety net in golden tests. @tech-lead please review F1 and decide whether the implicit coverage in test_operators.py is sufficient or whether an explicit characterization pin is required before TASK-234 starts.
- [2026-06-26T10:25:59Z] Mara Tester:
  - GATE PASSED. The two gaps are closed: test_operator_may_self_author_bootstrap (pins the operator leg of the  self-author check) and test_workload_excludes_role_and_skill_items (pins ) added + verified green. Characterization is now complete at 41 tests covering all 21 identity checks + the membership-check dependencies. Note for TASK-234: the two  membership checks must be reified onto is_meta alongside the is/== checks (the reification inventory must include them). Safe to proceed to reification.
- [2026-06-26T10:26:17Z] Mara Tester:
  - GATE PASSED (clean repost). Both gaps closed: test_operator_may_self_author_bootstrap pins the operator leg of the meta-type self-author membership check, and test_workload_excludes_role_and_skill_items pins the _NON_WORK_TYPES membership check; both verified green. Characterization now complete at 41 tests. Carry-forward for TASK-234: the two "in (...)" membership checks must be reified onto is_meta alongside the is/== identity checks. Safe to proceed to reification.
<!-- sq:discussion:end -->
