---
id: FEAT-902
sequence_id: 902
type: feature
title: 'Squad-global validators: parent outcomes, cycles, WIP, staleness'
status: Done
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
- FEAT-901
- ADR-982:implements
description: Five opt-in squad-wide checks from ADR-864 Part 2, selected in the workflow
  document's squad validators list
subentities:
- local_id: US1
  title: 'children_settled_with_parent: flag a settled parent with open children'
  status: Todo
- local_id: US2
  title: 'dependency_acyclic: flag a cycle among dependency edges'
  status: Todo
- local_id: US3
  title: 'wip_limit: flag an assignee over a declared active-item cap'
  status: Todo
- local_id: US4
  title: 'unassigned_active: roll up unassigned active items into one line'
  status: Todo
- local_id: US5
  title: 'stale_active: flag an active item untouched for n days, via the injectable
    clock'
  status: Todo
- local_id: US6
  title: As a squad, I want to select squad-global checks in one list
  status: Todo
created_at: '2026-09-03T09:02:36Z'
updated_at: '2026-10-16T21:01:59Z'
---
<!-- sq:body -->
## Why

Five squad-wide checks named in ADR-864 Part 2, each opt-in, none bundled by default. One of
them names a failure this team has already hit more than once.

## Scope (selectable squad-global members; warn by default)

- `children_settled_with_parent` -- a parent at a settled status with open children. **For
  everyone, and specifically for the failure this team has hit repeatedly**: a parent closed
  against its children rather than against its outcomes. EPIC-538 went Done with three unbuilt
  features and the design got re-derived weeks later.
- `dependency_acyclic` -- a cycle among dependency-role edges, which `sq blocked` would
  otherwise render as a permanent mutual block.
- `wip_limit:<n>` -- more than *n* active items for one assignee (an active item is a
  work-category item at a status whose role is live). Explicitly
  not for this squad (we run one agent per role, not kanban WIP discipline) -- named as the
  clearest example of the tier: a real check, nobody's defect, wrong to bundle.
- `unassigned_active:<n>` -- the roll-up of the per-item `assignee_present` check (FEAT-901):
  one finding when more than *n* active items have nobody assigned, for a board owner who
  wants one line instead of fifty.
- `stale_active:<days>` -- an active item untouched for *n* days. **Admitted
  with one binding condition**: the time it measures against is the injectable clock the rest of
  the codebase already uses, read once per run, and it is **never bundled** by default for any
  squad -- so `sq check` stays deterministic between two runs over an unchanged corpus unless a
  squad has knowingly selected it.

Statuses are matched by the flag the status's role declares (`live` for active, `settled` for
settled), edges by the role their kind declares (dependency), never by a name. An active item is
an item of a `work`-category type at a live status: roster and records items are not counted, since
the bundled `Active` status is live and is where every role, skill, operator and contract rests.
A selection that the spec's own declarations make unable to fire is refused at spec load: see the
surface story.

## Selection surface

A squad selects these members in a `[squad]` table of the workflow document, key `validators`:

```toml
[squad]
validators = ["children_settled_with_parent", "wip_limit:3", "stale_active:30@error"]
```

- The grammar and the parser are the ones a type's `[items.<type>] validators` list uses:
  `name`, `name:param`, `name@level`, `name:param@level`. `[items.task] validators` is what the
  task type runs; `[squad] validators` is what the squad runs.
- The bundled document ships the list empty. A squad selects in its `.overrides/workflow.toml`; the
  list is replaced whole by an override, and `"$(*squad.validators)"` extends the bundled one.
  `[selected]` does not accept `squad`.
- Two tiers at squad scope. The five squad-global checks that exist today (index, backend and
  roster-config reconciliation, duplicate default designation, playbook guide roles) are
  **always-on**: they run in every squad and cannot be named in the list. The five above are the
  **selectable** tier.
- Every squad-global member, always-on included, has one declared default level; a selected
  member reports at its selection's level and otherwise at its default. Always-on members keep
  the levels they have today.
- At this scope `@error` changes only whether `sq check` exits non-zero. Squad-global members
  never run at the create/update gate, so a level never refuses a write -- unlike a per-item
  `@error`, which does.
