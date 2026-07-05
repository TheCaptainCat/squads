---
id: EPIC-206
sequence_id: 206
type: epic
title: 'Config-driven workflow engine: custom types, statuses, state machines'
status: Done
author: product-owner
refs:
- EPIC-31
created_at: '2026-06-25T13:04:19Z'
updated_at: '2026-07-02T13:07:22Z'
---
<!-- sq:body -->
## Vision

Today three interrelated systems are hardcoded in Python and cannot be changed without modifying source code:

1. **Workflow** — ticket types (`task`, `bug`, `decision`, …), statuses, per-type state machines, the terminal set, and parent rules (`_workflow.py`, `_models/_enums.py`).
2. **Role catalog** — the 8 bundled roles (slug, full name, title, mission, responsibilities) and the stack-dev name pool (`_roles/_catalog.py`).
3. **Playbook** — per item-type overview, lifecycle text, commands, and per-role guidance (`enter`/`do`/`handoff`/`watch`) that drives the generated `sq-<type>` skills and `skills_for_role()` (`_interactions.py`).

This epic makes all three **fully config-driven**: each lives in its own bundled TOML file, loaded and validated at runtime using the same load-and-validate pattern, with default behavior byte-identical to today. A project can define brand-new types (e.g. an `incident` type, prefix `INC`, folder `incidents/`), brand-new statuses (`Triage → Mitigating → Resolved`), custom role definitions, and playbook entries for custom types — all in TOML, with no code changes and no fork.

`sq workflow` renders the **live loaded config** instead of today's static `workflow.md.j2`.

Grounded in the architecture study (Robert Architect, 2026-06-25). The study mapped the full coupled surface and quantified the blast radius: ~152 `ItemType.*` refs across 23 files and ~21 `Status.*` refs across 7 — but these split into cheap *generic dispatch* (`item.type`, `FOLDER_BY_TYPE[t]`) versus ~20 expensive *hardcoded identity checks* (`item.type is ItemType.TASK/DECISION/SKILL`) that encode workflow-spine semantics and are the real labor.

## Who needs this and why

**The constraint today:** every team using squads must fit their work into the built-in vocabulary (`task`, `bug`, `feature`, `decision`, `review`, `guide`), the 8 bundled roles, and the hand-authored role guides for those types. That works for software teams doing sprint-style delivery. It does not work once squads is used for:

- **Ops and SRE teams** that track `incident` and `change-request` items, with their own triage-to-resolution lifecycles (e.g. `Triage → Mitigating → Resolved → PostMortem`), not the `Draft → InProgress → Done` arc — and their own role structure (on-call engineer, incident commander).
- **Compliance and security teams** that need `finding`, `control`, or `risk` types with custom severities and sign-off states, and role-specific guidance for who reviews vs. who signs off.
- **Any team whose domain vocabulary doesn't map cleanly to software delivery** — the hardcoded type list, role catalog, and playbook are all vocabulary impositions, not deliberate boundaries.

Without this epic, every such team must either (a) shoehorn their work into `task`/`bug` with convention-based title prefixes — losing query, ref, and workflow fidelity — or (b) fork squads. Both are bad outcomes. Config-driven workflow, roles, and playbook remove the vocabulary imposition while keeping squads' coordination guarantees (stable IDs, query, refs, inbox, repair).

**Existing users are unaffected unless they opt in.** All bundled default specs reproduce today's behavior exactly; no team migrates unless they choose to.

## Recommended approach

Three parallel loaded specs, each following the same load-and-validate pattern:

