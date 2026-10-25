---
id: ADR-320
sequence_id: 320
type: decision
title: Introduce the contract (PRD) item type — the living functional contract
status: Accepted
author: architect
refs:
- ADR-541
- ADR-322
- ADR-263
- ADR-323
- ADR-775
- ADR-604
description: 'Add a first-class contract/PRD type: the living functional twin of the
  ADR set'
created_at: '2026-07-07T08:32:44Z'
updated_at: '2026-10-25T21:57:03Z'
---
<!-- sq:body -->
## Context

squads has a living, authoritative source of truth for the **technical** point of view: the ADR
set (the `decision` type, `ADR` prefix). ADRs impose the rules; features are history.

There is no equivalent for the **functional / user** point of view. Features and epics are
point-in-time records that accumulate and are never rewritten, so "what does this product do for
a user, right now?" is answered only by replaying their history.

This decision sets the architecture of the artifact that fills that gap, the twin of the ADR set:

> **`decision` (ADR) = the technical contract · `contract` (PRD) = the functional contract with the user.**

## Product drivers

Settled by the product owner and the operator; the mechanics below derive from them.

1. **A first-class item type, not a docs convention**, for stable ids, refs, status and the
   managed skill and playbook surface.
2. **Naming:** type word `contract`, id prefix `PRD`, the same split `decision` uses with `ADR`.
3. **Living versus historic.** A contract is the living current functional state, rewritten in
   place, from the user's point of view. Features and epics stay historic: a feature is the diff
   plus its rationale, a contract is the accumulated current truth.
4. **Maintenance discipline is load-bearing.** A living source of truth that is not kept current
   lies.
5. **A collection, not a monolith**, partitioned by capability or user-facing area.

## Mechanics

### A. The type is a bundled spec declaration

The type engine is config-driven (ADR-322): `src/squads/_specs/workflow.toml` declares every
type, and the CLI group, folder and default template follow from the declaration. `contract` is
declared in the **bundled** spec because the functional contract is a capability that ships to
every squad, not a bespoke local type:

- `[items.contract]`: prefix `PRD`, folder `contracts`, `category = "records"`,
  `lifecycle = "contract"`, `aliases = ["prd", "c"]`, no parent, no `subentity_kind`, and a
  `fields` binding carrying priority only (as `decision` and `guide` do).
- `[lifecycles.contract]`.

ADR-541 owns the category taxonomy: a record is durable, has no parent, and relates to work
through refs, never hierarchy.

### B. Lifecycle

`contract` runs **Draft → Active → Superseded (+ Deprecated)**, with existing status names.
`Active` is the steady state, the live functional truth for that capability. `Superseded` is
terminal and carries the `superseded` status role: a contract for a replaced capability is
superseded by the one that replaces it. `Deprecated` is terminal for a capability sunset with no
replacement, with a revive edge back to `Active`. The work lifecycle does not fit a document
rewritten in place, and the guide lifecycle's `Published` carries no supersede semantics.

### C. The living↔historic edge, and its currency check

A feature links the contract slice it changes with a forward **`implements`** ref (forward edges
only); `sq contract <n> refs --in` lists every feature that shaped a contract with nothing stored
on the contract. The kind is reused, disambiguated by the target's type, rather than adding an
`updates` kind: it reads correctly and keeps the bundled kind set small. Under ADR-775 ref kinds
are declared spec vocabulary, so this is a choice of legibility, not of vocabulary cost.

The `feature` type declares that edge's target on its ref rule:

```toml
ref_rules = [{ kind = "implements", target = "contract" }]
```

`RefRule.target` names a declared item type. It **types** the rule (an edge of this kind from
this type is expected to point at that type); it is not an allowlist and not an obligation, and it
carries no `hint`, which would otherwise leak into the invalid-parent message. Spec load checks
that `target` names a declared type.

