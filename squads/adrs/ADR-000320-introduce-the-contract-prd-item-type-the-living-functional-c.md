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
updated_at: '2026-08-26T13:50:57Z'
---
<!-- sq:body -->
## Context

squads has a living, authoritative source of truth for the **technical** point of view: the ADR
set (the `decision` item type, `ADR` prefix). ADRs impose the rules; features are history. To
learn a current technical constraint you read the ADR, not the feature that introduced it.

There is no equivalent for the **functional / user** point of view. To answer "what does this
product actually do for a user, right now?" you must replay the whole feature/epic history and
mentally apply every later override. Features and epics are point-in-time records — they
accumulate, they never get rewritten to reflect the current truth — so the current functional
state is never written down in one place.

This decision settles the **architecture** for a new artifact that fills that gap: a living
functional contract that is the twin of the ADR set. The linguistic symmetry is deliberate:

> **`decision` (ADR) = the technical contract · `contract` (PRD) = the functional contract with the user.**

## Product drivers — settled inputs, not open questions

Decided by the product owner and the operator in a design session; recorded here because the
mechanics below are derived from them.

1. **A first-class item type, not a docs convention.** A `squads/product/*.md` file convention was
   weighed and rejected in favour of the item-type path: stable IDs, refs, status, and the
   managed-skill/playbook surface.
2. **Naming is fixed:** type word `contract`, ID prefix `PRD` — the same split `decision` uses
   with its `ADR` prefix. "The search contract," `PRD-000042`.
3. **Living versus historic is the core model.** A contract is the *living* current functional
   state, rewritten in place as the product evolves, from the user's point of view.
   Features and epics stay *historic* — point-in-time records later work supersedes. A feature is
   the diff plus its rationale (the audit trail); a contract is the accumulated current truth
   (the winner).
4. **Maintenance discipline is load-bearing.** Landing a feature is not finished until it has
   updated the contract slice it touches. A living source of truth that is not kept current
   *lies* — that is the whole risk this design has to manage.
5. **A collection, not a monolith.** Contracts are partitioned by capability / user-facing area,
   so a feature updates one slice and ownership and merge granularity stay sane.

## Mechanics

### A. How the type is introduced

The type engine is config-driven. `WorkflowSpec` — bundled as package data at
`src/squads/_specs/workflow.toml` — declares every type's prefix, folder, lifecycle, parents,
aliases, category and capability flags, and the CLI builds each type's `sq <type>` command group
from that declaration. Two pieces of plumbing that a new declared type once needed are shipped:
ADR-263 registers a spec-declared type's CLI group ahead of Click's parse-time resolution, and
`create()` falls back to `items/_default.md.j2` for a type with no dedicated template.

So the open question is *which spec* carries the declaration, never which mechanism declares it.

`contract` is declared in the **bundled** spec: one `[items.contract]` block — prefix `PRD`,
folder `contracts`, `category = "records"`, `lifecycle = "contract"`, `aliases = ["prd", "c"]`
(both free today) — plus one `[lifecycles.contract]` block. Nothing else. The CLI group and the
folder follow from the declaration, and `sq init` already creates one folder per declared type.

A per-squad `.overrides/workflow.toml` declaration is rejected on one driver: the functional
contract is a product capability that ships to every squad out of the box, not a bespoke local
type.

**Why that reduces to a driver where it used to be a mechanism choice.** The analysis here
inverted, and the inversion is worth recording rather than quietly dropping. The bundled path was
originally argued on a reserved fast-path: `contract` would join the `ItemType` enum and the
`RESERVED_PREFIX` / `RESERVED_FOLDER` maps and so need no custom-type plumbing, while the override
path was rejected partly *because* that plumbing was incomplete. Both premises are gone. ADR-322
removed the enum, both maps and the reserved fast-path — every type now resolves through the spec
(ADR-266) — and the plumbing the override path was waiting on shipped. The two options stopped
being two mechanisms: both mean "declare `[items.contract]` in a spec", differing only in which
one. The driver above decides that on its own, without the reserved-vocabulary argument the
conclusion used to lean on.

