---
id: FEAT-691
sequence_id: 691
type: feature
title: 'CLI: expose the roster''s Draft/Active/Archived lifecycle'
status: Done
author: product-owner
refs:
- TASK-688:addresses
- PRD-860:implements
- PRD-861:implements
description: Give role/skill/operator a status verb so the roster's Draft/Active/Archived
  lifecycle is actually reachable
subentities:
- local_id: US1
  title: As a manager, I can set a role's/skill's/operator's status from the CLI
  status: Done
- local_id: US2
  title: As a maintainer, the status verb keys off declared roles, not names
  status: Done
- local_id: US3
  title: As a team, the generated CLI help and skill text teach the new verb
  status: Done
- local_id: US4
  title: As an operator, retiring a roster entry withdraws it from generated backend
    config
  status: Done
- local_id: US5
  title: As an operator, retiring a still-depended-on roster entry is refused, with
    a remedy
  status: Done
- local_id: US6
  title: As a team, sq check reports a roster entry already in a broken config state
  status: Done
created_at: '2026-07-29T13:13:44Z'
updated_at: '2026-09-01T13:51:19Z'
---
<!-- sq:body -->
Role, skill, and operator each carry a real three-state lifecycle in the workflow spec —
`machine_for("role")`/`machine_for("skill")`/`machine_for("operator")` all resolve to a
working `Lifecycle` with transitions, and the generic status-transition core
(`Service.set_status`) is already type-agnostic — it drives off the spec's declared
machine for whatever type it's given, no roster-specific branch needed. What is missing is
purely a CLI seam: `sq role`, `sq skill`, and `sq operator` never register a `status` verb
on their addressed subgroups (the same one every work-item type gets via `_cmd_status`), so
there is no command that can move a roster entity off its initial status at all. `sq role
<slug> --help` (and the skill/operator equivalents) show only `show`/`regen`/`rm`.

## Why it matters

A project's own roster entries have no way to progress through their lifecycle from the CLI:
a role/skill/operator that should retire (an agent that's no longer used, a skill that's been
superseded) has no path to `Archived`. Roster entries are created `Active` and the bundled
lifecycle has no edge back into `Draft`, so `Archived` is the reachable target this closes.
The gap is not hypothetical: the 0.12.3 VS Code Roster view already ships
hide-archived-by-default and a status filter (TASK-688) — a project can now filter and hide
roster entries by status in the UI with no CLI command able to set that status in the first
place. Every custom lifecycle a project declares for its roster types has the identical
problem; this is not just about the bundled three statuses.

## Capability

Add a `status` verb to the addressed `role`/`skill`/`operator` subgroups (`sq role <addr>
status <S>`, mirroring `sq task <n> status <S>`), wired onto the same generic
`Service.set_status` core work items already use. No new engine logic — the lifecycle
machinery, transition validation, and frontmatter write path already work for any type the
spec declares; this closes the CLI registration gap, nothing more.

Must not hardcode the bundled `Draft`/`Active`/`Archived` names as the allowed target set:
validity comes from the type's own declared lifecycle (`WorkflowSpec.can_transition`), so a
project that renames or extends the roster lifecycle gets the same command for free, with its
own statuses and transitions enforced exactly as they are for every other type today.

## Acceptance criteria

- `sq role <slug|id|n> status <S>`, `sq skill <slug|id|n> status <S>`, and `sq operator
  <slug|id|n> status <S>` exist and transition the entity's frontmatter `status`, rejecting a
  transition the type's declared lifecycle does not allow (same behavior/error shape as the
  work-item `status` verb, including `--force`).
- The allowed-transition set is read from the spec (`machine_for`/`can_transition`) for
  whichever type is addressed — never a literal `Draft`/`Active`/`Archived` check.
- `sq check` and the generated `.claude`/`AGENTS.md` help/skill text stay accurate for the new
  verb (roster items are otherwise unchecked by `sq check`'s work-item rules, so this only
  needs the command itself to be correct and discoverable).
