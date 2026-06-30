---
id: REV-000255
sequence_id: 255
type: review
title: 'FEAT-000250 de-globalize workflow spec: Service-owned threaded context, delete
  singleton'
status: Approved
author: reviewer
refs:
- FEAT-000250:addresses
- TASK-000251:addresses
- TASK-000252:addresses
- TASK-000253:addresses
- TASK-000254:addresses
subentities:
- local_id: F1
  title: Parse-ordering test under-proves its docstring claim
  status: Fixed
  severity: low
- local_id: F2
  title: test_rendering._template_for is a hand-copy of ServiceCore._template_for
    (drift risk)
  status: Fixed
  severity: low
- local_id: F3
  title: _meta_compat uses bundled_spec() inline rather than a threaded-in spec param
  status: WontFix
  severity: low
- local_id: F4
  title: '[duplicate — see F1/F2/F3] tool-retry artifact'
  status: WontFix
  severity: low
- local_id: F5
  title: '[duplicate — see F1/F2/F3] tool-retry artifact'
  status: WontFix
  severity: low
- local_id: F6
  title: '[duplicate — see F1/F2/F3] tool-retry artifact'
  status: WontFix
  severity: low
- local_id: F7
  title: '[duplicate — see F1/F2/F3] tool-retry artifact'
  status: WontFix
  severity: low
created_at: '2026-06-30T10:43:46Z'
updated_at: '2026-06-30T11:51:39Z'
---
<!-- sq:body -->
## Verdict: APPROVE

Independent review of FEAT-000250 (ADR-000249 Option A): replace the process-global workflow-spec singleton with a `Service`-owned, threaded `WorkflowSpec` context. I did not author this code.

**Singleton fully eliminated: YES. Behaviour byte-identical: YES.**

### Gates re-run (all green)
- `uv run pyright` — 0 errors, 0 warnings.
- `uv run ruff check .` — All checks passed.
- `uv run ruff format --check .` — 139 files already formatted.
- Safety-net suite (`test_spine_characterization`, `test_workflow_spec`, `test_workflow_capability_flags`, `test_workflow_override`, `test_cli`, `test_rendering`, `test_retype`) — **289 passed, 1 skipped, exit 0**.

### Singleton elimination (Focus 1) — confirmed
- No `_active_spec` mutable-cell list, no `_terminal_ref` cell, no in-place dict mutation, no `global TERMINAL`/`WORKFLOWS`, no `use_spec`/`reset_spec` live code. The only residual mention is a docstring in `_workflow/__init__.py:8` describing what was deleted.
- `WORKFLOWS`/`SUBENTITY_WORKFLOWS`/`ALLOWED_PARENTS`/`TERMINAL` are now read-only constants built once from the immutable `_BUNDLED_SPEC`; `test_workflow_override.py` asserts their immutability (identity stable, custom types never leak in).
- The retained free-function shims (`is_open`, etc.) delegate to `_BUNDLED_SPEC` and are only used where bundled vocab is correct (migrations, CLI fallback). No override-aware call site reaches them.

### Service threading (Focus 2) — correct and complete
- `open_service` resolves+merges+validates the spec once and passes it explicitly via `Service(sp, spec=...)`; `ServiceCore.spec` stores it and constructs `IndexStore(..., spec=self.spec)`.
- All ~40 former free-function call sites across `_base`, `_items`, `_maintenance`, `_subentities`, `_refs`, `_roster`, `_collab`, `_retype` now read `self.spec.<method>`. `_maintenance` (the dense `sq check`) is fully swept; the `_DEFAULT_SPEC` reach-in is gone; `@staticmethod` check methods became instance methods and callers updated. No service module imports a deleted free function. No consumer uses `bundled_spec()` where it should see the override.

### CLI per-invocation handle (Focus 3) — sound
- `_common._active_spec` + `set/get_active_spec`, bound in the root `--dir` callback via `_bind_active_spec` before subcommand parse. `get_active_spec()` falls back to `bundled_spec()` when unbound.
- Parse-ordering proven empirically: `test_ac1_sq_list_custom_type_returns_no_items` passes `sq list -t incident` for an override-only type — it only succeeds if the override spec is bound before `parse_type` fires. Bundled-only fallback path also covered.
- Module-global vs contextvar: ADR-249 sanctioned mirroring `set_active_dir`; acceptable, not a blocker (see F3).

