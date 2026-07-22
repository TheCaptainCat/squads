---
id: FEAT-567
sequence_id: 567
type: feature
title: Category axis + pluggable-validator dispatch engine
status: InReview
parent: EPIC-538
author: product-owner
priority: high
refs:
- EPIC-540
- ADR-541
subentities:
- local_id: US1
  title: category axis on ItemSpec, replacing is_meta
  status: Todo
- local_id: US2
  title: validator dispatch engine (report + abort modes)
  status: Todo
created_at: '2026-07-22T08:37:44Z'
updated_at: '2026-07-22T10:25:31Z'
---
<!-- sq:body -->
## Capability

The one joint foundation both EPIC-538 and EPIC-540 build on: replace `ItemSpec.is_meta`
with a `category` axis (`roster` / `work` / `records`, hard-coded closed catalog per
ADR-541), and stand up the pluggable-validator dispatch engine that a type's `category`
selects into. Both share one data model — a type's `category` names its behavioural
bundle, and that same bundle is what the validator engine dispatches on. This feature
lands the axis + the engine only; **no enforcement is wired yet** (no `no_parent` on
records, no consumer-site rewiring) — that is Phase B (EPIC-540 catalog + assignment)
and Phase C (EPIC-538 fan-out), both of which depend on this landing first.

## Why

Per ADR-541 (Accepted): `is_meta` conflates "roster vs not" with "burn-down work vs
not", and the current validator set is ~10 hardcoded `_check_*` methods with no
per-type composability. Both problems are fixed by the same underlying move — give
each type a `category`, and let category (+ per-type additions) select which
validators run. Cutting them as one feature keeps the shared data model from forking
into two designs that have to be reconciled later.

## Scope

- `ItemSpec.category: Literal["roster", "work", "records"]` replacing `is_meta: bool`.
  Closed catalog, hard-coded in squads, not on the override surface (ADR-541 Axis A).
  Settled assignments: roster = role/skill/operator (locked, no override may touch
  a roster-category type at all); work = epic/feature/task/bug/review; records =
  decision/contract/guide.
- Plane-1 (load-time) validation: category-catalog membership, roster-locked check
  (no add/deactivate/field-merge/rename touching a `category = roster` type), and
  well-formedness of any category reassignment among `work`/`records` (never into or
  out of `roster`). Fails closed via `SquadsError`, per `load_workflow_spec`.
- The validator **dispatch engine**: one engine, two call sites (report mode for
  `sq check`, abort-on-first-violation mode for create/update) per ADR-541 Axis B.
  Engine takes an item + its type's effective validator set and runs them AND-composed.
  This feature does **not** populate the catalog (Phase B) or point any category's
  bundle at real validators yet — the engine exists and is wired to run an (initially
  empty or stub) per-type validator list, proving the dispatch shape works end to end.
