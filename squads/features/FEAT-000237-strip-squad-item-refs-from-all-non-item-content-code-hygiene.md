---
id: FEAT-000237
sequence_id: 237
type: feature
title: Strip squad-item refs from all non-item content + code-hygiene guard
status: Draft
author: tech-lead
refs:
- FEAT-000231
subentities:
- local_id: US1
  title: Code comments carry no squad-item references
  status: Todo
- local_id: US2
  title: Src comments describe current behavior, not history
  status: Todo
- local_id: US3
  title: CI guard blocks squad-item refs outside item files
  status: Todo
- local_id: US4
  title: User-facing content carries no squad-item references
  status: Todo
- local_id: US5
  title: Bundled prose stripped of refs without churning wording
  status: Todo
created_at: '2026-06-26T14:19:55Z'
updated_at: '2026-07-03T09:26:31Z'
---
<!-- sq:body -->
## What this delivers

One repo-wide invariant enforced everywhere except where it belongs:

> **Only squad item files may reference squad item IDs.** No `FEAT-`/`TASK-`/`ADR-`/`REV-`/`BUG-`/`EPIC-` id, `US`/`ST` story-subtask number, or ADR `§N` section reference may appear in any **code content** (comments, docstrings, structural comments in the bundled TOML) **or user-facing content** (`docs/`, `README`, shipped markdown, CLI output strings, and the bundled role / skill / playbook prose + `CLAUDE.md`). Those references belong solely in the tracked squad item files under the dogfood squad (`squads/**`), nowhere else in the repo.

This is a codebase-wide sweep to satisfy that invariant, plus an enforced lint/CI guard so the cleanup does not rot the moment the next agent pastes a ticket id somewhere it doesn't belong. It also folds in the previously-untracked principle that **shipped docs must not cite internal items** — a doc, README, or CLI string states its guarantees on its own terms, never by pointing at a closed ticket.

The `src/` half additionally keeps the original code-hygiene aim: comments and docstrings there should be **terse, pure, and history-free** — they explain WHAT the code does and WHY on its own terms, never narrate how the code changed over time.

## Two things this feature does

1. **Strip squad-item references** from every non-item surface in the repo (see Scope).
2. **Restyle `src/` code commentary** — for `src/squads/` comments and docstrings *only*, also make them terser, purer, and history-free (mission items 2–4 below).

The reference-strip is universal; the restyle is deliberately confined to source code. See "What is stripped vs. left alone" for exactly where the line falls.

## Mission (in priority order)

1. **MOST IMPORTANT — remove squad-item references from ALL non-item content.** No `FEAT-`, `TASK-`, `ADR-`, `REV-`, `BUG-`, `EPIC-`, no `US`/`ST` story/subtask numbers, and no ADR section refs (`§N`) in any code comment/docstring, structural TOML comment, `docs/` page, `README`, shipped markdown, CLI output string, bundled role/skill/playbook prose, or `CLAUDE.md`. Content must stand on its own terms — the intent, the contract, the non-obvious why, the user-facing guarantee — never "the ticket that added this".
2. **Eliminate history / archaeology (`src/` code commentary).** No "previously X, now Y", "this used to…", "as of v0.5", "the FEAT lesson", no change-log narration. Comments describe the code as it IS, not how it evolved — git history is where evolution lives.
3. **Shorten, straight to the point (`src/` code commentary).** Terse and purposeful. Delete comments that merely restate the code; trim over-long docstring preambles. A comment earns its place only by explaining non-obvious intent or rationale that the code cannot express itself.
4. **Stay pure (`src/` code commentary).** Describe behaviour / contract / intent, not process or development history — the same principle that makes a test name describe behaviour rather than the bug that prompted it.

## Scope

Reference-strip applies across the whole repo except the item allowlist:

- ALL of `src/squads/`: module / class / function docstrings, inline comments, AND the comments inside the bundled TOML files (`default_workflow.toml`, `roles.toml`, `playbook.toml`).
- `docs/`, `README`, and any other shipped markdown.
- CLI output strings (help text, messages, table content the tool prints).
- The bundled role / skill / playbook **prose** and `CLAUDE.md` — the agent-facing guidance the tool ships.

The `src/` code-commentary restyle (mission items 2–4) applies to `src/squads/` comments/docstrings only.

## What is stripped vs. left alone (draw the line here)

