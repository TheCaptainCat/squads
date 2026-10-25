---
id: ADR-981
sequence_id: 981
type: decision
title: Pronouns are roster-item data; display preferences get a typed table
status: Accepted
author: architect
refs:
- FEAT-961
- ADR-766
- ADR-979
- FEAT-977
- ADR-1007
description: extra.pronouns on role and operator items; one declared roster default;
  a typed display table in .squads.toml; free text, checked shape
created_at: '2026-10-09T15:35:21Z'
updated_at: '2026-10-25T21:42:28Z'
---
<!-- sq:body -->
## Context

FEAT-961 adds pronouns to agent and operator identity, a way to give a whole agent roster one
default, and a setting for whether human-facing output shows them. Four design points fix a
frontmatter key, a config-file shape and `--json` fields, so they are decided here. Already
settled on FEAT-961's discussion and taken as given: generated agent-facing files (the
`CLAUDE.md` / `AGENTS.md` roster and an agent's own identity pointer) always carry pronouns, and
the display setting governs human UIs only.

Each claim below is marked **read** (the source was read), **driven** (a command was run) or
**inferred**.

**Where identity lived in 0.15**, when this was decided.

- A role's definition is resolved from the role catalog on every read and is not stored on the
  item. The item is authoritative only for what a dedicated verb writes: the name, in the item's
  own `title` (ADR-766), and the default-role designation, in `extra.is_default`, which is stored
  only when `sq role set-default` wrote it and otherwise falls back to the catalog's answer (read,
  `_roles/_resolver.py`: `role_base_from_item`, `holds_default_designation`).
- Every consumer of a live role goes through one seam, `resolve_role_for_item` (read). The
  default-role designation is "resolved, not read off `extra`" for the stated reason that a raw
  read finds no holder on a role whose answer comes from the catalog (read, same module).
- `RoleDef`'s stored-key tables are the residue no document answers. A key written by its own
  verb is deliberately not a member, because the reconciler would reassert it from the resolved
  definition on every sync (read, `_roles/_catalog.py`, the `_EXTRA_FIELD_KEYS` note).
- An operator has no catalog. Its name lives in `extra.full_name` beside `extra.slug` (read,
  `_services/_roster.py`: `add_operator`).
- `Item` is one model for every item type. Its top-level fields are universal (`title`, `status`,
  `author`, `assignee`) or spec-declared badge axes (`priority`, `severity`); `extra` is the
  type-specific bag (read, `_models/_item.py`). `severity` is no longer an `extra` key: it moved
  top-level when it became a declared badge field, with a tolerant read of the old location (read).
- An `extra` key this build does not know is preserved on a role item: the reconciler's sweep is a
  closed, named set (read, `_services/_maintenance.py`: `_retired_role_extra_keys`).

**How `--json` exposes identity.** The roster viewers build their objects key by key
(`sq role list`: `id, slug, full_name, title, is_default, status`; `sq operator <addr> show`:
`id, slug, full_name, status, path`) and never emit `extra` (read, `_cli/_role.py`,
`_cli/_operator.py`; driven on 0.15.0). The generic `show --json` and `list --json` emit `extra`
verbatim (driven). The roster viewers are named in the `--json` tier of `docs/stability.md`;
`extra`'s inner keys are not (read).

**Config in 0.15.** `SquadsConfig` carries `schema_version`, `squad_dir`, `active_backends`,
`squads_version` and `init_names`, with `extra: ignore`. `to_toml` is a hand-written emitter that
rebuilds the file from the model, and it runs on every version or schema stamp (read,
`_models/_config.py`, `_services/_maintenance.py`: `_stamp_version`, `_stamp_schema`). So a key
the model does not carry is dropped at the next rewrite (inferred from those two facts, not
driven). A config that fails validation stops every command, because config resolution runs
before dispatch (read, `_paths.py`: `load_config`). The config is already threaded:
`SquadPaths.config`, reached as `svc.paths.config` (read). squads has no per-user config file and
no preference environment variable (driven, `rg` over `src/`: the only variables read are the two
session ids).

**The VS Code client** reads exactly one key of `.squads.toml`, `squad_dir`, with a line scanner
and no TOML parser, and keeps its own view preferences in VS Code settings (`squads.typeIcons`)
(read, `clients/vscode/src/domain/squadDir.ts`, `package.json`). It shows an assignee as a slug
and a comment author as the string in `discussion[].author`; no non-test source reads `full_name`
(driven, `rg` with a known positive in the test fixtures).

**The role catalog document.** `.overrides/roles.toml` is a delta merged over the bundled catalog,
with a closed top-level key space `{roles, bundles, dev}`; `[dev]` already holds roster-level
defaults for generated developers (model, colour, name pool). `RoleSpec` is `extra="forbid"`. The
resolver loads this document itself, from the squad directory it is handed, with no config in
hand (read, `_roles/_loader.py`, `_roles/_models.py`, `_roles/_resolver.py`:
`_predefined_for_slug`).

## Decision

### 1. Pronouns are stored on the roster item, in `pronouns`

