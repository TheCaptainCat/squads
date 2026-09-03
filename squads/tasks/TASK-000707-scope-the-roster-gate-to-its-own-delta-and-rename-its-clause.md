---
id: TASK-707
sequence_id: 707
type: task
title: Scope the roster gate to its own delta and rename its clauses
status: Done
parent: FEAT-691
author: tech-lead
priority: urgent
refs:
- REV-706:addresses
- ADR-697:implements
- BUG-698:fixes
description: Delta-scoped clause evaluation, per-clause unlink, the withdrawn default-role
  clause, and condition-named clauses
subentities:
- local_id: ST1
  title: Refuse only what this transition introduces
  status: Done
  story: US5
- local_id: ST2
  title: Sever only the edges the refusal enumerated
  status: Done
  story: US5
- local_id: ST3
  title: Withdraw the default-role clause and warn instead
  status: Done
  story: US5
- local_id: ST4
  title: Omit the default role from generated prose when none is live
  status: Done
  story: US4
- local_id: ST5
  title: Condition the clause family on an active backend
  status: Done
  story: US5
- local_id: ST6
  title: Derive the always-on floor instead of listing it
  status: Done
  story: US5
- local_id: ST7
  title: Report one finding per detected dependency
  status: Done
  story: US6
- local_id: ST8
  title: Name clauses for their condition, keep the name internal
  status: Done
  story: US5
- local_id: ST9
  title: Define a retirement as a move out of a live status
  status: Done
  story: US5
- local_id: ST10
  title: Leave one gated entry point for a roster status change
  status: Done
  story: US5
- local_id: ST11
  title: Say retired, not unknown, for a retired slug
  status: Done
  story: US4
- local_id: ST12
  title: Restate the module's rationale, drop the dead parameter
  status: Done
created_at: '2026-07-31T09:36:29Z'
updated_at: '2026-07-31T12:41:29Z'
---
<!-- sq:body -->
## Context

`_services/_config_integrity.py` holds the roster config-integrity clause predicates;
`_services/_retirement.py` enforces them in the pure, pre-write half of a roster status
transition (`_set_status_model` in `_services/_items.py`). Both diverge from ADR-697 §7-§9,
which carries a 2026-07-31 amendment note that is now the contract: the clause family is
conditioned on an active backend with one named exception, the default-role clause is withdrawn
rather than repaired, and a clause answers whether *this* transition breaks something that was
not already broken.

Read ADR-697 §7, §8, §9 and that amendment note before editing either module. Where a shipped
docstring restates the pre-amendment clause text, the docstring is what is wrong.

## Delta-scoped evaluation

`enforce` calls `check_all(db, spec, active_backends)` — the whole squad's state — instead of the
findings the transition introduces. One pre-existing violation therefore refuses *every*
subsequent role or skill status transition, blamed on an entry the operator never touched, and a
squad carrying two violations cannot repair either because each blocks the other's fix. There is
no escape: `--force` never overrides a clause, `--unlink` cannot sever a tier-2 or tier-3
dependency, and the tier-3 message correctly reports that no remedy exists. Reproduced on a
throwaway squad: a hand-planted archived foundation skill makes `sq role architect status
Archived` fail citing the *skill*, remedy "none".

Refuse only on findings this transition introduces — compare the prospective evaluation against
the pre-transition snapshot and raise on the difference, or restrict to findings naming the
transitioning entry plus the last-live-role cardinality property. Either shape is acceptable;
what is not acceptable is a clause answering "is this squad currently well-formed". Pre-existing
invalidity belongs to the report-mode validator alone — that division of labour is the entire
reason the reporter exists as a separate surface.

The importer's pre-pass calls the same seam, so an import into an already-broken squad must stop
refusing at its first roster `status` event for a reason its own history did not create.

## `--unlink` severs the violated clause's own edges

`_sever_declared_edges` removes every ref on the retiring item whose kind appears anywhere in
`CLAUSE_REF_KINDS`, unioned across all clauses, without consulting the clause that refused. A
custom skill scoped to two roles — one live, one already retired — loses both edges; the retired
role's edge was never a dependency, was never enumerated in the refusal, and its severance
rewrites that role's `extra.skills` cache and `## Skills` body region anyway.

ADR-697 §8 is per-clause: a clause with a non-empty kind set is severable, and `--unlink`
enumerates *that clause's* edges, removes each, and re-evaluates. This matters beyond tidiness:
§8 declines to ship `--dry-run` on the grounds that "the refusal message is the dry run", so a
severance wider than the refusal enumerated makes the substitute for a dry run wrong in the
unsafe direction.

