---
id: REV-000109
sequence_id: 109
type: review
title: Review FEAT-000036 type aliases (TASK-107/108)
status: Approved
author: reviewer
refs:
- FEAT-000036
- TASK-000107
- TASK-000108
created_at: '2026-06-15T08:04:08Z'
updated_at: '2026-06-15T08:05:15Z'
---
<!-- sq:body -->
Review of FEAT-000036 (Type aliases in the CLI grammar), delivered via TASK-000107 (alias routing/equivalence, US1) and TASK-000108 (help clean + docs/contract, US2).

**Verdict: Approved.** All feature Scope/Acceptance points met; the full gate is green (602 passed, 1 skipped; pyright 0 errors; ruff check + format clean).

Correctness: each type sub-app is built once and re-registered under its canonical name plus hidden alias names (the proven _addr hidden=True pattern). Because Typer shares the same group object, every alias exposes the identical tree — verified empirically: all 7 letter aliases (e/f/t/b/d/r/g) and short forms (feat/dec/rev) route to their type, deep verb+sub-entity chains work (sq f 2 story 1 body, sq t N subtask, sq r N finding, sq t N ref add, sq dec N status), including mutations.

Canonical-output invariant holds: IDs/type names/--json derive from the item model, not the invoked alias. Verified errors (sq f 9999 -> 'use FEAT-009999', sq d 9999 -> 'use ADR-009999'), --json type field, and confirmations all canonical.

Help cleanliness: aliases registered hidden=True; root --help lists only the 7 canonical names; epilog mentions aliases and points to sq workflow. No single-letter canonical command exists to collide with (b!=blocked, t!=tree, r!=repair, d!=docs verified).

Single source of truth: TYPE_ALIASES in _models/_enums.py drives CLI registration, the workflow.md.j2 table (rendered via Jinja context, not hardcoded), the root epilog, and — via the {% include 'workflow.md.j2' %} in squads_skill.md.j2 with type_aliases propagated through the backend — the generated managed skill body. Confirmed the table renders in sq workflow and in the generated squads/agents/skills/squads.md. templates_manifest.json hash for workflow.md.j2 regenerated and matches (sha256 verified).

Add-only contract rule recorded next to the table with a ref/note to FEAT-000013; docs/stability.md correctly left to FEAT-000013 per the task scope.

CLAUDE.md conventions: module privacy respected (imports from underscore modules), no future import, strict typing clean, marker-safe (no hand edits to bodies), Rich escaping not newly required. Test coverage adequate: tests/test_aliases.py (19 tests) covers map structure, collision, hidden-from-help, canonical identity per type, deep chains, JSON, and error canonicality.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 109 add-finding "…" --severity high`; track with `sq review 109 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