- Existing `show`/`regen`/`rm`/`list`/`activate`/`add` behavior for role/skill/operator is
  unchanged.
- A roster entity moved to `Archived` (or any hidden-by-default status) is picked up correctly
  by clients already reading that state, e.g. the VS Code Roster view's hide-archived/status
  filter (TASK-688), `sq role list`/`sq operator list`, and `sq list -t skill`.

## Out of scope

TASK-688's discussion separately noted that `sq workflow types --json`/`roles --json` expose
no type→lifecycle→states mapping, so a client cannot ask "what statuses can THIS type reach"
and instead has to fall back to the whole spec's status list (as both the VS Code extension
and `sq ui`'s own filter screen do today). That is a real gap, but it is a read/introspection
concern that already has an established, working fallback precedent on both existing clients
— distinct from this feature's gap, which is that no command exists at all to change a roster
entity's status. It is out of scope here so this feature stays scoped to the missing verb.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 691 add-story "As a <role>, I want … so that …"`; track with `sq feature 691 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a manager, I can set a role's/skill's/operator's status from the CLI

<!-- sq:story:US1:body -->
sq role/skill/operator <addr> status <S>, wired onto the existing generic set_status core; transitions validated against the type's own declared lifecycle, not a hardcoded roster name set; --force works the same as it does for work items.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a maintainer, the status verb keys off declared roles, not names

<!-- sq:story:US2:body -->
Delivered by TASK-695/ST3: `sq role|skill|operator <addr> status <S>` reads its allowed targets
from `WorkflowSpec.machine_for`/`can_transition` for whichever type is addressed — no
`Draft`/`Active`/`Archived` literal and no `STATUS_*` import anywhere in the verb. That holds
today for every declared type, roster included, and is proven structurally (no literal in the
code) plus by the per-type error-text enumeration.

The other half of the original promise — a project renaming or extending the roster lifecycle
itself and getting this same command "for free" against *that* lifecycle — does not hold yet.
The workflow-override loader still refuses any override that redefines a built-in type or
lifecycle, so `role`/`skill`/`operator` cannot be rebound today. ADR-696 decides that
restriction lifts (per-field shadowing, validated against the roster floor: exactly one
`active`-role status, at least one reachable settled non-`active` status) — but the lift itself
is not implemented, and no task under this feature cuts it. This story cannot be proven
end-to-end against a renamed roster lifecycle until that lands.

Recommendation: the override lift is a workflow-spec-loader change reaching every item type's
lifecycle, not a CLI concern scoped to the roster status verb — it does not belong as a story
under this CLI-scoped feature. It should be scheduled as its own feature once prioritized,
tracked separately from FEAT-691.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a team, the generated CLI help and skill text teach the new verb

<!-- sq:story:US3:body -->
sq role/skill/operator --help and the regenerated .claude/AGENTS.md surfaces mention status alongside show/regen/rm; no change needed to sq check itself (roster items are outside its work-item rules).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an operator, retiring a roster entry withdraws it from generated backend config

<!-- sq:story:US4:body -->
Per ADR-697 §1-6, §10-11: a materialised roster entry is a pure projection of its frontmatter,
the active workflow spec, and the active backend list — never a second source of truth, never
migrated. An entry is materialised iff its status resolves to the `active` role; every other
role is unmaterialised. This story is the projection itself: writing it, withdrawing it, and
feeding it from the right roster view. Reference ADR-697 for the mechanism; do not restate it
here.

## Acceptance criteria

