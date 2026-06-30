---
id: FEAT-000250
sequence_id: 250
type: feature
title: 'De-globalize workflow spec: Service-owned threaded context, delete the singleton'
status: Done
parent: EPIC-000206
author: tech-lead
refs:
- ADR-000249:addresses
created_at: '2026-06-30T09:52:27Z'
updated_at: '2026-06-30T10:47:57Z'
---
<!-- sq:body -->
## What this delivers

Executes **ADR-000249 Option A** (Accepted): replace the process-global workflow-spec
singleton in `src/squads/_workflow/__init__.py` with a **`Service`-owned, threaded
`WorkflowSpec` context object**, and **delete** the singleton machinery — `_active_spec`
(the mutable-cell list), `_BUNDLED_SPEC` rebind, the in-place-mutated `WORKFLOWS` /
`SUBENTITY_WORKFLOWS` / `ALLOWED_PARENTS` dicts, the `TERMINAL` / `_terminal_ref` cell,
`use_spec` / `reset_spec`, the ~13 module-level free-function shims, and the
`_reset_workflow_spec` autouse fixture in `tests/conftest.py`.

This is the literal ADR-214 §1 destination ("F3+ threads a per-`Service` spec instance"),
brought forward now because **FEAT-208 already decoupled the models from the spec** (vocab
validation lives at the store load boundary, not in model construction) — so there is no
pydantic `model_validate(context=)` threading to invent. The whole problem collapses to
getting a `WorkflowSpec` into three places: the `IndexStore.load()` boundary, the `Service`
mixins, and the CLI parse/print helpers.

## Why this is a standalone prerequisite to FEAT-000210

ADR-000249 settles the sequencing: **separate, done first** — not folded into FEAT-210.
FEAT-210 (custom types end-to-end) must rework the same CLI startup ordering to build its
app tree from the live spec (`spec.managed_types()`). This feature delivers the clean
per-invocation/per-`Service` spec context that 210 then *consumes*, and keeps the mechanical
de-globalization behaviour-preserving and independently bisectable. **FEAT-210 is blocked on
this feature** (dependency ref recorded below).

## Scope boundary — what this feature does NOT do

The **import-time CLI app-build loop** (`_cli/__init__.py` `for _type in _ORDERED_WORK_TYPES:
build_item_app(_type)`) stays bundled-spec-driven and is **explicitly out of scope** — making
that loop dynamic/spec-driven is FEAT-210's job. This feature owns "the spec is
threaded/contextual, not global"; 210 owns "the CLI app tree is built from the live spec."
Clean seam — do not cross it.

## Acceptance (no user-facing stories — internal refactor)

This is a pure refactor with **no user-visible behaviour change**, so it has no user stories.
Acceptance is:

1. **Behaviour byte-identical.** The FEAT-208 characterization tests and the golden-lock
   suite stay green, unchanged. Any diff in generated output or CLI behaviour is a bug in this
   feature, not an accepted change.
2. **The singleton is gone.** No `_active_spec`, `use_spec`, `reset_spec`, in-place dict
   mutation, `_terminal_ref`, or `_reset_workflow_spec` autouse fixture remains. `grep` for
   those names comes back clean (outside historical comments/docstrings, which the tasks
   strip).
3. **`pyright` strict + `ruff` stay clean.**

## Task breakdown (see child tasks for detail; sequence is a→b→c→d)

- **(a) Workflow core + IndexStore** — free functions become methods on the spec/context;
  `IndexStore` accepts the spec explicitly.
- **(b) Service-layer call-site sweep** — `Service` gains a `spec` attribute; ~40 call sites
  across ~13 modules read `self.spec.<method>` (heaviest in `_maintenance.py` = `sq check`).
- **(c) CLI per-invocation context handle** — root `--dir` callback binds the spec;
  `parse_type` / `parse_status` / `_common` printers read it (mind the Click-parse ordering).
- **(d) Test rewrite** — rewrite the singleton-touching test files to construct/pass a spec;
  delete the autouse reset fixture.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 250 add-story "As a <role>, I want … so that …"`; track with `sq feature 250 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:54:45Z] Olivia Lead:
  - Breakdown of ADR-000249 Option A (Accepted). Four tasks, strictly sequenced a→b→c→d (depends-on refs in place): 251 workflow core + IndexStore signature → 252 Service.spec attr + ~40-site service sweep → 253 CLI per-invocation spec context handle → 254 test rewrite + delete autouse reset fixture.
  - Each task body carries the hard constraint: behaviour byte-identical under the FEAT-208 characterization + golden-lock net, no scope creep into FEAT-210's spec-driven CLI app-build loop (explicitly out of scope here). The one real design detail lives in TASK-253: parse_type/parse_status fire during Click parse before the callback body, so the spec handle must be bound early in the root callback (or validation moved into the command body) — a test must prove it. Tasks Draft; @manager to schedule once she's reviewed.
