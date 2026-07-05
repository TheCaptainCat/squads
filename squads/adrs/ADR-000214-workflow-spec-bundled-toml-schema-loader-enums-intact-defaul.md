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
created_at: '2026-06-25T14:18:42Z'
updated_at: '2026-06-26T09:27:27Z'
---
<!-- sq:body -->
## Context

Today the workflow vocabulary is hardcoded across `_workflow.py` (`Workflow`, `WORKFLOWS`,
`TERMINAL`, `ALLOWED_PARENTS`, `parent_hint`, `SUBENTITY_WORKFLOWS`) and `_models/_enums.py`
(`ItemType` with prefix/folder, `Status`, `TYPE_ALIASES`, the `*_EMOJI` badge maps). There is no
single "what the workflow is" artifact — knowledge is implicit in enum declarations and dict
literals.

`FEAT-000207` (F1) creates that artifact: a single loaded, validated `WorkflowSpec`, built from a
bundled-default TOML, that the code consumes instead of the scattered literals. F1 is the
**de-risking foundation** for `EPIC-000206` — it is **behavior-preserving and produces no
user-visible change**. This ADR is the design contract F2–F6 build on.

**Critical framing — F1 is NOT the de-typing.** The `ItemType`/`Status` enums **remain the typed
backbone**. The bundled spec is loaded and **validated against the enums**; the loader reproduces
today's `WORKFLOWS`/`TERMINAL`/`ALLOWED_PARENTS` exactly. No model field is widened to `str`, no
custom vocabulary, no project overrides. Those are F2/F3/F4 and explicitly out of scope (see Scope
Boundary).

This ADR is grounded in the architecture study (Robert Architect, 2026-06-25).

## Decision

### 1. The `WorkflowSpec` shape (loaded, validated value object)

A tree of pyright-strict pydantic v2 models. **In F1 the enum-typed fields stay enum-typed** — the
spec is parsed from TOML *string* values and immediately coerced/validated into the existing enums
(`ItemType(...)` / `Status(...)`), so an unknown name raises at load. This is the deliberate
enums-intact constraint: the spec is a *reorganization* of the literals into one object, not a
de-typing.

```
WorkflowSpec
    types:    dict[ItemType, TypeSpec]        # one entry per ItemType
    statuses: dict[Status, StatusSpec]        # one entry per Status the spec uses
    machines: dict[str, StateMachine]         # named machines, referenced by TypeSpec.machine
    subentity_machines: dict[str, StateMachine]  # keyed by sub-entity kind (subtask/story/finding)
    # derived reverse indexes built at load (not stored in TOML):
    #   prefix_to_type, alias_to_type

TypeSpec
    prefix:   str                 # e.g. "FEAT"  (today's PREFIX_BY_TYPE)
    folder:   str                 # e.g. "features" (today's FOLDER_BY_TYPE)
    machine:  str                 # name into WorkflowSpec.machines (e.g. "work", "adr", "review")
    parents:  list[ItemType]      # today's ALLOWED_PARENTS; empty list = unconstrained
    aliases:  list[str] = []      # today's TYPE_ALIASES
    # NOTE: capability flags (is_meta, subentity_kind, ref_rules) are F2 — NOT in F1.

StatusSpec
    terminal: bool                # membership in today's TERMINAL frozenset
    badge:    str | None = None   # today's STATUS_EMOJI (only the 9 sub-entity statuses have one)

StateMachine
    initial:     Status
    transitions: dict[Status, list[Status]]   # today's Workflow.transitions
    # .states is derived (initial ∪ all sources ∪ all targets), mirroring Workflow.states today
```

This covers **everything** in `_workflow.py` + `_enums.py` that defines the workflow: the seven
distinct machines (work / adr / review / bug / guide / agent + the two sub-entity machines
subentity / finding), the terminal set, parent rules, prefixes, folders, aliases, and status
badges. Priority/severity badges (`PRIORITY_EMOJI`/`SEVERITY_EMOJI`) are **not** workflow vocabulary
and stay where they are (out of the spec) for F1.

### 2. Bundled config location & TOML schema

The default `workflow.toml` ships as **package data inside the package tree**, mirroring how
templates ship. Templates work today purely because `[tool.hatch.build.targets.wheel] packages =
["src/squads"]` sweeps every non-`.py` file under the package — no per-file include needed. Place
the file at:

> **`src/squads/_workflow/default_workflow.toml`** — promoting today's `_workflow.py` module into a
> `_workflow/` package (`__init__.py` re-exporting the same public names so import sites are
> unchanged), with the TOML beside the loader. It ships in the wheel automatically (verify in the
> build test, consistent with the templates-are-package-data invariant).

Representative schema sketch (the default — reproduces today byte-for-byte):

```toml
# --- named state machines -------------------------------------------------
[machines.work]
initial = "Draft"
transitions.Draft      = ["Ready", "InProgress", "Cancelled"]
transitions.Ready      = ["InProgress", "Blocked", "Cancelled"]
transitions.InProgress = ["InReview", "Blocked", "Done", "Cancelled"]
transitions.InReview   = ["InProgress", "Done", "Blocked", "Cancelled"]
transitions.Blocked    = ["Ready", "InProgress", "Cancelled"]
transitions.Done       = ["InProgress"]
transitions.Cancelled  = ["Draft"]

[machines.adr]
initial = "Proposed"
transitions.Proposed   = ["Accepted", "Rejected"]
transitions.Accepted   = ["Superseded", "Deprecated"]
transitions.Rejected   = ["Proposed"]
# (review / bug / guide / agent machines follow the same shape)

# --- sub-entity machines (keyed by kind) ----------------------------------
[subentity_machines.subtask]
initial = "Todo"
transitions.Todo = ["InProgress", "Blocked", "Cancelled"]
# … (story reuses the subtask machine; finding has its own)

# --- statuses (terminal flag + optional badge) ----------------------------
[statuses.Done]       terminal = true
[statuses.InProgress] terminal = false
badge = "🟡"
[statuses.Todo]       terminal = false
badge = "⚪"
# … all 23 statuses; terminal flag mirrors today's TERMINAL frozenset exactly

# --- types ----------------------------------------------------------------
[types.epic]
prefix = "EPIC"
folder = "epics"
machine = "work"
parents = []

[types.feature]
prefix = "FEAT"
folder = "features"
machine = "work"
parents = ["epic"]
aliases = ["feat", "f"]

[types.task]
prefix = "TASK"
folder = "tasks"
machine = "work"
parents = ["feature"]
aliases = ["t"]

[types.decision]
prefix = "ADR"
folder = "adrs"
machine = "adr"
parents = []
aliases = ["dec", "d"]
# … bug / review / guide / role / skill / operator
```

### 3. Loader design — how `_workflow.py` / `_enums.py` consume the spec

- A `load_workflow_spec() -> WorkflowSpec` reads the bundled TOML via `importlib.resources` (the
  same offline, no-filesystem-assumption mechanism appropriate for package data), parses with the
  stdlib `tomllib`, coerces every type/status string into its enum, and runs validation (§5). A
  corrupt/invalid bundled spec raises `SquadsError` — fail closed.
- **The enums remain the source of names.** Validation asserts the spec is a faithful, *complete*
  expression of the enums: every `ItemType` has exactly one `TypeSpec`; every `Status` the machines
  use exists in `Status`; every prefix/folder/alias matches what the enum properties return today.
  The spec does not *introduce* names — it *organizes* the names the enums already define.
- The existing free functions become the public surface backed by the loaded spec, preserving call
  sites: `workflow_for(t)`, `initial_status(t)`, `can_transition(t, src, dst)`, `is_open(s)`,
  `parent_allowed(c, p)`, `parent_hint(c)`, and the `TERMINAL` set become **thin shims that read the
  loaded default spec** (a module-level singleton built once via `load_workflow_spec()`). Equivalent
  methods exist on `WorkflowSpec` (`spec.can_transition(...)`) for surfaces that will later receive
  the spec explicitly (F3+ threads a per-`Service` instance); in F1 the singleton keeps the
  free-function interface identical so nothing breaks wholesale.
- `parent_hint`'s today-hardcoded `if child is ItemType.TASK` branch **stays as-is in F1** (it is a
  message-text special-case, not part of the spec). Reifying it is F2's job; F1 must not change
  behavior, so it is left untouched and noted as a known F2 follow-up.

### 4. The golden-lock contract (the safety net)

A **frozen-snapshot test** asserts the loaded default `WorkflowSpec` reproduces today's exact
behavior:
- the set of `ItemType`s and, per type, its prefix / folder / aliases / parent set;
- every named machine's `initial` and full `transitions` map (so every legal/illegal transition is
  identical);
- the `TERMINAL` set (status-by-status);
- the sub-entity machines per kind;
- status badges.

