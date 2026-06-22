---
id: REV-000165
sequence_id: 165
type: review
title: Advisory create-lane warning (TASK-164, FEAT-122 US1/Slice B)
status: Approved
author: reviewer
refs:
- TASK-000164:addresses
subentities:
- local_id: F1
  title: Inline duplicate json imports in _cli/_create.py (import json in _make, import
    json as _json in create_guide) — prefer one top-level import json reused in both.
    Cosmetic; ruff clean.
  status: Fixed
  severity: low
- local_id: F2
  title: Internal artifact commands (sq dev add, role activate) routed through ServiceCore.create
    write an advisory lane_warning to the reflog with expected:[] (e.g. architect
    authoring a 'role' item). Harmless + not surfaced to the user (only _create.py
    renders it), but it is reflog noise. Consider exempting non-CREATE_LANES item
    types (role/skill/operator/dev) or internal-author paths in a follow-up. Not a
    blocker for this advisory cut.
  status: Fixed
  severity: low
created_at: '2026-06-22T13:31:03Z'
updated_at: '2026-06-22T13:40:45Z'
---
<!-- sq:body -->
Independent review of TASK-000164 — advisory create-lane warning (FEAT-000122 US1 / Slice B, under ADR-000163 Option A). Reviewed the uncommitted diff on `feat/async-core`.

## Scope reviewed
- `_interactions.py` — `CREATE_LANES`, `allowed_create_types`, `in_lane_owner`, `is_lane_exempt`.
- `_services/_base.py::ServiceCore.create` — advisory check + reflog delta tag (no print).
- `_services/_results.py::CreateResult.lane_warning`.
- `_cli/_create.py` (_make + create_guide) — render + --json.
- `_cli/_role.py::show_role` — creates row + create_lane JSON.
- `tests/test_lane_derivation.py` (45 tests) + golden files.

## Checks performed
1. Lane table vs Nina §1: product-owner→{feature,epic}, tech-lead→{task}, architect→{decision,guide}, reviewer→{review}, qa→{bug}, tech-writer→{guide}, *dev→∅, devops→∅, manager exempt, op-* exempt. MATCHES exactly. DEV sentinel → empty lane confirmed (python/dotnet/go-dev).
2. Warn-and-proceed: out-of-lane create returns CreateResult.lane_warning AND creates the item, exit 0; service does NOT print (layering preserved); CLI prints escaped via e() and is --json-aware; reflog delta tagged advisory (additive, free-form delta — no schema bump owed to this task). Verified live + by unit/CLI tests.
3. Exemptions: manager + op-* exempt BEFORE lookup; dev-bug warns (owner qa), no --author qa requirement, no special code path. Verified live.
4. Honesty: all warning/help/doc text advisory/best-effort; grep for tamper/forge/secur/enforce/guarantee in new code = clean.
5. Conventions: pyright 0 errors; ruff check + format clean (complexity within limits on the create branch); e() on new console output; ItemType-typed throughout; no from __future__; goldens changed additively (can_spawn + create_lane).
6. Fallback justification VERIFIED: the prose-scan misfire is real. reviewer's `sq create review` author verb lives in the TASK playbook section (line 206), not the REVIEW section; tech-writer has NO `sq create guide` verb anywhere in the playbook (its guide do= is "edit for clarity"). A per-section scan misses reviewer→review and tech-writer→guide entirely. The ADR §2 declarative CREATE_LANES fallback was justified, not a shortcut. It is co-located in `_interactions.py` (single source) and the table-pinning test asserts CREATE_LANES == Nina's §1 table AND every slug is in PLAYBOOK.
7. Table-pinning effectiveness VERIFIED by mutation: adding FEATURE to tech-lead's lane fails both test_create_lanes_map_matches_nina_table and test_tech_lead_lane. Drift is caught.

## Gates (re-run by reviewer)
- uv run pyright — 0 errors, 0 warnings.
- uv run ruff check . — All checks passed. ruff format --check — 118 files already formatted.
- uv run pytest — full suite green (1 skipped); test_lane_derivation.py 45 passed.

## Acceptance: AC-B1..AC-B7 all satisfied (verified live + tests).

Verdict: APPROVED.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 165 add-finding "…" --severity high`; track with `sq review 165 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Inline duplicate json imports in _cli/_create.py (import json in _make, import json as _json in create_guide) — prefer one top-level import json reused in both. Cosmetic; ruff clean. |
| F2 | 🟢 low | Fixed |  | Internal artifact commands (sq dev add, role activate) routed through ServiceCore.create write an advisory lane_warning to the reflog with expected:[] (e.g. architect authoring a 'role' item). Harmless + not surfaced to the user (only _create.py renders it), but it is reflog noise. Consider exempting non-CREATE_LANES item types (role/skill/operator/dev) or internal-author paths in a follow-up. Not a blocker for this advisory cut. |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Inline duplicate json imports in _cli/_create.py (import json in _make, import json as _json in create_guide) — prefer one top-level import json reused in both. Cosmetic; ruff clean.

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Internal artifact commands (sq dev add, role activate) routed through ServiceCore.create write an advisory lane_warning to the reflog with expected:[] (e.g. architect authoring a 'role' item). Harmless + not surfaced to the user (only _create.py renders it), but it is reflog noise. Consider exempting non-CREATE_LANES item types (role/skill/operator/dev) or internal-author paths in a follow-up. Not a blocker for this advisory cut.

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T13:40:45Z] Elias Python:
  - F1 fixed: consolidated the two inline json imports in src/squads/_cli/_create.py into a single top-level `import json`. Both the `_make` factory and `create_guide` now use it.
  - F2 fixed: added `LANED_TYPES: frozenset[ItemType]` to src/squads/_interactions.py — derived from the union of all CREATE_LANES values (single source, no hardcoded duplicate). In ServiceCore.create (src/squads/_services/_base.py) the advisory lane check is now gated on `item_type in LANED_TYPES` before the exempt/allowed checks, so role/skill/operator creates skip the check entirely — no lane_warning computed, no lane_warning key in the reflog delta.
  - New tests in tests/test_lane_derivation.py: TestLanedTypes (3 unit tests pinning LANED_TYPES content); two service tests verifying that activate_role (ROLE) and add_operator (OPERATOR) produce no lane_warning and no lane_warning key in the reflog delta.
  - Gates: pyright 0 errors. ruff check + format clean. pytest: 970 passed, 1 skipped.
<!-- sq:discussion:end -->
