---
id: ADR-214
sequence_id: 214
type: decision
title: 'Workflow spec: bundled TOML schema + loader, enums intact, default golden-locked'
status: Accepted
author: architect
refs:
- FEAT-207:addresses
- ADR-179
- ADR-322
- ADR-696
- ADR-604
created_at: '2026-06-25T14:18:42Z'
updated_at: '2026-10-25T21:36:54Z'
---
<!-- sq:body -->
## Context

The workflow vocabulary — item types with their prefix, folder, parents and aliases; statuses; the
lifecycles that move between them; the sub-entity machines — needs one artifact that says "what the
workflow is", rather than knowledge implicit in enum declarations and dict literals scattered across
the code.

`FEAT-000207` creates that artifact: a single loaded, validated `WorkflowSpec`, built from a bundled
TOML, that the code consumes. It is the foundation of `EPIC-000206`, and it is
**behavior-preserving**: the bundled default reproduces the vocabulary the code had. Later decisions
build on it — ADR-232 and ADR-322 make the spec the sole vocabulary authority, ADR-249 threads it
rather than holding it in a global, ADR-696 adds the project override and its merge.

## Decision

### 1. The `WorkflowSpec` shape (loaded, validated value object)

A tree of pyright-strict pydantic v2 models in `_workflow/_models.py`, keyed by plain strings:

```
WorkflowSpec
    items:           dict[str, ItemSpec]            # one entry per item type
    statuses:        dict[str, StatusSpec]          # every status the lifecycles use
    lifecycles:      dict[str, Lifecycle]           # named machines, referenced by ItemSpec.lifecycle
    subentity_kinds: dict[str, SubentityKindSpec]   # story / subtask / finding … (ADR-348)
    collections, roles, ref_kinds, views, squad     # badge collections, status roles, ref kinds,
                                                    #   derived views, squad-global settings
    # derived reverse indexes built at load (not stored in TOML):
    #   prefix_to_type, alias_to_type

ItemSpec
    prefix:    str                # e.g. "FEAT"
    folder:    str                # e.g. "features"
    lifecycle: str                # name into WorkflowSpec.lifecycles
    parents:   list[str]
    aliases:   list[str] = []
    # plus the capability fields later decisions declare (category, subentity_kind,
    # parent_required, ref_rules, fields, attributes, validators, labels, order)

StatusSpec
    badge: str | None = None
    role:  str | None = None      # the declared status role the engine binds to (ADR-696)

Lifecycle
    initial:     str
    transitions: dict[str, list[str]]
    # .states is derived (initial ∪ all sources ∪ all targets)
```

The spec **organises names; it does not introduce behaviour**. Terminality and openness derive from
a status's declared role, not from a per-status flag.

### 2. Bundled config location

The default spec ships as **package data at `src/squads/_specs/workflow.toml`**, beside
`roles.toml` and `playbook.toml`. It ships in the wheel because the wheel sweeps every non-`.py` file
under the package, the same way templates ship, and the build test verifies it.

Representative schema sketch:

```toml
[lifecycles.work]
initial = "Draft"
transitions.Draft      = ["Ready", "InProgress", "Cancelled"]
transitions.Ready      = ["InProgress", "Blocked", "Cancelled"]
# …

[statuses.Done]
role = "done"
# …

[items.feature]
prefix = "FEAT"
folder = "features"
lifecycle = "work"
parents = ["epic"]
aliases = ["feat", "f"]
```

### 3. Loader design

- `load_workflow_spec()` reads the bundled TOML via `importlib.resources` (offline, no filesystem
  assumption), parses with stdlib `tomllib`, builds the models through `model_validate`, and runs
  validation (§5). Every spec model carries `extra="forbid"`, so an unknown key fails closed. A
  corrupt or invalid spec raises `SquadsError` — fail closed.
- The bundled spec is loaded once at import and is immutable; `_workflow.bundled_spec()` returns it.
- Workflow capabilities are **methods on `WorkflowSpec`** (`spec.can_transition(...)`,
  `spec.non_roster_types()`, …). Code takes the active spec — the bundled default merged with the
  project override — from `Service.spec` or the per-invocation request context (ADR-249); there is
  no process-global mutable spec.

### 4. The golden-lock contract (the safety net)

**Frozen-snapshot tests** in `tests/goldens/` assert the loaded default spec — its types and their
prefix / folder / aliases / parents, every lifecycle's `initial` and full `transitions`, the statuses
and their roles, the sub-entity kinds, collections, ref kinds and views — against a recorded
snapshot. They are the regression gate for every later change to the default: if anything shifts
the default workflow, a golden fails.