Concretely: build the snapshot directly from today's `WORKFLOWS`/`TERMINAL`/`ALLOWED_PARENTS`/
`PREFIX_BY_TYPE`/`FOLDER_BY_TYPE`/`TYPE_ALIASES`/`STATUS_EMOJI` and assert structural equality with
the loaded spec. **This test is the regression gate for the entire epic** — if any later feature
accidentally shifts the default workflow, the golden fails. It is what lets F2+ proceed with
confidence that the externalization was behavior-preserving.

### 5. Validation at load (and where it lives)

`WorkflowSpec.validate()` runs inside `load_workflow_spec()` (fail-closed; raises `SquadsError`):
1. Every `machine.initial` is a declared status.
2. Every transition source and target status exists in the status set (and in the `Status` enum).
3. `terminal ⊆ statuses`.
4. **Reachability:** every state in a machine is reachable from `initial` (warn on islands; today's
   machines are all reachable, so this is green from day one).
5. Every `TypeSpec.machine` names a declared machine; every `TypeSpec.parents` entry is a declared
   type; prefix / folder / alias are unique across types (true today).
6. **Enums-intact check (F1-specific):** the spec's type set equals `set(ItemType)` and every status
   used equals its enum member — the spec may not omit or invent a name relative to the enums.

For F1 this validation runs only against the **bundled default** (there is no project override yet).
The friendlier author-facing `sq workflow lint` surface is **F3** — not built here.

## Scope boundary (what F1 does NOT do — so this ADR isn't over-read)

- **No model de-typing / no `str` widening.** `Item.type: ItemType` and `Item.status: Status` are
  unchanged. Widening to `str` and reifying the ~20 `is ItemType.X` checks as `TypeSpec` capability
  flags is **F2 / FEAT-208**.
- **No project overrides.** The spec is bundled-only; layering a project override via the
  `_overrides/` machinery + `sq override` + `sq workflow lint` is **F3**.
- **No custom types / statuses.** The spec must equal the enums (validation rule 6). Dynamic CLI app
  build, custom prefixes/folders, thin auto-generated skills are **F4**.
- **No custom sub-entity kinds, no vocabulary renames** — **F6** (possibly its own epic).
- **No renderer change.** `sq workflow` still renders the static `workflow.md.j2` in F1; making it
  spec-derived is F4.

## Relationship to ADR-179 (FEAT-176 prefix/folder layout)

No conflict. ADR-179 decides two `.squads.toml` knobs — a **global ID prefix** (replaces the
per-type ID prefix for all types) and a separate **flat-layout** knob (drops per-type subfolders) —
both plugging into a shared `ItemStore` locator seam. This ADR is the *upstream definition* of where
the per-type prefix and folder **come from**: in F1 they move out of `PREFIX_BY_TYPE`/
`FOLDER_BY_TYPE` literals and into `TypeSpec.prefix` / `TypeSpec.folder` in the spec. ADR-179's
global-prefix and flat-layout knobs **layer on top of this later** — they transform the
spec-provided per-type prefix/folder at the storage seam (global prefix overrides the per-type
prefix string; flat layout overrides the folder), rather than reading the enum maps directly. The
two efforts are orthogonal axes (vocabulary definition vs. storage layout) and compose: whichever
lands first, the other adapts to read `TypeSpec` instead of the enum map. This ADR does not decide
the storage seam; it only relocates the source of truth for prefix/folder into the spec.

## Consequences

- **Positive:** one auditable artifact for "what the workflow is"; the golden lock makes every
  subsequent epic feature safe; the free-function shims mean F1 lands with zero call-site churn; the
  enums-intact constraint keeps pyright-strict guarantees fully in force for F1.
- **Cost:** a TOML round-trip and a singleton load on first workflow query (negligible; cached).
  Promoting `_workflow.py` to a `_workflow/` package touches imports (mechanical, re-exported).
- **Risk:** low for F1 by design — it is behavior-preserving and golden-locked. The real risk lives
  in F2 (de-typing), which the EPIC-206 spike gate validates *together with* F1 before either is
  committed to implementation.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:27:27Z] Catherine Manager:
  - Follow-up (non-blocking, from REV-230): the WorkflowSpec models lack extra='forbid', so unknown TOML keys are silently ignored rather than failing closed. Acceptable for the bundled default (golden-locked, enums-intact), but must be added before the workflow TOML becomes user-editable (FEAT-209/210). Tracked on FEAT-209.
<!-- sq:discussion:end -->