- **Stripped everywhere:** squad-item references, as defined by the invariant, on every surface listed in Scope. This includes the bundled prose and `CLAUDE.md`.
- **Left alone:** the *wording* of user-facing prose — `docs/`, `README`, bundled role/skill/playbook guidance, and `CLAUDE.md`. That prose is product content whose phrasing should not be churned; this feature removes squad-item references from it but does **not** restyle it, shorten it, or rewrite it for "history-free/terse". Only `src/squads/` code commentary gets the terseness/history-free rewrite.
- **Legitimate uses that STAY (the guard must allow them):** illustrative example payloads that legitimately contain an id (e.g. a reflog JSON sample carrying a `TASK` id), and CLI-syntax templates in docs/help such as `--parent FEAT-…` or `sq task <n>`. These describe the *shape* of a command or a data sample, not a citation of a real tracked item, so they are not violations.

## Non-goals (explicit)

- **NOT a behaviour change.** Content only. Every test stays green and **untouched** — no test edited, no runtime code path altered by the strip/restyle itself (a new guard/lint config is the only additive change).
- **Does NOT cover test names / structure**, nor the sq-refs living in test names/docstrings that cite AC or ticket numbers (e.g. `test_ac5_…`) — that is the behaviour-named test-battery rewrite (`FEAT-000231`). Coordinate so the two features do not double-touch the same test files.
- **Does NOT restyle or reword user-facing prose.** The bundled role/skill/playbook guidance, `docs/`, `README`, and `CLAUDE.md` keep their wording; only their squad-item references are removed. The terse/history-free rewrite is confined to `src/` code commentary.

## The regression guard (crucial — without it this rots immediately)

Squads agents keep adding ticket references as they work, so a one-time cleanup decays the day it lands. This feature MUST ship an **enforced lint/CI gate** — a grep gate or a ruff rule — that FAILS the build when a squad-item reference appears anywhere it is forbidden.

- **Allowlist (may carry squad-item references): the dogfood squad's item files only — the item markdown under `squads/**`.** That is the single place references legitimately live.
- **Forbidden territory (fails the build): everything else in the repo** — `src/`, `docs/`, `README`, shipped markdown, CLI output strings, and the bundled prose + `CLAUDE.md`.
- **Detection pattern**, at minimum: `(FEAT|TASK|ADR|REV|BUG|EPIC)-\d`, bare `US`/`ST` story-subtask numbers, and a bare `§`. The gate must **allow the legitimate uses** above (CLI-syntax templates and example payloads) so it does not false-positive.

The gate is what converts a cleanup into a durable invariant; the cleanup pass and the gate land together (the gate would fail until the pass is done).

## Acceptance criteria

