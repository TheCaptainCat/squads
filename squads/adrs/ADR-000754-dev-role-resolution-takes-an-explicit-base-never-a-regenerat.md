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
description: Dev-role overrides merge onto a base supplied by the caller, built from
  the live role's stored identity
created_at: '2026-08-21T12:47:51Z'
updated_at: '2026-08-21T21:02:32Z'
---
<!-- sq:body -->
## Context

A `.overrides/roles/<slug>.toml` merges field-wise over a base: bundled slug, merge over the
catalog entry; unknown slug, no base, so every required field must be present
(`_roles/_resolver.py:169-193`, `:120-133`). A developer role has a third shape — its base is
*generated*, not catalogued — and `resolve_dev_role` is the only function that knows this
(`_roles/_resolver.py:196-225`). Every other consumer calls `resolve_role`, which treats a
`<tech>-dev` slug as an unknown slug with no base.

Driven on a fresh squad (`sq init --default-names`, `sq dev add --tech python`, then a
`python-dev.toml` whose only line sets `title`): `sq role python-dev show` exits 1,
`sq sync` exits 1, both with `role override for new slug 'python-dev' is missing required
fields: full_name, description, mission`. `sq check` exits 3 reporting the same load failure.
The file is valid — `sq dev add` honours exactly this shape — and the docs promise it
(`docs/overrides.md:78` lists `python-dev.toml`; `docs/overrides.md:126-135` promises
field-wise merge for any `roles/<slug>.toml`).

Two things make this not a widening of `resolve_role`.

**The generated base is not a function of the slug.** `dev_role(tech, name=None, seq=0)`
synthesises `DEV_NAME_POOL[seq % len(pool)] + " " + Tech`
(`_roles/_catalog.py:151-183`), and `seq` is the *count of existing dev roles at creation
time* (`_services/_roster.py:73`) — derived, consumed, and never stored. Driven: a squad whose
second developer is `Ada Typescript` (pool index 1) gets `Elias Typescript` from
`dev_role("typescript")` with the default `seq=0`. `dev_role` is a name **generator**,
correct exactly once, at creation; calling it again for a role that already exists is a fresh
roll of a lossy derivation.

**That regenerated name would be persisted.** `_refresh_catalog_extra`
(`_services/_maintenance.py:585-646`) merges `resolve_role(...).to_extra()` onto the live item
and mirrors it into the index in the same transaction, and `to_extra()` includes `full_name`
(`_roles/_catalog.py:42-56`). So a naive widening does not merely display a wrong name, it
writes one to frontmatter and index.

The same function carries a second defect. Its docstring says developer roles are skipped, and
it implements that by catching `RoleNotFoundError` — which `resolve_role` raises only when
**no** override file exists. A partial `<tech>-dev.toml` makes `resolve_role` raise a plain
`SquadsError` instead, which nothing catches, so the documented skip is not a skip at all: it
is a path that happens to be unreachable until an adopter writes the file the docs invite.

## Decision

**1. Resolution takes the dev base as an explicit input. It never derives one from a slug.**

`resolve_role(slug, squad_dir)` is unchanged — same signature, same behaviour, same bundled
and new-slug paths. Alongside it, one entry point that accepts the base:

    resolve_role_with_base(slug, squad_dir, *, base: RoleDef | None) -> RoleDef

`base=None` is exactly today's `resolve_role`. A supplied `base` is used as the merge base
whenever `slug` is not in `PREDEFINED`, which is precisely the case that has no base today.
Nothing infers a dev base inside the resolver, because the resolver does not hold the
information a correct one needs.

**2. Two base builders, because there are two different questions.**

- `dev_base_from_item(item)` — for a role that exists. Reads the item's own stored facts:
  `dev_role(item.extra[X.TECH], name=item.extra[X.FULL_NAME], model=item.extra[X.MODEL])`.
  The live name is passed in, so it is inherited rather than regenerated, and `seq` is never
  consulted. `X.IS_DEV`/`X.TECH` are outside `RoleDef.to_extra()`, so no merge can erase the
  marker this branch reads.
