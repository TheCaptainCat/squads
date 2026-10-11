---
id: FEAT-902
sequence_id: 902
type: feature
title: 'Squad-global validators: parent outcomes, cycles, WIP, staleness'
status: Ready
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
updated_at: '2026-10-09T18:42:50Z'
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
- `wip_limit:<n>` -- more than *n* items at an active-role status for one assignee. Explicitly
  not for this squad (we run one agent per role, not kanban WIP discipline) -- named as the
  clearest example of the tier: a real check, nobody's defect, wrong to bundle.
- `unassigned_active:<n>` -- the roll-up of the per-item `assignee_present` check (FEAT-901):
  one finding when more than *n* active-role items have nobody assigned, for a board owner who
  wants one line instead of fifty.
- `stale_active:<days>` -- an item at an active-role status untouched for *n* days. **Admitted
  with one binding condition**: the time it measures against is the injectable clock the rest of
  the codebase already uses, read once per run, and it is **never bundled** by default for any
  squad -- so `sq check` stays deterministic between two runs over an unchanged corpus unless a
  squad has knowingly selected it.

Statuses are matched by the role the spec gives them (active, settled), edges by the role their
kind declares (dependency), never by a name.

## Selection surface

A squad selects these members in a `[squad]` table of the workflow document, key `validators`:

```toml
[squad]
validators = ["children_settled_with_parent", "wip_limit:3", "stale_active:30@error"]
```

- The grammar and the parser are the ones a type's `[items.<type>] validators` list uses:
  `name`, `name:param`, `name@level`, `name:param@level`. `[items.task] validators` is what the
  task type runs; `[squad] validators` is what the squad runs.
- The bundled document ships the list empty. A project selects in `.overrides/workflow.toml`; the
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
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 902 add-story "As a <role>, I want … so that …"`; track with `sq feature 902 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — children_settled_with_parent: flag a settled parent with open children

<!-- sq:story:US1:body -->
As a team that has closed a parent against its children rather than its outcomes before, I want a settled parent with open children flagged, so an unbuilt outcome can't vanish silently the way EPIC-538 did with three unbuilt features.

