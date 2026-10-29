---
id: ADR-1250
sequence_id: 1250
type: decision
title: No bundled vocabulary is special-cased outside the spec
status: Proposed
author: architect
refs:
- ADR-323
- ADR-348
- ADR-622
- REV-1247
- MILE-1241
- ADR-1007
- ADR-322
description: CLI options, import ops, aliases and generated text derive from the active
  spec; frozen keys keep their names, labels come from the spec
created_at: '2026-10-29T19:08:39Z'
updated_at: '2026-10-29T19:09:07Z'
---
<!-- sq:body -->
## Context

The workflow spec is the only authority for item types, sub-entity kinds, badge fields and aliases (ADR-322, ADR-323, ADR-348). An audit of the code outside `_specs/` and `_migrations/` (REV-1247, architect comment b0dc838, 2026-10-29) drove a squad whose override drops the bundled work types and kinds and declares `initiative` (kind `outcome`, field `urgency`) and `job` (kind `action`, field `impact`). Four surfaces still treat bundled vocabulary as special:

- **Badge options.** `create`, `<type> <n> update`, `list` and `tree` carry static `--priority`, `--no-priority` and `--min-priority` options and dedicated request fields. A squad with no `priority` field gets a hidden flag that answers "updated" or "no items" with exit 0. It gets no `--urgency` on `update`, `list` or `tree`. The `list` table has a fixed "Priority" column. ADR-323 §5 allowed this on the grounds that Typer options are fixed at import, but `create` and `add-<kind>` already add options from the active spec in `get_params`, after the per-invocation spec is bound.
- **Story mapping.** `--story` resolves against the literal kind `story`. Its help, the `Story` column, the `story:` label and the messages ("user story OC9 not found") name the bundled kind whatever the parent hosts. ADR-348 §7 calls this "a bounded built-in".
- **Import.** `sq import` has fronts only for `add-story`, `add-subtask` and `add-finding`, and comment selectors only for `story`, `subtask` and `finding`. In the scratch squad, `add-outcome` does not exist. ADR-622 lists these fronts by name.
- **Root aliases.** `RESERVED_CLI_ALIASES` reserves the ten bundled aliases in every squad. A spec that drops `feature` and gives `f` to `initiative` is refused at load: "alias 'f' shadows the built-in sq f alias of the 'feature' command".

Generated agent text has the same defect. The squads skill teaches `sq f 26 story 4 show` and "(story/subtask/finding blocks)" in a squad where neither exists.

Some names are frozen and must not change before a major release: the frontmatter keys `priority`, `severity` and a sub-entity's `story` (stability Tier 1), the `priority` key on tree and graph nodes and the `story` key on sub-entity rows (Tier 3), the `maps_parent_story` spec key, and the `subtask_story_mapping` validator name.

## Decision

### 1. The rule

**No bundled vocabulary is special-cased in the CLI, in import or in generated text.** Code outside `_specs/` and `_migrations/` does not name a bundled type, sub-entity kind, badge field, collection, status or alias to decide an option, a column, a message, an import op or a generated line. It resolves what it needs from the active spec: a declared field, the kind a type hosts, a declared capability (`maps_parent_story`), a status role or a ref-kind semantic. A template looked up by the declared name, with the generic template as the fallback, is not a special case.

**Frozen keys keep their names, and their labels come from the spec.** A frozen storage, wire or grammar name stays as it is. Every human-facing word that renders it reads the declared vocabulary: help text, a column header, a show or head label, a refusal message. This covers the clients (VS Code, the TUI) as well as the CLI. Messages built from vocabulary use the declared `plural` and the declared label. They are phrased so that they need no article chosen in code ("a initiative").

**One collision rule.** When a name the spec declares derives a flag, an import key or a root command, spec load refuses it if it equals a fixed name on that surface. The refusal names the surface and the fixed name. Collisions are checked against the active spec only.

### 2. Badge-field options

Every badge-field option is derived from the declared fields when the command's parameters are resolved, as `create` already does. A field code with underscores gets a flag with dashes.

