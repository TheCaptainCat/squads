---
id: ADR-754
sequence_id: 754
type: decision
title: Dev-role resolution takes an explicit base, never a regenerated one
status: Accepted
author: architect
refs:
- BUG-744:addresses
- REV-736
- TASK-751
- REV-770
- ADR-971
- ADR-984
- ADR-1007
- ADR-1151
- ADR-766
- ADR-777
description: Dev-role overrides merge onto a base supplied by the caller, built from
  the live role's stored identity
created_at: '2026-08-21T12:47:51Z'
updated_at: '2026-10-25T21:49:49Z'
---
<!-- sq:body -->
## Context

A `.overrides/roles/<slug>.toml` merges field-wise over a base. For a bundled slug the base is
the catalog entry; for an unknown slug there is no base, so every required field must be present.
A developer role is a third shape: its base is *generated* from the `[dev]` template, not
catalogued, and a resolver that knows only the slug treats a `<tech>-dev` slug as an unknown slug
with no base, refusing a partial override the docs invite (`sq sync`, `sq role <slug> show` and
`sq check` alike).

Two facts make widening a slug-only resolver wrong.

**The generated base is not a function of the slug.** The developer pool synthesises a name from a
pool position that is the *count of existing developer roles at creation time*, derived, consumed
and never stored. The pool is a name **generator**, correct exactly once, at creation; calling it
again for a role that exists is a fresh roll of a lossy derivation (a squad whose second developer
is `Ada Typescript` would get `Elias Typescript` back).

**That regenerated name would be persisted.** The sync writer that reconciles a role item with its
resolved definition mirrors what it resolves into frontmatter and index in one transaction, so a
regenerated base does not merely display a wrong name, it writes one.

## Decision

**1. Resolution takes the base as an explicit input. It never derives one from a slug.**

`resolve_role(slug, squad_dir, *, catalog)` is the `base=None` case of one entry point that
accepts the base:

    resolve_role_with_base(slug, squad_dir, *, base, catalog, pinned_name=None) -> RoleDef

`base=None` falls back to the slug's catalog entry, or no base. A supplied base always wins over
the catalog entry, for a bundled slug as for a developer one, and the per-slug file merges over
it. Nothing infers a developer base inside the resolver, because the resolver does not hold the
information a correct one needs.

**2. The base is built from the live item, and only from stored facts.**

`role_base_from_item(item, catalog)` is the one seam every consumer that resolves against a live
role item (the sync writer, `sq role <slug> show`, `sq check`, and `resolve_role_for_item` behind
the roster projection and the backends) builds its base through:

- **A developer role** (a templated role, one whose item stores `tech`): `dev_base_from_item`
  builds the `[dev]` template base from the item's own stored facts: `tech`, its name (`title`),
  `model`, its default designation, and its `slug` (ADR-971: the stored slug is identity; the
  `<tech>-dev` derivation runs only when a developer is created). The pool position is never
  consulted.
- **A bundled role**: the slug's current catalog entry (the bundled catalog with any
  `.overrides/roles.toml` merged in), with the stored default designation.
- **Anything else**: no base.

The precedence is a stored fact, never a naming convention: whether a role is a developer is read
from the stored `tech` attribute (ADR-984), not from a `-dev` suffix, and a slug that names no
roster item has no item to build a base from.

**The item is authoritative for exactly those fields an operator can set on it, and for no
others.** `sq role activate` sets a name; `sq dev add` sets a name and a model and carries a tech.
Every other field (title, mission, responsibilities, agreements, colour, spawn authority,
capabilities) comes from the current catalog or template on every call, which is how a new
definition field reaches items created before it existed.

**3. A role's name is pinned; a partial override changes only what it declares.**

The role's name is stored at creation and pinned over every layer (`pinned_name`, read from the
item's `title`, ADR-766): a `full_name` in an override, the catalog or the pool names a role only
when it is created, and a rename goes through the role's update verb (ADR-777 §3). Every other
absent field inherits the live role's resolved value, so a file that sets only `title` changes
only the title.

**4. An override for a slug with no role is a new role.**

An override for a developer slug not on the roster has no base and is resolved like any other
unknown slug: it must carry every required field (`full_name`, `description`, `mission`), or
`sq check` reports a role override that does not load and `sq role <slug> show` refuses it. No pool
name is ever previewed for a developer that has not been added, because the pool pick depends on
how many developers exist when it is added (op-pierre, 2026-10-25). The supported order is
`sq dev add --tech <tech>` first (it takes `--name`, `--model`, `--slug`, `--pronouns`), then a
per-slug file only to customise beyond those flags; or a complete override written first, from
which `sq dev add --tech <tech>` then builds the developer. Whether a per-slug file may precede its
role at all is ADR-1151's subject.

