---
id: ADR-982
sequence_id: 982
type: decision
title: Squad-global validators are selected in a [squad] validators list
status: Accepted
author: architect
refs:
- ADR-864
- ADR-541
- ADR-738
- ADR-777
- FEAT-902
- ADR-696
description: Where a squad names, levels and parameterises a squad-global validator,
  and which members stay always-on.
created_at: '2026-10-09T18:25:28Z'
updated_at: '2026-10-12T06:23:21Z'
---
<!-- sq:body -->
## Context

ADR-541 defined two validator classes and gave only one of them an assignment surface. A per-item
member is selected through its type: common core, the category bundle, then the type's own
`validators` list. A squad-global member has no surface at all, by that decision's own words: "No
`category` turns these on or off; they always run. An override cannot deselect them."

ADR-864 then admitted five squad-global members that are policies rather than defects
(`children_settled_with_parent`, `dependency_acyclic`, `wip_limit:<n>`, `unassigned_active:<n>`,
`stale_active:<days>`), named three of them with a parameter, and required that `stale_active` is
"never bundled" and runs only for "a squad that selects it". It did not say where a squad writes
that selection. Its one sentence on the shape of a selection ("a level suffix on the assignment
... or a per-type map") is about a type's list.

What the code holds, all **read**:

- The workflow document's top-level key space is closed at eight sections
  (`WORKFLOW_TOP_LEVEL_SECTIONS`, `_workflow/_loader.py`), none of which is squad-scoped, and
  `WorkflowSpec` has no field a squad-global name could be written in.
- `SQUAD_GLOBAL_VALIDATOR_NAMES` holds five members. `ValidatorEngine.report` runs every one of
  them on every `sq check`; the only filter anywhere is `check` holding `index_reconciled` back for
  its confirm pass. Each writes its level as a literal: four `error`, one `warn`
  (`playbook_guide_role_live`).
- The assignment grammar is one function, `parse_validator_entry`, giving `name`, `name:param`,
  `name@level` and `name:param@level`. Its Plane-1 checks (`_check_validators_assignment`) test
  membership against the per-item catalog only, so a squad-global name written on a type's list is
  refused as "an unknown validator".
- `DEFAULT_VALIDATOR_LEVEL` and `VALIDATOR_LEVEL_FLOOR` are closed over the per-item catalog. No
  table declares a squad-global member's level.

So the five new members can be implemented but not selected, levelled or parameterised.

## Decision

### 1. The surface: a `[squad]` table with one key, `validators`

The workflow document gains one top-level table:

```toml
[squad]
validators = ["children_settled_with_parent", "wip_limit:3", "stale_active:30@error"]
```

- `squad` joins the document's closed top-level key space. It is a typed record (a nested model,
  unknown keys refused), not a map of declared entries. `validators` is its only key.
- The bundled document declares it with an empty list. An adopter selects in
  `.overrides/workflow.toml`, on the override contract every other key follows (ADR-777): the
  list is a leaf and is replaced whole, and `"$(*squad.validators)"` extends the bundled one.
- `[selected]` does not accept `squad`. It drops entries from a vocabulary map, and this table
  has none.

Reading the two surfaces side by side is the point: `[items.task] validators` is what the task
type runs, `[squad] validators` is what the squad runs.

### 2. One grammar, one parser

An entry is `name`, `name:param`, `name@level` or `name:param@level`, split by the same
`parse_validator_entry` a type's list uses. There is no second spelling, no per-member table and
no map form.

### 3. Two tiers at squad scope, declared as a partition

ADR-864's tiering test applies unchanged, with one tier fewer because no category exists at this
scope:

- **Always-on.** A defect in every squad. The five members that exist today. Held in a code
  constant, the squad-scope counterpart of `COMMON_CORE`, so no override reaches it and ADR-541's
  "cannot deselect" clause keeps holding for exactly these.
- **Selectable.** A policy. Effective only when `[squad].validators` names it. The five members
  ADR-864 admits.

The two sets are disjoint, their union is the squad-global name catalog, and an import-time
assert closes it, so a new member cannot be added without stating its tier. The squad-global and
per-item catalogs are disjoint as well, asserted the same way: one name, one rule.

A squad's effective set is the always-on members followed by its selection in declared order.

### 4. Plane-1 checks

Each is a spec-load refusal naming the entry, reported by `sq workflow lint` with the rest.

1. The bare name must be a selectable squad-global member. A per-item name is refused with a
   message saying it belongs on a type's `validators` list, and a squad-global name on a type's
   list is refused with the reciprocal message, in place of today's "unknown validator".
2. An always-on member is refused: it runs regardless and has nothing to select. Naming one is
   an entry that would load clean and do nothing.
3. A parameter is refused on a member that takes none and required on one that does:
   `wip_limit:<n>` and `stale_active:<days>` take a positive integer, `unassigned_active:<n>` a
   non-negative one.
4. A level must be `error` or `warn`. None of the five selectable members holds a level floor.
5. A bare name appears at most once. Every parameterised member here resolves one value, so two
   entries of one name are refused whatever their parameters.

> **Amended 2026-10-12 (ADR-864, amendment of the same date):** two additions.
>
> - **What the members count.** For `wip_limit`, `unassigned_active` and `stale_active` an
>   active item is an item of a `work`-category type whose status's role declares
>   `live = true`; for `children_settled_with_parent`, settled is the role's `settled` flag. No
>   role is matched by name. Roster and `records` types are not counted as active: the bundled
>   `Active` status is live and is where every role, skill, operator and contract rests.
> - **A sixth check.** A selection the spec's own declarations make unable to fire is refused:
>   `wip_limit`, `unassigned_active` or `stale_active` when no `work`-category type's lifecycle
>   holds a live status, and `dependency_acyclic` when no ref kind declares the dependency
>   role.

