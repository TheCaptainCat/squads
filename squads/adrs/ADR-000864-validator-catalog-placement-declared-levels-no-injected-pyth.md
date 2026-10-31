---
id: ADR-864
sequence_id: 864
type: decision
title: 'Validator catalog: placement, declared levels, no injected Python'
status: Accepted
author: architect
refs:
- ADR-541
- PRD-858
- ADR-777
- ADR-696
- ADR-955
- ADR-167:supersedes
- ADR-982
- ADR-1109
- ADR-1250
description: What a complete validator catalog looks like, which members are always
  on vs opt-in, and why adopter-supplied Python is not built.
created_at: '2026-09-01T15:26:04Z'
updated_at: '2026-10-29T19:50:51Z'
---
<!-- sq:body -->
## Context

`sq check` and the create/update gate share one engine over one closed catalog. The catalog was
assembled by lifting hardcoded checks into named members, then adding a member whenever a new rule
was wanted, without asking what the *complete* set looks like or on what principle a member
belongs always on rather than available and unselected.

The question became concrete when the currency rule for contract refs met real data and produced
92 warnings in a repository where a clean `sq check` is a must-pass gate. Every one was correct
against the rule and useless to the reader: plenty of delivered work implements no adopter promise,
deliberately. That case exposed that **"is this a defect in any squad?" and "is this a defect in
some squad?" are different questions**, and the catalog had been answering the second while
filing the answers under the first.

Three things are in scope: the catalog as a designed set; checks that should exist for adopters
this squad would never run; and whether an adopter should be able to supply their own Python as a
validator. The rulings are op-pierre's (2026-09-03): build the catalog out, with the declaration
surface that makes it dialable, and no adopter-supplied Python.

A per-item type's effective set is `COMMON_CORE` (always on) + the members on by default for its
category (`CATEGORY_BUNDLES`) + the type's own `validators` list. The composition is extend-only:
a type's list never subtracts from the always-on set or its category's defaults. The name catalog
lives in the spec layer (`_workflow/_validator_names.py`) and the behaviour in the service layer,
joined by an import-time assert that the two sets are equal, and `CONSISTENCY_CLAUSES` pairs each
validator with the clause that guards its reachability, with `UNGUARDED_VALIDATOR_NAMES` naming the
ones argued to need none, so a new member cannot be added without someone deciding which bucket it
is in.

Claims about behaviour below are labelled **(read)** where they come from the source,
**(driven)** where they come from running the CLI against a throwaway squad, and
**(speculative)** where they describe a design that does not exist.

## Decision

### 1. The placement test

The distinction the contract rule proved should be stated as a rule rather than rediscovered.
Three placements, with a test for each:

**Always on.** A finding that is a defect in *every* squad, whose subject exists whenever an item
exists, and that a well-run team can never legitimately sit in permanently. Test: *can a
competent squad be in this state on purpose, indefinitely?* If yes, it is not always on.

**On by default for a category.** A finding whose subject is a capability the *category* implies — a `work`
type burns down and hangs off a parent, a `records` type is a root document that can be
superseded. Test: *does this check follow from what the category means, or from what the
bundled types happen to want?* A check that follows only from the bundled vocabulary belongs
on the type, not in the category.

**Opt-in.** A finding that encodes a *policy* — a team's convention about how work should
be described or linked — rather than a defect. Test: *is clearing the finding a mechanical fix,
or a judgement call about the work?* A judgement call means the check is a policy, and a policy
belongs behind an opt-in. The contract-currency rule failed exactly this test: clearing it
required deciding, per feature, which promise the feature shaped.

An opt-in validator is not dead code. Opt-in is the placement that makes the catalog a design
rather than an accumulation, and the one the current set is thinnest in — two members.

### 2. A selection declares its level and parameter

- An entry on a type's `validators` list is `name`, `name:param`, `name@level` or
  `name:param@level`, parsed by one function (`parse_validator_entry`) and validated at spec load.
  An adopter selects a validator and says how much they mean it.