Pass the violated findings into the severance rather than unioning every declared kind and
matching against the item's whole ref list. The per-clause declaration already exists; what is
missing is using it. Sever only edges a finding named, and keep the re-evaluation a delta against
the pre-transition snapshot per the section above, so severing an edge cannot make the command
answerable for a violation it inherited.

## The default-role clause is withdrawn

The clause refusing to retire the `is_default`-carrying role named a remedy no command performs,
and the amendment withdraws it rather than giving it a verb: the state it refused is legitimate
(the AGENTS.md backend has no default-role concept at all), and the structural defect is the
Claude backend fabricating a slug when it finds no designated role. That door is already open
with no status transition in play — `sq role manager rm --purge` on a fresh squad exits 0 with
`sq check` clean, after which the generated `CLAUDE.md` still reads "default to **the manager**
(`manager`)" with no `manager` in the roster. Verified.

Three parts, all owed together:

- Remove the clause from the clause set **and** from the `sq check` reporter's output. The state
  stops being invalid, so the report is no longer owed — a reporter that keeps naming it would
  make `sq check` dirty for a legitimate squad.
- Fix the fabrication at its source: `_backends/_claude_code/_backend.py:104-105` substitutes
  `"the manager"` / `"manager"` when no live role carries the designation. Both template sites
  in `_rendering/templates/claude/claude_section.md.j2` read that value — the default-role line
  and the orchestration paragraph — and both must **omit** rather than invent. The generated
  prose says less than it did; it never names something that is not there. This is the
  degradation the developer-gated skill text already performs when the last `<tech>-dev` role
  retires (`has_dev` in the same backend module) — follow that shape.
- Add a **warning, not a refusal**, on a transition that takes the last live designation out of a
  live status, in the same shape as the open-assigned-work warning already carried on
  `_set_status_model`'s result. The adopter loses a line of routing guidance from their generated
  config and should hear about it; nothing another tool reads is left dangling.

## The backend condition is family-wide, with one exception

Only the last-live-role clause reads `active_backends`. The others refuse in a squad with no
active backend at all, where no generated config exists to break — un-blessing the sq-only squad
ADR-141 protects.

Thread the condition per the amendment, which is finer than "condition all of them":

- last-live-role: conditioned (unchanged).
- the skill-dependency clause, stored-edge and type-implied tiers: conditioned. The dependency is
  playbook- or spec-authored, but what it breaks is a generated entry, and with no backend there
  is no entry.
- the same clause's always-on-floor tier: **not** conditioned. Its authority is a declared rule
  of the roster contract rather than a derived property of the projection. It refuses in a squad
  with no backend, and a later refactor must not sweep it into the conditioned set.

That split means the clause cannot early-return on an empty `active_backends`; it has to reach
the floor tier regardless. Its other precondition is unchanged and is about roles, not backends:
a property quantified over every live role is vacuous when there are none.

## The always-on floor is a property, not a list

