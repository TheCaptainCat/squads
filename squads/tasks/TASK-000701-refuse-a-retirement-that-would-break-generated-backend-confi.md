---
id: TASK-701
sequence_id: 701
type: task
title: Refuse a retirement that would break generated backend config
status: Done
parent: FEAT-691
author: tech-lead
priority: high
refs:
- BUG-698:fixes
- ADR-697:implements
- TASK-700:depends-on
description: The C1-C3 transition-time clauses, force never overriding them, and --unlink
  severing tier-1 edges
subentities:
- local_id: ST1
  title: Evaluate the clauses in the pure half of the status transition
  status: Done
  story: US5
- local_id: ST2
  title: Widen rm_ref with an optional kind and demote unlink_role to a wrapper
  status: Done
  story: US5
- local_id: ST3
  title: 'Add --unlink to the roster status verb: sever, re-evaluate, report'
  status: Done
  story: US5
- local_id: ST4
  title: Word each refusal to its tier with a satisfiable remedy
  status: Done
  story: US5
- local_id: ST5
  title: Cover the refusals, the escape and the importer replay
  status: Done
  story: US5
created_at: '2026-07-30T07:47:23Z'
updated_at: '2026-07-31T12:41:24Z'
---
<!-- sq:body -->
## Context

BUG-698's gate half, per ADR-697 §7-§9. A roster status transition is refused when the resulting
projection would be structurally invalid for at least one active backend. The clause predicates
themselves are built by the reporter task; this task evaluates them at transition time and adds
the one mechanised way to *satisfy* C3.

The evaluation runs in the pure, pre-write half of the transition (`_set_status_model` in
`_services/_items.py`), against the transaction's own snapshot and before any write. That is
also the seam the bulk importer's pre-pass calls, so an import replaying history is held to the
same rule at each step it replays — including the stated cost that an import whose intermediate
state breaks config integrity is refused even when its final state is fine.

## Scope

Evaluate C1, C2 and C3 at transition time and refuse with a `SquadsError` naming the specific
remedy for the clause and, for C3, the tier.

`--force` overrides the lifecycle's own transition edge and nothing else. It never overrides
C1-C3, it composes with `--unlink` without either weakening the other's gate, and no further
flag may be added that bypasses these clauses.

`--unlink` on the roster `status` verb, registered once on the shared implementation the three
addressed subgroups already have (`register_status_verb` in `_cli/_common.py`) and offered only
for a `roster`-category type:

- severs the stored forward ref edges that constitute a **tier-1** C3 dependency — a custom
  skill's `scopes` edge to a role — then re-evaluates **every** clause, unforced, against that
  prospective state. A transition still refused aborts the whole transaction, so severing and
  then refusing in one command is impossible and a refusal can never leave a partially severed
  squad.
- reports each severance (the referring entity, the entity it stopped referencing, the kind) and
  reflogs one `ref` removal entry per severed edge plus the `status` entry.
- on a retirement with nothing severable: reports a no-op and proceeds.
- on a transition that is not a retirement: refused as meaningless.
- never touches a tier-2 or tier-3 dependency; those keep refusing regardless of the flag.

Each clause declares the set of ref kinds whose stored edges constitute the dependency it
detects — empty for a clause whose dependency is not a reference. A clause with a non-empty set
is severable; C1 and C2 simply declare the empty set rather than being hardcoded as
unlinkable-or-not, so either inherits the flag with no code change if it ever gains a severable
formulation. Behaviour in code, per-clause declaration in data.

Engine hygiene, called out in ADR-697 §8 and non-negotiable: `rm_ref` in `_services/_refs.py`
today drops every edge to a target regardless of kind. Widen it with an optional kind and demote
`unlink_role` — which guards its target's type and hardcodes the `scopes` kind — to a thin
wrapper over the widened primitive plus the existing projection refresh. The flag must call the
kind-aware generic removal, never `unlink_role`, or it inherits the very special case it exists
to avoid.

Order of mutation, under the durability rules already in force: sever in the in-memory snapshot
and re-evaluate before any write; then markdown first — the retiring entry's frontmatter and
every other referring item whose `refs` changed — before the index commit; then the reflog; then,
after commit, the projection work (which lands with the projection task).