- A finding's `item` is an item id when it concerns exactly one item, and empty otherwise, with
  the subjects named in the message. An assignee slug is never written there.
- Staleness is measured per squad: one `stale_active` threshold for the whole squad.

## Engine delivery and this project's selection are separate

This feature delivers the `[squad]` table and the five members, proven on scratch squads and in
tests, including a scratch copy of this repository's squad with the override extended there.

Writing this project's selection into this repository's own `squads/.overrides/workflow.toml` is
**not** part of the feature. Constraint: that file is read by the released tool (0.15.0) for as long
as that tool operates this board, and the released tool refuses a top-level key it does not know --
with a `[squad]` table in the file, `sq check` exits 3 and every other command exits 1, for
everyone. The table can only be written there once the squad is migrated and the board runs on the
new build. That is a step of release preparation, stated below.

## Release-preparation acceptance for this repository

Done by the manager at release preparation, **after the operator has migrated this repository's
squad** (the operator's step, once, after every contributor has amended the migration) and the board
runs on the new build:

- `squads/.overrides/workflow.toml` carries a `[squad]` table whose `validators` list is exactly
  `children_settled_with_parent` and `dependency_acyclic`. `wip_limit`, `unassigned_active` and
  `stale_active` are not selected (the stories say why).
- A bare `sq check` on this repository is clean afterwards: the settled parents with open children
  and the dependency cycles are counted on the migrated squad first; each one is fixed in the same
  step (a parent whose children are really unbuilt outcomes is reopened or given a home item), or
  its count is raised to the operator before the selection lands.
- `sq workflow lint` reports the override valid on the new build.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 902 add-story "As a <role>, I want … so that …"`; track with `sq feature 902 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — children_settled_with_parent: flag a settled parent with open children

<!-- sq:story:US1:body -->
As a team that has closed a parent against its children rather than its outcomes before, I want a settled parent with open children flagged, so an unbuilt outcome can't vanish silently the way EPIC-538 did with three unbuilt features.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project's own selection, where it makes one, is the release-preparation step in the feature body, not part of this feature); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Fires once per parent item whose status resolves to a role declaring settled = true while at least one child item (an item whose parent is it) is at a status whose role does not; the message lists the open children. The finding's item is the parent's id.
- Applies to any parent type, not only epic/feature/task; sub-entities (stories, subtasks, findings) are not children for this check.
- Silent when every child is settled (cancelled counts as settled), silent for a parent with no children, silent for an open parent.
- On a scratch copy of this repository's squad with the override extended there, selecting it flags a settled parent that still has open children and leaves the repository's own override untouched.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — dependency_acyclic: flag a cycle among dependency edges

<!-- sq:story:US2:body -->
As a team using dependency edges, I want a cycle among dependency edges flagged, since sq blocked would otherwise render it as a permanent mutual block with no way out.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project's own selection, where it makes one, is the release-preparation step in the feature body, not part of this feature); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Considers only edges whose kind declares the dependency role (blocks and depends-on in the bundled spec), after orienting each by its declared direction; a cycle of related or targets edges is not reported.
- Test shapes: a two-item cycle, a three-item cycle, one item blocking itself, a diamond (no cycle, no finding); a chain mixing blocks and depends-on that closes on itself.
- One finding per cycle; its item is empty and the message names the items on the cycle; terminates on any graph.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — wip_limit: flag an assignee over a declared active-item cap

<!-- sq:story:US3:body -->
As a team running a kanban discipline, I want to declare a WIP cap per assignee and be warned when it's exceeded.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project's own selection, where it makes one, is the release-preparation step in the feature body, not part of this feature); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required positive-integer parameter, wip_limit:<n> (a bare or malformed entry is refused at spec load; see the surface story).
- Fires once per assignee holding more than n active items (a work-category item at a status whose role is live); an assignee at exactly n is clean; items with no assignee are not counted here; settled and non-active items are not counted. The finding's item is empty; the message names the assignee and the count, and no assignee slug is written in the item field.
- Explicitly not selected in this project's own override -- named as the clearest example of a real check that is nobody's defect and would be wrong to bundle.
- Test rows: a role item and a contract item at Active are not counted; a project role declaring live = true under another name is counted; a role named active that declares live = false is not.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — unassigned_active: roll up unassigned active items into one line

