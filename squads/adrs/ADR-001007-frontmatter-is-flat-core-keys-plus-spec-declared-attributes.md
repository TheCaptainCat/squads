---
id: ADR-1007
sequence_id: 1007
type: decision
title: 'Frontmatter is flat: core keys plus spec-declared attributes'
status: Accepted
author: architect
refs:
- MILE-934:targets
- ADR-984
- ADR-981
- ADR-971
- ADR-979
- ADR-766
- ADR-696
- ADR-427
- ADR-323
- FEAT-980
- FEAT-986
description: No extra block; slug is core; roster keys are pinned spec attributes;
  unknown keys kept; writes remove only targeted keys; flattened by the 0.16 runner
created_at: '2026-10-15T18:49:27Z'
updated_at: '2026-10-16T16:15:34Z'
---
<!-- sq:body -->
## Context

Each claim is marked **read** (the source was read), **driven** (a command was run and its
output observed) or **inferred** (reasoned from read code, not exercised).

The operator ruled on 2026-10-15 (MILE-934, op-pierre): frontmatter is already scoped by type,
so the nested `extra:` block goes; every key it holds becomes a top-level field; this ships in
0.16 on this release's migration runner. The shape is ruled too: **core keys** are the ones
common to all items and used by the internals; **per-type keys** are generic and declared in
the specs, never hardcoded per type; frontmatter is parsed against core plus declared keys and
validated; **unknown keys are kept silently**. And a guarantee: a key removed from a custom spec
is not removed from the frontmatter the next time an item is saved. This record settles how.
The five points it then left open were ruled by the operator on 2026-10-15 (op-pierre, on this
record): `extra_fields` refused with no alias, the build order in decision 9, `tech` kept on roles,
the operator's `full_name` folded into `title`, and the opt-in check of decision 11.

**Where the keys live today.**

- `Item.extra: dict[str, Any]` (`_models/_item.py:185`) is written as a nested `extra:` mapping
  (`:635`). `Item.model_config` sets no pydantic `extra=` policy, so the default (ignore)
  applies (read).
- An unknown top-level key is dropped on load, is invisible to `sq check` and to
  `sq show --json`, and is erased from the file by the next write that touches the item
  (driven: a hand-added `hand_key: keep-me` on a guide in a scratch 0.15 squad; `sq check`
  reported no issues, `show --json` did not carry it, and `sq guide <n> update --set tags=a,b`
  rewrote the frontmatter without it). The writer replaces the whole frontmatter with
  `to_frontmatter_dict()` (`_itemfile.update_frontmatter`, read).
- Settable keys come from two places: a hardcoded per-roster-type table and a closed catalog of
  value kinds (`_models/_metadata.py`, `EXTRA_FIELDS` and `_GENERIC_FIELDS`), and the spec's
  `extra_fields` list, which may only name keys from that closed catalog: any other name is
  silently not settable (read).
- Custom badge field values with no dedicated attribute are stored in `extra[code]`
  (`Item.badge_value`/`set_badge_value`, read). `priority` and `severity` are already top-level.
- Two legacy folds run on every read: `extra.ref_kinds` into inline refs and `extra.severity`
  into `severity` (`_read_refs`, `_read_severity`, read).

**This corpus** (driven, a frontmatter census of `squads/`):

| type | `extra` keys (items carrying) |
|---|---|
| role | `slug` 10, `is_default` 10, `model` 2, `is_dev` 2, `tech` 2 |
| skill | `slug` 14, `description` 2, `when_to_use` 2, `allowed_tools` 2 |
| operator | `slug` 1, `full_name` 1 |
| milestone | `target_date` 1 |
| guide | `tags` 1, `tech` 1 |

- Every stored roster `slug` equals the slug segment of its file name, 25 of 25 (driven).
- The two skills carrying `extra.description` hold it byte-identical to their top-level
  `description` (driven). `sq skill add` writes `extra.description = description or name`
  (`_services/_roster.py:118`, read), and the Claude Code backend reads
  `extra.description or description or title` (`_backends/_claude_code/_backend.py:371,386`,
  read). Nothing writes `extra.description` after creation (read), so after a description edit
  the stale copy wins.
