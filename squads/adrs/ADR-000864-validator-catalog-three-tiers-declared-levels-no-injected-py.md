---
id: ADR-864
sequence_id: 864
type: decision
title: 'Validator catalog: three tiers, declared levels, no injected Python'
status: Proposed
author: architect
refs:
- ADR-541
- PRD-858
- ADR-777
- ADR-696
description: What a complete validator catalog looks like, which members are floor
  vs opt-in, and why adopter-supplied Python should not be built.
created_at: '2026-09-01T15:26:04Z'
updated_at: '2026-09-01T15:26:54Z'
---
<!-- sq:body -->
## Context

`sq check` and the create/update gate share one engine over one closed catalog. The catalog
was assembled by lifting the hardcoded `_check_*` methods that existed at the time into named
members, then adding a member whenever a new rule was wanted. Nobody has since asked what the
*complete* set looks like, or on what principle a member belongs in the always-on floor rather
than sitting available and unselected.

The question became concrete when the currency rule for contract refs met real data for the
first time and produced 92 warnings in a repository where a clean `sq check` is a must-pass
gate. Every one of those warnings was correct against the rule and useless to the reader: the
rule had no way to record "this delivered work implements no adopter promise, deliberately",
because plenty of delivered work genuinely does not. The resolution — unbundle it, leave the
edge typing in place, let a project opt in — is being applied separately and is not reopened
here. What that case exposed, and what this record is about, is that **"is this a defect in
any squad?" and "is this a defect in some squad?" are different questions, and the catalog has
been answering the second one while filing the answers under the first.**

Three things are in scope: the catalog as a designed set; checks that should exist for
adopters this squad would never run; and whether an adopter should be able to supply their own
Python as a validator.

Every claim below about current behaviour is labelled **(read)** where it comes from the source,
**(driven)** where it comes from running the shipped CLI against a throwaway squad, and
**(speculative)** where it describes a design that does not exist. The throwaway squad was a
fresh `sq init` in a scratch directory, removed afterwards.

---

## Part 1 — the catalog as a designed set

### What is there (read)

Fifteen per-item validators and five squad-global ones. A per-item type's effective set is
`COMMON_CORE` + its category's bundle + the type's own `validators` list. The floor is five:
item status validity, dangling ref, ref-kind validity, no status banner, agent registered. The
`work` bundle adds parent eligibility and the four sub-entity checks plus story mapping; the
`records` bundle adds no-parent and the supersession check; `roster` adds nothing. Two members
sit in no bundle at all and are reachable only by a type naming them: the requires-a-parent
check and the ref-rule currency check.

The composition is **extend-only, with no subtraction surface anywhere**. `effective_validator_names`
takes the floor and the bundle table as parameters, but both production call sites pass the
module defaults; the only test that substitutes a stub is exercising the composition itself.
The `[selected]` deselection mechanism in the override merge drops *keys from a spec document
section* — an item type, a status — and the floor and bundle tables are Python constants, not
document sections, so no override reaches them. An adopter cannot turn a floor member off.

Two structural properties are worth keeping and are easy to lose. First, the name catalog lives
in the spec layer and the behaviour lives in the service layer, joined by an import-time assert
that the two sets are equal, so a spec's declared name can be checked for membership without the
spec layer importing upward. Second, `CONSISTENCY_CLAUSES` pairs each validator with the clause
that guards its reachability, `UNGUARDED_VALIDATOR_NAMES` names the ones argued to need none,
and an assert closes the union against the whole catalog — so a new member cannot be added
without someone deciding which bucket it is in.

### The tiering test

The distinction the contract rule proved should be stated as a rule rather than rediscovered.
Three tiers, with a test for each:

**Floor.** A finding that is a defect in *every* squad, whose subject exists whenever an item
exists, and that a well-run team can never legitimately sit in permanently. Test: *can a
competent squad be in this state on purpose, indefinitely?* If yes, it is not floor.

**Category bundle.** A finding whose subject is a capability the *category* implies — a `work`
type burns down and hangs off a parent, a `records` type is a root document that can be
superseded. Test: *does this check follow from what the category means, or from what the
bundled types happen to want?* A check that follows only from the bundled vocabulary belongs
on the type, not in the category.

