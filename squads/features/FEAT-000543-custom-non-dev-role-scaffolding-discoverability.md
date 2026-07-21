---
id: FEAT-543
sequence_id: 543
type: feature
title: Custom non-dev role scaffolding & discoverability
status: Draft
parent: EPIC-538
author: product-owner
subentities:
- local_id: US1
  title: Scaffold a net-new custom role slug
  status: Todo
- local_id: US2
  title: Activate a custom role end-to-end, incl. can_spawn opt-in
  status: Todo
- local_id: US3
  title: Surface custom-role discoverability in catalog/help/docs
  status: Todo
created_at: '2026-07-21T20:43:26Z'
updated_at: '2026-07-21T20:44:19Z'
---
<!-- sq:body -->
## Capability

Let an adopter create a wholly custom **non-dev** role — e.g. `security-analyst`,
`incident-commander` — not just the 8 bundled roles or a `<tech>-dev` stack role.

## Why / the gap

The resolver (`_roles/_resolver.py::resolve_role`) already has a **new-slug path**:
a `.overrides/roles/<slug>.toml` for a slug absent from the bundled catalog defines
a wholly-new role (required: `full_name`, `title`, `description`, `mission`;
optional: `responsibilities`, `agreements`, `model`, `color`, `can_spawn`). And
`sq role activate <slug>` already routes through the resolver end-to-end — it
creates the tracked ROLE item plus the `.claude/` backend pointer. This was proved
by hand-authoring a TOML and activating `security-analyst`.

The gap is pure ergonomics/discoverability, not the engine:
- `sq override scaffold --role <slug>` only scaffolds a *bundled* role (copies its
  known defaults); it has no path for a slug that isn't already in the catalog.
- `sq role catalog` and `sq role activate --help` only surface bundled roles;
  nothing tells an adopter that a net-new custom role is possible at all.
- The `.overrides/roles/<slug>.toml` new-slug convention is discoverable today
  only by reading resolver source.

## Requirements — settled design (Pierre, verbatim in the provenance comment below)

1. **Create surface = scaffold-then-activate, two steps.** Extend
   `sq override scaffold` to accept a net-new role slug (e.g.
   `sq override scaffold role --new <slug>`): it writes a commented
   `.overrides/roles/<slug>.toml` template carrying the usual
   `squads:override-base:<version>` stamp, for the adopter to edit by hand. Then
   the existing `sq role activate <slug>` creates the role. No one-shot
   `sq role add`.
2. **Field scope = essentials + edit for the rest.** The scaffolded template
   pre-stubs the essentials (`full_name`, `title`, `description`, `mission`) with
   fill-in-here placeholders, and includes the advanced fields
   (`responsibilities`, `agreements`, `model`, `color`) as commented-out lines to
   uncomment and fill in by hand. The command itself stays simple — no flag per
   field.
3. **Spawn = opt-in via flag.** A custom role may be granted `can_spawn` (allowed
   to orchestrate/spawn subagents) via `can_spawn = true` in the TOML and/or a
   scaffold flag — opt-in, no forced warning. Note for the architect: this sits in
   tension with ADR-155's capability-attenuation stance (leaf roles can't spawn);
   the policy chosen here is deliberately permissive — opt-in and allowed, not
   blocked or gated.
4. **Discoverability.** `sq role catalog` and `sq role activate --help` gain
   text that a custom non-dev role is possible and point at the scaffold command;
   any relevant docs get the same pointer.

## Acceptance

- `sq override scaffold role --new <slug>` writes `.overrides/roles/<slug>.toml`
  with the override-base stamp, essential fields stubbed, advanced fields
  commented, refuses to clobber an existing file without `--force`.
- Editing that TOML and running `sq role activate <slug>` creates the ROLE item
  and `.claude/` pointer for the custom role, same as it does for a bundled slug
  today.
- `can_spawn` can be set true for a custom role via the TOML (and/or a scaffold
  flag) and is honoured by the resolver/activation path already in place.
- `sq role catalog` output and `sq role activate --help` text mention custom
  non-dev roles and point at the scaffold command.

## Dependencies / framing

This is the **roles axis** of the spec-driven customization work under EPIC-538
and is **orthogonal to ADR-541** (type categories / pluggable validators) — it
does not need to be sequenced behind that work, since it only touches the roles
resolver/activation path already in place, not the item-type/category system.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 543 add-story "As a <role>, I want … so that …"`; track with `sq feature 543 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Scaffold a net-new custom role slug |
| US2 | Todo |  | Activate a custom role end-to-end, incl. can_spawn opt-in |
| US3 | Todo |  | Surface custom-role discoverability in catalog/help/docs |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Scaffold a net-new custom role slug

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Extend 'sq override scaffold' with a net-new-slug path: 'sq override scaffold role --new <slug>' writes '.overrides/roles/<slug>.toml' stamped 'squads:override-base:<version>', with full_name/title/description/mission stubbed and responsibilities/agreements/model/color commented out. Refuses to clobber an existing file without --force. No 'sq role add' one-shot command.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Activate a custom role end-to-end, incl. can_spawn opt-in

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Confirm/harden the existing 'sq role activate <slug>' path for a hand-edited net-new TOML: creates the tracked ROLE item + '.claude/' pointer, same as a bundled slug. 'can_spawn = true' in the TOML (and/or a scaffold flag) opts a custom role into spawning; default is false. Note the tension with ADR-155 (leaf roles can't spawn) as context for the architect — chosen policy here is opt-in and allowed.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Surface custom-role discoverability in catalog/help/docs

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
'sq role catalog' output and 'sq role activate --help' text mention that a wholly custom non-dev role is possible and point at 'sq override scaffold role --new <slug>'. Any relevant docs (override/customization docs) get the same pointer.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T20:44:19Z] Pierre Chat:
  - Decision record for custom non-dev roles (FEAT-543):
  - 1. Create surface = scaffold-then-activate (two steps): sq override scaffold gets a --new <slug> path that writes a commented .overrides/roles/<slug>.toml template with the override-base stamp; adopter edits it; sq role activate <slug> (already works) creates the role. Do NOT build a one-shot 'sq role add'.
  - 2. Field scope = essentials + edit for the rest: scaffold pre-stubs full_name/title/description/mission and includes responsibilities/agreements/model/color as commented lines to fill in by hand. Command itself stays simple, no flag per field.
  - 3. Spawn = opt-in via flag: can_spawn may be granted to a custom role via can_spawn = true in the TOML and/or a scaffold flag, opt-in, no forced warning. (Tension with ADR-155's capability-attenuation stance is noted for the architect, but the policy is opt-in and allowed.)
  - 4. Home = feature under EPIC-538.
<!-- sq:discussion:end -->