### 5. Validation at load

Validation runs inside the loader (fail-closed; raises `SquadsError`):
1. Every lifecycle's `initial` is a declared status.
2. Every transition source and target is a declared status.
3. Status-role references resolve against the declared roles.
4. **Reachability:** every state in a lifecycle is reachable from `initial`.
5. Every `ItemSpec.lifecycle` names a declared lifecycle; every `ItemSpec.parents` entry is a declared
   type; prefix, folder and alias are unique across types.

Later decisions add their own load-time floors to the same pass — a reachable settled status per
lifecycle, the roster lifecycle floor, validator-catalog membership, ref-rule targets, and
parent-cycle detection. The author-facing `sq workflow lint` reports an override's errors with fix hints.

## What this decision does not decide

- **Vocabulary authority and de-typing** — ADR-232 and ADR-322.
- **Project overrides and their merge** — ADR-696, over ADR-85's override contract.
- **How the spec reaches its consumers** — ADR-249.
- **Storage layout** — a global ID prefix or a flat folder layout would transform the spec-provided
  per-type prefix and folder at a storage seam; this decision only makes the spec the source of
  truth for prefix and folder.

## Consequences

- **Positive:** one auditable artifact for "what the workflow is"; the golden lock makes every
  subsequent change to the default safe; fail-closed validation and `extra="forbid"` mean an invalid
  or misspelt spec refuses to run rather than being half-read.
- **Cost:** a TOML round-trip and one load at import for the bundled spec (negligible).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:27:27Z] `manager` Catherine Manager:
  - Follow-up (non-blocking, from REV-230): the WorkflowSpec models lack extra='forbid', so unknown TOML keys are silently ignored rather than failing closed. Acceptable for the bundled default (golden-locked, enums-intact), but must be added before the workflow TOML becomes user-editable (FEAT-209/210). Tracked on FEAT-209.
- [2026-08-03T08:31:46Z] `architect` Robert Architect:
  - Amended in place; nothing retired. The core ruling is verified in force — one loaded, validated `WorkflowSpec` from a bundled TOML via `importlib.resources` + `tomllib`, consumed through free-function shims, fail-closed, golden-locked — and ADR-249 executed its threading half rather than replacing it. This decision is the pattern every later spec decision cites, so its stale surface misleads more readers than any other; that is why it got the heaviest note.
  - Corrected field for field in section 1, against the tree rather than the audits summary: `types:` is `items: dict[str, ItemSpec]`, `machines:` is `lifecycles: dict[str, Lifecycle]`, `TypeSpec` is `ItemSpec` (`_workflow/_models.py:330,1090-1092`), sub-entity machines resolve through `subentity_kinds: dict[str, SubentityKindSpec]`, and `StatusSpec` is `{badge, role}` at `:445-458` with no `terminal` field at all. The boolean this section introduced is the one ADR-696/604 generalised into a declared status role — worth naming as the lineage, not just a rename.
  - Section 2s path corrected to `src/squads/_specs/workflow.toml`. The `_workflow/` package promotion decided here did happen; the spec files later moved out to their own directory beside `roles.toml` and `playbook.toml`, and the package-data mechanism is untouched.
  - Two clauses marked withdrawn in place, both by ADR-322: section 3s "the enums remain the source of names" and validation rule 6. Neither is a surprise reversal — this decision named the de-typing as out of its own scope and ADR-322 is the decision that did it, so the honest record is a withdrawal with the successor named, not a supersession. Rules 1 to 5 all still run. Section 4s golden lock survives as a mechanism but its stated construction from `WORKFLOWS`/`TERMINAL`/`PREFIX_BY_TYPE`/`STATUS_EMOJI` is unbuildable, so that is marked too.
  - Closed the open follow-up recorded here in 2026-06-26: `extra="forbid"` is now on `WorkflowSpec`, `ItemSpec` and `StatusSpec`, which was the stated precondition for the spec becoming adopter-editable. Added `related` edges to ADR-322, ADR-696 and ADR-604 — none of the three linked back.
- [2026-10-25T21:36:54Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Recorded the shipped model names. The free-function shims and singleton are gone (ADR-249): capabilities are spec methods and the spec is threaded. The enums-intact clauses are gone (ADR-322). The ADR-179 section is dropped (rejected). The golden lock now points at `tests/goldens/workflow_*.json`.
<!-- sq:discussion:end -->
