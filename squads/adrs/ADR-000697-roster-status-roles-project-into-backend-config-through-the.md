---
id: ADR-697
sequence_id: 697
type: decision
title: Roster status roles project into backend config through the ABC
status: Accepted
author: architect
refs:
- FEAT-691:addresses
- ADR-696
- ADR-133
- ADR-141
- ADR-114
- ADR-622
description: Active means materialised, non-active means withdrawn through the existing
  AgentBackend methods; config integrity is a derived transition-time invariant
created_at: '2026-07-29T15:18:23Z'
updated_at: '2026-08-03T08:25:28Z'
---
<!-- sq:body -->
## Context

A roster entry is not only an `sq` record. It is also the source of a file that an entirely
different tool reads as its own configuration. The Claude Code backend writes
`.claude/agents/<slug>.md` per role and `.claude/skills/<slug>/SKILL.md` per skill, plus a
managed region in `CLAUDE.md` that compiles the roster table, the operator list, the default
role, and the per-item-type skills; the AGENTS.md backend writes per-entry staging files under
`.agents_md/{roles,skills}/` and compiles them into an `AGENTS.md` section. Copilot and Codex
are the stated next consumers. A role entry is therefore what makes an agent *spawnable by the
host*, and a skill entry is what makes a skill *loadable*.

Nothing connects that to the entry's status.

- `grep -rn "status" src/squads/_backends/` returns nothing. The `AgentBackend` ABC's seven
  methods — `ensure_scaffold`, `write_managed`, `generate_role_entry`, `generate_skill_entry`,
  `remove_artifacts`, `candidate_orphans`, `managed_paths` — are status-blind, by construction.
- `Service.roster()` and `Service.operators()` list every entry of the type regardless of
  status, and those two lists are exactly what `write_managed` compiles from.
- Demonstrated on a throwaway squad on the current build: after retiring the `qa` role,
  `.claude/agents/qa.md` is still on disk and `sq create bug --author qa` still succeeds. A
  retired role stays spawnable by Claude Code and stays valid as an author.
- `remove_artifacts` — the one method that withdraws an entry's files — already exists, is
  already what `rm` uses, and is already required to be idempotent and missing-tolerant by the
  backend lifecycle-contract suite. It is simply not wired to status.

So the roster's lifecycle is currently decorative on the surface where it matters most: the one
place a loose or unenforced roster state corrupts another tool's config rather than merely
making an `sq` view odd. This decision fixes what the roster's declared status roles oblige a
backend to do. It builds on ADR-696, which supplies the role-keyed lookups and the roster
lifecycle floor (at least one live status; retirement reachable from it) that let everything below
be written without naming a status literal.

Two accepted decisions constrain the shape. ADR-133 committed to a backend-neutral ABC before
the 1.0 freeze — the seam must not be Claude-Code-shaped. ADR-141 fixed multi-active backends:
fan-out iterates the deduped `active_backends` list, order is not significant because backends
write disjoint paths, deactivating a backend leaves its files untouched, and `sq check` is
deliberately present-only rather than a currency check.

## Decision

### 1. A materialised entry is a projection, and only a projection

An entry's backend files are a pure function of three inputs: the entry's frontmatter, the
active workflow spec, and the active backend list. They are never a source of truth, they are
never migrated, and nothing anywhere records that a projection happened — the presence of a
file on disk carries no information the frontmatter does not already carry.

**An entry is materialised if and only if its status carries the `live` flag** — the boolean
ADR-696 §2a puts on the status-role object, read through `spec.live_statuses(item.type)`. Every
non-live status is unmaterialised, whatever its role is called and whether or not that role is
settled. There is no third state and no per-role table of behaviours: one predicate, read through
the spec off a single declared flag.

This is what finally gives a non-live roster state meaning: an entry being written but not yet
live to the agent host has no files, so it cannot be spawned and cannot be loaded. A project
that declares its roster lifecycle's `initial` status non-live gets exactly that on creation,
with no branch anywhere in the engine — the create path reads `initial`, the projection reads the
flag, and for a while they disagree.

### 2. What the two directions oblige a backend to do

- **Materialise** — `generate_role_entry` / `generate_skill_entry` for the entry's own files,
  **and** inclusion of the entry in every managed region the backend compiles, via
  `write_managed`.
- **Withdraw** — `remove_artifacts` for the entry's own files, **and** exclusion of the entry
  from the same recompiled managed regions.
- **Reactivate** — materialise again, in full. Because the artifact is a projection there is no
  partial-regeneration or repair path to design: the same call that first wrote the file writes
  it again from the same inputs.

Withdrawal is deliberately two-part, because the two built-in backends have two artifact
shapes. Claude Code's per-role pointer is a whole file that must be deleted; the `CLAUDE.md`
roster table is a compiled region that must be rewritten from a list that no longer contains
the entry. Deleting the file without recompiling the region would leave the region naming a
role with no definition — a worse state than either endpoint. A backend that has only compiled
regions and no per-entry files satisfies the first half trivially (its `remove_artifacts` is a
no-op) and the second half is what actually withdraws the entry.

Note that the compiled content depends on the roster in ways beyond the roster table: the
Claude backend's default-role line is picked from the entry carrying `is_default`, and its
generated per-item-type skills branch on whether any developer role is present
(`has_dev`). Withdrawal changes generated *prose*, not only a list.

### 3. Status-awareness lives in the service; the ABC learns nothing

**No method is added to the `AgentBackend` ABC, and no backend ever sees a status.** The
projection is expressed entirely in terms backends already implement, so a Copilot or Codex
backend inherits withdrawal by implementing the same seven methods it would have implemented
anyway. This is the strongest available reading of ADR-133's neutrality commitment: the seam
does not merely avoid Claude-Code vocabulary, it avoids growing at all.

The filter therefore belongs in the service, in the accessors that feed the backends:

- `Service.roster()` and `Service.operators()` return **live-only** entries. They exist to
  feed `write_managed`, and after this they mean "the entries this squad currently offers".
- `Service.roster_all()` and `Service.operators_all()` are added for the callers that need the
  full set.

Which projection each caller takes is a correctness question, not a preference:

| Caller | Projection | Why |
| --- | --- | --- |
| `write_managed`'s roster/operator lists | live | it compiles the host's config |
| `_skill_paths`, `_role_skills_map` / `resolved_skills_for` | live | they name skills the generated entries preload |
| `candidate_orphans` | **all** | see §5 |
| `_author_of` (display-name resolution) | **all** | a retired role's name must still render on the comments it wrote |
| `registered_slugs` (the `agent_registered` check) | **all** | see §10 |
| `sq role list`, `sq operator list`, `sq list -t skill` | **all** | they are the roster's own views, and already carry a status column |

### 4. Fan-out

Materialisation and withdrawal both iterate **every deduped entry of `active_backends`**, the
same list and the same order-insignificance ADR-141 fixed. A backend that was never scaffolded
is still called: `remove_artifacts` is missing-tolerant and idempotent by its existing
contract, so withdrawal against a backend with no files is a clean no-op.

A backend **removed** from `active_backends` is not touched — including a retired entry's
files under it. That follows directly from ADR-141 §5 (deactivation is ignore, not delete): a
backend squads no longer drives is neither refreshed nor probed, so its stale files, retired
entries among them, stay exactly as they were. This asymmetry is deliberate and worth stating
plainly to an adopter, because "I retired the role but the old backend still lists it" is
otherwise a surprise.

### 5. Orphans

`candidate_orphans` receives the **full** roster vocabulary — every entry of every status, plus
the full known skill-slug set — not the live projection.

An orphan means "a file on disk that this squad never managed", which is why the report is
warn-only and never deletes. A withdrawn entry's leftover file is the opposite of that: squads
wrote it, squads knows the entry, and squads is the thing that owes its removal. Feeding the
live-only list here would relabel the squad's own convergence debt as the adopter's foreign
file, and would do so most loudly on exactly the squads that have retired an entry.

### 6. `sq sync` is the convergence point, and the upgrade path

`sync` already sweeps every roster item and regenerates. It gains the §1 predicate: materialise
the entry when its status is live, withdraw it otherwise. That single rule keeps `sync`
idempotent and makes it the total convergence point for the projection.

It is also the whole story for **squads already on disk whose entries are retired today**. No
migration runner and no schema bump is owed: the first `sq sync` after this lands withdraws the
leftover files. Between landing and that sync nothing misbehaves — `sq check`'s backend
reconciliation probes only the always-present top-level files (`managed_paths`), never per-entry
files, so a lingering pointer is not reported and nothing fails.

**No currency check is added to `sq check`.** ADR-141 §4 deliberately scoped backend checking to
present-only, on the grounds that currency would require each backend to re-render and diff its
managed content. A projection mismatch — an active entry with no file, a retired entry with one
— is exactly that class of drift, so it stays out for the same reason, and `sq sync` remains the
tool that fixes it. The door stays open: a currency check can be added later without changing
anything decided here.

### 7. Config integrity: retirement must not break generated config