**The currency check is an opt-in, advisory validator.** `ref_rule_target_present:<T>` in the
closed validator catalog (ADR-541 axis B, ADR-864) reports a feature whose status resolves to the
`done` status role and that carries no outgoing edge, of a kind whose rule targets `<T>`, to an
item of type `<T>`. Its declared default level is `warn`, so it never gates create or update. The
bundled `feature` type does not select it: whether a delivered feature must name a contract slice
is the maintainer's call, because many features (internal refactors, test batteries, tooling)
change no adopter promise and a rule that cannot record that produces permanent warnings. A squad
that wants the obligation adds `validators = ["ref_rule_target_present:contract"]` to
`[items.feature]` in its `.overrides/workflow.toml`; spec load refuses that selection if no rule
of the type targets `contract`.

Its semantics, when selected:

- **The trigger is the `done` status role**, never a status spelling and never `InReview` (which
  names the `active` role every in-flight status shares) or the broader `settled` property (which
  would warn on a Cancelled feature that delivered nothing). No dedicated "under review" role is
  introduced for it: it would be identical to `active` under every derived predicate. A squad
  whose delivered status declares a custom settled role instead of `done` does not get the check.
- **The edge is found through the merged spec**, never by comparing against the literal
  `"implements"`; a `tests/meta` scan keeps bundled ref-kind names out of `src/squads/` outside
  `_specs/` and `_migrations/`. A squad renaming the kind or the type keeps the check.
- **It is inert while the corpus holds no item of the target type.** Its remedy is an edge into a
  collection that does not exist yet, so before the first contract is authored the finding is
  noise. From the first contract on, every settled feature is evaluated, earlier ones included.
  The aggregate is computed once per run; on the single-item create/update path, which has no
  index, the check yields nothing. There is no suppression, grandfather date or per-item
  exemption.

`contract` also declares a `supersedes` ref rule, as `decision` does. The `records` category
selects `supersedes_incoming`, so a `Superseded` contract with no incoming supersedes edge is
reported.

### D. Collection structure

**One `contract` item per capability or user-facing area**, edited in place, with ordinary
markdown headings inside. Merge granularity is per file and a feature's edges point at exactly
the contracts it touched. Sections as sub-entities are rejected: sub-entity prose lives in the
parent's body, recreating the monolith, and sub-entities are lifecycle-bearing mini-items, which
a section is not. Partitioning is the product owner's judgement and carries no structural guard.

### E. The generated agent-facing surface

All of it is regenerated by `sq sync` and stamped as such:

- `[types.contract]` entries in `playbook.toml` drive the managed `sq-contract` skill: the product
  owner authors contracts and keeps them current, the tech lead and developers update the touched
  slice as features land, the architect watches cross-contract consistency. Generated text renders
  from the active spec, playbook and roster, so a squad that renames or drops the type gets text
  in its own vocabulary.
- The `.claude` skill pointer carries its `name`, its `description` and the command
  `sq skill sq-contract show`, and no local path (ADR-781).
- `sq contract` is generated from the declaration, with no per-type module.
- `templates/items/contract.md.j2` steers the author toward functional-behaviour prose.

A contract's body is authored prose with no materialised region: no sub-entity summary, no head
(ADR-776). `sq check` reports the per-entry pointers' presence and currency for the live roster
(ADR-781).

### F. Schema

`contract` entered the bundled spec with schema `0.14`, sharing that release's single bump and
migration runner with the milestone type. The runner creates the `contracts/` folder and
regenerates the managed surface; its manual step tells an adopting squad the type exists and that
seeding contracts for its current capabilities is its own product work. The schema-number
convention is `_models/_schema.py`'s: a schema number names the release that introduces it.

## Decision

`contract` (prefix `PRD`) is a bundled item type of the config-driven engine:

- declared by `[items.contract]` (prefix `PRD`, folder `contracts`, `category = "records"`) and
  `[lifecycles.contract]` in `src/squads/_specs/workflow.toml`;
- on the lifecycle **Draft → Active → Superseded (+ Deprecated)**;
- one item per capability area, no sub-entities, partitioning left to the product owner;
- linked from the features that shape it by a forward `implements` ref, typed by
  `target = "contract"` on the feature's ref rule, and declaring a `supersedes` rule itself;
