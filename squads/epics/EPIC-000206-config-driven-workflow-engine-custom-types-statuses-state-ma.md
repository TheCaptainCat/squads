---
id: EPIC-000206
sequence_id: 206
type: epic
title: 'Config-driven workflow engine: custom types, statuses, state machines'
status: Draft
author: product-owner
refs:
- EPIC-000031
created_at: '2026-06-25T13:04:19Z'
updated_at: '2026-06-25T13:10:55Z'
---
<!-- sq:body -->
## Vision

Today the entire workflow — ticket **types** (`task`, `bug`, `decision`, …), **statuses**, per-type
**state machines**, the **terminal** set, and **parent rules** — is hardcoded in Python
(`_workflow.py`, `_models/_enums.py`). This epic makes it **fully config-driven with custom
vocabulary**: a project can define brand-new types (e.g. an `incident` type, prefix `INC`, folder
`incidents/`) and brand-new statuses with their own state machine (e.g. `Triage → Mitigating →
Resolved`) — none of which exist in today's enums — entirely in TOML. `sq workflow` renders the
**live loaded config** instead of today's static `workflow.md.j2`.

Grounded in the architecture study (Robert Architect, 2026-06-25). The study mapped the full coupled
surface and quantified the blast radius: ~152 `ItemType.*` refs across 23 files and ~21 `Status.*`
refs across 7 — but these split into cheap *generic dispatch* (`item.type`, `FOLDER_BY_TYPE[t]`)
versus ~20 expensive *hardcoded identity checks* (`item.type is ItemType.TASK/DECISION/SKILL`) that
encode workflow-spine semantics and are the real labor.

## Who needs this and why

**The constraint today:** every team using squads must fit their work into the built-in vocabulary (`task`, `bug`, `feature`, `decision`, `review`, `guide`). That works for software teams doing sprint-style delivery. It does not work once squads is used for:

- **Ops and SRE teams** that track `incident` and `change-request` items, with their own triage-to-resolution lifecycles (e.g. `Triage → Mitigating → Resolved → PostMortem`), not the `Draft → InProgress → Done` arc.
- **Compliance and security teams** that need `finding`, `control`, or `risk` types with custom severities and sign-off states.
- **Any team whose domain vocabulary doesn't map cleanly to software delivery** — the hardcoded type list is a vocabulary imposition, not a deliberate boundary.

Without this epic, every such team must either (a) shoehorn their work into `task`/`bug` with convention-based title prefixes — losing query, ref, and workflow fidelity — or (b) fork squads. Both are bad outcomes. Config-driven workflow removes the vocabulary imposition while keeping squads' coordination guarantees (stable IDs, query, refs, inbox, repair).

**Existing users are unaffected unless they opt in.** The bundled default spec reproduces today's behavior exactly; no team migrates unless they choose to.

## Recommended approach

A single loaded, validated **`WorkflowSpec`** value object (built from a bundled-default TOML,
optionally merged with a project override). The path:
- Model fields **widen from enums to `str`** (`Item.type`/`status`, sub-entity status) — frontmatter
  round-trips losslessly, so reading existing items needs no rewrite.
- The free functions (`can_transition`, `workflow_for`, `parent_allowed`, `is_open`, `parent_hint`)
  become **methods on `WorkflowSpec`** taking strings, validating against the loaded spec.
- The ~20 hardcoded `is ItemType.X` spine checks get **reified as declared capability flags on a
  `TypeSpec`** (e.g. `is_meta`, `subentity_kind`, `ref_rules`, `enforce_parent`). The engine asks the
  spec "does this type carry a fix/addresses ref rule?" instead of `is ItemType.TASK`.

Net: a **typed engine** with a **runtime-defined vocabulary**. (Rejected alternative: synthesizing
`StrEnum`s at runtime — pyright can't resolve dynamically-created members, so it defeats its own
purpose.)

## The explicit trade-off (conscious choice, on the record)

Runtime-defined statuses mean **giving up pyright's compile-time exhaustiveness** in exchange for
**load-time validation**. There is no way to have both "statuses defined in config" and "the compiler
proves every status is handled." We accept the loss of enum-member exhaustiveness deliberately, and
mitigate it with a strong `WorkflowSpec.validate()` (fail-closed on load) and an `sq workflow lint`.

