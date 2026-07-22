---
id: FEAT-568
sequence_id: 568
type: feature
title: 'Validator catalog: seed checks + category/type assignment'
status: Done
parent: EPIC-540
author: product-owner
priority: medium
refs:
- FEAT-567
- ADR-541
subentities:
- local_id: US1
  title: lift seed catalog verbatim from today's _check_* methods
  status: Todo
- local_id: US2
  title: category bundles + per-type validators + the two new enforcements
  status: Todo
created_at: '2026-07-22T08:38:35Z'
updated_at: '2026-07-22T11:51:26Z'
---
<!-- sq:body -->
## Capability

Populate the closed validator catalog with today's `_check_*` methods lifted
verbatim (per ADR-541's seed list), and build the declarative `.overrides`
**assignment** surface that binds catalog validators to a type's `category`
default bundle plus its own per-type additions. This is EPIC-540's payoff: the
engine FEAT-567 stands up starts actually enforcing something.

## Scope

- **The seed catalog**, lifted 1:1 from today's hardcoded checks (no behaviour
  change except the two deliberate new enforcements below): `parent_in:<types>`,
  `no_parent`, `item_status_valid`, `subtask_story_mapping`,
  `subentity_status_valid`, `subentity_body_written`, `subentity_title_max:<n>`,
  `no_status_banner`, `dangling_ref`, `ref_kind_valid`, `agent_registered`,
  `supersedes_incoming` (per-item class) plus `backend_reconciled` /
  `index_reconciled` (squad-global class, always-on, never per-type selectable).
- **Category default bundles**, implemented as validator-list membership, not a
  parallel mechanism: `records` = common core + `no_parent` +
  `supersedes_incoming` (gated on the type declaring a `supersedes` ref rule);
  `work` = common core + parent validator (per the empty-`parents`/`no_parent`
  semantics ADR-541 pins) + sub-entity validators + `subtask_story_mapping`;
  `roster` = common core only. Common core (all categories): `item_status_valid`,
  `dangling_ref`, `ref_kind_valid`, `no_status_banner`, `agent_registered`.
- **Type-level `validators` list**: extend-only over the category floor (no
  per-validator deselect of a category default — confirmed in ADR-541). A name
  not in the closed catalog fails Plane-1 load validation.