One top-level frontmatter key, `pronouns` (`AttributeKey.PRONOUNS`), declared as a `str`
attribute with `settable = false` on the `role` and `operator` types (ADR-1007). Unset is the key
being absent; a blank is never stored.

```yaml
slug: op-alex
title: Alex Rivera
pronouns: they/them
```

- It is written only by a verb that names it, on creation (`sq role activate`, `sq dev add`,
  `sq operator add`) and afterwards. The verb must work on a bundled role: pronouns are identity
  the operator sets, like the name and the default-role designation, not generated content.
- On a role it follows the `is_default` pattern exactly: not a member of `RoleDef`'s stored-key
  tables, never reasserted by sync, and read through `resolve_role_for_item`, never raw off the
  item.
- It is not a `RoleSpec` field. A `pronouns` key in a `[[roles]]` entry or a per-slug role file
  stays refused, and the refusal names the verb.
- **`--json`.** `sq role list`, `sq role <addr> show`, `sq operator list` and
  `sq operator <addr> show` gain a top-level `pronouns` key beside `full_name`: the resolved
  value (section 3), a string, or `null` when unset, always present. It joins the `--json` tier on
  the same terms as `full_name`. The generic item JSON carries the stored attribute flat, present
  only when stored, and is not the contract surface: for a role it can be absent while the
  resolved value is set.
- **No denormalisation.** Pronouns are not added to item rows' resolved fields, to `discussion[]`
  entries, or to comment headers. A client joins a slug (`assignee`, `author`, `author_slug`) to
  the roster viewers. A comment header records a name snapshot at write time; an edit keeps it
  and replaces only the bullets (ADR-1013), so no pronoun is ever written into discussion text,
  where it would go stale the way names did.

### 2. A typed `[display]` table in `.squads.toml`, and nothing more general than that

```toml
[display]
pronouns = false
```

- `[display]` holds presentation preferences for the renderers that run inside `sq`: CLI human
  output and `sq ui`. Its one key is `pronouns`, a boolean, **default `true`**. When true, a
  name with pronouns renders as `Name (pronouns)` with the parenthesis dimmed; a name without
  pronouns renders as it does now.
- **Admission rule.** A key belongs in `[display]` only if changing it alters nothing but what
  those renderers print. It never changes stored data, `--json`, exit codes or generated files.
  That rule is what makes the table reusable; the next preference is one more typed field.
- **Typed and closed.** `[display]` is a nested model on `SquadsConfig` with a declared type and
  default per key. `to_toml`, used at `sq init` and adopt, emits it only when a value differs from
  its default. The adopter owns `.squads.toml` otherwise (ADR-1119).
- **Threaded.** Renderers receive the settings as an argument, from `SquadPaths.config`. No
  module-level cache, no singleton. One pure formatter produces `Name (pronouns)` for every human
  surface.
- **A display value can never stop a command.** An unknown key or an unusable value falls back to
  the default, and `sq check` reports it by name.
- **Other clients own their presentation.** The VS Code client always receives the data and
  decides with a setting of its own, default on. `.squads.toml` does not become a cross-process
  presentation contract, and no `--json` surface is added to expose it.

### 3. A roster default is declared once and resolved, never stamped

The role catalog document gains one top-level table:

```toml
[defaults]
pronouns = "they/them"
```

- **Resolution.** A role's pronouns are its own `pronouns`, else `[defaults].pronouns`,
  else unset. An operator's are its own value, else unset: a default never applies to a person.
- The resolved value is computed in the role-resolution seam, so every surface agrees, and it is
  never written back to an item.
- **At init and on an existing roster it is the same act:** declare the default, and `sq sync`
  regenerates the roster section and pointers. `sq init` may take a flag as shorthand, on the
  condition that it writes this declaration through the override scaffold path and writes nothing
  per item. There is no bulk-apply verb.
- The bundled catalog declares no default and no pronouns for any bundled role. An upgraded squad
  renders nothing new.

### 4. Free vocabulary, checked shape

There is no curated set and no enum. The value is one line, stored trimmed, 1 to 40 characters,
with no control characters and no sq marker tag. The same check applies to a verb's argument and
to `[defaults].pronouns`. A stored value that fails it (a hand-edited file) is treated as unset by
renderers and reported by `sq check`. Console output escapes it like any other content string.

## Rejected

- **A first-class `Item.pronouns` field.** `Item` is shared by every type, so the key would be
  legal frontmatter on a task. Top-level fields are universal or declared badge axes; this is
  neither.
- **`pronouns` on `RoleSpec`** (per-role, in the catalog or a per-slug file). It would be a second
  place to state one agent's pronouns, above the item in precedence, so a successful write to the
  item could change nothing a reader sees: the silent no-effect write the resolver already
  documents for other fields.
- **Stamping a default onto each agent** (an init flag that seeds every item, plus a bulk-apply
  verb). One decision stored N times. An agent added later does not get it, a later change of
  mind cannot tell a stamped value from one set on purpose, and a third rule is needed to protect
  explicit values. Declared once, all three disappear.
