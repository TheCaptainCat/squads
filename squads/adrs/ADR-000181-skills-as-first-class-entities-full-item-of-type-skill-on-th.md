---
id: ADR-181
sequence_id: 181
type: decision
title: 'Skills as first-class entities: full Item of type SKILL on the role/operator
  meta-type profile'
status: Accepted
author: architect
refs:
- FEAT-178:addresses
- ADR-541
- ADR-322
- ADR-492
description: A skill is a full Item of the existing ItemType.SKILL with the lightweight
  role/operator profile (Active/Archived, no sub-entities), not a separate lighter
  class; frontmatter stamped onto the existing body file via migration
created_at: '2026-06-23T12:59:27Z'
updated_at: '2026-10-25T21:36:53Z'
---
<!-- sq:body -->
## Context

Skills are first-class ID'd entities (`SKILL-…`, FEAT-178): tracked in `.squads.json`, queryable and
referenceable. The design question this decision answers is:

> Is a skill a **full `Item` type** (same pydantic model, sub-entity machinery, workflow states,
> rendering pipeline) — or a **lighter id'd entity** "the way operators are"?

**The premise needs one correction.** Operators are not a lighter, non-`Item` entity. Roles and
operators are full `Item`s of the `roster` category (ADR-541): each is a real, indexed item with a
status, allocated from the **single global counter**, and reconstructable by `sq repair`. There is no
separate lighter entity class in the model. So the genuine choice is **not** "Item vs.
operator-style"; it is **how heavy a profile of the existing `Item` machinery** a skill adopts —
specifically its **lifecycle** and **sub-entity** surface — given that roles and operators show the
established pattern for roster types.

That leaves three questions: the skill's lifecycle/sub-entity profile, the relationship between the
**indexed skill item** and the **managed skill body file**, and how that file behaves under
`sq sync`, which regenerates managed skill bodies.

## Decision

**1. A skill is a full `Item` of the reserved `skill` type, following the role/operator pattern —
not a new, separate lightweight class.** Reusing the one `Item` model is what preserves every
invariant for free: the global counter via `IndexStore.transaction()`, frontmatter as the source of
truth, `sq repair` reconstruction, ref/backref inversion, and spec-driven prefix/folder resolution.
A parallel lighter entity would fork the model, the index schema, and `repair` for no benefit the
existing `Item` doesn't already give.

**2. Skills take the roster profile, not the work-item profile.** "Full Item" does **not** mean
skills get the task/feature lifecycle. `[items.skill]` is in the `roster` category (ADR-541) and binds
the `agent` lifecycle — `initial = "Active"`, `Active ⇄ Archived` — and declares no
`subentity_kind`, so a skill has **no sub-entities** (no stories/subtasks/findings). Skills are
reference assets, not units of work; giving them `Draft→Ready→InProgress→Done` would be meaningless.
They remain fully **referenceable** (`sq <type> <n> ref add SKILL-…`), which is the feature's primary
user value.

So: full `Item`, roster profile — the same weight as a role.

**3. The skill body file is the item file, and its regeneration preserves frontmatter.** A skill has
one file: sq frontmatter (`id`, `sequence_id`, `type: skill`, `title`, `status`, `author`, …) on the
body file under `agents/skills/`, not a second file beside it. The `.claude/` skill pointer stays a
pointer (invariant 5).

The file follows the **standard filename convention** every type uses —
`agents/skills/SKILL-<NNNNNN>-<slug>.md`, as roles are `agents/roles/ROLE-<NNNNNN>-<slug>.md` and
operators `operators/OP-<NNNNNN>-<slug>.md` — never a bare `<slug>.md`. The `.claude/` pointer
directory stays **keyed by slug** (`.claude/skills/<slug>/SKILL.md`).

