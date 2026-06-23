---
id: ADR-000179
sequence_id: 179
type: decision
title: 'Parameterized item-file storage: prefix scope vs layout, and the ItemStore
  locator seam'
status: Proposed
author: architect
refs:
- FEAT-000176:addresses
- ADR-000180
description: Global prefix changes the ID prefix only; folder layout is a separate
  knob; both plug into a shared ItemStore locator
created_at: '2026-06-23T12:58:51Z'
updated_at: '2026-06-23T12:59:42Z'
---
<!-- sq:body -->
## Context

`FEAT-000176` wants two `.squads.toml` knobs behind the local item-file store: a single
**global prefix** that replaces the per-type prefix table, and a **flat layout** that drops the
per-type subfolders. The feature explicitly defers one decision to this ADR: *when a global prefix
replaces the per-type prefixes, does it change the ID prefix, the folder prefix, or both?*

Today the two are driven by **two independent maps** keyed by the same `ItemType`, in
`_models/_enums.py`:

- `PREFIX_BY_TYPE` (`FEATURE → "FEAT"`) feeds the **formatted ID** — `Item.id` is a
  `@computed_field` returning `format_item_id(self.type.prefix, self.sequence_id, padding)`
  (`_models/_item.py`). The number itself comes from the **single global counter** (`allocate_id`),
  not from the prefix; the prefix is a pure type marker.
- `FOLDER_BY_TYPE` (`FEATURE → "features"`) feeds **path resolution** — `SquadPaths.folder_for`
  / `squad_relative` in `_paths.py`.

So the prefix and the folder are *already decoupled in the data model* (two maps), but **coupled by
convention** (every type's prefix and folder are chosen to rhyme). Nothing in the integrity core
requires them to match: `from_frontmatter` keys items by integer `sequence_id`, refs match on
`(prefix, seq)` whole-word, and `sq repair` rebuilds from frontmatter. The ID prefix is essentially
cosmetic/identity-facing; the folder is purely filesystem layout.

A second, framing concern from the feature: both knobs (and the `FEAT-000177` format swap) should
plug into a **storage abstraction** rather than scattering conditionals through `_paths.py`,
`_itemfile.py`, and `_models/_item.py`.

## Decision

**1. Global prefix changes the ID prefix only; folder layout is governed by a separate `layout`
knob.** Treat prefix-scope and folder-scope as two orthogonal axes rather than one coupled switch:

- `prefix = "<CODE>"` replaces the per-type **ID** prefix for *all* types, so IDs become
  `<CODE>-000001`, `<CODE>-000002`, … across features/tasks/bugs alike. The type is still carried
  in frontmatter (`type:`) and in the index; it is simply no longer encoded in the ID string. This
  is sound because the integer sequence is already globally unique (invariant 2) and type identity
  already lives in frontmatter, not in the prefix.
- `layout` governs folders independently: `layout = "nested"` (default) keeps `FOLDER_BY_TYPE`;
  `layout = "flat"` puts every item file directly under the squad dir.

We deliberately **do not** let the custom prefix rename folders. A single global prefix would
collapse all folder names to one string, which is exactly what `layout = "flat"` already expresses
more honestly — folding it into the prefix knob would give two ways to say "one directory" and a
confusing third state (custom prefix + nested = per-type folders named after a non-type prefix).
Keeping the axes orthogonal yields four clean, independently-testable combinations.

**2. Resolution must be uniqueness-safe under a custom prefix + flat layout.** With a single prefix
*and* a flat directory, the filename can no longer lean on a type folder for disambiguation. The
filename **must** therefore embed the globally-unique id (`<CODE>-000007-slug.md`). This already
holds today (filenames are id-prefixed); the ADR just records it as a hard requirement the store
contract must guarantee, because flat layout removes the folder as a second namespace.

**3. Introduce an `IdScheme` + `LayoutScheme` resolved once, behind a storage-locator seam.**
Rather than scatter `if config.prefix` / `if config.layout` across modules, route every
prefix/folder decision through small resolver objects derived from config at squad-open time:

- `prefix_for(item_type) -> str` (returns the custom prefix when set, else `type.prefix`).
- `folder_for(item_type) -> str` (returns `""`/squad-root for flat, else `type.folder`).
- `filename_for(item) -> str` and `squad_relative(item) -> str` built on the above.

`Item.id` currently reads `self.type.prefix` directly. To honor a config-driven prefix without
threading config into the model, the prefix becomes a **render-time concern**: the model keeps
`(type, sequence_id)` as identity, and the formatted string is produced through the resolver at the
edges (CLI/render/path), or the active prefix is injected into the model factory at load. The ADR's
recommendation is to keep `(type, sequence_id)` canonical and resolve the display/id-string prefix
through the locator, so the global counter and type identity stay untouched.

## This is the shared storage seam with FEAT-000177

This locator is the **same pluggable local-file-management abstraction** that `FEAT-000177`
(serialization format) plugs into — see that feature's ADR. The clean split is:

- **This ADR (`FEAT-000176`) owns identity + location**: how an item maps to a prefix string and to
  a path. It is format-agnostic.
- **The `FEAT-000177` ADR owns content**: how the item + its body/prose regions are serialized
  inside whatever file the locator names.

Recommendation: define one `ItemStore` protocol with two cleanly separable responsibilities — a
**locator** half (id-string + path resolution; this ADR) and a **codec** half (serialize/parse +
marker-equivalent body regions; the `FEAT-000177` ADR). Implement the locator half here first; it
ships independently because prefix/layout don't touch serialization. The two ADRs must agree on the
`ItemStore` surface so the codec swap and the layout swap compose (e.g. JSON + flat + custom prefix).

## Consequences

- **Default unchanged.** Absent `prefix`/`layout`, both maps behave exactly as today; existing
  squads need no migration (matches the feature's acceptance).
- **Refs stay valid under a custom prefix** because `ref_id_matches` compares `(prefix, seq)` and
  the prefix is uniform; but **cross-prefix refs in pre-existing files** (`FEAT-…` written before a
  team adopts a custom prefix) would no longer match a re-prefixed item. Adopting a custom prefix on
  a non-empty squad is therefore a **migration**, not a live toggle — recommend gating it to
  `sq init` / a dedicated `sq migrate` step, not an arbitrary edit of an established squad. New/empty
  squads can set it freely.
- **Type is no longer visible in the ID string** under a custom prefix; tooling/humans that parsed
  the type out of the ID must read `type:` from frontmatter or `sq show`. `TYPE_BY_PREFIX` reverse
  lookup becomes inapplicable for custom-prefix squads (the index already carries type, so the core
  is unaffected).
- **Flat layout removes the folder namespace**, so id-embedded filenames become load-bearing rather
  than merely conventional; `sq repair`/`sq check` must scan the squad root (not per-type folders)
  in flat mode.
- **One seam, two features.** Centralizing resolution in the locator is the prerequisite that lets
  both this feature and `FEAT-000177` land without scattering config conditionals through the core.

## Alternatives considered

- **Single coupled knob (prefix renames both ID and folders).** Rejected: collapses all folders to
  one name (duplicating flat layout), and creates an incoherent "custom prefix + nested" state.
- **Custom prefix changes folders only, IDs keep per-type prefixes.** Rejected: the stated user
  value is "our squad reflects our project code instead of the type taxonomy" — that is an
  *identity* (ID-string) ask, not a foldering ask; folders are covered by the layout knob.
- **Per-type custom prefixes (a full override table).** Rejected as out of scope — the feature asks
  for *one* global prefix; a full table is a heavier, separately-justified feature.

## Status

Proposed — drafting only. No implementation, tasks, or feature transition until accepted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