### Byte-identical safety net (Focus 4) — confirmed
- `test_spine_characterization.py`, `test_workflow_spec.py` (golden-lock), `test_workflow_capability_flags.py`, `test_retype.py` are **UNMODIFIED** (git status clean) and green against the new code — the strongest possible byte-identical signal. (Olivia's done-note claimed these were "rewritten"; the actual, better, state is that they were untouched.)

### No new private-usage / acyclic imports (Focus 5) — confirmed
- No `reportPrivateUsage` suppression introduced; the refactor **removed** two (`_DEFAULT_SPEC` reach-ins in `_common` and `_store`, `_template_for` in `test_rendering`). All remaining suppressions are pre-existing (`store._log`, etc., TASK-247 scope).
- Import graph acyclic: `_index/_store.py` now imports `_workflow._models.WorkflowSpec` at top level — a leafward edge, no cycle (`_workflow` core imports nothing from `_index`/`_services`). The `_workflow._loader` → `_models._index` edge stays lazy-inside-function. Full import chain verified clean.

Findings below are all LOW severity (observational / test-hygiene). None block.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 255 add-finding "…" --severity high`; track with `sq review 255 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Parse-ordering test under-proves its docstring claim |
| F2 | 🟢 low | Fixed |  | test_rendering._template_for is a hand-copy of ServiceCore._template_for (drift risk) |
| F3 | 🟢 low | WontFix |  | _meta_compat uses bundled_spec() inline rather than a threaded-in spec param |
| F4 | 🟢 low | WontFix |  | [duplicate — see F1/F2/F3] tool-retry artifact |
| F5 | 🟢 low | WontFix |  | [duplicate — see F1/F2/F3] tool-retry artifact |
| F6 | 🟢 low | WontFix |  | [duplicate — see F1/F2/F3] tool-retry artifact |
| F7 | 🟢 low | WontFix |  | [duplicate — see F1/F2/F3] tool-retry artifact |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Parse-ordering test under-proves its docstring claim

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
tests/test_cli.py:1764 `test_spec_bound_before_parse_type_runs` documents that parse_type/parse_status fire after the callback body, but it invokes `sq list --all` (no `--type`/`--status`), so neither parser callback actually runs — it only asserts `get_active_spec() is bundled_spec()` after the call. The real parse-time ordering with an OVERRIDE spec (where bundled != active) is proven elsewhere: tests/test_workflow_override.py:1534 `test_ac1_sq_list_custom_type_returns_no_items` runs `sq list -t incident` for an override-only type and asserts exit 0 (only possible if the override spec is bound before parse_type fires). So the coverage exists; this test is just mislabeled relative to what it exercises. Suggestion: have it pass `--status`/`--type` so a parser callback genuinely fires, or note that the override case is covered by the override test. Not a behaviour bug.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-30T11:51:37Z] Catherine Manager:
  - Fixed: test now invokes 'list --type task --status InProgress' so parse_type/parse_status actually fire — exit 0 proves the spec was bound in the root callback before parse. Docstring corrected to match.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — test_rendering._template_for is a hand-copy of ServiceCore._template_for (drift risk)

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
tests/test_rendering.py defines a module-local `_template_for` that hand-copies the logic of `ServiceCore._template_for` (now an instance method using `self.spec.item_is_meta`). The old test imported the real free function; since it became a method it can't be imported standalone, so the rewrite reconstructs it against `bundled_spec()`. This is faithful today, but the copy can silently drift if the real method changes (e.g. a third template branch). Low risk — the production logic is simple. Optional: have the test build a `ServiceCore`/`Service` and call the real method, or extract the mapping to a shared pure helper. Positive side-note: this rewrite removed a `# pyright: ignore[reportPrivateUsage]` suppression.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-30T11:51:38Z] Catherine Manager:
  - Fixed: hand-copied _template_for removed; test now calls the real bundled_spec().item_is_meta(), single source of truth, no suppression.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — _meta_compat uses bundled_spec() inline rather than a threaded-in spec param

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
src/squads/_migrations/_meta_compat.py:96 calls `bundled_spec().subentity_initial(kind)` inline. TASK-000252 prescribed "thread a spec explicitly (pass the bundled/loaded spec into the migration helper)" rather than reaching a module-level accessor. The impl reaches `bundled_spec()` directly inside `_parse_block`.