- **`sq create <type>`:** `--<code>` for each field the type declares.
- **`sq <type> <n> update`:** `--<code> <value>` for each field the type declares, and `--no-<code>` for each optional one. A required field has a default and is not cleared.
- **`sq <type> <n> add-<kind>` and `... <kind> <k> update`:** `--<code>` for each field the kind declares, and on `update` `--no-<code>` for each optional one.
- **`sq list` and `sq tree`:** `--<code> <value>` and `--min-<code> <value>` for each field that some non-roster type declares. They mean exactly `--badge <code>=<value>` and `--min-badge <code>=<value>`. `--min-<code>` exists for a field on an ordered collection, which today is every field (ADR-323 §3).
- `--badge`, `--min-badge`, `--sort`, `--set` and `--unset` stay. Each refuses a code that no non-roster type declares, naming the declared codes.

`--priority`, `--no-priority` and `--min-priority` exist only as the derived names of the bundled `priority` field. There is no static option and no request field dedicated to priority. The value travels in the generic fields map, and `ItemCreateRequest.priority` and `ItemUpdateRequest.priority`/`clear_priority` go. A squad that declares no `priority` field has no `--priority` anywhere, and Click refuses the flag as unknown. A bundled squad sees the same flags with the same meaning as before.

The `list` table has one badge column: the first field on an ordered collection in type declaration order (`first_ordered_field`), headed by that field's label. It has none when no type declares a field. `tree` and `show` already render every declared field.

### 3. Story mapping

A kind that declares `maps_parent_story` maps each sub-entity to a sub-entity of the host item's parent. The target kind is the kind the parent's type hosts, resolved from the spec. Code never names `story` to find it. When the host type declares no required parent, the fallback message names the kind the actual parent hosts.

`--story` and `--no-story` keep their names. They are grammar in the same sense as the `story` key: one spelling in every squad. Their help, the mapping column header, the show and head label and every message take the target kind's label and `local_prefix` ("outcome OC9 not found in INI-2", "as `OC<n>`"). No `--<target-kind>` alias is derived. A second spelling would add collision cases and buys nothing an adopter can't already read from `--help`.

A sub-entity kind declares its container heading under a new `heading` key in `[subentity_kinds.<kind>]` (spec grammar, additive). When the key is absent, the heading is the title-cased `plural`. The bundled spec declares the three bundled headings, and the code table that held them goes. `sq workflow subentity-kinds --json` already publishes the resolved value as `container_heading`, so that catalog is unchanged.

### 4. Import

The import surface follows the rule the CLI follows, so an adopter who knows `sq initiative 2 add-outcome` predicts `{"op": "add-outcome"}`:

- **`add-<kind>`** is accepted for every kind the active spec declares. It is `add-sub` with `kind` set to that name. It takes `add-sub`'s keys, plus each field the kind declares as a top-level key under its code. It also takes `story` when the kind declares `maps_parent_story`.
- **The comment selector** `"<kind>": "<local-or-handle>"` is accepted for every declared kind. The generic `sub: [kind, local-or-handle]` stays.
- In a bundled squad, `add-story`, `add-subtask`, `add-finding` and the `story`, `subtask` and `finding` selectors behave as before, because the bundled spec declares those kinds. In a squad that drops one, its op is unknown, and the refusal names the declared `add-<kind>` ops.
- `create` and `update` already take badge fields by code in `fields`. They are unchanged.

The collision rule refuses a kind named `sub`, and a kind or field whose import key equals a fixed key of the op it derives onto.

### 5. Root aliases

The root command table resolves a type token through the active spec's aliases. `RESERVED_CLI_ALIASES` is the bundled spec's declaration, used to register the bundled groups at import. It is not a reservation. Spec load checks an alias against the fixed verbs (`RESERVED_CLI_VERBS`), the declared type names and the other declared types' aliases, all in the active spec. So once the bundled owner no longer declares an alias, because the type is dropped or its aliases are overridden, another type may declare it. A bundled alias that the active spec does not declare is still refused as stale, naming the fix.

The Tier 2 alias table freezes what the bundled spec declares: in a squad that does not override them, each bundled alias names its bundled type, and a release may not remove or repurpose one. A squad's own override may.

### 6. Generated text

Generated skills, the workflow cheatsheet and item scaffolds take their examples from the active spec: the first aliased type and the kind it hosts, and `item.type` in every scaffold hint. They drop parenthetical lists of bundled kinds. A note keyed by a bundled kind's name moves into the spec or is dropped.