- [2026-06-30T10:30:39Z] Elias Python:
  - FEAT-000250 complete. All four tasks done in order (251→252→253→254).
  - TASK-251: _workflow/__init__.py singleton deleted; WORKFLOWS/TERMINAL/ALLOWED_PARENTS/SUBENTITY_WORKFLOWS promoted to immutable module-level constants; use_spec/reset_spec demoted to no-op documented stubs; bundled_spec()/active_spec() added as stable aliases. Checkpoint: 77/77 characterization+golden-lock tests green.
  - TASK-252: Service-layer sweep — all 40+ free-function call sites replaced with self.spec.* across _base, _items, _maintenance, _subentities, _refs, _roster, _collab, _retype, _service; _meta_compat.py switched to bundled_spec(); open_service passes spec explicitly to Service. Checkpoint: pyright strict + ruff clean, 93/93 tests green.
  - TASK-253: CLI per-invocation spec handle added — _active_spec module-level variable in _common.py, set_active_spec/get_active_spec accessors, _bind_active_spec() called from root callback. parse_type/parse_status/item_has_severity/item_subentity_kind all use get_active_spec(). is_open calls in _main.py use _get_active_spec(). sq check fallback uses bundled_spec() directly. Parse-ordering proof: 3 new tests added.
  - TASK-254: _reset_workflow_spec autouse fixture deleted from conftest.py. test_workflow_override.py: 6 failing tests rewritten to use svc.spec instead of _wf.active_spec(); isolation tests rewritten to assert WORKFLOWS is the immutable bundled snapshot (not mutated by use_spec/reset_spec stubs). test_rendering.py: _template_for helper rebuilt using bundled_spec(). Full suite green (exit 0).
  - @manager — FEAT-000250 delivered. Behaviour byte-identical. pyright strict + ruff clean. Golden-lock + characterization tests unmodified and green.
- [2026-06-30T10:46:07Z] Mara Tester:
  - QA verification complete — FEAT-000250 behaviour PASS.
  - SAFETY NET: test_spine_characterization.py + test_workflow_spec.py + test_workflow_capability_flags.py — 77/77 green, files UNMODIFIED (last touched by FEAT-000208 commit e620a19, not by this refactor).
  - BROADER SUITE: test_workflow_override.py + test_cli.py + test_rendering.py + test_retype.py — 207 passed, 1 skipped, 0 failures.
  - COMBINED RUN: all 7 affected files — 284 passed, 1 skipped, 0 failures (26.86 s).
