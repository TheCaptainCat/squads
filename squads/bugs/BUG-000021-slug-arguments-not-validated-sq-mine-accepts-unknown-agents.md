---
id: BUG-000021
sequence_id: 21
type: bug
title: 'Slug arguments not validated: sq mine accepts unknown agents and silently
  defaults to manager'
status: Verified
author: op-pierre
priority: medium
refs:
- FEAT-000019
description: sq mine/inbox exit 0 for unknown slugs and bare sq mine defaults to manager;
  slug args should be required and validated against the roster across commands
created_at: '2026-06-10T13:35:26Z'
updated_at: '2026-06-11T13:19:21Z'
---
<!-- sq:body -->
## Observed

- `sq mine totally-unknown` exits 0 and prints `nothing assigned to totally-unknown` — an unknown
  slug is indistinguishable from a registered agent with an empty plate.
- Bare `sq mine` exits 0 and silently defaults to `manager`.
- `sq inbox totally-unknown` behaves the same way (`nothing for @totally-unknown`, exit 0).

## Expected

- A slug supplied to `sq mine` / `sq inbox` (and any other slug-accepting surface) is validated
  against the roster — registered agents **and** operators (`op-…`) — and an unknown slug is a
  clean `SquadsError` (exit 1) naming the valid slugs or pointing at `sq operator list` / the
  roster.
- `sq mine` without an argument should require the slug rather than silently assuming `manager`
  (no agent identity is implied by the invoking shell).

## Why it matters

Agents drive their loop off `sq mine` / `sq inbox`. A typo'd slug silently reports an empty
workload, so an agent (or operator) concludes there is nothing to do — work goes stale with no
error anywhere. Validation exists elsewhere (`--author` on create requires a registered agent;
`sq check` warns on unregistered authors/assignees), so this is an inconsistency, not a design
choice.

## Scope

Audit every slug-accepting surface for the same laxity — at least: `sq mine`, `sq inbox`,
`sq workload` filters, `comment --as`, `update --assignee`, `--author` outside create. One shared
"resolve slug or raise" helper, mirroring the shared item-ID resolver decided in FEAT-000019.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:12:18Z] Catherine Manager:
  - Triage 2026-06-11: stays medium — second in the bug queue, after BUG-000022. Real correctness issue (typo'd slug silently reports an empty workload and stalls the agent loop) but no data corruption. Implementation note: build the shared resolve-slug-or-raise helper in step with FEAT-000019's item-ID resolver so the pattern lands once; audit all slug-accepting surfaces listed in the body.
- [2026-06-11T12:16:05Z] Olivia Lead:
  - Fix task created: TASK-000043 (medium, @python-dev). Shared resolve-slug-or-raise helper coordinated with FEAT-000019's resolver pattern. Second in the queue.
- [2026-06-11T12:51:03Z] Olivia Lead:
  - @qa Fix landed and reviewed (TASK-000043, Done). Slug args now validated against the roster (agents + operators) via resolve_slug_or_raise across mine/inbox/list/comment --as/update --assignee/--author/add-* --assignee. Please verify: 'sq mine ghost' and 'sq inbox ghost' exit non-zero with 'unknown slug'; a valid agent slug and an operator slug (op-pierre) both work; bare 'sq mine' errors (slug required). Uncommitted in the working tree. Bug stays open until you verify.
- [2026-06-11T13:19:21Z] Mara Tester:
  - Verified fix for BUG-000021 (TASK-000043) against working tree.
  - sq mine ghost → exit 1, 'error: unknown slug ghost; valid slugs: architect, devops, manager, op-pierre, product-owner, python-dev, qa, reviewer, tech-lead, tech-writer'.
  - sq inbox ghost → exit 1, same clean message.
  - Bare sq mine → exit 2, Typer missing-argument error (accepted per op-pierre's recorded decision).
  - Valid agent slug (qa) and op- slug (op-pierre) work correctly (exit 0).
  - Spot checks: sq bug 21 comment --as ghost → exit 1; sq bug 21 update --assignee ghost → exit 1. Both surfaces validated.
  - All acceptance criteria met. Closing.
<!-- sq:discussion:end -->