Why this is NOT a behaviour or correctness problem: migrations parse legacy body-stored `:meta` regions that predate any override mechanism, so the BUNDLED vocabulary is the only correct source here — an override spec must not influence how historical meta blocks are re-parsed. The old code (`subentity_initial(kind)`) delegated to the singleton which, during a migration, was always the bundled spec. So behaviour is byte-identical and the bundled choice is semantically right.

It is a minor shape deviation from the task's "pass it in" wording — `bundled_spec()` is a clean function returning the immutable default, not the deleted mutable singleton, so it does not reintroduce global mutable state. No action required; flagged only for the record so a future reader doesn't mistake it for a missed thread-through.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-30T11:43:44Z] Catherine Manager:
  - Accepted by design: migrations intentionally use the bundled vocabulary (not the project override), so _meta_compat reading bundled_spec() directly is correct and byte-identical. No change.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — [duplicate — see F1/F2/F3] tool-retry artifact

<!-- sq:finding:F4:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Duplicate created by a CLI retry (a shell-quoting artifact emitted spurious `--file -)` noise while the command actually succeeded). The canonical findings are F1 (parse-ordering test), F2 (test_rendering._template_for copy), and F3 (_meta_compat bundled_spec inline). Disregard this entry.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-06-30T11:43:38Z] Paul Reviewer:
  - Closing as duplicate tool-retry artifact; canonical findings are F1/F2/F3.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — [duplicate — see F1/F2/F3] tool-retry artifact

<!-- sq:finding:F5:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Duplicate created by a CLI retry (a shell-quoting artifact emitted spurious `--file -)` noise while the command actually succeeded). The canonical findings are F1 (parse-ordering test), F2 (test_rendering._template_for copy), and F3 (_meta_compat bundled_spec inline). Disregard this entry.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-06-30T11:43:39Z] Paul Reviewer:
  - Closing as duplicate tool-retry artifact; canonical findings are F1/F2/F3.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — [duplicate — see F1/F2/F3] tool-retry artifact

<!-- sq:finding:F6:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
Duplicate created by a CLI retry (a shell-quoting artifact emitted spurious `--file -)` noise while the command actually succeeded). The canonical findings are F1 (parse-ordering test), F2 (test_rendering._template_for copy), and F3 (_meta_compat bundled_spec inline). Disregard this entry.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-06-30T11:43:41Z] Paul Reviewer:
  - Closing as duplicate tool-retry artifact; canonical findings are F1/F2/F3.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — [duplicate — see F1/F2/F3] tool-retry artifact

<!-- sq:finding:F7:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
Duplicate created by a CLI retry (a shell-quoting artifact emitted spurious `--file -)` noise while the command actually succeeded). The canonical findings are F1 (parse-ordering test), F2 (test_rendering._template_for copy), and F3 (_meta_compat bundled_spec inline). Disregard this entry.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-06-30T11:43:42Z] Paul Reviewer:
  - Closing as duplicate tool-retry artifact; canonical findings are F1/F2/F3.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T11:51:10Z] Elias Python:
  - Fixed F1 and F2 (test-hygiene only; no production behaviour changed).
  - F1 (test_cli.py:1764 test_spec_bound_before_parse_type_runs): changed the invocation from ['list', '--all'] to ['list', '--type', 'task', '--status', 'InProgress']. Both --type and --status now trigger parse_type/parse_status as Typer parser callbacks; exit 0 is only possible if the bundled spec was already bound by the root callback. Docstring updated to match. The test_workflow_override.py coverage (override-spec parse-ordering via 'incident' type) is complementary and untouched.
  - F2 (test_rendering.py): removed the hand-copied _template_for helper function entirely. The parametrized test now calls bundled_spec().item_is_meta(type_str) directly — the exact same public method ServiceCore._template_for calls — and builds the template path inline. No separate copy exists; any new branch added to the production method will break the test immediately. No reportPrivateUsage suppression added; no production code touched.
  - Gates: pyright 0 errors, ruff clean, 173 passed 1 skipped across test_cli.py / test_rendering.py / test_workflow_override.py.
<!-- sq:discussion:end -->
