---
id: FEAT-1249
sequence_id: 1249
type: feature
title: Bundled vocabulary fully overridable
status: InProgress
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
  title: Badge-field options derived from the spec
  status: InProgress
- local_id: US2
  title: Root aliases resolved from the active spec
  status: InProgress
- local_id: US3
  title: Import fronts and selectors per declared kind
  status: InProgress
- local_id: US4
  title: Sub-entity mapping named after the target kind
  status: InProgress
- local_id: US5
  title: Generated text and messages from the spec
  status: InProgress
- local_id: US6
  title: Generic storage and the 0.19 schema migration
  status: InProgress
- local_id: US7
  title: Wire and DTO shapes, and the stability doc
  status: InProgress
- local_id: US8
  title: rename-field verb and check on unknown sub-entity keys
  status: Todo
- local_id: US9
  title: Guards derived from the spec, no allow-lists
  status: Todo
- local_id: US10
  title: Permanent override test squad and its CI job
  status: InProgress
created_at: '2026-10-29T19:04:26Z'
updated_at: '2026-10-29T21:07:42Z'
---
<!-- sq:body -->
## Problem

The settled intent is that only role, skill and operator are reserved types. Every work-item type, sub-entity kind and badge field is fully overridable, and nothing outside the spec names a bundled word: not an option, a column, a message, an import key, a stored key, a wire key, a generated line or a guard (ADR-1250). The architect's audit on REV-1247 drove a scratch squad that drops epic/feature/task/contract/guide and story/subtask and adds `initiative` (kind `outcome`, field `urgency`) and `job` (kind `action`, field `impact`). Bundled vocabulary is still special in these places:

- `create --priority`, item `update --priority`, `list --priority` and `tree` carry static options and request fields. A squad whose field is `urgency` gets no `--urgency`; `list --priority high` on a squad with no priority field prints "no items" and exits 0. `sq list` shows a fixed "Priority" column.
- An override that reuses a bundled root alias (`f`) is refused at spec load even though the owner type was dropped.
- Import fronts `add-story`/`add-subtask`/`add-finding` and the comment selectors `story`/`subtask`/`finding` are fixed. On a squad whose kind is `outcome` they give "a initiative, which does not host storys".
- The mapping option `--story`, "as US<n>", "user story X not found" and the "Story" column ignore the target kind.
- `priority` and `severity` are core keys with typed slots on `Item` and `SubEntity`; a sub-entity stores `story` and an `extra` mapping; tree and graph nodes carry a fixed `priority` key and sub-entity objects a fixed `severity`, `story` and `extra`. The spec key `maps_parent_story`, the validator `subtask_story_mapping` and the transform `milestone_rollup` name bundled vocabulary for generic mechanisms.
- Generated skill text and validator messages carry bundled words (`sq f 26 story 4 show`, "no incoming supersedes edge found", container headings), plus article and plural defects ("a initiative", "storys").
- The vocabulary guards in `tests/meta` keep hand-written literal sets and per-hit exception lists, which is how every case above passed them. Nothing runs the CLI surface suite on a squad whose vocabulary differs from the bundled one.

## Value

An adopter who renames or replaces bundled types, kinds and badge fields gets a CLI, import, storage, wire shapes, help, messages and generated skills in their own words. Nothing stays reserved for a type they dropped, no flag exists that the squad's spec does not declare, and an agent reading the generated skill is never told to run a command that squad refuses. The guards and a permanent override test squad keep it true.

## Scope

Ten stories, one per part of ADR-1250 (rows refer to the REV-1247 table):

- US1: badge-field options and the list column derived from the spec (rows 1-4, client label of row 5).
- US2: root aliases resolved from the active spec (row 7).
- US3: import fronts and comment selectors per declared kind (row 12).
- US4: sub-entity mapping named after the target kind (rows 9, 10, 11).
- US5: generated text and messages from the spec (rows 8, 13, 20, article and plural defects).
- US6: generic storage and the 0.19 schema migration.
- US7: wire and DTO shapes, and the stability doc.
- US8: `sq migrate rename-field` and `sq check` on sub-entity unknown keys.
- US9: vocabulary guards derived from the spec, with no exception lists.
- US10: the permanent override test squad and its CI job.