- **The two deliberate new enforcements** ADR-541 calls out: `records`
  category-default `no_parent` (flags the 5 currently-parented ADRs until the
  EPIC-538 migration feature re-homes them — must land with-or-after that
  migration, never before, per ADR-541's sequencing note), and `epic` gaining an
  explicit `no_parent` (enforcing the previously-unenforced work-root
  constraint).
- `parent_in:<types>` requires a **non-empty** allowlist; an empty `parent_in` is
  rejected at Plane 1 load with a diagnostic pointing at `no_parent` instead
  (ADR-541).

## Acceptance

- `sq check` re-expressed entirely over the catalog; a bare `uv run sq check` on
  this repo reports the same issues as today, **except** the two new
  enforcements above (which must be sequenced with the EPIC-538 ADR-migration
  feature so this repo's own `sq check` doesn't regress — see Dependencies).
- create/update and `sq check` share one engine; no rule logic duplicated
  between the abort gate and the report.
- A `validators` entry naming a non-catalog validator fails closed at spec load.
- Category default bundle membership matches ADR-541's bundle table exactly
  (common core + per-category additions).

## Dependencies / ordering

- **Depends on FEAT-567 (Phase A)** — the category axis and the dispatch engine
  must exist before there is anything to populate or assign against.
- **Sequencing constraint with EPIC-538's ADR-migration feature (Phase C)**: the
  `records` `no_parent` default must land with-or-before that migration re-homes
  the 5 currently-parented ADRs (ADR-129/155/158/516/527) to `related` refs —
  landing this enforcement first (without the migration) would make this repo's
  own `sq check` non-clean. Coordinate the merge order with whichever dev picks
  up the migration task.
- Built against ADR-541 (Accepted), Axis B + the seed catalog table.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 568 add-story "As a <role>, I want … so that …"`; track with `sq feature 568 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | lift seed catalog verbatim from today's _check_* methods |
| US2 | Todo |  | category bundles + per-type validators + the two new enforcements |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — lift seed catalog verbatim from today's _check_* methods

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Named validators 1:1 with today's hardcoded checks, per-item + squad-global classes, byte-identical sq check output for the untouched checks.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — category bundles + per-type validators + the two new enforcements

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Wire category default bundles, type-level extend-only validators list, records/epic no_parent additions -- sequenced with the ADR-migration feature (Phase C) so this repo's sq check stays clean.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T10:33:23Z] Olivia Lead:
  - Broke FEAT-568 into TASK-581 (lift seed catalog), TASK-582 (route check+gate through engine, byte-identical), TASK-583 (validators assignment surface + Plane-1), TASK-584 (records+epic no_parent, depends-on FEAT-572). @architect: 3 points ADR-541 doesn't pin, flagged in the task bodies —
  - 1) parent_in:<types> notation vs the 'no rule re-encoded as both a typed field and a string param' principle: I read parent_in as reading the structured parents field (no duplicated param), with no_parent the separate explicit opt-in. Confirm?
  - 2) 'byte-identical' output: sq check prints issues in production order, unsorted. The per-item engine reorders vs today's per-check grouping. Is byte-identical the issue SET (+ add a deterministic sort), or must the engine reproduce today's exact order? Leaning set-equality + stable sort, but it changes on-screen order so it's your call.
  - 3) Plane-1 catalog-membership check lives in _workflow/_models.py but CATALOG lives in _services/_validators.py, and _workflow sits below _services — importing up inverts the layer. Where should the valid-name registry live so _workflow can read it without a back-edge?
- [2026-07-22T10:37:20Z] Robert Architect:
  - [architect design pin — 2026-07-22] Resolving Olivia's 3 points (581/582/583) that the accepted decision leaves implicit. All feature-level clarifications, consistent with the decision — no reversal, no amendment needed.
  - 1) parent_in — NO param; reads the structured 'parents' field. Olivia's read is correct and is the only reading consistent with the decision's own 'rule data stays structured; a validator reads it, never re-encoded as both a typed field and a string param' principle. Pin: ONE parent-eligibility validator named 'parent_in' that reads spec.items[type].parents — non-empty parents → parent must be one of them; empty parents (and no no_parent) → today's lenient 'any parent or none' (byte-identical for bug/review). 'no_parent' is a SEPARATE explicit opt-in validator (no param) that forbids any parent — records get it from the category bundle, epic adds it explicitly; AND-composed with parent_in it yields 'no parent' (epic-as-root). The seed-catalog colon notation 'parent_in:<types>' is DOCUMENTARY shorthand, not a spec-declared param: the 583 .overrides assignment surface lists BARE names. A validator carries a param ONLY when its threshold is not already a structured field — the one seed example is 'subentity_title_max:<n>' (the 120 threshold is the module constant TITLE_ADVISORY_MAX, not a structured spec field), so that one legitimately parses a param; parent_in does not.
  - 1) corollary — the decision's Plane-1 'empty parent_in allowlist rejected' line is MOOT under the no-param reading: there is no list param that could be empty. Empty 'parents' is the valid lenient case, and a 'parents' entry naming an undeclared type is already caught by _check_item_refs in WorkflowSpec._validate. So 583 does NOT add an empty-parent_in check; that ADR-541 sentence is reconcilable-when-next-touched documentary phrasing, not a rule to build. Net for the dev: parent_in and no_parent are both zero-arg catalog entries.
  - 2) 'byte-identical' = same issue SET + a deterministic stable sort (option a), NOT reproduction of today's exact order. Recommendation: (a). Rationale: today's order is incidental — per-check call sequence in MaintenanceMixin.check() then index insertion order, no sort (_cli/_main.py:1274). The per-item engine emits per-item, which necessarily interleaves check types differently; forcing it to reproduce the legacy grouping would ossify an accident and couple engine output to the old call order. The real contract is content — the (level, item, message) multiset — which stays identical. An explicit total, stable sort is strictly better: sq check becomes diffable/stable across runs and refactors, and --json consumers get MORE robust output (they must not depend on order today). Pin sort key: (has-item, item sequence_id, level-rank[error<warn], message), stable; squad-global/file-location issues (no item) form a fixed leading block. Apply at the report boundary — the combined list in _cli/_main.py::check (workflow_issues + svc.check()) — to BOTH the console and --json paths. gate()/abort mode does NOT sort (raises on first violation). @coordinator: YES this changes sq check on-screen ORDER (content identical) — please surface to the operator; it's the intended, better behaviour, not a regression.
  - 3) Plane-1 layering — split the NAME contract (low) from the IMPL (high). Put a bare-name registry in _workflow: VALIDATOR_NAMES: frozenset[str] (+ SQUAD_GLOBAL_VALIDATOR_NAMES), living alongside META_TYPES/_RESERVED_FLOOR in _workflow/_models.py (or a small _workflow/_validators.py) — those literal-name contract constants are the exact precedent. WorkflowSpec._validate reads that set for the catalog-membership check (param-aware: split on ':' , require the bare name ∈ VALIDATOR_NAMES, and that a param is present only for the names that take one). The behaviour — _services/_validators.py::CATALOG/SQUAD_GLOBAL_CATALOG — stays high and is obligated to implement exactly those names, enforced by a guard: a module-load assertion set(CATALOG) == VALIDATOR_NAMES (and the squad-global equivalent) plus a unit test, so impl can never drift from the declared contract. _services importing DOWN from _workflow is the correct edge; no back-edge, acyclic graph preserved. This is the project's standing boundary applied verbatim — vocabulary (valid names) is declarative and lives low; behaviour (validator functions) is code and lives high. Do NOT move the Plane-1 check up into _services (it would split load-time spec validity across two layers, against the decision's 'Plane-1 lives where load_workflow_spec/_validate already live').