- with currency checked by the advisory `ref_rule_target_present:contract` validator, which a
  squad selects on its `feature` type; never a hard gate;
- with the managed `sq-contract` skill, its pointer, the playbook entries and the item template
  generated and stamped as `sq sync`-regenerated.

A contract's body describes product behaviour only; dated discussion comments hold notes about a
point in time.

## Consequences and trade-offs

**Positive.** The type is additive: rows in the tables existing types use, no new mechanism. The
functional truth is queryable in one place, and the feature→contract edge inverts into a free
"which features shaped this contract" view.

**Costs accepted.**

1. **Currency rests on an opt-in advisory warning.** A squad that does not select the check gets
   no reminder, and a selected warning can be ignored. Taken deliberately: a default-on rule
   buys currency with permanent false positives on technical features and with fake refs added to
   clear them. The levers are the selection and its level, not the design.
2. **`implements` names two relationships** (task→feature, feature→contract), disambiguated by the
   target's type.
3. **Partitioning discipline is unchecked**; coarse contracts drift toward monoliths, fine ones fan
   a feature's edges across many tiny items.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:38:06Z] `architect` Robert Architect:
  - Applied ADR-541s standing instruction — reworded to the `records` category — and re-derived section As mechanism, which had stopped describing anything. This stays forward design; the operator has moved FEAT-321 out of this release, so nothing here is blocking work.
  - The substantive finding is that the option analysis inverted, not that citations went stale. A2 was chosen because prefix/folder/id resolution had a reserved fast-path so it needed no custom-type plumbing, and A1 was rejected partly because that plumbing was incomplete. Both premises are false now: there is no reserved fast-path (ADR-266/322) and the plumbing shipped (ADR-263 plus a default item template). So A1 and A2 are no longer two mechanisms — both mean declaring `[items.contract]` in a spec, differing only in which spec.
  - Re-derived on the driver that survives untouched: this type ships to every squad out of the box, so it goes in the bundled spec. The mechanism is now one `[items.contract]` block plus one `[lifecycles.contract]` block in `src/squads/_specs/workflow.toml` and nothing else — a stronger version of the original conclusion, reached without the reserved-vocabulary argument it used to lean on.
  - Smaller corrections: `is_meta = false`/`severity_field = false` to `category = "records"` with no severity field binding (ADR-541 on the taxonomy, ADR-323 on the field); section Cs closed frozenset is `VALID_REF_KINDS` in `_models/_item.py` at nine kinds, which leaves the reuse-`implements` recommendation intact; the `0.7 → 0.8` bump is history. Everything genuinely settled is untouched — the living-versus-historic model and its five drivers, B2s lifecycle, D2s one-item-per-capability, the forward `implements` edge, advisory over hard gate, and section Es verify-on-both-`init`-and-`migrate` rule.
  - Added `related` edges to ADR-541, ADR-322, ADR-263 and ADR-323 — this decision had none, so nothing pointed at the four decisions that moved the ground under it.
- [2026-08-24T18:02:24Z] `op-pierre` Pierre Chat:
  - Enforcement stays advisory as written: warn-level, never a hard gate. A gate manufactures false positives and fake refs on purely technical features.
  - Ref kind: reuse implements, disambiguated by the target type. ADR-775 removes the vocabulary-growth cost, but reuse still reads correctly and keeps the bundled set smaller.
  - Partitioning: no structural guard. One contract per capability area stays the product owner judgement, revisited only if it goes wrong in practice.
  - Schema: 0.14 carries ONE bump for both new item types (PRD and MILE) in a single migration, so FEAT-321 and FEAT-693 land in the same release.