- **The default in `.squads.toml`.** The resolver takes the squad directory and already loads the
  role catalog document there; a config-held default would mean threading the config through
  every resolution call or resolving it in a second place, where two surfaces can disagree. It
  would also put what the pronouns are next to whether to show them.
- **A loose settings bag** (an untyped mapping any key can enter). A typo has no effect and
  reports nothing, a quoted `"false"` is truthy, and an unmodelled key does not survive the next
  rewrite of the file. These are the defects the role override loader was rebuilt to remove.
- **A settings system:** a key registry, `sq config get/set`, a per-user file, an environment
  override. One boolean does not pay for precedence rules or a new verb group. A per-user layer,
  if one is ever wanted, overlays this same typed table.
- **Display off by default.** Existing squads are unaffected either way, since they hold no
  pronouns. Off by default makes a value the adopter just recorded invisible until a second file
  is edited, and stores as a setting what is almost always derivable from the data being there.
- **A validated set of pronouns.** A closed list is wrong for someone and for every language but
  one. Unchecked text is also wrong: the value is rendered into generated files and Rich output.

## Consequences

- **Schema and migration.** No migration step and no `SCHEMA_VERSION` bump come from this
  decision. All three additions are optional with a default: an absent `pronouns` is unset, an
  absent `[display]` is all defaults, an absent `[defaults]` is no default.
- **Mixed package versions.** A package older than this decision refuses a role catalog document
  that carries `[defaults]`, because that key space is closed, so a squad that declares a default
  needs this release for everyone sharing it.
- **Durable surfaces:** the frontmatter key `pronouns` on role and operator items; the
  `[display]` table and its `pronouns` key; `defaults` in the role catalog document's top-level
  key space; `pronouns` on four roster `--json` shapes. `docs/stability.md` names each.
- **Not expressible:** an agent with no pronouns under a declared default. An agent's own value
  replaces the default; nothing erases it.
- **Backends.** `RoleView` and `OperatorView` gain `pronouns`, and the roster section and pointer
  templates render it. A verb that changes pronouns refreshes the managed region and that role's
  entry; a changed default is picked up by `sq sync`, like any override edit.
- **The bundled `roles.toml` declares no `[defaults]`.** The table is in the key space and the
  model, not in the bundled document.
- **Verb parity.** The refusal of content-changing verbs on a system role does not cover
  pronouns, or the bundled agents could never have any. Roles and operators take `--pronouns` on
  their `update` verb.
- **The developer pseudo-role's retirement** does not interact: `[defaults]` applies to every
  agent role and does not depend on how a developer is identified.
- **VS Code client.** It joins slugs to pronouns through the roster viewers, decides with its own
  setting, and its skew canary covers the key on those shapes.
- **Human output only shows pronouns after a name.** Surfaces that print a slug (assignee columns)
  are unchanged.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:36:59Z] `architect` Robert Architect:
  - Authored from the four questions the product owner raised on FEAT-961 (2026-09-24). Left Proposed for op-pierre. Three rulings depart from the recommendations there, and each is a call worth weighing before accepting:
    
    1. **Display defaults to on**, where FEAT-961 US5 says off. Reason in "Rejected". The cost of on: an adopter who gives every agent the same pronouns sees the same parenthesis on every name until they set `[display] pronouns = false`.
    2. **The roster default is declared in the role catalog document and resolved**, not seeded per agent by an init flag plus a bulk verb. Costs: `sq init` taking a flag means init writes an override document; a squad that declares a default needs this release for everyone sharing it; an agent cannot have no pronouns under a default.
    3. **The settings mechanism is a typed table, not a generic parameter system.** No registry, no get/set verbs, no per-user file. The VS Code client is deliberately outside it, so hiding pronouns everywhere takes two switches.
    
    Not driven: nothing here was exercised on a scratch squad. The claims marked inferred in the body (an unmodelled config key being dropped on rewrite, and the override drift path for the bundled catalog) should be confirmed by the tech lead at breakdown.
    
    The feature-side changes this implies are listed on FEAT-961 for the product owner.
- [2026-10-09T16:53:44Z] `op-pierre` Pierre Chat:
  - 2026-10-09: accepted as written, including display on by default, the declared roster default, and the typed display table.
- [2026-10-17T02:01:32Z] `architect` Robert Architect:
  - 2026-10-17: dated note owed under ADR-1013 (The append-only statement), from TASK-1079 ST14, on §1's "No denormalisation" bullet; body and status untouched.
    - Discussion text is no longer append-only: ADR-1013 lets a comment's author edit or remove it. The conclusion stands. An edit keeps the header's timestamp, slug and display-name snapshot, replaces only the bullets, and never writes a pronoun into a header, so no pronoun enters discussion text and the slug join to the roster viewers is unchanged (read, `_services/_collab.py` `edit_comment`).
- [2026-10-25T21:42:28Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale passages fixed; decision unchanged. extra.pronouns is the top-level pronouns attribute (ADR-1007 note folded), the append-only bullet restated against ADR-1013, display-table rewrite claims aligned with ADR-1119, roles/operators update --pronouns recorded.
<!-- sq:discussion:end -->