**A roster status transition is refused when it would *itself* make the resulting projection
structurally invalid for at least one active backend.** This is a derived invariant evaluated at
transition time, not a per-entry property, and it is scoped to the transition's own delta: a clause
answers "does this move break something that was not already broken", never "is this squad
currently well-formed". A squad already sitting in a state a clause would have refused keeps every
transition available to it, the repairing ones included — pre-existing invalidity belongs to the
report-mode validator plane, and a gate that refused on it would make the breakage unrepairable.

**Every clause in this family is conditioned on at least one active backend, with one declared
exception.** The family is defined over the projection, so with `active_backends = []` there is no
projection for any clause to find invalid, and the whole family stays silent: ADR-141 blessed the
sq-only squad and no clause may quietly un-bless it. The exception is `preloaded_skill`'s
`always_on_floor` kind, whose authority
is a declared rule of the roster contract rather than a derived property of the projection — §8
states it and says why it does not inherit the condition. Residual incoherence in a backend-less
squad — a live role's own record naming a non-live skill — is a state-validity question about an
item's own status, which the reporter answers and a gate over a projection that does not exist
cannot.

A scope note, because two different guarantees are easy to conflate. The requirement that the
roster *types* can never be dropped or reclassified is satisfied entirely by ADR-696 — the three
reserved type keys plus the fixed `roster` category — and needs nothing from this decision. What
follows is a narrower, entity-level guarantee standing on its own merit: retiring an individual
entry must not leave the generated config naming something that is not there.

**How a clause is identified.** Every clause carries an identifier that **describes the condition it
checks**, never its position in this list: `no_live_role`, `preloaded_skill`, and the per-kind
identifiers §8 declares for the second of those. Two rules govern them, and between them they are
the whole convention.

- **A clause identifier is internal.** It belongs to the code, to the per-clause ref-kind
  declaration §8 defines, to the tests, and to this decision. It **never appears in user-facing
  text.** A refusal and a report each read as the condition plus its remedy and nothing else — an
  identifier in a terminal is a cross-reference to a document the adopter does not have. The gate
  and the reporter render **identical condition text** for the same finding, because they are two
  renderings of one predicate; where that shared text reads awkwardly in one of them, the shared
  text is what gets fixed, never forked per caller.
- **An identifier describes the condition, so it survives the set changing.** Adding a clause needs
  no renumbering, and withdrawing one leaves no hole to explain. A descriptive name also has to stay
  true: if what a clause checks changes, its identifier changes with it, and that is a feature — a
  name that no longer describes its predicate is a defect a positional label could never surface.

An ordering is still owed and no longer comes free: with positional labels, the order findings are
reported in was implied by the labels themselves. It is now declared explicitly wherever more than
one finding can be rendered together, so output stays deterministic and testable.

*Withdrawn: the previous rule that clause labels are stable and must never be renumbered.* It was
argued here on the grounds that a label appears in every refusal an operator has already read, so
churning it would invalidate their memory of the message. The premise was the defect. The labels
were stable enough as identifiers, but they were doing double duty as user-facing vocabulary, and
that is what made their stability seem to matter — the observed output confirms it, with the gate
printing a label and the reporter printing the same condition without one, so the identifier was
never a reliable handle for an adopter in the first place. Withdrawing a clause then proved
positional labels do not survive the set changing at all: it left a hole where the second clause had
been, readable only by reconstructing the history. Once the identifier is internal there is nothing
for an adopter to remember and nothing to keep stable on their behalf.

The concrete clauses, each derived from what the generated config actually needs. The
default-designation clause is kept in the list under its own heading, as the record of a clause that
was decided and then withdrawn.

- **`no_live_role` — the last live role.** A transition that would leave no `role` entry in a live
  status is refused: the generated config would present no agent at all. This is a cardinality
  property of the projection, not a reference — nothing to sever, and the only remedy is to put
  another role in a live status.
- **`no_default_role` — the default role: withdrawn, not a clause. The projection is fixed
  instead.** Retiring the role carrying `is_default` is **not** refused. What is structurally
  invalid is not "no live role carries the designation" — that is a legitimate, expressible state,
  and one of the two shipped
  backends has no default-role concept at all — it is the Claude backend fabricating a hardcoded
  `manager` slug when it finds no designated role, which writes into the managed region a slug that
  need not exist. **The projection omits what it does not have**: no live role carries the
  designation, no default-role line, and no default-role name in the surrounding orchestration
  prose that reads off the same value. That is the degradation the developer-gated skill text
  already performs when the last `<tech>-dev` role retires (§2), and it is the right shape for
  generated prose conditioned on a roster class emptying.

  A refusal could not have held this invariant in any case. `rm` hard-deletes a role without
  consulting a clause (§11), and a role catalog that designates nobody reaches the same state with
  no roster mutation at all — so the fabricated fallback is reachable with no status transition in
  play, and a clause on the status axis guarded one door of several into a state whose cause sits on
  the other side of the projection. Fixing the fallback closes every door at once.

  What replaces the clause is a **warning on the transition that takes the last live designation
  out of a live status** — same shape as the open-assigned-work warning below, and for the same
  reason: the adopter loses a line of routing guidance from their generated config and should hear
  about it, but nothing another tool reads is left dangling.
- **`preloaded_skill` — a skill something still preloads.** Retiring a skill still named by a live
  role's resolved preload list — system membership or a `scopes` edge — or implied by a declared
  item type is refused, because the generated entry would preload a skill with no definition. Its
  dependants are not all alike — they fall into three kinds with three different remedies, one of
  which is "none" — and it is also the one clause with a mechanised escape. Both are §8's subject.

Retiring the last operator is **not** refused: an operator list may legitimately be empty, and a
freshly initialised squad has none.

**Why derived and not a per-entry `required` flag.** A stored per-entry flag marking some
entries as required is the obvious alternative encoding. It loses on three counts. It stores
what is derivable: "required" is not a property of the entry, it is a property
of what the generated config needs, and the config's needs are already expressed by
`is_default`, by the resolved preload lists, and by the declared type set — a flag is a second
source of truth that goes stale the moment those move. It has to be maintained by hand, on every
entry, forever. And it cannot see the interesting failure at all: `no_live_role` is about retiring
the *last* live role, which no per-entry flag detects, because no individual role is the required
one.

**`--force` does not override this.** `--force` on a status verb overrides the lifecycle's
transition edge — a policy question the operator is entitled to overrule. The clauses are
structural: overruling them writes config another tool will read and be wrong about. The precedent
is already set, in that `force` does not override the status-vocabulary check either. A refusal is
satisfiable wherever a remedy exists — activate a replacement, retire the dependants first — and
where none exists the message says so instead of naming one. **A clause may never assert a remedy
that no command performs.** An unperformable remedy is worse than an honest dead end: it sends the
operator hunting for a verb that is not there, and it hides the real gap behind what looks like a
solved problem. Any clause whose remedy depends on a verb squads has not shipped is either restated
so that what exists satisfies it, or withdrawn until the verb lands — never left asserting the
verb. Section 8 adds a way to *satisfy* `preloaded_skill` in one command, which is categorically
not the same as overriding it.

**Where it runs.** In the pure half of the status transition (`_set_status_model`), which needs
only the transaction's `db` snapshot and runs before any write. That is also the seam the bulk
importer's pre-pass calls, so an import replaying history is held to the same rule at each step.
That has a real cost, stated in the consequences.

**Open assigned work is a warning, not a refusal.** Retiring a role that still holds open
assigned items warns and proceeds. The board is not generated config; conflating board hygiene
with config integrity would make a routine retirement fail for a reason that has nothing to do
with what this rule protects. The lost-default-designation warning under `no_default_role` above is
the same
shape, and the two together mark the boundary: a refusal is owed when the projection would name
something that is not there, a warning when the projection merely says less than it did.

**The projection write happens after the transaction commits**, not inside it. Generated files
are regenerable cache, not markdown items, so they sit outside the markdown-ahead-of-index
durability rule; a crash between the commit and the projection leaves files that the next
`sq sync` converges. This is the ordering the roster create verbs already use today
(`create(...)` then `generate_role_entry`).

### 8. `--unlink`: remove the cause, never bypass the check

`preloaded_skill` stays a refusal. It gains one escape that works by **making the structure
valid**, not by
suppressing the check: `--unlink` on the retirement severs the reference relationships that
constitute the dependency, and then the ordinary, unforced clause evaluation runs and passes on
its own merits.

**The generic formulation.** The flag knows nothing about skills, roles, or the `scopes` kind. A
config-integrity clause already has to name what it reads in order to detect a dependency at all,
so the flag consumes that declaration: each clause additionally declares the **set of ref kinds
whose stored edges constitute the dependency it detects**, empty for a clause whose dependency is
not a reference. A clause with a non-empty kind set is **severable** — `--unlink` enumerates that
clause's edges, removes each, and re-evaluates. A clause with an empty kind set is not severable
and refuses regardless of the flag. This is the closed-catalog / open-assignment shape the
validator model already uses: behaviour in code, per-clause declarations in data, and a future
clause on a future type inherits `--unlink` without the engine growing a branch.