`_ALWAYS_ON_SKILLS` is a hand-maintained frozenset of three names, free to disagree with the
resolver it restates, while its own docstring claims the opposite ("stated as the property …
rather than re-derived from it"). ADR-697 §8 rules on this in terms — whatever
`skills_for_role` implies for every role is un-retirable — and the alternatives section rejects
the built shape by name.

Derive it: intersect `skills_for_role` over the live roles the clause already computes, or
subtract the type-implied `sq-<type>` names from any one role's resolved list. Mind the vacuous
case — an intersection over an empty role set is everything, which would classify every
non-live skill as an un-retirable floor member. At minimum the docstring must stop claiming a
property the code does not express, but the derivation is the fix.

## One finding per detected dependency

The skill-dependency clause classifies with `if implicating_types: … elif scoped_roles:`, so a
skill that is simultaneously type-implied and carrying a stored edge to a live role reports only
the type-implied finding, and the refusal never names the roles whose edges `--unlink` would
sever. §8's enumeration is concrete *per tier*, not per the skill's single highest tier. Emit one
finding per detected dependency, or carry both on one finding — the collected list shape already
supports several findings per entry.

## A retirement is a move out of a live status

Two ordering defects in `enforce`:

- The operator exemption returns *after* severance, so `sq operator <slug> status Archived
  --unlink` strips every severable-kind ref with no clause ever consulted. The exemption is "no
  clause names an operator", not "an operator transition severs unconditionally". Move the
  early return above the severance.
- `is_retirement` is computed as "the new status is not live", so under a lifecycle declaring two
  non-live statuses a non-live-to-non-live move accepts `--unlink` and severs while nothing is
  being retired. A retirement is a move *out of* a live status: the old status is live and the new
  one is not. The old status is already in hand at the call site.

Both are correct today only by coincidence — the first because of what operators happen not to
carry, the second because the bundled roster lifecycle has one non-live state. ADR-696 §3's
R1/R2 permit richer lifecycles explicitly.

## Clauses are named for what they check, and the name stays internal

The `C1`/`C2`/`C3` labels and the `tier 1/2/3` numbering go.

They have already rotted: with the default-role clause withdrawn the set reads `C1` and `C3`
around a hole, so the numbering misinforms every reader of the code, the decision, and the
message. And they leak into user-facing output inconsistently — the gate prints the label, the
reporter does not, and an adopter has no document in which `C3` means anything:

```
gate:     - C3 (SKILL-18): not live (status 'Archived') but every role preloads it …
sq check: error SKILL-18: config integrity: not live (status 'Archived') but every role preloads it …
```

- Rename each clause to describe the condition it checks, not its position in a list — e.g.
  `no_live_role` and `dependent_skill`, with the tiers named too (`scoped_edge`, `type_implied`,
  `always_on_floor`). Pick the final names; the requirement is that they describe the condition
  and survive a clause being added or withdrawn.
- **Drop the label from user-facing text entirely.** A refusal and a report each read as the
  condition plus its remedy, nothing else. The name stays internal: code, the per-clause ref-kind
  declaration, tests, and the decision record.
- Make the gate and the reporter render the **same** condition text. They already share
  `render_finding`; this should remove code rather than add it, and it settles the reviewer's
  separate observation that the gate's rendering repeats the target status the operator just
  typed. A gate rendering that drops the redundant parenthetical reads cleanly without disturbing
  the two-field message/remedy split.
- ADR-697 uses `C1`/`C2`/`C3` and `tier 1/2/3` throughout and needs the new vocabulary. That edit
  belongs with this change but **not** to whoever implements it: §7 currently *argues for* stable
  labels ("the labels are stable and C3 is never renumbered into the gap, because a clause label
  appears in every refusal an operator has already read"), so the rename reverses a stated
  position rather than swapping vocabulary. The architect makes that amendment; an implementer
  must not rewrite an Accepted decision's substance.

## One gated entry point for a roster status change

There are two pure-half status-transition seams and only one is gated. `_set_status_model` calls
the gate; `_update_model`'s status branch calls `_apply_status` with no clause evaluation and no
projection afterwards. Not reachable for a roster type today — the three roster groups register
no `update` verb and the importer has no `update` op — but nothing keeps it unreachable, and the
architect reached `is_default` itself through that seam while verifying the withdrawal above.

Either route `_update_model`'s status branch through the same gate, or add a guard asserting that
a roster item's status cannot change through any path that does not evaluate the clauses.
`tests/meta` is the right home for the guard shape if that is the route taken.

## A retired slug reads as retired

`_cli/_common.py::resolve_slug_or_raise` with the default `live_only=True` raises `unknown slug
'<slug>'; valid slugs: …` for a slug that is well known and merely retired, sending the operator
after a typo or a missing activation:

```
$ sq role qa status Archived
ROLE-5 → Archived
$ sq create bug "b" --author qa
error: unknown slug 'qa'; valid slugs: architect, devops, manager, product-owner, reviewer, tech-lead
```

The gate itself is right and the read paths correctly pass `live_only=False`. Only the wording
lags. When the slug resolves against the full roster but not the live one, say so and name the
entry and the one command that undoes it. The full-roster lookup is already one call away.

## Module prose and a dead parameter

`_config_integrity.py`'s module docstring explains why it avoids `Service.roster()` by reference
to a projection change "landing elsewhere" that "would race" it. That change shipped in the same
release, so the sentence is false as well as narrating a sequencing accident; it also carries the
only surviving `active-only` in `src/`, `tests/`, `docs/` and the changelog, against the
`live`/`non-live` vocabulary everything else uses. The durable reason is purity — no I/O, no
`Service` instance, so the same predicates serve both a reporter over on-disk state and a gate
over a transaction snapshot. State that and delete the rest.

`render_finding`'s `with_remedy=False` has no caller and its own docstring says so. Drop the
parameter; the periodic dead-code scan would find it otherwise.

## Out of scope

Making the playbook resolve per-request against the active spec, so the type-implied tier's
remedy takes effect for a bundled type — the message must keep saying what the code does. A
`--dry-run` shape. A designation verb for `is_default` (its own item). Attributing a `--unlink`
severance to an actor: the roster `status` verb takes no `--as` at all, so that is a decision
about the whole roster verb family rather than a fix here. The adopter-facing changelog and docs
entries. `_base.py`/`_maintenance.py`'s projection path.

## Acceptance

- A squad already violating any clause can still transition every roster entry, including the
  transitions that repair it, and two co-existing violations can each be fixed independently.
  A transition that introduces no new finding is never refused.
- An import into an already-broken squad replays without refusing at its first roster `status`
  event.
- `--unlink` severs only edges the refusal enumerated; an unrelated severable-kind edge on the
  same item survives, and every other item's frontmatter and body regions are byte-identical.
- A still-refused `--unlink` leaves the squad byte-identical to before the command, refs
  included.
- Retiring the `is_default`-carrying role succeeds, warns that the designation was lost, and the
  regenerated `CLAUDE.md` region names no default role in either the default-role line or the
  orchestration paragraph — while remaining coherent prose, not a dangling sentence.
- `sq check` no longer reports the not-live-default condition at all.
- With `active_backends = []`: every clause stays silent except the always-on floor, which still
  refuses.
- The always-on floor is derived from the preload resolver, and a test proves the derivation
  moves when the resolver's implied set moves — not a restated list of names.
- A skill that is both type-implied and scoped to a live role produces both findings, and the
  refusal names the roles whose edges would be severed.
- `sq operator <slug> status Archived --unlink` severs nothing. A non-live-to-non-live move
  refuses `--unlink` as meaningless.
- No refusal or report prints a clause label; gate and reporter render the same condition text
  for the same finding.
- A roster item's status cannot change through an ungated path.
- An `--as`/`--author`/`--assignee` naming a retired slug says it is retired, names the entry,
  and gives the reactivating command.
- `grep -rn "active-only" src/ tests/ docs/ CHANGELOG.md` returns nothing; no ticket ID, finding
  label or build-process narration in any source file, test name or comment.
- `uv run sq check` clean, `sq repair` a no-op.
- `uv run --all-extras` clean on each of `pyright`, `ruff check .`, `ruff format --check .`.
- Full suite green. A new module-level constant means running `tests/meta` and allowlisting it as
  a CODE constant rather than restructuring the code.
- Falsify the delta scoping and the per-clause severance: break each, watch the test go red,
  restore it, watch it go green, and report both.

## Tests

Named by behaviour. The modules that already own this surface, extended rather than duplicated:

- `tests/unit/test_roster_config_integrity_predicates.py` — the predicates: the derived floor,
  the family-wide backend condition with the floor tier exempt, both findings for a
  doubly-dependent skill, the withdrawn clause gone from the clause set, the shared rendering.
- `tests/service/test_retirement_refuses_a_config_breaking_transition.py` — the gate: the
  already-broken squad now transitioning (both directions, and two violations repaired
  independently), per-clause severance with an unrelated edge surviving, the operator exemption
  severing nothing, the non-live-to-non-live `--unlink` refusal, the lost-designation warning.
- `tests/service/test_check_flags_a_roster_entry_already_config_invalid.py` and
  `tests/cli/test_check_reports_config_invalid_roster_entries.py` — the reporter: the withdrawn
  condition no longer reported, and report text identical to the gate's for the same finding.
- `tests/integration/test_claude_code_backend.py` — the managed region omitting the default-role
  line and the orchestration paragraph's name when no live role carries the designation.
- `tests/cli/` — the retired-slug message on `--as`/`--author`/`--assignee`.
- `tests/meta/` — the guard for a single gated roster status seam, if that is the route chosen.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 707 add-subtask "<title>"`; track with `sq task 707 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Refuse only what this transition introduces

<!-- sq:subtask:ST1:body -->
Evaluate the clauses as a delta: compare the prospective state against the pre-transition snapshot and raise on the difference, or restrict to findings naming the transitioning entry plus the last-live-role cardinality property. A squad already violating a clause keeps every transition available to it, the repairing ones included, and two co-existing violations can each be fixed independently. The importer's pre-pass inherits the same behaviour.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Sever only the edges the refusal enumerated

<!-- sq:subtask:ST2:body -->
Pass the violated findings into the severance instead of unioning every declared ref kind and matching the item's whole ref list. An unrelated severable-kind edge on the retiring item survives; the re-evaluation after severing stays a delta against the pre-transition snapshot. A still-refused transition leaves the squad byte-identical, refs included.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Withdraw the default-role clause and warn instead

<!-- sq:subtask:ST3:body -->
Remove the clause from the clause set and from the sq check reporter — the state it refused is legitimate, so the report is no longer owed. Add a warning, not a refusal, on a transition that takes the last live designation out of a live status, in the same shape as the open-assigned-work warning already carried on the transition result.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Omit the default role from generated prose when none is live

<!-- sq:subtask:ST4:body -->
The Claude backend substitutes a hardcoded name and slug when no live role carries the designation, and both template sites read that value — the default-role line and the orchestration paragraph. Both omit rather than invent, leaving coherent prose. Same degradation the developer-gated skill text already performs when the last developer role retires.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Condition the clause family on an active backend

<!-- sq:subtask:ST5:body -->
State the condition once for the whole family — no projection, no clause — with the always-on-floor tier exempted by name, because its authority is a declared rule of the roster contract rather than a derived property of the projection. The skill-dependency clause therefore cannot early-return on an empty backend list; it must still reach the floor tier.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Derive the always-on floor instead of listing it

<!-- sq:subtask:ST6:body -->
Replace the hand-maintained frozenset of three names with the property it claims to state: whatever the preload resolver implies for every live role is un-retirable. Mind the vacuous case — an intersection over an empty live-role set is everything. A test must prove the derivation moves when the resolver's implied set moves.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Report one finding per detected dependency

<!-- sq:subtask:ST7:body -->
The skill-dependency clause classifies with if/elif, so a skill that is both type-implied and scoped to a live role reports only the type-implied finding and the refusal never names the roles whose edges the flag would sever. Emit one finding per detected dependency, or carry both on one; the collected list shape already supports several per entry.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Name clauses for their condition, keep the name internal

<!-- sq:subtask:ST8:body -->
Rename each clause and tier to describe the condition it checks rather than its position in a list, and drop the label from every user-facing string so a refusal and a report each read as the condition plus its remedy. Gate and reporter render the same condition text through the one shared renderer. Sequence this after the semantics settle, so the rename runs once over a stable set.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Define a retirement as a move out of a live status

<!-- sq:subtask:ST9:body -->
Move the operator exemption above the severance, so an operator transition never strips a ref with no clause consulted. Redefine the retirement predicate as old status live and new status not live, using the old status already in hand at the call site, so a non-live-to-non-live move under a richer lifecycle stops accepting the flag.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Leave one gated entry point for a roster status change

<!-- sq:subtask:ST10:body -->
The metadata-update path's status branch applies a status with no clause evaluation and no projection. Route it through the same gate, or add a guard asserting a roster item's status cannot change through any path that does not evaluate the clauses. Not reachable for a roster type today, but nothing keeps it that way.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Say retired, not unknown, for a retired slug

<!-- sq:subtask:ST11:body -->
The participation gate raises unknown slug for a slug that is well known and merely retired, sending the operator after a typo or a missing activation. When the slug resolves against the full roster but not the live one, say so, name the entry, and give the one command that undoes it. The full-roster lookup is already one call away.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->

<!-- sq:subtask:ST12 -->
### ST12 — Restate the module's rationale, drop the dead parameter

<!-- sq:subtask:ST12:body -->
The clause module's docstring explains its avoidance of a service accessor by reference to a change that has since shipped, in pre-rename vocabulary, narrating a sequencing accident. The durable reason is purity — no I/O and no service instance, so the same predicates serve both a reporter over on-disk state and a gate over a transaction snapshot. Also drop the finding renderer's callerless keyword parameter.
<!-- sq:subtask:ST12:body:end -->

#### Discussion

<!-- sq:subtask:ST12:discussion -->
<!-- sq:subtask:ST12:discussion:end -->
<!-- sq:subtask:ST12:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T10:27:37Z] Elias Python:
  - Implemented ST1-ST12. Delta-scoped enforce() (before/after check_all diff on old_status vs new); per-clause --unlink severance via finding.severable_targets; no_default_role clause withdrawn (check_c2 removed) + lost-designation warning + Claude backend/template fabrication fixed (default_role_full_name/slug now None, template omits both sites); backend condition threaded per clause (always_on_floor exempt); floor derived via skills_for_role minus each role's own type-implied set (guards both the empty-role and single-live-role collapse cases); one finding per dependency kind (scoped_edge + type_implied can co-fire); operator exemption moved above severance; is_retirement = old_status live and new not live; retired-slug hint on --as/--author/--assignee; _update_model now refuses a roster status change (single gated entry point), including through the bulk importer's generic update op; clause/kind identifiers are internal (no_live_role, preloaded_skill, scoped_edge, type_implied, always_on_floor) with no C1/C2/C3 or tier: int anywhere, and no clause label in gate or reporter output. Fast gates clean (pyright/ruff/format), sq check clean. Falsified delta-scoping and per-clause severance by hand (reverted, watched red, restored, watched green) -- see my handoff notes for the parent agent.
  - Out of scope untouched: TASK-708's reactivation projection path, TASK-709's docs/changelog, TASK-710's designation verb.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