## Format & reuse

- **TOML**, under a `[workflow.*]` table in `.squads.toml` (or a sibling `.squads.workflow.toml` the
  loader merges) — keeps the "`.squads.toml` is the config" invariant; no second config language. The
  state machine is just `status → [statuses]` maps + scalars, which TOML expresses cleanly. YAML was
  considered and rejected (marginal readability gain, second parser).
- **Reuses the partly-built overrides machinery** (`_overrides/` + `sq override`: scaffold / diff /
  drift / stamp). The workflow spec becomes the **third overridable artifact** alongside templates
  and roles — this is not greenfield.

## Compatibility contract

- **Bundled default spec reproduces today's behavior EXACTLY** (types, prefixes, folders, statuses,
  machines, terminal set, parent rules, badges) — **golden-locked** against a frozen snapshot built
  from today's `WORKFLOWS`/`_enums`. Any squad that adds no override sees zero change; `sq repair` /
  `sq check` stay stable no-ops.
- **Additive-only overrides in v1**: projects may *add* types/statuses/machines, not silently mutate a
  built-in type's machine.
- **Removing a status/type that the live index still references FAILS CLOSED** (lists offending items,
  like `sq remove` refusing on incoming refs).
- **Renames of built-in vocabulary go through migration** — reusing the existing `retype` machinery,
  which already rewrites IDs, parent links, and prose mentions atomically. They are an audited
  migration event, never a silent config edit.
- L1 (externalize, default==today) is an **additive** schema bump; full L3 (custom vocab) is
  **forward-incompatible** (older `sq` must hard-stop on the schema gate — it already does).

## Planned decomposition (roadmap — features NOT created yet)

Features will be **drafted later** by the product owner / tech lead once the spike clears the gate
below. Intended phased breakdown (one epic), each with one-line scope + risk:

- **F1 — Externalize workflow into a bundled spec; enums intact; default == today (golden-locked).**
  The de-risk foundation. Risk: Med (many call sites, behavior-preserving).
- **F2 — De-type models to `str` + spec-validated; reify the ~20 `is ItemType.X` checks as `TypeSpec`
  flags.** Risk: High (the pyright/typing inversion — the riskiest code change).
- **F3 — Project override of the spec (additive-only) via the existing overrides system + `sq workflow
  lint` + load-time fail-closed validation.** Risk: Med (merge-semantics decision is the crux).
- **F4 — Custom types (minimum viable: prefix/folder/machine/parents/aliases/badges); dynamic CLI app
  build from spec; spec-derived renderer + CLAUDE.md/AGENTS.md sections; thin auto-generated
  `sq-<type>` skill.** Risk: High (CLI startup-ordering; skill-generation degradation; touches the
  FEAT-000178 SKILL-id allocation). **First user-visible value** — a team can define and use a custom type end-to-end.
- **F5 — Custom statuses & badges end-to-end** (filters/inbox/blocked/`STATUS_EMOJI` defaults;
  lifecycle auto-linearization in the renderer). Risk: Med (mostly mechanical once F2 lands).
- **F6 — Custom sub-entity kinds + safe vocabulary-rename migrations.** Risk: High. **May split into
  its own epic** — sub-entity kinds are a second deep surface (machines, summary columns, `add-<kind>`
  CLI verbs). Recommend drawing the L3-v1 scope line before F6.

**Minimum-viable custom type** (the scope-control lever): prefix + folder + machine + optional
parents/aliases/badges, **reusing or omitting sub-entities**, with an auto-generated thin skill.
Brand-new sub-entity kinds and rich role playbooks are stretch goals (F6), not L3 v1.

**Product note on sequencing:** F1 and F2 deliver no user-visible change — they are pure foundation work. This is intentional: the spike-first gate and the de-typing refactor are prerequisites that must be clean before any user-facing custom vocabulary can safely land. The first user-visible value arrives at F4. Framing F1–F2 as foundation work (not as value-delivering features) sets the right expectation.

## Spike-first gate (before any feature is committed)