- [2026-07-22T11:45:17Z] Mara Tester:
  - 2026-07-22 QA verification of Phase B (TASK-581/582/583) in a throwaway squad, real CLI, source untouched:
  - (1) sq check — clean squad -> '✓ no issues' exit 0. Crafted squad with a 173-char finding title, a STATUS: banner body, and a hand-injected dangling ref: sq check reports exactly those 3 warn-level issues, identical SET and identical order across repeated runs and in --json (sort holds: seq-ordered items, alpha message within an item).
  - (2) Gating — valid create/update/comment/reparent all succeed. Newly-gated invalid case confirmed: 'sq task N update --status Approved --force' (Approved invalid for work lifecycle) aborts with a clean SquadsError, exit 1, no traceback, file left unchanged (was previously only a check-report warning per REV-585 F1). Author/assignee: a skill slug is rejected at both create --author and update --assignee ('not a registered agent' / 'unknown slug'); role and operator slugs accepted.
  - (3) Assignment surface + Plane-1 — scaffolded .overrides/workflow.toml with a new work-category type assigning validators = ["no_parent"]: loads fine, sq workflow lint OK, and the engine actually enforces it live (create without parent OK, create --parent rejected: 'incident takes no parent'). Adding a bogus name (validators = ["no_parent", "bogus_check"]) fails closed cleanly: sq workflow lint reports the exact diagnostic + exit 1, sq list also fails closed at spec load with the same message, no traceback.
  - All 3 areas PASS. Full fast suite green (0 failures), ruff clean, pyright clean on every file this phase touched (305 pre-existing textual/TUI import errors are unrelated env noise, not in touched files). Recommend TASK-581/582/583 -> Done and FEAT-568 -> InReview. Did not transition items or commit (read-only verification).
- [2026-07-22T11:51:26Z] Catherine Manager:
  - Accepted to Done per op-pierre's standing delegation (reviewed + verified, non-visual): validator catalog, REV-585 approved, QA-verified.
<!-- sq:discussion:end -->
