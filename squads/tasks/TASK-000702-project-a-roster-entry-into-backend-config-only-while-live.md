---
id: TASK-702
sequence_id: 702
type: task
title: Project a roster entry into backend config only while live
status: Done
parent: FEAT-691
author: tech-lead
priority: high
refs:
- ADR-697:implements
- TASK-699:depends-on
description: Materialise-iff-live through the AgentBackend ABC, withdrawal and regeneration,
  and the two roster projections
subentities:
- local_id: ST1
  title: Split the roster accessors into active-only and full projections
  status: Done
  story: US4
- local_id: ST2
  title: Audit every roster caller against the projection table
  status: Done
  story: US4
- local_id: ST3
  title: Materialise and withdraw through the backend ABC on a transition
  status: Done
  story: US4
- local_id: ST4
  title: Make sq sync the convergence point for the projection
  status: Done
  story: US4
- local_id: ST5
  title: Accept only a live slug where a participant is written
  status: Done
  story: US4
- local_id: ST6
  title: Cover both directions, the fan-out and the wrong projection
  status: Done
  story: US4
created_at: '2026-07-30T07:47:29Z'
updated_at: '2026-07-31T12:41:25Z'
---
<!-- sq:body -->
## Context

ADR-697 §1-§6 and §10-§11. A materialised roster entry is a pure projection of its frontmatter,
the active workflow spec and the active backend list — never a second source of truth, never
migrated. An entry is materialised if and only if its status resolves to the live role; every
other role is unmaterialised.

Nothing connects the two today. `grep -rn "status" src/squads/_backends/` returns nothing, and
`Service.roster()` / `Service.operators()` list every entry regardless of status — which is
exactly what `write_managed` compiles from. A retired role therefore keeps its pointer file,
stays in the compiled roster region, and stays a valid `--as`/`--assignee` slug.

## Scope

**The predicate, expressed only in the service.** No method is added to the `AgentBackend` ABC
and no backend ever sees a status. Materialise is `generate_role_entry` / `generate_skill_entry`
for the entry's own files plus inclusion in every managed region the backend compiles, via
`write_managed`. Withdraw is the existing `remove_artifacts` plus exclusion from those same
recompiled regions. Reactivate is materialise again, in full, through the same call path as
first creation — there is no partial-repair path to design.

Withdrawal is two-part because the two built-in backends have two artifact shapes. Deleting the
per-entry file without recompiling the region would leave the region naming an entry with no
definition, which is worse than either endpoint. Note the compiled content depends on the roster
beyond the roster table: the Claude backend's default-role line comes from the entry carrying
`is_default`, and its per-item-type skills branch on whether any developer role is present, so a
withdrawal changes generated *prose*, not only a list.

**Fan-out** iterates every deduped entry of `active_backends`, order-insignificant as ADR-141
fixed. A backend never scaffolded is still called — `remove_artifacts` is missing-tolerant and
idempotent by its existing contract. A backend *removed* from `active_backends` is not touched,
retired entries' files included; that asymmetry follows ADR-141 §5 and is deliberate.