- [2026-08-24T18:16:43Z] `architect` Robert Architect:
  - Rewrote the body to read as the current decision rather than a log of its own revisions: the three layers of inline "Rewritten/Reworded 2026-08-03" italics and the Amendment note are gone. The one piece of history worth keeping — the inverted A1/A2 option analysis — survives as a short paragraph inside section A, because a reader needs to know the reserved-fast-path argument is dead, not that a citation moved.
  - Folded in the four rulings. C: enforcement is advisory as the decision own position, warn-level, gate refused on false-positives-and-fake-refs. C: implements reused, reasons restated as legibility plus a smaller bundled set — the "expands a deliberately-closed vocabulary" argument is deleted, and the section now says plainly that ADR-775 removed that cost so the choice does not rest on it. D: partitioning carries no structural guard, stated as a ruling, revisited only if it goes wrong in practice. F: one schema bump (0.11 to 0.12) and one migration runner shared with the milestone type in 0.14, FEAT-321 and FEAT-693 together; the runner is the release, not this decision.
  - Stale points corrected beyond the ones flagged. The advisory rule no longer cites _check_decisions as its template — ADR-541 axis B shipped, so it is a named per-item validator in the closed CATALOG selected by the feature type validators list, and the records bundle already carries supersedes_incoming so the supersedes rule needs no new code. The claim that a contract show surfaces its incoming edges is wrong: backrefs print under refs --in/--all, never show. default_workflow.toml corrected to src/squads/_specs/workflow.toml. Section E reconciled with ADR-781 — the pointer names sq skill sq-contract show and carries no @ path — and with ADR-776: the type declares no subentity_kind, so it has no summary or head region to materialise, and the verify-on-both-init-and-migrate obligation now says ADR-781 2c makes it mechanical once presence lands.
  - One real tension, not smoothed over. ADR-775 2 keeps a tests/meta scan asserting no bundled ref-kind name appears as a literal in src/squads outside _specs and _migrations, and implements declares no semantic role — so the advisory check cannot find its edge by comparing against "implements". The body now constrains the implementation: the kind and the target type are read from the merged spec as a parameterised catalog entry on the feature type (the subentity_title_max shape). Second, smaller: ADR-776 6 also owes a migration for the retired body regions. The ruling names PRD and MILE; F is written so any other schema-level change in 0.14 joins the same runner rather than adding a second bump, which keeps both true.
- [2026-08-24T20:16:00Z] `manager` Catherine Manager:
  - Accepted on the operator four rulings (advisory enforcement, implements reuse, no partitioning guard, one shared schema bump with the MILE type). Read the revised body before accepting: schema 0.11 to 0.12 verified against _models/_schema.py, no status prose, and the retired closed-vocabulary argument is deleted rather than softened.
- [2026-08-25T18:20:44Z] `architect` Robert Architect:
  - Section F amended in place: the bump is 0.11 to 0.14, not 0.11 to 0.12, plus a new amendment note carrying the argument. Confirmed from the tags rather than from the convention text - v0.12.0 and v0.13.1 both ship SCHEMA_VERSION = 0.11, so a schema numbered 0.12 would name a release that shipped and introduced nothing, which is the one reading the alpha convention forbids. Gaps are already the convention: the series skips 0.6 and 0.9 for the same reason.
  - The convention is narrowed in the same change rather than left to be re-derived. It binds FORWARD - a new schema number takes the release that introduces it, and a release may introduce more than one - and schema 0.4 is recorded as the one exception in the series, since v0.4.0 ships SCHEMA_VERSION 0.3 and both the 0.3-to-0.4 and 0.4-to-0.5 runners shipped inside release 0.5.0. Nobody should read a release number backwards out of an intermediate label.
  - A2 names what the number touches so a dev is not left to find it: the runner module _v0_11_to_v0_14.py, its registry entry, and the corpus fixture tests/fixtures/corpus/v0_14 that the standing rule in test_migration_corpus.py requires of every bump. Nothing else moves - schema_tuple ordering is unaffected and the existing registry guard already ties the highest to_schema to SCHEMA_VERSION. Ruled on TASK-813. @tech-lead
- [2026-10-25T21:57:01Z] `op-pierre` Pierre Chat:
  - Record the contract currency check as opt-in: a squad selects ref_rule_target_present:contract in its own override.
- [2026-10-25T21:57:03Z] `manager` Catherine Manager:
  - Audited 2026-10-25: rewritten in the present tense; the currency check is opt-in, the dated amendment sections are folded in, and the stale pointer-presence section is gone.
<!-- sq:discussion:end -->
