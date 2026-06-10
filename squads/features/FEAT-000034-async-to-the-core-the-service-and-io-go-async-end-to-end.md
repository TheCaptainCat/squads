---
id: FEAT-000034
sequence_id: 34
type: feature
title: 'Async to the core: the service and IO go async end-to-end'
status: Draft
parent: EPIC-000031
author: product-owner
priority: high
refs:
- FEAT-000033:blocks
- FEAT-000032:blocks
description: Make the service layer, index store and file IO async (anyio or similar)
  all the way down, with the sync bridge only at the CLI entry edge — so the protocol
  seam, TUI, web server and remote client are all async-native
subentities:
- local_id: US1
  title: As a developer of an async consumer (TUI, web server, remote client), I want
    the service async-native, so that I never wrap calls in executor threads
  status: Todo
- local_id: US2
  title: As a CLI user, I want the async conversion invisible, so that every command
    behaves and outputs byte-identically to today
  status: Todo
created_at: '2026-06-10T15:49:05Z'
updated_at: '2026-06-11T07:40:17Z'
---
<!-- sq:body -->
## Problem

The entire engine is synchronous: service methods, the index store's transactions, every file
read/write. Meanwhile every consumer on the roadmap is async-native — Textual (`sq ui`,
EPIC-000028), FastAPI (`sq web`, EPIC-000029), and an HTTP `RemoteService` (FEAT-000033). If the
service stays sync, each of them must wrap every call in executor threads forever. Worse, the
timing is critical: FEAT-000033 is about to freeze the calling convention into typed Protocols —
whether those methods are `def` or `async def` is a now-or-painful decision, and retrofitting
async under a frozen sync protocol is the painful kind.

## Value

One calling convention for the whole architecture: the protocols are **async-first**, the TUI and
web server consume the service natively, and a future server handles concurrent agents without a
thread pool bolted to a blocking core. The CLI user sees zero change — sync remains an edge
concern, not a core property.

## Scope

- **Async end-to-end, sync only at the very edge**: service mixins, the index store
  (lock/load/mutate/atomic-write), item-file IO and rendering writes become `async`; the Typer
  commands stay sync-looking and bridge with a single `anyio.run(...)` (or equivalent) per
  invocation — the *only* place the word "sync" survives.
- **Async file IO** via a library chosen by the design ADR — `anyio` is the likely pick (also
  gives structured concurrency and is the foundation both Textual and FastAPI tolerate well);
  evaluate what to do about `filelock` (blocking) — an async-compatible lock or `to_thread` for
  the lock acquisition only.
- **Tests go async** where they touch the service (pytest + anyio plugin); the CLI test matrix is
  unchanged in form since commands still run synchronously from the runner's perspective.
- **Alignment**: FEAT-000033's protocols are typed `async def` from day one; FEAT-000032's
  SQLAlchemy work uses the async engine, not the sync one.
- **Honesty clause**: this makes nothing faster for a single CLI invocation (it may add a
  microsecond of event-loop startup). The value is architectural — consumer compatibility and
  server-mode concurrency — and the feature should be sold as exactly that.

## Acceptance

- No blocking file IO or blocking service call remains anywhere below the CLI entry edge
  (lint/review-enforced); the sync↔async bridge exists in exactly one place.
- Full test suite green; behaviour and outputs byte-identical for every command, offline mode.
- pyright strict stays clean across the `async` conversion (no `Any` leaks through awaitables).
- A demonstration consumer (e.g. a 10-line script driving the service from an async context)
  works without threads — the test that fails today.
- FEAT-000033's protocol definitions adopt the async signatures; documented in the design ADR.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 34 add-story "As a <role>, I want … so that …"`; track with `sq feature 34 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a developer of an async consumer (TUI, web server, remote client), I want the service async-native, so that I never wrap calls in executor threads |
| US2 | Todo |  | As a CLI user, I want the async conversion invisible, so that every command behaves and outputs byte-identically to today |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a developer of an async consumer (TUI, web server, remote client), I want the service async-native, so that I never wrap calls in executor threads

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** an async context drives the full service (create/update/comment/list) without threads or sync shims; FEAT-000033's protocols are typed async def; FEAT-000032 aligns on the async SQLAlchemy engine.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a CLI user, I want the async conversion invisible, so that every command behaves and outputs byte-identically to today

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the CLI test matrix passes unmodified with byte-identical outputs and exit codes; the only sync↔async bridge is at the command entry edge (single anyio.run per invocation).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
