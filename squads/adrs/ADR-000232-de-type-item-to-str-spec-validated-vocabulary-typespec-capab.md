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
created_at: '2026-06-26T09:45:13Z'
updated_at: '2026-06-26T09:48:06Z'
---
<!-- sq:body -->
## Context

`FEAT-000207` / `ADR-000214` externalized the workflow into a loaded `WorkflowSpec` but kept the
`ItemType` / `Status` enums as the **typed field backbone**, with a blunt `spec == enums` validation
(the enums-intact constraint). That constraint is exactly what keeps the vocabulary closed:
`Item.type: ItemType` means frontmatter with an unknown `type`/`status` raises at model
construction, so custom vocabulary literally cannot be read.

`FEAT-000208` (F2) is the **L1→L2 inflection** that relaxes that constraint. It is the highest-risk
feature in `EPIC-000206`: the pyright/typing inversion is irreversible and pervasive. Pierre opted
to go straight in with **no throwaway spike**, so this ADR makes the characterization suite + the
three golden locks the standing guard (§6). This is the study's **Option C** (recommended): a typed
*engine* over a runtime-defined *vocabulary*.

Scope is de-typing + capability-flag reification + reserved-vocab core + the fail-closed hardening
gap — and nothing downstream (no overrides F3, no custom-type/status end-to-end F4/F5, no
renderer/CLI-app changes).

## Decision

### 1. Widen the model fields to `str`, validate at the service boundary

- `Item.type: ItemType` → `Item.type: str`; `Item.status: Status` → `Item.status: str`;
  `SubEntity.status: Status` → `str` (and any sub-entity severity stays as-is — `Severity` is not
  workflow vocabulary and is **not** widened).
- `from_frontmatter` stops calling `ItemType(...)` / `Status(...)` (which raise on unknown). The
  string round-trips losslessly — **every existing item file is already a valid string**, so this is
  a typing/validation change, **not a data migration**. Existing squads read unchanged; no file
  rewrite, no schema-data change. (A schema-version bump still marks the capability boundary, since
  an older `sq` must refuse a squad that *uses* custom vocab — but the default-vocab on-disk bytes
  are identical.)
- Validation **moves from Pydantic field construction to the service boundary**: `ItemStore.load` /
  `open_service` checks each item's `type`/`status` against the loaded `WorkflowSpec`
  (`spec.is_known_type(t)`, `spec.is_valid_status(t, s)`), raising `SquadsError` with the offending
  item id on an unknown value. Pydantic still type-checks "is a str"; the *vocabulary* check is the
  spec's job. (Rationale, from the study: a Pydantic validator can't see the loaded spec without
  threading external state through construction — the service boundary is the natural seam.)

### 2. Reify every hardcoded identity check as a declared `TypeSpec` capability

I grepped the codebase (`is ItemType.` / `is not ItemType.` / `in (ItemType…)` / `in WORK_TYPES` /
`is Status.`). Every behavioral identity check below becomes a declared capability on `TypeSpec`
(or `StatusSpec`); **no behavioral type-identity `is` check is left hardcoded in the engine.**

New `TypeSpec` capability fields (additive to ADR-214's `prefix`/`folder`/`machine`/`parents`/
`aliases`):

```
TypeSpec (additions)
    is_meta:        bool = False    # role/skill/operator: outside WORK_TYPES, no work lifecycle,
                                    #   slug-keyed identity, retype-ineligible
    subentity_kind: str | None = None   # "story" | "subtask" | "finding" | None — the kind a
                                    #   type's children are (drives _SUBENTITY maps + add-<kind>)
    severity_field: bool = False    # type surfaces a severity badge (today: bug)
    parent_required: ItemType-name | None  # the parent type rule expressed declaratively
    ref_rules:      list[RefRule] = []  # e.g. task → fixes|addresses hint; decision → supersedes
```

Mapping of each found check → capability (the complete inventory):