<!-- sq:story:US4:body -->
As a board owner, I want one roll-up line for how many active items are unassigned, instead of reading fifty individual assignee_present warnings.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project's own selection, where it makes one, is the release-preparation step in the feature body, not part of this feature); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required non-negative-integer parameter, unassigned_active:<n> (zero is valid; a bare or malformed entry is refused at spec load). Fires once when MORE THAN n active items (work-category items at a status whose role is live) have no assignee; at n or fewer it is clean, so unassigned_active:0 flags any unassigned active item.
- The finding's item is empty; the message states the count and names at most the first few items.
- Independent of the per-item assignee_present check: a squad may select either, both or neither.
- This project does not select it.
- Test rows: a role item and a contract item at Active are not counted; a project role declaring live = true under another name is counted; a role named active that declares live = false is not.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — stale_active: flag an active item untouched for n days, via the injectable clock

<!-- sq:story:US5:body -->
As a team running a long-lived board, I want an active item untouched for n days flagged.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project's own selection, where it makes one, is the release-preparation step in the feature body, not part of this feature); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required positive-integer parameter, stale_active:<days> (a bare or malformed entry is refused at spec load).
- The engine reads the injectable clock once per run and every item in that run is measured against that same instant; the member itself calls no clock. A test freezes the clock and proves an item untouched for days+1 days warns while one untouched for exactly days days is clean, and that two items checked in one run are measured against the same instant.
- "Untouched" is measured from the item's updated_at timestamp; this feature does not change what bumps it. The finding's item is the stale item's id.
- Never bundled by default for any squad, so sq check is deterministic between two runs over an unchanged corpus unless a squad has knowingly selected it; a test proves two runs over an unchanged corpus with nothing selected agree.
- One threshold applies to the whole squad. This project does not select it.
- An item is active when it is a work-category item at a status whose role is live (a role declaring live = true), never by a role name. Test rows: a role item and a contract item at Active are not measured; a project role declaring live = true under another name is; a role named active that declares live = false is not.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As a squad, I want to select squad-global checks in one list

<!-- sq:story:US6:body -->
As an adopter, I want to name, level and parameterise squad-wide checks in one place, so I choose which policies my squad enforces and how loudly, without the checks every squad needs ever being switchable.

Acceptance:
- The workflow document accepts a [squad] table with one key, validators, a list of entries in the same grammar as a type's validators list (name, name:param, name@level, name:param@level). Any other key under [squad] is refused. The bundled document ships the list empty, and a squad that selects nothing sees no new finding from sq check.
- An override in .overrides/workflow.toml replaces the list whole; "$(*squad.validators)" extends the bundled one. [selected] refuses squad.
- Each of these is refused at spec load, naming the entry, and reported by sq workflow lint: an unknown name; an always-on member (index_reconciled, backend_reconciled, roster_config_integrity, default_designation_duplicated, playbook_guide_role_live); a parameter on a member that takes none; a missing or malformed parameter on one that requires it (wip_limit and stale_active need a positive integer, unassigned_active a non-negative one); a level other than error or warn; the same bare name twice, whatever the parameters. Selecting any of the five members at @warn or @error loads clean in a spec that holds what the member needs (the next bullet).
- A selection the spec's own declarations make unable to fire is refused at spec load, naming the entry, and reported by sq workflow lint: wip_limit, unassigned_active or stale_active when no work-category type's lifecycle holds a status of a live role; dependency_acyclic when no ref kind declares the dependency role. Whether the corpus holds an offender is never part of that test.
- A per-item validator name written under [squad] is refused with a message saying it belongs on a type's validators list; a squad-global name written on a type's validators list is refused with the reciprocal message, instead of "unknown validator".
- Every squad-global member, the five always-on ones included, has one declared default level. The always-on members report at exactly the levels they report at today (four error, one warn: playbook_guide_role_live); a test over the whole squad-global catalog proves each member has a declared default and that no member writes a level literal of its own. A selected member reports at its selection's level when it has one and at its default otherwise.
- The always-on and selectable names are disjoint, together make up the squad-global catalog, and neither overlaps the per-item catalog; a test fails when a new member is added without a tier.
- Squad-global members never run at the create/update gate at any level: a selection at @error makes sq check exit non-zero on a finding and does not refuse any write.
- A selection in an override that fails to load does not run; sq check falls back to the bundled spec as it does for every other declaration.
- Adopter documentation (authored by the tech writer) lists which squad-global findings are always-on and cannot be deselected, states that @error at this scope changes only sq check's exit code, and carries no item IDs or build-process narration.
- This repository's own squads/.overrides/workflow.toml is not edited by this feature, and a bare sq check on this repository's live board reports the same issues before and after the feature lands; the table is proven on a scratch copy of the squad (brought to the schema of the build under test if it differs).
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:45Z] `product-owner` Nina Product:
  - 2026-10-09 readiness pass: stays Draft. Prose tidied (role-keyed status and edge matching, parameter semantics for unassigned_active, testable stale_active, narration removed). Missing, owed by @architect: a selection surface for squad-global validators. The five that exist run unconditionally with no spec or override surface, no level and no parameter (read: SQUAD_GLOBAL_CATALOG, no spec field names it), and per-item selection is the per-type validators list. Needed: where a squad names a squad-global member, how :param and @level attach, and the Plane-1 checks. Every story here says this project selects it, and wip_limit and the others cannot be accepted until that exists. Once ruled, the stories need no change beyond naming the location.
