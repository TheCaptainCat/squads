---
id: ADR-1250
sequence_id: 1250
type: decision
title: No bundled vocabulary is special-cased outside the spec
status: Accepted
author: architect
refs:
- ADR-323
- ADR-348
- ADR-622
- REV-1247
- MILE-1241
- ADR-1007
- ADR-322
- ADR-1172
- ADR-541
- ADR-738
- ADR-864
- ADR-1109
- FEAT-1249
description: Options, import keys, stored keys, wire keys and generated text derive
  from the active spec; badge values and the mapping are stored flat under declared
  or neutral keys
created_at: '2026-10-29T19:08:39Z'
updated_at: '2026-10-29T19:51:16Z'
---
<!-- sq:body -->
## Context

The workflow spec is the only authority for item types, sub-entity kinds, badge fields and aliases (ADR-322, ADR-323, ADR-348). An audit of the code outside `_specs/` and `_migrations/` (REV-1247, architect comment b0dc838, 2026-10-29) drove a squad whose override drops the bundled work types and kinds and declares `initiative` (kind `outcome`, field `urgency`) and `job` (kind `action`, field `impact`). Bundled vocabulary is still special in five places:

- **Badge options.** `create`, `<type> <n> update`, `list` and `tree` carry static `--priority`, `--no-priority` and `--min-priority` options and dedicated request fields. A squad with no `priority` field gets a hidden flag that answers "updated" or "no items" with exit 0, and no `--urgency` on `update`, `list` or `tree`. The `list` table has a fixed "Priority" column.
- **Story mapping.** `--story` resolves against the literal kind `story`. Its help, the `Story` column, the `story:` label and the messages ("user story OC9 not found") name the bundled kind whatever the parent hosts.
- **Import.** `sq import` has fronts only for `add-story`, `add-subtask` and `add-finding`, and comment selectors only for `story`, `subtask` and `finding`. In the audit squad, `add-outcome` does not exist.
- **Root aliases.** `RESERVED_CLI_ALIASES` reserves the ten bundled aliases in every squad. A spec that drops `feature` and gives `f` to `initiative` is refused at load.
- **Storage and wire.** `priority` and `severity` are core keys with typed slots on `Item`. A sub-entity stores `severity` and `story` in typed slots and every other field in a nested `extra` mapping. Tree and graph nodes carry a fixed `priority` key, and sub-entity objects a fixed `severity`, `story` and `extra`. The spec key `maps_parent_story`, the validator `subtask_story_mapping` and the transform function `milestone_rollup` name bundled vocabulary for generic mechanisms.

Generated agent text has the same defect. The squads skill teaches `sq f 26 story 4 show` and "(story/subtask/finding blocks)" in a squad where neither exists. The guards meant to catch this carry hand-kept literal sets and per-hit allow-lists, which is how the cases above passed them.

## Decision

### 1. The rule

**No bundled vocabulary is special-cased outside the spec: not in the CLI, import, storage, wire shapes, generated text or the guards.** Code outside `_specs/` and `_migrations/` does not name a bundled type, sub-entity kind, badge field, collection, status or alias to decide an option, a column, a message, an import key, a stored key, a wire key or a generated line. It resolves what it needs from the active spec: a declared field, the kind a type hosts, a declared capability, a status role or a ref-kind semantic. A template looked up by the declared name, with the generic template as the fallback, is not a special case.

**Every name is derived, every label comes from the spec.** An option, an import key and a stored key are spelled after the declaration they derive from. A bundled squad sees `--priority` and `--story` because the bundled spec declares a field `priority` and a kind `story`, not because the code knows them. No static spelling and no alias of a bundled name exists. Every human-facing word reads the declared vocabulary: help text, a column header, a show or head label, a refusal message, in the CLI and in the clients (VS Code, the TUI). Messages use the declared `plural` and label, and are phrased so they need no article chosen in code ("a initiative").

**Grammar names the mechanism, not a bundled instance.** A spec key, a validator name or a transform name that every squad writes is neutral:

| Bundled-word name | Neutral name |
|---|---|
| `maps_parent_story` (kind key) | `maps_to_parent` |
| `subtask_story_mapping` (validator) | `subentity_mapping` |
| `milestone_rollup` (transform function in `squads._view_transforms`) | `status_rollup` |

The bundled view keeps the name the bundled spec declares for it (`[views.milestone_rollup]`), since a view name is spec vocabulary like a type name.

### 2. Badge-field options

Every badge-field option is derived from the declared fields when the command's parameters are resolved. A field code with underscores gets a flag with dashes.

- **`sq create <type>`:** `--<code>` for each field the type declares.
- **`sq <type> <n> update`:** `--<code> <value>` for each field the type declares, and `--no-<code>` for each optional one. A required field has a default and is not cleared.
- **`sq <type> <n> add-<kind>` and `... <kind> <k> update`:** `--<code>` for each field the kind declares, and on `update` `--no-<code>` for each optional one.
- **`sq list` and `sq tree`:** `--<code> <value>` and `--min-<code> <value>` for each field that some non-roster type declares. They mean exactly `--badge <code>=<value>` and `--min-badge <code>=<value>`. `--min-<code>` exists for a field on an ordered collection.
- `--set`, `--unset`, `--badge`, `--min-badge` and `--sort` are the generic forms. Each refuses a code that no non-roster type declares, naming the declared codes.

No request DTO carries a field by name: values travel in the generic fields map, and `ItemCreateRequest.priority`, `ItemUpdateRequest.priority` and `clear_priority` go. A squad that declares no `priority` field has no `--priority` anywhere, and Click refuses it as unknown.

The `list` table has one badge column: the first field on an ordered collection in type declaration order, headed by that field's label, and none when no type declares a field.

### 3. Sub-entity mapping

A kind that declares `maps_to_parent = true` maps each of its sub-entities to a sub-entity of the host item's parent. The **target kind** is the kind hosted by the host type's `parent_required` type. Spec load refuses a mapping kind hosted by a type that declares no `parent_required`, or whose `parent_required` type hosts no kind, naming the type and both remedies (declare `parent_required`, or drop `maps_to_parent`). The engine never guesses a target.

- **Option.** `add-<kind>` takes `--<target-kind> <local-or-id>`, and `<kind> <k> update` takes `--<target-kind>` and `--no-<target-kind>`: `--story` in a bundled squad, `--outcome` in one whose parent hosts `outcome`. Its help, the mapping column header, the show and head label and every message take the target kind's label and `local_prefix` ("outcome OC9 not found in INI-2", "as `OC<n>`").
- **Validator.** `subentity_mapping` checks each mapping against the parent's sub-entities and names the target kind.
- **Container heading.** A kind declares its container heading under a new `heading` key in `[subentity_kinds.<kind>]` (additive spec grammar). When the key is absent, the heading is the title-cased `plural`. The bundled spec declares the three bundled headings, and the code table that held them goes.

### 4. Import

The import surface follows the CLI, so an adopter who knows `sq initiative 2 add-outcome` predicts `{"op": "add-outcome"}`:

- **`add-<kind>`** is accepted for every kind the active spec declares. It is `add-sub` with `kind` set. It takes `add-sub`'s keys, plus each field the kind declares as a top-level key under its code, plus the target kind's name when the kind maps (`"story": "US1"`, `"outcome": "OC9"`).
- **`add-sub`** takes the mapping as `maps_to` and fields in `fields`, the same keys the stored entry uses.
- **The comment selector** `"<kind>": "<local-or-handle>"` is accepted for every declared kind. The generic `sub: [kind, local-or-handle]` stays.
- An op or selector for a kind the active spec does not declare is unknown, and the refusal names the declared `add-<kind>` ops. `create` and `update` take badge fields by code in `fields` and `unset_fields`, with no key named after a field.

### 5. Root aliases