**The two projections.** `Service.roster()` / `Service.operators()` become active-only; add
`Service.roster_all()` / `Service.operators_all()` returning every entry regardless of status.
Which one a caller takes is a correctness question, and picking the wrong one is a silent bug —
an active-only list where the full list belongs makes a retired entry look like an orphan or its
authorship look unregistered. Audit every caller against ADR-697 §3's table, caller by caller.
The full set is required for `candidate_orphans` (a withdrawn entry's leftover file is this
squad's own convergence debt, never a foreign file), for authorship display-name resolution
(`_author_of` — a retired role's name must still render on the comments it wrote), for
`registered_slugs` behind the `agent_registered` check, and for the roster's own views
(`sq role list`, `sq operator list`, `sq list -t skill`). Active-only is required for
`write_managed`'s roster and operator lists and for `_skill_paths` / `_role_skills_map` /
`resolved_skills_for_role`, which name the skills the generated entries preload.

**The transition.** The projection write happens **after** the transaction commits, not inside
it. Generated files are regenerable cache rather than markdown items, so they sit outside the
markdown-ahead-of-index durability rule; a crash between commit and projection leaves files the
next sync converges. This is the ordering the roster create verbs already use.

**`sq sync` is the convergence point.** Its existing roster sweep gains the same predicate:
materialise when live, withdraw otherwise. That single rule keeps sync idempotent and is also the
whole upgrade story for squads already on disk with retired entries — no migration runner, no
schema bump, converged on the next sync, and nothing misbehaving in between because `sq check`'s
backend reconciliation probes only the always-present top-level files.

**Participation.** The entry points that *write* a participant — `--as`, `--author`,
`--assignee` on create/comment/update — accept only live slugs. `resolve_slug_or_raise` in
`_cli/_common.py` already reads `svc.roster()` / `svc.operators()`, so the live-slug gate falls
out of the projection split; confirm that rather than adding a second gate. `agent_registered`
keeps validating against the full roster vocabulary — the question it asks is "was this a
registered participant", not "is it live now" — so an item authored by a role retired a year
later must never start reporting a warning it cannot fix. The bulk importer is exempt from the
live-slug gate and keeps the registration check only, because it replays history and history is
full of participants who have since retired.

## Out of scope

Any change to `sq check`'s present-only backend reconciliation, and no currency check for the
projection (ADR-697 §6). The config-integrity clauses and their refusals. Retirement is not
removal: `rm` keeps hard-deleting the item, and this task changes only the projection.

## Acceptance

- Moving a role or skill entry to a live status materialises it: its own backend file(s) exist and
  it is included in every managed region a backend compiles — the roster table, the default-role
  line, the developer-gated per-item-type skill text, and a role's resolved preload list.
- Moving it to any other status withdraws it: its own file(s) removed via `remove_artifacts` and
  excluded from every one of those same regions.
- Reactivating a withdrawn entry regenerates it in full, by the same call path as first creation.
- Both directions fan out over every deduped `active_backends` entry; a backend absent from that
  list is left untouched, its stale files for retired entries included.
- `roster()` / `operators()` return active-only and are what `write_managed` and skill-preload
  resolution consume; `roster_all()` / `operators_all()` return everything and are what the
  §3 table's full-set callers consume.
- `sq sync` applies the predicate to every roster entry on every run, including an entry already
  in a non-live status before this lands, and stays idempotent. No migration, no schema bump.
- `--as` / `--author` / `--assignee` reject a retired slug with a clean error; `agent_registered`
  and the bulk importer keep validating against the full vocabulary.
- `candidate_orphans` does not report a withdrawn entry's leftover file as an orphan.
- A comment written by a since-retired role still renders that role's display name.
- `sq check` clean and `sq repair` a no-op after a retirement and after a reactivation.
- Gate clean with `--all-extras` on each of pyright, `ruff check .` and `ruff format --check .`.
- Full suite green, goldens included — a withdrawal changes generated prose, so expect managed
  golden movement and review each diff rather than blanket-regenerating.
- Falsify: swap a full-set caller to the active-only projection and assert the test catches it;
  restore and watch it pass. ADR-697 names this the part of the contract most in need of tests
  that assert the *wrong* projection fails.

## Tests

Service level plus a CLI smoke per surface, named by behaviour. No ticket ID in any file name,
test name, or source comment.

- Service — a new module for the projection predicate: materialise, withdraw, reactivate, and the
  per-caller projection audit including the wrong-projection assertions.
- Service — `tests/service/test_active_role_roster_listing.py` for the `roster()` /
  `roster_all()` split next to the existing listing behaviour.
- Integration — `tests/integration/test_backend_lifecycle_contract.py` for the ABC-level
  obligations (missing-tolerant, idempotent withdrawal against an unscaffolded backend);
  `tests/integration/test_multi_active_backends.py` for the fan-out and the
  removed-backend-untouched asymmetry; `tests/integration/test_claude_code_backend.py` and
  `test_agents_md_backend.py` for the compiled-region exclusion, default-role line and
  developer-gated skill text.
- CLI — `tests/cli/test_roster_type_address_verbs.py` for the retirement's observable effect, and
  the existing author/assignee coverage for the live-slug gate.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 702 add-subtask "<title>"`; track with `sq task 702 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Split the roster accessors into active-only and full projections

<!-- sq:subtask:ST1:body -->
`Service.roster()` and `Service.operators()` in `_services/_base.py` list every entry of the type regardless of status today, and those two lists are exactly what `write_managed` compiles from. They become **active-only** and after this mean "the entries this squad currently offers".

Add `Service.roster_all()` and `Service.operators_all()` returning every entry regardless of status, for the callers that need the full vocabulary.

The filter belongs here, in the service accessors that feed the backends. No method is added to the `AgentBackend` ABC and no backend ever sees a status: the projection is expressed entirely in terms backends already implement, so a future backend inherits withdrawal by implementing the same seven methods it would have implemented anyway. Liveness is the `role_statuses(item_type, "active")` predicate — never a status literal.

Done when both pairs exist with the split semantics and no caller has been re-pointed yet.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Audit every roster caller against the projection table

<!-- sq:subtask:ST2:body -->
Which projection a caller takes is a correctness question, not a preference, and picking the wrong one is a silent bug: an active-only list where the full list belongs makes a retired entry look like an orphan or its authorship look unregistered. Go caller by caller against ADR-697 §3's table.

Full set: `candidate_orphans` — an orphan means "a file this squad never managed", and a withdrawn entry's leftover file is the opposite of that, so feeding the active-only list here would relabel this squad's own convergence debt as the adopter's foreign file, most loudly on exactly the squads that have retired an entry. `_author_of` — a retired role's display name must still render on the comments it wrote. `registered_slugs` behind the `agent_registered` check. And the roster's own views (`sq role list`, `sq operator list`, `sq list -t skill`), which already carry a status column.

Active only: `write_managed`'s roster and operator lists, because they compile the host's config; and `_skill_paths`, `_role_skills_map` and `resolved_skills_for_role`, because they name the skills the generated entries preload.

Done when every call site has been visited and the reason for its projection is legible at the call site or in the accessor's docstring.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Materialise and withdraw through the backend ABC on a transition

<!-- sq:subtask:ST3:body -->
An entry is materialised if and only if its status resolves to the live role. Every other role is unmaterialised. One predicate, read through the spec — there is no third state and no per-role table of behaviours.

Materialise: `generate_role_entry` / `generate_skill_entry` for the entry's own files, **and** inclusion of the entry in every managed region the backend compiles, via `write_managed`. Withdraw: the existing `remove_artifacts` for its own files, **and** exclusion from those same recompiled regions. Reactivate: materialise again, in full, by the same call path as first creation — the artifact is a projection, so there is no partial-regeneration or repair path to design.

Withdrawal is deliberately two-part because the two built-in backends have two artifact shapes. Deleting a per-entry pointer without recompiling the region would leave the region naming an entry with no definition, which is worse than either endpoint. A backend with only compiled regions satisfies the first half trivially and the second half is what actually withdraws the entry.

The compiled content depends on the roster beyond the roster table: the Claude backend's default-role line comes from the entry carrying `is_default`, and its generated per-item-type skills branch on whether any developer role is present. A withdrawal changes generated *prose*, not only a list, so expect a larger managed diff than a row removal.

Fan out over every deduped entry of `active_backends`, order-insignificant as ADR-141 fixed. A backend never scaffolded is still called — `remove_artifacts` is missing-tolerant and idempotent by its existing contract, so withdrawal against a backend with no files is a clean no-op. A backend *removed* from `active_backends` is not touched, its retired entries' files included; that follows ADR-141 §5 (deactivation is ignore, not delete) and is deliberate.

The projection write happens **after** the transaction commits, not inside it. Generated files are regenerable cache rather than markdown items, so they sit outside the markdown-ahead-of-index durability rule; a crash between commit and projection leaves files the next sync converges. This is the ordering the roster create verbs already use.

Retirement is not removal: `rm` keeps hard-deleting the item, and both paths correctly share `remove_artifacts` because the file-level effect is identical and only the record's fate differs. Retirement keeps the item, its body and its whole discussion.

Done when a transition in either direction converges the projection across every active backend, and reactivation is byte-identical to first creation.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make sq sync the convergence point for the projection

<!-- sq:subtask:ST4:body -->
`sync` in `_services/_maintenance.py` already sweeps every roster item and regenerates. It gains the same predicate: materialise the entry when its status is live, withdraw it otherwise. That single rule keeps sync idempotent and makes it the total convergence point for the projection.

It is also the whole upgrade story for squads already on disk whose entries are retired today. No migration runner and no schema bump: the first sync after this lands withdraws the leftover files. Between landing and that sync nothing misbehaves, because `sq check`'s backend reconciliation probes only the always-present top-level managed files and never per-entry files, so a lingering pointer is not reported and nothing fails.

No currency check is added to `sq check`. A projection mismatch — a live entry with no file, a retired entry with one — is exactly the class of drift ADR-141 §4 deliberately scoped out, since currency would require each backend to re-render and diff its managed content. Sync stays the tool that fixes it; the door stays open for a currency check later without changing anything decided here.

Done when sync converges an entry in either state on every run and is a no-op on the second run.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Accept only a live slug where a participant is written

<!-- sq:subtask:ST5:body -->
A retired entry stops being **offered** while its history stays intact. Those are two different questions and must be answered differently, or the board rots.

The entry points that *write* a participant — `--as`, `--author`, `--assignee` on create/comment/update — accept only a live slug. That is what "stops being offered as an active participant" means operationally. `resolve_slug_or_raise` in `_cli/_common.py` already reads `svc.roster()` and `svc.operators()`, so the gate falls out of the projection split: confirm that and cover it rather than adding a second gate on top.

`agent_registered` keeps validating against the **full** roster vocabulary. The question it asks is "was this a registered participant", not "is it live now" — an item authored by a role retired a year later must not start reporting a warning it cannot fix.

The bulk importer is exempt from the live-slug gate. It replays history, and history is full of participants who have since retired; it keeps the registration check only.

Done when a retired slug is rejected with a clean error at every write entry point, no existing item starts warning, and an import naming a retired participant still replays.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Cover both directions, the fan-out and the wrong projection

<!-- sq:subtask:ST6:body -->
Service level plus a CLI smoke per surface, named by behaviour. No ticket ID in any file name, test name or source comment.

Service — a new module for the predicate: materialise, withdraw, reactivate, and the per-caller projection audit. `tests/service/test_active_role_roster_listing.py` is the right home for the `roster()` / `roster_all()` split, beside the existing listing behaviour.

Integration — `tests/integration/test_backend_lifecycle_contract.py` for the ABC-level obligations (missing-tolerant, idempotent withdrawal against an unscaffolded backend); `tests/integration/test_multi_active_backends.py` for the fan-out and the removed-backend-untouched asymmetry; `tests/integration/test_claude_code_backend.py` and `test_agents_md_backend.py` for the compiled-region exclusion, the default-role line and the developer-gated skill text.

CLI — `tests/cli/test_roster_type_address_verbs.py` for a retirement's observable effect, and the existing author/assignee coverage for the live-slug gate.

The goldens will move, because a withdrawal changes generated prose. Review each diff rather than blanket-regenerating, and hold the roster constant while diffing generated skill text — the `sq-<type>` skill body is roster-dependent, so comparing a developer-less squad against a developer-bearing one reads as a false regression.

Falsify the projection split specifically: swap a full-set caller to the active-only projection, assert a test catches it, restore it, and watch it pass. ADR-697 names this the part of the contract most in need of tests that assert the *wrong* projection fails. Falsify each direction of the projection the same way and report both.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T10:09:22Z] Olivia Lead:
  - ADR-696 and ADR-697 were both amended after this task was cut, and ADR-697's §1 predicate is now ADR-696 §2a's `offered` flag. Body left as written; read this comment alongside it. TASK-703 carries the reshape and blocks this task.
  - The projection predicate: where this body says an entry is materialised iff "its status resolves to the live role" and that liveness is `role_statuses(item_type, "active")`, read the offered-statuses predicate instead. An entry is materialised iff its status carries `offered`. Every unoffered status is unmaterialised, whatever its role is called and whether or not that role is settled — the flag is the whole test.
  - Do not substitute non-settled for the flag. Four bundled roles are non-settled (`active`, `attention`, `blocked`, `pending`), so an adopter's `Suspended` on `blocked` or `Provisional` on `pending` would be read as offered and written into the agent host's config. That was checked and rejected on the evidence, not assumed.
  - R1 relaxes to "at least one offered status", so several may be offered. The projection does not care — it reads the flag per entry — but anything reporting on the roster must show the status rather than a yes/no, because "which status does an offered entry hold" stops having a single answer.
  - @python-dev sequence behind TASK-703.
- [2026-07-30T14:52:19Z] Elias Python:
  - Landed ST1-ST6. roster()/operators() -> offered-only; roster_all()/operators_all() added. candidate_orphans, author()/_author_of, registered_slugs, sq role|operator list confirmed already full-set (author()/registered_slugs never went through roster()/operators() at all — no change needed there); candidate_orphans DID need fixing (was feeding roster() + an offered-only skill map into the orphan scan).
  - Caller-audit finds the table didn't name: resolved_skills_for_role/_role_skills_map (offered, gates the pointer regen — fixed), _resync_role_skills's post-link/unlink generate_role_entry call (was unconditional, would've resurrected a retired role's pointer on a skill scope edit — gated on offered), and three roster() callers whose correct projection is neither pole: sq list/tree --assignee, sq mine, sq inbox are reads/filters (not --as/--author/--assignee writes) so they need the FULL roster, not offered-only — resolve_slug_or_raise gained an offered_only kwarg (default True for the write sites) rather than a second gate.
  - Bigger gap: sq create <type> --author/--assignee never called resolve_slug_or_raise at all (relies solely on the status-blind _is_participant check) -- a retired role could still author new items post-retirement. Added the same offered-only gate to all three create builders (_build_create_cmd, _make, create_guide).
  - Also gated activate_role/add_dev/add_skill's own generate_role_entry/generate_skill_entry calls on offered status (they were unconditional before -- ADR-696's unoffered-initial 'parked' roster entry would otherwise have materialised on creation).
  - Falsified every new test: set_status's projection hook, candidate_orphans's roster_all(), sync()'s offered gate, the roster()/roster_all() split, the fan-out loop, refresh_managed()'s roster()/operators() feed, the create --author/--assignee gate, and the mine/inbox/list --assignee full-set exemption -- each went red on the reverted code and green on restore.
  - sq check clean on this repo. No regressions: diffed a full tests/cli+service+integration+unit sweep against clean HEAD -- identical 390 pre-existing failures both with and without my changes (a prior 'author is required' change already on this branch broke those independently of this task; flagged for Pierre, not touched here).
  - Task body predates the offered-flag amendment throughout -- every 'active role'/'live' phrasing in the body means the offered predicate; I implemented against the amendment comment and ADR-697/696, not the stale body wording.
<!-- sq:discussion:end -->