A **throwaway F1+F2 spike** must validate the one irreversible assumption: build `WorkflowSpec` from
today's enums, widen `Item.type`/`status` to `str` validated against the spec, mechanically reify the
~20 `is ItemType.X` checks, and prove **`uv run pyright && ruff && pytest` all stay green with the
default-spec golden passing — with NO custom vocabulary yet**. If clean, the rest of the epic is
mostly mechanical engineering. If ugly (identity checks won't reify, or pyright/ruff fight us), we
learn the true cost before committing. Everything downstream (custom types, statuses, renderer) is
comparatively low-uncertainty once de-typing is proven.

## `sq workflow` renderer note

The cheatsheet becomes config-derived and regenerates on `sq sync` (so agents learn a project's
custom vocab) — but the renderer must **split** spec-rendered machine/type/alias sections from the
**static** FEAT-000013 stability-contract prose (ref-kinds table, retype, remove-vs-cancel) so a
frozen-grammar contract is never accidentally made config-editable.

## Multi-backend note

Both `claude_code` and `agents_md` source their type list and workflow section from the loaded spec
(via `managed_item_types()` → `spec.managed_types()`); custom types yield thin auto-generated skills
symmetrically in both. No backend-specific divergence, provided the spec flows through the existing
backend/roster plumbing rather than as a module global.

## Epic-level success criteria ("done" from a product perspective)

The epic is complete when:

1. A team can add a new item type (`incident`, `change-request`, or any project-specific name) with its own prefix, folder, state machine, and optional parent rules entirely in `.squads.toml` — with no code changes and no fork.
2. `sq workflow` renders the live config (not a static template), and `sq sync` regenerates agent skills to reflect custom types.
3. Existing squads that add no override are completely unaffected — `sq check`, `sq repair`, and all golden tests pass on the default spec.
4. `sq workflow lint` validates a project override and reports conflicts or invalid transitions clearly.
5. Documentation (`sq docs workflow`) reflects the config-driven model, including a worked example of defining a custom type.
6. The spike has passed (F1+F2 clean) and F6 scope has been explicitly drawn (in-epic or own-epic decision recorded).

## Non-goals (L3 v1 scope boundary)

- **Custom sub-entity kinds** (brand-new story/subtask/finding analogues with their own CLI verbs) — tracked as F6, may become its own epic. Not in L3 v1.
- **UI or web interface for editing the workflow spec** — TOML in `.squads.toml` is the authoring surface; no editor tooling.
- **Mutating built-in type state machines via override** — additive-only in v1; changing a built-in's transitions requires a migration.
- **Per-item-type role playbooks** auto-generated for custom types are a stretch goal, not a blocker. The thin auto-generated `sq-<type>` skill (F4) is sufficient for L3 v1.
- **Renaming built-in types (task → ticket)** without a migration — renames are audited migration events, never a silent config edit.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T13:10:55Z] Nina Product:
  - VALIDATED-WITH-NOTES — the epic is structurally sound and the architecture is well-grounded, but the original body was technically heavy with thin product framing. I augmented it (preserving all architect content) as follows:
  - Added 'Who needs this and why' section: names the concrete personas (Ops/SRE tracking incidents, compliance teams tracking controls/risks) and the without-this pain (shoehorn into task/bug or fork). Clarifies that existing users are unaffected unless they opt in — this was buried in the compatibility contract, not in the user-facing framing.
  - Added a product note on F1-F2 sequencing in the roadmap: first user-visible value is at F4, not F1. F1/F2 are pure foundation. That's the right call technically, but it needs to be stated explicitly so stakeholders don't expect visible change early. Also annotated F4 in-line as 'First user-visible value.'
  - Added 'Epic-level success criteria' (6 testable conditions for what done looks like from a product perspective) and 'Non-goals' (custom sub-entity kinds, UI editing, built-in mutation, rich role playbooks, silent renames) — both were missing entirely from the original body. The F6 split-into-own-epic recommendation is sensible and is preserved.
  - No concerns with scope or ambition. The compatibility contract is strong. The spike-first gate is appropriate. The one open product risk: F1-F2 are high-blast-radius internals with no user-visible result — the team should be prepared for a long foundation phase before any custom-vocabulary value ships. That's a sequencing reality to communicate, not a reason to change the plan.
<!-- sq:discussion:end -->
