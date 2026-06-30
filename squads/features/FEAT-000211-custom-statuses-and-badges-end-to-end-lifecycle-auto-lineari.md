---
id: FEAT-000211
sequence_id: 211
type: feature
title: Custom statuses and badges end-to-end + lifecycle auto-linearization
status: Ready
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000208:depends-on
- FEAT-000210:depends-on
subentities:
- local_id: US1
  title: As a team member, I want sq list --status and sq blocked to work correctly
    with my custom statuses
  status: Todo
- local_id: US2
  title: As a team member, I want custom status badges to render in sq show and sq
    list output
  status: Todo
created_at: '2026-06-25T13:20:36Z'
updated_at: '2026-06-30T07:47:14Z'
---
<!-- sq:body -->
## What this delivers

F4 delivers custom types with their own machines but relies on the status vocabulary still being resolved against the global set. F5 completes the picture: custom statuses flow correctly through every surface that today consumes `Status` values — filters, inbox, `sq blocked`, `sq list` default filter, `STATUS_EMOJI` badge lookup, and the lifecycle renderer.

After F5, a team with a custom `Triage → Mitigating → Resolved` lifecycle will see those statuses work correctly in `sq list --status Triage`, `sq blocked` (if `Mitigating` is non-terminal), `sq inbox`, and displayed with their configured badge (or a graceful default). The lifecycle string in `sq workflow` and agent skills will auto-linearize correctly from the transition graph.

This feature is mostly mechanical once F2 (models are `str`) lands — the status surfaces are already data-driven, they just need to iterate the spec rather than the enum.

## Scope

- Wire custom statuses through `sq list --status <value>`: `parse_status` in `_cli/_common.py` accepts any status string in the loaded spec's vocabulary; unknown values produce a clear "unknown status, known values: …" error.
- Wire through **terminal/open classification**: `spec.is_open(status)` / `spec.is_terminal(status)` replace `TERMINAL` frozenset lookups; `sq list` default filter (hide closed) and `sq blocked` logic use the spec.
- Wire through **`sq inbox`**: mentions in items with terminal statuses are suppressed correctly for custom types.
- Wire through **`STATUS_EMOJI` / badge lookup**: `StatusSpec.badge` provides the emoji for a custom status; the lookup falls back to a graceful default (e.g. ⚪) when no badge is declared. Today `STATUS_EMOJI` only covers the 9 sub-entity statuses — extend it to cover all item statuses via the spec.
- Wire through the **lifecycle auto-linearization renderer** used in `sq workflow` output and auto-generated skills: deterministic BFS linearization from the machine's initial state, with branching/cycling states listed as "(+ side states)".
- `sq workflow lint` validates that all transition target statuses exist in the vocabulary and that every machine has at least one reachable terminal state.

## Dependencies

Requires F2 (FEAT-000208) for `str`-typed status fields and F4 (FEAT-000210) for the spec-derived renderer. F3 (FEAT-000209) provides the override mechanism that introduces custom statuses.

## Acceptance criteria

1. `sq list --status Triage` works for a custom status `Triage` declared in `.squads.toml`; unknown status values produce an actionable error listing valid options.
2. `sq blocked` correctly uses spec-derived open/terminal classification — an item in a custom non-terminal status is treated as open; an item in a custom terminal status is treated as closed.
3. Custom status badges render in `sq <type> show` and `sq list` output; statuses with no declared badge show a graceful default (no crash).
4. `sq workflow` renders custom lifecycles with correct linearization; the auto-derived string uses BFS from initial state and lists side-states in parentheses.
5. `sq workflow lint` catches: transition targets not in the status vocabulary; machines with no reachable terminal state.
6. The F1 golden test remains green (built-in statuses and badges unchanged).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 211 add-story "As a <role>, I want … so that …"`; track with `sq feature 211 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team member, I want sq list --status and sq blocked to work correctly with my custom statuses |
| US2 | Todo |  | As a team member, I want custom status badges to render in sq show and sq list output |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team member, I want sq list --status and sq blocked to work correctly with my custom statuses

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a team member using a custom workflow, I want `sq list --status Triage`, `sq blocked`, and the default closed-item filter to correctly classify items by my custom statuses' open/terminal designations, so that the standard query commands reflect my team's actual workflow state.

**Acceptance:** `sq list --status Triage` returns items in that status; `sq blocked` treats items in non-terminal custom statuses as open; `sq list` (default, no `--all`) hides items in terminal custom statuses. Unknown status values in `--status` produce a 'known values: …' error.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a team member, I want custom status badges to render in sq show and sq list output

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a team member, I want custom statuses to render with their declared badge emoji in `sq show` and `sq list` output, and fall back to a neutral default when no badge is declared, so the display is always coherent.

**Acceptance:** a status with `badge = '🟠'` in the spec renders that emoji; a status with no badge declared renders a default (e.g. ⚪); no crash or missing output in either case.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:44:14Z] Catherine Manager:
  - Process rule (from the FEAT-220 incident, REV-000230): for externalize/refactor-with-byte-identical-output work, the characterization golden must be authored FIRST — against HEAD, as a gating test — BEFORE the rewire, so the change runs under a passing guard rather than leaving the proof as a last task an agent can abandon. Pin ALL inputs (roster/flags/clock) for generated-artifact comparisons. See [[pin-roster-when-diffing-generated-skills]].
<!-- sq:discussion:end -->