- `dev_base_for_slug(slug)` — for a `<tech>-dev` file with no roster entry. Falls back to the
  generated pool name, which is safe here for the reason it is unsafe above: there is no live
  identity to overwrite, and the caller only asks whether the document loads.

The precedence is a stored fact first, a naming convention only where no stored fact exists:
`extra.is_dev` when an item is in hand, and `_interactions.is_dev_slug` (the existing
`slug.endswith("-dev")` predicate, `_interactions/__init__.py:181-182`) only when none is.

**3. What a partial dev override may and may not change.**

Absent fields inherit the live role's current values, so a file that sets only `title`
changes only the title. A file that *declares* `full_name` renames the role, because that is
what a declaration means and it is exactly what a bundled-slug override already does — but a
name the adopter never wrote is never invented. The distinction is between a name declared
and a name regenerated, and only the second is forbidden.

This replaces `resolve_dev_role`'s current rule that an explicit `name` argument suppresses
the file's `full_name`. That rule is right where `name` is an *assignment* (`sq dev add
--name` is more specific than a file) and wrong where `name` is the role's *existing
identity* (a file that says `full_name` should win over a value it is overriding). The two
uses must be distinguishable at the call site rather than share one parameter.

**4. The three consumers.**

- **`sq sync`** (`_refresh_catalog_extra`) branches on `item.extra.get(X.IS_DEV)` and passes
  `dev_base_from_item(item)`. The `RoleNotFoundError` catch narrows to the case it is honest
  about: a slug with neither a catalog entry nor an override, i.e. an orphaned custom role
  item. With no override file present the merged definition equals the base equals the item's
  own values, so the diff loop finds nothing and returns `None` — **the skip becomes a no-op
  rather than an exception catch**, and "no file" and "a file that changes nothing" reach the
  same answer by the same path.
- **`sq role <slug> show`** passes `dev_base_from_item(it)` when the item exists
  (`_cli/_role.py:227-229` already resolves it) and `dev_base_for_slug(slug)` when it does
  not.
- **`sq check`** (`check_override_issues`, `_overrides/_service.py:996-1010`) passes
  `dev_base_for_slug(slug)` for a dev-shaped slug with no roster entry, and
  `dev_base_from_item` when there is one. Its report for the partial-dev shape must be
  retired in the same change that makes the shape load; leaving it would flag a file that
  now works.

**5. The skew-guard exemption set does not change, but its stated reason does.**

`_itemfile._exempt_extra_keys` grants a dev role only `{X.SKILLS}`, reasoning that "a dev role
never goes through `_refresh_catalog_extra`" (`_itemfile.py:92-133`). The premise becomes
false. The conclusion stays correct and must stay: `_refresh_catalog_extra` writes markdown
first and mirrors into the index inside one transaction, so no permanent index lag is
introduced for dev roles and nothing needs exempting. Widening the set for dev roles would
reopen the exact loss class that comment names — an interrupted `--set model=haiku` on a dev
role, followed by an edit through another seam, silently overwritten by a stale index value.
Correct the comment; do not touch the set.

## Consequences

- A partial `<tech>-dev.toml` becomes what the docs already say it is. `sq sync` applies the
  declared fields; `sq role <slug> show` renders; `sq check` stops reporting a refusal that
  no longer happens.
- A live developer role's `show` card stops degrading. Driven today: `sq role python-dev show`
  renders the three-line item fallback (name, id, status) because `resolve_role` raises for
  every dev slug, override or not. With a base it renders the full card — title, model,
  spawn, create lane, mission, responsibilities — like every other role.
- Every path that materialises a dev role now runs its definition through the typed
  `RoleSpec` validation and the shared merge engine, so the four loose-value classes that
  validation exists to catch (a truthy `can_spawn = "false"`, an off-whitelist `model`, a
  non-string `color`, a silently dropped typo'd key) are caught for dev overrides too.
- `resolve_dev_role` keeps its `sq dev add` call site and its assignment semantics for
  `name`. It is not the general seam and does not become one.
- `docs/overrides.md` owes a paragraph: what a `<tech>-dev.toml` merges onto, and that
  omitting `full_name` preserves the live name while declaring it renames the role.

## Falsification the implementation owes

- The rename is the risk, so it is the first test: a squad with two developers, a partial
  override on the *second* one, then `sq sync` — the second developer's `full_name` must be
  unchanged in **both** frontmatter and index. Make the base regenerate instead of inherit
  and that test must go red naming the pool name.
- A partial override that omits `full_name` and one that declares it are separate tests with
  opposite expectations. A single test covers whichever branch was written and neither of the
  two rules.
- Cover the file shapes, not just the fields: a partial dev override, a complete one, one for
  a tech with no roster entry, one whose `slug` key disagrees with its filename, and one with
  an invalid value (an off-whitelist `model`) — the last must still refuse, at all three
  consumers, for all three of `sync`, `role show`, and `check`.
- Assert the no-override case takes the no-op path in `_refresh_catalog_extra` rather than
  raising: remove the narrowed `RoleNotFoundError` catch and the orphaned-custom-role test
  must go red.
- `sq check` must be clean on a squad carrying a partial dev override, and must still exit
  non-zero on one carrying a broken dev override.

## Amendments

Recorded against the implementation this decision governs. The original text above is unedited;
these state what it left unsaid.

### A1 (2026-08-21) — §2's precedence is universal; it was implemented only where it was forced to be

§2 states the precedence generally — "a stored fact first, a naming convention only where no
stored fact exists" — and the wording is deliberately not dev-specific. The implementation
applies it only to slugs outside `PREDEFINED`, and one line is the whole reason
(`_roles/_resolver.py:255-256`):

    predefined = _PREDEFINED_BY_SLUG.get(slug)
    effective_base = predefined if predefined is not None else base

For a bundled slug the caller's base is **discarded outright**, so no caller can make the live
item the merge base for `architect` however correct its base is. A developer slug works only
because `PREDEFINED` happens to hold no entry for it. That is an artifact of where the bundled
catalog has rows, not a property of the two role kinds, and there is no reason bundled roles
should differ: an operator names a bundled role by exactly the same documented inputs
(`sq init --name`, the interactive init prompt, `sq role activate --name`, whose own help reads
"overrides bundled default").

Driven, on a fresh squad with no override files: `sq init --default-names --name
architect='Ada Lovelace'` then a single `sq sync` reverts `title`, `extra.full_name`, and the
generated `CLAUDE.md` roster line to `Robert Architect`, with `sq sync` exit 0 and `sq check`
exit 0. Same result for `sq role activate architect --name 'Grace Hopper'`.

**The precedence is universal. Extending it is conformance to this decision, not a new one**, so
no separate decision governs it — this amendment is the record.

**The extension is narrower than "make the item the base", and must stay narrow.** Refreshing the
catalog's own prose and vocabulary (`title`, `mission`, `responsibilities`, `agreements`,
`color`, `is_default`, `can_spawn`) is what `_refresh_catalog_extra` exists for — it is how a new
`RoleDef` field reaches items created before it existed. Freezing all of it to the item would
break that. The rule instead:

> **The item is authoritative for exactly those fields an operator can set on it, and for no
> others.** Every other field comes from the resolved definition as it does today.

Driven from the CLI surface: `sq role activate` offers `--name` alone, so for a bundled role that
set is `{full_name}`. `sq dev add` offers `--name` and `--model`, and carries `tech`, so for a
developer role it is `{full_name, model, tech}` — which is exactly what `dev_base_from_item`
already reads. The asymmetry between the two is therefore not a special case; it falls out of the
one rule.

### A2 (2026-08-21) — `[init.names]` sits outside the resolution order and must not be read at resolve time

`sq init` persists the chosen names to `.squads.toml` under `[init.names]`
(`_services/_service.py:152`). Read: the only consumer is `sq init` itself, when re-run over an
existing config (`_cli/_main.py:311`); no resolver, no sync path, and no backend ever reads it.

It stays that way. `[init.names]` is the **input that produced** the item's stored name, and the
item's `extra.full_name` is the **result**. Reading the input at resolve time would consult a
stale copy of something whose output already exists, and would be actively wrong the moment the
name changes legitimately through any other sanctioned route — an override's `full_name`, or any
future rename verb. Driven that the two genuinely diverge in normal use: after
`sq role activate architect --name 'Grace Hopper'`, `[init.names]` is empty while the item
carries the name, so a resolver reading the table would find nothing for the very case the table
is supposed to cover.

So `[init.names]` is not tier 0, not a tie-breaker, and not consulted on any resolve. It keeps
its two existing jobs: an input to `sq init`, and (see A3) a forensic record.

**The resolution order for any role's `full_name`, in full:**

1. `.overrides/roles/<slug>.toml` `full_name`, when the file declares it. Unchanged from rule 3
   above: a declared name renames, an omitted one inherits.
2. The item's stored `extra.full_name`, when a roster item exists for the slug.
3. The bundled `PREDEFINED` entry's `full_name` — or, for a developer slug with no item, the
   generated pool name (`dev_base_for_slug`).

`[init.names]` is deliberately absent from that list. It participates only at activation, where
it is one of the inputs that decides what tier 2 is *first set to*.

### A3 (2026-08-21) — a damaged squad is recoverable; the fix is to stop the loss, not to heal automatically

Driven on a squad after the loss: the operator's name survives in two places on disk.

- `.squads.toml` still carries `[init.names] architect = "Ada Lovelace"` verbatim. Only `sq init`
  ever writes that table, so no later sync can overwrite it.
- `squads/.reflog.jsonl` carries the role's `create` entry with
  `{"title":"Ada Lovelace","type":"role","status":"Active"}` — and covers the
  `sq role activate --name` case too, which `[init.names]` does not.

Driven that neither is clobbered: the projection writes no reflog entry at all (zero `update`
ops after a reverting sync), so the `create` entry stays intact. That is the one benefit of a
gap worth fixing on its own account — this writer changes an agent's identity without bumping
`updated_at`, setting `modified_session`, or logging, so the rename is invisible to every recency
surface.

Consequently **the fix is to stop the loss, and a heal path is not part of it.** Once tier 2 is in
the order no further sync can revert a name, and the value for an already-damaged squad is
readable by hand from either source above, so this is not unrecoverable data.

An automatic heal is refused, for a reason A2 already fixes: restoring from `[init.names]` on
sync would make an init-input table retroactively authoritative over the item, resurrecting a
name in every squad whose adopter has since changed it deliberately. What is warranted instead is
a **report**, not a repair: `sq check` should say so when a role item's `extra.full_name` differs
from that slug's `[init.names]` entry, so a squad that has already lost a name is told rather
than left silently pinned to the bundled default. That reads only data already on disk, makes
nothing authoritative, and is its own small item — not a precondition for this fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T15:17:06Z] Pierre Chat:
  - Rule 3 stands as written: a dev-role override that explicitly declares full_name renames the live role, because a declaration means what it says and it matches bundled-role override behaviour. Only a regenerated pool name is forbidden. No extra warning line required.
- [2026-08-21T21:02:31Z] Robert Architect:
  - Amended in place (A1-A3) after the operator-set-name loss driven on release/0.14. Ruling: no new decision is warranted — section 2 precedence was already written generally and the implementation applied it only where PREDEFINED has no row, so extending it to bundled roles is conformance to this decision, not a new one.
  - A1: one line is the whole cause — _roles/_resolver.py:255-256 discards the caller base whenever the slug is in PREDEFINED, so no caller can make the live item the base for a bundled role. Narrow rule to implement: the item is authoritative for exactly the fields an operator can set on it ({full_name} for a bundled role, {full_name, model, tech} for a dev role) and no others; the rest of the catalog merge is untouched.
  - A2: [init.names] stays outside the resolution order and must not be read at resolve time — it is the input that produced extra.full_name, and it is empty for the sq role activate --name path (driven), so a resolver reading it would miss the very case it looks like it covers. Order: override full_name > item extra.full_name > bundled default (or pool name for a dev slug with no item).
  - A3: recoverable — the name survives in .squads.toml [init.names] and in the reflog create entry (both driven; the projection logs nothing, so the create entry is never clobbered). So the fix is to stop the loss; an automatic heal is refused because it would make an init-input table retroactively authoritative. A sq check report on the mismatch is the right follow-up, as its own small item.
<!-- sq:discussion:end -->