- Rides the `RequestContext` seam FEAT-533 just landed: the active spec (carrying each
  type's `category`) is a per-request value, not a module singleton — this feature adds
  the `category` field onto that per-request spec object, it does not reintroduce a
  global.

## Acceptance

- `ItemSpec.category` exists, is populated for all built-in types per ADR-541's
  settled assignments, and `is_meta` is gone (or a deprecated pure-derived shim, if the
  architect judges a transitional read-compat shim is warranted — see open question).
- A spec with a `category` naming something outside the closed catalog fails to load
  (`SquadsError`), and any override attempting to add/deactivate/field-merge/rename a
  `category = roster` type is refused clean, both at Plane 1 (load).
- The validator engine runs in both report mode and abort mode over a stub/empty
  validator set with no behaviour change to `sq check` output yet (Phase B wires real
  validators — this phase must not regress today's hardcoded `_check_*` results).
- `uv run pytest` green, `sq check` clean, byte-identical `sq check` output vs. today
  (this phase adds no new enforcement).

## Dependencies / ordering

- **Phase A of a A→B→C sequence** (tech-lead's cut): B (EPIC-540 catalog + `.overrides`
  assignment surface) and C (EPIC-538's fan-out: custom types, UI surfacing, CLI
  surfacing, ADR migration, consumer audit) both depend on this landing first. B and C
  do not depend on each other and can run in parallel once A is Done.
- Built against ADR-541 (Accepted) — the category taxonomy and validator-model
  contract are pinned there; this feature does not reopen those questions.
- Rides FEAT-533 (InReview) — the per-request `RequestContext`/active-spec seam.

## Open question — flag @architect

ADR-541 pins the *taxonomy and behavioural contract* but this feature is the first
place the category axis and the validator-engine *code* actually meet — the technical
boundary between "type declares a category" (a spec/model concern) and "engine
dispatches validators by category" (a services-layer concern) isn't fully specified.
Concretely: does the engine live in `_models/` (next to `ItemSpec`) or in `_services/`
(next to `_maintenance.py`'s current `_check_*` methods), and does `ItemSpec` carry a
resolved validator list or just the bare `category` name with resolution happening at
call time in the service layer? This is an architecture call, not a product one —
@architect please pin the module boundary before implementation starts.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 567 add-story "As a <role>, I want … so that …"`; track with `sq feature 567 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | category axis on ItemSpec, replacing is_meta |
| US2 | Todo |  | validator dispatch engine (report + abort modes) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — category axis on ItemSpec, replacing is_meta

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Add ItemSpec.category (roster/work/records), settled assignments per ADR-541, drop is_meta, Plane-1 load validation (catalog membership, roster-locked, reassignment well-formedness).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — validator dispatch engine (report + abort modes)

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
One engine over a per-type validator set, run in sq check report mode and create/update abort mode; no catalog population yet (Phase B), no behaviour change to today's sq check output.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T09:21:39Z] Robert Architect:
  - [architect design pin — 2026-07-22] Pinning the module boundary FEAT-567's body flagged @architect, so the tech-lead can cut US1/US2. Three calls below, then the schema/migration verdict. ADR-541's taxonomy + validator model are NOT reopened — these are the code-boundary calls it delegates.
  - D1 — Engine placement: the validator DISPATCH ENGINE lives in _services/ (new _services/_validators.py), NOT _models/. Rationale: it reads live item + index state (parent lookups, incoming-supersedes edges, registered-slug set, on-disk body text) — exactly what _maintenance.py's _check_* methods hold today via self.store/self.paths/self.spec. _models must stay pure-pydantic with no internal deps (project invariant: acyclic graph, _models depends on nothing internal); putting the engine there would invert the layering. _workflow/_models.py stays pure value objects and owns ONLY the category field + the Plane-1 load-time spec-validity checks (category-catalog membership, roster-locked, reassignment well-formedness, empty parent_in) inside WorkflowSpec._validate / the loader — that is US1, pure declarative validation with no item state.
  - D1 shape: _services/_validators.py holds (a) a Validator protocol taking a ValidatorContext(item, spec, precomputed squad-global inputs) and yielding CheckIssue; (b) the closed catalog as a module-level dict[str, Validator] — a CODE/definition constant (immutable, shared), not request-scoped mutable global, so it's fine under the _context.py CODE-vs-REQUEST split; (c) an engine exposing report(index, on_disk)->list[CheckIssue] and gate(item, index)->None-or-raise. MaintenanceMixin.check() becomes a thin caller in report mode; create/update gating calls gate() in abort mode. Phase A wires the engine but runs an empty/stub per-type set (no-op) while today's _check_* still produce output verbatim — the byte-identical guarantee. Phase B (EPIC-540) lifts the _check_* into named catalog validators.
  - D2 — ItemSpec carries bare category, NOT a pre-resolved validator list. ItemSpec.category: Literal['roster','work','records'] (with the Literal itself giving free catalog-membership rejection at construction). The effective per-item set (common core + category default bundle + type 'validators' additions) is resolved AT CALL TIME by the engine in _services. Rationale: (1) declarative-spec cleanliness — the category→bundle mapping is behaviour, and behaviour lives in code (ADR-541's standing boundary); baking resolved validators onto the value object duplicates the catalog's authority and invites the axis-drift ADR-541 explicitly guards against. (2) layering — resolution references the catalog in _services; a resolved list on ItemSpec would force _models→_services (cycle). (3) caching is premature — bundles are tiny and the spec is a per-request immutable (FEAT-533); if ever hot, memoize on the engine keyed by (category, tuple(validators)), never on the spec.
  - D3 — Two validator classes, one engine. Per-item validators: engine iterates index.items, resolves each item's effective set, runs AND-composed; squad-global INPUTS (registered slugs, incoming-supersedes map, on_disk body map) are computed once and passed in, mirroring how _check_items/_check_decisions precompute today. Squad-global validators (index_reconciled=_check_reconciliation, backend_reconciled=_check_backends): a separate small registry the engine runs ONCE per invocation, not selectable by category, not removable. Report/abort split: report() collects both classes (squad-global run in report only — never a create/update gate); gate() runs only the one item's per-item set and stops at first violation. Same split as the existing workflow-lint report-vs-abort.
  - US1 impl note for tech-lead: drop the is_meta FIELD but KEEP the accessors item_is_meta() and work_types() as category-derived shims (item_is_meta := category=='roster'; work_types := category != roster, i.e. work+records, preserving today's 'not is_meta' set). The ~15 consumer sites compile and behave identically; their precise per-site reclassification (roster-vs-not vs burn-down-vs-not) is Phase C / EPIC-538, NOT this feature. This is what keeps FEAT-567 no-enforcement / byte-identical.
- [2026-07-22T09:21:57Z] Robert Architect:
  - [architect — schema/migration surface for the operator] Verdict on the three points the manager must brief before anything lands:
  - (c) FRONTMATTER SCHEMA BUMP — NO. is_meta is a type-level property of the item-type SPEC, resolved from the workflow spec at runtime. Grep-confirmed: it appears only in ItemSpec, default_workflow.toml, Jinja templates, and code consumers — NEVER in item .md frontmatter, NEVER in .squads.json, NEVER in .squads.toml. Nothing in item data derives from it. SCHEMA_VERSION governs the frontmatter/index shape only; the workflow-spec format is versioned on a separate axis (the squads:override-base:<ver> stamp). So is_meta→category is purely a spec-format change: no SCHEMA_VERSION bump, no sq migrate data migration, no runner in _migrations/.
  - (a) BUNDLED TOML — regenerated, fine. The is_meta=… lines in default_workflow.toml become category='roster|work|records' per ADR-541's settled assignments. Give ItemSpec.category a default of 'work' so types that omit it (and the common case) load unchanged. No adopter impact from the bundled file itself.
  - (b) ADOPTER OVERRIDE COMPAT — YES, but narrow, and handled with a read-compat shim (not a version bump). Overrides are additive-only today, so is_meta can only appear on a CUSTOM type an adopter added; is_meta=false is the default so writing it is redundant, and is_meta=true on a custom type was never really supported (roster is closed/locked). With ItemSpec extra='forbid', a lingering is_meta key would become a hard SquadsError on load after the rename. Approach: a transitional read-compat shim in the loader's item parser (_parse_item_spec_str + the bundled item loop) — POP a legacy is_meta before model_validate (keeps extra='forbid' intact); false/absent → let category fall to its 'work' default; true on a non-roster type → clean SquadsError pointing at category + the roster-locked rule. Document the deprecation in the release CHANGELOG/upgrade notes; plan to drop the shim at 1.0. Note there is NO stamped bundled-workflow copy in adopter repos (workflow overrides carry only deltas, unlike templates with their hash manifest), so there is no drift-manifest angle to migrate.
  - ADR-541 amendment? The three design calls (D1-D3) and points (a)/(c) need NO amendment — they're the code-boundary calls ADR-541 delegates and are recorded here at feature level. The ONE durable-contract item ADR-541 does not pin is the adopter BACK-COMPAT POLICY for the deprecated is_meta key — i.e. that we ship a deprecation shim rather than hard-break, and drop it at 1.0. If the operator wants that policy on the durable record, I recommend a one-paragraph ADR-541 amendment stating it. Proposing only — I will not author the amendment without Pierre's go. Everything else stays feature-level. FEAT-567 stays Draft.
<!-- sq:discussion:end -->