### 7. What stays

- The frontmatter keys `priority` and `severity`, the typed `Item.priority`, `Item.severity` and `SubEntity.severity` slots, and the `story` key stay until a major release (Tier 1, ADR-323 §4). This is recorded debt, not a gap.
- The wire keys `priority` on tree and graph nodes and `story` on sub-entity rows stay (Tier 3). Clients take the label from `badges`/`display` and from the target kind.
- `maps_parent_story`, `subtask_story_mapping` and the `milestone_rollup` transform keep their names. A neutral alias name may be added later as an additive change.

### 8. Narrowing the older decisions

This decision overlaps one clause in each of three accepted ADRs. Under board rule 6 each is narrowed in place to the text below, with an "Amended in place" comment, and linked `related`. None is superseded, because their other sections stand.

- **ADR-323 §5.** Replace the two bullets and the closing paragraph with: "`create`, `update`, `add-<kind>`, `list` and `tree` derive `--<code>`, `--no-<code>` (optional fields, on update) and `--min-<code>` (ordered fields, on list and tree) from the declared fields at parameter resolution. `--set`, `--badge`, `--min-badge` and `--sort` remain the generic forms. `--priority` and `--min-priority` are the derived names of the bundled `priority` field, not static options. See ADR-1250 §2."
- **ADR-348 §7.** Retitle it "Story mapping is declared". Replace the last sentence with: "The target kind is the kind the parent's type hosts, resolved from the spec. `--story` keeps its name, and its help, column, labels and messages name the target kind. See ADR-1250 §3." Add `heading` to §1's stored vocabulary.
- **ADR-622, The op set.** Replace the `add-story / add-subtask / add-finding` bullet with: "**`add-<kind>`**, for every declared kind: `add-sub` with `kind` set, plus the kind's field codes as top-level keys and `story` when the kind maps to a parent story. **`add-sub`** is the generic form." In the `comment` bullet, replace "(`story`/`subtask`/`finding`, ...)" with "(`<kind>` for any declared kind, or the generic `sub: [kind, local-or-handle]`)". In Addressing, replace "`add-story`/`add-subtask`/`add-finding`" with "`add-<kind>`/`add-sub`". See ADR-1250 §4.

## Consequences

- The `SANCTIONED` table in `tests/meta/test_render_paths_never_hardcode_a_field_code_literal.py` becomes empty. `--priority` was its only entry.
- Removing the dedicated priority request fields changes the request DTOs of `items.create` and `items.update`. The command layer is not a published contract, and the daemon's HTTP surface carries the generic shape from its first release.
- A squad with no `priority` field now gets "No such option: --priority" from `create`, `update`, `list` and `tree` instead of a hidden flag or an exit-0 no-op. In a bundled squad nothing changes. The CHANGELOG records the refusal as a fix.
- The audit's scratch override is the acceptance scenario. Under it, every command the audit drove gives the derived flag, the target kind's wording, the derived import op and the reassigned alias.
- docs/stability.md and the adopter docs need the edits listed on this ADR's discussion.

## Options considered

- **One ADR stating the rule, narrowing three clauses in place (chosen).** One rule covers four surfaces. Stating it once and narrowing each older clause is what board rule 6 prescribes for a clause-level overlap.
- **Supersede ADR-323, ADR-348 and ADR-622.** Rejected: it would retire three decisions whose other sections stand (the badge model, the kind schema, the import engine) to change one clause each.
- **Three separate amendments, no new ADR.** Rejected: the shared rule would live in three places and the next surface (aliases, generated text) would have no home.
- **Keep `--priority` as static sugar and add the derived flags beside it.** Rejected: two paths for one field, and a flag that is hidden but parses in squads without the field. That is the exit-0 defect.
- **Fold the import fronts into `add-sub` as undocumented aliases.** Rejected: an alias still has to name its kind, so the three bundled names would stay special in every squad, while a custom kind would get no front.
- **Derive `--<target-kind>` beside `--story`.** Rejected: a second spelling with its own collision cases, and nothing an adopter cannot read from the kind's label in `--help`.
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
<!-- sq:discussion:end -->