- Moving a role/skill entry's status to a status whose role is `active` materialises it: its
  own backend file(s) exist, and it is included in every managed region a backend compiles
  (the roster table, the default-role line, the developer-gated per-item-type skill text, a
  role's resolved skill-preload list).
- Moving it to any other status withdraws it: its own file(s) removed via the existing
  `remove_artifacts`, and it is excluded from every one of those same managed regions.
- Reactivating a withdrawn entry regenerates it in full — same call path as first creation, no
  partial-repair path.
- Both directions fan out over every deduped entry of `active_backends`, in the existing
  order-insignificant way; a backend absent from that list is left untouched (its stale files,
  retired entries included, stay exactly as they were).
- `Service.roster()` / `Service.operators()` return active-only entries (status role `active`)
  and are what `write_managed` and skill-preload resolution consume.
- `Service.roster_all()` / `Service.operators_all()` are added and return every entry regardless
  of status; used for authorship display-name resolution, the `agent_registered` check,
  `sq role list` / `sq operator list` / `sq list -t skill`, and as `candidate_orphans`' input
  (the full roster + skill-slug vocabulary, never the active-only projection — a withdrawn
  entry's leftover file is squads' own convergence debt, not a foreign file).
- `sq sync` applies the same materialise/withdraw predicate to every roster entry on every run,
  including one already sitting in a non-active status before this change ships — no migration,
  no schema bump; it converges silently on the next sync.
- No new currency check in `sq check` for this projection (ADR-697 §6) — its present-only
  backend reconciliation is unchanged.
- The interactive `--as` / `--author` / `--assignee` entry points accept only a live (active-role)
  slug. `agent_registered` and the bulk importer keep validating against the full roster
  vocabulary regardless of current status — an item authored by a now-retired role must not
  start reporting a warning it cannot fix.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy

<!-- sq:story:US5:body -->
Per ADR-697 §7-9: retiring a roster entry is refused when it would leave a generated config
structurally invalid for an active backend. This is the transition-time gate — BUG-698's
missing "refuse it" half. Reference the ADR for the reasoning; specify only the observable
behaviour here.

## Acceptance criteria

- **C1 — last live role.** Retiring the only role whose status resolves to `active` is refused
  whenever `active_backends` is non-empty, and allowed when it is empty.
- **C2 — default role.** Retiring the role carrying `is_default` is refused unless another live
  role already carries it.
- **C3 — a still-depended-on skill.** Retiring a skill still named by a live role's resolved
  preload list is refused: whether by a stored `scopes` edge, by system membership, or by a
  declared item type's `sq-<type>` implication.
- `--force` overrides only the lifecycle's own transition edge; it never overrides C1/C2/C3.
  Every refusal names the specific remedy available for that clause.
- `--unlink` (offered only for a `roster`-category type's `status` verb):
  - severs the stored ref edges that constitute a **tier-1** C3 dependency (a custom skill's
    `scopes` edge to a role), then re-evaluates every clause, unforced, against that prospective
    state — a transition still refused after severing aborts the whole transaction, so a
    refusal can never leave a partially-severed squad;
  - reports each severance (the referring role, the skill, the ref kind) and reflogs it, one
    entry per severed edge plus the status change;
  - on a retirement with nothing severable: reports a no-op and proceeds;
  - on a transition that is not a retirement: refused as meaningless;
  - never touches a **tier-2** (type-implied `sq-<type>`) or **tier-3** (the always-on
    `squads`/`greeting`/`sq-memory` trio, or any bundled `sq-<type>` skill until the playbook
    resolves per-request against the active spec) dependency — those keep refusing regardless
    of the flag. The refusal names the implicating type(s) for tier 2 (capped and summarised
    when there are many) and states the permanent-floor rule for tier 3, offering no remedy
    where none exists.
- The whole evaluation runs in the pure, pre-write half of the status transition, against the
  transaction's own snapshot, so the bulk importer's replay is held to the same rule at each
  step of history it replays.
- Retiring the last **operator** is never refused (an empty operator list is legitimate).
- A retiring role that still holds open assigned work warns and proceeds; board hygiene is not
  a config-integrity concern.

## Note for the cutting task

This is also BUG-698's fix for its gate half. A task cut from this story should reference
BUG-698 so the two stay linked.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As a team, sq check reports a roster entry already in a broken config state

<!-- sq:story:US6:body -->
Per ADR-697's consequences: C1-C3 gate *transitions*, they cannot see a squad already sitting in
the state they would have refused. A squad transitioned before the gate existed — or one an
adopter reaches some other way — keeps the invalid state, and `sq sync`'s convergence sweep
faithfully projects the breakage (e.g. a retired system skill's files withdrawn while every
role's generated entry still preloads it). This is BUG-698's second, separate gap: the reporter.

## Acceptance criteria

- A `sq check` validator (report-mode, not a transition gate) flags a roster entry currently in
  a non-`active` status while still depended on by any of C1-C3's criteria as they'd apply to a
  fresh transition: the last live role for a non-empty `active_backends`, a non-live `is_default`
  role, or a non-live skill still named by a live role's resolved preload list.
- Each finding names the same specifics a transition-time refusal would: the dependent
  entity/entities and, where the dependency is a `sq-<type>` implication, the implicating
  type(s) (capped/summarised as C3's own enumeration is).
- Findings surface through `sq check`'s existing collected-report shape — one line per issue,
  same severity/exit-code convention as its other checks — not a separate command.
- Verified against BUG-698's own repro: a fresh squad where `sq skill squads status Archived`
  was accepted before the gate existed is caught by this validator afterwards.
- This closes BUG-698's reporter gap; a task cut from this story should reference BUG-698 and
  can land independently of US5's gate — the ADR is explicit the two are separate needs.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T13:14:30Z] Pierre Chat:
  - Scheduled for 0.13.
- [2026-07-29T14:45:14Z] Olivia Lead:
  - Broken down into TASK-695 (one task, six subtasks mapped to US1/US2/US3). Left in Draft for the dispatch gate.
  - @product-owner three acceptance-criteria corrections. (1) `sq skill list` does not exist and deliberately so — docs/stability.md says the skill type has no dedicated list verb; the equivalent is `sq list -t skill`. (2) Nothing in the generated `.claude`/AGENTS.md surfaces enumerates the roster addressed verbs today (no `sq-role` skill exists, and the CLAUDE.md region only cites `sq role <slug> show` for impersonation), so US3 reduces to `--help`/epilogs plus the adopter docs — I scoped it that way rather than adding new roster grammar to the managed templates. (3) US2 cannot be proven end-to-end against a renamed roster lifecycle: the workflow override loader is additive-only and refuses to redefine a built-in type or lifecycle, so an adopter cannot rebind role/skill/operator today. The task proves it structurally (no status literals) plus via the per-type error enumeration.
  - Also worth a separate decision, not folded in: roster items are created `Active` and the bundled lifecycle has no edge back into `Draft`, so the body's "parked Draft and picked up later" scenario stays unreachable without `--force` even after this lands. And `Service.roster()`/`operators()` ignore status, so an Archived role keeps its `.claude` pointer, its CLAUDE.md roster row, and its validity as an `--as`/`--assignee` slug.
- [2026-07-29T14:47:01Z] Catherine Manager:
  - Corrected two factual errors the breakdown found: the acceptance criteria cited a non-existent 'sq skill list' (docs/stability.md is explicit that skills have no dedicated list verb — 'sq list -t skill' is the equivalent), and the Draft-parking rationale was unreachable since roster entries are created Active with no lifecycle edge back to Draft. Archived is the target this closes.
- [2026-07-29T14:50:17Z] Pierre Chat:
  - Fold the archive-semantics work behind this feature: an Archived roster entry must stop being offered as an active participant (roster()/operators() status-awareness, the .claude pointer, the CLAUDE.md roster row, --as/--assignee validity). Not a separate feature.
  - The roster is locked: role/skill/operator keep their built-in lifecycles and are not adopter-customisable. We do not need custom roster lifecycles. US2's promise ('a custom roster lifecycle gets the same command for free') is therefore void and needs reframing — the no-status-literals implementation constraint stands on engine-hygiene grounds, not adopter customisation.
- [2026-07-29T15:06:27Z] Pierre Chat:
  - Reversing the lockup: constrain, don't lock. The roster lifecycle stays customisable and the engine keys off the declared status roles (active/retired), not the literal status names.
  - The principle behind it: squads must not break when a project's customisation is too loose. That holds for every item type — the engine must validate the minimum semantics it depends on rather than trusting a spec. The roster is the special case because its entries are materialised into the agent hosts' own files (Claude Code today, Copilot and Codex later), so a loose roster spec breaks the generated backend config, not just an sq view.
- [2026-07-29T15:19:49Z] Robert Architect:
  - Authored two decisions for the remaining archive-semantics work: ADR-696 (the general rule — engine keys off declared status roles, loader enforces a per-capability floor, workflow overrides may shadow built-ins under validation) and ADR-697 (the roster-as-backend-projection contract — active means materialised, anything else withdrawn, both through the existing AgentBackend methods).
  - Split because they sit on different planes: ADR-696 is spec-load validation and applies to every type; ADR-697 is the runtime materialisation seam and only concerns the roster. ADR-697 builds on ADR-696.
  - ADR-696 lifts the additive-only override restriction — without it 'constrain, don't lock' is unreachable for the roster, since no adopter can rebind role/skill/operator to a renamed lifecycle at all. Shadowing becomes per-field merge, validated; only the three roster type keys and their fixed category stay prohibited. This narrows ADR-541's type-axis floor.
  - The non-disablable rule is a derived transition-time invariant, not a per-entry 'required' flag: a retirement is refused when the resulting projection would break an active backend's config (last live role, the is_default role, a still-referenced skill). A flag would store a derivable fact and could not catch the last-live-role case at all.
  - One refinement to the framing, flagged rather than assumed: the engine needs only the 'active' role by name. Retirement and default-hiding are consumed through the role object's settled/hidden flags, so requiring the names 'retired'/'pending' would re-import name-locking one level up. Both stay in the bundled spec.
  - @manager both left Proposed for op-pierre to read and accept; sq check clean, nothing committed.
- [2026-07-29T16:34:24Z] Nina Product:
  - US2 rewritten: it now states only what TASK-695/ST3 delivered (no literal roster status name anywhere in the new verb; targets derived per-type from the spec). The adopter-facing half — a project rebinding role/skill/operator to a renamed lifecycle and proving this verb against it — waits on ADR-696's override-loader lift, which is decided but not implemented and has no task under this feature.
  - Recommendation: that lift is a workflow-spec-loader change reaching every item type, not a CLI concern scoped to this feature's status verb. I judge it belongs in its own feature once scheduled, not folded into a story here — flagging before creating anything.
- [2026-07-29T16:34:34Z] Nina Product:
  - Ruling on the decorative Draft roster status (ADR-696/697): drop it from the bundled role/skill/operator lifecycle. Nothing in the bundled spec ever transitions into it, every roster-create verb writes the active status directly, and this repo's own squad has zero roster items sitting at Draft — it is unreachable vocabulary shipped for a 'parked, picked up later' scenario this same investigation already found dead. Collapsing the bundled roster lifecycle to Active/Archived satisfies R1/R2 trivially (Active is the sole active status, Archived is the one reachable settled status) and matches the two-role model (active/retired) ADR-697 actually drives off.
  - An adopter who wants a pre-active provisioning state can declare one themselves once the ADR-696 override lift lands — dropping it from the bundled default doesn't remove that option, it just stops shipping dead vocabulary as the default.
  - Migration flag, not decided around: Draft is reachable today via --force (Active/Archived -> Draft), so a squad could in principle already have a roster item stamped Draft. Dropping the status from the bundled spec needs a pre-flight check across existing squads (validate_against_index would fail-closed on load if any live roster item holds it) and, if any are found, a migration remapping them to Active before the status is removed — this is implementation work for whoever picks up the drop, not something I'm deciding around.
- [2026-07-29T16:39:59Z] Pierre Chat:
  - Confirmed: drop Draft from the bundled roster lifecycle, collapsing to Active/Archived, including the pre-flight check and remap for any existing squad holding it via --force.
  - Confirmed: the ADR-696 override lift gets its own feature rather than a story here — it is a spec-loader change reaching every item type.
- [2026-07-30T07:53:10Z] Olivia Lead:
  - Broken down US4/US5/US6 into four tasks, all left in Draft for the dispatch gate: TASK-699 (spec-semantics foundation + the confirmed Draft drop, no story), TASK-700 (US6, the sq check reporter, urgent), TASK-701 (US5, the C1-C3 gate + --unlink), TASK-702 (US4, the backend projection). Serial chain 699 → 700 → 701; 702 runs parallel with 700 after 699. Recorded as depends-on edges, so sq blocked shows the order.
  - TASK-699 is an addition to the three stories, not a restatement of them: ADR-696 §2's role-keyed accessors (role_statuses / sole_role_status) do not exist yet — _RESERVED_FLOOR and the three STATUS_* literals are still live across nine call sites — and every one of US4/US5/US6 is specified in terms of 'the status resolves to the active role'. Without it each of the three would grow its own liveness predicate. Its scope is ADR-696 §2/§3/§5 only; the §4 override lift stays out, per the ruling that it gets its own feature.
  - TASK-700 owns the C1-C3 clause predicates and TASK-701 consumes them, rather than each deriving its own. That is why the reporter is first in the chain as well as first in priority.
  - @python-dev the Draft-drop migration tail is settled and needs no migration runner — two load-path facts, both verified in code and both written up as assertions on TASK-699/ST6: validate_against_index tests the spec's global status set (the dropped name stays declared for work and guide) and only runs at all when a workflow override file is present, so nothing hard-stops; and _apply_status with force=True skips the edge check, so an item at a no-longer-declared status is remappable in place. The residue is one item_status_valid error per affected item in sq check. Assert both rather than trusting the write-up.
- [2026-07-30T07:57:44Z] Pierre Chat:
  - All three archive stories (US4/US5/US6) stay in 0.13 — the verb and its guards ship together, so no adopter sees the unguarded intermediate state.
  - Dropping the bundled Draft roster status also ships in 0.13, with FEAT-691.
- [2026-07-31T09:40:02Z] Olivia Lead:
  - Four tasks cut against REV-706, all Draft: TASK-707 (the clause family and its enforcement), TASK-708 (the projection path), TASK-709 (the adopter-facing changelog and docs), TASK-710 (the is_default designation verb). US4 and US5 are the two the review judged not met; 707 and 708 are what close them, and 709 carries the US3 gap on --unlink.
  - TASK-710 is parented here on purpose — same surface (sq role <addr>), its spec is ADR-697 §9, and every other roster-verb task already hangs off this feature, so the decision-to-task trail stays one hop. It maps to no story: US1-US6 do not cover designation, so it must not be counted against this feature's acceptance and does not gate 0.13. That leaves a Draft child under a feature heading for Done — either close this feature with an explicit note that 710 rides the next roster increment, or reparent it then. Do not let it close silently.
- [2026-07-31T09:54:23Z] Pierre Chat:
  - TASK-710 (the is_default designation verb) stays in this feature and ships with it — it is small enough not to warrant its own increment. The feature closes when it is done too, not before.
- [2026-07-31T11:49:05Z] Olivia Lead:
  - US5 moved back off Done: two of its criteria are unmet as shipped. The delta comparison still refuses a transition that strictly reduces a pre-existing violation (the importer replay too), so the pure pre-write rule is not satisfied; and the scoped-edge remedy names --unlink on a reactivation, where the command rejects it, so the every-refusal-names-a-remedy criterion fails in that direction. TASK-711 carries both, mapped to this story.
- [2026-07-31T12:41:57Z] Catherine Manager:
  - Closing: all six stories meet their acceptance as written per the reviewer's round-three verdict, all eleven tasks are Done, the batch review is Approved by a second party, and the defect this feature exposed is Verified. Non-visual work, so accepted directly rather than held for an operator pass; two low findings stay open on the review as recorded follow-ups.
<!-- sq:discussion:end -->