- No item carries `extra.title`. `ExtraKey.TITLE` is the role catalog's job title, read only as
  a fallback (`_roles/_catalog.py:226`, `_cli/_common.py:1200`) and already retired from role
  items (`RETIRED_ROLE_EXTRA_KEYS`, read). A role item's top-level `title` is the agent's name
  (ADR-766), and `full_name` is retired on roles (read).
- An operator stores its name twice: `title` and `extra.full_name`, both set from the same
  argument by `sq operator add` (`_services/_roster.py:152`, read). No operator verb edits
  either (driven: `sq operator <n>` offers show, rm and status only). Every operator surface
  reads `full_name` first (`_cli/_operator.py`, `operator.md.j2`, read).
- Nine system skills carry a stray top-level `path:` key, written by the 0.5 migration runner
  (read: `git log -S` on SKILL-192 lands on that commit). It is ignored on read today.
- `tech` is declared on guides as a guide attribute (`extra_fields = ["tags", "tech"]`) and is
  stored on templated developer roles. ADR-984 decision 4 keeps `tech` on roles, as the
  template's parameter, and removes only `is_dev`; FEAT-986 US4 says the same (read).

**Readers outside Python.** `sq list`, `show`, `create` and `mine` with `--json` dump
the whole `Item`, so `extra` is a key of every generic item row (read). The VS Code client
reads no `extra` key (read: `src/` has one comment mentioning it). Its skew canary pins
`extra` in `LIST_ROW_KEYS` and pins `TYPE_ENTRY_KEYS` for `sq workflow` type entries (read,
`test/canary/skewCanary.test.ts`). The roster card payloads (`sq role show --json`,
`sq operator list --json`) never emitted `extra` (read, ADR-981). Bundled templates read the
`extra` render variable (`review.md.j2`, `skill.md.j2`, `operator.md.j2`, read), and the
overrides guide tells adopters an unknown key "is preserved in `extra` and available to your
own templates" (`docs/overrides.md`, read).

**Schema.** `SCHEMA_VERSION` is still `"0.15"` on this branch and no 0.15 to 0.16 runner exists
yet; FEAT-980 creates both (read; MILE-934, 2026-10-12). The root gate refuses every command on
a squad whose schema differs from the package in either direction (read,
`require_current_schema`), so an older package never writes a flattened file.

## Decision

### 1. Two kinds of key, one flat mapping

A frontmatter document is one flat mapping. Every top-level key is either **core** or an
**attribute**. There is no nested container on any wire surface: not in frontmatter, not in
`--json`, not in render contexts.

**Core keys** are the model's own fields, common to every item and read by the internals:
`id`, `sequence_id`, `type`, `title`, `slug`, `status`, `description`, `parent`, `author`,
`assignee`, `priority`, `severity`, `labels`, `refs`, `subentities`, `created_at`,
`updated_at`, `created_session`, `modified_session`. `priority` and `severity` stay core because
they are already model fields with engine readers; their collections remain spec-declared
(ADR-323).

**Attributes** are every other key. A type's attributes are declared in the workflow spec, per
type, in one grammar, for built-in, reserved and adopter types alike. No Python table lists the
keys of a type.

### 2. `slug` is core

`slug` is common to every item (`Item.slug` is a required model field on every item, read) and
the internals use it for file names and roster lookups. It has one meaning: the item's handle,
which the file name spells.

- It is written to frontmatter for every item whose type has `category = "roster"`, where it is
  identity (ADR-971) and FEAT-980 builds on it. It is read from frontmatter when present and from
  the file name otherwise, exactly as today.
- On any other item it is written when the file being rewritten carried it, so a hand-added
  `slug:` is never dropped (decision 7).
- `ExtraKey.SLUG` and every `extra.get(X.SLUG, item.slug)` site collapse into `item.slug`.

### 3. The roster keys are attributes declared in the bundled spec, pinned by the loader

`is_default`, `model`, `tech` (role), `when_to_use`, `allowed_tools`, `model` (skill) exist on
only some types, so they are attributes, declared in the bundled `workflow.toml` on `role` and
`skill` like any other type's attributes. Keys the open 0.16 work adds (`origin`, `pronouns`,
`operator_invocable`) are declared the same way by the features that add them.

Because the engine materialises these into agent-host files (ADR-696), the loader **pins** them:
an override may add attributes to a roster type, but a resolved spec whose `role` or `skill`
type lacks a pinned attribute, or declares it with another kind, is refused at load, naming the
key and the remedy. The pinned set and kinds are one table next to the other roster minimum
semantics, not a per-type key list: it says what the engine depends on, and the spec still says
what the type carries.