| Identity check (file:line) | Today | Reified as |
|---|---|---|
| `_service.py:152`, `_base.py:200-204,454,460,508-535`, `_items.py:180-183`, `_maintenance.py:284,613,652`, `_agents_md:143`, `_claude_code:275` — `is ItemType.ROLE/SKILL/OPERATOR` | meta-type branches (slug-keyed lookup, skill-prefix file rule, roster filtering, author-is-self) | **`is_meta`** (+ `subentity_kind is None`); the slug-keyed lookup table keys on `spec.meta_types()` |
| `_items.py:85,237`, `_retype.py:35-43`, `__init__.py:111` — `in WORK_TYPES` | which types get a `sq <type>` app + are retype-eligible | **`not is_meta`** → `spec.work_types()` derived (replaces the `WORK_TYPES` tuple) |
| `_subentities.py:455` (`is not ItemType.FEATURE`), `_items.py:45` + `_common.py:334` `_SUBENTITY` maps | parent→sub-entity-kind | **`subentity_kind`** (feature→story, task→subtask, review→finding) |
| `_maintenance.py:694` (`is not ItemType.TASK`), `:700` (`is not ItemType.FEATURE`) — task→feature parent + fix/addresses rules | task spine | **`parent_required`** + **`ref_rules`** |
| `_workflow/__init__.py:108` — `if child is ItemType.TASK` in `parent_hint` | task-specific hint text (`link a bug/review via ref add … --kind fixes\|addresses`) | **`ref_rules`** drive the hint string (the `parent_hint` text becomes spec-derived) |
| `_maintenance.py:752` (`is not ItemType.DECISION`) + `:754` (`status is Status.SUPERSEDED`) | ADR supersede warning | **`ref_rules`** (a `supersedes` rule) keyed off a **`StatusSpec` role** (see below) |
| `_common.py:142` (`is ItemType.BUG`) — show severity row | bug severity surfacing | **`severity_field`** |
| `_v0_1_to_v0_2.py:93` (`is ItemType.REVIEW`) | migration scaffolding | **frozen — migrations are pinned to historical vocab; not reified** (see §6) |

`StatusSpec` gains the structural-role markers the engine needs without `is Status.X`:
`terminal: bool` (already, ADR-214), plus the small set of **semantic status roles** the code keys
on — at minimum a way to identify `Superseded` for the ADR rule. Recommend a single optional
`role: str | None` (e.g. `"superseded"`) rather than a flag-per-status, so future rules add a role
name not a column. The retype `_carry_or_reset_status` logic stays structural (it compares whole
machines via `workflow_for(...).states`, no status `is` check) and needs no change.

### 3. The enums' new role: canonical reserved built-in vocabulary

`ItemType` and `Status` **stop being the field types** but are **retained as the canonical source of
the reserved built-in vocabulary** — `RESERVED_TYPES = frozenset(ItemType)` and the structural
subset of `RESERVED_STATUSES` (see §4). Decided explicitly: we do **not** delete the enums in F2.
They serve three durable jobs: (a) generate ADR-214's bundled default TOML (the golden source); (b)
define the reserved sets the loader fails-closed against (§4); (c) give internal code readable
string constants (`ItemType.TASK.value`) instead of bare `"task"` literals during the transition.
What they lose: being the *runtime field type* and conferring compile-time exhaustiveness.

### 4. Reserved-vocabulary invariant — replaces FEAT-207's `== enums` check

With `spec == enums` relaxed (a spec may now be a **superset**), the loader's old equality check is
replaced by a **subset/coverage check that fails closed**:

> `WorkflowSpec.validate()` MUST raise `SquadsError` if the spec **omits any reserved type or
> reserved status**. Custom vocabulary is **additive over the reserved core**; it can extend, never
> remove.

- **Reserved types:** all of `ItemType` — crucially the meta-types `role`/`skill`/`operator` (the
  engine's slug-keyed machinery depends on them existing) plus the seven work types.
- **Reserved statuses:** the **structural statuses the agent and sub-entity lifecycles require** —
  the agent machine's `Draft/Active/Archived`, the sub-entity machines' `Todo/InProgress/Blocked/
  Done/Cancelled`, and the finding machine's `Open/Fixed/Verified/WontFix`. (Work/ADR/review/guide
  statuses are part of the bundled default but the *hard-reserved* floor is the structural set the
  code cannot function without.) Pin the exact reserved-status set in the ADR-accept review.
- **Location:** this lives in `WorkflowSpec.validate()` (run inside the loader, fail-closed), and it
  **supersedes** the FEAT-207 blunt-equality assertion. The F1 golden (default == today) still holds
  because the default spec trivially satisfies a subset check.

### 5. Fold in the fail-closed gap (FEAT-209 / ADR-214 follow-up): `extra="forbid"`

The workflow spec models today silently **ignore unknown TOML keys** (no `extra="forbid"`), unlike
the now-hardened roles/playbook loaders, and the workflow loader does not route through
`model_validate`. **Recommend folding this into F2, not deferring to F3/209:** F2 is already
rewriting `WorkflowSpec` (adding the capability fields) and tightening its validation (§4), so
adding `model_config = {"extra": "forbid"}` to every workflow spec model and routing the loader
through `model_validate(...)` is cohesive here and avoids shipping a known fail-open loader through
another release. It is a small, contained hardening that belongs with the validation overhaul. (If
the team prefers to keep F2 minimal, it can move to FEAT-209 — but the recommendation is to fix it
here, since F2 touches these exact models.)

### 6. Characterization gate (the standing guard, in lieu of the spike)