**A declared reference relationship is a stored forward ref edge** — an `item.refs` entry, kind-
tagged inline, owned by exactly one item, discoverable in the other direction only by inverting
`SquadsDB.backrefs` (never persisted; Invariant 4). That is the whole definition, and it is what
makes severance a coherent act: one place to edit, one owner to attribute the edit to, one reflog
line to record it. Anything derived from the spec is not a reference and cannot be severed.

**Which of `preloaded_skill`'s dependants are unlinkable.** It detects three kinds of dependency
that look alike and are not. They differ in what holds the dependency, and therefore in whether a
remedy exists at all. Each kind carries its own identifier — `scoped_edge`, `type_implied`,
`always_on_floor` — named for what holds the dependency, under §7's rule and internal on the same
terms. The refusal must distinguish them and state the remedy per kind — including "none", where
that is the truth. Anything else is a message that sends the operator after a fix that does not
exist.

The three are **ordered by the remedy available**, from severable to none: `scoped_edge`,
`type_implied`, `always_on_floor`. That ordering is now declared here rather than implied by a
number, and it is what statements below appeal to when they say one kind *degrades to* another. It
orders remedies, nothing else — it is not a severity, not an evaluation order, and never a reason to
report only the worst kind a skill happens to be caught by: a skill can be caught by several at once
and each is a separate finding, because each names different specifics the operator has to act on.

**`scoped_edge` — a stored `scopes` edge. Severable.** A custom skill is attached to a role by a
forward `<ROLE-id>:scopes` entry in the skill's own `refs`. Stored, kind-tagged, single-owner, and
severing it is already a first-class operation (`sq skill <addr> unlink-role`) that also already
runs the correct post-commit refresh. `--unlink` reuses that path rather than inventing a second way
to sever an edge. *Remedy: `--unlink`, or the explicit unlink verb first.* Inherits §7's backend
condition: with no active backend no entry is generated, so no generated entry preloads a
definition that is not there.

**`type_implied` — a declared type implies the `sq-<type>` skill. Not severable, but the refusal is
temporary.** There
is no edge: the implication follows the declared type set, so a skill is implicated for exactly as
long as its type is declared. Dropping or renaming that type un-implies the skill, and the same
unforced retirement then succeeds. *Remedy: change the spec, then retry — an act of a different
order from severing an edge, and one `--unlink` must never perform on the operator's behalf.
Retiring one skill may not silently drop an item type.* Inherits §7's backend condition for the
same reason as `scoped_edge`: the implication is squads-authored, but what it breaks is a generated
entry, and with no backend there is no entry to break.

**`always_on_floor` — every role preloads it. Not severable, and there is no remedy.**
`skills_for_role` prepends `squads`, `greeting`, and `sq-memory` to **every** role's preload list,
unconditionally — they are
not per-type, not playbook-mapped to particular roles, and not spec-declared, so nothing an adopter
can write changes the implication. **This is a deliberate rule of the roster contract, not an
artifact of how the preload list happens to be built today: the skills that every role preloads
are a permanent floor and can never be retired.** The refusal says exactly that and offers no
remedy, because offering one would be a lie.

State the floor as a property, not as a list of three names: **whatever `skills_for_role` implies
for every role is un-retirable.** That formulation survives a rename, and survives the set growing
or shrinking, without a blocklist to maintain. No new mechanism is introduced for it — the playbook
already implies the trio for every role and the clause already refuses on that basis; this names the
consequence and fixes a message that previously offered a spec change that cannot be made. Note the
identifier names the *condition* — every role preloads it — not the three slugs that satisfy it
today, which is the same reason the floor is stated as a property.

**`always_on_floor` is the one part of the family that does not inherit §7's backend condition, and
the asymmetry is deliberate.** Every other clause is *derived*: it computes what some generated
config needs, so an absent projection leaves it nothing to defend. `always_on_floor` is *declared* —
a rule of the roster contract that the always-on set is a permanent floor, which stands whether or
not anything projects it. The tempting reading is that it is squads' own concern because the
playbook rather than a backend authors the dependency; that reading is wrong, and would prove too
much, since the `sq-<type>` implication behind `type_implied` is playbook-authored too. What
separates them is the source of the *authority*, not the source of the dependency. So
`always_on_floor` refuses in a squad with no backend, and a backend-conditioned clause set must not
sweep it along on a later refactor. The floor's other condition is unchanged and is about roles, not
backends: a property quantified over every live role is vacuous when there are none, so a squad with
no live role has no floor to enforce (`no_live_role` is what makes that state unreachable while a
backend is active).

**`type_implied` does not yet honour its own promise for bundled types, and the message must not
pretend
otherwise.** The `sq-<type>` implication reaches a role through `item_types_for_role`, which reads
the `PLAYBOOK` singleton — built once at import from the **bundled** workflow spec, with no
squad-directory parameter and no per-request rebuild. So dropping `task` from a project's workflow
override does not remove `task` from the playbook, and `sq-task` stays implied: the `type_implied`
remedy works for a project-declared custom type (whose `sq-<type>` implication is a pure function of
the active spec) and does **not** work for a bundled one. Until the playbook resolves against the
active spec rather than the bundled one — the same per-request-context direction the workflow spec
already took — a bundled `sq-<type>` skill behaves as `always_on_floor`, and the refusal must say so
instead of naming a remedy that will not take effect.

The net reach: `--unlink` helps with adopter-authored custom skills, which is also the only
category an adopter realistically retires. The skills whose retirement would do the most damage are
precisely the ones it cannot touch.

**Direction.** In the one case that exists today the edges are **outgoing from the retiring
entry**: the skill holds the `scopes` refs and the roles are the referents. The mechanism must
still handle the incoming direction, since a future clause may refuse retiring an entry that
others point at — that is what the `backrefs` inversion is for — but nobody should implement the
incoming direction first and conclude the flag does nothing.

**Where the flag lives and how it reads.** On the roster `status` verb —
`sq role|skill|operator <addr> status <S> --unlink` — registered once on the shared
implementation the three addressed subgroups already have, and available only for a
`roster`-category type, because no other category has config-integrity clauses for it to satisfy.
Two edge readings:

- **On a retirement with nothing severable: a reported no-op.** The transition proceeds and the
  command says no references were severed. Refusing here would break a script that passes the flag
  unconditionally, for no benefit; staying silent would leave the operator unable to tell whether
  anything happened.
- **On a transition that is not a retirement: refused as meaningless.** Passing `--unlink` while
  moving an entry *into* a live status is not an empty set, it is a misreading of what the flag
  does, and a clean error serves better than a no-op.

**`--unlink` is not a gentler `--force`, and the two must never be collapsed.** `--force`
overrides a **policy** gate — the lifecycle's own transition edge — and leaves the resulting state
exactly as asked for, sanctioned or not. `--unlink` overrides **nothing**: it performs additional,
explicit, individually-recorded mutations so that the structure genuinely satisfies the clause,
and then
the same unforced check that would have refused runs and passes. Three consequences follow, and
they are the reason to keep the flags apart:

- `--unlink` never suppresses a refusal. If `no_live_role` refuses, or if any `type_implied` or
  `always_on_floor` dependency remains, the transition still fails with the flag present.
- The two compose without interacting: `--force --unlink` forces the edge and severs the edges;
  neither weakens the other's gate.
- **No flag bypasses the clauses, and none may be added.** The moment one exists, generated config
  gets written from a state the engine has already determined is broken — the failure this decision
  exists to prevent.

**What it mutates, and in what order**, under the transaction and durability rules already cited:

1. **Inside the transaction, before any write:** sever the clause's edges in the in-memory
   snapshot, then re-evaluate **every** clause against that prospective state — still as a delta
   against the pre-transition snapshot per §7, so severing an edge cannot make the command
   answerable for a violation it inherited. A transition still refused aborts the transaction, so a
   refusal can never leave a partially severed squad — severing and then refusing in the same
   command must be impossible.
2. **Inside the transaction, markdown first:** write the frontmatter of the retiring entry (its
   `status`, plus its own `refs` for each outgoing edge severed) and of every other referring item
   whose `refs` changed, before the index commit.
3. **Reflog:** one `ref` removal entry per severed edge, plus the `status` entry. The audit trace
   is inherited from the existing ref path; nothing new is needed to make a severance
   attributable.
4. **After commit:** withdraw the retiring entry's projection (§2) and refresh the projection of
   every entity whose projection depended on a severed edge — for a `scopes` severance, one
   partial resync per affected role. Fan-out over `active_backends` per §4.

**What `--unlink` on a skill touches today**, enumerated:

- the retiring skill item — its `status`, and one `refs` entry removed per scoped role;
- each previously-scoped role — its `extra.skills` cache (a re-derivable cache, never
  hand-authored), the `## Skills` region of its body, and its generated entry in every active
  backend;
- the retiring skill's own backend files, withdrawn, and every managed region that listed it,
  recompiled;
- the reflog — one line per severance, plus the status line.