Regenerating a managed skill body is **marker-safe**: `sq sync` replaces only the body region and
leaves the frontmatter and every other region intact — the same way a role body is regenerated
(invariant 3). A full-file overwrite of template output would wipe the `id`/`sequence_id`/`status`
on the next sync and destroy the stable identity skills exist to provide. What `sq sync` regenerates
is the managed skills — the bundled ones and the generated `sq-<type>` skills; an authored skill's
body (ADR-492) is outside the regen path and nothing rewrites it, so the marker-safe write protects
the managed bodies specifically.

**4. Identity is allocated once; `sq sync` is idempotent on a stamped skill.** A skill's
`id`/`sequence_id` are allocated **exactly once** — at migration of an existing squad, or when the
skill is first seeded — and **never reallocated**. Re-running `sq sync` never changes an existing
skill's id; it refreshes pointers and the body region only. This is a distinct guarantee from the
initial-allocation ordering in decision #5: #5 governs *what number a skill first gets*; this clause
governs that *sync never churns it afterwards*.

**5. Migration and fresh-init parity: deterministic *ordering*, not identical numbers.** "An
upgraded squad is indistinguishable from a fresh `sq init`" can only mean **ordering parity**: the
single global counter makes identical `SKILL-…` numbers impossible on an already-populated squad,
whose existing items have already consumed counter values. What matches is the **relative allocation
order** — both paths allocate `SKILL-…` ids **lexically by skill slug**, so the same skill sorts to
the same position in both squads even when its absolute number differs.

The migration that introduced skill ids walks `agents/skills/` in that order, allocates ids through
`IndexStore.transaction()`, stamps frontmatter, **renames** each legacy `agents/skills/<slug>.md` to
the convention name, rewrites the slug-keyed `.claude/` pointer, then runs `repair` and stamps the
schema version. The rename is idempotent: a file that already carries the convention name is left
alone. `sq init` seeds skills with the convention name and the same ordering from the start.

## Consequences

- **Minimal model surface.** `skill` is a declared roster type; there is no skill-specific pydantic
  model, index-schema fork or storage path. Skills are located and serialized like any other item.
- **The sync regen path is the sensitive one.** The managed skill-body write is a marker-safe
  body-region replacement, and a test that runs `sq sync` twice and asserts a skill's
  `id`/`sequence_id` are unchanged guards it.
- **Invariants preserved by construction** — global counter, frontmatter truth, repair, refs all come
  from the shared `Item` path; invariant 3 (marker-safe edits) explicitly covers skill bodies.
- **Skills are not work items.** No stories/subtasks/findings, no work lifecycle, not in the `work`
  category and not retype-eligible — a deliberate scope line that can be revisited without reversing
  this decision (adding sub-entities to a roster type is additive).
- **One file per skill, not two**, at the standard filename; pointers stay slug-keyed and stay
  pointers.
