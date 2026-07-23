---
id: TASK-636
sequence_id: 636
type: task
title: 'Import event model: schema, handles, validate-first pre-pass'
status: Done
parent: FEAT-576
author: tech-lead
refs:
- ADR-622:implements
description: JSONL event schema + parser, handle to id resolution map, and the validate-first
  pre-pass that resolves handles, simulates allocation, and validates every event
  collecting ALL errors, writing nothing.
created_at: '2026-07-23T13:29:36Z'
updated_at: '2026-07-23T14:51:00Z'
---
<!-- sq:body -->
Implements the read/validate half of the bulk-import mechanism defined in ADR-622 (Event schema, Addressing, and the "Validate-first, then apply" section). This task builds the model, parser, handle map, and the pre-pass; it writes nothing. The apply half is a separate task; the CLI is a separate task.

## Scope

**Event model (ADR-622 "Event schema" + "The v1 op set").** A JSONL stream, one JSON object per line. Common fields on every event: `op` (required), `at` (optional ISO-8601 UTC), `as` (optional acting slug). Model the v1 op set exactly and no more: `create`, `status`, `body`, `comment`, `ref`, `add-story`/`add-subtask`/`add-finding` (ergonomic fronts over the generic `add-sub` with an explicit `kind`), `sub-status`, `sub-body`, `assign`, `update`. Per-op fields are enumerated in the ADR's "v1 op set" list — model those fields, nothing invented. Parse into typed pydantic models (a discriminated union on `op` is the natural shape). Track line numbers on every parsed event so downstream error reporting can cite them.

**Inheritance of `at`/`as`.** An event with no `at`/`as` inherits the previous event's value, falling back to the file-level default (supplied by the CLI task). This is pure model/pre-pass bookkeeping here — resolve each event's effective `at`/`as` during the pass.

**Handle resolution (ADR-622 "Addressing: client-supplied handles").** A creating op (`create`, `add-story`/`add-subtask`/`add-finding`) may carry `"handle"`. Build a `handle -> allocated-id` map (and, for sub-entities, `handle -> (parent-id, local-id)`). Any later event's `target`/`to`/`parent`/`story` resolves against the handle map first, then falls back to a literal existing ID. Handles unify item and sub-entity addressing.

**Validate-first pre-pass (ADR-622 "Atomicity, validation, idempotency").** Resolve every handle, **simulate** ID allocation (never touch the real counter here), and check every event against the active spec, collecting **ALL** errors (not just the first) before reporting:
- a creating op precedes any event that targets it (file order is authoritative — do NOT reorder by `at`);
- `type`/`status` vocabulary valid for the active spec;
- transition legality (same workflow gate the interactive `status` verb uses);
- parent eligibility (`ALLOWED_PARENTS`/`parent_allowed`);
- ref kinds valid (`VALID_REF_KINDS`, forward edge only);
- actor (`as`) registered (role or operator);
- marker-safety of every prose field (`body`/`comment`/`sub-body`) — the same marker-rejection guard the section helpers apply, so an imported body can never carry a raw `<!-- sq:* -->` tag.

Each error carries its line number and a human message. The pass returns a structured result (resolved `handle -> id` plan, per-op counts, ordered error list) that both `--dry-run` and the apply task consume — it does NOT print or exit itself.

Optional `--check-monotonic` advisory (non-decreasing `at`) may be modelled here but NEVER reorders — leave the CLI flag wiring to the CLI task if cleaner.

## Where it plugs in

- Reuse `_workflow.can_transition`/`ALLOWED_PARENTS`, `_models/_item.split_ref` + `VALID_REF_KINDS`, the spec vocab (`_models/_vocab`), and the registered-slug set (`registered_slugs` in `_services/_validators.py`) rather than re-deriving any of them.
- Simulated allocation mirrors `db.allocate_id`'s formatting/counter bump against an in-memory copy — do NOT open a transaction or bump the real counter (invariant #2: allocate only inside a real transaction, which is the apply task's job).
- Put the model + pre-pass in a new private module (e.g. `_services/_import.py` or a small `_import/` subpackage) below the CLI; keep the import graph acyclic.

## Conventions (must hold)
- No status/lifecycle prose in any body/docstring. Category is "roster", never "meta". No ticket/sq IDs in source or test names — name by behaviour. PEP-695 `type` aliases (`type X = …`), never bare assignment. Errors subclass `SquadsError`. Marker-safe reasoning only. Time via `clock`/the context seam, never `datetime.now()`.
- Honor invariants: frontmatter is source of truth; one global counter (simulate only here); forward edges only.

## Testing / gates
- Run gates with `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`.
- If you add ANY module-level constant, run `tests/meta` — the mutable-state guard trips on new module-scope mutable globals.
- Add a service-level test (feed JSONL, assert the pre-pass collects every seeded error with correct line numbers, and that a clean file yields the right `handle -> id` plan) — cover each error class at least once. A CLI smoke test belongs to the CLI task.
- Run `uv run sq check` before finishing.

## Sizing
This is one of the two sizable core tasks (with the apply task). Do NOT fold apply, the CLI, or docs into it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 636 add-subtask "<title>"`; track with `sq task 636 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T14:30:31Z] Elias Python:
  - Event model + validate-first pre-pass done. JSONL discriminated-union pydantic model (_services/_import_model.py): create/status/body/comment/ref/add-sub(+ add-story/add-subtask/add-finding ergonomic fronts)/sub-status/sub-body/assign/update, common at/as with inheritance, line-tracked parse (bad JSON/unknown op never aborts the pass, becomes a collected issue). Pre-pass (_services/_import.py ImportMixin._plan_import) runs against a throwaway deep-copied SquadsDB — never the real store/transaction — reusing the interactive mixins' existing PURE _X_model methods (parent/author/assignee checks, status transitions, ValidatorEngine.gate) plus HandleMap resolution (item + sub-entity handles) and marker-safety, catching SquadsError/pydantic ValidationError per event and continuing. Simulated id allocation via the shadow copy's own db.allocate_id (never the real counter). Gate result group ImportPlan (op_counts/handle_to_id/handle_to_sub/issues).
  - Also fixed a latent reflog bug this design surfaces: IndexStore buffered ops used to snapshot actor/clock ONCE at flush time, wrong once a single transaction spans several ambient-actor rebinds (bulk import); each _log() call now snapshots ts/actor/session at buffer time (behavior-identical for every existing single-op transaction — full suite stayed green).
  - Tests: tests/service/test_bulk_import_engine.py — prepass error-collection test seeds all 6 ADR-listed error classes (bad type, bad status vocab, illegal transition, dangling parent, unregistered actor, bad ref kind) in one file and asserts every line surfaces, nothing written. Gates green: pyright/ruff (repo-wide) + targeted suite + tests/meta.
<!-- sq:discussion:end -->