Release 0.19.0 carries the schema change (`SCHEMA_VERSION` 0.19). Decision records: ADR-1250 states the rule and narrows ADR-323, ADR-348, ADR-622, ADR-1007 and ADR-1172 in place.

## Non-goals

- The harmless rows 14-19, 21-23 (per-type templates, display tie-breaks, dead code, icons, orchestration prose) are not part of this feature.
- No static spelling and no alias of a bundled name survives: no `--priority`, `--story` or `story` key exists except where the bundled spec declares the field or kind.
- No automatic field rename from an override diff: a rename is not distinguishable from a drop plus an add, so `rename-field` is an explicit verb.
- No new stored state beyond the declared values and `maps_to`: aliases, labels and target kinds are derived from the active spec.

## Acceptance

- On the override test squad (US10), no CLI option, column, help text, error message, import key, stored key, `--json` key or generated skill line names a dropped type, kind, field or alias.
- A bundled squad sees the same spellings it has today (`--priority`, `--story`, `add-story`, `f`), derived from the bundled spec, and its item frontmatter is unchanged.
- An existing squad reaches 0.19 through `sq migrate up` with entries flat and `.squads.json` rebuilt from the files.
- Every vocabulary guard reads its names from `bundled_spec()` and keeps no exception list.
- The CLI surface suite passes on the bundled squad and on the override test squad, in CI.
- Each story's "Done when" holds, with a regression test per case (ADR-1172).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1249 add-story "As a <role>, I want … so that …"`; track with `sq feature 1249 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Badge-field options derived from the spec

<!-- sq:story:US1:body -->
As an adopter with my own badge fields, I get create, update, add, list and tree options, columns and headers named after the fields my spec declares, and none for fields it does not.

Rows 1-4 and the client label of row 5; ADR-1250 section 2, narrowing ADR-323 section 5.

Done when:
- On a squad whose field is `urgency`, `create` and `<type> <n> update` accept `--urgency`, `update` accepts `--no-urgency` for an optional field, and `--priority`, `--no-priority` and `--min-priority` are unknown options (Click exit 2).
- `add-<kind>` and `<kind> <k> update` take `--<code>` for each field the kind declares, and `--no-<code>` on update for each optional one.
- `list` and `tree` take `--<code> <value>` and, for a field on an ordered collection, `--min-<code> <value>`; each means exactly `--badge <code>=<value>` and `--min-badge <code>=<value>`.
- A code with underscores gets a dashed flag.
- `--set`, `--unset`, `--badge`, `--min-badge` and `--sort` refuse a code no non-roster type declares, exit 1, naming the declared codes.
- No request DTO carries a field by name: `ItemCreateRequest.priority`, `ItemUpdateRequest.priority` and `clear_priority` are gone; values travel in the generic fields map.
- `sq list` shows one badge column, the first field on an ordered collection in type declaration order, headed by that field's label, and none when no type declares a field.
- The VS Code graph label reads `badges` and `display`.
- A bundled squad still accepts `--priority`, derived from its declared field.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Root aliases resolved from the active spec

<!-- sq:story:US2:body -->
As an adopter who dropped a bundled type, I can reuse its root alias.

Row 7; ADR-1250 section 5. The bundled groups and their aliases register from the bundled spec, and the code table `RESERVED_CLI_ALIASES` is gone.

Done when:
- With `feature` dropped, an override giving another type the alias `f` loads and `sq f` runs that type.
- With `feature` kept, shadowing `f` is refused at spec load, naming the owner.
- Spec load checks an alias against the fixed verbs, the declared type names and the other declared types' aliases, all in the active spec.
- A bundled squad resolves every bundled alias as before.
- No code table of bundled aliases exists under `src/squads`.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Import fronts and selectors per declared kind