**5. `[init.names]` is outside the resolution order.**

`sq init` records the chosen names in `.squads.toml` under `[init.names]`; its only reader is
`sq init` re-run over an existing config. It is the **input that produced** the item's stored
name, never consulted at resolve time: reading it would consult a stale copy of something whose
result already exists, and it is empty for a name set by `sq role activate --name`. The name order
for any role is therefore the stored name for an existing role, and the creation inputs (`--name`,
the catalog, the per-slug file, the developer pool) only when the role is created. There is no
automatic heal from `[init.names]`, which would make an init input retroactively authoritative over
a deliberately changed name.

**6. The skew-guard exemption follows the writer, not the role kind's history.**

`_itemfile._exempt_attribute_keys` grants a developer role no exempt keys: its attributes are
written by the sync writer inside one transaction, markdown first and index last, so there is no
permanent index lag to tolerate, and an operator's `model` is compared like any other field.
Exempting more for developer roles would reopen the loss class the guard exists for: an
interrupted `--set model=haiku` followed by an edit through another seam, silently overwritten by
a stale index value.

## Consequences

- A partial `<tech>-dev.toml` merges onto the live developer: `sq sync` applies the declared
  fields, `sq role <slug> show` renders the full card, and `sq check` reports nothing.
- An operator-set name survives every sync, for bundled and developer roles alike.
- The sync writer is not silent: a change moves `updated_at`, sets `modified_session` and appends
  one `update` reflog entry.
- Every path that materialises a role runs its definition through the typed `RoleSpec` validation
  and the shared merge engine, so a truthy `can_spawn = "false"`, an off-whitelist `model`, a
  non-string `color` or a silently dropped key is caught for developer overrides too.
- `resolve_dev_role` keeps its `sq dev add` call site, where an explicit `--name` is an
  assignment. It is not the general seam.

## Falsification the tests owe

- A squad with two developers, a partial override on the *second*, then `sq sync`: the second
  developer's name is unchanged in **both** frontmatter and index. A base that regenerates instead
  of inherits must go red naming the pool name.
- An operator-set bundled role name (`sq init --name`, `sq role activate --name`) survives `sq sync`.
- File shapes, not just fields: a partial developer override, a complete one, one for a slug with
  no roster entry (refused unless complete), one whose `slug` key disagrees with its filename, and
  one with an invalid value (an off-whitelist `model`), which refuses at `sync`, `role show` and
  `check`.
- With no override file the sync writer takes the no-op path; only an orphaned custom role item
  (no catalog entry, no template, no file) is skipped through the `RoleNotFoundError` catch.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T15:17:06Z] `op-pierre` Pierre Chat:
  - Rule 3 stands as written: a dev-role override that explicitly declares full_name renames the live role, because a declaration means what it says and it matches bundled-role override behaviour. Only a regenerated pool name is forbidden. No extra warning line required.
- [2026-08-21T21:02:31Z] `architect` Robert Architect:
  - Amended in place (A1-A3) after the operator-set-name loss driven on release/0.14. Ruling: no new decision is warranted — section 2 precedence was already written generally and the implementation applied it only where PREDEFINED has no row, so extending it to bundled roles is conformance to this decision, not a new one.
  - A1: one line is the whole cause — _roles/_resolver.py:255-256 discards the caller base whenever the slug is in PREDEFINED, so no caller can make the live item the base for a bundled role. Narrow rule to implement: the item is authoritative for exactly the fields an operator can set on it ({full_name} for a bundled role, {full_name, model, tech} for a dev role) and no others; the rest of the catalog merge is untouched.
  - A2: [init.names] stays outside the resolution order and must not be read at resolve time — it is the input that produced extra.full_name, and it is empty for the sq role activate --name path (driven), so a resolver reading it would miss the very case it looks like it covers. Order: override full_name > item extra.full_name > bundled default (or pool name for a dev slug with no item).
  - A3: recoverable — the name survives in .squads.toml [init.names] and in the reflog create entry (both driven; the projection logs nothing, so the create entry is never clobbered). So the fix is to stop the loss; an automatic heal is refused because it would make an init-input table retroactively authoritative. A sq check report on the mismatch is the right follow-up, as its own small item.
- [2026-09-29T13:44:31Z] `architect` Robert Architect:
  - ADR-971 (Proposed) extends this decision: dev_base_from_item would take slug from the item too, beside name/model/tech. If ADR-971 is accepted, a dated narrowing note goes into this body.
- [2026-10-25T20:15:39Z] `op-pierre` Pierre Chat:
  - Keep: an override for a dev slug not on the roster is a new role and must be complete; add the developer with sq dev add first, and write an override only to customise beyond its flags.