- **Determinism is ordering parity, not identical ids** (decision #5).
- **Idempotent sync** (decision #4) — re-running `sq sync` never reallocates or changes an existing
  skill's id.

## Alternatives considered

- **A new, separate lightweight non-`Item` skill record.** Rejected: forks the model, index schema,
  and `repair`; duplicates what `Item` + the roster pattern already provides. The "operator-style"
  framing assumed operators were non-`Item`; they are not.
- **Full work-item profile (workflow + sub-entities).** Rejected: skills are reference assets, not
  units of work; `Draft→…→Done` and stories are meaningless for them.
- **Two files (keep the managed body, add a separate index stub).** Rejected: violates
  one-source-of-truth ergonomics and complicates `repair`.
- **Keep the full-file overwrite and re-stamp frontmatter on every sync.** Rejected: it would force
  sync to read the existing file, re-derive the id, and re-emit it on every run anyway — the
  frontmatter-preserving path of decision #3, but more fragile (any miss silently re-churns the id).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T15:02:29Z] `manager` Catherine Manager:
  - @architect — before this moves toward Accepted, one open interaction to settle: skill body files are regenerated by `sq sync` (headers say "regenerated by sq sync; do not edit by hand"). If a skill is a full Item with sq frontmatter stamped onto that same body file, does `sq sync` regeneration preserve the stamped frontmatter (id, sequence_id, schema_version), or does it churn/overwrite it? ID stability across sync runs is load-bearing for the referenceability the feature exists for (US1) and for the determinism in acceptance #4. Please check the sync regeneration path and record the answer here.
- [2026-06-24T15:03:44Z] `architect` Robert Architect:
  - Investigated the sync regeneration path for managed skill bodies. Finding: as decision #3 is written today, sync WOULD churn/overwrite stamped frontmatter — ID is NOT stable. Skill body files (e.g. squads/agents/skills/squads.md) currently carry no frontmatter; they're pure rendered prose. During sync, the SKILL-item loop (_services/_maintenance.py:90-92) calls only backend.generate_skill_entry, which writes the .claude/ POINTER (_backends/_claude_code/_backend.py:207), not the body. The body files are (re)written separately by write_managed -> _write_managed_skill (_backend.py:107-128) via _aio.write_text(body_path, body) — a FULL-FILE OVERWRITE (_aio.py:32, plain path.write_text) of template output that contains no frontmatter. It does not read the existing file, does not route through _sections.py, and does not preserve frontmatter. So any stamped id/sequence_id/status/schema_version would be wiped on the next sq sync.
  - Contrast: roles do it safely — _regen_role_body (_maintenance.py:125-140) reads the existing file and uses sections.replace_section(..., markers.BODY, ...), explicitly leaving frontmatter + discussion intact. The skill body path has no equivalent; it is the only managed-file regen that blows away the whole file.
  - Requirement implementation MUST meet to make the ADR safe (one of): (a) make skill-body regen marker-safe like roles — render into a sq:body region of an Item file and write only that region via _sections.replace_section, so the stamped frontmatter is preserved across sync; OR (b) have sync read-and-preserve existing frontmatter (load Item from disk, re-emit frontmatter + freshly rendered body) — i.e. round-trip through the index rather than re-render from a bare template. Either way id/sequence_id must be allocate-once and sync must never reallocate. Acceptance #4's determinism is about INITIAL allocation order; this is the separate, equally load-bearing guarantee that sync is idempotent on an already-stamped skill.
  - This changes ADR-181's design surface: decision #3 currently says 'stamp frontmatter onto the existing body file' without specifying that the body-regen path must become frontmatter-preserving/marker-safe. The ADR body needs a revision to add that constraint (and note the skill body must adopt the sq:body region structure roles already use) before this moves toward Accepted. Flagging only — not revising the body in this pass.
- [2026-08-03T08:44:24Z] `architect` Robert Architect:
  - Amended in place; nothing retired. The profile shipped exactly as decided — `[items.skill]` binds the roster lifecycle (`initial = "Active"`, `Active` to `Archived`, no `subentity_kind`), the mandated filename convention is on disk for every skill, and section 3s required property is implemented: `_write_managed_skill` replaces the body region only and preserves frontmatter.
  - Two renames recorded: `WORK_TYPES` and both enums are gone (ADR-322), and the roster/work distinction is `category` (ADR-541), so every "excluded from `WORK_TYPES`" sentence now means "not in the `work` category".
  - One narrowing worth a readers attention rather than a rename: ADR-492 narrowed sections 3 and 4 in fact. `sq sync` iterates the bundled trio plus the generated `sq-<type>` skills, so an author-defined skill body sits structurally outside the regen path. This decision reads as though every skill body is sync-regenerated and therefore needs the marker-safe write to survive it; for an authored skill nothing regenerates it at all. The marker-safe write is still required for the managed bodies — but the property it protects no longer applies uniformly across skills.
- [2026-10-25T21:36:53Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Removed the pre-implementation analysis, the Status/Amended sections, and the FEAT-176/177 ItemStore section: ADR-179 was rejected and ADR-180 is Proposed, so no locator or codec seam exists. Folded in the roster category, the `agent` lifecycle, and the ADR-492 narrowing that only managed skills are regenerated.
<!-- sq:discussion:end -->