`contract` takes the `records` category. ADR-541 is the authority on the taxonomy and ruled on
this type by name: durable, no parent — a record relates to work through refs, never through
hierarchy — with its own non-burn-down lifecycle. It declares no `subentity_kind` (§D). Its
`fields` binding carries priority only, as `decision` and `guide` do; there is no severity field
(ADR-323 replaced the old per-type severity flag with that generic binding).

### B. Lifecycle

A contract is not a build-lifecycle artifact, so the work lifecycle
(Draft → Ready → InProgress → InReview → Done) is wrong for it — most of those states are
meaningless for a document continuously rewritten in place.

`contract` runs **Draft → Active → Superseded (+ Deprecated)**. All four statuses already exist in
the shared status set, so no new status names are introduced. `Active` is the steady state — the
live functional truth for that capability. `Superseded` is terminal and carries
`role = "superseded"`, which the shipped supersede check keys on: a contract for a replaced
capability is superseded by the contract that replaces it. `Deprecated` is terminal for a
capability sunset with no direct replacement, with a revive edge back to `Active`. Both terminals
are reachable and settled, so ADR-696 §3's lifecycle floor holds. This mirrors the ADR twin
(Accepted / Superseded / Deprecated) and reads correctly for a living artifact.

Reusing the `guide` lifecycle (Draft → Published → Deprecated) was weighed: it is free, and a
guide is also a living document. It is not taken, because "Published" frames the artifact as a
document release and the lifecycle carries no supersede semantics — which is exactly what the
living-versus-historic model needs.

### C. The living↔historic edge, and how maintenance is enforced

The historic→living relationship is a **forward ref from the feature to the contract it updates**
(forward edges only). A contract's incoming edges are computed by inversion, so
`sq contract <n> refs --in` lists every feature that shaped it with nothing stored on the contract
itself.

**The ref kind is `implements`, disambiguated by the target's type.** A feature *implements* the
slice of the functional contract it delivers, which reads correctly at the call site and in a raw
edge; and reuse keeps the bundled kind set smaller. A dedicated `updates` kind would give a check
a more literal anchor, and is not taken.

The ground under that choice has moved, and the choice does not rest on it. Under ADR-775 ref
kinds are a declared `[ref_kinds]` section of the workflow spec, merged and validated like every
other vocabulary axis, rather than a closed frozenset in code — so a new kind no longer costs a
vocabulary expansion. Reuse is chosen on legibility and on keeping the bundled set small, not on
a vocabulary cost that no longer exists. `implements` declares no semantic role, so it stays
navigational; the only consumer is the check below, which resolves the edge by the target's type.

Separately, `contract` declares a `supersedes` ref rule, as `decision` does, so a replacement
contract links the one it supersedes. That declaration is the whole wiring: the `records` category
bundle already selects `supersedes_incoming`, so a `Superseded` contract with no incoming
supersedes edge is reported with no new code.

**Enforcement is advisory, and stays advisory.** A **warn**-level `sq check` finding when a
feature reaches `InReview` or `Done` with no `implements` edge to a `contract`. Never a hard gate.
A gate is refused for a specific reason rather than a general dislike of friction: purely
technical and internal features have no user-facing contract change, so a gate manufactures false
positives, and the way a team clears a false positive is a fake ref — which corrupts the very
edge the design reads. Convention alone is too weak, since staleness is the whole risk here. The
warning is the level that surfaces the debt and leaves the judgement with the human or agent
deciding whether this feature legitimately touches no contract.

This lands as one more entry in the shipped validator framework (ADR-541 axis B), not as a
bespoke check: a named per-item validator in the closed catalog, selected by the `feature` type's
own `validators` declaration. Two properties come free. The create/update gate aborts only on
error-level issues, so a warn-level validator is report-only by construction — advisory is a
severity here, not a second code path. And that severity is the only lever if the guarantee ever
needs strengthening; the structure does not change with it.

One constraint on the implementation, stated because it is easy to get wrong: the validator may
not find its edge by comparing against the literal `"implements"`. ADR-775 §2 binds engine
behaviour to a kind's declaration rather than its spelling, and keeps a `tests/meta` scan
asserting that no bundled ref-kind name appears as a literal in `src/squads/` outside `_specs/`
and `_migrations/`. The kind and the target type are read from the merged spec — a parameterised
catalog entry declared on the `feature` type, the shape `subentity_title_max` already uses — so a
squad that renames the kind, or the type, keeps the check.