**Reporting is mandatory; a dry-run flag is not.** The command reports each severance — the
referring entity, the entity it stopped referencing, and the kind — because quietly editing
reference relationships is the flag's whole risk, and the reflog data is already there. A
`--dry-run` shape is deliberately **not** added: "what would `--unlink` sever" is answered by
running the command *without* it, which obliges the refusal to enumerate the dependants it found
and classify each by kind. The refusal message is the dry run, and one query surface beats three
spellings of it.

**The refusal names the implicated types.** Because the refusal *is* the dry run, a message that
says only "a type implies this skill" is not one — the operator cannot act on it or even judge
whether acting is wise. So the enumeration is concrete per kind: `scoped_edge` names the roles whose
edges would be severed; **`type_implied` names the specific implicating type or types**;
`always_on_floor` states the floor in one line and stops. Two constraints on how `type_implied` is
worded:

- **It states the mechanism, not a recommendation.** "`sq-task` is implied by declared type `task`"
  is a fact. "Drop `task` to retire this skill" is advice, and it is usually terrible advice — a
  live work type with items under it is not something to drop so that one skill can retire. A
  remedy that technically exists can still be the wrong move, and the message must not nudge
  toward it.
- **It is bounded.** `type_implied`'s set moves whenever the type set moves, and a widely-mapped
  skill can
  implicate many types, so the enumeration caps and summarises the tail the way a collected
  conflict report does, rather than printing an unbounded list.

**Engine-hygiene note.** The existing sanctioned sever path, `unlink_role`, is skill-to-role
shaped: it guards its target's type and hardcodes the `scopes` kind. `--unlink` must instead call a
kind-aware generic removal — today's `rm_ref` drops every edge to a target regardless of kind and
needs widening with an optional kind — plus the projection refresh, leaving `unlink_role` as a
convenience wrapper. Otherwise the flag inherits the very special case it exists to avoid.

### 9. `no_live_role` gains no analogue, and the default designation has its own verb

**`no_live_role` has no edge at all.** "At least one live role for a backend to present" is a
cardinality property of the projection, not a reference. There is nothing to sever, and the only
remedy — put another role in a live status — is a choice only the operator can make. It is not
hardcoded as unlinkable-or-not: it declares an empty ref-kind set per §8, so if it ever gains a
severable formulation it inherits the flag with no code change. The same holds for any future
clause.

**The default designation has its own verb, and not a flag on the status verb.** `is_default` is a
designation on the role item, not an edge; the projection reads it and, per §7's `no_default_role`,
omits the default-role line when no live role carries it. Moving a designation and retiring an entry
are two unrelated acts, so the designation gets a verb of its own — `sq role <addr> set-default` —
rather than a companion flag on `status`. A status flag doing both would be the kind of overloading
§8 keeps `--force` and `--unlink` apart to avoid, and it would make one command answer to two
questions.

**The verb is a move, not a set**, and that is the load-bearing part of this section: it designates
one live role and clears **every** other holder it finds, in a single transaction. The reason is
that the projection resolves the designation by first match over the roster, so two holders is not
an error the projection reports — it is an arbitrary winner it presents silently. Clearing every
holder rather than the one the caller knows about is also what converges a squad that already
carries two, in one call, with no separate repair path: refusing on a pre-existing two-holder state
would strand the squad in it, which is the mistake `no_default_role` made when it billed an
inherited condition to whoever moved next.

**Designating a non-live role is refused rather than stored.** A designation the projection cannot
present is not a designation, and the generated default-role line already omits itself when no live
role carries one, so storing it would record an intention nothing can act on.

**A two-holder state is reported, never gated.** `sq check` names it and points at the verb; no
clause refuses a transition over it. This follows §7's own boundary rather than an exception to it:
the clause family exists for a projection that would name something *not there*, and two live
holders names something that is there — real, live, and merely under-determined. That is a
state-validity question about the items' own data, which is the reporter's plane. Gating it would
also bill the wrong action: the condition is created by whatever wrote the second designation, while
a clause on the status axis would refuse the next reactivation instead — again `no_default_role`'s
error. Note that the remedy *would* have been performable, so this is not the unperformable-remedy
rule of §7 doing the work: designating either existing holder clears the other. Report rather than
gate is a proportionality call about a state with no dangling reference in it, not a forced move.

The importer's `update` event can also write the key, and it is history replay rather than a
designation verb — it neither converges a second holder nor refuses a non-live target, so it must
never be named as the remedy for anything.

*Withdrawn: this section's second half as an answer to "why does the default-role clause gain no
`--unlink` analogue".* That was the question it was written to answer, and the clause it asked about
no longer exists. Nothing in the reasoning depended on the clause — the argument that the
designation needs a *replacement chosen*, which did depend on it, went with it — so there are no two
positions left standing here, only a heading that had stopped naming its subject. The standing
question is where the designation lives and what shape its verb takes, which outlived the clause and
is what the text above answers.

### 10. Participation: what a retired entry stops being

A retired entry stops being **live** while its history stays intact. Those are two different
questions and must be answered differently, or the board rots:

- The interactive entry points that *write* a participant — `--as`, `--author`, `--assignee` on
  create/comment/update — accept only live slugs. This is what "stops being live as an
  active participant" means operationally.
- The `agent_registered` check keeps validating against the **full** roster vocabulary. An item
  authored by a role retired a year later must not start reporting a warning it cannot fix; the
  question that check asks is "was this a registered participant", not "is it live now".
- The bulk importer is exempt from the live-slug gate. It replays history, and history is full
  of participants who have since retired. It keeps the registration check only.

### 11. Retirement is not removal

`rm` hard-deletes the item, with the reflog as its audit trace (ADR-114). Retirement keeps the
item, its body, and its whole discussion, and withdraws only the projection. Both end up calling
`remove_artifacts`, which is why that method is correctly reused rather than duplicated — the
file-level effect is identical, and only the record's fate differs.

## Alternatives considered

**Lock the roster lifecycle instead: keep role/skill/operator on a fixed, non-overridable
lifecycle and hard-code the three states.** This is the strongest alternative and it was the
standing position. It is genuinely cheaper: every binding is trivially correct, no floor needs
enforcing, and the projection predicate can be a literal comparison. It loses because the
roster is the *most* projected surface, not the least — its entries become another tool's
config, so a squad whose vocabulary does not match ours is pushed into either abandoning its
vocabulary or hand-editing generated files. It also buys less safety than it appears to: a
locked lifecycle guarantees the three names exist, but it does not guarantee the projection is
coherent, so the clauses would still be owed. Locking removes the ability to customise without
removing the need to validate.

**Make the ABC status-aware** — either a `withdraw_artifacts` method or a
`materialise(ctx, item, active: bool)` that each backend branches on. Rejected: it pushes
lifecycle semantics into every backend, so a third backend must reimplement a rule that has one
correct answer, and it re-Claude-ifies the seam in spirit at the exact moment ADR-133 committed
to the opposite. The service already holds the spec; the backend never should have to.

**Leave the files in place and filter only the managed region**, by analogy with ADR-141 §5's
ignore-not-delete rule for deactivated backends. Tempting for symmetry, and the least
destructive option. Rejected because the analogy does not hold: a deactivated backend is a tool
squads has stopped driving, so leaving its files is respecting a boundary. A retired role is
squads' own entry inside a backend squads still drives — and the file it leaves behind is what
makes the agent spawnable, which is precisely the thing retirement is supposed to stop.

**Hard-delete the item on retirement.** Rejected outright: it destroys the entry's history and
makes every item it authored dangle. Retirement exists so that history survives.

**Refuse retirement only when the entry is flagged `required`.** Covered in §7 — it stores a
derivable fact and cannot express the last-live-role case.

**Keep the default-role clause as a refusal, and add the designation verb first.** The
conservative option: leave the refusal standing, build a verb that moves `is_default`, and the
remedy the message names becomes performable. Rejected on three counts. It defends the wrong thing —
"no live role carries the designation" is a valid state for one of the two shipped backends and a
perfectly coherent one for the other, so refusing it declares invalid something that is not.
It cannot hold the line it claims: `rm` and a catalog that designates nobody reach the fabricated
fallback with no status transition involved, so the clause covers one door of several while the
fallback stays. And it sequences a whole verb ahead of a release to keep a bundled role retirable,
where fixing the projection closes every door at once and removes the clause instead of feeding it.
The verb is still owed (§9) — it just stops being a prerequisite for retiring anything.

**Condition only `no_live_role` on an active backend, and leave the rest unconditional.** What was
in fact built, and what the clause-by-clause wording invited. Rejected: the clauses are defined over
the projection, so a clause that fires with no projection in existence is refusing to protect
anything. The concrete cost is that an sq-only squad — the shape ADR-141 blessed — could not retire
a scoped skill or its default role, which is precisely the un-blessing that rule forbids.
`always_on_floor` is the single exception and it is exempted by name rather than by omission (§8).

**Let `--force` override the clauses as well, instead of adding `--unlink`.** The simplest possible
escape, one flag instead of two, and the one an operator reaches for first. Rejected: forcing past
a config-integrity clause writes agent-host config from a state already known to be broken, and
the breakage then surfaces in another tool rather than in `sq`, where nothing will explain it.
`--unlink` costs more to implement and reaches less, but it leaves no path by which a squad can
generate config it knows is wrong.

