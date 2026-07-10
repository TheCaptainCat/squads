---
id: TASK-367
sequence_id: 367
type: task
title: Update shipped docs for overridable vocabulary
status: Draft
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:10Z'
updated_at: '2026-07-10T02:02:37Z'
---
<!-- sq:body -->
## Scope

Surface 3 of the REV-360 audit: shipped user docs. Update the customization/reference
docs so the item-type/status/priority/severity/prefix/folder vocabulary is presented as
the bundled DEFAULT of a spec-driven, overridable system — not a fixed closed grammar —
and so the workflow-spec override (`.overrides/workflow.toml`) is documented alongside
templates/roles. Docs-only, no code; independent of the other tasks (tech-writer work).
Files: `docs/overrides.md`, `docs/workflow.md`, `docs/stability.md`, `docs/internals.md`,
`docs/recipes.md`, `README.md`. (Per shipped-docs policy: no sq/item IDs or external
URLs in the doc prose.)

## Covered REV-360 findings

- HIGH (current-doc bug) — `docs/overrides.md` (whole doc; layout tree 46-76) — the
  customization guide documents only template + role overrides and NEVER mentions
  `.overrides/workflow.toml` (item-type/status/lifecycle/priority/severity vocab).
  Add it, including in the "Override layout" tree. This is wrong TODAY, not just under
  custom vocab.
- MEDIUM — `docs/workflow.md:234` (override-format section 234-370) — states the file
  has exactly three sections `[lifecycles.*]/[statuses.*]/[items.*]`; never documents
  `[collections.*]` (priority/severity badge axes). Add it.
- MEDIUM — `docs/workflow.md:146-147` — finding severity stated as a fixed five-value
  scale with no note it's the bundled `[collections.severity]` default.
- MEDIUM — `README.md:96-97` — types listed as a flat closed set; no note that the
  seven work types are the customizable bundled default (only role/skill/operator
  reserved, ADR-266).
- MEDIUM — `README.md:169` & `:172` — `--priority urgent|high|medium|low` documented as
  a fixed enum; it's an overridable ordered badge collection.
- MEDIUM — `README.md:124-132` — status-workflows table presented as THE status
  vocabulary with no mention statuses/lifecycles are override-extensible.
- MEDIUM — `docs/stability.md:68-86` — Tier-1 overrides section lists only
  `.overrides/{templates,roles}/` and omits `.overrides/workflow.toml`; inconsistent
  with workflow.md.
- LOW — `README.md:100` — prefix map stated as fixed (prefixes are `[items.*].prefix`).
- LOW — `docs/internals.md:19` & `:53` — type enumeration + per-type folder layout
  stated as fixed (folders are `[items.*].folder`, type set extensible).
- LOW — `docs/stability.md:174-191` — alias table "frozen at 1.0" without noting custom
  types declare their own aliases (freezing built-in aliases is fine; presenting the
  table as the complete grammar is incomplete).
- LOW — `docs/recipes.md:88-90` — priority recipe treats codes as fixed; add a pointer
  that the axis is a customizable badge collection.

## Acceptance

- `.overrides/workflow.toml` and `[collections.*]` are documented in overrides.md,
  workflow.md, and stability.md, consistently across the three.
- README/internals present the type/status/priority/prefix/folder vocabulary as the
  bundled default of an overridable system, not a closed grammar.
- Docs remain accurate for the bundled default reader (the common case) while stating
  overridability; no broken internal cross-references.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 367 add-subtask "<title>"`; track with `sq task 367 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
