---
id: TASK-640
sequence_id: 640
type: task
title: 'Docs: recovering from a failed import'
status: Draft
parent: FEAT-576
author: tech-lead
refs:
- ADR-622:implements
description: 'Adopter-facing recovery note: mid-apply I/O crash then repair reconciles;
  re-running duplicates (v1 no idempotency), recover manually, no blind retry.'
created_at: '2026-07-23T13:29:39Z'
updated_at: '2026-07-23T13:33:47Z'
---
<!-- sq:body -->
Adopter-facing documentation for the one rough edge ADR-622 flags: recovering from a mid-apply crash. Depends on the `sq import` CLI being documented (this note extends the same import section).

## Scope

Add a short recovery note to the adoption/import docs (`docs/adoption.md` is the natural home — the import command's own section). It must convey, in adopter terms:
- A validation failure writes **nothing** — the whole file is rejected before any write, so there is nothing to recover; fix the file and re-run.
- The only partial-write case is a rare I/O failure **after** validation passed, mid-apply. It can leave some item files written but the index uncommitted.
- Recovery: run `sq repair` first — it reconciles the index to whatever files exist on disk. Then inspect what was actually written **before** touching the file again.
- Do **not** blind-retry the same import file: v1 has no idempotency — a re-run allocates fresh IDs and duplicates every item. Recover manually rather than re-importing.

Keep it tight — a few sentences plus the `sq repair` step. This is the adopter's safety note, not an internals essay.

## Conventions (must hold)
- **Adopter-facing only.** No sq/ticket IDs, no internal dev-process content (CI gates, dogfood, packaging/test internals), no reference to this feature or its stories. Describe the tool's behaviour for someone adopting it.
- No status/lifecycle prose. Category is "roster" if the word comes up. Match the existing voice/structure of `docs/adoption.md`.

## Testing / gates
- Docs-only: no code, no new tests. Still run `uv run --all-extras ruff format --check .` if you touch anything outside docs (you shouldn't).
- Sanity-read the rendered section for accuracy against the import behaviour as built (repair reconciles, re-run duplicates).
- `uv run sq check` clean before finishing.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 640 add-subtask "<title>"`; track with `sq task 640 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
