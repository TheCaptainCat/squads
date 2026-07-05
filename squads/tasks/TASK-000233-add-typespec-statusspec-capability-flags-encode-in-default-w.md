---
id: TASK-233
sequence_id: 233
type: task
title: Add TypeSpec/StatusSpec capability flags, encode in default_workflow.toml,
  harden loader (extra=forbid)
status: Done
parent: FEAT-208
author: tech-lead
subentities:
- local_id: ST1
  title: Add capability flags to TypeSpec/StatusSpec + encode in default_workflow.toml
  status: Done
  story: US2
- local_id: ST2
  title: extra=forbid + model_validate hardening; characterization tests pin 22 checks
  status: Done
  story: US2
created_at: '2026-06-26T09:48:47Z'
updated_at: '2026-06-26T10:26:02Z'
---
<!-- sq:body -->
## Goal

Add the capability-flag surface to the workflow spec models (ADR-232 §2/§5) and encode their
values in `default_workflow.toml` for all 10 types, plus fold in the fail-closed hardening gap. This
is the additive, behavior-neutral foundation for FEAT-208 (F2): it introduces the flags and their
default-vocab values WITHOUT yet consuming them — the engine still uses today's `is ItemType.X`
checks after this task, so behavior is byte-identical and all three golden-locks stay green.

Also lands the **characterization tests** that pin the current behavior of each identity check, so
TASK-234's reification can be proven equivalent rather than assumed (ADR §6, characterization-first
— the FEAT-220 lesson: the regression guard comes BEFORE the rewire).

Sequence: **first** task. TASK-234 (reify) consumes these flags; TASK-235 (de-type) depends on
the hardened loader + reserved-vocab plumbing introduced here.

## What to build

- **New `TypeSpec` capability fields** (additive to ADR-214's prefix/folder/machine/parents/aliases),
  pyright-strict, typed:
  - `is_meta: bool = False` (role/skill/operator: outside work types, no work lifecycle, slug-keyed
    identity, retype-ineligible);
  - `subentity_kind: str | None = None` ("story" | "subtask" | "finding" | None — the kind a type's
    children are; feature→story, task→subtask, review→finding);
  - `severity_field: bool = False` (type surfaces a severity badge — today: bug);
  - `parent_required: str | None = None` (the parent-type rule expressed declaratively — today: task→
    feature);
  - `ref_rules: list[RefRule] = []` (e.g. task → fixes|addresses hint; decision → supersedes). Define
    the `RefRule` model (pyright-strict).
- **`StatusSpec.role: str | None = None`** — the semantic-status-role marker the engine keys on (at
  minimum `"superseded"` for the ADR supersede rule), so future rules add a role name not a column.
- **Encode the values in `default_workflow.toml`** for all 10 types so the bundled default sets every
  flag to reproduce today's behavior exactly (is_meta on role/skill/operator; subentity_kind on
  feature/task/review; severity_field on bug; parent_required on task; ref_rules for task + decision;
  StatusSpec.role="superseded" on Superseded).
- **Fail-closed hardening (ADR §5):** add `model_config = ConfigDict(extra="forbid")` to EVERY
  workflow spec model and route the workflow loader through `model_validate(...)` (it does not today —
  the gap from FEAT-209/ADR-214, folded in here since F2 is already rewriting these models).
- **Characterization tests (ADR §6):** pin current behavior of each of the 22 identity checks before
  reification — e.g. "a decision with no incoming `supersedes` and status Superseded warns in
  `sq check`"; "a skill file not prefixed `SKILL-` is flagged"; task→feature parent enforcement;
  feature/task/review→sub-entity-kind; bug severity row. These lock today's behavior so TASK-234
  is proven equivalent.
- **New-surface unit tests:** each new flag has a direct test; the `extra="forbid"` rejection of an
  unknown TOML key is tested.

## Design constraints (ADR-232)

- §2 flag set exactly; §5 extra=forbid + model_validate; flags are ADDITIVE — not yet consumed by the
  engine in this task (consumption is TASK-234). Severity (`Severity`) is not widened/affected here.
- The F1 golden (default == today) still holds because the default spec sets flags to reproduce today;
  encoding the flags must not change any existing transition/terminal/prefix/folder value.

## THE STANDING GATE (every task in F2)

The entire existing test suite + all THREE golden-locks (workflow ADR-214, role-catalog ADR-221,
playbook ADR-226 incl. its byte-identical skill-output layer) MUST pass UNCHANGED — byte-identical
behavior. No existing test may be edited to accommodate F2; if one needs editing, that is a behavioral
change to be justified, not absorbed.

## Acceptance

1. `TypeSpec` carries is_meta/subentity_kind/severity_field/parent_required/ref_rules; `StatusSpec`
   carries `role`; all pyright-strict, `extra="forbid"`. `RefRule` model defined.
2. `default_workflow.toml` encodes the flag values for all 10 types reproducing today's semantics;
   the workflow loader routes through `model_validate`.
3. Characterization tests pinning all 22 current identity-check behaviors exist and pass against
   today's (unreified) engine.
4. Standing gate holds: full suite + all three goldens green, unchanged. pyright/ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 233 add-subtask "<title>"`; track with `sq task 233 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add capability flags to TypeSpec/StatusSpec + encode in default_workflow.toml | US2 |
| ST2 | Done |  | extra=forbid + model_validate hardening; characterization tests pin 22 checks | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add capability flags to TypeSpec/StatusSpec + encode in default_workflow.toml

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — extra=forbid + model_validate hardening; characterization tests pin 22 checks

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T10:14:32Z] Elias Python:
  - TASK-233 implementation complete. Three parts delivered:
  - **Part A — Characterization tests (39 tests in tests/test_spine_characterization.py)**. All 22+ identity-check behaviors pinned against today's unreified engine. Each test named for the behavior it pins, not the layer. Covers: meta-type exclusion from WORK_TYPES / retype; self-author bypass for role/skill/operator; SKILL- prefix scan convention; role/skill body-generation guard; regen gating on role/skill; sq <type> app only for WORK_TYPES; task→feature parent spine + parent_hint ref-add hint; feature/task/review→sub-entity kind resolution; bug severity panel row; decision supersedes warn/clean/non-decision-skip; sq check subtask→story spine; retype status-carry vs. reset; repair from frontmatter; roster blocks skill slugs; SUBENTITY_KIND map exactness.
  - **Part B — Capability flags (17 tests in tests/test_workflow_capability_flags.py + TOML/models)**. New fields added to ItemSpec (is_meta, subentity_kind, severity_field, parent_required, ref_rules) and StatusSpec (role). New RefRule model. All with extra='forbid'. Encoded in default_workflow.toml for all 10 types reproducing today's semantics exactly. NOT yet consumed by the engine — behavior byte-identical.
  - **Part C — Fail-closed hardening**. extra='forbid' added to ALL workflow spec models (Lifecycle, ItemSpec, StatusSpec, RefRule, WorkflowSpec). Loader routes through model_validate, passing raw dicts so unknown TOML keys trigger the forbid. Unknown-key rejection tested both at model construction level and via _build_spec.
  - Gate results: full suite 0 failures (1 skip = wheel-build skip, pre-existing); all three golden-locks pass (workflow spec, role catalog, playbook); behavioral golden-locks byte-identical; pyright strict 0 errors; ruff clean. The workflow golden snapshot grew to include the new flag fields — the one legitimate change.
  - @manager ready for completeness gate before TASK-234 starts.
<!-- sq:discussion:end -->