> **Confirmed 2026-10-12 (op-pierre, this decision's discussion):** both additions stand as
> written. The amendment of ADR-864 they follow was corrected the same day on a point no member
> at this scope reads: blocked is a `blocked` flag a role declares, not a role named by a
> parameter.

### 5. What a level means at this scope

A selectable member's default level is `warn`. `@error` makes `sq check` exit non-zero on the
finding, and that is all it does. Squad-global members do not run at the create/update gate
(ADR-541), so `wip_limit:3@error` never refuses an assignment. This differs from a per-item
`@error`, which does abort a write, and the adopter documentation has to say so.

Always-on members keep the levels they ship with. Because they cannot be named, they cannot be
dialled. Accepting a level on one later is an additive relaxation of check 2.

### 6. Level and time are read, never written inline

- Every squad-global member, always-on included, has one declared default level in the spec
  layer, in a table closed against the name catalog by assert. A member reports at its
  selection's level when one is declared and at its default otherwise, through one resolver.
- `ValidatorEngine.report` reads the injectable clock once per run and hands that instant to
  squad-global members on their context. `stale_active` measures against it and calls no clock
  itself, so every item in one run is measured against the same instant.

### 7. Why these five sit at squad scope

ADR-541 defines the class by its subject, "the squad as a whole". `dependency_acyclic` (a cycle),
`wip_limit` (an assignee) and `unassigned_active` (a count) fit plainly. `stale_active` and
`children_settled_with_parent` report one finding per item and could have been per-item members.
They stay where ADR-864 placed them, for two reasons:

- Both must stay out of the create/update gate at any level, and this class is report-only by
  construction, not by a withheld-context declaration.
- A parent relation spans types. Selected per type, the check silently misses a type a project
  adds later.

The cost is one staleness threshold per squad. A per-type threshold, if a squad asks for one,
arrives as an additive change.

### 8. Finding provenance

- The new members are members of the existing squad-global catalog and are run by
  `ValidatorEngine.report`. `sq check` gains no finding source.
- Every finding a selected member emits belongs to exactly one catalog name, and that bare name
  is the rule's identity: what a `rule` key on a check finding would carry if one is added. This
  decision adds no such key and no member may be identified by matching message text.
- The always-on/selectable partition of clause 3 is the declared answer to "can this finding be
  deselected" for this class.
- A finding's `item` is an item id when it concerns exactly one item (the settled parent, the
  stale item) and empty otherwise (a cycle, an assignee, a count), with the subjects named in the
  message. An assignee slug is never written there.

## What this narrows

- **ADR-541**, "they always run. An override cannot deselect them": true of the always-on tier,
  no longer of the class.
- **ADR-864**, the build order's fifth step: the members are unchanged; this supplies the
  surface they are selected on and carries the tiering test to squad scope.
- **ADR-738**: `squad` is a typed record, not a declared map, so the one-catalog-per-map rule
  asks for no command. The selection stays unpublished on the same terms as a type's
  `validators` (its section 7).

## Consequences

- No frontmatter key, no index field, no schema bump, no migration. An override naming `[squad]`
  is refused by an older package as an unknown top-level key, which is the closed top level
  doing its job.
- The bundled document changes (one empty table), so its golden lock changes with it.
- The override trap a type's list already has applies here: a plain list replaces the bundled
  one. It costs nothing while the bundled list is empty and starts to matter the day a member is
  bundled.
- A selection made in an override that fails to load does not run, because `sq check` then
  falls back to the bundled spec, as it does for every other declaration.

## Alternatives rejected

- **A root-level `validators` key.** A TOML root key must precede every table header. Written
  after `[items.task]` it is that type's list, replacing whatever the type declared.
- **A map, one table per member with `level` and `param` keys.** A second grammar for the
  dimension ADR-864 already settled as a suffix, and a declared map that would owe a catalog
  command.
- **Selecting squad-global members on a type's list.** Three of the five have no type.
- **`.squads.toml`.** Validator selection is spec vocabulary: linted, stamped against a base and
  diffed by `sq override`. Splitting it across two files splits all three.
- **Listing the always-on members in the bundled document.** A list is a leaf, so one plain
  override entry would drop index reconciliation.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T18:34:58Z] Pierre Chat:
  - 2026-10-09: accepted as written. One staleness threshold per squad and non-dialable always-on checks are fine for now.
- [2026-10-12T05:59:31Z] Robert Architect:
  - 2026-10-12: one dated note added after clause 4's list, nothing else in the body changed; `related` ref to ADR-696 added. For op-pierre to confirm. @manager
    
    - The three members that count active items count `work`-category items at a status whose role declares `live = true`, never a role matched by name.
    - A sixth Plane-1 check: a selection the spec's own declarations make unable to fire is refused.
    - It follows ADR-864's amendment of the same date; FEAT-902 has the story changes.
- [2026-10-12T06:19:21Z] Pierre Chat:
  - 2026-10-12: the note of this date stands for squad scope (an active item is a work-category item at a live status; a selection that cannot fire is refused at load), with one change from my ruling on ADR-864: blocked is a flag a role declares, not a role named by a parameter.
<!-- sq:discussion:end -->
