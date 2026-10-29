---
id: FEAT-1249
sequence_id: 1249
type: feature
title: Bundled vocabulary fully overridable
status: Draft
parent: EPIC-538
author: product-owner
priority: high
refs:
- MILE-1241:targets
- REV-1247
- ADR-323
- ADR-348
- ADR-622
description: Overrides rename or replace types, kinds and badge fields end to end,
  with nothing reserved for a dropped type.
subentities:
- local_id: US1
  title: Priority surface derived from the spec
  status: Todo
- local_id: US2
  title: Root aliases resolved from the active spec
  status: Todo
- local_id: US3
  title: Import fronts and selectors per declared kind
  status: Todo
- local_id: US4
  title: Story-mapping wording after the target kind
  status: Todo
- local_id: US5
  title: Generated text and messages from the spec
  status: Todo
created_at: '2026-10-29T19:04:26Z'
updated_at: '2026-10-29T19:16:52Z'
---
<!-- sq:body -->
## Problem

The settled intent is that only role, skill and operator are reserved types. Every work-item type and sub-entity kind is fully overridable, and a field's label comes from the spec. The architect's audit on REV-1247 found twelve places where bundled words still leak into the CLI, import, help, messages and generated skills. Driven on a scratch squad that drops epic/feature/task/contract/guide and story/subtask and adds `initiative` (kind `outcome`) and `job` (kind `action`), these gaps appear:

- `create --priority` and item `update --priority` are static options, so the squad's own field (`--urgency`) gets no update option. `list --priority high` on a squad with no priority field prints "no items" and exits 0.
- `sq list` shows a fixed "Priority" column that is empty for the squad's field.
- An override that reuses a bundled root alias (`f`) is refused at spec load even though the owner type was dropped.
- Import fronts `add-story`/`add-subtask`/`add-finding` and the comment selectors `story`/`subtask`/`finding` are fixed. On a squad whose kind is `outcome` they give "a initiative, which does not host storys".
- Story-mapping wording (`--story`, "as US<n>", "user story X not found", the "Story" column) ignores the target kind.
- Generated skill text and validator messages carry bundled words (`sq f 26 story 4 show`, "no incoming supersedes edge found", container headings), plus article and plural defects ("a initiative", "storys").

## Value

An adopter who renames or replaces bundled types, kinds and badge fields gets a CLI, import, help, messages and generated skills in their own words. Nothing stays reserved for a type they dropped, and an agent reading the generated skill is never told to run a command that squad refuses.

## Scope

Five stories, one per block of the audit (rows refer to the REV-1247 table):

- Priority surface derived from the spec (rows 1-4, and the client label of row 5).
- Root aliases resolved from the active spec (row 7).
- Import fronts and comment selectors per declared kind (row 12).
- Story-mapping wording after the target kind, `--story` kept (rows 9, 10 labels, 11).
- Generated text and messages from the spec (rows 8, 13, 20, and the article and plural defects).

Decision records: the work amends ADR-323 section 5, ADR-348 section 7 and ADR-622, so each change lands with the architect's amendment.

## Non-goals

- The frozen storage and wire keys stay: `priority`, `severity` and `story` as frontmatter, DTO, tree/graph and client keys (rows 5, 6, 10). Only their labels come from the spec.
- The harmless rows 14-19, 21-23 (per-type templates, display tie-breaks, dead code, icons, orchestration prose) are not part of this feature.
- No new stored state: aliases and labels are derived from the active spec.

## Acceptance

- On a squad whose override drops every bundled work-item type and kind and declares its own, with a custom priority-collection field, no CLI option, column, help text, error message or generated skill line names a dropped type, kind or the word priority/story, except the frozen keys in `--json` output.
- A root alias of a dropped type is usable by an override; a bundled squad still refuses to shadow a live alias.
- Bundled squads behave as before, apart from the documented option renames, and each amended ADR records the change.
- Each story's "Done when" holds, with a regression test per case (ADR-1172).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1249 add-story "As a <role>, I want … so that …"`; track with `sq feature 1249 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Priority surface derived from the spec

<!-- sq:story:US1:body -->
As an adopter with my own priority field, I get create, update, list and tree options, columns and headers named after it.

Rows 1-4 and the client label of row 5; supersedes ADR-323 section 5.

Done when:
- On a squad whose field is `urgency`, `create` and `update` accept `--urgency` and `--no-urgency`, and the static `--priority` and `--min-priority` options are gone.
- `list --badge` and the list sugar refuse a code no type declares, exit 1.
- `sq list` shows a column headed and keyed by the first ordered field.
- The VS Code graph label reads `badges`/`display`, not the `priority` key; the `priority` key in tree/graph JSON is unchanged.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Root aliases resolved from the active spec

<!-- sq:story:US2:body -->
As an adopter who dropped a bundled type, I can reuse its root alias.

Row 7: the reserved-alias table stays only as a guard for bundled squads.

Done when:
- With `feature` dropped, an override giving another type the alias `f` loads and `sq f` runs that type.
- With `feature` kept, shadowing `f` is still refused at spec load.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Import fronts and selectors per declared kind

<!-- sq:story:US3:body -->
As an adopter, my import files use my kinds' words, and the errors read in them.

Row 12; amends ADR-622.

Done when:
- On a squad with kind `outcome`, an import accepts the `add-outcome` front and the `outcome` comment selector.
- The `add-story`, `add-subtask` and `add-finding` fronts are accepted only where the kind is declared.
- Error messages name the declared kind and its plural.
- The generic `add-sub` and `sub` forms keep working.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Story-mapping wording after the target kind

<!-- sq:story:US4:body -->
As an adopter, mapping a sub-entity to its parent kind reads in my words, while `--story` still works.

Rows 9, 10 (labels only) and 11; amends ADR-348 section 7. The `story` storage and wire keys stay.

Done when:
- On a squad with kinds `action` mapping to `outcome`, `add-action --help`, the table header, the `show` label and the not-found message name `outcome` and take the prefix from its `local_prefix`.
- `--story` is still accepted as an alias.
- The mapping validator message uses the actual parent's kind name when the type has no required parent.
- The VS Code and TUI sub-entity label come from the target kind.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Generated text and messages from the spec

<!-- sq:story:US5:body -->
As an adopter, the generated skills and validator messages never use a bundled word for something I renamed.

Rows 8, 13, 20 plus the article and plural defects.

Done when:
- A kind has a spec key for its container heading, the bundled spec declares the three, and the fixed table is gone.
- On the scratch squad, `sq skill squads show` has no `sq f 26 story 4 show` example or story/subtask/finding parenthetical; the example is built from the first aliased type and its kind.
- The supersession validator message names the declared supersession kind.
- The article reads `an initiative` and `an action's`, the import plural reads from the spec's plural, and `add-action --help` lists the collection codes that create lists.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T19:16:52Z] `op-pierre` Pierre Chat:
  - 2026-10-29: in scope as well: (1) the vocabulary guards derive what they check from the spec and lose their exception lists, covering badge codes, aliases and generated text; (2) the audit override squad (initiative/outcome, job/action, urgency, impact) becomes a permanent test squad and the CLI surface suite also runs on it in CI. Storage goes generic with a schema migration (see ADR-1250).
<!-- sq:discussion:end -->