Internals read an attribute through named constants (the successor of `ExtraKey`, renamed to
`AttributeKey` in `_models/_attributes.py`) and a single accessor on the item
(`item.attribute(AttributeKey.MODEL)`). Typed roster accessors (`role_is_default(item)`, and so
on) wrap it and treat a stored value of the wrong kind as unset; `sq check` reports that value
(decision 5). No reader indexes the mapping by a string literal.

### 4. The declaration grammar

`extra_fields` (a list of catalog names) is replaced by a table, `[items.<type>.attributes]`:

```toml
[items.guide.attributes]
tags = { kind = "list" }
tech = { kind = "str" }

[items.role.attributes]
is_default = { kind = "bool", settable = false }
model = { kind = "str" }
tech = { kind = "str", settable = false }
```

- `kind` is one of `str`, `list` (a list of strings), `bool`, `date` (ISO `YYYY-MM-DD`). It
  replaces the closed `_GENERIC_FIELDS` catalog: an adopter declares a custom attribute of any
  of these kinds on any type, including a roster type.
- `required` (default `false`): a missing required attribute is reported by `sq check`
  (decision 5); it is never a load refusal, so adding `required` to an existing type cannot make
  its items unreadable.
- `settable` (default `true`): whether `sq update --set` writes it. `false` is for keys a
  dedicated verb owns (`is_default` by `sq role set-default`, `tech` by `sq dev add`).