**Catalog-only.** A finding that encodes a *policy* — a team's convention about how work should
be described or linked — rather than a defect. Test: *is clearing the finding a mechanical fix,
or a judgement call about the work?* A judgement call means the check is a policy, and a policy
belongs behind an opt-in. The contract-currency rule failed exactly this test: clearing it
required deciding, per feature, which promise the feature shaped.

A validator nobody bundles is not dead code. It is the tier that makes the catalog a design
rather than an accumulation, and the tier the current set is thinnest in — two members.

### Two floor members fail their own test

**The status-banner check is a house convention in the floor.** It reports a body or summary
whose first line opens with `STATUS:` or a `## Status` heading. This project has a strong,
stated reason to want that: status lives in frontmatter and prose copies of it go stale. That
reason is not universal. A team whose ADR template has carried a `## Status` heading for a
decade gets a warning on every record they own, on a floor member with no subtraction surface,
and their only remedy is to restructure their documents to suit a tool. Relocating it to the
`records` and `work` bundles would not help — a bundle cannot be subtracted from either. The
honest placement is catalog-only, selected by the types that want it, and selected by this
project's own spec.

**The sub-entity title threshold is a constant, not a declaration.** The advisory fires above
120 characters, and 120 is a module constant with no spec field behind it (read). Every squad
gets our number. This is a smaller version of the same defect: a policy shipped as a floor.

Neither is urgent and neither is broken. Both are the same mistake the contract rule made, and
both are still standing.

### The dimension the catalog does not have: declared level and threshold

Each validator hardcodes its own level. Error-level findings fail the gate and abort a create
or update; warn-level ones are advisory everywhere (read). An adopter can select a validator
but cannot say *how much they mean it*.

That single missing dimension explains most of the pressure toward injected code. The
requires-a-parent check is unbundled because turning it on would error on every parentless item
already on disk (its own docstring says so) — but as a *warning* it would be immediately
useful to a project that wants the convention without the cliff. The contract-currency rule
would have been shippable-bundled at warn if a project could have dialled it, and it is warn
already; what it lacked was a parameter for "and here is the class of work that is exempt by
construction". A threshold expressed in the spec rather than in a module constant covers the
title case.

The likely shape (speculative): a level suffix on the assignment (`name:param@warn`) or a
per-type map, validated at spec load the same way the parameter suffix already is, with a
declared floor a selection may raise but not lower for the members whose level is load-bearing.
This is a smaller change than injection and covers a large share of what injection would be
used for.

---

## Part 2 — checks that should exist, including ones this squad would not run

Each is named with the tier it belongs in and who it is for. Levels are the proposed default.
None of these exist (read: none appear in either name catalog).

**Defects — these belong in the floor or a bundle, for everyone:**

- **`parent_acyclic`** (error, floor). A parent chain that closes on itself. Driven: two bugs
  made each other's parent under the *bundled* spec, with no override involved; `sq check`
  reported no issue and exited 0, `sq list`, `sq <type> <n> show` and `sq repair` all behaved
  normally, and both `sq tree <id>` and bare `sq tree` had to be killed after twenty seconds.
  Read, for the mechanism: the ancestor walk that builds the keep set has no visited set, and
  the downward walk recurses without one either. Read, for reachability: two bundled types
  declare an empty parent list with no no-parent member, which the parent-eligibility validator
  documents as "any parent or none" — so this is not an adopter-only shape. This is the
  clearest case in the whole list: a silent corpus state that every gate calls clean and that
  makes one command non-terminating. For everyone.

- **`field_value_declared`** (error, work + records bundles). A badge or field value in
  frontmatter that is not a member of the collection its field declares. Values set through the
  CLI are parsed against the collection, but a hand-edited file, a bulk import, or a collection
  narrowed in an override after the fact can all leave one behind, and nothing reads it back.
  For every adopter who customises collections — which is to say, for adopters rather than for
  us, since we ship the collections we use.

**Policies — catalog-only, selected by the squads that want them:**