### D. Collection structure

**One `contract` item per capability / user-facing area.** The collection *is* the set of `PRD-*`
items: each one capability's living contract, edited in place, with ordinary markdown headings for
internal structure. Merge granularity is per file, ownership is per area, and a feature's
`implements` edges point at exactly the contracts it touched. This is why `contract` declares no
`subentity_kind` — structurally it is `guide`, not `feature`.

Sections as sub-entities within one contract is rejected. Sub-entity prose lives in the parent
item's body, so every section would share one file — reintroducing exactly the monolith and merge
contention driver 5 rules out. Sub-entities are also lifecycle-bearing mini-items
(Todo / InProgress / Done), which does not describe a section of a living document.

**Partitioning carries no structural guard.** "One contract per capability area" is the product
owner's judgement. Too coarse and contracts drift back toward monoliths with merge contention;
too fine and a feature fans its `implements` edges across many tiny contracts. Neither failure is
expressible as a spec rule that would not also refuse legitimate shapes, so nothing enforces it.
The position is revisited if it goes wrong in practice, not before.

### E. The generated agent-facing surface

A new item type grows the managed agent-facing surface, all of it regenerated by `sq sync` and
stamped in place as such:

- new `[types.contract]` entries in the interactions playbook (`playbook.toml`) drive a managed
  `sq-contract` skill — per-role enter / do / handoff / watch guidance: the product owner authors
  contracts and keeps them current, the tech lead and each `<tech>-dev` update the touched slice
  as features land, the architect watches cross-contract consistency. The skill's real body is the
  skill item's own body under `squads/agents/skills/`, and generated agent text renders from the
  active spec, the active playbook and the live roster rather than from bundled literals — so a
  squad that renames or drops the type gets text that matches its own vocabulary.
- the `.claude` skill pointer carries only what the host must read before anything can run — its
  `name` and its `description` — plus the command that renders the definition,
  `sq skill sq-contract show`. Under ADR-781 a pointer names commands and never a local file path,
  so it carries no `@` path into the squad directory and no copy of the skill body.
- the per-type CLI group `sq contract`, generated from the declaration in §A with no per-type
  module.
- an item template `templates/items/contract.md.j2` steering the author toward functional-behaviour
  prose. `_default.md.j2` would serve; a dedicated template sets the right shape.

**Nothing in this surface materialises a derived projection.** Under ADR-776 a derived view is
computed on request and never written into an item body. A contract's body is authored prose, and
because the type declares no `subentity_kind` it carries no roll-up summary and no badge head
region — so there is no materialised region here to retire later.

**The on-disk artifacts are verified against the roster for BOTH a fresh `init` AND `migrate`.**
Pointer filenames, targets and descriptions are not validated today, and a type addition that
wired only the `init` path and left `migrate` unregenerated has bitten this project before.
ADR-781 §2c makes that mechanical rather than manual as it ships: the per-entry artifacts become
declared paths scoped to the live roster, `sq check` reports presence and then currency, and the
unprompted root-callback notice reports a missing pointer without being asked. Until presence
lands, the verification is by hand.

### F. Schema and migration

`contract` is one of two item types entering the bundled spec for the 0.14 release; the milestone
type (`MILE`, FEAT-693) is the other. **They share one schema bump and one migration runner**, and
FEAT-321 and FEAT-693 land in the same release. The bump is `0.11 → 0.14` on
`_models/_schema.py::SCHEMA_VERSION` — the schema number names the release that introduces it, and
0.12 and 0.13 shipped without one (see the amendment note); the root CLI callback hard-stops a
squad on a schema mismatch until `sq migrate up` runs. The runner belongs to the release rather than to this
decision — any other schema-level change shipping in 0.14 joins it rather than adding a second
bump.

No existing item data is rewritten on this half, so its deterministic work is light: create the
`contracts/` folder, matching what `init` does per declared type, and regenerate the managed
skills, the pointers and the `CLAUDE.md` / `AGENTS.md` regions so the `sq-contract` surface
appears. The `manual` runbook entry tells an adopting squad that the functional-contract type now
exists and, optionally, to seed initial `contract` items for their current capabilities — a
migration cannot author functional truth on their behalf.