**A `--dry-run` on the retirement.** Covered in §8: the unforced refusal already has to enumerate
and classify the dependants, so the dry run is the same command without the flag.

**A per-skill `required` flag or a hardcoded blocklist for the always-on trio.** The obvious way to
make the `always_on_floor` rule explicit. Rejected for the same reason §7 rejected a per-entry
`required` flag, and one more: the floor is already implied — the trio is in every role's preload
list, so the clause already refuses on the existing derivation. A flag or blocklist would be a
second, hand-maintained statement of a fact the preload list already makes, free to disagree with
it, and it would pin the floor to three literal names rather than to the property that defines it.

**Have `--unlink` also edit the spec** — drop the item type or the playbook mapping behind a
type-implied skill, so that every dependency the clause detects becomes severable. Rejected: that is
a squad-wide vocabulary change wearing the costume of a one-entry retirement, and it would let a
status verb silently remove an item type that live work depends on. The spec is the adopter's to
edit, deliberately.

## Consequences

- The roster lifecycle becomes load-bearing. Retiring an entry is a real operation with a real
  effect on the agent host: the agent stops being spawnable and the skill stops being loadable.
  A pre-active state becomes meaningful for the first time.
- The `AgentBackend` ABC does not grow, and no backend gains a status branch. A future backend
  gets withdrawal for free.
- **Retirement now deletes generated files.** It is reversible — reactivate and sync — but an
  adopter who had come to rely on a generated file being there will find it gone. The mitigation
  is the one already stamped in every generated file: it is regenerated by `sq sync` and must not
  be hand-edited.
- **Squads already on disk with retired entries converge on their next `sq sync`**, silently and
  with no migration. Their leftover pointers disappear at that point, not at upgrade time, and
  nothing fails in between.
- **Cost: the config-integrity refusal can block a legitimate-looking action.** "Retire this
  role" can fail because it is the last live one, or because a skill still points at it. Where a
  remedy exists the refusal names it and it can be performed, but the operator has to do two steps
  where they expected one; where none exists the refusal says so and the entry stays.
- **Cost: a retirement can take a squad's default-role guidance away, and only a warning says so.**
  The generated config's default-role line and the orchestration prose that names the same role both
  disappear when no live role carries the designation. Two recoveries exist and the warning names
  both: designate another live role with the §9 verb, or reactivate the previous holder. The cost
  that remains is not a missing capability, it is that the loss is quiet in the generated file
  itself — the adopter learns it from the transition, or from a diff.
- **Cost: two live roles can carry the designation, and the projection picks by roster order.** The
  state is reachable (a history import is enough) and its resolution is arbitrary rather than wrong.
  Withdrawing the default-role clause does not create this — the clause never checked it either.
  `sq check` reports it and the §9 verb converges it in one call; what nothing does is refuse a
  transition over it, deliberately, per §9.
- **Cost: deactivating every backend is now an escape hatch from the whole clause family,
  `always_on_floor` aside.** An adopter who empties `active_backends`, retires what a clause was
  refusing, and reactivates the backend has bypassed the guard — and per ADR-141 §5 the deactivated
  backend's files were never deleted, so its stale config still names the retired entry until the
  next `sq sync`. This is the price of scoping the clauses to the projection rather than to the
  record, it is the same ignore-not-delete asymmetry §4 already states plainly, and `sq sync`
  converges it. Closing it would mean gating on a projection that does not exist, which is the
  un-blessing ADR-141 forbids.
- **Cost: a bulk import whose intermediate state breaks config integrity is refused**, even when
  its final state is fine — for example a history that retires the only role in one event and
  adds a replacement in the next. The remedy is to order the import so the replacement lands
  first. This is the price of holding the importer to the same rule as the interactive path, and
  the alternative — an importer that can write a state the CLI refuses — is worse.
- **Cost: two roster projections now exist, and picking the wrong one is a silent bug.** An
  live-only list where the full list belongs makes a retired entry look like an orphan or its
  authorship look unregistered. §3's table is the contract, and it is the part of this decision
  most in need of tests that assert the *wrong* projection fails.
- **Cost: `--unlink` changes definitions the operator did not name.** One retirement can rewrite
  several roles' skill lists, bodies, and generated entries. The mitigations are that every
  severance is reported and reflogged, and that the refusal being escaped already enumerated
  exactly what would be severed — but an operator who types `--unlink` without reading that
  enumeration widens the blast radius without noticing. That is the honest price of the escape, and
  the reason the flag reports rather than proceeding quietly.
- **`--unlink` reaches less than its name suggests.** Adopter-authored custom skills and nothing
  else; every type-implied skill keeps a refusal whose remedy is a spec change or nothing at all.
  An adopter reading "there is an escape for this" will over-estimate it, which is why the refusal
  has to state the kind of dependency they are up against rather than describing the escape
  generically.
- **The always-on trio becomes un-retirable by contract, and an adopter has no way to opt out.**
  That is the intended rule, and it sits in real tension with the direction ADR-696 opens up: a
  project that shadows most of the spec still cannot decline `greeting`. The mitigation is that the
  floor governs *retirement*, not *content* — all three bodies render from bundled templates that
  are already on the override surface, so a project can rewrite what `greeting` says, just not
  remove it. That is a genuine answer for "we want different onboarding" and no answer at all for
  "we want none", and the second case is not served. It holds in a squad with no active backend
  too, which makes the floor the one thing an sq-only squad cannot decline — deliberate, and the
  one place the clause family reaches past the projection it is otherwise defined over.
- **Stating the floor as a contract creates a coupling nothing enforces.** It is true today only
  because `skills_for_role` prepends three module constants for every role. A later refinement that
  looks entirely reasonable — making the always-on set playbook-declared, or role-scoped so a leaf
  role skips `greeting` — would quietly move those skills from `always_on_floor` to `type_implied`
  and hand adopters a remedy the contract says they do not have. Writing the floor as "whatever
  every role preloads" rather than as three names is what keeps the rule and the derivation in step;
  a change to that derivation is a change to this contract and has to be recognised as one.
- **`type_implied`'s promise is not yet true for bundled types, and that is a live defect rather
  than a future refinement.** The playbook is an import-time singleton over the bundled spec, so a
  bundled `sq-<type>` skill's refusal does not track the active spec the way `type_implied` claims.
  Until the playbook resolves per-request against the active spec, those skills are
  `always_on_floor` in practice and the message has to be honest about it — which means the
  classification is a three-way split in contract and closer to a two-way one in behaviour.
- **A squad can already be in the state these clauses exist to prevent, and no clause will notice.**
  The roster status verb has shipped and nothing refuses retiring `squads` today, so a squad may
  already carry a retired system skill that every role still preloads. The clauses gate
  *transitions*, not existing state, so such a squad stays broken and the convergence sweep in §6
  will faithfully project the breakage: the skill's files withdrawn while every role's generated
  entry still preloads it. This is not the currency drift §6 declined — it is a state-validity
  question about an item's own status, which is what the report-mode validator plane is for. A
  `sq check` validator reporting a non-live system skill is owed, and is the only part of this
  decision that needs a reporter rather than a gate.
- Retiring roles changes generated *content* beyond the roster table — the default-role line, which
  can now vanish entirely, and the developer-gated per-item-type skill text — so a retirement
  produces a larger managed-file diff than an adopter might expect.
- The forward door: a currency check that reports a projection mismatch without waiting for
  `sq sync`, and a `sq backend remove` that cleans up a deactivated backend's files, both fit on
  top of this without revisiting anything decided here.

## Amendment note

**2026-07-30 — the materialisation predicate moves onto a flag.** As first written, this decision
read materialisation off the status *role name*: an entry was materialised if and only if its
status resolved to the role called `active`. That is the name-locking ADR-696 §1 forbids, one layer
up from the status names it retired, and it would have made a project's roster projection depend on
a role name it may reasonably want to call something else.

The axis is now ADR-696 §2a's `live` boolean, a fourth field on the status-role object beside
`settled`, `hidden`, and `color`. Non-settled was checked as a cheaper substitute and does not
work: four bundled roles are non-settled, so a project's `Suspended` (on a `blocked` role) or
`Provisional` (on `pending`) would be read as live and written into the agent host's config —
backwards in the one direction that matters.

What changed here: §1's predicate, §6's convergence rule, §3's `roster()`/`operators()` split
(live-only) and its per-caller table, §7's C1 clause, and §9's C1 rationale all restate in terms
of the flag rather than the role name. Nothing else moves — the two-part withdrawal through
`remove_artifacts` plus a recompiled managed region, the status-blind ABC, the fan-out and orphan
rules, the C2/C3 clauses, `--unlink` and its tiers, and the participation gate are unchanged, and
they were already written against a predicate rather than against a name.

One consequence of ADR-696's matching relaxation is worth reading alongside §1: because R1 now
requires only *at least one* live status, a lifecycle may declare several, so "this entry is
live" no longer implies a single status. Nothing in the projection cares — it reads the
predicate — but anything reporting on the roster should show the status rather than a yes/no.

