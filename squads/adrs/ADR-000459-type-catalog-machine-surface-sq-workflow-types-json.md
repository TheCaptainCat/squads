---
id: ADR-459
sequence_id: 459
type: decision
title: 'Type catalog machine surface: sq workflow types --json'
status: Proposed
author: architect
refs:
- TASK-450
- REV-448
- ADR-427
description: 'New frozen --json type catalog on a dedicated subcommand (sq workflow
  types): bare array of {type, order|null, prefix, reserved} in resolved order; additive-superset
  + golden-frozen; unblocks TASK-450 (REV-448 F1).'
created_at: '2026-07-17T14:04:05Z'
updated_at: '2026-07-17T14:04:44Z'
---
<!-- sq:body -->
## Context

REV-448 F1 (and its core half, TASK-450) needs the workflow spec's per-type `order`
(`ItemSpec.order`) reachable by the VS Code client so it can sort type groups spec-driven
instead of alphabetically. Per ADR-427 the client is a **pure consumer of `sq … --json`** —
it must not read `.squads.json` or the spec files — so "expose `order`" means a `--json` CLI
surface, not a model-dump artifact like `playbook_spec.json` (which is a golden-frozen
`model_dump`, not a CLI surface, so a client cannot reach it).

`order` is a per-**type** property. Repeating it on every `sq tree`/`sq list` node would be
redundant — the same value copied onto every node of a type, derivable from the node's `type`
plus a one-time catalog lookup. The right shape is a **type catalog**: the declared types
listed once, each with its per-type metadata.

Two adjacent design points constrain where it lives:
- `sq workflow` (its `show`/default callback) is the **human cheatsheet**, and REV-448 F8 will
  add `--raw` to emit that cheatsheet as clean markdown. Overloading a `--json` onto the same
  callback would make one command emit two unrelated payloads (cheatsheet-as-markdown vs. a
  type catalog that is not the cheatsheet at all) — a conflation to avoid.
- Existing `--json` read surfaces (`tree`/`list`/`show`, frozen by FEAT-15) are all **bare JSON
  arrays** of flat objects; a new surface should match that convention.

## Decision

**1. Surface — a new subcommand, `sq workflow types`.** Not a flag on the cheatsheet callback.
It joins the existing `sq workflow` group (`show`, `lint`, + `types`) with clean single-purpose
grammar, and leaves `sq workflow`/`show` free for F8's `--raw`. Default (no `--json`) prints a
human Rich table; `--json` emits the frozen machine shape below. This mirrors the `list`
table-plus-`--json` pattern and `lint`'s dual human/exit-code nature.

**2. Shape — a bare JSON array, one object per declared type**, emitted in ascending resolved
`order` (type-name string breaks ties) — the same ordering the CLI uses to register per-type
commands. Every declared type is included, work and reserved alike, so the client can spec-drive
the work-vs-reserved split (e.g. REV-448 F12's meta view) without a hardcoded
role/skill/operator list. Field set per object:

- `type` — the type key (e.g. `"task"`); matches the `type` field already on `tree`/`list` nodes.
- `order` — the resolved `ItemSpec.order` as a JSON number, or `null` when it is `+inf`
  (an un-ordered/custom type). `null` is present-but-empty (not omitted) so the key set is stable
  across every object and the golden; a consumer sorts `null` last, type-name tiebreak.
- `prefix` — the id prefix (e.g. `"TASK"`).
- `reserved` — boolean, `= ItemSpec.is_meta`; `true` for the reserved meta-types
  (role/skill/operator). Named for the operator-facing "reserved types" vocabulary.

Spec-driven throughout: read from the active `WorkflowSpec` (`.types` / `work_types()` + the meta
types), never a hardcoded type list. No `title` field — item types have no distinct label in
`ItemSpec`; the type key is the label (a Title-cased form is client-derivable, so storing it here
would be redundant). No `folder` — an on-disk internal the consumer contract forbids the client
from using. No lifecycle/status catalog — a separate, larger surface, out of scope here; this
catalog is type-identity only.

**3. Semantics — additive-superset + golden-frozen, same discipline as FEAT-15.** No existing
`--json` shape changes. A new golden under `tests/goldens/` (e.g. `workflow_types.json`) pins the
byte-identical shape, with a test asserting it and that the field set matches the model. Future
additions to this surface are additive-only (new keys), never removals or renames.

## Consequences

- The client sorts type groups by a real spec value via one `sq workflow types --json` call and
  derives the work-vs-reserved split from `reserved` — no hardcoded type list, satisfying
  REV-448 F1/F12's spec-driven requirement.
- `order` stays a single per-type fact exposed once, not duplicated onto every tree/list node.
- One coherent type-identity catalog now (`order`+`prefix`+`reserved`) rather than piecemeal
  surfaces later; genuinely separate concerns (the workflow machine's statuses/transitions,
  the cheatsheet's `--raw`) stay their own surfaces.
- Adds one more frozen shape to keep under the golden-freeze discipline — the intended cost of a
  frozen contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:04:44Z] Robert Architect:
  - Proposed. Authored to settle TASK-450's surface (REV-448 F1 core half) before the build. Chose a dedicated `sq workflow types` subcommand over a --json flag on the cheatsheet to keep each surface single-purpose and leave `sq workflow --raw` (F8) unconflicted. Needs Pierre/tech-lead sign-off before Accepted.
<!-- sq:discussion:end -->
