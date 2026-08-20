---
id: ADR-320
sequence_id: 320
type: decision
title: Introduce the contract (PRD) item type — the living functional contract
status: Proposed
author: architect
refs:
- ADR-541
- ADR-322
- ADR-263
- ADR-323
description: 'Add a first-class contract/PRD type: the living functional twin of the
  ADR set'
created_at: '2026-07-07T08:32:44Z'
updated_at: '2026-08-03T08:38:06Z'
---
<!-- sq:body -->
## Context

squads has a living, authoritative source of truth for the **technical** point of view:
the ADR set (the `decision` item type, `ADR` prefix). ADRs impose the rules; features are
history. To learn a current technical constraint you read the ADR, not the feature that
introduced it.

There is no equivalent for the **functional / user** point of view. To answer "what does
this product actually do for a user, right now?" you must replay the whole feature/epic
history and mentally apply every later override. Features and epics are point-in-time
records — they accumulate, they never get rewritten to reflect the current truth — so the
current functional state is never written down in one place.

This ADR settles the **architecture** for a new artifact that fills that gap: a living
functional contract that is the twin of the ADR set. The linguistic symmetry is deliberate:

> **`decision` (ADR) = the technical contract · `contract` (PRD) = the functional contract with the user.**

## Decision drivers (product-level, already settled — recorded, not reopened)

These were decided by the product owner and the operator in a design session and are inputs
to this ADR, not open questions:

1. **First-class item type, not a docs convention.** A `squads/product/*.md` file convention
   was considered and rejected in favour of the item-type path (stable IDs, refs, status,
   the managed-skill/playbook surface).
2. **Naming is fixed:** type word `contract`, ID prefix `PRD` (the same split the `decision`
   type uses with its `ADR` prefix). "The search contract," `PRD-000042`.
3. **Living vs historic is the core model.** The `contract` is the *living* current functional
   state, rewritten in place as the product evolves, from the user's POV. Features/epics stay
   *historic* — point-in-time records that later work can supersede. Feature = the diff +
   rationale (the audit trail); contract = the accumulated current truth (the winner).
4. **Maintenance discipline is load-bearing.** Landing a feature is not done until it has
   updated the `contract` slice it touches. A living source of truth that is not kept current
   *lies* — that is the whole risk this design has to manage.
5. **A collection, not a monolith.** Contracts are partitioned by capability / user-facing
   area so a feature updates just its slice and ownership/merge stays sane.

## Options weighed and the recommended mechanics

### A. How the type is introduced

The type engine is already config-driven: `WorkflowSpec` (`default_workflow.toml`) declares
every type's prefix, folder, lifecycle, parents, aliases and capability flags, and the CLI
builds each type's `sq <type>` command group generically from that spec. Two paths exist:

- **A1 — override-only** (`.overrides/workflow.toml` in one squad). Rejected: the PRD is a
  product capability that must ship to *every* squad out of the box, not a bespoke local type.
  It also runs into the incomplete custom-type plumbing (`create()` has no template path for a
  custom type yet, and `SquadsDB.format_id` derives the prefix from the reserved map, not the
  spec), which A1 would have to finish first. *That blocker is closed: ADR-263 registers a
  spec-declared type's CLI group ahead of Click's parse-time resolution, and there is a default
  item template. The surviving reason to reject A1 is the first one — this type ships to every
  squad, so it belongs in the bundled spec, not a per-squad override.*
- **A2 — declared in the bundled spec (recommended).** Add one `[items.contract]` block (prefix
  `PRD`, folder `contracts`, `category`, `lifecycle`, `aliases`) and one `[lifecycles.contract]`
  block to the bundled `src/squads/_specs/workflow.toml`, exactly as every other declared type is
  carried. The CLI group `sq contract` and the folder come from that declaration. It is the minimal
  correct path *for a shipped type*: extend the declarative spec rather than invent a mechanism.

  *Rewritten 2026-08-03. As first written this option added `contract` to the `ItemType` enum and
  the `RESERVED_PREFIX`/`RESERVED_FOLDER` maps, and argued for itself on a reserved fast-path that
  needed no custom-type plumbing. Enum, both maps and the fast-path are all gone (ADR-322), so A1
  and A2 are no longer two mechanisms — both mean "declare `[items.contract]` in a spec", differing
  only in which spec. See the amendment note.*