## Refusal wording

Every refusal is satisfiable and names the specific remedy for its clause. C3 enumerates its
dependants and classifies each by tier, because the refusal *is* the dry run — no `--dry-run`
flag is added.

- **Tier 1** names the roles whose edges would be severed. Remedy: the flag, or the explicit
  unlink verb first.
- **Tier 2** names the specific implicating type or types, capped and summarised for a widely
  implicated skill. It states the mechanism, never a recommendation: "this skill is implied by
  declared type X" is a fact; "drop X to retire this skill" is advice, and usually terrible
  advice. Retiring one skill must never nudge toward dropping a live work type.
- **Tier 3** states the floor in one line and offers no remedy, because none exists: whatever
  `skills_for_role` implies for every role is un-retirable. State it as that property, not as a
  list of names.
- **The bundled tier-2 caveat is behavioural, not aspirational.** `item_types_for_role` reads the
  `PLAYBOOK` singleton, built once at import from the bundled spec with no squad-directory
  parameter and no per-request rebuild. Dropping a type from a project's override therefore does
  not un-imply its bundled `sq-<type>` skill. A bundled type-implied skill behaves as tier 3
  today and its message must say so, rather than naming a remedy that will not take effect.
  Spec the message to what the code does. Do not fix the playbook here.

## Out of scope

The `sq check` reporter and the clause predicates themselves. The projection write and
withdrawal. Making the playbook resolve per-request against the active spec. A `--dry-run`
shape. A `--default <slug>` companion for C2.

## Acceptance

- C1: retiring the only live role is refused while at least one backend is active, and allowed
  when `active_backends` is empty.
- C2: retiring the `is_default` role is refused unless another live role carries it.
- C3: retiring a skill still named by a live role's resolved preload list is refused, for each of
  the three dependency kinds.
- `--force` does not override any of the three, alone or combined with `--unlink`.
- `--unlink` severs only tier-1 edges, re-evaluates unforced, and proceeds only when the
  structure genuinely satisfies every clause; a still-refused transition leaves the squad
  byte-identical to before the command, refs included.
- `--unlink` reports every severance and reflogs one entry per severed edge plus the status
  change; the no-op and the not-a-retirement readings behave as specified.
- `--unlink` is offered only on a `roster`-category type's `status` verb.
- `rm_ref` removes only the named kind when one is given and keeps its current
  kind-agnostic behaviour when none is; `unlink_role`'s observable behaviour is unchanged.
- Retiring the last operator is never refused. A retiring role holding open assigned work warns
  and proceeds.
- The importer's pre-pass is held to the same rule, refusing a history whose intermediate state
  breaks a clause.
- `sq check` clean and `sq repair` a no-op after a successful `--unlink` retirement.
- Gate clean with `--all-extras` on each of pyright, `ruff check .` and `ruff format --check .`.
- Full suite green. A new module-level constant means running `tests/meta` and allowlisting it as
  a CODE constant rather than restructuring the code.
- Falsify each refusal and the abort-on-still-refused path: break it, watch the test go red,
  restore it, watch it go green, report both.

## Tests

Service level plus a CLI smoke per surface, named by behaviour. No ticket ID in any file name,
test name, or source comment.

- Service — a new `tests/service/` module for the refusals: one case per clause, the
  `--force`-does-not-override cases, the last-operator and open-work cases, and the
  sever-then-still-refused abort asserting nothing changed on disk.
- Service — `tests/service/test_status_vocabulary_enforcement.py` already owns roster
  transition/vocabulary behaviour; add only what belongs with it, not a duplicate of the above.
- Unit — `rm_ref`'s kind filter and `unlink_role`'s unchanged behaviour, alongside the existing
  ref tests.
- CLI — `tests/cli/test_roster_type_address_verbs.py` for the flag's presence, help text, the
  no-op and not-a-retirement readings; `tests/cli/test_skill_role_scoping_verbs.py` for the
  severance reporting next to the existing scoping verbs.
