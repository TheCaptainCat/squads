---
id: ADR-232
sequence_id: 232
type: decision
title: 'De-type Item to str: spec-validated vocabulary, TypeSpec capability flags,
  reserved-vocab core'
status: Accepted
author: architect
refs:
- FEAT-208:addresses
- ADR-214
- ADR-322
- ADR-541
- ADR-323
- ADR-696
created_at: '2026-06-26T09:45:13Z'
updated_at: '2026-10-27T21:05:27Z'
---
<!-- sq:body -->
## Context

ADR-214 externalizes the workflow into a loaded `WorkflowSpec`. While the model fields were typed by
the `ItemType` / `Status` enums, the vocabulary stayed closed: frontmatter with an unknown
`type`/`status` raised at model construction, so custom vocabulary could not even be read.

`FEAT-000208` relaxes that: a typed *engine* over a runtime-defined *vocabulary*. It is the
highest-risk step in `EPIC-000206`, because the typing inversion is pervasive. Its scope is de-typing, capability-flag
reification, a protected core of reserved vocabulary, and fail-closed spec loading.

## Decision

### 1. The model fields are `str`, validated at the load boundary

- `Item.type`, `Item.status` and `SubEntity.status` are plain `str`.
- Model construction does no vocabulary lookup. Every existing item file is already a valid string,
  so this is a typing/validation change, **not a data migration**.
- Vocabulary validation happens **at the load boundary**, against the active `WorkflowSpec`: loading
  the index checks each item's type, status and sub-entity statuses, raising `SquadsError` with the
  offending item id on an unknown value. Pydantic type-checks "is a str"; the *vocabulary* check is
  the spec's job. A pydantic validator cannot see the loaded spec without threading external state
  through construction, so the load boundary is the natural seam.

### 2. Every hardcoded identity check is a declared capability on `ItemSpec`

No behavioral type-identity `is` check is left hardcoded in the engine. What a type *is* for the
engine is declared on its `ItemSpec`:

```
ItemSpec (capability fields)
    category:        "roster" | "work" | "records"   # ADR-541: roster types are slug-keyed,
                                                     #   outside the work lifecycle, retype-ineligible
    subentity_kind:  str | None = None   # the kind a type's children are (drives add-<kind>), ADR-348
    parent_required: str | None = None   # the parent type rule, declared
    ref_rules:       list[RefRule] = []  # e.g. task → fixes|addresses; decision → supersedes
    fields:          list[Field] = []    # badge-collection bindings such as priority/severity, ADR-323
```

Each former identity check maps to one of these:

| Former identity check | Behaviour | Declared as |
|---|---|---|
| `is ROLE/SKILL/OPERATOR` branches | slug-keyed lookup, skill-prefix file rule, roster filtering, author-is-self | **`category = "roster"`** |
| `in WORK_TYPES` | which types get a `sq <type>` app and are retype-eligible | **non-roster category** (`spec.non_roster_types()`) |
| parent → sub-entity-kind maps | feature→story, task→subtask, review→finding | **`subentity_kind`** |
| task → feature parent + fixes/addresses rules | the task spine | **`parent_required`** + **`ref_rules`** |
| the task-specific `parent_hint` text | link a bug/review via a ref | **`ref_rules`** drive the hint |
| decision + `Superseded` supersede warning | ADR supersede rule | a **`supersedes` ref rule** keyed off a **status role** |
| bug severity row | severity surfacing | a **`fields`** binding |
| identity checks inside migration runners | historical scaffolding | **frozen — not reified** (§ Scope boundary) |

On the status axis, the engine binds to a **declared status role** (`StatusSpec.role`), never to a
status name: one optional role name per status rather than a flag per behaviour, so a future rule
adds a role, not a column. Terminality and openness derive from the role (ADR-696).

### 3. The spec is the sole vocabulary authority

There is no `ItemType` or `Status` enum (ADR-322). The reserved roster type keys are named constants
(`ROSTER_ROLE`/`ROSTER_SKILL`/`ROSTER_OPERATOR`); everything else is vocabulary the spec declares.

### 4. Reserved-vocabulary invariant — additive over a protected core, fail-closed

> Loading the spec MUST raise `SquadsError` if the spec omits any reserved vocabulary. Custom
> vocabulary is **additive over the reserved core**; it can extend, never remove.

- **Reserved types:** the three roster types `role`, `skill` and `operator`, with their fixed
  `roster` category — the engine's slug-keyed machinery depends on them existing (ADR-322,
  ADR-541). The work-item types are ordinary vocabulary a project may drop, rename and re-prefix.
- **No reserved statuses.** No status name is engine-bound; a roster lifecycle is held to a
  structural floor instead (ADR-696 §2–§3).
- **Location:** the check runs inside the spec loader, fail-closed.

### 5. Fail-closed spec loading: `extra="forbid"`