Treat `contract` as a `category = "records"` type with no `subentity_kind` and no severity field
binding. Aliases: `prd`, and `c` (currently free).
*Reworded 2026-08-03 from "a non-meta work-item type (`is_meta = false`, … `severity_field =
false`)", which predated the work/records split. ADR-541 ruled on this decision by name and is the
authority on the taxonomy; ADR-323 replaced `severity_field` with the generic `fields` binding.* It has no required
parent; it is not parented under features (the historic→living edge runs the other way, as a
ref — see C).

### B. Lifecycle states for a living artifact

A contract is not a build-lifecycle artifact, so the work lifecycle (Draft→Ready→InProgress→
InReview→Done) is wrong — most of it is meaningless for a document that is continuously
rewritten in place. Two candidates:

- **B1 — reuse the guide lifecycle** (Draft → Published → Deprecated). Free, and a guide is
  also a living doc. But "Published" frames it as a doc release, and it does not carry the
  supersede semantics the historic-vs-living model wants.
- **B2 — a dedicated `contract` lifecycle (recommended):** `Draft → Active → Superseded`
  (+ `Deprecated`). All four statuses already exist in the shared status set, so no new
  `Status` members are needed. `Active` is the steady state — the live functional truth for
  that capability. `Superseded` is terminal and already carries `role = "superseded"`, which the
  existing supersede consistency check keys on; a `contract` for a replaced capability is
  superseded by the contract that replaces it. `Deprecated` is terminal for a capability that is
  sunset without a direct replacement (with a revive edge back to `Active`). This mirrors the
  ADR twin (`Accepted`/`Superseded`/`Deprecated`) and reads correctly for a living artifact.

The reachable-terminal invariant is satisfied (`Superseded` and `Deprecated` are terminal).

### C. The living↔historic edge and DoD enforcement

The historic→living relationship is a **forward ref from the feature to the contract it
updates** (forward edges only; the contract's incoming edges are computed by backref
inversion — so a contract's `sq … show` surfaces every feature that shaped it, for free).

- **Ref kind.** The ref-kind vocabulary is a closed frozenset (`VALID_REF_KINDS` in
  `_models/_item.py`, nine kinds — ADR-49 as narrowed by ADR-492) that already includes
  `implements`. Recommend **reusing `implements`**: a feature *implements* the slice of the
  functional contract it delivers. This needs no vocabulary expansion, and the advisory check
  below can disambiguate it from a task→feature `implements` edge by inspecting the **target's
  type** (`contract`). A dedicated new kind (`updates`) was considered — it would give the
  check a more literal anchor — but it expands a deliberately-closed vocabulary for no behaviour
  the target-type test doesn't already give us. Separately, `contract` should declare a
  `supersedes` ref rule (like `decision`) so a replacement contract links the one it supersedes.
- **Enforcement — advisory `sq check` rule (recommended), not a hard gate.** Three options:
  convention only (too weak — staleness is the whole risk); a hard gate blocking a feature from
  `Done` without a contract edge (too rigid — purely-technical/internal features have no
  user-facing contract change, so a gate manufactures false positives and fake refs); or an
  **advisory warn-level rule** in the spirit of the existing unwritten-body / status-banner /
  supersede checks — warn when a feature reaches `InReview`/`Done` with no `implements` ref to a
  `contract`. Non-blocking, it surfaces the debt and lets the human/agent judge whether this
  feature legitimately touches no contract. The supersede check (`_check_decisions`) is the
  structural template — it already keys off `spec.item_ref_rules(...)` and `status_role(...)`.

### D. Collection structure

- **D1 — section sub-entities within one contract.** Rejected. Sub-entity *prose* lives in the
  parent item's body and sub-entity *state* in the parent's frontmatter, so every section would
  share one file — reintroducing exactly the monolith/merge-contention that driver 5 rules out.
  Sub-entities are also lifecycle-bearing mini-items (Todo/InProgress/Done), which does not
  match "a section of a living document."
- **D2 — one `contract` item per capability / user-facing area (recommended).** The collection
  *is* the set of `PRD-*` items; each is one capability's living contract, edited in place, with
  ordinary markdown headings for internal structure. Merge granularity is per file, ownership is
  per area, and a feature's `implements` edges point at exactly the contract(s) it touched. This
  is why `contract` needs **no** `subentity_kind` — it is structurally like `guide`, not
  `feature`.

### E. Generated `.claude` / AGENTS.md surface

A new item type grows the managed agent-facing surface, all of which is regenerated by
`sq sync` and must say so in place:

- a managed `sq-contract` skill (real body under `squads/agents/skills/`, thin pointer in
  `.claude/`), driven by new `[types.contract]` entries in the interactions playbook
  (`playbook.toml`) — per-role enter/do/handoff/watch guidance (product-owner owns/authors and
  keeps it current; tech-lead and `*dev` update the touched slice as features land; architect
  watches cross-contract consistency);
- the per-type CLI group `sq contract` (auto-generated, no per-type module);
- an item template `templates/items/contract.md.j2` guiding the author toward functional
  behaviour prose (a `_default.md.j2` fallback exists, but a dedicated template sets the
  right shape and keeps status/lifecycle prose out of the body).

**On-disk `.claude`/AGENTS.md artifacts must be verified against roles/ops for BOTH fresh
`init` AND `migrate`** — pointer filenames, targets, and descriptions are not validated by
`sq check`, and a type-addition that only wired the `init` path (missing the `migrate`
regeneration) has bitten this project before.

### F. Schema and migration

Adding a type to the bundled spec bumps the schema — the root callback hard-stops a squad on a
schema mismatch until `sq migrate up` runs. *The `0.7 → 0.8` originally written here is history;
the bump is against whatever the current version is when this lands.* No existing item data is rewritten, so the deterministic `run` step is
light (create the `contracts/` folder, regenerate the managed skills/pointers/CLAUDE.md and
AGENTS.md regions so the `sq-contract` surface appears). The `manual` runbook entry should
tell an adopting squad that the new functional-contract type now exists and (optionally) to
seed initial `contract` items for their current capabilities — the migration cannot author
functional truth on their behalf.

## Decision

Introduce `contract` (prefix `PRD`) as a **built-in reserved work-item type** carried by the
existing config-driven type engine:

- declared as one `[items.contract]` block (prefix `PRD`, folder `contracts`, `category =
  "records"`) plus a `[lifecycles.contract]` block in the bundled `src/squads/_specs/workflow.toml`;
  CLI group and folder come from that declaration;
- on a dedicated `contract` lifecycle **Draft → Active → Superseded (+ Deprecated)**, reusing
  existing statuses (`Active` is the live steady state; `Superseded` carries the supersede role);
- structured as **one item per capability area** (a collection of `PRD-*` items, no
  sub-entities), with internal markdown headings;
- linked from the features that shape it by a forward **`implements`** ref (reused kind;
  disambiguated by the target being a `contract`), with `contract` also declaring a
  `supersedes` rule for replacement;
- with DoD maintenance enforced by an **advisory `sq check` rule** (warn a feature reaching
  `InReview`/`Done` with no `implements` edge to a `contract`), never a hard gate;
- with the managed `sq-contract` skill, pointer, playbook entries and item template generated
  and stamped as `sq sync`-regenerated, verified on disk for both `init` and `migrate`;
- shipped behind a schema bump whose migration creates the folder and regenerates
  the agent-facing surface, with a manual runbook note.

The `contract` body describes **product behaviour only** — never its own workflow state; the
frontmatter `status:` field is the single source of truth, and dated discussion comments are the
home for state-at-a-point-in-time notes.

## Consequences and trade-offs

**Positive.** Riding the config-driven engine makes this an additive, low-blast-radius change:
new rows in the tables the ten existing types already use, no new mechanism, the CLI group and
folder generated automatically. The functional truth becomes queryable in one place, twinning
the ADR set, and the historic→living edge is a plain forward ref that inverts into a free
"which features shaped this contract" view.

**Negative / risks to weigh on review.**

1. **The maintenance guarantee is only as strong as its enforcement, and the recommendation is
   advisory.** An advisory warning can be ignored, and a living source of truth that drifts is
   worse than none — it lies with authority. This is the sharpest call: advisory (chosen, for
   the false-positive reasons above) vs a hard gate that guarantees currency at the cost of
   friction and fake refs on purely-technical features. If review wants a stronger guarantee, the
   lever is the check's severity, not the design.
2. **Reusing `implements` overloads one ref kind for two relationships** (task→feature *and*
   feature→contract). The disambiguation rests on the target's type. It keeps the closed vocab
   closed, but a reader skimming raw refs sees the same word for two edges; a dedicated `updates`
   kind trades vocabulary growth for legibility. Worth a deliberate yes/no.
3. **Sectioning by "capability area" is a human judgement with no schema enforcement.** Too
   coarse and contracts drift back toward monoliths with merge contention; too fine and features
   fan their `implements` edges across many tiny contracts. The per-item model keeps merges sane
   but pushes the partitioning discipline onto the product owner — there is no structural guard
   that a contract stays single-capability.

## Amendment note

**2026-08-03 — the mechanism is re-derived against the current engine, and section A's option
analysis has inverted.** Nothing here is implemented, which is consistent with where this decision
sits; what needed correcting is that the recommended mechanism no longer describes anything, and the
argument that chose it over the alternative rests on two premises that are now false.

**What changed under it.** ADR-322 removed the `ItemType` enum, the `RESERVED_PREFIX`/`RESERVED_FOLDER`
maps and the reserved fast-path in prefix resolution; the bundled spec moved to
`src/squads/_specs/workflow.toml`; and ADR-541 replaced the `is_meta` boolean with a three-valued
`category`, ADR-323 replaced `severity_field` with a generic per-type `fields` binding. So A2 as
written — "add `contract` to the `ItemType` enum, `RESERVED_PREFIX`, `RESERVED_FOLDER`, and
`default_workflow.toml`" — names four things, three of which do not exist.

**Why the A1-versus-A2 argument inverted.** A2 was chosen because "prefix/folder/id-format/type-for-id
resolution all have a reserved fast-path, so this needs no new custom-type plumbing", and A1 was
rejected partly because custom-type plumbing was incomplete. Both premises are gone: there is no
reserved fast-path (every type resolves through the spec, ADR-266/322), and the plumbing A1 was
waiting on shipped — ADR-263 registers a spec-declared type's CLI group ahead of Click's parse-time
resolution, and `create()` falls back to a default item template for a type with no dedicated one.

**What the choice actually is now.** A1 and A2 are no longer two mechanisms. Both mean "declare
`[items.contract]` in a spec"; they differ only in *which* spec — the bundled one or a project
override. That reduces the decision to the driver this section already stated and which is unaffected:
the functional-contract type is a product capability that must ship to every squad out of the box, so
it is declared in the bundled spec. The mechanism is one `[items.contract]` block (prefix `PRD`, folder
`contracts`, `category`, `lifecycle`, `aliases`) plus one `[lifecycles.contract]` block, and nothing
else. That is a *stronger* version of the original conclusion, reached without the reserved-vocabulary
argument it used to lean on.

**The category label.** ADR-541 ruled on this decision by name: `contract` is `category = "records"`,
not the "non-meta work-item type" written here before the work/records split existed. ADR-541 is the
authority on the taxonomy and carries the `related` edge; the rest of the mechanics it names — prefix
`PRD`, the `Draft → Active → Superseded (+ Deprecated)` lifecycle, no `subentity_kind`, a `supersedes`
ref rule — it leaves standing unchanged. Note that this also moves `contract` off "work", which
section A asserted.

**Two smaller premises.** §C leans on the ref-kind vocabulary being "a closed frozenset" — it is
`VALID_REF_KINDS` in `_models/_item.py`, and it is nine kinds rather than eight (ADR-49 as narrowed by
ADR-492). Reusing `implements` still needs no vocabulary growth, so the recommendation is unaffected;
the count is not what it was. And §F's `0.7 → 0.8` bump is history — a schema bump is still owed
whenever this lands, against whatever the current version is then.

Everything genuinely settled here is untouched: the living-versus-historic model and its five product
drivers, the dedicated lifecycle (B2), one item per capability area rather than section sub-entities
(D2), the forward `implements` edge with backref inversion, advisory enforcement over a hard gate, and
the generated-surface obligations in §E including the verify-on-both-`init`-and-`migrate` rule.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:38:06Z] Robert Architect:
  - Applied ADR-541s standing instruction — reworded to the `records` category — and re-derived section As mechanism, which had stopped describing anything. This stays forward design; the operator has moved FEAT-321 out of this release, so nothing here is blocking work.
  - The substantive finding is that the option analysis inverted, not that citations went stale. A2 was chosen because prefix/folder/id resolution had a reserved fast-path so it needed no custom-type plumbing, and A1 was rejected partly because that plumbing was incomplete. Both premises are false now: there is no reserved fast-path (ADR-266/322) and the plumbing shipped (ADR-263 plus a default item template). So A1 and A2 are no longer two mechanisms — both mean declaring `[items.contract]` in a spec, differing only in which spec.
  - Re-derived on the driver that survives untouched: this type ships to every squad out of the box, so it goes in the bundled spec. The mechanism is now one `[items.contract]` block plus one `[lifecycles.contract]` block in `src/squads/_specs/workflow.toml` and nothing else — a stronger version of the original conclusion, reached without the reserved-vocabulary argument it used to lean on.
  - Smaller corrections: `is_meta = false`/`severity_field = false` to `category = "records"` with no severity field binding (ADR-541 on the taxonomy, ADR-323 on the field); section Cs closed frozenset is `VALID_REF_KINDS` in `_models/_item.py` at nine kinds, which leaves the reuse-`implements` recommendation intact; the `0.7 → 0.8` bump is history. Everything genuinely settled is untouched — the living-versus-historic model and its five drivers, B2s lifecycle, D2s one-item-per-capability, the forward `implements` edge, advisory over hard gate, and section Es verify-on-both-`init`-and-`migrate` rule.
  - Added `related` edges to ADR-541, ADR-322, ADR-263 and ADR-323 — this decision had none, so nothing pointed at the four decisions that moved the ground under it.
<!-- sq:discussion:end -->