<!-- sq:story:US3:body -->
As an adopter, my import files use my kinds' words, and the errors read in them.

Row 12; ADR-1250 section 4, narrowing ADR-622.

Done when:
- On a squad with kind `outcome`, an import accepts the `add-outcome` front and the `outcome` comment selector.
- `add-<kind>` is `add-sub` with `kind` set; it takes add-sub's keys, each field the kind declares as a top-level key under its code, and the target kind's name as a key when the kind maps.
- `add-sub` takes the mapping as `maps_to` and fields in `fields`.
- `create` and `update` take badge fields by code in `fields` and `unset_fields`, with no key named after a field.
- An op or selector for a kind the active spec does not declare is unknown, and the refusal names the declared `add-<kind>` ops.
- The `add-story`, `add-subtask` and `add-finding` fronts are accepted only on a squad that declares those kinds.
- The generic `add-sub` and `sub: [kind, local-or-handle]` forms work on every squad.
- Error messages use the declared kind label and plural, with no article chosen in code.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Sub-entity mapping named after the target kind

<!-- sq:story:US4:body -->
As an adopter, mapping a sub-entity to a sub-entity of its parent reads in my words: the option, column, label and messages are named after the target kind.

Rows 9, 10 and 11; ADR-1250 section 3, narrowing ADR-348 section 7. A kind declares `maps_to_parent = true`; the spec key, the validator `subentity_mapping` and the catalog column take the neutral names.

Done when:
- The target kind is the kind hosted by the host type's `parent_required` type.
- On a squad where kind `action` maps to `outcome`, `add-action` takes `--outcome <local-or-id>`, `action <k> update` takes `--outcome` and `--no-outcome`, and `--story` is an unknown option.
- `add-action --help`, the mapping column header, the show and head label and the not-found message ("outcome OC9 not found in INI-2") name `outcome` and take the prefix from its `local_prefix`.
- Spec load refuses a mapping kind hosted by a type with no `parent_required`, or whose `parent_required` type hosts no kind, naming the type and both remedies.
- `subentity_mapping` checks each mapping against the parent's sub-entities and names the target kind.
- `maps_parent_story`, `subtask_story_mapping` and the transform function `milestone_rollup` are refused in an override with a message naming `maps_to_parent`, `subentity_mapping` and `status_rollup`; the bundled spec uses the neutral names and keeps the view named `milestone_rollup`.
- The VS Code and TUI sub-entity labels come from the target kind.
- A bundled squad still takes `--story`, derived from kind `story`.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Generated text and messages from the spec

<!-- sq:story:US5:body -->
As an adopter, the generated skills and validator messages never use a bundled word for something I renamed.

Rows 8, 13, 20 plus the article and plural defects; ADR-1250 sections 1 and 3.

Done when:
- A kind declares its container heading under a `heading` key in `[subentity_kinds.<kind>]`; when absent the heading is the title-cased `plural`; the bundled spec declares the three bundled headings and the fixed code table is gone.
- On the override test squad, `sq skill squads show` has no `sq f 26 story 4 show` example and no story/subtask/finding parenthetical; the example is built from the first aliased type and its kind.
- The supersession validator message names the declared supersession kind.
- Messages use the declared label and `plural` and read without an article chosen in code ("a initiative" and "storys" cannot occur).
- `add-<kind> --help` lists the collection codes that `create` lists.
- Documentation for the `heading` key is in `docs/overrides.md`.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Generic storage and the 0.19 schema migration

<!-- sq:story:US6:body -->
As an adopter, my badge values and sub-entity mappings are stored under their declared keys, and `sq migrate up` carries my existing squad to 0.19.

ADR-1250 sections 6 and 8; narrows ADR-323 section 4, ADR-348 section 4 and ADR-1007.