Two release mechanics follow from touching bundled artifacts, inherited rather than restated here.
Editing `workflow.toml` and `playbook.toml` and adding an item template forces a template-manifest
regeneration, which queues behind the version bump (ADR-781 §6). And with ADR-777 §2's manifest
widening, a squad carrying a `.overrides/workflow.toml` sees a genuine, content-gated drift
warning when this lands — the correct signal, in place of the every-release false positive that
spec-document overrides get today.

## Decision

Introduce `contract` (prefix `PRD`) as a bundled item type carried by the existing config-driven
type engine:

- declared as one `[items.contract]` block — prefix `PRD`, folder `contracts`,
  `category = "records"` — plus one `[lifecycles.contract]` block in the bundled
  `src/squads/_specs/workflow.toml`; the CLI group and folder follow from that declaration;
- on a dedicated lifecycle **Draft → Active → Superseded (+ Deprecated)**, reusing existing
  statuses, with `Active` the live steady state and `Superseded` carrying the supersede role;
- structured as **one item per capability area** — a collection of `PRD-*` items with no
  sub-entities and ordinary markdown headings inside — with partitioning left to the product
  owner's judgement and no structural guard;
- linked from the features that shape it by a forward **`implements`** ref, reusing the kind and
  disambiguating it by the target being a `contract`, with `contract` also declaring a
  `supersedes` rule for replacement;
- with maintenance enforced by an **advisory, warn-level `sq check` rule** — a feature reaching
  `InReview` or `Done` with no `implements` edge to a `contract` — expressed as a declared
  per-item validator on the `feature` type, never a hard gate;
- with the managed `sq-contract` skill, its command-naming pointer, the playbook entries and the
  item template generated and stamped as `sq sync`-regenerated, and verified on disk for both
  `init` and `migrate`;
- shipped in the 0.14 release behind the **single schema bump and single migration runner** that
  release also carries for the milestone type, with a manual runbook note.

A contract's body describes **product behaviour only**. Dated discussion comments are the home for
notes about a point in time.

## Consequences and trade-offs

**Positive.** Riding the config-driven engine makes this additive and low-blast-radius: new rows
in the tables the existing types already use, no new mechanism, the CLI group and folder generated
from the declaration. The functional truth becomes queryable in one place, twinning the ADR set,
and the historic→living edge is a plain forward ref that inverts into a free "which features
shaped this contract" view.

**Costs accepted.**

1. **The maintenance guarantee is only as strong as an advisory warning.** A warning can be
   ignored, and a living source of truth that drifts is worse than none — it lies with authority.
   That cost is taken deliberately, because the alternative buys currency with false positives on
   purely technical features and with fake refs added to clear them. The lever if it ever needs
   strengthening is the finding's severity, not the design.
2. **Reusing `implements` gives one word to two relationships** — task→feature and
   feature→contract. Disambiguation rests on the target's type, which every consumer already has.
   A reader skimming raw refs sees the same word for two edges; a dedicated `updates` kind would
   trade that legibility against a larger bundled set. This is a stated cost of the choice, not an
   open question.
3. **Partitioning discipline sits with the product owner and nothing checks it.** Contracts that
   grow too coarse drift back toward monoliths; contracts too fine fan a feature's edges across
   many tiny items. There is no structural guard, by decision, and the failure mode is visible in
   practice rather than at validation time.

## Amendment note

**2026-08-25 — §F's schema number is corrected from `0.12` to `0.14`, and the convention it follows
is narrowed to say what it actually binds.** The number is encoded in the runner's filename, the
registry entry and a required corpus fixture, so it cannot be left for whoever writes the runner.

### A1. The bump is `0.11 → 0.14`, and gaps are the convention rather than an exception

`_models/_schema.py`'s own docstring states the rule: while squads is alpha the schema version
tracks **the alpha release that introduced it**, not an opaque counter. Read from the tags rather
than assumed: v0.12.0 and v0.13.1 both ship `SCHEMA_VERSION = "0.11"`. A schema numbered `0.12`
would therefore name a release that shipped and introduced nothing — the one reading the convention
forbids. A runner shipping in 0.14.0 stamps `0.14`.