**2026-07-30 — the flag is renamed `offered` → `live`, following ADR-696.** ADR-696 renamed the
underlying status-role flag this decision projects (§1's predicate, §3's `roster()`/`operators()`
split, §6's convergence rule, §7's C1 clause, §9's C1 rationale, §10's participation gate) —
`offered` read as roster-projection vocabulary specifically, when the flag it names sits on the
status-role object every item type's statuses resolve through. This ADR carries no independent
rationale for the name; it restates ADR-696's throughout, replacing `offered`/`unoffered` with
`live`/`non-live` and `roster()`/`operators()`'s `offered-only` split with `live-only`. No
semantics move: the projection predicate (§1), the two-part withdrawal, the fan-out and orphan
rules, C1–C3, `--unlink` and its tiers, and the participation gate are exactly as decided above,
under the new name.

**2026-07-31 — the default-role clause is withdrawn, and the clause family is conditioned on an
active backend.** Two review findings turned out to be about this decision rather than about its
implementation, and both are amended above.

The default-designation clause is **withdrawn rather than patched**. It refused retiring the role
carrying `is_default`, and the remedy it named was a designation verb that did not exist — so the
bundled `manager` role was un-retirable, under `--force` and `--unlink` alike. One factual
correction to the finding that prompted it: the key is *not* unwritable. `is_default` is declared
settable for the role type and the bulk importer's update event reaches it, verified end to end by
setting it on a role and then retiring the previous holder successfully. That path is history replay
through an ungated seam, so it must never be named as a remedy, and §7 says so.

The deeper reason it goes rather than gains a verb: the state it refused is legitimate — one of the
two shipped backends has no default-role concept at all — while the structural defect sits
elsewhere, in the Claude backend fabricating a hardcoded `manager` slug when it finds no designated
role. That door is already open with no status transition in play: hard-deleting the manager role
reaches the same state, leaves `sq check` clean, and leaves the managed region naming a slug that is
not in the roster. A clause on the status axis guarded one door of several. What replaces it is the
projection **omitting what it does not have** — no default-role line, and no default-role name in
the orchestration prose that reads the same value — plus a warning on the transition that takes the
last live designation out of a live status, which is the degradation the developer-gated skill text
already performs.

**The backend condition belongs to the whole clause family, not to one clause**, and is therefore
stated once in §7 rather than repeated per clause. Per clause: `no_live_role` is a derived
cardinality property of the projection, so it is conditioned; the withdrawn clause's successor
warning is about generated config, so it is conditioned too; `preloaded_skill`'s `scoped_edge` and
`type_implied` kinds are conditioned, because although the dependency is playbook- or spec-authored,
what it breaks is a generated entry, and with no backend there is no entry. `always_on_floor` is
**not** conditioned, and is exempted **by name** rather than by omission: its authority is a declared
rule of the roster contract, not a derived property of the projection. The tempting split — that the
floor is squads' own concern because the playbook authors it — proves too much, since the
`sq-<type>` implication behind `type_implied` is playbook-authored as well; what separates them is
the source of the authority, not who wrote the dependency.

Both amendments are consistent with a delta-scoped gate throughout: §7's headline asks whether *this
transition* breaks something that was not already broken, and §8's unlink re-evaluation is spelled
as a delta against the pre-transition snapshot. Nothing added here assumes whole-squad evaluation.
Three costs are recorded rather than hidden: an adopter can lose the default-role line, with
reactivation as the recovery; two live roles can carry the designation, with the projection picking
by roster order; and emptying `active_backends` is an escape hatch from the conditioned clauses,
stated rather than closed, because closing it means gating on a projection that does not exist.

**2026-07-31 — positional clause labels are out; every clause is named for its condition.** The
C1/C2/C3 labels and the tier 1/2/3 numbering are replaced by identifiers describing what each clause
checks — `no_live_role` and `preloaded_skill`, with `scoped_edge`, `type_implied` and
`always_on_floor` for the second's three kinds of dependency. The withdrawn default-designation
clause is recorded as `no_default_role` under its own heading, because a descriptive identifier
leaves no hole behind when a clause goes, which is the whole point of the convention.

This reverses a position §7 previously argued rather than merely swapping vocabulary, so the old
rationale is withdrawn in place rather than deleted. Label stability had been defended on the
grounds that a label appears in every refusal an operator has already read — and that premise is
exactly the leak. Both reasons for dropping it were verified rather than taken from the finding: the
gate printed the label alongside the condition, while forcing a squad into the same state on disk
and running `sq check` printed the identical condition with no label, so the identifier was an ADR
cross-reference in an adopter's terminal, and an inconsistent one. And the numbering had already
rotted — withdrawing the default-designation clause left the set reading as a first and a third.

`preloaded_skill` was chosen over a `dependent_skill` shape because what the clause reads is a live
role's resolved **preload** list, and that one description covers all three kinds of dependency;
"dependent" also reads ambiguously about which end depends on which.

Two things the numbering had been carrying silently are now stated outright. Findings' render order
was inherited from the labels, so §7 declares an ordering explicitly wherever more than one finding
renders together. And the tier numbers encoded a remedy gradient — severable, then a spec change,
then none — which the statement that a bundled `sq-<type>` behaves as `always_on_floor` depends on,
so §8 declares that ordering as an ordering of **remedies**: not a severity, not an evaluation
order, and not a licence to report only the worst kind a skill is caught by.


**2026-07-31 — the designation verb shipped; §9 describes it rather than owing it.** Recorded from a
review finding. §9 said the designation had no owning verb and that building one was work owed
elsewhere; `sq role <addr> set-default` exists, and I verified on a throwaway squad that it meets
every constraint the section set — it designates a live role and clears every other holder it finds
in one call (converging a squad already carrying two), it refuses a non-live target, and designating
the current holder is a reported no-op. The projection refreshes with it, so the default-role line
and the orchestration prose follow the move.

The reasoning is kept and is now vindicated rather than hypothetical: **a move, not a set**, because
the projection resolves the designation by first match over the roster, so a plain set would leave
an arbitrary winner and no way to converge one already stored. What changed is tense and one expired
premise — "nothing validates a single holder" was true when written and is not now, because `sq
check` reports a two-holder state.

That report is ruled on rather than inherited: a two-holder state is **reported, never gated**. It
follows §7's own boundary — the clause family is for a projection that would name something not
there, and two live holders names something real and merely under-determined, which is the
reporter's plane — and gating it would bill an inherited condition to whoever transitioned next,
which is the error `no_default_role` was withdrawn for. It is *not* an instance of §7's
unperformable-remedy rule: I checked, and the remedy would have been performable, since designating
either existing holder clears the other. Report rather than gate is a proportionality call about a
state with no dangling reference in it.

The consequences lines move with it: a lost default-role line now has two named recoveries rather
than one, and the two-holder cost is stated as reported-and-convergeable rather than unguarded.
Also withdrawn in place: §9's second half as an answer to "why does the default-role clause gain no
`--unlink` analogue". Nothing in it leaned on that clause — the "needs a replacement chosen"
argument that did was removed when the clause was — so this retires a heading that had stopped
naming its subject, not a position.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T15:27:49Z] Pierre Chat:
  - Clarification on 'non-disablable': I meant the item types themselves, not individual roster entries. The three roster types must not be droppable or reclassifiable — that requirement is satisfied by ADR-696's reserved type keys plus the fixed roster category, not by this ADR's transition-time refusals.
- [2026-07-29T15:27:50Z] Catherine Manager:
  - For the record: the C1-C3 entity-level retirement refusals in this ADR came from my brief, not from the operator's requirement. They stand or fall on their own merit as a config-integrity guarantee.
- [2026-07-29T15:55:24Z] Pierre Chat:
  - C3 stays as a refusal, but with an escape: a --unlink flag that retires the entry AND removes it from the entities referencing it, rather than forcing past the check. Keep this generic — express it over declared reference relationships, not a skill-in-roles special case; the engine must not grow a per-type branch.
