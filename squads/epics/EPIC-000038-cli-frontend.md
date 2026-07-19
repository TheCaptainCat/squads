---
id: EPIC-38
sequence_id: 38
type: epic
title: CLI frontend
status: Done
author: product-owner
description: 'The daily terminal experience of sq: complete and rendered reading,
  graph navigation, and the ergonomics of driving a squad from the command line'
created_at: '2026-06-11T07:57:10Z'
updated_at: '2026-07-19T19:34:46Z'
---
<!-- sq:body -->
## Outcome

Working a squad from the terminal feels first-class: one command reads a whole item beautifully,
the ref web is navigable from where you stand, and the things humans type all day are as short
and forgiving as they are unambiguous. The CLI stops being only the *machine* surface (that
rigor lives in Road to 1.0) and becomes a pleasant *human* surface too.

## Framing

- This epic owns the **plain CLI's reading and navigation experience** — `show` completeness and
  rendering, the `sq graph` ego view, and whatever daily-loop ergonomics come next.
- **Boundaries**: full-screen interactivity is EPIC-28 (`sq ui`); the browser is EPIC-29
  (`sq web`); anything that *freezes* — grammar, aliases, `--json` shapes — belongs to
  EPIC-12 (which is why type aliases live there, not here). This epic's features change how
  output *looks and reads*, never what scripts parse: piped/`--raw`/`--json` stability is a
  standing constraint inherited from the 1.0 contract.
- Natural consumers of the same groundwork: both UI epics reuse the service-layer traversal and
  rendering decisions made here.

Current features: FEAT-26 (complete, rendered `show` + root `sq show`), FEAT-37
(`sq graph`). Candidates the operator has floated but not commissioned: markdown themes, a
full-graph view (explicitly delegated to exports/UIs for now).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
