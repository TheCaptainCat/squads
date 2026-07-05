---
id: REV-144
sequence_id: 144
type: review
title: Multi-active agent backends (FEAT-138) runtime + check rule
status: Approved
parent: TASK-140
author: reviewer
refs:
- TASK-140
- FEAT-138
- ADR-141
subentities:
- local_id: F1
  title: Stale schema_version="0.4" in test_agent_naming.py config-parsing tests
  status: Open
  severity: low
created_at: '2026-06-16T12:58:05Z'
updated_at: '2026-06-16T12:59:17Z'
---
<!-- sq:body -->
Independent review of FEAT-138 multi-active agent backends, delivered in TASK-140 (InReview). Reviewed against ADR-141 as amended by the op-pierre override (Elias's comment + manager directive): NO 0.4 schema bump and NO migration — active_backends is part of the in-development 0.3 schema, config reads legacy default_backend tolerantly. All other ADR-141 rulings stand and were verified.

Gate: 819 passed / 1 skipped, pyright 0 errors, ruff check + format clean. Repo squad at schema 0.3 with active_backends=["claude_code"], sq check green. Imports acyclic. Invariant 1 (nothing new in .squads.json) and Invariant 6 (no .claude/ reach-around) both hold.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 144 add-finding "…" --severity high`; track with `sq review 144 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Stale schema_version="0.4" in test_agent_naming.py config-parsing tests |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stale schema_version="0.4" in test_agent_naming.py config-parsing tests

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
tests/test_agent_naming.py:186 and :198 pass schema_version="0.4" to SquadsConfig.from_toml_dict. These are residue from the reverted 0.4 work. HARMLESS — from_toml_dict has model_config extra=ignore and does not validate schema_version against SCHEMA_VERSION; the tests only assert init_names hoisting, so they pass and exercise the right path. But the literal "0.4" is now misleading (current schema is 0.3) and is the only 0.4 string left in non-doc code. Recommend changing both to "0.3" for hygiene. Not blocking.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T12:59:17Z] Paul Reviewer:
  - VERDICT: APPROVED. FEAT-138 multi-active backends is correct and complete per ADR-141 as amended by the op-pierre override.
  - Confirmed (a) NO 0.4/migration residue in code: SCHEMA_VERSION="0.3"; no _v0_3_to_v0_4.py; registry stops at the 0.3 migration; no v0_4 corpus fixture; _CORPUS_CASES = [(0.1),(0.2),(0.3)] only; no test asserts a 0.4 schema except two stale config-parsing fixtures in test_agent_naming.py (F1, low, harmless). All other "0.4" strings are in tracked sq item docs/reflog — immutable history, not code.
  - Confirmed (b) managed_paths lists ONLY guaranteed-written files for both backends: claude_code → [CLAUDE.md (write_managed, unconditional), .claude/settings.json (ensure_scaffold)]; agents_md → [AGENTS.md (ensure_scaffold + write_managed)]. No per-role pointers listed (would false-fail when no roles). Both managed_paths are read-only (no mkdir/write); conformance asserts read-only + present-after-sync for both.
  - Back-compat read verified: legacy default_backend="claude_code" → active_backends=["claude_code"] (from_toml_dict), explicit active_backends=[] preserved, missing both → ["claude_code"] default (never silently sq-only). Exercised non-vacuously by the v0_3 corpus fixture (keeps singular default_backend) migrating up to 0.3 and passing sq check.
  - Fan-out verified across every backend-writing path over the deduped active list: scaffold_backend, refresh_managed, sync, activate_role/add_dev/add_skill, regen, remove_item. Dedup at config field-validator (first-occurrence order). --backend repeatable; none sentinel (case-insensitive) → []; none+real → SquadsError. sq check errors on missing active managed path, empty list = no check, deactivated not probed.
  - Gate: 819 passed / 1 skipped, pyright 0 errors, ruff check + format clean. Repo squad at 0.3, sq check green. Invariants 1 & 6 hold; imports acyclic. One low finding (F1) — non-blocking cosmetic.
<!-- sq:discussion:end -->