Done when:
- `priority` and `severity` are not item core keys; an item stores each badge value at the top level under its field code; `Item.priority`, `Item.severity`, `SubEntity.severity`, `SubEntity.story` and `SubEntity.extra` are gone.
- A sub-entity entry has core keys `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`; every other key is an attribute of the entry; `maps_to` is written only when set.
- `Item.attributes` and `SubEntity.attributes` hold every non-core key; `badge_value(code)` and `set_badge_value(code, value)` read and write them on both models.
- Unknown keys on an entry are kept through every write, repair and migration.
- Spec load refuses a field code or attribute key that collides with a core key, `path`, `prefix`, a key `--json` adds to the row, or another field of the same type or kind, naming the key and what it collides with; the same for a derived flag or import key against the fixed names of its surface and for a kind named `sub`.
- `SCHEMA_VERSION` is 0.19, with one runner in `_migrations/_registry.py` that rewrites only `subentities` entries: `story: X` becomes `maps_to: X`, each `extra` key moves to the entry's top level, and an empty `severity` is dropped. Item top-level keys, body bytes and markers are untouched.
- The runner scans first and refuses, exit 1 with nothing written, when an entry holds both `story` and `maps_to`, or an `extra` key equal to a core key or to a key already at the top level, naming the item and the key.
- A second run rewrites nothing and leaves every file byte-identical; `sq migrate up` then rebuilds `.squads.json` from the files.
- The migration's `manual` step lists the override spellings refused at load, the removed template context names and their replacements, and that reflog entries keep their recorded keys.
- This repository's squad migrates with the runner and `sq check` is clean.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Wire and DTO shapes, and the stability doc

<!-- sq:story:US7:body -->
As a client or script author, every JSON and render shape carries values by badge code and mapping, with no bundled field name as a key.

ADR-1250 section 7; narrows ADR-1007. The change lands in the same release as the stored shape.

Done when:
- Item rows (`list`, `show`, `create`, `mine`) have no `priority` or `severity` core keys; a stored badge value appears at the top level only when the file stores it, and `badges` carries every declared field.
- Tree and graph nodes have no `priority` key; `badges` carries every field.
- Sub-entity objects have the keys `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`, then each stored attribute flat, then `body`, `badges`, `discussion`, `display`; `maps_to` and `deferred_to` are always present and `null` when unset; `severity`, `story` and `extra` are absent.
- The sub-entity row's `display.story` is `display.maps_to`, the mapped sub-entity as shown.
- `sq workflow subentity-kinds --json` has the column `maps_to_parent`, not `maps_parent_story`.
- Sub-entity head and item templates receive the declared fields as a list of `{code, label, badge}` and the mapping as `{label, value}`; the names `severity`, `severity_label` and `story` are gone and a template reading one fails under `StrictUndefined`.
- VS Code and the TUI read badge values from `badges`, labels from `display` and the catalogs, and `maps_to`; the daemon's HTTP surface returns the same shapes.
- The DTO guard still holds every field JSON-native.
- `docs/stability.md` records the entries ADR-1250 lists for Tier 1, Tier 2 and Tier 3, and the adopter docs (`docs/workflow.md`, `docs/overrides.md`, `docs/adoption.md`) match; the CHANGELOG records the removed hidden flag as a fix.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — rename-field verb and check on unknown sub-entity keys

<!-- sq:story:US8:body -->
As an adopter who renamed or dropped a badge field, `sq check` reports the values left under the old code, and one verb moves them.

ADR-1250 section 6.

Done when:
- A stored key that the active spec does not declare on that type or kind is kept, never a load refusal.
- `sq check` reports it under `frontmatter_key_undeclared` on items and on sub-entity entries, and the finding names `sq migrate rename-field`.
- `sq migrate rename-field <old> <new>` moves every stored value from key `<old>` to `<new>` on items and sub-entities in one transaction.
- It refuses, exit 1 with nothing written, when an entry's type or kind does not declare `<new>`, when an entry already holds `<new>`, or when a moved value is not a badge of `<new>`'s collection; the refusal names the entry.
- A kind rename needs no data move: after a rename that keeps `local_prefix`, `sq check` is clean and mappings still resolve.
- A test breaches `frontmatter_key_undeclared` on a sub-entity entry (`@pytest.mark.breaches`), and a CLI test covers `rename-field`.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Guards derived from the spec, no allow-lists