Acceptance:
- Shared: selected by name in the squad validators list of the workflow document (this project selects it in its own .overrides/workflow.toml unless the story says otherwise); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Fires once per parent item whose status resolves to a settled role while at least one child item (an item whose parent is it) is at a non-settled role; the message lists the open children. The finding's item is the parent's id.
- Applies to any parent type, not only epic/feature/task; sub-entities (stories, subtasks, findings) are not children for this check.
- Silent when every child is settled (cancelled counts as settled), silent for a parent with no children, silent for an open parent.
- This project selects it in the squad validators list of its own override.
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
- Shared: selected by name in the squad validators list of the workflow document (this project selects it in its own .overrides/workflow.toml unless the story says otherwise); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
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
- Shared: selected by name in the squad validators list of the workflow document (this project selects it in its own .overrides/workflow.toml unless the story says otherwise); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required positive-integer parameter, wip_limit:<n> (a bare or malformed entry is refused at spec load; see the surface story).
- Fires once per assignee holding more than n items at an active-role status; an assignee at exactly n is clean; items with no assignee are not counted here; settled and non-active items are not counted. The finding's item is empty; the message names the assignee and the count, and no assignee slug is written in the item field.
- Explicitly not selected in this project's own override -- named as the clearest example of a real check that is nobody's defect and would be wrong to bundle.
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
- Shared: selected by name in the squad validators list of the workflow document (this project selects it in its own .overrides/workflow.toml unless the story says otherwise); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required non-negative-integer parameter, unassigned_active:<n> (zero is valid; a bare or malformed entry is refused at spec load). Fires once when MORE THAN n active-role items have no assignee; at n or fewer it is clean, so unassigned_active:0 flags any unassigned active item.
- The finding's item is empty; the message states the count and names at most the first few items.
- Independent of the per-item assignee_present check: a squad may select either, both or neither.
- This project does not select it.
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
- Shared: selected by name in the squad validators list of the workflow document (this project selects it in its own .overrides/workflow.toml unless the story says otherwise); a squad that does not select it sees no finding from it; it reports at warn by default; @error on it only makes sq check exit non-zero and never refuses a write.
- Required positive-integer parameter, stale_active:<days> (a bare or malformed entry is refused at spec load).
- The engine reads the injectable clock once per run and every item in that run is measured against that same instant; the member itself calls no clock. A test freezes the clock and proves an item untouched for days+1 days warns while one untouched for exactly days days is clean, and that two items checked in one run are measured against the same instant.
- "Untouched" is measured from the item's updated_at timestamp; this feature does not change what bumps it. The finding's item is the stale item's id.
- Never bundled by default for any squad, so sq check is deterministic between two runs over an unchanged corpus unless a squad has knowingly selected it; a test proves two runs over an unchanged corpus with nothing selected agree.
- One threshold applies to the whole squad. This project does not select it.
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
- Each of these is refused at spec load, naming the entry, and reported by sq workflow lint: an unknown name; an always-on member (index_reconciled, backend_reconciled, roster_config_integrity, default_designation_duplicated, playbook_guide_role_live); a parameter on a member that takes none; a missing or malformed parameter on one that requires it (wip_limit and stale_active need a positive integer, unassigned_active a non-negative one); a level other than error or warn; the same bare name twice, whatever the parameters. Selecting any of the five members at @warn or @error loads clean.
- A per-item validator name written under [squad] is refused with a message saying it belongs on a type's validators list; a squad-global name written on a type's validators list is refused with the reciprocal message, instead of "unknown validator".
- Every squad-global member, the five always-on ones included, has one declared default level. The always-on members report at exactly the levels they report at today (four error, one warn: playbook_guide_role_live); a test over the whole squad-global catalog proves each member has a declared default and that no member writes a level literal of its own. A selected member reports at its selection's level when it has one and at its default otherwise.
- The always-on and selectable names are disjoint, together make up the squad-global catalog, and neither overlaps the per-item catalog; a test fails when a new member is added without a tier.
- Squad-global members never run at the create/update gate at any level: a selection at @error makes sq check exit non-zero on a finding and does not refuse any write.
- A selection in an override that fails to load does not run; sq check falls back to the bundled spec as it does for every other declaration.
- Adopter documentation (authored by the tech writer) lists which squad-global findings are always-on and cannot be deselected, states that @error at this scope changes only sq check's exit code, and carries no item IDs or build-process narration.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:45Z] Nina Product:
  - 2026-10-09 readiness pass: stays Draft. Prose tidied (role-keyed status and edge matching, parameter semantics for unassigned_active, testable stale_active, narration removed). Missing, owed by @architect: a selection surface for squad-global validators. The five that exist run unconditionally with no spec or override surface, no level and no parameter (read: SQUAD_GLOBAL_CATALOG, no spec field names it), and per-item selection is the per-type validators list. Needed: where a squad names a squad-global member, how :param and @level attach, and the Plane-1 checks. Every story here says this project selects it, and wip_limit and the others cannot be accepted until that exists. Once ruled, the stories need no change beyond naming the location.
- [2026-10-09T17:04:09Z] Pierre Chat:
  - 2026-10-09: unassigned_active:<n> meaning more than n stands.
- [2026-10-09T18:26:23Z] Robert Architect:
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
- [2026-10-09T18:42:50Z] Nina Product:
  - 2026-10-09 aligned with ADR-982 (Accepted) and the architect's list: selection surface stated in the body, new US6 for the surface (load refusals, default-level table, always-on tier, docs), US1-US5 name the list, warn by default, shared @error-never-refuses-a-write acceptance, finding item per story, US5 single clock read, implements ref to ADR-982. Moved to Ready.
<!-- sq:discussion:end -->