- [2026-10-09T17:04:09Z] `op-pierre` Pierre Chat:
  - 2026-10-09: unassigned_active:<n> meaning more than n stands.
- [2026-10-09T18:26:23Z] `architect` Robert Architect:
  - @product-owner Ruled in ADR-982 (Proposed, for op-pierre). ADR-864 does not answer this and the feature misread nothing: it names the five members and their parameters and says a squad "selects" them, but its only sentence on where a selection is written is about a type's list, and ADR-541 says the class "always run[s]" with no surface (read, both).
    
    **Ruling.** A squad selects a squad-global validator in a new top-level `[squad]` table of the workflow document, key `validators`, with the same entry grammar and the same parser as a type's list (`name`, `name:param`, `name@level`, `name:param@level`). The five that exist today become a declared always-on tier, held in code and not nameable in the list; the five in this feature are the selectable tier, bundled list empty. At this scope `@error` only changes `sq check`'s exit code, because squad-global members never run at the create/update gate.
    
    **What has to change here**
    
    - Body, "Selection surface": state the location (`[squad].validators`, in `.overrides/workflow.toml` for a project) and drop the sentence about the shape being a pending ruling.
    - Add a story for the surface itself. It is the larger part of the engine work and no story carries it today. Acceptance, from ADR-982 clause 4: an unknown name, an always-on member, a missing or malformed parameter, an unknown level and a repeated name are each refused at spec load and by `sq workflow lint`; a per-item name under `[squad]` and a squad-global name on a type's list each get a message naming the right list; `[selected]` refuses `squad`; the bundled document ships the list empty; a squad that selects nothing sees no new finding.
    - Same story: every squad-global member, the existing five included, gets one declared default level read through one resolver (clause 6). Today each writes its level as a literal (read: four `error`, one `warn`).
    - US1 to US5: "this project selects it in its own override" names the list. "Warn, catalog-only" becomes "warn by default"; add once, as shared acceptance, that `@error` makes `sq check` exit non-zero and never refuses a write.
    - US5: the engine reads the injectable clock once per run and hands that instant to the member (clause 6); the member calls no clock. The frozen-clock test stands as written.
    - Each story says what the finding's `item` is (clause 8): the parent id for US1, the item id for US5, empty for US2, US3 and US4 with the subjects in the message. Never an assignee slug.
    - Docs acceptance: the adopter page lists which squad-global findings are always-on and cannot be deselected. This is REV-956 F11's documentation ask for this class.
    - Refs: add `implements` to ADR-982.
    
    **Unchanged.** The five members, their parameters ("more than n" for `unassigned_active` included), their default level, and "none bundled". No schema bump and no migration.
    
    **On REV-956 F11.** This adds no finding source: the five are members of the existing squad-global catalog. Each selected member's bare name is the rule identity a `rule` key would carry, and the always-on/selectable split is declared, not inferred. One correction to F11's own text: it says the squad-global catalog is selectable; today it is not (read: `ValidatorEngine.report` runs every member), and after ADR-982 only its selectable tier is.
    
    **For op-pierre to weigh.** `stale_active` and `children_settled_with_parent` report per item and could have been per-item members with a per-type threshold. ADR-982 clause 7 keeps them at squad scope, as ADR-864 placed them, at the cost of one staleness threshold per squad.
