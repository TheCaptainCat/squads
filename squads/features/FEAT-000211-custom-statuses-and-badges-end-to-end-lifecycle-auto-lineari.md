---
id: FEAT-000211
sequence_id: 211
type: feature
title: Custom statuses and badges end-to-end + lifecycle auto-linearization
status: InProgress
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
  title: As a team member, I want custom status badges to render without crashing,
    with a graceful default
  status: Todo
created_at: '2026-06-25T13:20:36Z'
updated_at: '2026-07-02T09:27:07Z'
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
- Wire through **`STATUS_EMOJI` / badge lookup**: `StatusSpec.badge` provides the emoji for a custom status; the lookup falls back to a graceful default (e.g. ⚪) when no badge is declared. Today `STATUS_EMOJI` only covers the 9 sub-entity statuses — extend it to cover all item statuses via the spec, without crashing on a custom value.
- Wire through the **lifecycle auto-linearization renderer** used in `sq workflow` output and auto-generated skills: deterministic BFS linearization from the machine's initial state, with branching/cycling states listed as "(+ side states)".
- `sq workflow lint` validates that all transition target statuses exist in the vocabulary and that every machine has at least one reachable terminal state.

## Dependencies

Requires F2 (FEAT-000208) for `str`-typed status fields and F4 (FEAT-000210) for the spec-derived renderer. F3 (FEAT-000209) provides the override mechanism that introduces custom statuses.

## Acceptance criteria

1. `sq list --status Triage` works for a custom status `Triage` declared in `.overrides/workflow.toml`; unknown status values produce an actionable error listing valid options.
2. `sq blocked` correctly uses spec-derived open/terminal classification — an item in a custom non-terminal status is treated as open; an item in a custom terminal status is treated as closed.
3. Custom statuses do not crash any surface that resolves a status badge: `_discussion._status_badge` (and any equivalent top-level lookup) resolves a custom status's configured badge, or a graceful default (⚪) when none is declared, instead of raising on `Status(custom)`. **This AC is scoped to fixing the crash and completing badge resolution for sub-entities (where badges render today) — it does not add a status-badge display to top-level `sq show`/`sq list` output where none exists today.** Any such new top-level display surface is out of scope for F5 and would be a separate, deliberate change (tracked as a follow-up if wanted), since it would break the byte-identical default-spec invariant (AC#6).
4. `sq workflow` renders custom lifecycles with correct linearization; the auto-derived string uses BFS from initial state and lists side-states in parentheses.
5. `sq workflow lint` catches: transition targets not in the status vocabulary; machines with no reachable terminal state.
6. The F1 golden test remains green (built-in statuses and badges unchanged, including top-level `sq show`/`sq list` output byte-for-byte).

## AC#3 ruling (product decision, 2026-07-02)

Olivia flagged AC#3 as ambiguous between (a) adding new top-level item status badges to `sq show`/`sq list` (a display change, breaks byte-identical) and (b) fixing the custom-status crash and completing badge resolution while leaving today's top-level display untouched (byte-identical preserved). **Ruling: (b).** It preserves the byte-identical invariant (a project-wide rule), it is consistent with AC#6 (F1 golden stays green), and it matches what US2's acceptance text already asked for (a status renders its badge or a graceful default, no crash) — nothing in the original ask required inventing a new display surface. Adding top-level badges is a legitimate future idea but is a deliberate, separate product decision with its own golden-test implications, not an F5 deliverable.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 211 add-story "As a <role>, I want … so that …"`; track with `sq feature 211 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team member, I want sq list --status and sq blocked to work correctly with my custom statuses |
| US2 | Todo |  | As a team member, I want custom status badges to render without crashing, with a graceful default |
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
### US2 — As a team member, I want custom status badges to render without crashing, with a graceful default

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a team member, I want custom statuses to resolve to their declared badge emoji wherever badges render today (sub-entity summaries, discussion heads), and fall back to a neutral default when no badge is declared — instead of crashing — so the display is always coherent.

**Acceptance:** a status with `badge = '🟠'` in the spec renders that emoji wherever a badge is shown today; a status with no badge declared renders a default (e.g. ⚪); no crash (e.g. `_discussion._status_badge` raising on `Status(custom)`) in either case. This does not add a new top-level status-badge display to `sq show`/`sq list` where none exists today — see the feature's AC#3 ruling.
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
- [2026-07-01T09:09:28Z] Catherine Manager:
  - Scope addition (op-pierre, reviewing workflow.md.j2 post-TASK-261): two static-prose artifacts remain in the sq workflow cheatsheet that FEAT-211 should spec-derive, since 211 already owns the cheatsheet/lifecycle renderer. (1) workflow_static.md.j2:11 'Valid targets: epic, feature, task, bug, decision, review, guide' — hardcoded retype-target type list; custom types ARE retypeable (build_item_app._cmd_retype) so this should render from the spec. (2) workflow.md.j2:5-22 — the role→type authoring flow (product-owner→feature, tech-lead→task), the epic→feature→task hierarchy, and the FEAT-/BUG- prefix examples are hardcoded prose; the playbook is already a spec (playbook.toml, ADR-226) but the cheatsheet doesn't render from it, so custom setups don't see themselves.
  - PRODUCT JUDGMENT for whoever scopes 211: decide whether the authoring prose SHOULD render from the playbook spec (custom types/roles appear) or legitimately stays as 'how the bundled team works' prose — the retype-target list is the clearer, less debatable fix. KEEP STATIC (do NOT spec-derive): FEAT-013's stability-contract prose in workflow_static.md.j2 (ref-kinds table, retype mechanics, remove-vs-cancel, alias evolution rule) — that's the whole point of the TASK-261 split. @product-owner can rehome to a thin standalone feature if 211 turns out to be the wrong fit.
- [2026-07-01T11:18:18Z] Catherine Manager:
  - Decision from op-pierre (resolving the product-judgment I flagged above): the role→type authoring prose in workflow.md.j2 (the 'Product owner → features / user stories', 'Tech lead → tasks under a feature', manager-triage bullets, the epic→feature→task hierarchy line, and the FEAT-/BUG- prefix examples) SHOULD render generically from the playbook spec (playbook.toml / roles), NOT stay as hardcoded bundled-team prose — so a project with custom roles/types sees itself in sq workflow.
  - Design note for whoever scopes this: the role→type ASSOCIATIONS are already in playbook.toml, but the current text is a crafted authoring NARRATIVE with example commands, not a table — going generic means deciding how much to auto-generate from playbook interaction data vs. template with roster/type substitution. Keep the FEAT-013 static contract (workflow_static.md.j2) literal regardless. Still deliberately NOT part of the FEAT-210 corrective (TASK-269 only adds the lifecycle rows).
- [2026-07-02T09:26:55Z] Nina Product:
  - @tech-lead AC#3 ruling on your ambiguity flag: reading (b) — fix the custom-status badge crash (_discussion._status_badge calling Status(custom)) and complete badge resolution with a graceful default, for the surfaces that render badges today (sub-entities). No new top-level status-badge display is added to sq show/sq list — that would break the byte-identical invariant and isn't what US2 asked for. AC#3's wording on the feature body is tightened accordingly; proceed on that basis.
<!-- sq:discussion:end -->
