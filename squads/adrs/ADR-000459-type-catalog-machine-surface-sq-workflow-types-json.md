---
id: ADR-459
sequence_id: 459
type: decision
title: 'Type catalog machine surface: sq workflow types --json'
status: Accepted
author: architect
refs:
- TASK-450
- REV-448
- ADR-427
- ADR-541
- ADR-474
- ADR-646
- ADR-738
description: 'New frozen --json type catalog on a dedicated subcommand (sq workflow
  types): bare array of {type, order|null, prefix, reserved} in resolved order; additive-superset
  + golden-frozen; unblocks TASK-450 (REV-448 F1).'
created_at: '2026-07-17T14:04:05Z'
updated_at: '2026-10-25T21:28:43Z'
---
<!-- sq:body -->
## Context

A machine client needs the workflow spec's per-type facts, starting with `ItemSpec.order`, so it can
sort type groups by the spec instead of alphabetically (REV-448 F1). Per ADR-427 the VS Code client
is a pure consumer of `sq … --json`, so exposing them means a CLI surface, not a model dump.

`order` is a per-**type** property. Repeating it on every `sq tree`/`sq list` node would copy one
value onto every node of a type, derivable from the node's `type` and a one-time lookup. The right
shape is a **type catalog**: each declared type listed once with its per-type metadata.

Two adjacent points constrain where it lives. `sq workflow` (`show`) is the human cheatsheet, with
its own `--raw` markdown output; a `--json` on the same callback would make one command emit two
unrelated payloads. And the item `--json` read surfaces are bare JSON arrays of flat objects, a
convention a new surface should match.

## Decision

**1. Surface — a subcommand, `sq workflow types`.** Not a flag on the cheatsheet. Without `--json`
it prints a human table; with `--json` it emits the machine shape below.

**2. Shape — a bare JSON array, one object per declared type**, in ascending resolved `order` (type
name breaking ties), the order the CLI registers per-type commands in. Every declared type is
listed, roster types included, so a client derives the roster/work split from the catalog rather
than a hardcoded role/skill/operator list. This decision fixes four keys:

- `type` — the type key; matches the `type` field on item rows.
- `order` — the resolved `ItemSpec.order` as a JSON number, or `null` for a type that declares
  none (`+inf`). The key is always present; a consumer sorts `null` last.
- `prefix` — the id prefix.
- `reserved` — `true` for the roster types, computed as `category == "roster"` (ADR-541).

The row carries further keys added by later decisions, each under the additive rule of §3:
`category` (ADR-541), `subentity_kind` and `lifecycle` (ADR-738), `fields` (ADR-474 A3),
`attributes` (ADR-1007) and `labels` (ADR-646). `TYPE_CATALOG_FIELDS` in `_cli/_workflow_cmd.py` is
the declared key set. The catalog reads the active spec throughout. It carries no `folder`, an
on-disk internal the consumer contract keeps clients away from. The type catalog is one of the
`sq workflow` catalog family; ADR-738 owns the family's completeness rule.

**3. Evolution — additive only, pinned by a golden.** The JSON shape is pinned by a golden fixture
and a test that the emitted key set equals the declared constant. Changes are additive: a key may
be added, never removed or renamed. A decision that adds a key to this catalog says so in its own
body and names the catalog it extends; ADR-1025 sets what a listed key freezes.

## Consequences

- A client sorts type groups by a real spec value in one call and derives the roster/work split
  from `reserved`, with no hardcoded type list.
- `order` stays a single per-type fact exposed once.
- Separate concerns keep their own surfaces: statuses, collections and roles have sibling catalogs
  (ADR-474, ADR-604), and the cheatsheet keeps `--raw`.
- One more pinned shape to keep under the golden discipline, the intended cost of a contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:04:44Z] `architect` Robert Architect:
  - Proposed. Authored to settle TASK-450's surface (REV-448 F1 core half) before the build. Chose a dedicated `sq workflow types` subcommand over a --json flag on the cheatsheet to keep each surface single-purpose and leave `sq workflow --raw` (F8) unconflicted. Needs Pierre/tech-lead sign-off before Accepted.
- [2026-07-17T15:34:38Z] `op-pierre` Pierre Chat:
  - Signed off — accept.
- [2026-08-03T08:45:41Z] `architect` Robert Architect:
  - Corrected the `reserved` derivation in place: it is `ItemSpec.category == "roster"` (ADR-541), not `is_meta`. Same verdict, different route — the category is exactly the axis the boolean stood in for — so this is a citation fix, not a contract change. The catalog itself is verified in force.
  - The finding worth keeping is not the citation but the rows growth. This decision froze four keys; the live row carries seven — `+fields` (ADR-474 A3), `+category` (ADR-541), `+labels` (ADR-646) — and only the first is declared at its own end as an extension of this catalog. All three are legitimate under the additive-superset rule, so nothing is a breach; but a frozen shape whose growth is undocumented cannot be audited against its own freeze, which is the point of freezing it. Recorded the forward rule: a decision adding a key to a frozen catalog says so in its own body and names the catalog.
  - Added `related` edges to ADR-541, ADR-474 and ADR-646.
- [2026-10-25T21:28:43Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the catalog decision is unchanged. The row has ten keys, not four or seven: added subentity_kind and lifecycle (ADR-738) and attributes (ADR-1007) to the list of later additions, pointing at TYPE_CATALOG_FIELDS as the declared set. Folded the is_meta citation fix and the "a decision adding a key says so" rule from the 2026-08-03 amendment into §2 and §3, and replaced "no status catalog, out of scope" with the sibling catalogs that exist.
<!-- sq:discussion:end -->