<!-- sq:story:US9:body -->
As a maintainer, the vocabulary guards find a bundled word wherever it hides, because they read the names from the bundled spec and keep no exception.

ADR-1250 section 9.

Done when:
- Every vocabulary guard in `tests/meta` reads the type names, kind names, field codes, collection names, statuses, ref kinds and aliases it looks for from `bundled_spec()`; none keeps a literal set.
- None keeps a per-hit allow-list, sanctioned table or exception entry; a hit is fixed by deriving the name.
- The scope is `src/squads` outside `_specs/` and `_migrations/`, the spec layer and the frozen vocabulary of released runners.
- The guard on generated agent text renders that text for the override test squad and fails on any bundled name that squad's spec drops.
- Each guard fails when a bundled name is added to a scratch copy of a source file (checked once per guard against a known positive).
- A search of `tests/meta` for allow-list constructs in the vocabulary guards finds none.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Permanent override test squad and its CI job

<!-- sq:story:US10:body -->
As a maintainer, a squad whose vocabulary shares nothing with the bundled one is a permanent test squad, and CI runs the CLI surface suite on it.

ADR-1250 section 10; ADR-1172.

Done when:
- The audit override squad is checked in beside the bundled test squad. Its override drops every bundled work-item type, sub-entity kind and badge field and declares `initiative` (kind `outcome`), `job` (kind `action`), fields `urgency` and `impact`, a reference type with a mapping kind, a kind with a field and a deferred status, create-time attributes of each kind, and a root alias of a dropped type.
- The `tests/cli` surface suite runs on it as well as on the bundled squad, with the same coverage and verb-parity guards.
- A CI job runs the suite on the override squad on every pull request.
- The generated-text guard (US9) and the acceptance scenario of this feature run on it.
- A case that passes on the bundled squad and fails on the override squad fails the CI job, shown once by reintroducing a static `--priority`.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T19:16:52Z] `op-pierre` Pierre Chat:
  - 2026-10-29: in scope as well: (1) the vocabulary guards derive what they check from the spec and lose their exception lists, covering badge codes, aliases and generated text; (2) the audit override squad (initiative/outcome, job/action, urgency, impact) becomes a permanent test squad and the CLI surface suite also runs on it in CI. Storage goes generic with a schema migration (see ADR-1250).
- [2026-10-29T19:57:07Z] `tech-lead` Olivia Lead:
  - Broken into eight tasks, all Draft, ordered by depends-on. Pair 1: TASK-1251 (storage and the 0.19 runner, US6) beside TASK-1252 (aliases, neutral grammar names and target kind, heading key, generated text, override test squad: US2, US4, US5, US10). Pair 2: TASK-1253 (item badge options, list column, import: US1, US3) beside TASK-1254 (mapping option, messages, wire shapes and render context: US4, US1, US5, US7). Pair 3: TASK-1255 (rename-field and check, US8) beside TASK-1256 (guards, the suite on the override squad and CI, repo squad migration: US9, US10, US6). TASK-1257 (VS Code, typescript-dev) after TASK-1254; TASK-1258 (docs and CHANGELOG, tech-writer) last.
  - Storage does not have to land alone: TASK-1252 shares only _workflow/_validity.py (different functions) and one-token maps_parent_story renames with it. The wire and template shapes stay unchanged in TASK-1251 and move in TASK-1254. Repo squad migration waits for the release cut (TASK-1256 ST6), since the released sq refuses a 0.19 squad. @manager ready for dispatch after the bug batch.
<!-- sq:discussion:end -->