Gaps are not a concession to make here; they are already how the series reads. The registry runs
0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.8, 0.10, 0.11 — no 0.6 and no 0.9, because 0.6.0 and 0.9.0
introduced no schema change. Skipping 0.12 and 0.13 applies that same rule, and the migration
corpus (`tests/integration/test_migration_corpus.py`) enumerates the same series, so the fixture
name follows the number rather than the release count.

**The one recorded exception, so nobody derives licence from it.** Schema `0.4` does not name
release 0.4.0: v0.4.0 ships `SCHEMA_VERSION = "0.3"`, and both the 0.3→0.4 and 0.4→0.5 runners
shipped inside release 0.5.0, which walked a squad through two steps in one upgrade. So the
convention binds **forward**: a new schema number takes the release that introduces it, and a
release may introduce more than one. It does not license reading a release number backwards out of
an intermediate schema label, and `0.4` is the only label in the series where that reading fails.

### A2. What the number touches, and what it does not

Three places encode it and must move together — the runner module `_v0_11_to_v0_14.py`, its registry
entry (`version="0.14.0"`, `from_schema="0.11"`, `to_schema="0.14"`), and the corpus fixture
`tests/fixtures/corpus/v0_14` that `test_migration_corpus.py`'s standing rule requires of every
schema bump. Beyond those, nothing changes: ordering goes through `schema_tuple`, so `(0, 14)` sorts
after `(0, 11)` exactly as `(0, 12)` would; the existing registry guard already ties the highest
registered `to_schema` to `SCHEMA_VERSION`; and no test, doc or runbook pins the retired number.

## Amendment note — 2026-08-26: the currency check's trigger, and where the edge's target type is declared

Three questions the FEAT-321 breakdown raised against §C, ruled here. §C stands as written except
where these narrow it.

### B1. The trigger narrows to the settled `done` status role; no new status role is introduced

§C says the finding fires when a feature reaches `InReview` **or** `Done`. It cannot, and the reason
is vocabulary rather than an implementation gap. Read from the bundled document rather than assumed:
`InReview` names the `active` role — the same role `InProgress`, `ChangesRequested`, `Fixed` and
`Active` name — while `Done` names `done`. Binding to `active` warns on every feature merely in
flight, which is not what an advisory currency check is for.

**The trigger is the `done` status role**, resolved through the spec and never compared against a
status spelling, mirroring the shipped `supersedes_incoming`. This is the sanctioned form rather
than a workaround: ADR-604 promoted `role` to the sole explicit status axis precisely because it was
already "the semantic role marker for engine rules that key on a specific status". An engine rule
keys on a role; it does not key on a status name.

Not the broader `settled` property. `retired` and `superseded` are settled too, and a Cancelled
feature delivered nothing — warning on it is exactly the false positive §C's advisory posture is
built to avoid.

**A role separating "under review" from "in progress" is refused.** Such a role would declare
`settled = false`, `live = true`, `hidden = false` — identical to `active` under every derived
predicate, with only the colour intent free to differ, which is presentation. It would be a status
spelling wearing a role's costume, and it would buy the check nothing it does not already have.
Its cost, since the question asked for it: `[roles]` is a bundled catalog every squad merges
(ADR-604, ADR-474), so re-pointing `InReview` re-points it for every existing squad and every
override that reasons about `active`; the role→behaviour join is consumed by the CLI, the TUI and
the VS Code client through the closed colour-intent palette; the `live` flag projects into backend
config for roster types (ADR-697); and `sq workflow statuses`/`roles` payloads change for anything
joining them. That is a cross-cutting vocabulary change made for one advisory check that behaves
identically without it.

**Under an adopter's own vocabulary.** A squad that renames `Done` keeps the check as long as its
delivered status names the `done` role, and a squad that wants no check drops one line from its
`[items.feature]` `validators` list — the selection is per-type declared, so opting out needs no
suppression mechanism. A squad that declares a *custom* settled role instead of reusing `done` loses
the check silently. That residual is accepted and recorded rather than guarded: the alternative is a
load-time rule about which role a lifecycle ought to use, which would be squads legislating an
adopter's semantics.