Because there is no throwaway spike, the regression guard is explicit and mandatory:

- **The entire existing test suite + all three golden locks (workflow ADR-214, role-catalog
  ADR-221, playbook ADR-226 incl. its byte-identical skill-output layer) MUST pass UNCHANGED** —
  byte-identical behavior. No existing test may be edited to accommodate F2; if one needs editing,
  that is a behavioral change and must be justified, not absorbed.
- **Characterization-first** (per the FEAT-208 manager note): before reifying, add characterization
  tests that pin the *current* behavior of each identity check (e.g. "a `decision` with no incoming
  `supersedes` and status `Superseded` warns in `sq check`"; "a `skill` file not prefixed `SKILL-`
  is flagged"), so the reification is proven equivalent rather than assumed.
- **New surface gets new tests:** each `TypeSpec` capability flag and the reserved-vocab
  fail-closed validation get direct unit tests (including the negative: a spec missing
  `role`/`skill`/`operator` or a structural status must raise).
- `uv run pyright && ruff check . && ruff format --check . && pytest` all green.

### 7. The pyright-strict trade-off, on the record

Widening to `str` trades **compile-time enum exhaustiveness** for **load-time spec validation**.
What we lose: pyright can no longer prove a `match item.type` / status handling is exhaustive; a
typo in a type/status string is a runtime (load-time) error, not a type error; autocomplete on
`ItemType.X` at field sites goes away. What we keep: the **engine stays fully typed** — `WorkflowSpec`,
`TypeSpec`, `StatusSpec` are pyright-strict models, the capability flags are typed booleans/enums,
and every operation on vocabulary goes through typed spec methods (`spec.type_spec(t).is_meta`).
Only the **vocabulary values** are runtime-defined strings. ruff/pyright strict mode stays green;
the mitigations are the strong fail-closed `WorkflowSpec.validate()` (§4) and, later, `sq workflow
lint` (F3).

## Scope boundary (what F2 does NOT do)

- **No project overrides** (F3/FEAT-209-area) — the spec is still bundled-only; F2 only makes the
  *models* able to carry non-enum values and the *loader* able to validate a superset.
- **No custom types/statuses end-to-end** (F4/F5) — no dynamic `sq <type>` app build, no
  custom-prefix ID parsing, no custom badges, no folder auto-create. F2 proves the *foundation*
  (str fields + reserved-core validation + capability flags); F4/F5 *consume* it.
- **No renderer/CLI change** — `sq workflow` still renders the static template; `parse_type`/
  `parse_status` switch to iterating `spec.managed_types()`/the spec's status set instead of the raw
  enums, but that is the only CLI touch and it is behavior-identical for the default vocab.
- **Migrations stay pinned to historical vocab** — `_v0_1_to_v0_2.py`'s `is ItemType.REVIEW` is not
  reified; migration runners are frozen against the vocabulary of their era by design.

## Consequences

- **Positive:** unblocks all of L2/L3 (custom vocabulary becomes *readable*); removes ~20 scattered
  `is ItemType.X` checks in favor of one declared capability table on `TypeSpec` (more honest, more
  testable); hardens the workflow loader to match the other two (`extra="forbid"`). The reserved-vocab
  invariant makes "additive over a protected core" an enforced contract, not a convention.
- **Cost / risk (stated plainly):** this is the irreversible typing inversion and the riskiest
  change in the epic, done without a spike. The mitigation is entirely the characterization gate
  (§6): byte-identical behavior under the full suite + three goldens is the only thing that proves
  the reification is faithful. The subtle hazards are (a) a missed identity check that wasn't in the
  grep (e.g. an implicit reliance on enum ordering or membership), and (b) the service-boundary
  validation changing *when* an error is raised (construction-time → load-time) for malformed
  frontmatter — the characterization tests must cover the bad-value path.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:48:06Z] Catherine Manager:
  - Accepted. Verified the identity-check inventory independently (grep: 22 type/status checks, matching the ADR's line-cited set; the capability flags is_meta/subentity_kind/severity_field/parent_required/ref_rules + StatusSpec.role cover them). Two notes for the breakdown: (1) MIGRATION RUNNERS (_migrations/_vN_*.py — e.g. the ItemType.REVIEW check in _v0_1_to_v0_2.py:93) are version-frozen historical code pinned to a past schema; their enum references are OUT of scope for reification — leave them as-is. (2) Reserved-status floor = the architect's proposed structural minimum: the agent meta-type statuses (Active/Archived) + the sub-entity statuses (subtask/story + finding); work-item statuses are NOT reserved (customizable when F5/custom-statuses lands). The characterization gate stands: entire existing suite + all three golden-locks pass UNCHANGED.
<!-- sq:discussion:end -->
