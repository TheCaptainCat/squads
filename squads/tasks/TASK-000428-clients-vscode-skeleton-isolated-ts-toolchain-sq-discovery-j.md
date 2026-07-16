---
id: TASK-428
sequence_id: 428
type: task
title: 'clients/vscode skeleton: isolated TS toolchain, sq discovery, --json adapter'
status: Draft
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
created_at: '2026-07-16T13:51:27Z'
updated_at: '2026-07-16T16:02:19Z'
---
<!-- sq:body -->
## Goal

Stand up the `clients/vscode/` package skeleton that US1–US3 build on: an isolated TypeScript/Node toolchain, the `sq`-invocation/discovery module, and a thin `sq --json` adapter with committed fixtures captured from real output. No VS Code UI in this task — the tree provider, preview, and filter/group commands land in the story tasks on top of this foundation.

## Scope

- **Package skeleton** at `clients/vscode/`: `package.json` (VS Code extension manifest + scripts), `tsconfig.json`, ESLint flat config, Prettier config, own lockfile, and a `src/` + `test/` layout. Entirely disjoint from the Python core — own toolchain, own lockfile, no shared build/config/virtualenv.
- **`sq` discovery module**: resolves how to invoke `sq` by auto-detecting the workspace toolchain against the workspace root, in the ADR-427 #2 order (first that works wins): (1) explicit config override (`squads.sqPath`, or a `squads.command` array); (2) workspace virtualenv `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows); (3) `uv` present + a project → `uv run sq`; (4) `poetry` present + a project → `poetry run sq`; (5) bare `sq` on PATH (fallback). The resolved invocation is **cached and re-probed on failure**. Never PATH-only.
- **`sq --json` adapter**: a thin layer that shells out to the resolved `sq`, parses stdout as the frozen 1.0 JSON shapes, and maps exit codes per the frozen table — `2` usage (our bug: log the argv), `3` check failure (surfaced verbatim), `1`/other runtime (show stderr); a version/schema-skew `1` with the "run `sq migrate up`" message is surfaced verbatim (the adapter pins **no** schema knowledge). Every failure surfaces as a VS Code notification with an actionable message — never a crash, never a partial silent result.
- **Committed fixtures**: capture real output of `sq tree <root> --json`, `sq list --json`, and `sq show <id> --raw` into fixture files under the package, so unit tests run with no `sq` binary present.

## Strict TS quality bar (parity with the Python core — set up here)

Stand up the exact toolchain/config so the story tasks inherit it. Parity target for `clients/vscode/`:

- **Type check** — `tsc --noEmit` with `strict: true` PLUS `noUncheckedIndexedAccess`, `noImplicitReturns`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`, `exactOptionalPropertyTypes`, `isolatedModules` (closest analog to pyright strict).
- **Lint** — ESLint flat config on `typescript-eslint` **strict-type-checked** + **stylistic-type-checked** (type-aware), plus rules mirroring ruff: `complexity` ≤ 12 (≈ C901), `max-params` ≤ 8 (≈ PLR0913), import ordering (≈ ruff I), and bugbear/simplify-style rules (≈ B/SIM). Zero warnings tolerated (`--max-warnings 0`).
- **Format** — Prettier `--check` (≈ `ruff format --check`).
- **Single gate command** — `npm run check` = `typecheck && lint && format:check`, mirroring `uv run pyright && uv run ruff check . && uv run ruff format --check`.

## Acceptance criteria

- `clients/vscode/` exists as a self-contained package with its own lockfile; nothing under it is referenced by the Python toolchain and vice versa (`clients/` is in the Python tooling's ignore set — a stray `.ts`/`node_modules` can never fail a Python run).
- `npm run check` runs the full strict gate (tsc + ESLint + Prettier) and passes on the skeleton.
- The discovery module resolves `sq` through all five strategies in order, caches the result, and re-probes on failure; each failure mode produces an actionable notification (no throw, no crash).
- The `--json` adapter parses the three surfaces from committed fixtures and maps every documented exit code; unit tests pass with **no `sq` binary present**.
- The adapter reads **only** via `sq … --json` / `sq show <id> --raw` — it MUST NOT read `.claude/` and MUST NOT parse `.squads.json` (ADR-427 #2, invariant #1).

## ADR-427 constraints this task must honor

- #1 Placement & isolation: `clients/vscode/`, isolated toolchain/lockfile, no shared config inheritance.
- #2 Consumer contract + discovery order + failure-mode notifications; no `.claude/`/`.squads.json` access.
- #3 Testing: unit layer against committed fixtures runs with no `sq` present (this task establishes the fixture discipline).

## Implementer note

Project rule: **sq/ticket IDs must not appear in source** (this task's ID included). Name files, modules, and tests by behavior (e.g. `discovery`, `sqAdapter`, `exitCodeMapping`), not by ticket. Keep the ticket pointer in the sq task / PR, not in code.

Implements FEAT-100 (foundation for US1–US3). Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 428 add-subtask "<title>"`; track with `sq task 428 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
