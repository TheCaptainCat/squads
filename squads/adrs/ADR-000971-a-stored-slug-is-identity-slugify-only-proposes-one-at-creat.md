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
- ADR-984
- ADR-1007
- ADR-1151
description: No path re-derives a stored slug; dev roles resolve to their stored slug;
  existing slugs stay; duplicates match both rules
created_at: '2026-09-29T13:41:21Z'
updated_at: '2026-10-25T21:42:25Z'
---
<!-- sq:body -->
## Context

BUG-965: `slugify` (`_util.py`) dropped non-ASCII letters (`Réduire` became `r-duire`,
`Élodie` became `op-lodie`). Fixing the derivation function is safe only if no path re-derives a
slug after creation, because such a path would then disagree with the slug it stored.

**Where a slug is derived.** `create` (`slug or slugify(title)`), `add_skill` (`slugify(name)`),
`add_operator` (`operator_slug(name)`, bypassed by an explicit `--slug`), `add_dev` (the
`<slugified tech>-dev` proposal, bypassed by an explicit `--slug`), memory `add`, and a work-item
retitle (`_rename`), which moves the file to the new name in the same step.

**Where a slug is looked up.** `roster_item` compares the stored slug exactly. `--as`,
`--assignee`, `sq skill <slug>` and `sq memory <role> show <slug>` match stored strings. Load and
repair read a work item's slug from its frontmatter or its filename. None of these recomputes a
slug.

**The developer role was the one re-derivation.** When this was decided, `dev_base_from_item`
rebuilt the base `RoleDef.slug` as `slugify(tech) + "-dev"` on every resolve, the catalog
refresh merged it back into the item on every sync, and the Claude Code backend named the
pointer from it. A transliteration fix would have renamed every accented developer's stored
slug and pointer on the next sync, while its filename, `@mentions`, `--as` values and assignees
kept the old one. Creation also looked up the per-slug override under `tech.strip().lower() +
"-dev"` while every later read used the stored slug, so `--tech Node.js` read
`node.js-dev.toml` once and `node-js-dev.toml` afterwards.

**Precedent.** ADR-754 established that the developer template is a generator: it is correct
once, at creation, and running it again for an existing role re-rolls a lossy derivation. That
decision applied the rule to the developer's name. The slug belongs to the same class of field.

## Decision

**1. A stored slug is identity. Derivation only proposes a slug for something being created.**

- Once a roster entry (role, developer role, skill, operator) exists, its identity is
  `item.slug`, the core frontmatter key (ADR-1007). Once a memory entry exists, its identity is
  its filename stem.
- `slugify`, `operator_slug` and the developer `<tech>-dev` proposal run only when a slug is
  proposed for a new entry.
- No read, resolve, sync, check or repair path recomputes a slug from a title, a name or a tech
  label.

**2. A developer role resolves to its stored slug.**

- `dev_base_from_item` takes `slug` from the item, never from the tech label. The role's `tech`
  attribute is an input to the generated template (surname, title, mission), and its presence on
  a role item marks a templated developer (ADR-984 decision 4); ADR-1151 moves the choice of base
  to a stored `template` attribute, with `tech` as its parameter. It supplies no identity and never
  says what the role may do.
- The catalog refresh therefore converges the stored slug onto itself, which is a no-op, and
  the pointer keeps its filename.
- At creation, `resolve_dev_role` looks up the per-slug override under the slug the role will be
  stored with: the explicit `--slug` when given, otherwise `slugify(tech) + "-dev"`. There is one
  derivation, not two.

**3. Existing slugs stay as they are.**

- No migration, and no re-slug verb.
- A slug is referenced from places squads does not own or must not rewrite: `@mentions` in
  discussions and agent-authored bodies (invariant 3), and generated files and scripts in other
  clones.
- A rename verb, if one is ever wanted, is its own feature, because covering those references is
  its whole difficulty. ADR-979 decision 1 makes the slug permanent.

**4. Duplicate detection at creation matches both derivations.**

- `add_operator` (without an explicit `--slug`), `add_skill` and `add_dev` (without an explicit
  `--slug`) refuse when a stored slug of the same roster type equals the proposed slug under the
  current rule **or** under the rule before the transliteration fix.
- The earlier rule is kept as one private, frozen function (`legacy_slugify`, and
  `legacy_operator_slug` beside it). It is used for this comparison only and never to propose a
  slug.
- The refusal names the existing entry's slug.
- An explicit `--slug` is compared exactly. It is the escape hatch for a genuinely different
  person or a second developer of one tech.
- Memory entries are out of scope. `add` already disambiguates with a numeric suffix, and a
  memory is not an identity that other entries reference.

**5. Identity by a stored property, not by a spelling.**

Decision 2 gives developer roles the identity rule bundled roles already follow: the slug is
stored and never derived on read. No read path consults the `-dev` suffix; a developer is
identified by the capability it declares (ADR-984).

## Consequences

- The `slugify` transliteration fix is safe for every stored identity.
- Work-item filename slugs are unaffected. They are derived at creation and re-derived only by a
  retitle, which renames the file in the same step. A retitle of an item created before the fix
  produces the new form, which is expected.
- The earlier `slugify` rule stays in the codebase as permanent code. It is small, and removing
  it would only be possible after a rename of stored slugs, which decision 3 declines.
- `slug` is one of the fields `dev_base_from_item` takes from the item (ADR-754).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:45:27Z] `architect` Robert Architect:
  - @op-pierre for your call: left Proposed. Written to settle the TASK-969 ST4/ST5 questions the tech lead raised.
- [2026-09-29T13:53:01Z] `op-pierre` Pierre Chat:
  - Accepted. No slug-rename command: existing slugs stay as they are.
- [2026-10-25T21:42:25Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale passages fixed; decision unchanged. Identity expression is item.slug (ADR-1007 note folded), tech is a top-level attribute, sq dev add --slug is recognised in decisions 2 and 4, legacy_slugify named; the ADR-984 narrowing folded and ADR-1151 cited for template selection. Related ref to ADR-1151.
<!-- sq:discussion:end -->
