---
id: REV-000248
sequence_id: 248
type: review
title: 'Wave 2-4 review: workflow lint + sq check + override artifact + docs (TASK-242/243/244/245)'
status: Approved
author: reviewer
refs:
- FEAT-000209:addresses
- TASK-000242:addresses
- TASK-000243:addresses
- TASK-000244:addresses
- TASK-000245:addresses
- FEAT-000210
- TASK-000247
subentities:
- local_id: F1
  title: AC#1 'sq create incident works' is NOT met end-to-end — custom-type create
    CLI is FEAT-210 scope
  status: WontFix
  severity: medium
- local_id: F2
  title: 'open_service: vestigial F5 comment block + redundant try/except SquadsError
    re-wrap around validate_against_index_fail_closed'
  status: Fixed
  severity: low
- local_id: F3
  title: Two new reportPrivateUsage suppressions on _common._active_dir (_workflow_cmd.py:80,
    _main.py:998) — tracked by TASK-247 but new
  status: WontFix
  severity: low
- local_id: F4
  title: 'docs/workflow.md: lint sample output shows a line number (.toml:15) the
    linter never emits; hard-stop sample message is the index-cross-check msg, not
    the syntax-error one'
  status: Fixed
  severity: low
- local_id: F5
  title: No e2e test asserting an override type round-trips through create→file→list
    (carries forward REV-246 F4); is_open() now returns True for unknown status instead
    of raising (info)
  status: WontFix
  severity: low
created_at: '2026-06-30T09:11:44Z'
updated_at: '2026-06-30T11:44:43Z'
---
<!-- sq:body -->
Independent review of FEAT-000209 Wave 2-4 (I did not write this code). Scope: TASK-242 (sq workflow lint), TASK-243 (sq check integration + AC#5 fail-closed wiring), TASK-244 (workflow as the 3rd sq override artifact), TASK-245 (docs/workflow.md). Builds on REV-000246 (Wave-1 engine core, Approved). Gates re-run: pyright 0/0, ruff check clean, ruff format clean, targeted pytest green (see verdict comment). Verdict: APPROVE — no blocking defects in the Wave 2-4 deliverables. The one cross-feature caveat (custom-type create CLI is FEAT-210 scope, AC#1 only half-met here) is a feature-signoff note for the manager, not a defect in this code.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 248 add-finding "…" --severity high`; track with `sq review 248 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | WontFix |  | AC#1 'sq create incident works' is NOT met end-to-end — custom-type create CLI is FEAT-210 scope |
| F2 | 🟢 low | Fixed |  | open_service: vestigial F5 comment block + redundant try/except SquadsError re-wrap around validate_against_index_fail_closed |
| F3 | 🟢 low | WontFix |  | Two new reportPrivateUsage suppressions on _common._active_dir (_workflow_cmd.py:80, _main.py:998) — tracked by TASK-247 but new |
| F4 | 🟢 low | Fixed |  | docs/workflow.md: lint sample output shows a line number (.toml:15) the linter never emits; hard-stop sample message is the index-cross-check msg, not the syntax-error one |
| F5 | 🟢 low | WontFix |  | No e2e test asserting an override type round-trips through create→file→list (carries forward REV-246 F4); is_open() now returns True for unknown status instead of raising (info) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — AC#1 'sq create incident works' is NOT met end-to-end — custom-type create CLI is FEAT-210 scope

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**File:** src/squads/_cli/__init__.py:97 (`_ORDERED_WORK_TYPES = [t for t in ItemType if t in _work_types()]`) + src/squads/_cli/_create.py:26-32,99 (`_TYPES` hardcoded from `ItemType` enum, one create command per enum member).

**Severity:** MEDIUM (traceability / AC-wording, NOT a code defect).

**Issue:** FEAT-000209 AC#1 says a custom `[items.incident]` block makes `sq list -t incident` work AND (US1 acceptance) `sq create incident` work. I verified by hand on a real squad: `sq workflow lint` reports OK and the spec loads/validates the `incident` type, and `sq list -t incident` resolves the type via `parse_type` (which reads `active_spec()`) and returns rc 0. BUT `sq create incident` fails with `No such command 'incident'`: the Typer create/item sub-apps are built at IMPORT time from the fixed `ItemType` enum, before `open_service` ever calls `use_spec()`. So the LIST/filter half of AC#1 works; the CREATE half does not — you can never produce an incident to list. `sq list -t incident` returning 'no items' is therefore vacuous.

**Why this is not a Wave-2-4 defect:** the dynamic-CLI-from-spec build (iterate `spec.managed_types()` instead of the static enum, load the spec before the app tree is built) is explicitly **FEAT-000210** scope ('Custom types end-to-end: CLI, folder, skill' — confirmed in its body: 'The `for _type in WORK_TYPES` app-build loop in `_cli/__init__.py` must iterate `spec.managed_types()`'). FEAT-209's job is the loader/merge/lint/validate/override-artifact, all of which are correctly delivered.

**Suggested fix:** No code change in FEAT-209. Reconcile the AC#1/US1 wording so 'sq create incident works' is owned by FEAT-210, not claimed complete here (same class as REV-246 F2). @manager: do NOT sign FEAT-209 off as 'custom types are usable' — only 'override spec loads, validates, lints, and the override artifact works'.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-30T11:44:39Z] Catherine Manager:
  - Not a defect in this feature — custom-type create/show/transition CLI is FEAT-000210 scope (spec-driven command registration). AC#1/US1 re-scoped accordingly; tracked by FEAT-000210.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — open_service: vestigial F5 comment block + redundant try/except SquadsError re-wrap around validate_against_index_fail_closed

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**File:** src/squads/_services/_service.py, open_service() — the F5 comment block (lines ~196-201, the multi-line '# F5 (REV-000246): wrap OSError ... (Already handled by load_workflow_spec's own OSError handling ... but the guard above makes the pattern explicit for reviewers.)') and the try/except around validate_against_index_fail_closed (lines ~205-208: `try: validate_against_index_fail_closed(...) except SquadsError as exc: raise SquadsError(f'{exc}') from exc`).

**Severity:** LOW (dead/misleading commentary + no-op re-wrap).

**Issue (two parts):**
1. The F5 comment block describes a guard that does NOT exist — it says 'the guard above makes the pattern explicit' but there is no guard above it, only the load_workflow_spec try/except for SquadsError. It is vestigial scaffolding referencing a REV-246 finding that was resolved inside load_workflow_spec itself. It misleads a future reader into thinking there is OSError handling at this layer.
2. `raise SquadsError(f'{exc}') from exc` is a pure no-op re-wrap: validate_against_index_fail_closed already raises SquadsError whose message contains 'run `sq workflow lint` to see details', so this catch-and-rethrow changes nothing (it does not even add the pointer the load_workflow_spec branch adds). It is redundant.

**Suggested fix:** Delete the F5 comment block entirely. For the cross-check call, either drop the try/except (let it propagate — the message is already complete and points to lint) or, if you want consistency with the load branch, make the re-wrap actually add value. Cleaner: remove the try/except.

**Note:** ordering is CORRECT and robust — validate_against_index_fail_closed runs BEFORE use_spec(merged_spec), so an index-incompatible spec can never be installed. lint reaches lint_workflow_spec via a separate entry point and never routes through this hard-stop. The gate itself is sound; this is cleanup only.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-30T11:44:26Z] Catherine Manager:
  - Fixed: vestigial F5 comment block and the no-op try/except re-wrap around validate_against_index_fail_closed removed from open_service.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Two new reportPrivateUsage suppressions on _common._active_dir (_workflow_cmd.py:80, _main.py:998) — tracked by TASK-247 but new

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**File:** src/squads/_cli/_workflow_cmd.py:80 (`sp = resolve(_common._active_dir)  # pyright: ignore[reportPrivateUsage]`) and src/squads/_cli/_main.py:998 (same, in `check`).

