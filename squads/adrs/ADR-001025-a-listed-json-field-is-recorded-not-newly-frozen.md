---
id: ADR-1025
sequence_id: 1025
type: decision
title: A listed --json field is recorded, not newly frozen
status: Proposed
author: architect
refs:
- FEAT-1024
- REV-958
- ADR-738
- ADR-775
- ADR-947
- ADR-427
- ADR-459
description: Listing a field in docs/stability.md records the existing Tier 3 freeze;
  no new tier, but each key's value is marked vocabulary, open set or display.
created_at: '2026-10-15T21:48:00Z'
updated_at: '2026-10-15T21:51:08Z'
---
<!-- sq:body -->
## Context

FEAT-1024 US3 moves the `--json` field reference out of the help of `sq search`, `sq tree`, `sq graph` and `sq workflow ref-kinds` and into `docs/stability.md` (REV-958 F3, R6). The story asks whether writing those fields into the stability document extends the frozen contract to every field it lists, and whether there is a tier distinction among them.

What the contract says today (read):

- Tier 3 freezes shapes by command. `list`, `tree`, `graph`, `inbox`, `search` and the others are named in the frozen surface, and `docs/stability.md` closes the section with: "The promise above covers the fields a shape emits either way, whether or not you find them enumerated here." Every key `search`, `tree` and `graph` emit is therefore frozen now, unlisted.
- `sq workflow ref-kinds --json` is a catalog under ADR-738 (one catalog per declared spec map; ADR-775 names it as owed). ADR-738 §8 puts every catalog in Tier 3 and says the stability catalog table "gains a row per catalog". That table has seven rows and no `ref-kinds` row, and the payload has a golden (`tests/goldens/workflow_ref_kinds.json`). The row is owed, not new.
- The same document names help as the authority for `search`, `tree` and `graph` ("document their shapes there in full"). That authority is already wrong in one place: `sq graph --json` emits `badges` on every node (golden `graph_feat_json.json`, read), and its help does not list it (driven, `sq graph --help`).
- Tier 3 promises a key's name, type and presence. It says nothing about the values a key may carry, and several keys carry values a consumer must not treat as a fixed set: `edge_kind` is the project's own spelling (ADR-775), the omissions report's `code` is an open set that grows additively (ADR-947 §3), and `source` there is a display token not to be parsed.

## Decision

### 1. Listing a field records the freeze; it does not set it

A shape is frozen by its command's place in Tier 3, and the freeze already covers every key the shape emits. Writing a key into `docs/stability.md` records that promise where a reader can find it. Leaving a key out never exempted it. Moving the field reference of `search`, `tree`, `graph` and `workflow ref-kinds` from help into the document changes no promise, and needs no decision beyond this one.

The `ref-kinds` row discharges ADR-738 §8 for the one catalog its table omitted.

### 2. The document is the authority, and it is written from the payload

The sentence naming `sq <command> --help` as the authority for a shape is withdrawn. For every shape whose fields the document enumerates, the enumeration matches the live payload key for key, in emitted order, and is checked against the golden rather than copied from help. A shape the document does not enumerate (`list`, `blocked`, `workload`, `mine`) keeps the rule that its emitted fields are its contract.

A new Tier 3 shape lands with its field reference in the document in the same change. Help carries the one-line `--json` description, any sentence a caller needs in order not to misuse the payload, and the pointer.

### 3. No new tier. Within Tier 3, a key's value is classed

Every listed key is frozen in name, JSON type, presence (`null` rather than omitted where the shape states that convention) and meaning. What its value promises differs, and the field reference marks each key whose value is not a fixed squads format with exactly one of three classes:

- **vocabulary**: the value is a name the squad declares: an item type, a status, a priority code, a ref kind, a sub-entity kind or local id, a badge field (from the active spec), or an assignee slug (from the roster). Frozen: that it names an entry of the corresponding catalog or roster. Not frozen: which names exist. Read the catalog; never hardcode a name.
- **open set**: a squads-defined value from a set that may grow between majors. A consumer handles a value it does not recognise without failing, and never infers anything from the set being complete. The forms that exist are listed.
- **display**: human text. The key is frozen; its content is not, and is never parsed or compared.

A key with no mark carries a fixed squads format, frozen with the key: an item id, a boolean, `direction`'s `in`/`out`, nested `children`.

Applied to the four shapes US3 moves (read from the goldens and help; the doc writer verifies each against the live payload):

| Shape | vocabulary | open set | display |
|---|---|---|---|
| `search` | `type`, `status`; the kind and local id inside `region` | `region` (its form family: `title`, `description`, `body`, `discussion#<n>`, `<kind>:<local_id>`, `<kind>:<local_id>:discussion#<n>`) | `location`, `snippet` |
| `tree` | `type`, `status`, `priority`, `assignee`, the keys of `badges` | none | none |
| `graph` | `type`, `status`, `priority`, `assignee`, `edge_kind`, the keys of `badges` | `edge_semantic` | none |
| `workflow ref-kinds` | `kind` | `role` | `label`, `hint` |

`title` is stored item data and carries no mark.

The marking is three words defined once, in the Tier 3 introduction and the glossary. Its typography (a column, a suffix) is the writer's call; the words are not.

### 4. Changing a class is a contract change

A key moves to a stricter class (display to open set, open set to fixed) freely. It moves to a looser one only by a decision that says so in its body and names the shape, under the same rule ADR-459 sets for adding a key to a frozen catalog. The classes this decision assigns loosen no written promise: no document stated that `edge_semantic`, `region` or `role` was a closed set (read: a search of `docs/` names neither `edge_semantic` nor search's `region`; `docs/workflow.md` lists the four ref-kind `role` values the engine reads today, as a description, with no promise the set will not grow; graph's help lists three `edge_semantic` values as examples, and help is not contract). The `role` case is the nearest to a narrowing, and is called out here so a reader of `docs/workflow.md` is not surprised: the writer adds the open-set mark there too.

## Consequences

- FEAT-1024 US3 proceeds with no contract risk: the docs change records fields already frozen.
- A consumer bound by ADR-427 §2 gains an explicit rule it was already exposed to: an unrecognised `edge_semantic`, `region` form or ref-kind `role` is tolerated, not an error.
- The writer's pass costs one verification per enumerated key against the live payload; that check, not help, is what found `graph`'s missing `badges`.
- The stability document's other enumerated shapes (catalogs, reflog, override inspection, omissions report) take the same marks when next touched. The omissions report already reads this way in prose (`code` open, `source` and `message` display) and needs only the words.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T21:51:08Z] Robert Architect:
  - Authored for FEAT-1024 US3. An ADR rather than a dated note: search, tree and graph have no governing ADR of their own, and the value-class rule spans catalogs (ADR-738), graph semantics (ADR-775) and the omissions report (ADR-947), so a note on any one would bind the others from the wrong place. Once accepted, dated notes owed on ADR-738 §8 (ref-kinds row discharged) and ADR-427 §2 (tolerate unknown open-set values).
<!-- sq:discussion:end -->