The root command table resolves a type token through the active spec's aliases. The bundled groups and their aliases register from `bundled_spec()`: there is no code table of aliases, and `RESERVED_CLI_ALIASES` goes. Spec load checks an alias against the fixed verbs (`RESERVED_CLI_VERBS`), the declared type names and the other declared types' aliases, all in the active spec. An alias whose bundled owner the active spec drops, or whose aliases it overrides, is free for another type.

### 6. Storage: every value under its declared key

**Frontmatter.** An item stores each badge value at the top level under its field code, as every custom field already does. `priority` and `severity` stop being core keys. A sub-entity entry in the parent's `subentities` list is flat in the same way:

- **Sub-entity core keys:** `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`. `maps_to` holds the local id of the mapped sub-entity in the parent, and is written only when set, like `deferred_to`.
- **Every other key** is an attribute of the entry: each declared field under its code, and any unknown key, kept through every write, repair and migration. The `extra` container goes.

```yaml
subentities:
  - local_id: ST2
    title: Render the form
    status: Todo
    maps_to: US1
  - local_id: F3
    title: Unchecked index read
    status: Open
    severity: high
```

**Why `maps_to`, not the target kind's name.** The value is the only stored fact; the target kind is derivable from the spec and from the value's own `local_prefix`. A key spelled after the kind would store that derivable name a second time and orphan every mapping when an override renames the kind. One fixed key cannot.

**In memory.** `Item.attributes` is the one mapping of every non-core key, badge values included, and `SubEntity.attributes` is its counterpart on an entry. `Item.priority`, `Item.severity`, `SubEntity.severity`, `SubEntity.story` and `SubEntity.extra` go; `SubEntity.maps_to` is the one typed mapping slot. A badge value is read and written through `badge_value(code)` / `set_badge_value(code, value)` on both models, which index `attributes`. Parsing stays spec-free: the model cannot tell a field from an attribute without the spec, so it keeps one flat mapping and the spec classifies it at read time.

**The index.** `.squads.json` serializes the same models and is rebuilt from the files, so it takes the new shape with no rule of its own.

**A dropped or renamed field.** A stored value whose key the active spec no longer declares on that type or kind is an unknown key: kept, never a load refusal, and reported by `sq check` under `frontmatter_key_undeclared`, which now also scans sub-entity entries. The loader cannot tell a rename from a drop, and refusing would make a field impossible to remove without first deleting data. The remedy is a new verb, beside `rename-type` and `rename-status`:

- **`sq migrate rename-field <old> <new>`** moves every stored value from key `<old>` to key `<new>`, on items and sub-entities, in one transaction. It refuses, writing nothing, when an entry's type or kind does not declare `<new>`, when an entry already holds `<new>`, or when a moved value is not a badge of `<new>`'s collection. The `frontmatter_key_undeclared` finding names it.

A renamed kind needs no data move: the mapping key is fixed, and the local ids keep their prefix while `local_prefix` is unchanged.

**One collision rule for stored keys.** Spec load refuses, naming the key and what it collides with:

- an item field code or attribute key equal to an item core key, `path`, `prefix`, a key `--json` adds to an item row, or another field or attribute of the same type;
- a kind's field code equal to a sub-entity core key, a key `--json` adds to a sub-entity object (`body`, `badges`, `discussion`, `display`), or another field of the same kind;
- a derived flag or import key equal to a fixed name on its surface: a field code or target kind against the fixed options of the command it derives onto, a kind named `sub`, a kind or field whose import key equals a fixed key of its op. The refusal names the surface and the fixed name.

All collisions are checked against the active spec only.

### 7. Wire shapes

