---
id: EPIC-29
sequence_id: 29
type: epic
title: sq web — a local web view of the squad
status: Draft
author: product-owner
priority: low
refs:
- EPIC-28
- FEAT-15:depends-on
description: An sq web command starting a local webserver to browse the squad in a
  browser; read-only first, with full CRUD as a possible long-term destination
created_at: '2026-06-10T15:16:05Z'
updated_at: '2026-06-11T07:40:18Z'
---
<!-- sq:body -->
## Outcome

`sq web` starts a local webserver and the squad becomes shareable at a glance: anyone with the URL
on the machine (or tunnel) browses the tree, reads items, follows refs and discussions — no
terminal, no editor, no markdown-viewer gymnastics. The squad's state stops being something only
CLI users can see.

## Framing

- **Read-only first, CRUD as a possible destination**: the first increment serves the squad for
  browsing. Unlike the TUI, a web app reachable by others raises real write questions (who is the
  actor? auth? concurrent edits), so mutations stay a deliberate, separate decision — possible
  someday, promised never.
- Stack TBD by an ADR when the epic activates — FastAPI is the natural candidate (typed, async,
  serves JSON we already shape), but the design phase decides; either way it ships as an optional
  extra (`squads[web]`) so the core stays lean.
- The read API should be a thin skin over the same `--json` shapes the CLI freezes
  (EPIC-12's FEAT-15) — one machine surface, two consumers; the shared resolver
  (FEAT-19) does the addressing.
- Big sibling of EPIC-28 (`sq ui`): same browse-first philosophy, same service layer,
  different audience — the TUI serves the operator at the keyboard, the web view serves everyone
  else.

Features (authored when this activates): the `sq web` command + server skeleton, the browse UI
(tree, item, refs, discussion), and — if ever — the CRUD decision as its own feature with its own
ADR.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