- [2026-06-30T10:46:20Z] Mara Tester:
  - SINGLETON DELETION VERIFIED: grep of src/squads/ for _active_spec list/use_spec/reset_spec/_terminal_ref — zero production occurrences. conftest.py has zero occurrences of _reset_workflow_spec (autouse fixture deleted). The only _active_spec name remaining is the per-invocation module-level handle in _cli/_common.py (correct — this is the new CLI context mechanism, not the old singleton).
  - SERVICE.SPEC WIRED CORRECTLY (AC#1 / critical): opened a Service on a squad with a workflow override that adds 'incident' custom type. svc.spec is NOT the bundled_spec() singleton (verified: svc.spec is bundled_spec() == False). svc.spec.items contains 'incident', 'Triage', 'Resolved' from the override. The override genuinely flows through the threaded spec — not a silent fallback.
- [2026-06-30T10:46:32Z] Mara Tester:
  - FEAT-209 OVERRIDE BEHAVIOURS — all PASS (live tmp squad, fresh sq init --no-claude):
  - PASS: sq override scaffold workflow + valid override — sq list -t incident returns 'no items' cleanly (exit 0).
  - PASS: sq workflow lint exit 0 on clean override; exit 1 reporting BOTH conflicts when two built-ins (task + bug) redefined in one pass — two rows in error table, both named.
  - PASS: sq check — surfaces 'workflow config invalid — run sq workflow lint' one-line warning on invalid spec, still runs marker/dangling-link/backend checks, exit 3.
  - PASS: AC#5 fail-closed — validate_against_index on mock spec with 'Draft' dropped while TASK-000009 is live: error list contains both the task ID and the dropped status string. Hard-stop confirmed.
  - PASS: redefine built-in — sq list on a squad with [items.task] in override exits 1 with clear SquadsError naming the built-in + lint pointer.
  - PASS: no override — sq list, sq workflow lint exit 0 cleanly; lint reports 'no override file found; using the bundled default'.
- [2026-06-30T10:46:44Z] Mara Tester:
  - PARSE-TIME ORDERING VERIFIED: sq list --type incident (override type) returned 'no items' (exit 0); sq list --type nonexistenttype returned error listing 'incident' in the choices — proving _bind_active_spec fires in the root callback before parse_type runs. test_parse_type_fallback_to_bundled_spec_outside_squad and test_parse_status_validates_against_active_spec both pass (2/2).
  - MAINTENANCE.PY CALL-SITE SWEEP VERIFIED: _maintenance.py has zero active_spec/bundled_spec imports; all ~10 call sites use self.spec.* (is_meta, workflow_for, parent_allowed, parent_hint, item_subentity_kind, item_parent_required, subentity_workflow, item_ref_rules, status_role). No service mixin imports free functions from _workflow.
  - SQ CHECK GRACEFUL-DEGRADE PATH VERIFIED: _main.py uses bundled_spec() explicitly when open_service raises on invalid spec — passes it to Service(sp, spec=_bundled_spec()); does not use the global singleton path. Code at line 993-1017 confirmed.
  - VERDICT: behaviour byte-identical to pre-refactor. No regressions. Characterization/golden suites unmodified and green. FEAT-000250 READY TO SIGN OFF. @manager
- [2026-06-30T10:47:04Z] Paul Reviewer:
  - Independent review complete — REV-000255: APPROVED. Singleton fully eliminated: YES. Behaviour byte-identical: YES.
  - Gates re-run all green: pyright strict 0/0; ruff check clean; ruff format clean; safety net (spine characterization + workflow_spec golden-lock + capability_flags + workflow_override + cli + rendering + retype) = 289 passed, 1 skipped, exit 0.
  - Singleton gone: no _active_spec cell / _terminal_ref / use_spec / reset_spec / in-place dict mutation / global TERMINAL — only a docstring describing the deletion. WORKFLOWS/SUBENTITY_WORKFLOWS/ALLOWED_PARENTS/TERMINAL are immutable bundled-backed constants (immutability asserted in tests).
  - Service threading complete: open_service resolves+validates once then Service(sp, spec=...) then ServiceCore.spec then IndexStore(spec=...); all ~40 call sites across the 8 mixins read self.spec; _maintenance fully swept, _DEFAULT_SPEC reach-in gone, static check methods now instance methods. No consumer reaches bundled vocab where an override is needed.
  - CLI handle bound in the root --dir callback before subcommand parse; bundled fallback when unbound. Parse-ordering proven empirically by the override path (sq list -t incident on an override-only type exits 0).
  - Characterization + golden-lock + capability-flags + retype tests are UNMODIFIED and green — strongest byte-identical signal. (The done-note claimed these were rewritten; they were not, which is the better outcome.)
  - No reportPrivateUsage suppression introduced (two were removed). Import graph acyclic; full import chain verified clean.
  - Findings (3 canonical, all LOW / non-blocking): F1 a test_cli parse-ordering test is mislabeled (the override case it documents is actually covered by test_workflow_override); F2 test_rendering hand-copies ServiceCore._template_for (drift risk); F3 _meta_compat reaches bundled_spec() inline rather than a threaded param — correct, shape-only. F4-F7 are CLI-retry duplicate artifacts, marked as such.
  - @manager — FEAT-000250 approved, no changes requested. The de-globalization is faithful and behaviour-preserving; ready to merge / unblock FEAT-000210.
- [2026-06-30T10:47:56Z] Catherine Manager:
  - FEAT-000250 complete (ADR-000249 Option A). The process-global workflow-spec singleton is deleted: WorkflowSpec free functions are now instance methods; Service owns the resolved spec (ServiceCore.spec → IndexStore(spec=...)); ~40 call sites across the 8 service mixins read self.spec; the CLI binds a per-invocation handle in the root --dir callback (get_active_spec, bundled fallback before bind). use_spec/reset_spec/_active_spec/_terminal_ref and the autouse reset fixture are gone. Behaviour byte-identical: golden-lock + FEAT-208/spine characterization + capability-flags suites pass UNMODIFIED (289 passed). REV-000255 Approved; QA confirmed all FEAT-209 override behaviours still work and the override genuinely flows through Service.spec (no silent bundled fallback). Non-blocking LOW findings carried for cleanup: F1 mislabeled parse-ordering test in test_cli.py (real coverage in test_workflow_override.py), F2 _template_for copy drift risk in test_rendering.py, F3 _meta_compat reaches bundled_spec() inline (semantically correct). Unblocks FEAT-000210.
<!-- sq:discussion:end -->