- **`WorkflowSpec`** — built from a bundled `default_workflow.toml`; optionally merged with a project override. Covers types, statuses, machines, terminal set, parent rules, prefixes/folders/aliases/badges.
- **`RoleCatalogSpec`** — built from a bundled `roles.toml`; covers the 8 role definitions (slug, full name, title, mission, responsibilities) and the dev-name pool. Golden-locked against today's `_catalog.py`.
- **`PlaybookSpec`** — built from a bundled `playbook.toml`; covers per-type overview, lifecycle text, commands, and per-role `RoleGuide`s (`enter`/`do`/`handoff`/`watch`). Drives `sq-<type>` skill generation and `skills_for_role()`. Depends on `RoleCatalogSpec` (playbook references role slugs). Golden-locked against today's `PLAYBOOK` in `_interactions.py`.

For the workflow spec:
- Model fields **widen from enums to `str`** (`Item.type`/`status`, sub-entity status) — frontmatter round-trips losslessly, so reading existing items needs no rewrite.
- The free functions (`can_transition`, `workflow_for`, `parent_allowed`, `is_open`, `parent_hint`) become **methods on `WorkflowSpec`** taking strings, validating against the loaded spec.
- The ~20 hardcoded `is ItemType.X` spine checks get **reified as declared capability flags on a `TypeSpec`** (e.g. `is_meta`, `subentity_kind`, `ref_rules`, `enforce_parent`). The engine asks the spec "does this type carry a fix/addresses ref rule?" instead of `is ItemType.TASK`.

Net: a **typed engine** with a **runtime-defined vocabulary**. (Rejected alternative: synthesizing `StrEnum`s at runtime — pyright can't resolve dynamically-created members, so it defeats its own purpose.)

## The explicit trade-off (conscious choice, on the record)

Runtime-defined statuses mean **giving up pyright's compile-time exhaustiveness** in exchange for **load-time validation**. There is no way to have both "statuses defined in config" and "the compiler proves every status is handled." We accept the loss of enum-member exhaustiveness deliberately, and mitigate it with a strong `WorkflowSpec.validate()` (fail-closed on load) and an `sq workflow lint`.

## Format & reuse

- **TOML**, three separate bundled files (`default_workflow.toml`, `roles.toml`, `playbook.toml`) — keeps the "config is TOML" invariant; no second config language. Each file is independently overridable.
- **Reuses the partly-built overrides machinery** (`_overrides/` + `sq override`: scaffold / diff / drift / stamp). Each spec becomes an overridable artifact alongside templates and roles.

## Compatibility contract

- **All bundled default specs reproduce today's behavior EXACTLY** — **golden-locked** against frozen snapshots of today's Python source. Any squad that adds no override sees zero change; `sq repair` / `sq check` stay stable no-ops.
- **Additive-only overrides in v1**: projects may *add* types/statuses/machines/roles/playbook entries, not silently mutate built-in definitions.
- **Removing a status/type that the live index still references FAILS CLOSED** (lists offending items, like `sq remove` refusing on incoming refs).
- **Renames of built-in vocabulary go through migration** — reusing the existing `retype` machinery, which already rewrites IDs, parent links, and prose mentions atomically. They are an audited migration event, never a silent config edit.
- L1 (externalize, default==today) is an **additive** schema bump; full L3 (custom vocab) is **forward-incompatible** (older `sq` must hard-stop on the schema gate — it already does).

## Planned decomposition (roadmap)

Features are created Draft for sequencing; the spike gate must pass before F1/F2 are committed to implementation.

**Workflow axis (F1–F6):**
- **F1 (FEAT-207) — Externalize workflow into a bundled spec; enums intact; default == today (golden-locked).** The de-risk foundation. Risk: Med.
- **F2 (FEAT-208) — De-type models to `str` + spec-validated; reify the ~20 `is ItemType.X` checks as `TypeSpec` flags.** Risk: High (pyright/typing inversion — riskiest code change).
- **F3 (FEAT-209) — Project override of the spec (additive-only) + `sq workflow lint` + load-time fail-closed validation.** Risk: Med.
- **F4 (FEAT-210) — Custom types end-to-end (minimum viable: prefix/folder/machine/parents/aliases/badges); dynamic CLI app build; spec-derived renderer + CLAUDE.md sections; thin auto-generated `sq-<type>` skill.** Risk: High. **First user-visible value.**
- **F5 (FEAT-211) — Custom statuses & badges end-to-end** (filters/inbox/blocked/`STATUS_EMOJI` defaults; lifecycle auto-linearization). Risk: Med.
- **F6 (FEAT-212) — Custom sub-entity kinds + vocabulary rename migrations.** Risk: High. **May split into its own epic.**

**Config axis (FR, FP):**
- **FR — Externalize role catalog into a bundled `roles.toml`.** The 8 roles + dev-name pool moved from `_catalog.py` to a bundled TOML, loaded/validated, default == today (golden-locked). Risk: Low-Med (self-contained, no cross-cutting enum changes).
- **FP — Externalize playbook into a bundled `playbook.toml`.** `PLAYBOOK` (per-type overview/lifecycle/commands/role-guides) moved from `_interactions.py` to TOML; drives `sq-<type>` skill generation and `skills_for_role()`; default == today (golden-locked). Depends on FR (playbook references role slugs). Connects to F4: once the playbook is config-driven, custom types can get proper per-role guidance rather than the minimum-viable thin skill. Risk: Med.

**Minimum-viable custom type** (the scope-control lever): prefix + folder + machine + optional parents/aliases/badges, **reusing or omitting sub-entities**, with an auto-generated thin skill. Brand-new sub-entity kinds and rich role playbooks are stretch goals (F6/FP), not L3 v1.

**Product note on sequencing:** F1 and F2 deliver no user-visible change — they are pure foundation work. This is intentional: the spike-first gate and the de-typing refactor are prerequisites that must be clean before any user-facing custom vocabulary can safely land. The first user-visible value arrives at F4. FR and FP can proceed in parallel with the F1/F2 foundation once the spec loader/validation pattern is established.

## Spike-first gate (before any feature is committed)

A **throwaway F1+F2 spike** must validate the one irreversible assumption: build `WorkflowSpec` from today's enums, widen `Item.type`/`status` to `str` validated against the spec, mechanically reify the ~20 `is ItemType.X` checks, and prove **`uv run pyright && ruff && pytest` all stay green with the default-spec golden passing — with NO custom vocabulary yet**. If clean, the rest of the epic is mostly mechanical engineering. If ugly (identity checks won't reify, or pyright/ruff fight us), we learn the true cost before committing. Everything downstream (custom types, statuses, renderer) is comparatively low-uncertainty once de-typing is proven.

