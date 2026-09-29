---
id: ADR-971
sequence_id: 971
type: decision
title: A stored slug is identity; slugify only proposes one at creation
status: Accepted
author: architect
refs:
- BUG-965:addresses
- ADR-754
- MILE-934
- TASK-969
description: No path re-derives a stored slug; dev roles resolve to their stored slug;
  existing slugs stay; duplicates match both rules
created_at: '2026-09-29T13:41:21Z'
updated_at: '2026-09-29T13:53:06Z'
---
<!-- sq:body -->
## Context

BUG-965: `slugify` (`_util.py`) drops non-ASCII letters (`Réduire` becomes `r-duire`,
`Élodie` becomes `op-lodie`). The fix changes the derivation function. Any path that
re-derives a slug after creation would then disagree with the slug it stored.

**Where a slug is derived** (read, `rg "slugify\(|operator_slug\("`): `create`
(`slug or slugify(title)`), `add_skill` (`slugify(name)`), `add_operator`
(`operator_slug(name)`, bypassed by an explicit `--slug`), `add_dev` (through
`dev_role_from_pool`, `slugify(tech) + "-dev"`), memory `add`, and a work-item retitle
(`_rename`), which moves the file to the new name in the same step.

**Where a slug is looked up** (read): `roster_item` compares the stored `extra.slug`
exactly. `--as`, `--assignee`, `sq skill <slug>` and `sq memory <role> show <slug>` match
stored strings. Load and repair parse a work item's slug back from its filename. None of
these recomputes a slug.

**The one re-derivation after creation is the dev role** (read, not driven):

- `dev_base_from_item` calls `dev_role(extra.tech, ...)`, so the base `RoleDef.slug` is
  `slugify(extra.tech) + "-dev"`, recomputed on every resolve.
- `resolve_role_with_base` returns that base unchanged when no
  `.overrides/roles/<slug>.toml` exists. When one does exist, `_apply_override` pins `slug`
  to the filename.
- `_refresh_catalog_extra` merges `RoleDef.to_extra()` into the item on every sync and
  mirrors it into the index. `to_extra()` is exactly `{slug}`, plus `model` for a
  developer.
- The Claude Code backend names the pointer `.claude/agents/<role.slug>.md` from the
  resolved `RoleDef`.

So after the `slugify` fix, a developer whose tech label has an accent would, on the next
sync, get its `extra.slug` rewritten to the new form while `item.slug` and the filename keep
the old one. Its pointer would be written under a new name, and every `@mention`, `--as` and
assignee holding the old slug would stop matching `roster_item` (inferred from the chain
above).

**A second derivation already disagrees** (read). At creation, `resolve_dev_role` looks for
the per-slug override at `tech.strip().lower() + "-dev"`. Every later resolution looks it up
by the stored slug. For `--tech Node.js`, creation reads `node.js-dev.toml` and every later
read uses `node-js-dev.toml`.

**Precedent.** ADR-754 established that `dev_role` is a generator: it is correct exactly
once, at creation, and calling it again for a role that already exists re-rolls a lossy
derivation. That ADR applied the rule to the developer's name. The slug belongs to the same
class of field.

## Decision

**1. A stored slug is identity. Derivation only proposes a slug for something being
created.**

- Once a roster entry (role, developer role, skill, operator) exists, its identity is
  `item.extra.get(X.SLUG, item.slug)`. That is the expression `resolve_role_for_item`, the
  validators and the backend already use. Once a memory entry exists, its identity is its
  filename stem.
- `slugify`, `operator_slug` and the developer `<tech>-dev` rule run only when a slug is
  proposed for a new entry.
- No read, resolve, sync, check or repair path recomputes a slug from a title, a name or a
  tech label.

**2. A developer role resolves to its stored slug.**

- `dev_base_from_item` takes `slug` from the item, never from `slugify(extra.tech)`.
  `extra.tech` stays an input to the generated template (surname, title, mission) and nothing
  else.
- As a result, `_refresh_catalog_extra` converges `extra.slug` onto itself, which is a
  no-op, and the pointer keeps its filename.
- At creation, `resolve_dev_role` looks up the per-slug override under the same slug the
  role will be stored with, `slugify(tech) + "-dev"`, so there is one derivation instead of
  two.

**3. Existing slugs stay as they are.**

- No migration, and no re-slug verb.
- A slug is referenced from places squads does not own or must not rewrite: `@mentions` in
  discussions and agent-authored bodies (invariant 3), and generated files and scripts in
  other clones.
- A rename verb, if one is ever wanted, is its own feature, because covering those
  references is its whole difficulty.

**4. Duplicate detection at creation matches both derivations.**

- `add_operator` (without an explicit `--slug`), `add_skill` and `add_dev` refuse when a
  stored slug of the same roster type equals the proposed slug under the current rule **or**
  under the rule before this fix.
- The earlier rule is kept as one private, frozen function. It is used for this comparison
  only and never to propose a slug.
- The refusal names the existing entry's slug.
- An explicit operator `--slug` is compared exactly. It is the escape hatch for a genuinely
  different person.
- Memory entries are out of scope. `add` already disambiguates with a numeric suffix, and a
  memory is not an identity that other entries reference.

**5. This is compatible with retiring the `-dev` pseudo-role.**

- Decision 2 gives developer roles the identity rule bundled roles already follow: the slug
  is stored and never derived on read. It removes the slug's dependence on the tech label,
  which is the direction that retirement takes (identity by a declared property, not by a
  spelling).
- It adds no new reader of the `-dev` suffix and decides nothing about how developer roles
  will be identified or migrated. The ADR for that retirement owns those questions.

## Consequences

- The `slugify` transliteration fix is safe for every stored identity once decisions 2 and 4
  land with it.
- Work-item filename slugs are unaffected. They are derived at creation and re-derived only
  by a retitle, which renames the file in the same step (read, BUG-965). A retitle of an item
  created before the fix produces the new form, which is expected.
- The earlier `slugify` rule stays in the codebase as permanent code. It is small, and
  removing it would only be possible after a rename of stored slugs, which decision 3
  declines.
- ADR-754's list of fields `dev_base_from_item` takes from the item grows to include `slug`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:45:27Z] Robert Architect:
  - @op-pierre for your call: left Proposed. Written to settle the TASK-969 ST4/ST5 questions the tech lead raised.
- [2026-09-29T13:53:01Z] Pierre Chat:
  - Accepted. No slug-rename command: existing slugs stay as they are.
<!-- sq:discussion:end -->
