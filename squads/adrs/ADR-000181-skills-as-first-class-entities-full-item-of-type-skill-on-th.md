---
id: ADR-000181
sequence_id: 181
type: decision
title: 'Skills as first-class entities: full Item of type SKILL on the role/operator
  meta-type profile'
status: Proposed
author: architect
refs:
- FEAT-000178:addresses
description: A skill is a full Item of the existing ItemType.SKILL with the lightweight
  role/operator profile (Active/Archived, no sub-entities), not a separate lighter
  class; frontmatter stamped onto the existing body file via migration
created_at: '2026-06-23T12:59:27Z'
updated_at: '2026-06-23T12:59:38Z'
---
<!-- sq:body -->
## Context

`FEAT-000178` wants skills to become first-class ID'd entities (`SKILL-…`), tracked in
`.squads.json`, queryable and referenceable. Today skills live as managed files under
`agents/skills/` with thin `.claude/` pointers, carry no id, and appear nowhere in the index. The
feature routes one design question to this ADR:

> Is a `Skill` a **full `Item` type** (same pydantic model, sub-entity machinery, workflow states,
> rendering pipeline) — or a **lighter id'd entity** "the way operators currently are"?

**A grounding correction the ADR must record.** Inspecting the code, the premise that operators are
a "lighter, non-Item" entity is inaccurate. `ItemType` (`_models/_enums.py`) **already** defines
both `OPERATOR` and `ROLE` — and `SKILL` — with prefixes (`OP`, `ROLE`, `SKILL`) and folders
(`operators`, `agents/roles`, `agents/skills`). `sq list -t operator` and `sq list -t role` return
real, indexed `Item`s today (e.g. `OP-000010 Pierre Chat`, `ROLE-000001..009`), each with a status
(`Active`), allocated from the **single global counter**, and reconstructable by `sq repair`. There
is no separate "lighter entity" class in the model. So the genuine choice is **not** "Item vs.
operator-style"; it is **how heavy a profile of the existing `Item` machinery `SKILL` should adopt**
— specifically its **workflow** and **sub-entity** surface — given that `SKILL` is *already* an
`ItemType` and roles/operators show the established pattern for meta-types.

The infrastructure is in fact mostly in place: `SKILL` exists in `ItemType` with prefix `SKILL` and
folder `agents/skills`; the model keys on integer `sequence_id`; `from_frontmatter` /
`to_frontmatter_dict` already handle any type. What is missing is (a) seeding/migrating actual
`SKILL-…` items, (b) deciding the workflow/sub-entity profile, and (c) the relationship between the
**indexed skill item** and the **managed skill body file** that already exists.

## Decision

**1. A skill is a full `Item` of the existing `ItemType.SKILL`, following the role/operator pattern —
not a new, separate lightweight class.** Reusing the one `Item` model is what preserves every
invariant for free: global counter via `IndexStore.transaction()`, frontmatter-as-source-of-truth,
`sq repair` reconstruction, ref/backref inversion, and `prefix→folder` resolution. Introducing a
parallel lighter entity would fork the model, the index schema, and `repair` for no benefit the
existing `Item` doesn't already give — roles and operators prove the meta-type pattern works without
the work-item ceremony.

**2. Adopt the *meta-type* profile (like `ROLE`/`OPERATOR`), not the *work-item* profile.** "Full
Item" does **not** mean skills get the task/feature lifecycle. Skills take the lightweight status set
already defined for roles/skills — `Active` / `Archived` (both exist in `Status`) — and **no
sub-entities** (no stories/subtasks/findings). This matches `WORK_TYPES` in `_enums.py`, which
deliberately **excludes** the agent/operator meta-types from retyping and the work lifecycle. Skills
are reference assets, not units of work; giving them `Draft→Ready→InProgress→Done` would be
meaningless. They remain fully **referenceable** (`sq <type> <n> ref add SKILL-… --kind related`),
which is the feature's primary user value (US1).

