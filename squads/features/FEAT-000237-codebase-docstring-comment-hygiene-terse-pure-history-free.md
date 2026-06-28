---
id: FEAT-000237
sequence_id: 237
type: feature
title: 'Codebase docstring/comment hygiene: terse, pure, history-free'
status: Draft
author: tech-lead
refs:
- FEAT-000231
subentities:
- local_id: US1
  title: Code comments carry no squad-item references
  status: Todo
- local_id: US2
  title: Comments describe current behavior, not history
  status: Todo
- local_id: US3
  title: A CI gate blocks new ticket refs in comments
  status: Todo
created_at: '2026-06-26T14:19:55Z'
updated_at: '2026-06-26T14:20:42Z'
---
<!-- sq:body -->
## What this delivers

A codebase-wide pass over every docstring and comment in `src/squads/` to make them **terse, pure,
and history-free** — and a lint/CI guard so the cleanup does not rot the moment the next agent adds a
ticket reference. Code should explain WHAT it does and WHY on its own terms, never cite the work item
that introduced it or narrate how it changed over time.

This is a **someday backlog item** — drafted for the record, not scheduled. It must ride **after the
EPIC-000206 vocabulary-externalization churn settles**: the active de-typing work keeps adding exactly
the references this feature strips (e.g. comments like "reserved-vocab (TASK-…)", "the §5-6a check",
"replaces FEAT-…'s == enums"), so cleaning mid-flight would churn against in-flight work. Settle the
epic first, then sweep.

## Mission (in priority order)

1. **MOST IMPORTANT — remove squad-item references from code comments and docstrings.** No `FEAT-…`,
   `TASK-…`, `ADR-…`, `REV-…`, `BUG-…`, `EPIC-…`, no `US`/`ST` story/subtask numbers, and no ADR
   section refs (`§N`) anywhere in `src/squads/` comments or docstrings. A comment must stand on the
   code's own terms — the intent, the contract, the non-obvious why — never "the ticket that added
   this". (The recent de-typing pass introduced many such refs; those are precisely what to strip.)
2. **Eliminate history / archaeology.** No "previously X, now Y", "this used to…", "as of v0.5",
   "the FEAT-… lesson", no change-log narration. Comments describe the code as it IS, not how it
   evolved — git history is where evolution lives.
3. **Shorten, straight to the point.** Terse and purposeful. Delete comments that merely restate the
   code; trim over-long docstring preambles. A comment earns its place only by explaining non-obvious
   intent or rationale that the code cannot express itself.
4. **Stay pure.** Describe behaviour / contract / intent, not process or development history — the
   same principle that makes a test name describe behaviour rather than the bug that prompted it.

## Scope

- ALL of `src/squads/`: module / class / function docstrings, inline comments, AND the comments inside
  the bundled TOML files (`default_workflow.toml`, `roles.toml`, `playbook.toml`).

## Non-goals (explicit)

- **NOT a behaviour change.** Comments and docstrings only. Every test stays green and **untouched** —
  no test edited, no runtime code path altered.
- **Does NOT cover test names / structure** — that is the ground-up test-battery rewrite (linked
  `related`); this feature touches comments/docstrings only, not test identity.
- **Does NOT rewrite CLAUDE.md, nor the bundled role / skill / playbook PROSE.** Those are product
  content (the agent-facing guidance the tool ships), not source-code commentary, and are out of
  scope. Only the structural *comments* in the TOML files are in scope, not the guidance strings they
  carry.

## The regression guard (crucial — without it this rots immediately)

Squads agents will keep adding `TASK-`/`ADR-` references to comments as they work, so a one-time
cleanup decays the day it lands. This feature MUST ship an **enforced lint/CI gate** — a grep gate or
a ruff rule — that FAILS the build when a squad-item reference appears in a source comment or
docstring. The detection pattern is, at minimum: `(FEAT|TASK|ADR|REV|BUG|EPIC)-\d` and a bare `§`
inside `src/squads/` comments/docstrings. The gate is what converts a cleanup into a durable
invariant; the cleanup pass and the gate land together (the gate would fail until the pass is done).

## Acceptance criteria

1. Zero squad-item references (`(FEAT|TASK|ADR|REV|BUG|EPIC)-\d`, `US`/`ST` numbers, `§`) in any
   comment or docstring under `src/squads/`, including the bundled TOML comments.
2. No history/archaeology narration in comments/docstrings (no "previously/now", "used to", "as of
   vX", change-log prose).
3. Comments are measurably terser — restate-the-code and dead preamble comments removed; what remains
   explains non-obvious intent/why.
4. A lint/CI gate (grep gate or ruff rule) is in place and **green** across `src/`, and FAILS on a
   newly-introduced squad-item reference in a comment/docstring (verified by a negative check).
5. Zero behaviour change: the full existing test suite passes **unchanged and green**; `uv run pyright
   && uv run ruff check . && uv run ruff format --check .` clean.

## Sequencing

Drafted as a someday item. Schedule only **after EPIC-000206** (the workflow/role/playbook
externalization + de-typing) has landed and settled — the in-flight epic is the largest current
source of the references this strips, so cleaning before it settles would churn.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 237 add-story "As a <role>, I want … so that …"`; track with `sq feature 237 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Code comments carry no squad-item references |
| US2 | Todo |  | Comments describe current behavior, not history |
| US3 | Todo |  | A CI gate blocks new ticket refs in comments |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Code comments carry no squad-item references

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a developer reading the code, I want comments and docstrings to carry no squad-item references (FEAT-/TASK-/ADR-/REV-/BUG-/EPIC- ids, US/ST numbers, ADR section refs), so that the code explains itself on its own terms and I never have to chase a closed ticket to understand what a line does.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Comments describe current behavior, not history

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a developer maintaining the code, I want comments to describe the code as it currently is — not its history (no 'previously/now', 'used to', 'as of vX', change-log narration) — so that comments stay true as the code evolves and git history remains the single place for the story of how it got here.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — A CI gate blocks new ticket refs in comments

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a maintainer, I want an enforced lint/CI gate that fails when a squad-item reference appears in a source comment or docstring, so that the one-time cleanup becomes a durable invariant instead of rotting the moment the next agent pastes a ticket id into a comment.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
