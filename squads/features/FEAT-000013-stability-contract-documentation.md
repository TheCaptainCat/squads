---
id: FEAT-000013
sequence_id: 13
type: feature
title: Stability contract documentation
status: Ready
parent: EPIC-000012
author: product-owner
priority: high
description: docs/stability.md + README tiering the public surfaces and what each
  promises through 1.0
subentities:
- local_id: US1
  title: As a squad user on 0.x, I want a written promise that my items reach 1.0
    via sq migrate up, so that adopting squads before 1.0 is safe
  status: Todo
- local_id: US2
  title: As a script author, I want to know which CLI and --json surfaces are SemVer-stable,
    so that my automation survives upgrades
  status: Todo
- local_id: US3
  title: As an integrator, I want internals (Python import paths, generated .claude/
    files) explicitly marked non-public, so that I don't build on the wrong layer
  status: Todo
created_at: '2026-06-10T12:40:59Z'
updated_at: '2026-06-12T15:44:22Z'
---
<!-- sq:body -->
## Problem

We *behave* as if the `.md` format, the CLI grammar, and the `--json` shapes are stable, but
nothing says so. A user adopting squads today cannot tell which surfaces are safe to build on and
which are internals that may shift without notice. Unstated promises are the worst kind: we are
bound by them anyway, without having chosen their scope.

## Value

A written, tiered contract turns 1.0 from a vibe into a checkable claim. Users know exactly what
they can rely on; we know exactly what we are allowed to change. Every other feature in this epic
gets its acceptance bar from this document.

## Scope

A `docs/stability.md` plus a short README paragraph, tiering the public surfaces:

1. **Durable `.md` format** — the strongest promise: any squad created on any 0.x release reaches
   1.0 intact via `sq migrate up`. The user's items are their data, never hostage to our refactors.
2. **CLI grammar** — commands, arguments and options are SemVer-stable from 1.0.
3. **`--json` output shapes** — stable; additive changes only within a major version.
4. **Python import paths** — explicitly *not* public; the underscore convention is the contract.
5. **Generated `.claude/` files** — regenerable, never migrated; deleting them loses nothing.

This includes settling the **post-1.0 `schema_version` scheme** (today a dotted string tracking
the introducing release) — the decision belongs to the contract, not to a migration PR.

## Acceptance

- `docs/stability.md` exists, covers the five tiers above, and states the migration promise verbatim.
- The README links to it with a one-paragraph summary.
- The post-1.0 `schema_version` scheme is decided and recorded (ADR) and reflected in the doc.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 13 add-story "As a <role>, I want … so that …"`; track with `sq feature 13 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a squad user on 0.x, I want a written promise that my items reach 1.0 via sq migrate up, so that adopting squads before 1.0 is safe |
| US2 | Todo |  | As a script author, I want to know which CLI and --json surfaces are SemVer-stable, so that my automation survives upgrades |
| US3 | Todo |  | As an integrator, I want internals (Python import paths, generated .claude/ files) explicitly marked non-public, so that I don't build on the wrong layer |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a squad user on 0.x, I want a written promise that my items reach 1.0 via sq migrate up, so that adopting squads before 1.0 is safe

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** docs/stability.md states the migration promise verbatim — any squad created on any 0.x release reaches 1.0 intact via `sq migrate up` — and names it the strongest tier.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a script author, I want to know which CLI and --json surfaces are SemVer-stable, so that my automation survives upgrades

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the doc tiers CLI grammar and --json shapes as SemVer-stable from 1.0, says what 'additive change' means for JSON, and the README paragraph links to it.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an integrator, I want internals (Python import paths, generated .claude/ files) explicitly marked non-public, so that I don't build on the wrong layer

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** Python import paths are documented as not public (underscore convention is the contract) and generated .claude/ files as regenerable-never-migrated; the post-1.0 schema_version scheme is settled and recorded in an ADR linked from the doc.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:54:11Z] Nina Product:
  - Sequencing note (from the readiness review): this doc is late-binding — it records decisions made by FEAT-000019/027/035/023/024/016/032. Start it early as a living draft, but its Done means 'reflects final decisions': it closes last in the epic.
- [2026-06-11T21:28:59Z] Catherine Manager:
  - Obligations accumulated from shipped features (so far): (1) FEAT-000019 — document the addressing rule in the CLI-grammar tier: anywhere an item is named, both the full ID and the bare number are accepted; addressing an existing item through the wrong type is an error. (2) FEAT-000035 / ADR-000049 — state the ref-kind policy verbatim: vocabulary closed in 1.0 (eight kinds, unknown kinds rejected); a project-declared custom-kind extension is reserved for a future release and will be additive and non-breaking, the built-in kinds' meanings stay fixed.
  - Own scope reminder: the post-1.0 schema_version scheme needs its own ADR before the doc can state it.