- [2026-07-29T16:01:49Z] Robert Architect:
  - Amended the body for op-pierre's C3 escape. New §8 (--unlink) and §9 (C1/C2 gain no analogue); Participation and Retirement-is-not-removal renumbered to §10/§11.
  - Generalisation landed on: a declared reference relationship is a stored forward ref edge (kind-tagged, single-owner, backrefs-inverted, never persisted). Each config-integrity clause declares the ref kinds whose edges constitute the dependency it detects — non-empty means severable, empty means the refusal stands. --unlink consumes that declaration, so it grows no per-type branch and a future clause inherits it.
  - Which of C3's dependants are unlinkable: the scopes edge, yes (stored on the retiring skill itself; sq skill <addr> unlink-role is already the sanctioned sever path). System membership and type-implied sq-<type> skills, no — skills_for_role() is computed from the playbook and the declared type set, so there is no edge, and the thing that would have to change is the spec. Refusal survives for that case with a spec-change remedy. Net: --unlink reaches adopter-authored custom skills and nothing else.
  - --force vs --unlink kept explicitly apart in the body: --force overrides a policy gate and leaves the state as asked; --unlink overrides nothing and makes the structure valid first, after which the unforced check passes on its own. Recorded that no flag bypasses C1-C3 and none may be added.
  - Two things in the framing that do not generalise as stated, flagged rather than silently fixed: (1) the direction is inverted for the only case that exists today — the retiring skill is the referrer, so --unlink clears its own refs, and no other item's authored declarations change (their derived extra.skills cache, body Skills region and generated entry do). (2) unlink_role is itself skill-to-role shaped, so the flag must call a kind-aware generic ref removal (rm_ref needs widening with an optional kind) or it inherits the special case it exists to avoid.
  - Also corrected two body facts while in there: §7 no longer attributes the C1-C3 clauses to the operator's requirement, and it now points the type-level non-disablability at ADR-696's reserved keys plus fixed roster category. No dry-run flag — the unforced refusal must enumerate and classify the dependants, so running without --unlink is the dry run.
  - @manager still Proposed; sq check clean, the amendment is uncommitted.
- [2026-07-29T16:08:53Z] Catherine Manager:
  - Heads-up for whoever implements the projection refresh here: the operator has scheduled the stored extra.skills cache and the role body's ## Skills region for conversion to derived views (recorded on FEAT-693). The refresh footprint enumerated in this ADR assumes both exist — once they become computed projections, severing a scopes edge touches the skill's own frontmatter plus the regenerated backend entries only, and the cache-write steps drop out.
- [2026-07-29T16:14:29Z] Pierre Chat:
  - The three always-on skills (squads, greeting, sq-memory) are a permanent floor by design: every role preloads them and they can never be retired. State that as a deliberate rule, and have the refusal say so plainly rather than offering a remedy that does not exist. No new prohibition mechanism — the playbook already implies them; this is naming the consequence, not adding a flag.
- [2026-07-29T16:18:32Z] Robert Architect:
  - Amended §8 for op-pierre's tier ruling. C3's dependants now classify in three tiers with a remedy stated per tier, including 'none' where that is the truth: (1) stored scopes edge — severable via --unlink; (2) type-implied sq-<type> — no edge, but the implication tracks the declared type set, so the refusal is temporary; (3) the always-on trio — a permanent floor of the roster contract, no remedy offered.
  - Verified the defect: skills_for_role (_interactions/__init__.py:268-275) prepends SQUADS_SKILL/GREETING_SKILL/MEMORY_SKILL unconditionally for every role — module constants, not playbook-mapped per role and not spec-declared. 'Adjust the playbook scope' was impossible for those three. Message fixed.
  - Wrote the floor as a property, not a name list: whatever skills_for_role implies for EVERY role is un-retirable. Survives a rename and a change in set size without a blocklist. No new mechanism — the playbook already implies them and C3 already refuses; a per-skill required flag was added to alternatives as rejected.
  - Found a second defect in the same remedy text while verifying, and recorded it rather than papering over it: tier 2 does not hold for BUNDLED types today. item_types_for_role reads the PLAYBOOK singleton, built once at import from the bundled spec with no squad_dir and no per-request rebuild, so dropping 'task' from a project's workflow override does not un-imply sq-task. Tier 2's remedy works for project-declared custom types only; until the playbook resolves against the active spec (the same per-request-context direction the workflow spec already took), a bundled sq-<type> behaves as tier 3 and the refusal must say so.
  - Ruled yes on naming the implicated types — it follows from 'the refusal message is the dry run', which a message saying merely 'a type implies this' would not be. Two constraints written in: it states the mechanism, never a recommendation (dropping a live work type to retire one skill is usually the wrong move), and the enumeration is capped with a summarised tail.
  - Also flagged in consequences: a squad can ALREADY be in the state these clauses prevent — the status verb has shipped and nothing refuses retiring 'squads' today. Clauses gate transitions, not existing state, so such a squad stays broken and the sync sweep faithfully projects it. That is a state-validity question, not the currency drift §6 declined, so a sq check validator for a non-live system skill is owed.
  - @manager still Proposed; sq check clean, uncommitted.
- [2026-07-29T16:30:40Z] Pierre Chat:
  - The playbook/spec asymmetry that makes tier 2's remedy untruthful for bundled types gets its own ADR, not a fix ticket. It has to reconcile three accepted decisions: ADR-534's permitted-cache boundary (a spec-resolved playbook stops being a bundled immutable and can no longer live in a module constant), ADR-696's minimum-semantics floor, and this ADR's tier 2. And it must answer whether the playbook and custom_skill_slugs should remain two mechanisms for one concept.
- [2026-07-29T16:40:01Z] Pierre Chat:
  - Broaden the commissioned playbook decision: the same delta-based override loading must sit on top of every bundled spec file, not just the playbook. Current state is uneven — workflow.toml has a single-file delta, roles.toml has per-role delta files merged by slug, playbook.toml has no override path at all. Decide one uniform model (including whether granularity stays per-file or per-entity) rather than adding a third shape.
- [2026-07-29T16:42:49Z] Catherine Manager:
  - Findings for the commissioned override/playbook decision, recorded at the operator's request. (1) A custom role today resolves only the three always-on skills — the playbook's role guides name exactly seven slugs (architect, product-owner, qa, reviewer, tech-lead, tech-writer, and the *dev sentinel), so any role outside that set gets no sq-<type> skills. The decision's real question is therefore not only whether an adopter can edit the playbook, but whether a custom role can ENTER it — declaring that, say, a security-auditor interacts with bug and review and getting the generated per-type guidance automatically, instead of hand-authoring a scoped skill.
  - (2) The *dev sentinel is a load-bearing naming convention with nothing declaring it: is_dev_slug is slug.endswith('-dev'), so a custom rust-dev inherits the entire developer playbook across every type while a rustacean or security-auditor inherits none. Either make that contract explicit or replace it with a declared capability.
  - (3) It lowers the stakes on this ADR's tier 2. Two bundled roles — manager and devops — have no playbook presence at all and resolve the trio plus a scoped skill (releasing-squads, reaching them through a scopes edge). So a role with no per-type skills is the normal condition for part of the bundled roster, not a broken state, and an sq-<type> skill going un-implied is correspondingly less severe than tier 2's wording implies.
- [2026-07-30T10:01:23Z] Robert Architect:
  - [amendment — 2026-07-30] Materialisation no longer keys off a role name. §1's predicate is now ADR-696 §2a's offered flag; §6's convergence rule, §3's roster()/operators() split and per-caller table, §7's C1 and §9's C1 rationale all restate on the flag. Amendment note added to the body.
  - Non-settled was checked as the cheaper substitute and does not work: four bundled roles are non-settled (active, attention, blocked, pending), so a project's Suspended on blocked or Provisional on pending would read as offered and be written into the agent host's config — backwards in the one direction that matters.
  - Nothing else moved. The two-part withdrawal, the status-blind ABC, fan-out, orphans, C2/C3, --unlink and its tiers, and the participation gate were already written against a predicate rather than a name, so they restate without design change.
  - One knock-on from ADR-696's matching relaxation, noted in §1 and the amendment note: R1 now requires only at least one offered status, so a lifecycle may declare several and 'this entry is offered' no longer implies a single status. The projection does not care — it reads the predicate — but anything reporting on the roster should show the status, not a yes/no.
  - @manager still Accepted; sq check clean, uncommitted.
- [2026-07-30T15:44:27Z] Elias Python:
  - Renamed offered -> live throughout, following ADR-696; added a dated amendment note in the body, status left Accepted.