- **Badge attributes stay in `fields`.** A custom badge field (`fields = [{ code, label,
  collection }]`) is stored top-level under its code, like `priority`. Its validation is
  collection membership (FEAT-900's field-value check).
- **Names the loader refuses** for an attribute or a badge code: any core key; any other
  attribute or badge code on the same type; the names `--json` adds to an item row (`badges`,
  `body`, `discussion`, `matched_subentities`); `path` and `prefix` (model fields that are not frontmatter); and
  `extra`.
- An override that still carries `extra_fields` is refused at load with a message naming
  `attributes` and the equivalent table. There is no alias: the old key is never read.

### 5. What "validated" means

Validation never changes or removes a stored value. It decides what a reader may use and what is
reported.

| check | where | on failure |
|---|---|---|
| core key type (as today) | load boundary, `Item.from_frontmatter` | item refused, `SquadsError` naming the file |
| attribute kind | `sq check`, the default validator bundle, `error` | reported; the value stays as written; typed accessors read it as unset |
| required attribute present | `sq check`, same validator | reported |
| badge code in its collection | FEAT-900's field-value check | reported; value kept |
| input to `sq update --set`, `sq import` | the command, before writing | refused; nothing written |

A declared attribute whose stored value fails validation is therefore **kept on read and on
write**: an unrelated write carries it through verbatim, and only a command that targets that key
can replace it, with a value that passes. The core-key row is unchanged from today because the
engine cannot build an item without those.

**Note 2026-10-16.** "Verbatim" means the same JSON-representable value, not the same YAML
type. An attribute value is kept in its JSON form: on load, a YAML-only type is normalized
(`_json_form` in `_models/_item.py`), and the next write of the item stores that form. An
unquoted date or timestamp becomes the string of the same value, in ISO form
(`2026-10-20` becomes `'2026-10-20'`), and a non-string mapping key becomes a string key. The
reason: the index and `--json` carry JSON, and a YAML-typed value made an item unwritable
(REV-1063 F2). The one visible change of value is a key type: `{1: a}` is written back as
`{'1': a}`. Core keys keep their own handling, as above.

### 6. Unknown keys are kept, in the same mapping as declared ones

The model holds every attribute, declared or not, in **one** mapping on the item,
`Item.attributes: dict[str, Any]`. Whether a key is declared is a question asked of the spec at
the boundary (check, `--set`, rendering), never a storage split, so a key moving between declared
and undeclared moves nothing.

It does not become a second `extra` because:

- **No wire surface nests it.** One serialiser flattens it into the top level for frontmatter,
  for every `--json` item row and for render contexts. The name `attributes` never appears in a
  file or a payload.
- **Nothing reads an undeclared key.** Readers go through declared names (decision 3); an
  unknown key is only ever carried.
- **There is no unknown bin.** A typo, a key from a newer spec and a key from an override that
  was removed are all the same thing: a key that is kept and not interpreted.

The index (`.squads.json`) carries the whole mapping, because writes build the frontmatter from
an index-derived item; its internal shape is free (invariant 1 holds: it is rebuilt from the
files).

Rejected for holding the mapping: pydantic `extra="allow"`, because the load payload passes
through keys that are not frontmatter fields (the persisted `id`, consumed by
`_derive_prefix_from_id`, read) and they would be captured as attributes (inferred); per-type
model subclasses, because item types are spec-declared strings (ADR-232).

### 7. Invariant: a write never removes a key the command did not target

A write removes or changes only the frontmatter keys its command names. A key that stops being
declared becomes unknown and keeps its name and value. Each path that could break this, and how it
is held:

- **The writer serialises core plus declared keys only.** It serialises core plus the whole
  attribute mapping; it never consults the spec. `slug` on a non-roster item follows decision 2.
- **Validation coerces or normalises a value whose declaration changed or vanished.** Load and
  check never coerce an attribute; coercion happens only on a command's own input
  (decision 5). The existing read folds apply to core keys only.
- **Retype to a type that does not declare the key.** Retype carries the attribute mapping over
  unchanged (it mutates the loaded item in place today, read). Keys the target does not declare
  become unknown and stay.
- **Type rename, renumber, import.** Rename reuses retype's primitive; renumber rewrites ids as
  text; import's `unset_fields` is a targeted removal and its `fields` a targeted set.
- **`sq sync` reconciliation.** Its sweep removes a closed, named set of retired role keys
  (`RETIRED_ROLE_EXTRA_KEYS`, ADR-981), never "every key this build does not know". It is
  re-pointed at top-level names and stays named.
- **`sq repair`.** It rebuilds the index from the files and does not rewrite frontmatter (read,
  `_models/_item.py`, `INVENTED_WHEN_ABSENT`). The index it builds carries unknown keys
  (decision 6).
- **Migrations.** A runner removes only the keys it names (decision 9). Runners for earlier
  schemas keep their own legacy readers.
- **The skew guard.** `ensure_no_skew` compares round-tripped frontmatter; unknown keys take part
  on both sides, and its retired-key exemptions (`PERMITTED_EXTRA_SKEW`, `_exempt_extra_keys`)
  are re-pointed from nested to top-level names. A hand-added key makes the file ahead of the
  index and is reported as skew, as any hand edit is today; that refusal removes nothing.

**Tests this owes** (pipeline-level invariant tests, table-driven, not one per branch). One
table, rows = write paths, columns = key shapes; each cell sets up the key, applies the change in
the column, runs the write path on the item, and asserts the key is in the file with an equal
value, and in `--json` and the rebuilt index.

- Write paths: `update` of another field, `update --set` of another attribute, `status`,
  `comment`, `body`, sub-entity add and update, `ref add`, retype, type rename, `renumber`,
  `import`, `sq sync` on a role, `sq role set-default`, `sq repair` then a write, the 0.16
  runner.
- Shapes: declared then removed from an override; never declared (hand-added); declared with a
  value whose kind no longer matches; carried onto a retype target that does not declare it;
  named like a `--json`-only key; a nested mapping value; a list; an explicit null.
- Plus one control per row that targets the key (`--set` and an `import` unset) and shows the
  write does change it, so the table cannot pass on a write path that never runs.

### 8. The collisions

- **`description`** has one meaning: the item's short summary, which for a skill is the host's
  selection text. `extra.description` is folded into it and not promoted. The backend reads
  `description or title`.
- **`title`** has one meaning on every roster type: the display name of the agent or person.
  `full_name` is not stored on any item: operators fold it into `title`, as roles already did
  (ADR-766). Operator surfaces read `title`. A role's job title stays catalog data
  (`roles.toml`) and is not a frontmatter key.
- **`slug`** is core (decision 2); `extra.slug` folds into it.
- **`tech`** is one declared attribute name with a separate declaration on each type that
  carries it: a guide's subject on `guide`, the template parameter on `role` (ADR-984). Same
  name, same kind, two declarations; nothing shares meaning across types.

### 9. Migration: rides the 0.16 runner

There is no second schema bump. The flattening is one step of FEAT-980's 0.15 to 0.16 runner
(the rule of 2026-09-24 and the single-runner rule of 2026-10-09), and it is the **first** step
that touches frontmatter, so every later contributor (FEAT-986's `is_dev` removal, FEAT-976's
`origin`, FEAT-961's `pronouns`, FEAT-966's `operator_invocable`) operates on flat keys.

It is built after the 0.16.0 version bump, because it changes bundled files, and before TASK-990,
FEAT-976, FEAT-961 and FEAT-966, so each of those writes top-level keys from its first commit.
This adds one step to MILE-934's main stream of 2026-10-12: TASK-954, FEAT-980, the bump, this
change, TASK-989, TASK-990, FEAT-976, FEAT-977, then FEAT-961 and FEAT-966.

Per item file:

- Each `extra` key is lifted to the top level with its value unchanged, declared or not, except:
  - `ref_kinds`: folded into inline refs (the existing fold);
  - `severity`: becomes top-level `severity` when that is absent; when both are present the
    top-level value wins, as the read path does today;
  - `slug`: becomes top-level `slug`;
  - `description` on a skill: dropped when the top-level `description` is non-empty; otherwise
    it becomes `description` unless it equals the title;
  - `full_name` on an operator: dropped; when it differs from `title`, `title` takes its value
    (what every operator surface showed) and the runner reports the file;
  - the retired role keys (`RETIRED_ROLE_EXTRA_KEYS`): dropped, as the existing sweep does.
- The top-level `path:` written by the 0.5 runner on system skills is removed. It is a key this
  tool wrote, not an adopter's.
- `is_dev` is lifted like any key and then removed by FEAT-986's contribution (ADR-984 decision
  4 adds it to the retired set). `tech` is lifted and kept, on roles and on guides.