### B2. The edge's target type is declared on the ref rule, not inferred from the type's rule list

The check has to know that a feature's `implements` edge points at a `contract`. `RefRule` carries
`kind` and `hint` only, so the breakdown proposed reading the accepted kinds from the union of the
declaring type's rules and taking the target type from the validator's parameter, leaving the model
untouched. That is refused, for three reasons in order of weight.

1. **It makes an enforcement surface out of a list whose declared meaning is otherwise hint text.**
   `RefRule`'s own contract is that a rule is a rule *about* a kind, never a permission for one, and
   the Plane-1 coherence check that reads it says the rest plainly: apart from a supersession-role
   rule, a type's `ref_rules` drive hint text only. Under the union reading, any rule later added to
   `[items.feature]` for its hint — bundled or adopter-declared — silently widens the set of edges
   that satisfy the currency check. Binding behaviour to what a declaration *says*, rather than to
   what happens to sit beside it, is the whole point of the axis ADR-775 established.
2. **It splits one fact across two declarations with nothing tying them.** The kind would live in
   `ref_rules`, the target in the `validators` parameter, and the spec would load happily with
   either half missing: a type selecting `ref_rule_target_present:contract` while declaring no ref
   rule has an accepted set that is empty by construction, so every settled item warns and no edge
   can ever clear it. An adopter reaches that unsatisfiable state by deleting one line.
3. **The target type is genuinely new information, and it is load-bearing.** Nothing in the merged
   spec records what type an edge points at, and consequence 2 of this decision accepts that one
   word names two relationships with the target's type as the only disambiguator. That fact is not
   derivable from anything stored — this repository's own corpus already carries 13 feature
   `implements` edges, every one of them pointing at a decision — so it gets a declared home rather
   than an inference.

**`RefRule` gains an optional `target`, naming a declared item type:**

```toml
[[items.feature.ref_rules]]
kind = "implements"
target = "contract"
```

What it means, and what it does not:

- It **types** the rule: an edge of this kind, declared by this type, is expected to point at an
  item of that type. It is not an allowlist and it restricts nothing — a feature carrying
  `implements` to a decision is unaffected, exactly as `ref_rules` has never been a permission.
- It is **not an obligation on its own**. Requiredness stays where selection already lives, the
  type's `validators` list, so a targeted rule that no validator selects is inert — which is what
  lets `contract`'s own `supersedes` rule be targeted without every contract being required to
  supersede one.
- The validator keeps its name, its parameter and its selection line:
  `validators = ["ref_rule_target_present:contract"]`. The parameter **selects** the obligation;
  the rule **types** the edge. The two coincide in spelling here only because `feature` declares one
  targeted rule — a type declaring two enforces just the one named, so this is not one fact stored
  twice.
- **Referential validation gains a real check, which is the field earning its keep.** `target` must
  name an item type the merged spec declares. That belongs in the same Plane-1 referential pass that
  checks the validator's parameter — item types are known only after every `[items.*]` block has
  parsed, whereas the ref-rule parser sees the declared *kinds* alone. The pass can then check the
  pair for coherence: a type selecting `ref_rule_target_present:<T>` with no rule targeting `<T>` is
  refused at load rather than warning forever at runtime. Neither check exists under the
  parameter-only shape.
- **It publishes nothing.** ADR-738 §7 keeps `ItemSpec.ref_rules` as declared vocabulary with no
  catalog field, and publishing any of it is a decision under that family's grammar. `target` is
  carried on the same terms; no `sq workflow` payload grows here.
- **Declare no `hint` on this rule.** `parent_hint` appends every non-empty hint a type's rules carry
  to the message explaining an invalid *parent*, where contract guidance would be noise.

§C's remaining constraint is untouched: the kind and the target type are both read from the merged
spec, and the validator may not find its edge by comparing against the literal `"implements"`.

### B3. First-run scope: no suppression, and the check is inert while the target collection is empty

Measured on this repository's corpus rather than estimated: 105 features, 90 of them `Done`; 13
carry an `implements` edge and every one points at a decision; none points at a contract, and none
can, because the type does not exist. `sq check` reports zero issues here today. §C as built turns
that into 90 warnings on the day it lands, in a repository where a clean `sq check` is a must-pass
gate rather than an advisory.