1. Zero squad-item references (`(FEAT|TASK|ADR|REV|BUG|EPIC)-\d`, `US`/`ST` numbers, `§`) on any non-item surface: `src/squads/` comments/docstrings (including the bundled TOML comments), `docs/`, `README`, shipped markdown, CLI output strings, and the bundled role/skill/playbook prose + `CLAUDE.md`.
2. No history/archaeology narration in `src/squads/` comments/docstrings (no "previously/now", "used to", "as of vX", change-log prose).
3. `src/squads/` comments are measurably terser — restate-the-code and dead preamble comments removed; what remains explains non-obvious intent/why.
4. User-facing prose (`docs/`, `README`, bundled guidance, `CLAUDE.md`) keeps its wording — the diff there is reference removals only, not rewording.
5. A lint/CI gate (grep gate or ruff rule) is in place and **green** with the dogfood squad's item files (`squads/**`) as the sole allowlist and everything else forbidden; it FAILS on a newly-introduced squad-item reference on any forbidden surface (verified by a negative check) and does NOT fire on the legitimate CLI-syntax/example-payload uses.
6. Zero behaviour change: the full existing test suite passes **unchanged and green**; `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Sequencing (two waves)

- **`src/` code-commentary wave** — still gated behind **EPIC-000206** (the workflow/role/playbook externalization + de-typing) settling. That in-flight work is the largest current source of exactly the references this strips, so cleaning `src/` mid-flight would churn against it. Settle the epic, then sweep source.
- **User-facing wave** — `docs/`, `README`, CLI output strings, bundled prose, and `CLAUDE.md`. This has **no such dependency** and can proceed independently and sooner; whoever schedules the work can split it from the `src/` wave. The guard can be scoped to land per wave (user-facing surfaces first, `src/` added when its sweep runs).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 237 add-story "As a <role>, I want … so that …"`; track with `sq feature 237 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Code comments carry no squad-item references |
| US2 | Todo |  | Src comments describe current behavior, not history |
| US3 | Todo |  | CI guard blocks squad-item refs outside item files |
| US4 | Todo |  | User-facing content carries no squad-item references |
| US5 | Todo |  | Bundled prose stripped of refs without churning wording |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Code comments carry no squad-item references

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a developer reading the source, I want comments and docstrings in src/squads/ (including the structural comments in the bundled TOML) to carry no squad-item references (FEAT-/TASK-/ADR-/REV-/BUG-/EPIC- ids, US/ST numbers, ADR §N refs), so that the code explains itself on its own terms and I never chase a closed ticket to understand a line.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Src comments describe current behavior, not history

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a developer maintaining the source, I want src/squads/ comments to describe the code as it currently is — not its history (no 'previously/now', 'used to', 'as of vX', change-log narration) and terse rather than restating the code — so comments stay true as the code evolves and git history remains the single place for how it got here. (Restyle is confined to src/ code; user-facing prose keeps its wording.)
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — CI guard blocks squad-item refs outside item files

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a maintainer, I want an enforced lint/CI gate whose sole allowlist is the dogfood squad's item files (squads/** item markdown) and whose forbidden territory is everything else in the repo (src/, docs/, README, shipped markdown, CLI output strings, bundled prose, CLAUDE.md), so a squad-item reference on any non-item surface fails the build. The gate must allow legitimate CLI-syntax templates (e.g. --parent FEAT-…) and illustrative example payloads (e.g. a reflog sample carrying a TASK id) so it does not false-positive, and it must fire on a newly-introduced reference (verified by a negative check).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — User-facing content carries no squad-item references

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a user reading the shipped docs, README, and CLI output, I want them to carry no squad-item references — a doc, README, or CLI string states its guarantees on its own terms, never by citing an internal FEAT-/TASK-/ADR-/REV-/BUG-/EPIC- id, US/ST number, or ADR §N — so nothing user-facing points at a closed internal ticket. (This captures the previously-untracked 'shipped docs must not cite internal items' principle.)
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Bundled prose stripped of refs without churning wording

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As a maintainer of the agent-facing guidance, I want the bundled role/skill/playbook prose and CLAUDE.md to have their squad-item references removed WITHOUT their guidance wording being restyled, shortened, or rewritten, so the diff on those product surfaces is reference removals only — their phrasing (product content) is preserved while the invariant is satisfied.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T11:50:01Z] Catherine Manager:
  - Scope refinement (Pierre, 2026-06-30) — still DEFERRED until EPIC-206 (210/211/212) settles; the guard-first-now option was considered and declined to avoid churning against in-flight work. When scheduled, broaden scope beyond src/squads/ to ALSO cover tests/ and docs/ (and all docstrings): strip sq-item refs (FEAT-/TASK-/ADR-/REV-/BUG-/EPIC-/§N) and history/archaeology there too. Current magnitude: ~303 refs in src/squads (46 files), ~958 in tests/ (89 files), ~70 in docs/ (8 files).
  - Distinguish ILLEGITIMATE refs (citing the ticket that introduced code; 'previously X now Y' history; ADR section refs) — STRIP — from LEGITIMATE uses that stay: illustrative example payloads (e.g. a reflog JSON sample with a TASK id), and doc CLI-syntax templates like '--parent FEAT-…'. The guard must allow the latter or it'll false-positive.
  - Test-side overlaps FEAT-000231 (behaviour-named test rewrite): test NAMES/docstrings citing AC#/ticket numbers (test_ac5_…) are FEAT-231's domain — coordinate so the two don't double-touch the same files.
- [2026-07-03T09:26:31Z] Olivia Lead:
  - Scope broadened (Pierre, 2026-07-03) from 'src/squads/ comments/docstrings only' to a single repo-wide invariant: only squad item files (the dogfood squad under squads/**) may reference squad item IDs — nowhere else in the repo, code or user-facing.
  - Lifted the previous carve-outs: docs/, README, shipped markdown, CLI output strings, the bundled role/skill/playbook prose, and CLAUDE.md are now IN scope for reference stripping. This also captures the previously-untracked 'shipped docs must not cite internal items' principle under the same guard.
  - Deliberate line kept: the terse/pure/history-free RESTYLE stays confined to src/ code commentary. User-facing prose (docs/README/bundled guidance/CLAUDE.md) is product content — we strip its squad-item refs but do NOT churn its wording.
  - Guard boundary: allowlist = squads/** item markdown (sole legitimate home for refs); forbidden = everything else (src/, docs/, README, CLI strings, bundled prose, CLAUDE.md). Must allow legitimate CLI-syntax templates (--parent FEAT-…) and example payloads (reflog sample with a TASK id).
  - Scheduling split into two waves: the src/ code-commentary sweep stays gated behind EPIC-000206 settling (that de-typing work keeps adding these refs); the user-facing sweep has no such dependency and can proceed independently/sooner. Test-name/docstring refs (test_ac5_…) remain FEAT-000231's domain — coordinate to avoid double-touching test files.
  - Leaving Draft — backlog scope-expansion only; no tasks, no code touched.
<!-- sq:discussion:end -->
