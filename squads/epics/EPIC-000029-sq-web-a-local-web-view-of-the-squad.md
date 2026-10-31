---
id: EPIC-29
sequence_id: 29
type: epic
title: sq web — a local web view of the squad
status: InProgress
author: product-owner
refs:
- EPIC-28
- FEAT-15:depends-on
description: An sq web command serving the squad in a browser through the daemon's
  /v1 routes; read-only first, with full CRUD as a possible long-term destination
created_at: '2026-06-10T15:16:05Z'
updated_at: '2026-10-28T22:07:54Z'
priority: low
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
- **The server is the daemon** (FEAT-1140): it serves the squad as resource routes under `/v1`,
  with an OpenAPI document a front generates its types from, on a browser listener that is off by
  default. Its HTTP server packages ship with every install; only the daemon loads them.
- **One API, every client**: the browser front, the CLI's remote mode and the terminal UI call
  the same routes, and each route answers with the same result a command prints with `--json`
  (FEAT-1226), display labels and badges included, so the front needs no copy of the vocabulary.
- **The front's stack is its own decision**, taken with the web frontend milestone (MILE-868):
  it calls the `/v1` routes whatever its framework.
- Big sibling of EPIC-28 (`sq ui`): same browse-first philosophy, same API,
  different audience — the TUI serves the operator at the keyboard, the web view serves everyone
  else.

Features: the daemon and its routes (FEAT-1140), the command layer they serve (FEAT-1226), a squad
hosted on another machine (FEAT-33); still to author: the browse UI (tree, item, refs, discussion),
and — if ever — the CRUD decision as its own feature with its own ADR.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T13:00:46Z] `op-pierre` Pierre Chat:
  - Proposed build sequence for the web line, explicitly up for debate: (1) make the web API; (2) give the sq CLI a remote mode and a local mode; (3) make the daemon logic, with the dogfood running daemon mode disabled; (4) make a frontend using Jinja templates for SEO and Vue 3 for the interactivity.
- [2026-09-03T13:07:04Z] `manager` Catherine Manager:
  - Driven measurements (op-pierre, 2026-09-03, release/0.15, this machine, this repo's corpus) — the number for the daemon-value argument above: uv run overhead alone 0.049s; import squads 0.072s; .venv/bin/sq --version (no uv) 0.740s; .venv/bin/sq task 909 show 0.668s; uv run sq check (whole corpus) 3.203s.
  - Reading: ~0.7s of fixed pre-dispatch cost (Typer app construction + spec loading) sits between import and the simplest command answering, independent of uv and of import — --version pays nearly all of it doing nothing. Lazy-loading that cost is a fraction of daemon-scale work and benefits every caller, including non-daemon users; the daemon would then buy back the remaining per-call cost on top, not the whole 0.7s. See FEAT-916.
- [2026-10-16T11:27:13Z] `op-pierre` Pierre Chat:
  - 2026-10-16: all daemon work (API, CLI remote/local modes, daemon logic, dogfood) lives in this epic alongside the web frontend; no separate daemon epic. Milestones split the delivery: MILE-1051 (0.17, daemon) and MILE-868 (frontend).
- [2026-10-28T13:54:01Z] `product-owner` Nina Product:
  - Outcome and framing predate the daemon line: the body still speaks of `sq web`, FastAPI and an `squads[web]` extra, while the web frontend now consumes the daemon API (FEAT-1140, ADR-1052). @manager the epic wants a rescope when you next open it; no change made here.
- [2026-10-28T22:07:54Z] `product-owner` Nina Product:
  - Framing refreshed 2026-10-28 per the manager (FEAT-1140, 027ea69) to match ADR-1224/ADR-1225: the server is the daemon with /v1 resource routes and OpenAPI, its HTTP packages are required dependencies (no `squads[web]` extra, no FastAPI), results carry display so the front needs no vocabulary, and the front stack stays MILE-868's decision. Features line now lists FEAT-1140, FEAT-1226 and FEAT-33. Summary updated.
<!-- sq:discussion:end -->
