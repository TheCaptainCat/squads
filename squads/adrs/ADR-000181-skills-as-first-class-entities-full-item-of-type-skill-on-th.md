---
id: ADR-000181
sequence_id: 181
type: decision
title: 'Skills as first-class entities: full Item of type SKILL on the role/operator
  meta-type profile'
status: Accepted
author: architect
refs:
- FEAT-000178:addresses
description: A skill is a full Item of the existing ItemType.SKILL with the lightweight
  role/operator profile (Active/Archived, no sub-entities), not a separate lighter
  class; frontmatter stamped onto the existing body file via migration
created_at: '2026-06-23T12:59:27Z'
updated_at: '2026-06-25T07:56:42Z'
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
folder `agents/skills` (**no new enum entry is needed**); the model keys on integer `sequence_id`;
`from_frontmatter` / `to_frontmatter_dict` already handle any type. What is missing is (a)
seeding/migrating actual `SKILL-…` items, (b) deciding the workflow/sub-entity profile, and (c) the
relationship between the **indexed skill item** and the **managed skill body file** that already
exists — including how that file behaves under `sq sync`, which today regenerates it (see decision
#3).

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

**3. The skill body file is the item file — and its regeneration must become frontmatter-preserving,
mirroring the role pattern.** A skill already has a managed body under `agents/skills/`. Rather than
create a *second* file, the design **stamps sq frontmatter** (`id`, `sequence_id`, `type: skill`,
`title`, `status`, `author`, `schema_version`) onto that existing file — one file, the `.claude/`
pointers stay pointers (invariant 5). The `agents/skills/` folder mapping already routes there.

The skill item file follows the **standard meta-type filename convention** — `agents/skills/SKILL-<NNNNNN>-<slug>.md`
— consistent with how every other type names its file, including the two meta-types this ADR models
skills on: roles are `agents/roles/ROLE-000001-manager.md` and operators are
`operators/OP-000010-op-pierre.md`. It is **not** the bare `<slug>.md` (e.g. `greeting.md`) the
managed files used before this feature; that legacy name predates skills being indexed items and
must not be locked in. The rest of #3's intent is unchanged: still **one file per skill**
(frontmatter stamped onto the body, not a second file), bodies intact, and the `.claude/` pointer
dir stays **keyed by slug** — `.claude/skills/<slug>/SKILL.md` — but the body path it references
updates to the renamed convention-correct file.

This is only safe if `sq sync`'s skill-body regeneration is made **frontmatter-preserving /
marker-safe**, because today it is **not**. As built, `sq sync` rewrites each managed skill body via
a **blunt full-file overwrite** of pure template output that carries no frontmatter
(`_write_managed_skill` → `_aio.write_text(body_path, body)`, in
`_backends/_claude_code/_backend.py:107`; the per-`SKILL` sync loop in
`_services/_maintenance.py` only regenerates the `.claude/` pointer, not the body). Stamping
frontmatter onto that file as-is would mean the **next `sq sync` wipes the `id`/`sequence_id`/`status`
/`schema_version`** — destroying the stable identity the feature exists to provide.

The required design property (stated at the design level, not as code): the skill-body regen path
must touch **only the rendered body region and leave frontmatter intact**, exactly the way roles are
already regenerated — `_regen_role_body` (`_services/_maintenance.py:125`) reads the existing role
item file and replaces *only* the `sq:body` region via a marker-safe section edit (invariant 3),
never the frontmatter. The skill body must therefore adopt the same `sq:body` region structure an
item file uses, and `sq sync` must regenerate skills through that same read-only-the-body path
(equivalently: load the skill `Item` and re-emit preserved frontmatter + freshly rendered body —
round-tripping through the index rather than re-rendering a bare template). The managed skill body
already uses sq markers, so it is region-compatible; this decision pins that the regen path must
*use* that structure rather than overwrite the whole file (and it stays so under the `FEAT-000177`
codec contract).

**4. Identity is allocated once; `sq sync` is idempotent on an already-stamped skill.** A skill's
`id`/`sequence_id` are allocated **exactly once** — at migration of an existing squad, or at first
`sq init` seeding — and **never reallocated**. Re-running `sq sync` on a squad whose skills are
already stamped must **not** change any existing skill's id (it only refreshes pointers and the body
region per decision #3). This idempotence is a distinct guarantee from the initial-allocation
determinism in decision #5: #5 governs *what number a skill first gets*; this clause governs that
*sync never churns it afterwards*. Both are load-bearing for the referenceability in US1.

**5. Migration + fresh-init parity: deterministic *ordering*, not identical numbers.** Acceptance #4
asks an upgraded squad to be "indistinguishable from a fresh `sq init`." Read precisely, that can
only mean **ordering parity**, not byte-identical numeric ids: the **single global counter** makes
identical `SKILL-…` numbers impossible on an already-populated squad (a migrating squad has already
consumed counter values for its existing items, so its skills necessarily land on different numbers
than a fresh init's). What must match is the **relative allocation order** of skills. Both paths
allocate `SKILL-…` ids in the same fixed order — **recommend: lexical by skill slug** — so the same
skill sorts to the same position in both squads even when its absolute number differs. The ordered
migration (`sq migrate up`) walks `agents/skills/` in that order, allocates ids through
`IndexStore.transaction()`, stamps frontmatter, then runs `repair` + stamps the new
`SCHEMA_VERSION`; `sq init` seeds the bundled skills in the identical order so US3 holds. The
feature's acceptance #4 should be tightened to assert **ordering parity (lexical-by-slug)**, not
identical ids.

As part of the same `0.4 → 0.5` migration, `sq migrate up` must **rename** each legacy
`agents/skills/<slug>.md` to `agents/skills/SKILL-<NNNNNN>-<slug>.md` (decision #3's convention) and
rewrite the `.claude/skills/<slug>/SKILL.md` pointer to reference the new body path. The rename must
be **idempotent** — re-running migration on a squad whose skill files already carry the
convention-correct name is a no-op. Fresh `sq init` seeds skills with the convention-correct name
from the start, so it never needs the rename.

**6. Schema bump is unpinned, set at release-cut.** This adds the first *populated* `SKILL` items +
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

- **Minimal new model surface.** `SKILL` already exists in `ItemType` (no new enum entry); the work
  is seeding/migration, a status profile (`Active`/`Archived`), wiring `sq skill <n> show` /
  `sq list -t skill`, and making the skill-body regen path frontmatter-preserving. No new pydantic
  model, no index-schema fork.
- **The sync regen path is the riskiest change.** Decision #3 requires converting the skill-body
  write from a full-file overwrite to a marker-safe body-region replacement (the role pattern). This
  is the one place the existing code is actively unsafe for stamped frontmatter; implementation must
  cover it with a test that runs `sq sync` twice and asserts a skill's `id`/`sequence_id` are
  unchanged.
- **Invariants preserved by construction** — global counter, frontmatter truth, repair, refs all come
  from the shared `Item` path; invariant 3 (marker-safe edits) now explicitly covers skill bodies.
- **Skills are not work items.** No stories/subtasks/findings, no work lifecycle, excluded from
  `WORK_TYPES`/retype — a deliberate scope line that can be revisited later without reversing this
  decision (adding sub-entities to a meta-type is additive).
- **One file per skill, not two.** Frontmatter is stamped onto the existing body file; no duplication.
  The file follows the standard `agents/skills/SKILL-<NNNNNN>-<slug>.md` convention (like ROLE/OP),
  so migration renames the legacy `<slug>.md` and rewrites the slug-keyed `.claude` pointer to the
  new path; pointers stay slug-keyed and stay pointers.
- **Determinism is ordering parity, not identical ids** (decision #5). The migration and `sq init`
  must share one lexical-by-slug ordering; the global counter makes identical numbers impossible on a
  populated squad, so acceptance #4 is satisfied by matching *order*, and should be worded that way.
- **Idempotent sync** (decision #4) — re-running `sq sync` never reallocates or changes an existing
  skill's id; allocation happens once, at migration or first init.
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
- **Keep the full-file overwrite and re-stamp frontmatter on every sync.** Rejected: it would force
  sync to read the existing file, re-derive the id, and re-emit it on every run anyway — i.e. it
  collapses into the frontmatter-preserving path of decision #3, but more fragilely (any miss
  silently re-churns the id). The marker-safe body-region replacement is the clean form.

## Status

Accepted.

**Amended 2026-06-25 (architect), post-implementation, decision still Accepted.** A gap surfaced
after implementation: skill body files were left slug-named (`agents/skills/greeting.md`) instead of
the `<PREFIX>-<NUM>-<slug>.md` filename convention every other type uses (roles
`ROLE-000001-manager.md`, operators `OP-000010-op-pierre.md`). Decision #3's original wording
(frontmatter stamped onto "the existing `agents/skills/<slug>.md` file") read literally locked in the
non-standard name. This amendment clarifies decision #3, the migration text (decision #5), and the
"one file per skill" consequence to require the standard `agents/skills/SKILL-<NNNNNN>-<slug>.md`
filename and an idempotent `0.4 → 0.5` rename of legacy files + pointer rewrite. No other section is
reopened; the core decision (skill = full `Item`, meta-type profile, one file, frontmatter-preserving
sync) is unchanged.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T15:02:29Z] Catherine Manager:
  - @architect — before this moves toward Accepted, one open interaction to settle: skill body files are regenerated by `sq sync` (headers say "regenerated by sq sync; do not edit by hand"). If a skill is a full Item with sq frontmatter stamped onto that same body file, does `sq sync` regeneration preserve the stamped frontmatter (id, sequence_id, schema_version), or does it churn/overwrite it? ID stability across sync runs is load-bearing for the referenceability the feature exists for (US1) and for the determinism in acceptance #4. Please check the sync regeneration path and record the answer here.
- [2026-06-24T15:03:44Z] Robert Architect:
  - Investigated the sync regeneration path for managed skill bodies. Finding: as decision #3 is written today, sync WOULD churn/overwrite stamped frontmatter — ID is NOT stable. Skill body files (e.g. squads/agents/skills/squads.md) currently carry no frontmatter; they're pure rendered prose. During sync, the SKILL-item loop (_services/_maintenance.py:90-92) calls only backend.generate_skill_entry, which writes the .claude/ POINTER (_backends/_claude_code/_backend.py:207), not the body. The body files are (re)written separately by write_managed -> _write_managed_skill (_backend.py:107-128) via _aio.write_text(body_path, body) — a FULL-FILE OVERWRITE (_aio.py:32, plain path.write_text) of template output that contains no frontmatter. It does not read the existing file, does not route through _sections.py, and does not preserve frontmatter. So any stamped id/sequence_id/status/schema_version would be wiped on the next sq sync.
  - Contrast: roles do it safely — _regen_role_body (_maintenance.py:125-140) reads the existing file and uses sections.replace_section(..., markers.BODY, ...), explicitly leaving frontmatter + discussion intact. The skill body path has no equivalent; it is the only managed-file regen that blows away the whole file.
  - Requirement implementation MUST meet to make the ADR safe (one of): (a) make skill-body regen marker-safe like roles — render into a sq:body region of an Item file and write only that region via _sections.replace_section, so the stamped frontmatter is preserved across sync; OR (b) have sync read-and-preserve existing frontmatter (load Item from disk, re-emit frontmatter + freshly rendered body) — i.e. round-trip through the index rather than re-render from a bare template. Either way id/sequence_id must be allocate-once and sync must never reallocate. Acceptance #4's determinism is about INITIAL allocation order; this is the separate, equally load-bearing guarantee that sync is idempotent on an already-stamped skill.
  - This changes ADR-181's design surface: decision #3 currently says 'stamp frontmatter onto the existing body file' without specifying that the body-regen path must become frontmatter-preserving/marker-safe. The ADR body needs a revision to add that constraint (and note the skill body must adopt the sq:body region structure roles already use) before this moves toward Accepted. Flagging only — not revising the body in this pass.
<!-- sq:discussion:end -->