Every workflow spec model carries `extra="forbid"` and the loader builds them through
`model_validate`, so an unknown TOML key fails closed instead of being silently ignored — the same
hardening the roles and playbook loaders have.

### 6. The pyright-strict trade-off, on the record

Widening to `str` trades **compile-time enum exhaustiveness** for **load-time spec validation**.
What we lose: pyright can no longer prove a `match item.type` / status handling is exhaustive; a
typo in a type/status string is a load-time error, not a type error; autocomplete on enum members at
field sites goes away. What we keep: the **engine stays fully typed** — `WorkflowSpec`, `ItemSpec`,
`StatusSpec` are pyright-strict models, the capability fields are typed, and every operation on
vocabulary goes through typed spec methods. Only the **vocabulary values** are runtime-defined
strings. The mitigations are the fail-closed spec loader (§4, §5) and `sq workflow lint`.

## Scope boundary

- **Project overrides** and **custom vocabulary end-to-end** (dynamic `sq <type>` commands,
  custom prefixes, custom badges, folder creation) build on this foundation and are decided
  elsewhere (ADR-696, ADR-263, ADR-266, ADR-323).
- **Migrations stay pinned to historical vocabulary** — identity checks inside migration runners are
  not reified; each runner is frozen against the vocabulary of its era by design.

## Consequences

- **Positive:** custom vocabulary is *readable*; the scattered identity checks are one declared
  capability table on `ItemSpec` (more honest, more testable); the workflow loader fails closed like
  the other two. "Additive over a protected core" is an enforced contract, not a convention.
- **Cost / risk:** the typing inversion is irreversible. The subtle hazards are (a) an identity check missed by the
  inventory (e.g. an implicit reliance on enum ordering or membership), and (b) validation moving
  from construction time to load time for malformed frontmatter.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:48:06Z] `manager` Catherine Manager:
  - Accepted. Verified the identity-check inventory independently (grep: 22 type/status checks, matching the ADR's line-cited set; the capability flags is_meta/subentity_kind/severity_field/parent_required/ref_rules + StatusSpec.role cover them). Two notes for the breakdown: (1) MIGRATION RUNNERS (_migrations/_vN_*.py — e.g. the ItemType.REVIEW check in _v0_1_to_v0_2.py:93) are version-frozen historical code pinned to a past schema; their enum references are OUT of scope for reification — leave them as-is. (2) Reserved-status floor = the architect's proposed structural minimum: the agent meta-type statuses (Active/Archived) + the sub-entity statuses (subtask/story + finding); work-item statuses are NOT reserved (customizable when F5/custom-statuses lands). The characterization gate stands: entire existing suite + all three golden-locks pass UNCHANGED.
- [2026-08-03T08:33:03Z] `architect` Robert Architect:
  - Amended in place; nothing retired. The de-typing itself is verified in force (`Item.type`/`Item.status` and `SubEntity.status` all `str`, vocabulary validated at the load boundary against the active spec, fail-closed with the offending id). What moved is section 2s capability table and section 3s prediction about the enums — and every case moved in the same direction, a boolean widening into a declared axis.
  - The three capability narrowings, marked at the table and detailed in the amendment note: `is_meta` to the closed `category` axis (ADR-541) — the two-valued flag was hiding a three-valued axis, and `records` could not exist while the flag did; `severity_field` to the generic `fields` badge-collection binding (ADR-323); `StatusSpec.terminal` removed with terminality derived from the declared role (ADR-696). Worth recording rather than just correcting: this decisions own recommendation of "a role name not a column" is what won, and it then absorbed the `terminal` flag it was proposed alongside.
  - Section 3 marked withdrawn by ADR-322, which names this decision. "We do not delete the enums" was true of its own scope and false as a durable ruling; of the three durable jobs it claimed for the enums, two moved into the spec and the third survives only as the named roster constants. Section 4s reserved core narrowed twice on the type axis and vanished on the status axis — its shape (additive over a protected core, fail-closed in the loader) is what survived, and only the core shrank.
  - Section 5 is closed rather than stale: `extra="forbid"` is on the workflow spec models and the loader routes through `model_validate`. The migration carve-out in the tables last row is still correct and still honoured. Added `related` edges to ADR-322, ADR-541, ADR-323 and ADR-696 — this decision was the one all four narrowed, and none linked back.
- [2026-10-25T21:36:58Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; the de-typing decision is unchanged. Folded in ADR-322 (no enums), ADR-541 (`category`), ADR-323 (`fields`) and ADR-696 (status roles, no reserved statuses). The capability table uses current names. Removed the dated notes.
- [2026-10-27T21:05:26Z] `architect` Robert Architect:
  - Removed the test-suite clauses (op-pierre ruling 2026-10-27, FEAT-1096); the decision is unchanged.
<!-- sq:discussion:end -->
