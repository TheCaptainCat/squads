---
id: FEAT-714
sequence_id: 714
type: feature
title: Playbook as the 4th override kind, resolved per request
status: Done
parent: EPIC-538
author: product-owner
refs:
- EPIC-538
- ADR-696
- FEAT-533
- FEAT-712:depends-on
- PRD-859:implements
subentities:
- local_id: US1
  title: As a spec author, I want a playbook loader that merges .overrides/playbook.toml
    onto the bundled base
  status: Done
- local_id: US2
  title: As sq, I want the merged playbook resolved per request, not cached as an
    import-time singleton
  status: Done
- local_id: US3
  title: As an adopter, I want sq override to scaffold/diff/update the playbook like
    any other override kind
  status: Done
created_at: '2026-07-31T13:02:58Z'
updated_at: '2026-09-01T13:51:32Z'
---
<!-- sq:body -->
## Capability

Give the playbook (`_interactions/playbook.toml` — which role/skill guidance attaches to which item type) an override, the one bundled spec left out of the `.overrides/` subsystem today: `.overrides/playbook.toml`, wired into `sq override` (scaffold/diff/update), the drift-check, and the `override_base` stamp — the same shape workflow, roles, and templates already have.

## The seam this cannot ship without

The playbook is currently an import-time singleton over the bundled spec (`_interactions/__init__.py::_PLAYBOOK_SPEC`). A `.overrides/playbook.toml` merged by the shared engine would still be composed against, and coverage-validated against, the *bundled* type set rather than the project's active one — per ADR-696's own stated caveat, "the playbook cannot honour its half of this until it resolves per-request." So this feature carries that seam as non-optional scope, not a follow-up:

- **The bundled playbook stays a module-level immutable** — `_PLAYBOOK_SPEC` (and any `_BUNDLED_SPEC`-style export) remains the code default, exactly as FEAT-533 left it. FEAT-533 removed the *mutable* ambient globals (`_active_spec`, `_active_dir`); it deliberately did not touch this bundled-default cache, and this feature does not touch it either.
- **The merged (override-applied) playbook becomes a per-request value**, resolved the same way the active `WorkflowSpec` already is — folded onto the same request-scoped context primitive FEAT-533 built (the `ContextVar`-based container already carrying the active spec/dir/clock/actor), not a new ambient singleton. This is the exact pattern FEAT-533 established for the workflow spec; read that feature before building this one rather than re-deriving the shape.
- Every consumer that reads playbook coverage or role/skill guidance for a type (the coverage check, the generated `sq-<type>` skill text, `sq workflow` cheatsheet rendering) reads the per-request merged playbook, not the bundled singleton — so a project with an override sees its own guidance, and a project without one sees exactly today's bundled behaviour.

## Scope

- A new playbook loader, built on the shared merge engine (FEAT-712): bundled base + `.overrides/playbook.toml` → merged playbook, using the same deep-merge/`selected`/splat-ref mechanics the workflow loader uses.
- Per ADR-696 §4c: the playbook is addressed as a **single-file delta with keyed tables**, like the workflow override, not a per-slug file like roles — it is one referentially-coupled document (a playbook entry references role slugs and a type name).
- Splat-refs are the entry point for adding a custom role's guidance to a type's playbook entry: `roles = ["$(*self)", { slug = "my-role", … }]` — inheriting the bundled guides and adding one, in TOML's inline-array form (the `[[…]]` header form has no slot for the token).
- **No independent deselect for the playbook.** Per ADR-696 §4c, the playbook's active type set is *derived*, not independently declarable: the existing coverage rule already requires exactly one playbook entry per active non-roster type, so dropping a type from the workflow spec (FEAT-713) drops its playbook entry as a consequence. This feature does not add a `selected.playbook_types` key or equivalent.
- `sq override scaffold`/`diff`/`update` gain the playbook as a fourth kind, alongside workflow/roles/templates, with the same `override_base` drift stamp and the same CLI verbs an adopter already knows.
- Wire the per-request merged playbook into every consumer: coverage checks, generated `sq-<type>` skill text, `sq workflow` cheatsheet rendering.

## Acceptance

Traceable to EPIC-538's epic-level acceptance list:

- Appending one playbook bullet (one role guide to one type) takes one line (`$(*self)` + the addition), not a restated list — and a later bundled improvement to that type's other guides still flows through on the next load.
- `sq override scaffold --playbook` / `sq override diff --playbook` / `sq override update --playbook` (or the equivalent verb shape `sq override` already uses for workflow/roles/templates) work end to end, including the `override_base` drift warning.
- Two concurrent requests against two differently-customized squads each see their own merged playbook; neither observes the other's — proven the same way FEAT-533's acceptance proved it for the active spec.
- With no `.overrides/playbook.toml` present, behaviour is byte-identical to today: the bundled playbook, unchanged.
- Dropping a type via `.overrides/workflow.toml` (FEAT-713) removes its playbook coverage requirement as a consequence, with no separate deselect declaration needed and no coverage-check false positive.

## Constraints

- No module-level mutable singleton is introduced for the *merged* playbook — only the request-scoped context FEAT-533 built. The bundled playbook stays the module-level immutable it is today.
- Byte-identical default behaviour with no override present.
- No `eval`; splat-refs only, per the standing no-eval line.
- This feature does not reopen the merge/deselect/splat-ref design (FEAT-712's scope) or the workflow shadowing rules (FEAT-713's scope) — it is the playbook loader consuming both.

