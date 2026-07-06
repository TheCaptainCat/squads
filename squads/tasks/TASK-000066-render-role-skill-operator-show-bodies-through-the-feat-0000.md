---
id: TASK-66
sequence_id: 66
type: task
title: Render role/skill/operator show bodies through the FEAT-000026 styled path
status: Done
parent: FEAT-64
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Route role/skill/operator show bodies through the FEAT-000026 styled path
    (TTY/raw/piped)
  status: Done
  story: US2
- local_id: ST2
  title: Preserve role catalog card + activation-hint fallback; add operator show
  status: Done
  story: US2
- local_id: ST3
  title: Styled-vs-raw rendering tests; full-suite regression check on print_item
  status: Done
  story: US2
created_at: '2026-06-12T12:05:15Z'
updated_at: '2026-07-06T15:19:02Z'
---
<!-- sq:body -->
Make `sq role <n> show`, `sq skill <n> show`, and `sq operator <n> show` render their bodies through the FEAT-26 styled markdown path — the same renderer `sq feature <n> show` uses for its body facet. Depends on TASK-65 for the item-first `show` surface (especially the new `sq operator show`); both tasks touch the same three CLI modules, so coordinate / stack.

## The gap
`print_item` in `_cli/_common.py` (~line 277-280) renders the metadata Panel for every type, but then GUARDS the body: `if it.type not in (ItemType.ROLE, ItemType.SKILL): ... _print_item_content(...)`. So role/skill bodies are never styled. Today `_cli/_role.py::show_role` prints the body with `console.print(e(body))` (raw, line 76) and `_cli/_skill.py::skill_show` prints no body at all (panel only). Operator has no show today (added in TASK-65).

## What to build
Route the three groups' `show` body rendering through the FEAT-26 helpers so behavior matches `sq feature <n> show`'s body facet:
- On a TTY (and not `--raw`): styled Rich `Markdown` (headings, bullets, code, panes) — gate via `_is_styled()`, the same predicate the item path uses.
- `--raw`: plain body text (current default behaviour) — byte-stable.
- Piped / `NO_COLOR`: plain, byte-stable. `_is_styled()` already encodes this.
- The metadata Panel/card is UNCHANGED — only the body rendering changes (US2 acceptance: "no change to the panel").

Pick the cleanest seam. Options, in order of preference:
1. Relax the `print_item` guard so ROLE/SKILL/OPERATOR also render their body via the shared styled path, and have the three groups' `show` call `print_item`. This is the most uniform and kills the special-case. Verify it does not pull in sub-entity summaries or other facets these types don't have (roles/skills/operators carry no stories/subtasks/findings, so the sub-entity branch is a no-op for them — confirm `_print_item_content` degrades cleanly, or render just the body facet).
2. If `print_item` carries item-only assumptions that don't fit, factor a small shared `render_body(text, *, raw)` helper out of `_print_item_content` and call it from the three `show` commands plus the item path. Do NOT duplicate the styled-vs-plain logic inline in three places.

Role's `show` has extra behaviour to PRESERVE: the catalog card (full name / title / model / mission / responsibilities from `role_by_slug`) and the graceful "no active item — run `sq role activate`" hint when a bundled role has no tracked item (`role_body` returns None). Keep that fallback; only the active-item body should flow through the styled renderer.

Operator `show` (new): same styled-body treatment over the operator item body, plus its metadata card (id / slug / name).

## `sq operator show` rendering note
Per the brief: operator bodies are likely a no-op in practice (operators rarely carry a markdown body), but the rendering path must be consistent with role/skill — wire it the same way. If the body is empty, degrade to a clean "(no body)"-style line rather than an empty render. Do not special-case operator out of the styled path.

## Tests (call out churn)
- `sq role <n> show` and `sq skill <n> show` render styled markdown on a TTY (assert via a forced-styled console / the same fixture pattern FEAT-26 tests use); `--raw` prints raw body; piped output is plain and byte-stable. Add an operator show smoke test.
- Reuse the FEAT-26 styled-vs-raw test idiom rather than inventing a new one — find how the item `show` tests assert styled vs plain and follow it.
- This task changes `_cli/_common.py::print_item` (shared by every item type) — run the FULL suite and watch feature/task/review `show` tests for regressions from relaxing the guard.

## Acceptance
- `sq role <n> show` / `sq skill <n> show` / `sq operator <n> show` render the body as styled markdown on a TTY; `--raw` opts out; piped/`NO_COLOR` is plain & byte-stable.
- Role's catalog card + activation-hint fallback preserved.
- Metadata panel unchanged across all three.
- No regression in existing item `show` rendering.
- pyright strict + ruff clean; full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 66 add-subtask "<title>"`; track with `sq task 66 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Route role/skill/operator show bodies through the FEAT-26 styled path (TTY/raw/piped) | US2 |
| ST2 | Done |  | Preserve role catalog card + activation-hint fallback; add operator show | US2 |
| ST3 | Done |  | Styled-vs-raw rendering tests; full-suite regression check on print_item | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Route role/skill/operator show bodies through the FEAT-26 styled path (TTY/raw/piped)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a CLI user reading a role or skill definition, I want the body rendered as styled markdown (headings, bullets, code blocks, panes) just like any other item show, so that role bodies are as readable as feature bodies
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Route the sq role/skill/operator show body rendering through the FEAT-000026 styled markdown path (the same helper feature show uses): styled Rich Markdown on a TTY gated by _is_styled(), --raw for plain byte-stable body, plain when piped/NO_COLOR — by relaxing the print_item ROLE/SKILL guard or factoring a shared render_body helper rather than duplicating the styled-vs-plain logic. Metadata panel unchanged (US2).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Preserve role catalog card + activation-hint fallback; add operator show

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a CLI user reading a role or skill definition, I want the body rendered as styled markdown (headings, bullets, code blocks, panes) just like any other item show, so that role bodies are as readable as feature bodies
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Preserve role show's extra behaviour through the reroute: the catalog card (full name/title/model/mission/responsibilities) and the graceful 'no active item — run sq role activate' fallback when role_body is None (only the active-item body flows through the styled renderer). Wire the new operator show with the same styled-body treatment plus its id/slug/name card, degrading an empty body to a clean '(no body)' line (US2).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Styled-vs-raw rendering tests; full-suite regression check on print_item

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a CLI user reading a role or skill definition, I want the body rendered as styled markdown (headings, bullets, code blocks, panes) just like any other item show, so that role bodies are as readable as feature bodies
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Add styled-vs-raw rendering tests (reusing the FEAT-000026 forced-styled-console idiom) for role/skill/operator show — styled markdown on a TTY, --raw plain, piped byte-stable — plus an operator show smoke test, and run the full suite since print_item is shared by every item type to catch feature/task/review show regressions from relaxing the guard (US2).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T12:39:04Z] Elias Python:
  - Delivered. Seam: factored _render_body(body, styled) and public render_body_text(body, raw) in _common.py. print_item guard removed (ROLE/SKILL/OPERATOR now go through _print_item_content, sub-entity branches no-op). show_role/skill_show/operator_show each call render_body_text(body, raw=raw) after their own panel. --raw added to all three. 354 tests, pyright strict, ruff: all green. --comments not wired (out of scope).
<!-- sq:discussion:end -->