**Severity:** LOW (tracked tech-debt, but new code).

**Issue:** Pierre's standing rule (TASK-000247) is no new `# pyright: ignore[reportPrivateUsage]` cross-module reach-ins. These two reach into `_common._active_dir` (a private module-level global). The Wave-2-4 work correctly cleaned ALL the workflow-spec reach-ins (verified: no `_active_spec[0]` / `_BUNDLED_SPEC` / `._from_machine` usages remain outside _workflow/__init__.py; call sites use the public active_spec()/bundled_spec()/Workflow.from_machine). But `_workflow_cmd.py:80` is genuinely NEW code (new file) introducing a NEW suppression, and `_main.py:998` is new code in the rewritten check command.

**Mitigating:** TASK-000247 Group B EXPLICITLY lists '`_cli/_workflow_cmd.py + _cli/_main.py common._active_dir`' as the pre-existing-style debt to clean in one focused pass. So this is acknowledged and tracked, not silent.

**Suggested fix:** Trivial and within reach now — `_common.py` already has `set_active_dir()`; add a symmetric public `active_dir() -> str | None` getter and call that in both sites, dropping both suppressions. If deferred, leave as-is and let TASK-247 sweep it — but flag to @manager that TASK-247 must run before the reportPrivateUsage rule is promoted from ignore to error, or these two will trip it.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-30T11:44:41Z] Catherine Manager:
  - Deferred to TASK-000247 (Group B reportPrivateUsage cleanup) — the two _active_dir suppressions are swept there as one focused pass.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — docs/workflow.md: lint sample output shows a line number (.toml:15) the linter never emits; hard-stop sample message is the index-cross-check msg, not the syntax-error one

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**File:** docs/workflow.md:329-337 (lint error sample table) and docs/workflow.md:406-412 (hard-stop sample).

**Severity:** LOW (doc-vs-implementation drift; doc is otherwise accurate).