- The `extra` key is removed. A file with no `extra` is left as it is; a second run changes
  nothing.

Pre-flight, before any file is written (the same shape as the vocabulary pre-check that now runs
before any runner): the runner refuses, naming each file and key, when `extra` is not a mapping;
when an `extra` key other than the folds above collides with a top-level key holding a different
value; or when a roster item's `extra.slug` differs from its file name's slug (none in this
corpus, driven).

After 0.16 the model reads no `extra`: `_read_extra`, `_extra_mapping` and the two legacy folds
move under `_migrations/` as a compat reader, used by the runners that need it, the way
`_meta_compat.py` is. A 0.16 file that still carries an `extra:` key (hand-pasted from an old
file) has an unknown key named `extra`, kept like any other.

### 10. The `--json` and client contract

- A generic item row (`list`, `show`, `create`, `mine` with `--json`) is: the core keys exactly as
  today, without `extra`; plus each attribute the file carries, flat, at the top level, present
  only when stored; plus the keys the command already adds (`badges`, `body`, `discussion`,
  `matched_subentities`). An
  unknown key whose name is one of those added keys is kept in the file and left out of the row,
  so the added key keeps its meaning.
- `sq workflow --json` type entries gain `attributes`: name to `{kind, required, settable}`. A
  client learns a type's keys there.
- Roster card payloads are unchanged.
- This is a breaking change to the generic rows and is called out in the 0.16 upgrade notes. It
  narrows ADR-427's additive-only rule for `show --json` for this release.
- The VS Code client reads no `extra` key, so no client code changes. Its canary changes:
  `LIST_ROW_KEYS` drops `extra`, and the row assertion becomes the exact core set plus, for each
  other key, membership in that type's `attributes` from `sq workflow --json`; `TYPE_ENTRY_KEYS`
  gains `attributes`. This lands with FEAT-980's canary keys, in the same release.
- Render contexts expose the flat item; the `extra` template variable is removed. An adopter
  template that reads `extra.<key>` reads `<key>` from the item instead; the upgrade notes say
  so.

### 11. An opt-in report of undeclared keys