- **Item rows** (`list`, `show`, `create`, `mine`): `priority` and `severity` leave the core keys. A stored badge value appears at the top level beside the other attributes, only when the file stores it; `badges` carries every declared field.
- **Tree and graph nodes:** the `priority` key goes. `badges` carries every field.
- **Sub-entity objects** (in `subentities`, the sub-entity lists and `<kind> <k> show`): the keys are `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`, then each stored attribute flat, then `body`, `badges`, `discussion`, `display`. `maps_to` and `deferred_to` are always present, `null` when unset. `severity`, `story` and `extra` go.
- **Display:** the sub-entity row's `display.story` becomes `display.maps_to`, the mapped sub-entity as shown.
- **Catalog:** the `sq workflow subentity-kinds --json` column `maps_parent_story` becomes `maps_to_parent`.
- **Render context:** the sub-entity head and the item templates receive the declared fields as a list of `{code, label, badge}` and the mapping as `{label, value}` (the target kind's label and the `maps_to` value), instead of the `severity`, `severity_label` and `story` names.

The clients read badge values from `badges` and labels from `display` and the catalogs, never from a field-named key.

### 8. Schema version and migration

The change to the stored sub-entity entry and to the frozen `--json` shapes is a schema change. `SCHEMA_VERSION` moves from `0.17` to the release that ships it, with one new runner in `_migrations/_registry.py`.

**The runner** walks every item file of every type, roster included, and rewrites only `subentities` entries:

- `story: X` becomes `maps_to: X`;
- each key of `extra` moves to the entry's top level, and `extra` goes;
- an empty `severity` (the loose spelling the model tolerated) is dropped.

Item top-level keys are not touched: `priority: high` and `severity: critical` are already stored under their field code. Body bytes and markers are untouched. The runner first scans every file and refuses the run, exit 1 with nothing written, when an entry holds both `story` and `maps_to`, or an `extra` key equal to a sub-entity core key or to a key already at the entry's top level; the refusal names the item and the key. Both arise only from hand edits. **Idempotence:** an entry with no `story` and no `extra` is left byte-identical, so a second run rewrites nothing. `sq migrate up` then rebuilds `.squads.json` from the files.

**What the runner does not rewrite**, listed in the migration's `manual` step:

- An override that spells `maps_parent_story`, `subtask_story_mapping` or the transform `milestone_rollup` is refused at load with a message naming the neutral name, so `sq migrate up` stops before any runner, nothing migrated, until the override is edited.
- An override template that reads a name this change removes (the sub-entity head's `severity`, `severity_label` and `story`, an item's `.priority` or `.severity`, a sub-entity's `.story` or `.extra`) fails to render under `StrictUndefined`. The step names the generic context that replaces each one (§7).
- Reflog entries keep the keys they recorded: they are history.

This repository's squad is brought up to date by the same runner.

### 9. Guards derive from the spec

Every vocabulary guard in `tests/meta` reads the names it looks for from `bundled_spec()`: the type names, sub-entity kind names, field codes, collection names, statuses, ref kinds and aliases. None keeps a literal set, and none keeps a per-hit allow-list, sanctioned table or exception entry: a hit is fixed by deriving the name, never by listing it. The scope is `src/squads` outside `_specs/` and `_migrations/`, the spec layer and the frozen point-in-time vocabulary of released runners. The guard on generated agent text renders that text for the permanent override test squad (below) and fails on any bundled name that squad's spec drops.

### 10. A permanent override test squad

The audit squad becomes a permanent test squad beside the bundled one. Its override drops every bundled work-item type, sub-entity kind and badge field, and declares its own covering every capability the CLI surface suite exercises: a reference type with a mapping kind, a kind with a field and a deferred status, create-time attributes of each kind, a root alias of a dropped type, and the audit's `initiative`/`outcome`, `job`/`action`, `urgency` and `impact`. The CLI surface suite runs on it as well as on the bundled squad, as ADR-1172 states.

### 11. Narrowing the older decisions

Each overlap below is a clause-level amendment (board rule 6): the older decision is narrowed in place to the text given, with an "Amended in place" comment, and linked `related`. None is superseded, because their other sections stand.

- **ADR-323 §4.** Replace "A sub-entity's entry in its parent's frontmatter carries `severity` in its own slot and any other declared field under its code in the entry's `extra` mapping." with "A sub-entity's entry in its parent's frontmatter stores every declared field the same way, flat under its code (ADR-1250 §6)." In the collision sentence, replace "`path`, `prefix` or `extra`" with "`path` or `prefix`, and a kind's field code may not collide with a sub-entity core key".
- **ADR-323 §5.** Replace the two bullets and the closing paragraph with: "`create`, `update`, `add-<kind>`, `list` and `tree` derive `--<code>`, `--no-<code>` (optional fields, on update) and `--min-<code>` (ordered fields, on list and tree) from the declared fields at parameter resolution. `--set`, `--unset`, `--badge`, `--min-badge` and `--sort` are the generic forms. No option is named in code. See ADR-1250 §2."
- **ADR-348 §1.** Replace the `maps_parent_story` row with `maps_to_parent` | `bool = False` | "Capability: this kind maps to a sub-entity of the host's `parent_required` type (drives `--<target-kind>` and its column)". Add a `heading` row: `str | None = None`, the container heading, title-cased `plural` when absent. In the derived-columns bullet, replace "a `Story` column iff `maps_parent_story`" with "a column headed by the target kind's label iff `maps_to_parent`".
- **ADR-348 §4.** Replace the paragraph's first sentence with: "A sub-entity entry stores every declared field's badge code flat under its code, and the mapping under `maps_to` (ADR-1250 §6)."
- **ADR-348 §7.** Retitle it "Sub-entity mapping is declared" and replace its body with: "A kind declaring `maps_to_parent` maps each sub-entity to a sub-entity of the host type's `parent_required` type, whose hosted kind is the target. The option is `--<target-kind>`, the stored key is `maps_to`, the validator is `subentity_mapping`, and every label and message names the target kind. See ADR-1250 §3."
- **ADR-622, Addressing.** Replace "`add-story`/`add-subtask`/`add-finding`" with "`add-<kind>`/`add-sub`".
- **ADR-622, The op set.** In `create`, replace "badge fields (`priority`, `severity`, …)" with "`fields` (field code to badge code)". In `comment`, replace "(`story`/`subtask`/`finding`, ...)" with "(`<kind>` for any declared kind, or the generic `sub: [kind, local-or-handle]`)". Replace the `add-story / add-subtask / add-finding` bullet with: "**`add-<kind>`**, for every declared kind: `add-sub` with `kind` set, plus the kind's field codes as top-level keys and the target kind's name when the kind maps. **`add-sub`** is the generic form, with `fields` and `maps_to`." In `update`, replace "`priority`" with "`fields`/`unset_fields`". In the closing paragraph, replace "(status/assignee/severity/story mapping)" with "(status, assignee, field values, mapping)". See ADR-1250 §4.
- **ADR-1007 §1.** Remove `priority` and `severity` from the core-key list and the sentence "`priority` and `severity` stay core because they are already model fields with engine readers; their collections remain spec-declared (ADR-323)." In §4, replace "like `priority`" with "like every badge field".
- **ADR-541, ADR-738, ADR-864, ADR-1109.** Each names `maps_parent_story`, `subtask_story_mapping` or the `milestone_rollup` transform function; the name is replaced by its neutral name from §1, with no other change.

## Consequences

- The bundled squad's item frontmatter is unchanged; its sub-entity entries change only where they carry `story` or `extra`. Its CLI flags, import ops and aliases have the same spellings, now derived.
- A squad that declares no `priority` field gets "No such option: --priority" instead of a hidden flag or an exit-0 no-op. The CHANGELOG records it as a fix.
- Every `--json` client that reads `priority` on a tree or graph node, or `severity`, `story` or `extra` on a sub-entity, moves to `badges` and `maps_to`. The VS Code extension and the TUI do so in the same change. The daemon's HTTP surface carries the new shapes from its first release.
- A mapping kind on a type with no `parent_required` is refused at load. No bundled type is affected.
- `docs/stability.md` changes in Tier 1 ("Sub-entity state lives in frontmatter", "Frontmatter is flat"), Tier 2 (aliases, migrate sub-app, bulk import, a new badge-options entry) and Tier 3 (item rows, tree and graph nodes, sub-entity objects and display, the sub-entity-kinds catalog). The entries are listed on this decision's discussion.
- The audit override squad is the acceptance scenario: under it, every surface the audit drove gives the derived flag, the target kind's wording, the derived import op, the reassigned alias and the flat storage.

## Options considered

- **One ADR stating the rule, narrowing the older clauses in place (chosen).** One rule covers every surface; board rule 6 prescribes in-place narrowing for a clause-level overlap.
- **Keep the frozen keys and typed slots until 1.0, deriving only labels.** Rejected by the operator (2026-10-29): it leaves the storage, the wire and a static `--story` special in every squad, the exact debt this rule removes, and gets more expensive after 1.0.
- **Store the mapping under the target kind's name.** Rejected: the kind name is derivable, and a kind rename would orphan every mapping (§6).
- **A separate `fields` mapping beside `attributes`.** Rejected: frontmatter is flat and parsing is spec-free, so the model cannot split a key into a field or an attribute at read; one mapping per level, classified by the spec, is what the file holds.
- **Refuse at load when a stored key's field is dropped or renamed.** Rejected: the loader cannot tell a rename from a drop, and a field could not be removed without first deleting data. The value is kept, reported, and moved by `rename-field`.
- **Migrate a renamed field automatically from the override diff.** Rejected for the same reason: a rename is not distinguishable from a drop plus an add.
- **Keep a static `--priority`, or a `--story` alias beside the derived flag.** Rejected: two spellings for one value, and a flag that parses in a squad without the field.
- **Supersede ADR-323, ADR-348, ADR-622 and ADR-1007.** Rejected: their other sections stand.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T19:09:07Z] `architect` Robert Architect:
  - Docs to update once this decision is accepted (tech writer):
    
    docs/stability.md
    - Tier 2, "Type-command aliases" (lines 580-599): the table freezes what the bundled spec declares. A release may not remove or repurpose a bundled alias. A squad's override may give an alias to another type once the bundled owner no longer declares it (§5).
    - Tier 2: no section covers badge-field options. Add a short one under the item grammar: `--<code>` on create and add-<kind>, `--<code>`/`--no-<code>` on update, `--<code>`/`--min-<code>` on list and tree, all derived from the declared fields. `--priority`/`--min-priority` are the bundled field's derived names (§2).
    - Tier 2, "Bulk import" (lines 630-641): `add-<kind>` and the `<kind>` comment selector exist for every declared kind; `add-sub` and `sub` are the generic forms (§4).
    - Tier 3, tree and graph node tables (lines 916 and 934): `priority` keeps its name and is `null` in a squad that declares no `priority` field; `badges` carries every field.
    - Tier 1, "Sub-entity state lives in frontmatter" (line 66) and Tier 3 sub-entity row (line 825): the key stays `story`; one clause saying it holds the mapped sub-entity of whatever kind the parent hosts.
    
    Adopter docs, same pass:
    - docs/workflow.md:1000-1001 and docs/overrides.md:1542-1543: "sugar" for the bundled priority axis becomes "every field gets `--<code>`, `--no-<code>` and `--min-<code>`".
    - docs/adoption.md:254-256: the three op rows become one `add-<kind>` row, with the bundled kinds as examples.
    - docs/overrides.md: document the new `heading` key on `[subentity_kinds.<kind>]`.
    - docs/workflow.md:331: `--story` maps to the target kind the parent hosts.
    
    @manager: ADR-1250 is up for the operator. The ADR-1172 rule 5 exception is in place (comment above that ADR's last entry).
- [2026-10-29T19:13:27Z] `op-pierre` Pierre Chat:
  - 2026-10-29: no sugar and nothing hardcoded, not even --story. Every option, column, label, message and import key is derived from the spec: the mapping option is named after the target kind (--story only because the bundled kind is story; --outcome when the parent hosts outcome). No static or alias spelling survives for a bundled name.
- [2026-10-29T19:16:51Z] `op-pierre` Pierre Chat:
  - 2026-10-29: the rule covers storage too. Badge values and the sub-entity mapping are stored under their declared key (frontmatter and JSON), and the dedicated typed slots (Item.priority, Item.severity, SubEntity.severity, SubEntity.story) go. A schema migration carries existing squads; the stability contract changes before 1.0.
- [2026-10-29T19:25:56Z] `architect` Robert Architect:
  - Revised 2026-10-29 per op-pierre dde0bae and f2f60a7 (and ca59f6b on FEAT-1249). Changes from the previous text:
    - No derived name has a bundled spelling: `--story` is `--<target-kind>`, the import mapping key is the target kind's name, `RESERVED_CLI_ALIASES` goes, and `maps_parent_story`, `subtask_story_mapping` and the `milestone_rollup` transform function get neutral names.
    - The target kind is the kind hosted by the host type's `parent_required` type; a mapping kind without one is refused at load. No fallback.
    - New §6-§8: badge values stored flat under their field code on items and sub-entities (`priority`/`severity` leave the core keys, `extra` goes), the mapping under a fixed `maps_to` key, one `attributes` mapping per level, wire keys follow, a schema bump with one runner, and `sq migrate rename-field` for a renamed field.
    - New §9-§10: guards read their names from the bundled spec with no allow-lists; the audit squad is a permanent test squad (ADR-1172 amended in place).
    - §11 narrows ADR-323 §4/§5, ADR-348 §1/§4/§7, ADR-622, ADR-1007 §1/§4 and the names in ADR-541/738/864/1109.
    Stability-doc entries (tech writer, replaces the list in d06d909):
    - Tier 1 "Sub-entity state lives in frontmatter": severity and mapped story become each declared field under its code and the mapping under `maps_to`; entries are flat, no `extra`.
    - Tier 1 "Frontmatter is flat": drop `priority` and `severity` from the core keys; every badge field is stored as an attribute under its code; unknown keys on sub-entity entries are kept too; a dropped field's values are moved by `sq migrate rename-field`.
    - Tier 2: alias table freezes the bundled spec's declaration only; migrate sub-app gains `rename-field`; bulk import gets `add-<kind>`, the `<kind>` selector and `maps_to` on `add-sub`; a new badge-options entry.
    - Tier 3: item rows lose `priority`/`severity` as always-present keys; tree and graph nodes lose `priority`; sub-entity objects drop `severity`, `story`, `extra`, gain `maps_to` (always present) and flat field keys; display `story` becomes `maps_to`; the subentity-kinds catalog column `maps_parent_story` becomes `maps_to_parent`.
    @manager ADR-1250 is ready for the operator again. Open points are in my handback.
- [2026-10-29T19:38:50Z] `op-pierre` Pierre Chat:
  - 2026-10-29: on the open points: the mapping is stored under the neutral key maps_to; derived per-field flags sit beside the generic --set/--badge/--min-badge; a value under a renamed or dropped field code is kept as an unknown key, reported by sq check, and moved by sq migrate rename-field; a mapping kind on a type without parent_required is refused at spec load. The release is 0.19.0, so the schema becomes 0.19.
- [2026-10-29T19:46:00Z] `op-pierre` Pierre Chat:
  - 2026-10-29: ADR-1250 accepted.
- [2026-10-29T19:51:16Z] `architect` Robert Architect:
  - §11 applied 2026-10-29: ADR-323 §4/§5, ADR-348 §1/§4/§7, ADR-622 (Addressing, the op set), ADR-1007 §1/§4, and the neutral names in ADR-541, ADR-738, ADR-864 and ADR-1109 are amended in place, each with a dated comment and a related ref back here. ADR-1172 needed nothing further (its amendment b2bb2a8 already matches §10). Statuses unchanged.
<!-- sq:discussion:end -->