So: full `Item`, meta-type profile — the same weight as a role, which is the honest reading of the
feature's "operator-style" instinct once we correct the premise.

**3. The skill body file is the item file.** A skill already has a managed body under
`agents/skills/<slug>.md`. Rather than create a *second* file, the migration **stamps sq
frontmatter** (`id`, `type: skill`, `title`, `status`, `author`, `schema_version`) onto that
existing file, exactly as the feature's scope says ("leaving the skill bodies and pointer files
intact"). The `agents/skills/` folder mapping already routes there. The `.claude/` pointers stay
pointers (invariant 5). The managed skill body uses sq markers today, so it is already
marker-/region-compatible (and stays so under the `FEAT-000177` codec contract).

**4. Migration + fresh-init parity, deterministic ids.** Acceptance #4 requires an upgraded squad to
be "indistinguishable from a fresh `sq init`." Both paths must allocate `SKILL-…` ids in the **same
deterministic order** (recommend: lexical by skill slug) so the same skill gets a comparable id
across squads. The ordered migration (`sq migrate up`) walks `agents/skills/`, allocates ids through
`IndexStore.transaction()` in that fixed order, stamps frontmatter, then runs `repair` + stamps the
new `SCHEMA_VERSION`. `sq init` seeds the bundled skills with the same ordering so US3 holds.

**5. Schema bump is unpinned, set at release-cut.** This adds the first *populated* `SKILL` items +
the migration, so it bumps `SCHEMA_VERSION` (the feature anticipates `0.5`, decided at cut time per
project convention — `_models/_schema.py` is the single source of truth; compare with `schema_tuple`,
never raw string `<`/`>`).

## Relationship to FEAT-000176 / FEAT-000177

Skills become ordinary `Item`s, so they ride the **same** `ItemStore` seam those two ADRs define:
they get located (prefix/layout) by the `FEAT-000176` locator and serialized by the `FEAT-000177`
codec like any other type. A custom global prefix would re-prefix `SKILL-…` along with everything
else; a JSON/XML squad would serialize skill items through the active codec. No skill-specific
storage path is introduced — that is the payoff of choosing "full `Item`."

## Consequences

- **Minimal new model surface.** `SKILL` already exists in `ItemType`; the work is seeding/migration,
  a status profile (`Active`/`Archived`), and wiring `sq skill <n> show` / `sq list -t skill`. No new
  pydantic model, no index-schema fork.
- **Invariants preserved by construction** — global counter, frontmatter truth, repair, refs all come
  from the shared `Item` path.
- **Skills are not work items.** No stories/subtasks/findings, no work lifecycle, excluded from
  `WORK_TYPES`/retype — a deliberate scope line that can be revisited later without reversing this
  decision (adding sub-entities to a meta-type is additive).
- **One file per skill, not two.** Frontmatter is stamped onto the existing body file; no duplication,
  pointers unchanged.
- **Determinism is load-bearing for acceptance #4** — the migration and `sq init` must share one
  ordering; this is the main thing implementation tasks must get right and test.
- **Existing squads:** `migrate up` is required to pick up skill ids on an upgrade; default markdown
  squads otherwise unaffected until they migrate.

## Alternatives considered

- **A new, separate lightweight non-`Item` skill record.** Rejected: forks the model, index schema,
  and `repair`; duplicates what `Item` + the role/operator meta-type pattern already provides. The
  feature's "operator-style" framing assumed operators were non-`Item`; they are not.
- **Full work-item profile (workflow + sub-entities).** Rejected: skills are reference assets, not
  units of work; `Draft→…→Done` and stories are meaningless for them, and `WORK_TYPES` already
  excludes meta-types from that lifecycle.
- **Two files (keep the managed body, add a separate index stub).** Rejected: violates one-source-of-
  truth ergonomics and complicates `repair`; stamping frontmatter onto the existing body file is
  simpler and matches the feature's "bodies intact" scope.

## Status

Proposed — drafting only. No implementation, tasks, or feature transition until accepted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