- **`item_title_max:<n>`** (warn). Sub-entity titles are length-checked; item titles are not.
  Driven: a 200-character bug title was created with no advisory and `sq check` stayed clean.
  For any team whose items are authored by agents — ours emphatically included, which makes
  this one this project would select.

- **`ref_rule_target_typed`** (warn). An edge carrying a declared rule's kind but pointing at a
  type the rule does not target. Read: kind validity checks membership in the declared kind set
  and nothing else; the currency check returns early on a *satisfying* edge and otherwise
  reports an absence. Driven, with the currency rule opted in through an override: a feature
  holding an `implements` edge to a task, with a contract present in the corpus, produced
  "settled with no implements ref to a contract" — an accurate message about an absence, and
  no message at all about the edge that was pointing at the wrong thing. For adopters who
  declare typed ref rules, which is the whole point of declaring them.

- **`body_written`** (warn). An item body still sitting at the rendered placeholder. The
  sub-entity equivalent already exists and is bundled; the item-level one does not. For teams
  that create items in batches ahead of writing them.

- **`description_present`** (warn). An item with no summary line, which is what every list
  view shows. For large boards; irrelevant on a small one.

- **`assignee_present`** (warn). An item at an `active`-role status with nobody on it. For
  teams mixing human and agent assignment; noise for a squad where one agent picks up
  everything.

- **`blocked_has_blocker`** (warn). An item at a `blocked`-role status with no dependency edge
  in either direction — the blocker exists only in somebody's head. For teams that use the
  blocked status as a real signal rather than a parking space.

- **`settled_requires_discussion`** (warn). An item reaching a settled status with an empty
  discussion. For teams using the corpus as an audit record, where "why did this close" has to
  be answerable later. Not for a squad that closes routine work silently.

- **`external_id_not_in_title:<pattern>`** (warn). A title carrying a foreign tracker's
  identifier. For teams mirroring another system, who want the identifier in a ref and not
  baked into a title that outlives the mirror.

- **`label_declared`** (warn). A label outside a declared vocabulary. Read: labels are free
  strings with no spec vocabulary behind them, so this member presupposes new spec vocabulary
  and is not shippable on its own. For organisations that want a controlled taxonomy. Named
  here as a catalog member with a prerequisite, not as a candidate ready to build.

**Squad-global candidates:**

- **`children_settled_with_parent`** (warn). A parent at a settled status with open children.
  For everyone, and specifically for the failure this team has already hit more than once —
  a parent closed against its children rather than against its outcomes.

- **`dependency_acyclic`** (warn). A cycle among dependency-semantic edges, which the blocked
  view would render as a permanent mutual block. For adopters who use dependencies heavily.

- **`wip_limit:<n>`** (warn). More than *n* items at an `active`-role status for one assignee.
  For teams running a kanban discipline. Explicitly not for this squad, and a good example of
  the tier: it is a real check, it is nobody's defect, and it would be wrong to bundle.

- **`unassigned_active:<n>`** (warn). The roll-up of the per-item version, for a board owner
  who wants one line rather than fifty.

- **`stale_active:<days>`** (warn). An item at an active status untouched for *n* days. For
  adopters running long-lived boards. Worth naming for a second reason: neither context object
  carries a clock (read), and a check whose output changes with wall-clock time makes `sq check`
  non-deterministic between two runs over an unchanged corpus. That is a real cost, and it is
  the kind of cost that should be argued once in the catalog rather than per adopter.

---

## Part 3 — adopter-supplied Python

The accepted decision that created this framework states the boundary in those words: validator
logic is hardcoded, there is no adopter-supplied validator code and no `eval`, and what a spec
declares is only *which* validators run (read). So this is not a green field. Anything here is
an amendment to a standing ruling, and the burden is on the amendment.

Below, the hard questions, with what is actually true today rather than what would be
convenient.

### Trust and execution

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

### Discovery and declaration

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

### API surface and stability — the real cost

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

### Failure modes

Better than expected in one direction and worse in another.