**The prohibition stands.** No suppression, no grandfather clause, no "created after" date, no
per-item exemption and nothing an item can be marked with. A check that ships pre-suppressed is one
nobody ever acts on, and every one of those mechanisms is a place a team learns to put things.

**The check is inert while the corpus holds no item of its parameterised target type.** This is a
precondition on the finding's premise, not an exemption for a class of items: the remedy for "this
feature records no contract slice" is an edge into a collection that does not exist, so before the
first contract is authored the finding names work that cannot be done, and a finding whose remedy is
unavailable is noise by construction. It is the shape `supersedes_incoming` already has — that check
runs only for a type declaring a supersession rule — moved one step from declaration to corpus.

Nothing is permanently excused. The day the first contract is authored the check evaluates every
settled feature, the pre-existing ones included, so the debt arrives in full at the moment a team has
decided to keep the collection — which is also the moment it is actionable, since seeding the
collection is the work each finding points at. The count is reported to the operator with a real
number in hand either way; the decision to seed this repository's contracts is his, and it is product
work rather than part of the type's delivery.

The cost, stated rather than hidden: check behaviour varies with corpus state, so authoring one item
turns on a batch of findings at once, which is surprising the first time it happens. That is the
honest shape of adopting a currency practice, and it is preferable to a permanent floor of warnings
that trains the team to stop reading them.

Two implementation notes that follow. The "corpus holds an item of type T" aggregate is computed once
per run alongside the existing incoming-supersedes aggregate, never rescanned per item. And on the
single-item create/update gate path, where no index handle is available, the precondition cannot be
evaluated and the check yields nothing — failing open is correct for a warn-level finding that never
gates anything.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:38:06Z] Robert Architect:
  - Applied ADR-541s standing instruction — reworded to the `records` category — and re-derived section As mechanism, which had stopped describing anything. This stays forward design; the operator has moved FEAT-321 out of this release, so nothing here is blocking work.
  - The substantive finding is that the option analysis inverted, not that citations went stale. A2 was chosen because prefix/folder/id resolution had a reserved fast-path so it needed no custom-type plumbing, and A1 was rejected partly because that plumbing was incomplete. Both premises are false now: there is no reserved fast-path (ADR-266/322) and the plumbing shipped (ADR-263 plus a default item template). So A1 and A2 are no longer two mechanisms — both mean declaring `[items.contract]` in a spec, differing only in which spec.
  - Re-derived on the driver that survives untouched: this type ships to every squad out of the box, so it goes in the bundled spec. The mechanism is now one `[items.contract]` block plus one `[lifecycles.contract]` block in `src/squads/_specs/workflow.toml` and nothing else — a stronger version of the original conclusion, reached without the reserved-vocabulary argument it used to lean on.
  - Smaller corrections: `is_meta = false`/`severity_field = false` to `category = "records"` with no severity field binding (ADR-541 on the taxonomy, ADR-323 on the field); section Cs closed frozenset is `VALID_REF_KINDS` in `_models/_item.py` at nine kinds, which leaves the reuse-`implements` recommendation intact; the `0.7 → 0.8` bump is history. Everything genuinely settled is untouched — the living-versus-historic model and its five drivers, B2s lifecycle, D2s one-item-per-capability, the forward `implements` edge, advisory over hard gate, and section Es verify-on-both-`init`-and-`migrate` rule.
  - Added `related` edges to ADR-541, ADR-322, ADR-263 and ADR-323 — this decision had none, so nothing pointed at the four decisions that moved the ground under it.
- [2026-08-24T18:02:24Z] Pierre Chat:
  - Enforcement stays advisory as written: warn-level, never a hard gate. A gate manufactures false positives and fake refs on purely technical features.
  - Ref kind: reuse implements, disambiguated by the target type. ADR-775 removes the vocabulary-growth cost, but reuse still reads correctly and keeps the bundled set smaller.
  - Partitioning: no structural guard. One contract per capability area stays the product owner judgement, revisited only if it goes wrong in practice.
  - Schema: 0.14 carries ONE bump for both new item types (PRD and MILE) in a single migration, so FEAT-321 and FEAT-693 land in the same release.