## `sq workflow` renderer note

The cheatsheet becomes config-derived and regenerates on `sq sync` (so agents learn a project's custom vocab) — but the renderer must **split** spec-rendered machine/type/alias sections from the **static** FEAT-13 stability-contract prose (ref-kinds table, retype, remove-vs-cancel) so a frozen-grammar contract is never accidentally made config-editable.

## Multi-backend note

Both `claude_code` and `agents_md` source their type list and workflow section from the loaded spec (via `managed_item_types()` → `spec.managed_types()`); custom types yield thin auto-generated skills symmetrically in both. No backend-specific divergence, provided the spec flows through the existing backend/roster plumbing rather than as a module global. Once FP lands, both backends source skill content from the loaded `PlaybookSpec` rather than the hardcoded `PLAYBOOK` dict.

## Epic-level success criteria ("done" from a product perspective)

The epic is complete when:

1. A team can add a new item type (`incident`, `change-request`, or any project-specific name) with its own prefix, folder, state machine, and optional parent rules entirely in `.overrides/workflow.toml` — with no code changes and no fork.
2. `sq workflow` renders the live config (not a static template), and `sq sync` regenerates agent skills to reflect custom types.
3. Existing squads that add no override are completely unaffected — `sq check`, `sq repair`, and all golden tests pass on the default spec.
4. `sq workflow lint` validates a project override and reports conflicts or invalid transitions clearly.
5. The role catalog (`roles.toml`) and playbook (`playbook.toml`) are externalized, golden-locked, and the Python source files they replace are retired.
6. Custom types can get proper per-role playbook guidance (not just the thin auto-generated skill) by declaring playbook entries in `playbook.toml`.
7. Documentation (`sq docs workflow`) reflects the config-driven model, including a worked example of defining a custom type.
8. The spike has passed (F1+F2 clean) and F6 scope has been explicitly drawn (in-epic or own-epic decision recorded).

## Non-goals (L3 v1 scope boundary)

- **Custom sub-entity kinds** (brand-new story/subtask/finding analogues with their own CLI verbs) — tracked as F6, may become its own epic. Not in L3 v1.
- **UI or web interface for editing any spec** — TOML files are the authoring surface; no editor tooling.
- **Mutating built-in type state machines, roles, or playbook entries via override** — additive-only in v1; changing a built-in's definition requires a migration.
- **Per-item-type role playbooks** auto-generated for custom types beyond the thin skill are a stretch goal pending FP landing.
- **Renaming built-in types (task → ticket)** without a migration — renames are audited migration events, never a silent config edit.


## Invariant — reserved vocabulary

Today the workflow loader enforces `set(spec.items) == set(ItemType)` and `set(spec.statuses) == set(Status)` (fail-closed), so the meta-types `role`/`skill`/`operator` and their statuses are required for free. Once de-typing (F2) relaxes that equality to allow custom vocabulary, that accidental guarantee disappears. The engine's own machinery (role backend, skill generation, operators) depends on those meta-types existing, so they — plus the structural statuses they need (e.g. `Active`/`Archived`, the sub-entity statuses) — become **reserved vocabulary**: a custom spec may ADD to the vocabulary but may not omit the reserved set, and the loader must fail closed if any reserved type/status is absent. Custom vocabulary is additive over the reserved core, never a replacement for it.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T13:10:55Z] Nina Product:
  - VALIDATED-WITH-NOTES — the epic is structurally sound and the architecture is well-grounded, but the original body was technically heavy with thin product framing. I augmented it (preserving all architect content) as follows:
  - Added 'Who needs this and why' section: names the concrete personas (Ops/SRE tracking incidents, compliance teams tracking controls/risks) and the without-this pain (shoehorn into task/bug or fork). Clarifies that existing users are unaffected unless they opt in — this was buried in the compatibility contract, not in the user-facing framing.
  - Added a product note on F1-F2 sequencing in the roadmap: first user-visible value is at F4, not F1. F1/F2 are pure foundation. That's the right call technically, but it needs to be stated explicitly so stakeholders don't expect visible change early. Also annotated F4 in-line as 'First user-visible value.'
  - Added 'Epic-level success criteria' (6 testable conditions for what done looks like from a product perspective) and 'Non-goals' (custom sub-entity kinds, UI editing, built-in mutation, rich role playbooks, silent renames) — both were missing entirely from the original body. The F6 split-into-own-epic recommendation is sensible and is preserved.
  - No concerns with scope or ambition. The compatibility contract is strong. The spike-first gate is appropriate. The one open product risk: F1-F2 are high-blast-radius internals with no user-visible result — the team should be prepared for a long foundation phase before any custom-vocabulary value ships. That's a sequencing reality to communicate, not a reason to change the plan.
- [2026-07-02T13:07:22Z] Catherine Manager:
  - Closing EPIC-206 Done: the config-driven-workflow mission is complete — FEAT-207/208/209/210/211 (externalize workflow, de-type, override, custom types, custom statuses) + FEAT-219/220 (roles + playbook specs) + FEAT-250 (de-globalize) all Done, default output byte-identical throughout (golden-locked). FEAT-212 (sub-entity kinds + rename migrations) was split to EPIC-280 (ADR-274); FEAT-271 (verb-first CLI grammar) re-parented to EPIC-38 as a separate axis. Matches ADR-274's 'clean shippable unit at F1–F5 + roles + playbook'.
<!-- sq:discussion:end -->