- [2026-10-25T20:15:40Z, edited 2026-10-25T20:16:00Z] `architect` Robert Architect:
  - @tech-writer amended ADR-754 (2026-10-25): the override-first flow is retired. Doc mismatches to fold into your current edit (not touched by me):
    - `docs/overrides.md` "A developer's override merges onto the developer you already have": the paragraph "You can write the file before the developer exists and run `sq dev add` afterwards: the new developer is built from it. … Add the developer, or remove the file, to clear it." still presents a partial file written first as a path that works once you add the developer. State the two supported flows instead: `sq dev add --tech <tech>` first (`--name`, `--model`, `--slug`, `--pronouns`), then an override only to customise beyond those flags; or a complete override (every required field) written first, which `sq dev add` then builds from. Keep the exit-3 example as what a partial file for an unadded slug gets.
    - Same section, the rule "A name you never wrote is never invented. Omit `full_name` and a new developer takes a name from the pool." reads as guidance for writing the file before the developer exists; under the ruled flow a file without `full_name` only applies to a developer already added. Reword or drop.
    - Same section and `docs/roles.md` (the "A developer's fields are overridable" paragraph): "Its `full_name` names a developer added after the file was written" implies the override-first flow. True only for a complete override; say so.
    - `docs/overrides.md` "Which name wins", tier 2: same point, a per-slug `full_name` names a developer at `sq dev add` only when that file is complete.
    - `docs/overrides.md` scaffold notes: `sq override scaffold --role python-dev` is described for a developer already on the roster, which matches; worth one line that for a dev slug not yet added the scaffolded stub does not load until it is complete (or point at `--new`).
- [2026-10-25T20:19:08Z] `tech-writer` Theo Writer:
  - Docs aligned with the 2026-10-25 amendment. All five mismatches fixed:
    - `docs/overrides.md`, "A developer's override merges onto the developer you already have": rewritten around the two flows. First, `sq dev add` (with `--name`, `--model`, `--slug`, `--pronouns`) and then an override for the rest. Second, a complete override written first (`full_name`, `title`, `description`, `mission`) that `sq dev add` builds from. The "write the file before the developer exists" paragraph is gone. The exit-3 example stays, as what a partial file for a slug not on the roster gets. The "name you never wrote is never invented" rule is dropped, and the `full_name` rule no longer implies writing the override first.
    - New note: a complete file written first needs the `squads:override-base` stamp. Without it, once the developer is added, `sq check` reports `role override has no squads:override-base stamp` at error until `sq override update --role <slug>`.
    - "Which name wins", tier 2: a per-slug `full_name` names a developer only from a complete file written before `sq dev add`.
    - `docs/roles.md`, the "A developer's fields are overridable" paragraph, and the "Retitle a developer" worked example: same correction.
    - Scaffold notes: a dev already on the roster now gets every field commented out with its current values, not just the stamp. The old text was wrong and is fixed in both places. For a slug not on the roster yet, the stub does not load until it is complete, and `--new` is the pointer.
    - Ran with the dev build on a scratch squad, now deleted. Quoted output comes from three runs: `dev add --tech go --name "Gina Go" --model sonnet`, then a title override and `sync`; a complete stamped `zig-dev.toml`, then `dev add --tech zig --model haiku`; and a title-only `rust-dev.toml` with no developer, which gives the exit-3 message. Doc guards pass.
    - Gap, not documented: `sq override scaffold --new elixir-dev` followed straight away by `sq dev add --tech elixir` stores `TODO: full name (e.g. "Sam Security")` as the developer's name. `sq check` stays clean, and the stored name then never changes.
- [2026-10-25T21:06:46Z] `architect` Robert Architect:
  - Dated narrowing added 2026-10-25 for ADR-1151 (role bases and templates). The original text is unedited.
- [2026-10-25T21:49:49Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten clean in the present tense; the decision (resolution takes an explicit base, never a regenerated one) is unchanged. Folded A1–A3, the ADR-971 and ADR-984 narrowings, the ADR-1007 note and the 2026-10-25 amendment (op-pierre: a dev-slug override not on the roster is a new role and must be complete). Now matches the resolver: role_base_from_item for bundled and developer roles, a supplied base always wins, the stored name pinned over every layer (ADR-766/777, so rule 3's "a declared full_name renames" is gone), dev_base_for_slug and is_dev_slug retired, the developer skew exemption empty, the sync writer reflogged. The ADR-1151 narrowing is a one-line pointer in §4; related refs added to ADR-766 and ADR-777.
<!-- sq:discussion:end -->