A catalog-only validator (ADR-864's opt-in tier), `frontmatter_key_undeclared`, reports an
attribute that no declaration on the item's type names, at `warn`, to catch typos. It is selected
per project, reports and never rewrites. A squad that does not select it keeps unknown keys
silently, which is the default.

## Rejected

- **Keeping a nested container under another name.** It is the thing the ruling removes.
- **Refusing an unknown key at load.** One stray key would make an item unreadable, and the nine
  `path:` keys in this corpus would have done so.
- **Dropping unknown keys on write** (today's behaviour, driven). It loses data silently and
  breaks the guarantee in decision 7.
- **Validating declared attributes at the load boundary.** A spec change (a kind changed, a key
  made required) would make existing items unreadable. Load refuses only what the engine cannot
  build an item without.
- **Roster keys as core.** They exist on two or three types; core is what every item carries.
  Pinning in the loader gives the engine its guarantee without a hardcoded per-type list.
- **Keeping both `title` and `full_name` on operators.** Two stores of one name, one of them read
  first, and no verb that edits either.
- **A second schema bump for this.** The release's one runner is the vehicle.
- **Reading `extra_fields` as an alias of `attributes` for a release.** It would keep a grammar
  key alive that names a container that no longer exists, and an alias cannot carry the `kind`
  the new table declares.
- **Dropping `tech` from roles with `is_dev`.** ADR-984 decision 4 keeps it as the developer
  template's one parameter; it becomes a declared role attribute.

## Consequences

- Every `item.extra` reader moves to `item.slug`, a declared accessor or a typed roster accessor
  (about 150 sites in about 33 modules, read). `ExtraKey` becomes `AttributeKey`;
  `_models/_metadata.py`'s per-type tables give way to the spec declaration.
- Bundled `workflow.toml` declares `attributes` on `guide`, `milestone`, `review`, `role` and
  `skill`; the role and skill templates read flat keys (built after the 0.16.0 version bump,
  decision 9).
- The override grammar changes: `extra_fields` becomes `attributes`, and an override using the
  old key is refused at load with the remedy. The 0.16 upgrade notes say so.
- The validator catalog gains `frontmatter_key_undeclared` (catalog-only, `warn`).
- Adopter docs to refresh (tech writer): `docs/overrides.md` (the `extra` passage and the full
  name passage), `docs/roles.md`, `docs/internals.md`, `docs/migration.md`, `docs/adoption.md`,
  `docs/faq.md`, and `docs/stability.md`, which should name the flat frontmatter and the
  `attributes` grammar as contract.
- **ADRs that need a dated note**, each narrowed in place with a `related` ref back: ADR-085
  (names stored in `extra.full_name`), ADR-221 (`RoleSpec` mapped onto `extra` keys), ADR-323 and
  ADR-348 (custom badge values in `extra`), ADR-427 (additive-only `show --json`), ADR-474
  (custom axes ride in `extra` in `--json`), ADR-663 and ADR-775 (the `extra.ref_kinds` and
  `extra.severity` normalisation moves into the migration compat reader), ADR-754 and ADR-971
  (`extra.slug`, `extra.tech`, `extra.full_name`), ADR-766 (decision 6, "the `extra` copies
  stay") and ADR-776 (section 2d), ADR-979 (operator name from `extra.full_name`; repair from
  `extra.slug`), ADR-981 (`extra.pronouns`, `extra` in the generic JSON, unknown `extra` keys
  preserved), ADR-983 (`extra.operator_invocable`), ADR-984 (decision 4's `extra.is_dev` and
  `extra.tech` become top-level `is_dev` and `tech`). ADR-492, ADR-697 and ADR-753 mention only
  the retired `extra.skills` cache and need nothing.
- FEAT-961, FEAT-966, FEAT-976, FEAT-980 and FEAT-986 describe their keys as `extra.<key>`; their
  acceptance text reads as the top-level key once this lands.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T18:50:20Z] `architect` Robert Architect:
  - Drafted from the operator's rulings of 2026-10-15 on MILE-934 (flatten `extra`, ship it in 0.16, the core/declared/unknown shape, and the no-silent-removal guarantee). @manager, five points need the operator's call:
    
    1. **Override grammar break.** `extra_fields` becomes an `[items.<type>.attributes]` table with a declared `kind`. An adopter override that still uses the old key is refused at load, with a message naming the replacement. There is no alias. Accept the break, or ask for a one-release alias.
    2. **Build order.** The flattening is the first frontmatter step of FEAT-980's runner, and it changes bundled files. So I placed it after the 0.16.0 bump and before TASK-990, FEAT-976, FEAT-961 and FEAT-966, which then write top-level keys directly. That changes the main stream of 2026-10-12.
    3. **The manager's per-key list differs from ADR-984 on `tech`.** ADR-984 decision 4 (accepted 2026-10-09) and FEAT-986 US4 keep `tech` on roles as the template's parameter. Only `is_dev` goes. The ADR promotes `tech` on roles and guides. Removing it would mean amending ADR-984.
    4. **Operator name.** The operator's `full_name` is folded into `title` and not promoted, so `title` is the name on every roster type. Where the two differ, `title` takes the `full_name` value, since that is what every operator surface displayed, and the runner reports the file. The role catalog's job-title key (`title` in roles.toml) and the role card's `full_name` key in its JSON are left as they are. That is a remaining naming pair in the catalog grammar, outside this decision.
    5. **Optional typo check** (section 11). The operator can accept or decline an opt-in `frontmatter_key_undeclared` catalog-only check, at warn. It reports and never rewrites.
    
    Also: `--json` item rows lose `extra` and gain flat keys. This narrows ADR-427's additive-only rule for this release, and the canary changes ride with FEAT-980's. 15 ADRs need a dated note, listed under Consequences. I did not touch them. Probe evidence: in a scratch squad on 0.15, a hand-added top-level key is invisible to `sq check` and `--json`, and the next write erases it. Every roster slug in this corpus matches its file name (25/25).
- [2026-10-15T18:50:30Z] `architect` Robert Architect:
  - Correction to the count above: 16 ADRs need a dated note (the list under Consequences), not 15.
- [2026-10-15T19:07:58Z] `op-pierre` Pierre Chat:
  - 2026-10-15, on the five points of this record:
    
    1. An override still using `extra_fields` is refused at load, naming the replacement. No alias.
    2. Build order as proposed: after the 0.16.0 bump, before TASK-990, FEAT-976, FEAT-961 and FEAT-966.
    3. `tech` stays a declared role attribute, per ADR-984.
    4. The operator's `full_name` folds into `title`.
    5. The opt-in `frontmatter_key_undeclared` check is in: catalog-only, warn, reports and never rewrites. The default stays silent.
- [2026-10-15T19:09:11Z] `architect` Robert Architect:
  - 2026-10-15: body updated to state the five rulings of op-pierre (2026-10-15T19:07:58Z) as decisions: extra_fields refused with no alias (decision 4, Rejected), build order (decision 9, also commented on MILE-934), tech kept (decision 8, Rejected), full_name folded into title (decision 8), frontmatter_key_undeclared as an opt-in catalog-only warn check (decision 11). Status left as is. @manager
- [2026-10-15T20:11:50Z] `op-pierre` Pierre Chat:
  - 2026-10-15: accepted.
- [2026-10-15T20:17:27Z] `architect` Robert Architect:
  - @manager Dated notes are added for all 16 ADRs listed in the Consequences, each as "Note 2026-10-15 (ADR-1007)" at the affected passage, and each has a related ref back to this record: ADR-085 (section 5 naming contract), ADR-221 (the to_extra bridge, section 1), ADR-323 (section 6 storage), ADR-348 (section 4), ADR-427 (section 2 consumer contract), ADR-474 (the "additive superset" consequence), ADR-663 (the round-trip normalisation paragraph), ADR-754 (decision 2), ADR-766 (section 6), ADR-775 (A3), ADR-776 (amendment 2(d)), ADR-971 (decision 1), ADR-979 (the sq repair bullet, plus the operator-name lookup), ADR-981 (decision 1), ADR-983 (section 3), ADR-984 (decision 4).
    None was skipped: on reading, each one names an extra key, the extra container or the additive-only JSON rule at the passage noted. ADR-492, ADR-697 and ADR-753 got nothing, as this record says.
    Every diff against HEAD is additions only, apart from the updated_at the body verb stamps. No status changed, no stray content tags, and sq check is clean.
    One reading to confirm: the ADR-979 note says a lookup of an operator by title after the flattening gives the name extra.full_name held. That is inferred from decision 9 and holds only if the comment-header rewrite runs after the flattening step in the 0.16 runner.
- [2026-10-16T16:14:44Z] `op-pierre` Pierre Chat:
  - 2026-10-16: accepted that frontmatter values are kept as JSON-representable values: YAML-only types are normalized on write (an unquoted date becomes a string of the same value; a non-string mapping key becomes a string key). Record it as a dated note on decision 5.
<!-- sq:discussion:end -->