- [2026-10-09T18:42:50Z] `product-owner` Nina Product:
  - 2026-10-09 aligned with ADR-982 (Accepted) and the architect's list: selection surface stated in the body, new US6 for the surface (load refusals, default-level table, always-on tier, docs), US1-US5 name the list, warn by default, shared @error-never-refuses-a-write acceptance, finding item per story, US5 single clock read, implements ref to ADR-982. Moved to Ready.
- [2026-10-12T05:26:04Z] `product-owner` Nina Product:
  - 2026-10-12: separated engine delivery from this project's own selection; the live override is read by the released 0.15.0 tool, so this repository's selection moves to a release-preparation step after the squad is migrated.
- [2026-10-12T05:59:25Z] `architect` Robert Architect:
  - @product-owner Two additions to ADR-982 clause 4, dated 2026-10-12, from rulings made for FEAT-901's breakdown (TASK-1001 has the full reasoning). For op-pierre to confirm.
    
    **Ruling.** No member matches a status role by name: role names are a project's to rename (ADR-696 section 3). An active item, for `wip_limit`, `unassigned_active` and `stale_active`, is an item of a `work`-category type whose status's role declares `live = true`. A selection the spec's own declarations make unable to fire is refused at load.
    
    **Why the `work` category.** In the bundled spec the `Active` status is live, and it is where every role, skill, operator and contract rests (read: `[statuses.Active]`, the `agent` and `contract` lifecycles). Counted as written, `unassigned_active` would report every roster entry and `stale_active` every contract, in every squad that selects them.
    
    **What changes here**
    
    - Body: "Statuses are matched by the role the spec gives them (active, settled)" becomes: by the property the status's role declares, `live` for active and `settled` for settled.
    - US3, US4, US5: "active-role status" becomes "a `work`-category item at a status whose role is live". Add test rows: a role at `Active` and a contract at `Active` are not counted; a project role declaring `live = true` under another name is counted; a role named `active` with `live = false` is not.
    - US6: two more refusals at spec load. `wip_limit`, `unassigned_active` or `stale_active` when no `work`-category type's lifecycle holds a live status; `dependency_acyclic` when no ref kind declares the dependency role.
    - US1 is unchanged: it already reads the settled property.
    
    Not edited by me: FEAT-901 stories 2, 5, 6 and 8 need the matching changes, listed on TASK-1001.
- [2026-10-12T06:25:21Z] `architect` Robert Architect:
  - @product-owner op-pierre confirmed the ADR-982 note of this morning (its discussion, 06:19): an active item is a `work`-category item at a status whose role declares `live = true`, and a selection that cannot fire is refused at load. My comment of 05:59 stands as the list of story changes.
    
    One wording point follows from his ruling on ADR-864: roles are matched by a flag the role declares, never by a role name. So the body sentence reads "by the flag the status's role declares (`live` for active, `settled` for settled)". Blocked is now a `blocked` flag on the role, delivered with FEAT-901; no member of this feature reads it.
- [2026-10-12T06:31:53Z] `product-owner` Nina Product:
  - 2026-10-12: roles matched by flag, active item defined as a work-category item at a live status, selections that cannot fire refused at load, test rows added.
- [2026-10-16T19:58:54Z] `tech-lead` Olivia Lead:
  - Task TASK-1074 (Draft) carries the breakdown; dependencies in its body.
<!-- sq:discussion:end -->