**Raising is safe.** The gate runs inside the open transaction, with the store's lock held, and
before the markdown render and write (read: the model is built and gated, then the file is
rendered and written). An exception escaping the transaction body releases all three lock layers
and reaches `os.replace` never having been called, leaving markdown ahead of the index — the one
skew direction `sq repair` heals losslessly, by design. So an injected validator that raises
produces an ugly traceback instead of a clean error message, and does not corrupt anything. The
durability model already covers this case.

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

### Layering

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
catalog member is either guarded by a reachability clause, in the floor, or explicitly argued to
need no guard, and an import-time assert closes the union. An injected name is in none of those
buckets and cannot be, because the clause that would guard it would have to be written by the
adopter too. So the closure either stops covering the whole effective set, or injected
validators sit outside a property the catalog currently has end to end. That is a smaller cost
than the API surface, and it is a real one.

### The recommendation

**Do not build injected validators.** Not because the engineering is impossible — the layering
question has a clean answer and the durability model already survives a raising validator — but
because the two costs that remain are ones this project cannot pay right now. It would freeze
six private model types into a public API before the compatibility promise that would govern
them has been written, and it would turn every mutation verb into an execution vector for code
that arrives with the corpus rather than by a deliberate install.

**Build the catalog out instead, and build the declaration surface that makes it dialable.**
Concretely, in the order the evidence supports: the parent-cycle check, because it is a live
non-terminating command that every gate calls clean; declared level and threshold on the
assignment, because that is the dimension whose absence is generating the pressure; then the
catalog-only members above, chosen by whoever wants them.

**If injection is wanted anyway, the entry-point shape is the one to take**, not a dropped file
under `.overrides/`. It puts the trust decision at an install, it is versionable, and it does not
pretend to participate in an override contract that has no base document to diff against. And it
would still need the public-API question answered first.

### The strongest argument against this recommendation

It is this. A closed catalog means every rule an adopter wants has to come through us, and the
list in Part 2 is evidence that we are not good at guessing which rules adopters want — it took
one contact with real data to discover that a rule we had bundled was wrong for its own author.
An adopter with a twenty-line check that encodes their own team's convention has no route at all
today, and telling them to open an issue and wait for a release is a worse experience than
telling them to write a function. The tiering and the level declaration make the catalog better
without making it *theirs*, and a customisation story that stops at "choose from our list" is a
weaker promise than this project makes elsewhere: item types, statuses, roles, ref kinds,
templates and the playbook are all genuinely open. Validators would be the one axis where
customisation means selection rather than authorship, and that inconsistency is a fair thing to
hold against the position above.

The counter to the counter, stated so the next reader can weigh both: the templates are the
precedent that cuts the other way. They are open, and they are also the one place an adopter's
content already executes in-process without anyone having decided that on purpose.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T15:26:54Z] Robert Architect:
  - Drafted at op-pierre's request: a complete validator catalog, opt-in members the dogfood would not run, and whether an adopter can inject their own Python. The contract-currency unbundling is the motivating case only — it is being handled separately and is not reopened here.
    
    Verdict on injection: do not build it. The layering objection has a clean answer (parameterise the known-name set through the spec loader) and the durability model already survives a raising validator, but the two costs that remain are unpayable now — it makes six private model types a public API before the compatibility promise that would govern them exists, and it turns every mutation verb into an execution vector for code that arrives with the corpus rather than by a deliberate install. The counter-argument is stated in the body rather than buried: validators would become the one customisation axis where "open" means selection rather than authorship.
    
    Two floor members fail the tiering test the record proposes: the status-banner check is this project's house convention shipped as a universal defect, and the sub-entity title threshold is a module constant every squad inherits. Neither is subtractable — no override surface reaches the floor or the category bundles.
    
    One live defect found while driving the evidence, unrelated to the subject and worth routing: a parent cycle is constructible under the bundled spec (two bugs made each other's parent — two bundled types declare an empty parent list with no no-parent member, which reads as "any parent or none"). sq check reports it clean and exits 0; list, show and repair are unaffected; both `sq tree <id>` and bare `sq tree` had to be killed after twenty seconds. Mechanism: the ancestor walk that builds the keep set and the downward walk both recurse with no visited set. Driven in a throwaway squad, since removed. @manager for the routing call — this wants a bug, not an ADR clause.
<!-- sq:discussion:end -->