- Every member has one declared default level (`DEFAULT_VALIDATOR_LEVEL`). A selection's `@level`
  overrides it, within a declared floor (`VALIDATOR_LEVEL_FLOOR`) that a selection may raise but
  never lower, for the members whose level is load-bearing: `parent_acyclic` and
  `subentity_container_marker` stay `error`.
- A threshold lives in the spec, as the member's parameter, never in a module constant:
  `subentity_title_max:<n>` and `item_title_max:<n>` take a length, `ref_rule_target_present:<type>`
  the type it selects an obligation for, `external_id_not_in_title:<pattern>` a regular expression.
  The pattern is compiled at load and refused if it does not compile; `@` cannot appear in it,
  since an entry is cut at its first `@` to read the level, and `\x40` spells a literal one. The
  pattern runs unbounded, which is the adopter's own configuration risk, and the adopter
  documentation says that a backtracking pattern can hang `sq check` and a gated write.
- A member never binds to a status role by name. An *active* status is one whose role declares
  `live = true`; a *settled* one is one whose role declares `settled = true`; a *blocked* one is one
  whose role declares `blocked = true`, a boolean on the status role (default `false`; the bundled
  `blocked` role declares it). `sq workflow roles --json` rows carry `blocked`.
- A selection that the spec's own declarations make unable to fire, or unable to be cleared, is
  refused at load: `assignee_present` on a type whose lifecycle holds no status of a live role;
  `blocked_has_blocker` on a type whose lifecycle holds no status of a role declaring `blocked`, or
  in a spec that declares no dependency-role ref kind; `ref_rule_target_typed` on a type that
  declares no ref rule with a target; a work-policy member on a `roster` type. Whether the corpus
  currently holds an offender is never part of that test.

### 3. The gate runs a member only where it can refuse, and only with the context it needs