- Integration — the importer replay refusal, alongside the existing import coverage.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 701 add-subtask "<title>"`; track with `sq task 701 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Evaluate the clauses in the pure half of the status transition | US5 |
| ST2 | Done |  | Widen rm_ref with an optional kind and demote unlink_role to a wrapper | US5 |
| ST3 | Done |  | Add --unlink to the roster status verb: sever, re-evaluate, report | US5 |
| ST4 | Done |  | Word each refusal to its tier with a satisfiable remedy | US5 |
| ST5 | Done |  | Cover the refusals, the escape and the importer replay | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Evaluate the clauses in the pure half of the status transition

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Call the shared clause predicates from `_set_status_model` in `_services/_items.py` — the pure, pre-write half of the transition, which needs only the transaction's own snapshot. A violated clause raises a `SquadsError` before anything is written.

That is also the seam the bulk importer's pre-pass calls, so an import replaying history is held to the same rule at each step it replays. The stated cost is accepted: an import whose *intermediate* state breaks a clause is refused even when its final state is fine, and the remedy is to order the import so the replacement lands first.

`--force` overrides the lifecycle's own transition edge and nothing else. It never overrides these clauses: forcing past one writes agent-host config from a state the engine has already determined is broken, and the breakage then surfaces in another tool where nothing will explain it. The precedent is already set — `force` does not override the status-vocabulary check either. No further flag may be added that bypasses them.

Retiring the last operator is never refused: an operator list may legitimately be empty and a freshly initialised squad has none. A retiring role that still holds open assigned work warns and proceeds — the board is not generated config, and conflating board hygiene with config integrity would fail a routine retirement for an unrelated reason.

Done when each clause refuses at transition time, `--force` does not lift any of them, and no write happens on a refusal.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Widen rm_ref with an optional kind and demote unlink_role to a wrapper

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Engine hygiene called out in ADR-697 §8, and a prerequisite for the flag rather than a cleanup: the flag must not inherit the special case it exists to avoid.

`rm_ref` in `_services/_refs.py` today drops every edge to a target regardless of kind. Widen it with an optional kind: given one, remove only edges of that kind; given none, keep exactly today's kind-agnostic behaviour. Preserve its existing width-tolerant target matching and its `ref` reflog line.

`unlink_role` guards its target's type and hardcodes the `scopes` kind. Demote it to a thin wrapper over the widened primitive plus the existing projection refresh, with its observable behaviour — the type guard, the single-kind removal, the resync — unchanged.

The flag calls the kind-aware generic removal, never `unlink_role`. Routing it through the wrapper would bake a skill-to-role shape and a hardcoded kind into a mechanism that has to stay generic over whatever kinds a clause declares.

Done when `rm_ref` honours a kind filter, `unlink_role` is a wrapper with unchanged behaviour, and both are covered.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add --unlink to the roster status verb: sever, re-evaluate, report

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`--unlink` on the roster `status` verb, registered once on the shared `register_status_verb` in `_cli/_common.py` that the three addressed subgroups already use, and offered only for a `roster`-category type — no other category has config-integrity clauses for it to satisfy.

It overrides nothing. It performs additional, explicit, individually-recorded mutations so the structure genuinely satisfies the clauses, and then the same unforced evaluation that would have refused runs and passes on its own merits. It is not a gentler `--force` and the two must never be collapsed: they compose (`--force --unlink` forces the edge and severs the edges) with neither weakening the other's gate.

The flag consumes each clause's declared ref-kind set rather than knowing anything about skills, roles or the `scopes` kind. A clause with a non-empty set is severable; a clause with an empty set refuses regardless of the flag. C1 and C2 declare the empty set rather than being hardcoded as unlinkable-or-not, so either inherits the flag with no code change if it ever gains a severable formulation.

A severable dependency is a stored forward ref edge — an `item.refs` entry, kind-tagged inline, owned by exactly one item, discoverable in the other direction only by inverting backrefs. Anything derived from the spec is not a reference and cannot be severed. In the one case that exists today the edges are *outgoing* from the retiring entry (the skill holds the `scopes` refs and the roles are the referents), but the mechanism must still handle the incoming direction, since a future clause may refuse retiring an entry that others point at — do not implement only the incoming direction and conclude the flag does nothing.