- [2026-08-24T18:16:43Z] Robert Architect:
  - Rewrote the body to read as the current decision rather than a log of its own revisions: the three layers of inline "Rewritten/Reworded 2026-08-03" italics and the Amendment note are gone. The one piece of history worth keeping — the inverted A1/A2 option analysis — survives as a short paragraph inside section A, because a reader needs to know the reserved-fast-path argument is dead, not that a citation moved.
  - Folded in the four rulings. C: enforcement is advisory as the decision own position, warn-level, gate refused on false-positives-and-fake-refs. C: implements reused, reasons restated as legibility plus a smaller bundled set — the "expands a deliberately-closed vocabulary" argument is deleted, and the section now says plainly that ADR-775 removed that cost so the choice does not rest on it. D: partitioning carries no structural guard, stated as a ruling, revisited only if it goes wrong in practice. F: one schema bump (0.11 to 0.12) and one migration runner shared with the milestone type in 0.14, FEAT-321 and FEAT-693 together; the runner is the release, not this decision.
  - Stale points corrected beyond the ones flagged. The advisory rule no longer cites _check_decisions as its template — ADR-541 axis B shipped, so it is a named per-item validator in the closed CATALOG selected by the feature type validators list, and the records bundle already carries supersedes_incoming so the supersedes rule needs no new code. The claim that a contract show surfaces its incoming edges is wrong: backrefs print under refs --in/--all, never show. default_workflow.toml corrected to src/squads/_specs/workflow.toml. Section E reconciled with ADR-781 — the pointer names sq skill sq-contract show and carries no @ path — and with ADR-776: the type declares no subentity_kind, so it has no summary or head region to materialise, and the verify-on-both-init-and-migrate obligation now says ADR-781 2c makes it mechanical once presence lands.
  - One real tension, not smoothed over. ADR-775 2 keeps a tests/meta scan asserting no bundled ref-kind name appears as a literal in src/squads outside _specs and _migrations, and implements declares no semantic role — so the advisory check cannot find its edge by comparing against "implements". The body now constrains the implementation: the kind and the target type are read from the merged spec as a parameterised catalog entry on the feature type (the subentity_title_max shape). Second, smaller: ADR-776 6 also owes a migration for the retired body regions. The ruling names PRD and MILE; F is written so any other schema-level change in 0.14 joins the same runner rather than adding a second bump, which keeps both true.
- [2026-08-24T20:16:00Z] Catherine Manager:
  - Accepted on the operator four rulings (advisory enforcement, implements reuse, no partitioning guard, one shared schema bump with the MILE type). Read the revised body before accepting: schema 0.11 to 0.12 verified against _models/_schema.py, no status prose, and the retired closed-vocabulary argument is deleted rather than softened.
- [2026-08-25T18:20:44Z] Robert Architect:
  - Section F amended in place: the bump is 0.11 to 0.14, not 0.11 to 0.12, plus a new amendment note carrying the argument. Confirmed from the tags rather than from the convention text - v0.12.0 and v0.13.1 both ship SCHEMA_VERSION = 0.11, so a schema numbered 0.12 would name a release that shipped and introduced nothing, which is the one reading the alpha convention forbids. Gaps are already the convention: the series skips 0.6 and 0.9 for the same reason.
  - The convention is narrowed in the same change rather than left to be re-derived. It binds FORWARD - a new schema number takes the release that introduces it, and a release may introduce more than one - and schema 0.4 is recorded as the one exception in the series, since v0.4.0 ships SCHEMA_VERSION 0.3 and both the 0.3-to-0.4 and 0.4-to-0.5 runners shipped inside release 0.5.0. Nobody should read a release number backwards out of an intermediate label.
  - A2 names what the number touches so a dev is not left to find it: the runner module _v0_11_to_v0_14.py, its registry entry, and the corpus fixture tests/fixtures/corpus/v0_14 that the standing rule in test_migration_corpus.py requires of every bump. Nothing else moves - schema_tuple ordering is unaffected and the existing registry guard already ties the highest to_schema to SCHEMA_VERSION. Ruled on TASK-813. @tech-lead
<!-- sq:discussion:end -->