`ValidatorEngine.gate()` aborts a create or update on the first finding of an effective per-item
member whose resolved level for the item's type is `error`; a member at `warn` is not evaluated at
the gate at all, and `sq check` still runs it. Each member declares the context it requires (the
item's on-disk text, a full-index scan), the gate builds its runnable set from the context it
holds, and an assertion over the catalog enforces the correspondence, so no member falls out of the
gate by the accident of a sentinel.

The gate is not widened to the item's on-disk text. A create builds the `Item` in memory and gates
it before the markdown exists, so a text-reading member could act on some gated doors and not
others. `subentity_container_marker` therefore runs in `sq check` only, and keeps `error`: the
condition it reports (a sub-entity kind's `plural` renamed over existing items) half-bricks a
corpus, no create or update causes or cures it, and gating on it would refuse every item of the
type at once for a defect none of them has. Report severity and gate participation are two
declared properties, not one field doing two jobs.

### 4. The catalog

**Always on (`COMMON_CORE`):** `item_status_valid`, `dangling_ref`, `ref_kind_valid`,
`agent_registered`, `parent_acyclic`, `attribute_valid`. `parent_acyclic` is the clearest case: a
parent cycle is a silent corpus state that made `sq tree` non-terminating.

**On by default for a category (`CATEGORY_BUNDLES`):** `work` turns on `parent_in`,
`subentity_status_valid`, `subentity_container_marker`, `subentity_body_written`,
`subentity_deferral_resolved` and `subentity_mapping`; `records` turns on `no_parent` and
`supersedes_incoming`; `roster` turns on `pronouns_valid`.

**Opt-in, selected by the types that want them:**

- `no_status_banner` and `subentity_title_max:<n>`: house conventions, not universal defects. Both
  fail the placement test as always-on members, so they are opt-in, and this project's own spec
  selects them on every type it wants them on (`squads/.overrides/workflow.toml`).
- `parent_present`: requires a parent. Its rule was always right; its cliff was its level, so it is
  opt-in and selectable at `warn`.
- `ref_rule_target_present:<type>`, the contract-currency rule that started this record.
- The policy members: `item_title_max:<n>`, `ref_rule_target_typed`, `body_written`,
  `description_present`, `assignee_present`, `blocked_has_blocker`,
  `settled_requires_discussion`, `external_id_not_in_title:<pattern>`,
  `frontmatter_key_undeclared`, `item_skill_shadowed`.

**Squad-global members** are selected in `[squad] validators` (ADR-982), with the same placement
test: `children_settled_with_parent`, `dependency_acyclic`, `wip_limit:<n>`,
`unassigned_active:<n>`, `stale_active:<days>` and `type_has_live_author` are selectable, never on by
default. `stale_active` reads time through the injectable clock, once per run, so `sq check`
stays deterministic over an unchanged corpus for every squad that has not selected it.

**Not catalog members:**

- A badge or field value outside its declared collection is refused where the index loads, for
  items and sub-entities alike, so no `field_value_declared` member exists: a member could never
  report, because the load refuses first.
- `label_declared` presupposes a declared label vocabulary, and labels are free strings with no
  spec vocabulary behind them. It becomes buildable when that vocabulary exists.

### 5. Adopter-supplied Python is not built

Validator logic is hardcoded, a spec declares only *which* validators run and how loud, and there
is no injected code and no `eval`. Two costs decide it: it would make six private model types a
public API before the compatibility promise that would govern them exists, and it would turn every
mutation verb, the create/update gate included, into an execution vector for code that arrives
with the corpus rather than by a deliberate install. Two things are ruled alongside it so they are
not re-litigated as loopholes:

- If injection is ever revisited, only the **entry-point** shape is admissible (an installed,
  versioned, resolvable package), not a dropped file under `.overrides/`, which would sit inside
  the override contract without participating in it. The compatibility promise for the exposed
  surface is answered *first*.
- The override-templates asymmetry (adopter Jinja renders in-process in an environment that is not
  a security boundary) is **not** settled here and is **not** a reason to admit validators. It is a
  question about templates, owned by whoever writes the stability promise. View transforms
  (ADR-1109) are a separately decided, trusted adopter surface; they are not validators.

### 6. What the placement test binds

The three placements are the admission rule for any future member: always on is a defect in every
squad that no competent team can sit in on purpose; on by default for a category follows from what
the category *means*, not from what its bundled types happen to want; and a finding whose
clearing is a judgement call about the work is a policy, which sits behind an opt-in. A new member
also states which bucket of the consistency-clause closure it is in, and which context it requires.
An opt-in validator is not dead code; opt-in is the placement that makes the catalog a design.

## Why adopter-supplied Python is not built

#### Trust and execution

Today no adopter-named Python is imported anywhere. The backend registry imports a hardcoded
tuple of two built-in module paths and nothing else; there is no `eval`, no `exec`, and no
dynamic import of a path that comes from configuration (read, across the whole source tree).

The comparison to "the project already runs its own test suite" is the strongest argument for
injection and it is not sound, for one reason: **consent and timing**. Running a test suite is a
deliberate act against code you have decided to trust, at a moment you chose. `sq check` is a
reflex — every agent runs it before every handoff — and the same engine backs the create/update
gate, so `sq task 5 status Ready` would become an execution vector. A `git pull` that adds a
file under an injection directory would gain code execution on the next `sq` command with no
separate act of trust anywhere in the sequence. That is a genuinely new property, and it is
worse for exactly the adopters this feature is for: a squad cloned from another team, or a
template repository, is precisely the case where the corpus arrives from somewhere the reader
has not audited.

The honest counterweight, which should not be suppressed: **an adopter can already get code to
run in-process today.** Templates under the override templates directory shadow bundled ones by
name and render in a plain Jinja2 environment — not a sandboxed one (read: the environment is
constructed directly, `autoescape` off, `StrictUndefined` on). Jinja2's own position is that
the default environment is not a security boundary. I did not attempt an exploit and make no
claim about how far that reaches in practice; what I will say is that if the threat model
forbids injected validators, the same threat model has something to say about override
templates, and the two should be answered together rather than one being used to wave the
other through.

#### Discovery and declaration

Two shapes, and they differ on precisely the consent question above (speculative — neither
exists).

A **dropped file** — say a directory under `.overrides/` holding modules that declare
validators — is discoverable, diffable and travels with the corpus, which is everything the
override system is good at. It is also the shape with no act of trust in it.

An **entry point** — a package the adopter installs that advertises validators — puts the trust
decision where trust decisions belong: an install, performed deliberately, resolvable to a
version and a source. It costs the adopter a package to author for what might be twenty lines.

There is an asymmetry with the override contract that matters and is easy to miss: `.overrides/`
overrides *documents*. Each override is scaffolded from a bundled base, stamped with the base
version it was written against, and reported when the base moves — the machinery is a diff
against something we ship. There is no bundled validator file, so there is nothing to diff, and
the stamp has no meaning. A validator directory would therefore *sit inside* `.overrides/`
without *participating in* it, which is a worse outcome than living somewhere else honestly:
adopters would reasonably expect `sq override` to know about it. (Read, for the mechanics: an
override missing its base stamp is an error-level check finding — driven, incidentally, while
opting into the currency rule.)

#### API surface and stability — the real cost

The two context objects are frozen dataclasses in a private service module, in a package whose
`__init__` re-exports nothing. Handing them to adopter code makes public API of the contexts
*and of their field types*: the item model, the index model, the workflow spec, the resolved
paths, the playbook spec, and the issue record. That is six types across five private packages,
promoted to a compatibility surface.

Two things make that expensive rather than merely annoying. First, the convention here is that
every implementation module is private with no re-exports, so there is no façade to put them
behind — one would have to be built, and everything in it becomes a versioned promise. Second,
these are not stable types: the item model's ref encoding has already changed shape once, and
the on-disk schema has been stamped four times. A public validator API freezes the shape of the
item model against adopter code at exactly the point in the project's life when it is still
moving.

And the surface it would freeze is one whose stability contract does not exist yet. The
compatibility promise — which surfaces are versioned, what the pre-1.0 migration promise is,
what is explicitly not public — was named in the contract seeding pass as the single largest
gap in the contract set. Injecting validators means answering that question first, for this
surface, in isolation from the rest of it. That ordering is backwards, and it is the strongest
non-security argument against building this now.

#### Failure modes

Better than expected in one direction and worse in another.

**Raising is safe.** The gate runs inside the open transaction, with the store's lock held, and
before the markdown render and write (read: the model is built and gated, then the file is
rendered and written). An exception escaping the transaction body releases all three lock layers
and reaches `os.replace` never having been called, leaving markdown ahead of the index — the one
skew direction the reconcile heals losslessly, by design: `sq repair` on a squad at the package's
schema, and the reconcile `sq migrate up` runs before its first runner on a squad behind it
(ADR-955). So an injected validator that raises produces an ugly traceback instead of a clean
error message, and does not corrupt anything. The durability model already covers this case.

**Hanging is not.** Validators are synchronous callables and `sq check` is an async method
(read), so a validator that loops blocks the event loop for the whole process, and there is no
timeout available without moving execution to a thread or a subprocess. On the gate path it is
materially worse: the hang happens with the index lock held, so it blocks every other `sq`
mutation against that squad — not just the caller. I drove this shape by accident from the other
end: the parent-cycle finding above is a non-terminating walk in *our own* code, and the
experience of it is a command that simply never comes back.

**Mutation is the quiet one.** Both contexts are frozen dataclasses, but the item model and the
index model they carry are ordinary pydantic models with no frozen configuration (read). Frozen
containers do not deep-freeze their contents. So injected code can mutate the item it was handed
— and on the gate path that item is the one about to be written, so the mutation commits. On the
report path, `sq check` currently guarantees it takes no lock and never writes, and that
guarantee is structural: nothing in the read path can write. Injection converts it into a
guarantee about the bundled catalog only, since arbitrary Python can simply open a file. Losing
a structural guarantee and keeping the sentence that states it is how prose starts asserting
more than the code holds.

**Slow is a policy question, not a bug.** A check that takes a minute because an adopter wrote a
quadratic validator over ten thousand items is their problem, provided the tool does not
misattribute it. It would need attribution — per-validator timing in the report — which is cheap
and worth having regardless.

#### Layering

The least hard of the five, and the one most likely to be mistaken for a blocker.

The name catalog lives in the spec layer precisely so the load-time membership check can reject
an unknown name without the spec layer importing upward into services (read: the constant's own
comment says so). An injection loader has to live at or above the service layer, so a naive
version leaves two exits, both bad: give up load-time membership checking for injected names —
failing open on exactly the axis the standing ruling closed — or push a module that imports
adopter code from disk down beneath the pure spec layer.

There is a third exit, and it is the pattern this codebase already prefers: parameterise. The
spec loader would take the set of known validator names as an argument, defaulting to the closed
set, and the caller that already knows about injection supplies the widened set. No new import
edge, no global, and the fail-closed check survives intact. The rendering layer's position above
the interaction and spec layers is not disturbed, because nothing about this touches rendering.

What the layering *cannot* be parameterised out of is the consistency-clause closure. Every
catalog member is either guarded by a reachability clause, always on, or explicitly argued to
need no guard, and an import-time assert closes the union. An injected name is in none of those
buckets and cannot be, because the clause that would guard it would have to be written by the
adopter too. So the closure either stops covering the whole effective set, or injected
validators sit outside a property the catalog currently has end to end. That is a smaller cost
than the API surface, and it is a real one.

#### The strongest argument against this recommendation

It is this. A closed catalog means every rule an adopter wants has to come through us, and the
catalog's own history is evidence that we are not good at guessing which rules adopters want — it took
one contact with real data to discover that a rule we had turned on by default was wrong for its own author.
An adopter with a twenty-line check that encodes their own team's convention has no route at all
today, and telling them to open an issue and wait for a release is a worse experience than
telling them to write a function. The placement test and the level declaration make the catalog better
without making it *theirs*, and a customisation story that stops at "choose from our list" is a
weaker promise than this project makes elsewhere: item types, statuses, roles, ref kinds,
templates and the playbook are all genuinely open. Validators would be the one axis where
customisation means selection rather than authorship, and that inconsistency is a fair thing to
hold against the position above.

The counter to the counter, stated so the next reader can weigh both: the templates are the
precedent that cuts the other way. They are open, and they are also the one place an adopter's
content already executes in-process without anyone having decided that on purpose.

## Consequences

- An adopter selects, levels and parameterises every policy check from the spec, and cannot turn
  an always-on member off.
- This project's own house rules (`no_status_banner`, `subentity_title_max:120`) live in its
  override, not in the bundled defaults.
- A customisation story for validators stops at selection rather than authorship. The argument
  above against that is weighed and outvoted, and stays in the record to be reweighed if the
  compatibility promise changes what is payable.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T15:26:54Z] `architect` Robert Architect:
  - Drafted at op-pierre's request: a complete validator catalog, opt-in members the dogfood would not run, and whether an adopter can inject their own Python. The contract-currency unbundling is the motivating case only — it is being handled separately and is not reopened here.
    
    Verdict on injection: do not build it. The layering objection has a clean answer (parameterise the known-name set through the spec loader) and the durability model already survives a raising validator, but the two costs that remain are unpayable now — it makes six private model types a public API before the compatibility promise that would govern them exists, and it turns every mutation verb into an execution vector for code that arrives with the corpus rather than by a deliberate install. The counter-argument is stated in the body rather than buried: validators would become the one customisation axis where "open" means selection rather than authorship.
    
    Two floor members fail the tiering test the record proposes: the status-banner check is this project's house convention shipped as a universal defect, and the sub-entity title threshold is a module constant every squad inherits. Neither is subtractable — no override surface reaches the floor or the category bundles.
    
    One live defect found while driving the evidence, unrelated to the subject and worth routing: a parent cycle is constructible under the bundled spec (two bugs made each other's parent — two bundled types declare an empty parent list with no no-parent member, which reads as "any parent or none"). sq check reports it clean and exits 0; list, show and repair are unaffected; both `sq tree <id>` and bare `sq tree` had to be killed after twenty seconds. Mechanism: the ancestor walk that builds the keep set and the downward walk both recurse with no visited set. Driven in a throwaway squad, since removed. @manager for the routing call — this wants a bug, not an ADR clause.
- [2026-09-03T08:45:11Z] `op-pierre` Pierre Chat:
  - Ruled: build the catalog out, no adopter-supplied Python. Full scope for 0.15, including the Part 2 catalog-only members. Secondary to ADR-880.
- [2026-09-03T08:50:28Z] `qa` Mara Tester:
  - @manager routing on the parent-cycle defect the architect flagged: it's not new. BUG-865 already tracks it (Fixed by TASK-866, Verified 2026-09-02, closed with the 0.14 milestone commit f8c76e57/0901816c today). Re-drove it on current HEAD — write door refuses (exit 1), a frontmatter-forced cycle is now caught by sq check (exit 3), sq tree no longer hangs on any shape. Linked BUG-865 here (addresses) instead of filing a duplicate.
  - Also for Part 2: the parent_acyclic entry ("None of these exist") is stale — it already shipped as a COMMON_CORE floor validator (_services/_validators.py:267/646, _workflow/_models.py:148/212), landed by the same fix. Worth updating before this ADR is accepted.
- [2026-09-03T08:50:53Z] `architect` Robert Architect:
  - Ruled per op-pierre (2026-09-03): no adopter-supplied Python; build the catalog out. Added "The ruling" section so the record states a decision rather than a recommendation. Scope widened to the full build-out in 0.15 — every buildable Part 2 member, not just the parent-cycle check and the declared-level dimension. Secondary to ADR-880 in priority, not in completeness.
  - Injection is closed with two guards written in so they are not re-litigated: if ever revisited, only the entry-point shape and only after the compatibility promise for the exposed surface; and the override-templates asymmetry is not settled here and is not a reason to admit validators.
  - Accepted build order: (1) parent_acyclic, error/floor — the walk non-termination stays a separate bug, neither waits on the other; (2) the assignment grammar — declared level, declared parameter/threshold, declared required context with an assert over the catalog, which discharges what the correction obliges; the correction rulings carry unchanged (gate not widened, subentity_container_marker keeps error) and requires_parent becomes selectable at warn; (3) re-tier the two floor members that fail the tiering test — no_status_banner and the sub-entity title threshold both move to catalog-only with the threshold declared in the spec, and both are selected by our own spec so nothing weakens here; (4) field_value_declared; (5) the Part 2 catalog-only members; (6) the squad-global members, with stale_active admitted only via the injectable clock and never bundled.
  - One carve-out, on a prerequisite and not on scope: label_declared presupposes a declared label vocabulary that does not exist, so it stays a named member with its prerequisite recorded and blocks nothing above it.
- [2026-09-03T08:53:39Z] `architect` Robert Architect:
  - Correction to my comment above, and to the ruling as first written: parent_acyclic is NOT 0.15 work — it already shipped. Verified against source myself: implemented _services/_validators.py:267, registered :646, in VALIDATOR_NAMES and COMMON_CORE at _workflow/_models.py:148,212; both walks now carry visited sets (_services/_base.py:215-247, :250-300). Landed 2026-09-02, after the comment that reported it here and before the 0.14 tag.
  - Part 2 opens "None of these exist (read: ...)" — that (read) label no longer holds, so it is corrected in place under its own heading rather than tidied away: of Part 2s sixteen named members, parent_acyclic is the one that exists, the other fifteen do not. Same class of error as the gate clause, corrected the same way. Thanks @qa for catching it on BUG-865.
  - The accepted build order therefore opens on the declared level/threshold plus declared required-context dimension, then re-tiering the two floor members, field_value_declared, the Part 2 catalog-only members, and the squad-global members. Also corrected while there: Part 1s requires-a-parent check is parent_present in the catalog, and it is the member that becomes selectable at warn once level is declarable.
- [2026-10-11T20:19:44Z] `architect` Robert Architect:
  - 2026-10-11: narrowed in place, on the operator's ruling of this date recorded on MILE-934. One dated note, under "Failure modes", after the paragraph stating that a raising validator leaves markdown ahead of the index, the direction `sq repair` heals. It says the claim holds at the package's schema, and that while a squad's schema is behind the package the gate refuses `sq repair` and the reconcile inside `sq migrate up` is the recovery path (ADR-955 and its amendments of 2026-10-09). Nothing else in the body changed; `related` ref to ADR-955 added.
- [2026-10-12T05:59:29Z] `architect` Robert Architect:
  - 2026-10-12: two dated notes added in Part 2, nothing else in the body changed. For op-pierre to confirm. @manager
    
    - At `blocked_has_blocker`: a member never binds to a status role by name (ADR-696 section 3). "Active" is a role declaring `live = true`; `blocked_has_blocker` takes its role as a required parameter; a selection the spec makes unable to fire or to be cleared is refused at load.
    - At `external_id_not_in_title:<pattern>`: the pattern is a template of literal text, `{d}` and `{A}`, not a regular expression, because nothing in the standard library bounds a `re` match.
    - The squad-scope half is a note in ADR-982 clause 4. Reasoning and the gate ruling for `blocked_has_blocker` are on TASK-1001.
- [2026-10-12T06:19:20Z] `op-pierre` Pierre Chat:
  - 2026-10-12, on the amendment notes of this date:
    
    - Status roles: a role declares what it means with a flag. Active is a role with `live = true`. Blocked becomes a `blocked` flag on the role, uniform with `live`, and `blocked_has_blocker` takes no parameter. No role name is hard-wired in the engine. This replaces the note's required `:<role>` parameter.
    - A selected check that the squad's own vocabulary makes unable to fire is refused at load, as the note says.
    - `external_id_not_in_title` takes a regular expression, as this decision first said. The template grammar of the note is not adopted; the cost of a bad pattern is the adopter's own configuration risk.
- [2026-10-16T20:58:39Z] `op-pierre` Pierre Chat:
  - 2026-10-16: the validator 'tiers' are not understandable. Drop the word for validators everywhere (this ADR's title and tiering-test heading, code docstrings, docs) and use plain terms: always on, on by default for a category, opt-in, and file checks for the raw scan. Wording only, no behaviour change. Recorded as a task for later, not 0.16.
- [2026-10-24T23:46:53Z] `architect` Robert Architect:
  - 2026-10-25: renamed for plain terms (TASK-1077 ST1). Title "three tiers" -> "placement"; heading "The tiering test" -> "The placement test"; body: Floor -> always on, Category bundle -> on by default for a category, Catalog-only -> opt-in, tier -> placement. Wording only, the decision is unchanged. The level floor (a selection may raise a level, never lower it) keeps its name: it is a different concept.
- [2026-10-25T21:42:21Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. Parts 1-2, the 2026-09-02 gate correction and the 2026-09-03 ruling folded into sections 1-6; the catalog is listed as built (validator_names.py). field_value_declared is recorded as not a member (the index load refuses the value; FEAT-900 cancelled), the ADR-864/982 amendment notes folded (blocked flag, regex pattern). Part 3 reasoning kept.
- [2026-10-29T19:50:51Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 per ADR-1250 §11 (accepted by op-pierre 184b880), board rule 6, linked related to ADR-1250. Status unchanged. The validator name `subtask_story_mapping` becomes `subentity_mapping` (ADR-1250 §1); no other change.
<!-- sq:discussion:end -->