## Dependencies

- Depends on FEAT-712 (the shared override merge engine).
- Rides the request-scoped context primitive FEAT-533 (Done) already built for the active workflow spec — read it for the pattern; do not re-derive a second ambient mechanism.

## References

Settled input: EPIC-538 (epic body "Dependencies/relationships" — explicitly frames this as riding FEAT-533's seam), ADR-696 §4c (per-loader addressing, derived-not-independent playbook deselect) and its Consequences section ("the playbook cannot honour its half of this until it resolves per-request"), Pierre Chat's confirmation on ADR-696's discussion (bundled playbook stays module-level immutable; merged playbook lives in the request context). Do not re-derive or amend.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 714 add-story "As a <role>, I want … so that …"`; track with `sq feature 714 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a spec author, I want a playbook loader that merges .overrides/playbook.toml onto the bundled base |
| US2 | Done |  | As sq, I want the merged playbook resolved per request, not cached as an import-time singleton |
| US3 | Done |  | As an adopter, I want sq override to scaffold/diff/update the playbook like any other override kind |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a spec author, I want a playbook loader that merges .overrides/playbook.toml onto the bundled base

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Build the playbook loader on the shared merge engine (FEAT-712): single-file keyed-table delta, per ADR-696 4c, using deep-merge and splat-refs. No independent selected/deselect for the playbook type set — it derives from the workflow spec's active types via the existing coverage rule.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As sq, I want the merged playbook resolved per request, not cached as an import-time singleton

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Fold the merged playbook onto the same request-scoped context primitive FEAT-533 built for the active workflow spec. The bundled _PLAYBOOK_SPEC stays a module-level immutable default; nothing new is cached as a mutable singleton. Coverage checks, generated sq-<type> skill text, and cheatsheet rendering all read the per-request merged playbook.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want sq override to scaffold/diff/update the playbook like any other override kind

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
sq override scaffold/diff/update treat the playbook as a fourth kind alongside workflow/roles/templates, with the same override_base drift stamp and CLI verb shape.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T13:42:46Z] Olivia Lead:
  - Broken down as one task: TASK-720 (high, python-dev). Four subtasks: ST1 the playbook loader over the shared engine (US1); ST2 the seam — merged playbook as a field on _context.RequestContext, bundled _PLAYBOOK_SPEC untouched as the module-level immutable (US2); ST3 threading every playbook consumer onto the merged value (US2); ST4 sq override as a fourth kind (US3).
  - One task, not several: same owner role and one shipping increment throughout — the override is not correct without the seam, and the seam has no purpose without the override. ST3 is the widest surface (the _interactions accessors plus backends, _services/_base, _maintenance, _config_integrity, _roster, the cheatsheet) but it is the same change applied at each call site, not a second increment.
  - ST3 carries one cleanup the audit will hit: _services/_config_integrity.py holds a standing comment that item_types_for_role reads the bundled singleton and never the active spec, which its surrounding remedy logic leans on. That stops being true here — the note gets re-read and updated or deleted, not left to mislead.
  - @manager ordering note for dispatch: ST3 and TASK-718's ST4 (FEAT-713's consumer audit) touch the same call sites — the generated sq-<type> skill writers and the _interactions accessors. Sequence them; do not run the two devs concurrently in one tree.
- [2026-07-31T14:28:55Z] Robert Architect:
  - @architect ruling recorded for this feature's benefit: the playbook override needs NO escaping clause and no field exemption for its shell-bearing values.
  - The splat sigil is POSIX command-substitution syntax, and this document is the one of the three that carries command lines — a playbook entry's commands are CLI invocations and its guidance arrays quote them. Under the engine's original detection predicate (any occurrence of the sigil in a string value is a violation) an ordinary snippet like git commit -m "$(cat msg)" would have been a hard load failure on the adopter's squad, explained in terms of a grammar its author never used, and sq override scaffold would have owed a permanent escape-on-the-way-out duty.
  - Ruled instead as ADR-696 §4a (dated amendment): a value is in token territory only if it BEGINS with an unescaped sigil; a value that merely contains one after its first character is data, left verbatim. So shell content in commands and in the guidance arrays is safe with no work in this feature, and the scaffolded playbook override is byte-identical to its bundled source rather than an escaped variant of it. The fix lives in the engine (FEAT-712 / TASK-716), not here.
  - One thing to keep true when this feature's scaffold lands: do not introduce a bundled playbook string value that BEGINS with the sigil, which is the single residual case that would still need the double-sigil escape. TASK-716 carries a tests/meta guard asserting exactly that across the bundled documents, so a violation is caught by the gate rather than by an adopter — but a scaffold writer that synthesises new strings should know the constraint exists rather than discovering it from a red gate.
- [2026-08-02T20:16:15Z] Catherine Manager:
  - Carry REV-726 F17 into this feature scope. The bundled playbook holds 63 cross-type command references; under a rename or drop they instruct an agent to run refused commands from inside a surviving type skill (sq-feature telling the product owner to sq create task after task was renamed). Making the playbook overridable is what gives an adopter the remedy, so the acceptance should state the limitation and the path out rather than leaving prose staleness undocumented.
- [2026-08-03T15:48:12Z] Catherine Manager:
  - All three stories delivered by TASK-720 (four subtasks Done); review REV-735 Approved as second party. The playbook ships as the fourth override kind in 0.13, resolved per request rather than cached at import.
<!-- sq:discussion:end -->
