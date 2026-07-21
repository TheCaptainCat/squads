---
id: EPIC-28
sequence_id: 28
type: epic
title: sq ui — a terminal UI for browsing the squad
status: InProgress
author: product-owner
priority: low
refs:
- FEAT-15:depends-on
- FEAT-19:depends-on
description: 'An sq ui command opening a TUI: navigate the tree, read items with tabs
  for stories/body/discussion; browse-first, mutations a later increment'
created_at: '2026-06-10T15:15:37Z'
updated_at: '2026-07-21T11:26:52Z'
---
<!-- sq:body -->
## Outcome

Operators (and curious humans) get a comfortable way to *live in* a squad from the terminal:
`sq ui` opens a TUI with the hierarchy on one side and the selected item on the other — body,
stories/subtasks/findings and discussion as tabs, rendered markdown, status at a glance. The CLI
stays the tool for *doing*; the TUI becomes the tool for *seeing*.

## Framing

- **Browse-first, not read-only-by-design**: the first increment ships navigation and reading —
  the cheap, high-value 80% — but the architecture sits on the same service layer as the CLI
  (validated, locked transactions), so mutations (transition, comment, assign) are a later
  increment, explicitly not a non-goal.
- Likely stack: Textual (sister project of rich, already in our dependency tree) — Tree,
  TabbedContent and Markdown widgets map one-to-one onto the need. An optional extra
  (`squads[tui]`) keeps the core lean for agents who'll never open it.
- Sequencing: a pure consumer of the machine surface — best built on the frozen `--json` shapes
  and shared resolver (EPIC-12's FEAT-15 / FEAT-19), and a great way to stress them.

Features (the product owner will author them when this epic activates): the `sq ui` shell +
navigation, the item reader with tabs, then the first mutation increment.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T11:26:52Z] Pierre Chat:
  - Test layer: the sq ui tests get their own tests/tui/ layer (Textual Pilot harness fits none of unit/service/cli/integration), registered properly in tests/CONVENTIONS.md + the meta ticket-ID scanner — not folded into tests/cli/.
<!-- sq:discussion:end -->
