---
id: BUG-000021
sequence_id: 21
type: bug
title: 'Slug arguments not validated: sq mine accepts unknown agents and silently
  defaults to manager'
status: Ready
author: op-pierre
priority: medium
refs:
- FEAT-000019
description: sq mine/inbox exit 0 for unknown slugs and bare sq mine defaults to manager;
  slug args should be required and validated against the roster across commands
created_at: '2026-06-10T13:35:26Z'
updated_at: '2026-06-11T07:54:56Z'
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
<!-- sq:discussion:end -->