Order of mutation. Inside the transaction and before any write: sever the clause's edges in the in-memory snapshot, then re-evaluate **every** clause, unforced, against that prospective state. A transition still refused aborts the whole transaction, so severing and then refusing in one command is impossible and a refusal can never leave a partially severed squad. Then markdown first — the retiring entry's frontmatter (its status plus its own `refs` per severed edge) and every other referring item whose `refs` changed — before the index commit. Then the reflog: one `ref` removal entry per severed edge plus the `status` entry.

Reporting is mandatory: each severance names the referring entity, the entity it stopped referencing, and the kind. Quietly editing reference relationships is the flag's whole risk, and the reflog data is already there. No `--dry-run` shape is added — the unforced refusal is the dry run.

Two edge readings. On a retirement with nothing severable: report a no-op and proceed, so a script passing the flag unconditionally is not broken for no benefit. On a transition that is not a retirement: refuse it as meaningless, because the flag is being misread rather than applied to an empty set.

Done when the flag severs only tier-1 edges, re-evaluates unforced, reports and reflogs every severance, and leaves the squad byte-identical to before the command when the transition is still refused.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Word each refusal to its tier with a satisfiable remedy

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Every refusal is satisfiable and names the specific remedy for its clause. C3 additionally enumerates its dependants and classifies each by tier, because the refusal *is* the dry run — an operator decides whether to reach for the flag by reading it.

C1's remedy is to make another role live; C2's is to move `is_default` to a live role. Neither gains an unlink analogue: C1 has no edge at all (it is a cardinality property of the projection), and C2 has a stored designation but not a reference — clearing it would leave the projection with no default at all.

Tier 1, a stored `scopes` edge: name the roles whose edges would be severed. Remedy is the flag, or the explicit unlink verb first.

Tier 2, a type-implied skill: name the specific implicating type or types, capped and summarised for a widely implicated skill. State the mechanism, never a recommendation — retiring one skill must not nudge toward dropping a live work type.

Tier 3, whatever `skills_for_role` implies for every role: state the floor in one line as that property and stop. There is no remedy and offering one would be a lie. Write it as the property, not as a list of names, so it survives a rename and survives the set growing or shrinking.

The bundled tier-2 caveat is behavioural, not aspirational, and this is the one place to get it right. `item_types_for_role` reads the `PLAYBOOK` singleton, built once at import from the bundled spec with no squad-directory parameter and no per-request rebuild, so dropping a type from a project's override does not un-imply its bundled `sq-<type>` skill. A bundled type-implied skill therefore behaves as tier 3 today, and its message must say so rather than naming a remedy that will not take effect. Spec the message to what the code does; do not fix the playbook here.

Done when each refusal names a remedy that exists, the tiers are distinguishable from the message alone, and no message promises the bundled tier-2 remedy.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Cover the refusals, the escape and the importer replay

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Service level plus a CLI smoke per surface, named by behaviour. No ticket ID in any file name, test name or source comment.

Service — a new module for the refusals: one case per clause, C1 allowed with `active_backends` empty, `--force` not lifting any clause alone or combined with the flag, the last-operator and open-assigned-work cases, and the sever-then-still-refused abort asserting the refs and the frontmatter are unchanged on disk.

Service — `tests/service/test_status_vocabulary_enforcement.py` already owns roster transition and vocabulary behaviour; add only what genuinely belongs beside it rather than a second copy of the above.

Unit — `rm_ref`'s kind filter and `unlink_role`'s unchanged behaviour, alongside the existing ref coverage.

CLI — `tests/cli/test_roster_type_address_verbs.py` for the flag's presence, its help text, the no-op reading and the not-a-retirement refusal; `tests/cli/test_skill_role_scoping_verbs.py` for the severance reporting, next to the existing scoping verbs.

Integration — the importer replay refusing a history whose intermediate state breaks a clause, alongside the existing import coverage.