- [2026-07-31T09:24:06Z] Robert Architect:
  - [amendment — 2026-07-31] Two review findings were mine, not the implementer's, and both are amended in the body. Status unchanged (Accepted); dated amendment note added.
  - F2 — C2 withdrawn as a clause, not patched. I verified the missing verb myself: X.IS_DEFAULT is written only by _roles/_catalog.py::RoleDef.to_extra at activate; sq role and sq role <addr> register no designation verb and no update; and on a throwaway squad the refusal fires under --force and --unlink alike, so the bundled manager role was un-retirable. One correction to the finding: the key is NOT unwritable — _models/_metadata.py::_ROLE_FIELDS declares is_default settable for the role type, and the bulk importer's update event reaches it (verified end to end: an update event set it on ROLE-2, after which retiring manager succeeded). That path is history replay through the ungated seam, so it is not a remedy and the ADR now says it must never be named as one.
  - The deeper reason C2 goes rather than gains a verb: the state it refused is legitimate (the AGENTS.md backend has no default-role concept at all), and the real structural defect is the Claude backend fabricating a hardcoded 'manager' slug when it finds no designated role. Verified that door is already open without any status transition — 'sq role manager rm --purge' on a fresh squad exits 0, sq check is clean, and CLAUDE.md then reads 'default to **the manager** (manager)' with no manager in the roster. C2 guarded one door of several. §7's C2 is now: the projection omits the default-role line (and the orchestration prose that reads the same value) when no live role carries the designation, with a warning on the transition that removes the last one — the same degradation has_dev already performs. §9 states what the designation verb must be when built: a move, not a set.
  - F5 — the backend condition belongs to the whole clause family, stated once in §7, with C3 tier 3 exempted by name. Per clause: C1 derived cardinality of the projection, conditioned (unchanged). C2 gone; its successor warning is about generated config, so conditioned. C3 tiers 1 and 2 conditioned — the dependency is playbook/spec-authored but what it breaks is a generated entry, and with no backend there is no entry. Tier 3 NOT conditioned: its authority is a declared rule of the roster contract, not a derived property of the projection. The tempting split — 'tier 3 is squads' own concern because the playbook authors it' — proves too much, since tier 2's implication is playbook-authored too; what separates them is the source of the authority.
  - Consistent with a delta-scoped gate throughout: §7's headline now says a clause answers whether THIS transition breaks something not already broken, and §8's unlink re-evaluation is spelled as a delta against the pre-transition snapshot. Nothing added assumes whole-squad evaluation. Honest costs recorded: an adopter can lose the default-role line with only reactivation as recovery; two live roles can carry the designation with the projection picking by roster order; and emptying active_backends is now an escape hatch from the conditioned clauses, stated rather than closed because closing it means gating on a projection that does not exist.
  - @reviewer @python-dev the fix set changes shape: C2's fix is not a message edit but removing check_c2 from the clause set and the reporter, fixing the Claude backend's default fallback plus the two template sites that name the default role, and adding the lost-designation warning. The designation verb is separate work, no longer a prerequisite for any retirement. sq check clean; uncommitted.
- [2026-07-31T09:40:03Z] Olivia Lead:
  - @architect the fix cut adds one item to your side: the C1/C2/C3 labels and the tier 1/2/3 numbering are being renamed to describe the condition, and dropped from user-facing text entirely (the gate prints the label, the reporter does not, and no adopter document defines C3). §7 currently argues the opposite — 'the labels are stable and C3 is never renumbered into the gap, because a clause label appears in every refusal an operator has already read' — so this reverses a stated position rather than swapping vocabulary. Recorded on TASK-707's rename subtask that the amendment is yours to make, not the implementer's.
- [2026-07-31T09:48:15Z] Robert Architect:
  - [amendment — 2026-07-31] Positional clause labels are out, per op-pierre's ruling. Clauses are now `no_live_role` and `preloaded_skill`; the latter's three kinds of dependency are `scoped_edge`, `type_implied`, `always_on_floor`. The withdrawn default-designation clause is recorded as `no_default_role` under its own heading — a descriptive identifier leaves no hole behind when a clause goes, which is the whole point. Status unchanged (Accepted); dated amendment note added.
  - Verified both reasons myself on a throwaway squad rather than taking them from the finding. The gate prints '- C3 (SKILL-9): not live (status Archived) but every role preloads it unconditionally — a permanent floor …'; forcing the same squad into that state on disk and running sq check prints the identical condition with no label. So the label was an ADR cross-reference in an adopter's terminal, and inconsistently at that. The numbering had also already rotted: withdrawing the default-designation clause left the set reading as a first and a third.
  - Chose `preloaded_skill` over the suggested `dependent_skill` shape: what the clause reads is a live role's resolved PRELOAD list, and that one description covers all three kinds (scopes edge, type implication, always-on membership) — 'dependent' also reads ambiguously about which end depends on which. Easy to overrule; the ADR states the naming rule, which is what binds the implementer.
  - Ruled the identifiers internal: code, the per-clause ref-kind declaration, tests, this ADR — never user-facing text. A refusal and a report each read as the condition plus its remedy, and both render the SAME condition text, because they are two renderings of one predicate. That resolves the review's improvement note I3 in the opposite direction from its suggestion: if the shared text reads awkwardly in the gate, the shared text is what gets fixed, never forked per caller.
  - The old rationale is withdrawn in place, not contradicted: §7 carries a marked withdrawal saying label stability was argued on the grounds that a label appears in every refusal an operator has read — and that premise is exactly the leak. The labels were adequate as identifiers and unfit as vocabulary; carrying both jobs on one token is what made their stability look load-bearing.
  - Two things the numbering had been carrying silently, now stated: (1) findings' render order was inherited from the labels, so §7 declares an ordering is owed explicitly wherever several findings render together, for deterministic output; (2) the tier numbers encoded a remedy gradient (severable → spec change → none) that the 'a bundled sq-<type> behaves as tier 3' statement depends on, so §8 declares that ordering as an ordering of REMEDIES — not a severity, not an evaluation order, and not a licence to report only the worst kind a skill is caught by. That last clause is deliberately consistent with the review's F12.
  - @reviewer @python-dev the rename is a rendering-and-identifier change on top of the fix set, not a new behaviour: drop the label from the gate's refusal lines so gate and reporter agree, and carry the clause/kind identity as named values internally. sq check clean; uncommitted.
- [2026-07-31T12:26:16Z] Robert Architect:
  - [amendment — 2026-07-31] §9 now describes the shipped designation verb instead of owing one, per F18 on the batch review. Status unchanged (Accepted); dated amendment note added.
  - Verified `sq role <addr> set-default` myself on throwaway squads, not from the finding: it designates a live role and clears EVERY other holder in one call (converged a two-holder state by clearing both ROLE-5 and ROLE-6), refuses a non-live target, reports designating the current holder as a no-op, and refreshes the projection — CLAUDE.md's default-role line followed the move, and vanished (along with the orchestration prose naming a role) once no live role carried it. Also confirmed the retirement warning names set-default first and reactivation second, which is what made the old 'until that verb exists … only reactivation' consequence untrue.
  - Kept the move-not-a-set reasoning intact and marked it as the load-bearing part: the projection resolves the designation by first match over the roster, so a plain set leaves an arbitrary winner and no way to converge one already stored. Clearing every holder is also what converges a pre-existing two-holder state without a separate repair path — refusing on it would strand the squad, which is exactly the mistake the withdrawn default-role clause made.
  - One correction to the reason offered for reporting rather than gating the two-holder state. I checked, and gating it WOULD have had a performable remedy: designating either existing holder clears the other (verified — reactivated a stale holder alongside a live one, then ran set-default on one of the two, which cleared the other and left sq check clean). So this is not §7's unperformable-remedy rule doing the work. The reasons that do hold are written in: two live holders names something real and merely under-determined rather than something absent, so it sits on the reporter's side of §7's own boundary; and a gate on the status axis would bill an inherited condition to whoever transitioned next — the withdrawn clause's error again. Report over gate is a proportionality call, which is worth stating as one.
  - On whether §9 still leaned on the withdrawn clause: no argument did. The 'needs a replacement chosen' reasoning that genuinely depended on it was already removed with the clause. What remained was a heading and framing that answered 'why does the default-role clause gain no --unlink analogue' — a question about something that no longer exists — plus one expired factual premise ('nothing validates a single holder', now false since sq check reports it). Both are withdrawn in place rather than quietly retitled, and the standing question the section really answers (where the designation lives, what shape its verb takes) is named as such.
  - No divergence found between the shipped verb and what §9 specified. @reviewer F18 is addressed in the ADR; nothing here changes a decision.
- [2026-08-03T08:25:28Z] Robert Architect:
  - Repaired two physical corruptions in the body. No decision content changed and no clause moved; this restores prose that a shell-substituted backtick in an `sq body -m` argument had deleted (the same failure I recorded in my own role memory, and the reason this edit went through `--file`).
  - Restored the truncated 2026-07-31 amendment note from the discussion record at 2026-07-31T09:24:06Z. It had been cut mid-sentence at "conditioned on an" with its whole content gone. The note now records what that amendment ruled: the default-designation clause withdrawn rather than patched (with the correction that `is_default` is settable, so the importer path exists but is not a remedy), the projection omitting the default-role line plus a warning on the last live designation leaving, and the backend condition stated once for the whole clause family with `always_on_floor` exempted by name.
  - A second amendment note was missing entirely, not merely truncated: the 2026-07-31T09:48:15Z ruling that positional clause labels are out. The identifiers themselves were already applied throughout the body, so the record of why was the only casualty. Restored, including the withdrawn label-stability rationale, the `preloaded_skill` over `dependent_skill` choice, and the two things the numbering had carried silently (declared render order, and the tier ordering being an ordering of remedies).
  - Rebuilt section 3 per-caller projection table, which had exploded into roughly 45 one-word rows. Prose reconstruction only: I verified each row against the tree before restoring it rather than trusting the fragments. `roster()`/`operators()` are live-only and `roster_all()`/`operators_all()` exist at `_services/_base.py:962-1008`; `_role_skills_map` takes the live projection and `candidate_orphans` takes the full one at `:1114` and `:1146`; the default-slug resolver takes live for authoring and all for display at `_cli/_common.py:1064,1072`.
  - Verified after writing by reading the stored text back off disk: the table renders as six rows, all five amendment notes have intact headings, and no stray wrapper tag leaked in. Nothing staged or committed.
<!-- sq:discussion:end -->