- [2026-06-11T21:31:02Z] Pierre Chat:
  - Sequencing decision: this feature runs LAST in the epic — it's the capstone. The contract decisions are made feature-by-feature as the epic progresses (each recorded where it happens, ADR or feature body) and deferred here via comments; by the time this runs it's a pure writing pass over settled facts, plus its one piece of original work: the post-1.0 schema_version ADR. Writing it earlier would mean rewriting after every grammar/format-touching feature.
  - Discipline for the loops until then: any feature that settles a format or grammar question must record the decision on its own item and leave a deferral comment here — the obligations list above is the running bill. @manager enforces this in every loop.
  - Pairs naturally with the other doc-flavored tail work: FEAT-000018 (architecture backfill) and FEAT-000016 (AGENTS.md backend) — consider scheduling the three together with @tech-writer.
- [2026-06-12T11:58:22Z] Nina Product:
  - Deferral obligation from FEAT-000064 (agent-type grammar alignment, 2026-06-12).
  - Decisions to record in the CLI-grammar tier of the stability contract:
  - (1) Item-first grammar for agent-type groups: role, skill, and operator commands that address an existing item follow 'sq <type> <id|n> <verb>' — same as every other item type. The historical verb-first form is removed pre-1.0.
  - (2) Creation commands stay verb-first at the group level ('sq role activate <slug>', 'sq skill add <name>', 'sq operator add <name>') — these receive a catalog slug or a new name, not an existing item ID.
  - (3) Bundled catalog: 'sq role catalog' is the dedicated subcommand for the bundled-but-not-activated role catalog (slug, name, title, default). 'sq role list --available' is gone.
  - (4) Standalone list commands removed: 'sq role list', 'sq skill list', 'sq operator list' are removed in favor of 'sq list -t <type>'. No deprecation shim — pre-1.0 removal is allowed.
  - (5) Slug resolution: for role show/regen/rm, slug is a valid address form in addition to full ID and bare number.
- [2026-06-12T14:30:00Z] Catherine Manager:
  - Deferral from FEAT-000018 (architecture backfill, shipped): the retroactive ADR record now exists — ADR-000071..078 (frontmatter-as-truth, global counter, forward-only refs, marker-safe editing, pluggable backends, schema-version scheme, injectable clock, module privacy), all Accepted, cross-linked with GUIDE-000079 (the architecture guide, Published). The capstone doc can cite ADR numbers directly; the schema_version and Python-floor ADRs called for by this feature and FEAT-000017 attach to the same record when authored.
- [2026-06-12T15:28:54Z] Olivia Lead:
  - Deferral / contract obligation from FEAT-000015 breakdown (TASK-000082/083/084): two surfaces become stability-contract material and must be reflected here when this feature documents the tiers.
  - 1) **`--json` shapes** — the JSON emitted by every read command (list, tree, inbox, search, blocked, workload, mine, show, refs, create, plus the newly-added check and sub-entity list). TASK-000084 freezes these with golden files; the field-level shapes are the public promise to document in docs/stability.md.
  - 2) **Exit-code table** — 0 success / 1 squads runtime error (incl. schema mismatch and check failures) / 2 usage error. TASK-000083 documents and tests it. **Open contract question**: should `check` failures get a distinct code (e.g. 3) vs generic error 1, so CI can distinguish 'check found issues' from 'command errored'? Needs a product/contract decision before we freeze. cc @product-owner
  - Not freezing anything here yet — flagging the obligation so the stability doc covers both surfaces and the agreed exit-code semantics.
- [2026-06-12T15:30:02Z] Robert Architect:
  - Deferral: ADR-000085 (Proposed) settles the project-level override layout for FEAT-000014. Once accepted, the durable contract must list these surfaces: the override root `<squad-dir>/.overrides/{templates,roles}/` (templates sub-tree mirroring bundled template names 1:1, roles as `<slug>.toml`); per-file precedence (project override → bundled default, presence is the override, templates override whole-file, roles merge field-wise by slug); the staleness contract (`squads:override-base:<version>` stamp, `sq check` warns on version drift and errors on missing required markers, valid overrides always render, `sq migrate` never rewrites overrides); and the naming contract (names in ROLE-item `extra.full_name`, slugs canonical and not renamable, unnamed roles fall back to the bundled pool). Folding into the contract waits on acceptance. @manager
- [2026-06-12T15:44:22Z] Olivia Lead:
  - Follow-up to my 2026-06-12 deferral: both open contract points are now settled by op-pierre (2026-06-12).
  - Exit-code table — **decided**: check failures get a distinct exit code **3**; 1 stays the generic squads runtime error (incl. schema mismatch); 2 stays usage error. The earlier open question is resolved. TASK-000083 implements/documents/tests it.
  - --json surface — **expanded**: the role/skill/operator catalog viewers join the frozen --json surface (added by ruling, alongside check and the sub-entity list commands). repair/docs/workflow stay table-only. TASK-000082 closes these; TASK-000084 pins their shapes. All of this is the contract to document when this feature writes the stability tiers.
<!-- sq:discussion:end -->