Falsify each refusal and the abort-on-still-refused path: break it, watch the test go red, restore it, watch it go green, and report both.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T10:09:14Z] Olivia Lead:
  - ADR-696 was amended after this task was cut. Body left as written; read this comment alongside it. TASK-703 carries the vocabulary reshape and blocks this task.
  - This body does not name the retired accessors directly, so the substance of C1/C2/C3 and the `--unlink` design stands. What changes is the word: everywhere it says a "live role" or a role being "live" (C1's only-live-role refusal, C2's another-live-role-carries-the-default remedy, C3's live-role preload list), read "offered" — the axis is now an `offered` boolean on the status-role object, defaulting false, read through an offered-statuses predicate.
  - R1 relaxes to "at least one offered status", so a lifecycle may declare several. C1 is a cardinality property of the projection, so it must count entries whose status is in the offered set, not compare against a single status name — same correction as noted on TASK-700.
  - The body already uses "stops being offered" for what retirement means to a roster entry; that reading is now literal rather than figurative, which is the direction the flag's name was chosen for.
  - @python-dev sequence behind TASK-703.
- [2026-07-30T13:05:19Z] Catherine Manager:
  - Two prose fixes in _services/_config_integrity.py belong to this task, since it owns --unlink and the same file. (1) CLAUSE_REF_KINDS currently has no consumer — only its own test asserting the literal table against itself, plus a tests/meta allowlist entry. Move the declaration here, where --unlink reads it, so the test can assert real behaviour (severs exactly C3's scopes edges, refuses C1/C2) instead of a table nobody reads. (2) Strip the forward-referencing and tier-numbered comments: the module currently says the retirement gate 'consumes this' in the present tense about code that does not exist, and cites 'tier 2'/'tier 3' by number to a reader who has no tier list. Describe the mechanism — a severable stored edge versus a cardinality property versus a designation — not where the code sits in a plan.
- [2026-07-31T08:27:15Z] Elias Python:
  - Implemented C1-C3 gate in _set_status_model (new _services/_retirement.py: enforce()/Severance/CLAUSE_REF_KINDS/open_assigned_work), reusing check_all from TASK-700's _config_integrity.py unchanged.
  - --force never overrides (separate from the lifecycle-edge check in _apply_status); operator retirement exempted from check_all entirely (no clause examines operators), verified against an already-broken squad, not just a clean one.
  - --unlink: new Service.set_roster_status (RosterStatusResult: item/severed/warnings) wired to register_status_verb; severs CLAUSE_REF_KINDS' union of declared kinds (today: scopes) from the retiring item's own refs, re-evaluates check_all in the same snapshot before any write, raises ConfigIntegrityError (new, in _errors.py) naming every finding + a per-clause/tier remedy on any remaining violation.
  - rm_ref(from_id, to_id, kind=None) widened; unlink_role demoted to a thin wrapper (rm_ref(kind='scopes') + existing resync) -- observable behaviour unchanged, covered by the pre-existing scope-link-unlink-hook suite plus new kind-filter unit tests.
  - Tier wording (_remedy in _retirement.py): C1 'activate another role first', C2 'make another live role the default first', tier1 'pass --unlink, or run unlink-role first', tier2 states the bundled reality honestly ('none today -- the playbook resolves the bundled spec, not this project's active one'), tier3 'none -- permanent floor'.
  - Prose cleanup done in _config_integrity.py per the assigned comment: CLAUSE_REF_KINDS moved to _retirement.py (its only consumer); the forward-referencing 'gate consumes this' comment is gone with it; the tier-numbered _ALWAYS_ON_SKILLS comment now describes the mechanism (stored edge vs cardinality vs designation) instead of citing tier 2/3 by number.
  - Fixed 6 pre-existing tests that constructed a config-broken state via svc.set_status (now correctly refused by the new gate): switched them to a direct index-transaction write, mirroring test_check_detects_structural_corruption.py's established bypass pattern for other now-service-refused states -- test_check_flags_a_roster_entry_already_config_invalid.py (3), test_check_reports_config_invalid_roster_entries.py (2), test_claude_code_backend.py (2, the CLAUDE.md default-line fallback + the sync round-trip).
  - Falsified every new behavior (break -> red -> restore -> green), each isolated and reported: C1, C2, C3 tier1/tier2/tier3 (incl. the bundled-caveat wording), force-does-not-override (3 variants), unlink severing, unlink meaningless-refusal (service+CLI), unlink sever-then-still-refused abort, rm_ref's kind filter, open-work warning, operator exemption (strengthened the test to retire an operator against an already-C1-broken squad after the first falsification attempt proved too weak to catch removing the carve-out), and the importer-replay refusal.
  - Gate: pyright/ruff check/ruff format clean full-tree (--all-extras); tests/meta clean (62/62, incl. the moved CLAUSE_REF_KINDS mutable-state allowlist entry); sq check clean on this repo; sq repair a no-op (679 items/counter 705 unchanged, confirmed by comparing item count+counter against HEAD -- the on-disk diff is pure JSON re-serialization).
  - One spec point that no longer literally holds: TASK-700's docstring in _config_integrity.py said active-only Service.roster() semantics were 'landing elsewhere' -- that's now this task's own _project_roster_transition/set_roster_status, already in place before I started (looks like it shipped alongside or just ahead of the gate); noted for the record, not a defect.
- [2026-07-31T08:40:41Z] Elias Python:
  - Fixed the composed-refusal duplication (caught live: sq skill squads status Archived repeated 'a permanent floor of the roster contract' and followed 'no remedy exists' with 'remedy: none -- permanent floor').
  - Root cause: ConfigIntegrityFinding.message baked remedy wording straight into the condition text for some clauses/tiers, and the gate's separate _remedy() (now deleted) appended its own remedy phrase on top -- two independent authors of the same idea, concatenated.
  - Fix: split into ConfigIntegrityFinding.message (condition only, never mentions what to do) + .remedy (str | None). New _config_integrity.render_finding(finding, with_remedy=True) is the single place the two are ever joined; the gate (_retirement.py) and the sq check reporter (_validators.py) both render through it instead of composing their own string. _remedy() deleted from _retirement.py entirely -- remedy text now lives once, in _config_integrity.py's clause builders.
  - Checked and re-verified every clause/tier, live output pasted verbatim:
  - C1: error: cannot move ROLE-1 to 'Archived': the resulting projection would be structurally invalid: - C1 (ROLE-1): no role entry is live, but backend(s) claude_code are active — the generated config can present no agent — remedy: activate another role first
  - C2: - C2 (ROLE-1): carries is_default but is not live (status 'Archived'), and no live role carries the default designation — remedy: move `is_default` to another live role first
  - C3 tier1: - C3 (SKILL-12): not live (status 'Archived') but still scoped to live role(s): manager — remedy: pass --unlink, or run `sq skill <addr> unlink-role <role>` first
  - C3 tier2: - C3 (SKILL-10): not live (status 'Archived') but implied by declared type(s): task — remedy: none today — the playbook resolves the bundled spec, not this project's active one, so dropping the type would not un-imply this skill
  - C3 tier3 (the reported bug): - C3 (SKILL-11): not live (status 'Archived') but every role preloads it unconditionally — a permanent floor of the roster contract; no remedy exists  -- single occurrence, nothing appended, since remedy=None for this tier.
  - Tests: added remedy-field + no-duplicate assertions to test_roster_config_integrity_predicates.py (a render_finding suite, one exact-string test per clause/tier plus a with_remedy=False case); added an end-to-end composed-message section to test_retirement_refuses_a_config_breaking_transition.py (exact full ConfigIntegrityError text per clause/tier, not fragments); added one true CLI end-to-end test (sq skill squads status Archived through invoke()) to test_roster_type_address_verbs.py asserting the tier-3 phrase count on the actual terminal output, normalizing Rich's line-wrap first.
  - Falsified the fix itself: reverted render_finding to always append a remedy tail (even when remedy is None) -- all three new tier-3 composition tests (unit render_finding, service end-to-end, CLI end-to-end) went red on the reintroduced duplicate; restored, green again.
  - Verify: pyright/ruff check/ruff format clean full-tree; the 9 touched test files + tests/meta all green (199 passed); sq check clean on this repo.
<!-- sq:discussion:end -->