**Issue (two small inaccuracies):**
1. Lines 334: the sample lint output shows location `.overrides/workflow.toml:15` — with a line number. The real `lint_workflow_spec` never produces a line number: the `location` field of a LintFinding is only ever the literal `.overrides/workflow.toml` (WORKFLOW_OVERRIDE_FILENAME) or `index cross-check`. A reader will expect line numbers that never appear.
2. Lines 408-411: the 'Hard stops' section is introduced with 'you ... introduced a syntax error' but the sample message shown is 'workflow spec is incompatible with the live index — run sq workflow lint' — which is the AC#5 index-cross-check message, NOT the syntax-error message. A TOML syntax error actually surfaces 'Malformed workflow override <path>: <err> — run sq workflow lint to see details'.

**Verified good:** no internal sq-item refs, no external URLs in the override section; documents `.overrides/workflow.toml` (correct — not `.squads.toml`); the worked-example TOML round-trips against the real loader (I parsed it: valid, loads the incident type); scaffold/diff/update command names all match the shipped CLI.

**Suggested fix:** Drop the `:15` from the sample location (or note line numbers are not emitted), and either swap the hard-stop sample to the malformed-TOML message or reword the lead-in to cover both spec-error and index-incompatibility cases. Cosmetic; non-blocking.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-06-30T11:44:27Z] Catherine Manager:
  - Fixed: docs/workflow.md lint sample output corrected to real linter output (TASK-000245 doc-fix pass).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — No e2e test asserting an override type round-trips through create→file→list (carries forward REV-246 F4); is_open() now returns True for unknown status instead of raising (info)

<!-- sq:finding:F5:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**Files:** tests/test_workflow_override.py (coverage gap); src/squads/_workflow/__init__.py:206 (is_open behavior).

**Severity:** LOW (test gap) + INFO (benign behavior change).

**Issue (two related observations):**
1. TEST GAP (carries forward REV-246 F4): the suite proves the override spec LOADS the incident type (test_*_merged_spec*), and that use_spec updates the WORKFLOWS/ALLOWED_PARENTS dicts, and the override-artifact scaffold/diff/update commands all work — but there is still NO end-to-end test that creates an override type item and reads it back (create → file under squads/<folder>/ → list/show). This is partly because that path is FEAT-210 (see F1), but the LIST/filter half of AC#1 (which DOES work today via parse_type+active_spec) has no CLI smoke either. Recommend FEAT-210 own the full e2e; for FEAT-209, a service/CLI test asserting `parse_type('incident')` resolves and `sq list -t incident` runs clean under an installed override would lock the half that ships now.

2. BEHAVIOR CHANGE (info, Wave-1 code but interacts with custom statuses): `is_open` was changed from `_DEFAULT_SPEC.is_open(status)` (== `not self.statuses[status].terminal`, raises KeyError on an unknown status) to `status not in _terminal_ref[0]`. An unknown/undeclared status now returns True (treated as open) instead of raising. This is arguably MORE robust and consistent with the FEAT-208 de-typing direction — flagging it as a deliberate semantic shift, not a regression. No action needed; just record it so a future 'why doesn't an unknown status blow up' question has an answer.

**Suggested fix:** Add the list-half CLI smoke for FEAT-209; leave the create/show e2e to FEAT-210. Accept the is_open change as intended.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-06-30T11:44:43Z] Catherine Manager:
  - e2e create→list test deferred to FEAT-000210 (the path it exercises is 210 scope). is_open() returning True for an unknown status accepted as intended (FEAT-208-consistent, more robust).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:13:25Z] Paul Reviewer:
  - VERDICT: APPROVE (Wave 2-4 deliverables). No blocking defects. All five findings are MEDIUM(traceability)/LOW/INFO — none require code changes for the FEAT-209 deliverables to be correct.
  - Gates re-run by me: pyright 0 errors/0 warnings; ruff check clean; ruff format --check clean (139 files); pytest tests/test_workflow_override.py + test_workflow_spec.py + test_docfiles.py = 96 passed; tests/test_override_commands.py + test_override_loader.py = 70 passed.
  - Focus-area verdicts: (1) AC#5 fail-closed wiring — CORRECT & robust: validate_against_index_fail_closed runs BEFORE use_spec(merged_spec), so an index-incompatible spec can never be installed; lint reaches the same checks via lint_workflow_spec (separate entry point) and never self-blocks through the hard-stop. Vestigial F5 comment + no-op re-wrap noted (F2, cleanup only). (2) sq check fallback — SOUND: lint probe + bundled-spec fallback on SquadsError lets other checks run; it cannot mask a real failure (the workflow error is captured as its own CheckIssue first, then other checks run against the bundled default, never a misleading override). (3) Override artifact — follows the templates/roles pattern with NO parallel mechanism; scaffold writes canonical .overrides/workflow.toml, refuses clobber without --force, and the scaffolded example round-trips to a no-op (all commented); drift is stamp-version-only by design and consistent with roles (acceptable for v1). (4) reportPrivateUsage — workflow accessors used everywhere; ZERO new spec reach-ins; the only two new suppressions are _common._active_dir, tracked by TASK-247 (F3). (5) Docs — accurate, .overrides/workflow.toml documented, no internal refs / external URLs, example round-trips; two cosmetic drifts (F4).
<!-- sq:discussion:end -->
