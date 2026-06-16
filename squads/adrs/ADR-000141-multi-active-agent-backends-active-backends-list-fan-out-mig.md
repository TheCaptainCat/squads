---
id: ADR-000141
sequence_id: 141
type: decision
title: 'Multi-active agent backends: active_backends list, fan-out, migration, and
  the check-present rule'
status: Accepted
author: architect
refs:
- FEAT-000138
- TASK-000139
- TASK-000140
- FEAT-000016
- ADR-000133
- FEAT-000137
description: 'Replace singular default_backend with active_backends: list[str]; fan-out
  over all active backends; SCHEMA 0.3->0.4 migration; present-only sq check via a
  new read-only managed_paths ABC probe'
created_at: '2026-06-16T09:44:28Z'
updated_at: '2026-06-16T12:43:45Z'
---
<!-- sq:body -->
## Context

The operator has decided to replace the singular `.squads.toml` `default_backend: str`
with **`active_backends: list[str]`**, so a squad can maintain several agent backends at
once (e.g. both `CLAUDE.md` and `AGENTS.md`). This is the schema shape FEAT-000013 will
**freeze at 1.0**, so it must be settled now. ADR-000133 already de-Claude-ified the
`AgentBackend` ABC, so the two backends are symmetric enough to run side by side. This ADR
resolves FEAT-000137's OQ-2 (single-vs-multiple active) in favour of **multiple-active** and
fixes the exact mechanics so TASK-000139 (schema + migration) and TASK-000140 (config model +
runtime fan-out + check) need make no further design calls.

The decision (replace the singular field; multi-active; empty `[]` valid; check verifies
active backends present; deactivation = ignore-not-delete) is **already made** — this ADR makes
it precise and implementable. Two facts established from the code grounded the rulings below:

- **The two built-in backends write disjoint file sets.** `claude_code` owns `CLAUDE.md`,
  `.claude/` pointers, and skill bodies under `<squad>/agents/skills/`; `agents_md` owns
  `AGENTS.md` and `.agents_md/` staging. **No two backends write the same path.**
- **The ABC has no "are my managed files present?" probe.** `ensure_scaffold` and
  `write_managed` already *return* `list[Artifact]` whose `.path` is each managed file —
  but they *write*. `sq check` must be read-only, so it needs a pure probe.

## Decision

### 0. Config model & TOML shape

- `SquadsConfig.default_backend: NonEmpty = "claude_code"` becomes
  **`active_backends: list[str] = ["claude_code"]`** (`_models/_config.py`). `[]` is valid.
- `to_toml()` emits a TOML array: `active_backends = ["claude_code", "agents_md"]` (or
  `active_backends = []`). `from_toml_dict` reads it as a list. The field is **no longer
  `NonEmpty`** — empty is a legal value, not a misconfiguration.
- `[init.names]` and all other fields are unchanged.

### 1. Migration mapping (SCHEMA 0.3 → 0.4)

- **Bump `SCHEMA_VERSION` `"0.3"` → `"0.4"`** in `_models/_schema.py` (single source of truth;
  compare via `schema_tuple`, never raw string).
- **New runner `_migrations/_v0_3_to_v0_4.py`** with `migrate(paths) -> int` + `MANUAL = ""`
  (fully automatic), registered in `_migrations/_registry.py::MIGRATIONS` as
  `Migration(version="0.4.0", from_schema="0.3", to_schema="0.4", summary="…", run=…, manual="")`.
  It rewrites **`.squads.toml` only** (not item frontmatter); the returned `int` is the count of
  config files rewritten (0 or 1 for a normal squad).
- **Mapping rule — be literal about the source key:**
  - `default_backend = "X"` (any non-empty string) → `active_backends = ["X"]`.
    In practice the only real value in the wild is `"claude_code"` → `["claude_code"]`.
  - **Missing or empty `default_backend`** in an old squad → **`active_backends = ["claude_code"]`**,
    NOT `[]`. Rationale: pre-0.4 there was no way to express "sq-only"; every 0.3 squad had a
    backend, and the model default was `"claude_code"`. An absent key meant "fell back to the
    default", i.e. claude_code was active — so the faithful migration preserves that behaviour.
    `[]` (sq-only) is a *new, deliberate* post-migration choice an operator makes explicitly via
    FEAT-000137's management commands; the migration must never silently turn an existing
    agent-file-bearing squad into a sq-only one (that would orphan a `CLAUDE.md` the user relies
    on). **Empty is reachable only by intent, never by migration.**
  - If `active_backends` is already present (idempotent re-run / hand-edited), leave it untouched.
- **Corpus fixture (FEAT-000017 standing rule, `tests/fixtures/corpus/README.md`):**
  1. Copy current `v0_3` → new `v0_4` (the new *current* schema), stamp its `.squads.toml`
     `schema_version = "0.4"` and replace `default_backend = "claude_code"` with
     `active_backends = ["claude_code"]`.
  2. **Keep `v0_3` as the now-previous from-schema** — its `.squads.toml` must KEEP the singular
     `default_backend = "claude_code"` (it already does) so the new runner is actually exercised
     and not vacuous (REV-000130 lesson).
  3. Add `("0.3", "v0_3")` is already present; add `("0.4", "v0_4")` to `_CORPUS_CASES` in
     `tests/test_migration_corpus.py` and confirm
     `test_corpus_migrates_to_current_and_passes_check` is green for every entry.

### 2. Order & dedup

- **Order is NOT significant.** Because the built-in backends write **disjoint** paths, fan-out
  order can never change the bytes on disk. We do not promise ordered output and code must not
  rely on it. (Should a future backend ever overlap another's path, that collision is a backend
  design bug to resolve in the registry, not a config-order semantic — we explicitly decline to
  make `active_backends` order a last-writer-wins tiebreak.)
- **Dedup: de-duplicate on read, preserving first-occurrence order.** `active_backends =
  ["claude_code", "claude_code"]` is treated as `["claude_code"]`. A repeated entry is a no-op,
  not an error — running a backend's fan-out twice would just rewrite the same files, so silently
  collapsing duplicates is the least-surprising, safe choice. Implement as a small normalizer
  (a pydantic field validator or an `active_backends()` accessor that returns the deduped list);
  TASK-000140 picks the mechanism, but **every consumer iterates the deduped list**.
- **Unknown backend names** in the list: `get_backend()` already raises `SquadsError` for an
  unknown name. Fan-out resolving an unknown active backend surfaces that error — acceptable for
  1.0 (a hand-corrupted config). No new validation is mandated here.

### 3. init / adopt → list

- **`sq init`/`sq adopt` keep a single `--backend` Option, made repeatable** (Typer
  `list[str]`), defaulting to `["claude_code"]` when omitted. This seeds `active_backends`
  directly. Examples:
  - `sq init` → `["claude_code"]` (unchanged default behaviour).
  - `sq init --backend claude_code --backend agents_md` → `["claude_code", "agents_md"]`.
  - **`sq init --backend none`** → `active_backends = []` (the sq-only squad). The literal token
    `none` (case-insensitive) is the sentinel for "no backends"; it may not be combined with a
    real backend name (combining is a `SquadsError`).
- This is the **minimal seed grammar**; full lifecycle management (`sq backend add/switch/remove/
  list`) is FEAT-000137, post-1.0. `init`/`adopt` only need to populate the list.
- The `sq init` info line at `_cli/_main.py:185` that prints `config.default_backend` becomes
  `"agent backends: " + ", ".join(config.active_backends) or "(none)"`.

### 4. The `sq check` rule — "managed files present"

- **New ABC probe (minimal, read-only):**

  ```python
  @abstractmethod
  def managed_paths(self, ctx: BackendContext) -> list[str]:
      """Root-relative paths this backend OWNS and that sq check expects to exist.
      Read-only: must not create or modify any file."""
  ```

  Each backend returns the same root-relative paths its `ensure_scaffold`/`write_managed` would
  write, **without writing them**. For `claude_code` that is at least `CLAUDE.md` and the
  `.claude/settings` file; for `agents_md`, `AGENTS.md`. (Implementations may scope this to the
  always-present top-level files rather than every per-role pointer — the contract is "the files
  whose absence means this backend was never scaffolded/synced".)

- **`sq check` rule** (`_services/_maintenance.py::check`, a new `_check_backends` helper):
  for **each active (deduped) backend**, call `managed_paths(ctx)` and emit a
  **`CheckIssue("error", <path>, "managed file missing — run `sq sync`")`** for any path that does
  not exist on disk.
  - **Empty `active_backends = []` → no check fires** (nothing to verify; sq-only squad is clean).
  - **Deactivated backends are not checked** — only names currently in `active_backends` are
    probed, so a removed backend's lingering files are neither verified nor flagged.

- **Present-only for 1.0, not currency/drift.** The operator said "present", and present-only is
  the right scope: currency would require each backend to re-render its managed content and diff
  it (expensive, and `write_managed` is not idempotent-by-diff today). `sq sync` is the tool that
  refreshes content; `sq check` only proves scaffolding exists. (FEAT-000138's US1 prose mentions
  "and current" — this ADR **narrows that to present-only**; a drift check can be added later
  without a schema change, so it does not need to be frozen at 1.0.)

- **Why a new ABC method despite the about-to-freeze ABC:** the ABC has no read-only way to ask a
  backend which files it owns (`ensure_scaffold`/`write_managed` write). Reusing them in `check`
  would make check mutate the tree — unacceptable. `managed_paths` is the smallest possible
  addition: one pure method, returning data the backend already knows. It is added to BOTH
  built-in backends and to `tests/test_backend_conformance.py` (a new contract: "managed_paths is
  read-only and its paths exist after a sync"). Adding it now, pre-freeze, is exactly why this ADR
  runs before 1.0.

### 5. Deactivation = ignore, not delete

**Confirmed.** Removing a backend from `active_backends` leaves its on-disk files **untouched**;
`sync` stops refreshing them and `check` stops probing them (per §4). **No artifact cleanup belongs
in this feature.** Active removal/cleanup (`sq backend remove`) is the post-1.0 FEAT-000137 story.

## Consequences

- **Invariants honoured.** Backends stay pluggable (Inv 6) — fan-out goes through the ABC +
  registry, never reaching into `.claude/` directly. Nothing new lands in `.squads.json`
  (`active_backends` lives in `.squads.toml`, the durable config; the index stays rebuildable).
  Import graph stays acyclic. `managed_paths` is added to both backends so the parametrized
  conformance suite covers both.
- **`_backend()` (singular) → `active_backends()` (plural iterator)** in `_services/_base.py`;
  `scaffold_backend`, `refresh_managed`, and `sync`'s loop iterate the deduped active list.
  Empty list = a clean no-op everywhere (sq-only squad).
- **FEAT-000013 freeze obligation (noted, not filed here):** at 1.0 the stability contract must
  FREEZE the `active_backends: list[str]` shape — including empty-`[]` (sq-only) and
  deactivation-ignore semantics — as part of the durable `.squads.toml` surface. The
  present-only check rule and the `none` init sentinel are part of that surface.
- **Forward door left open:** a currency/drift check and `sq backend` management commands can be
  added later without touching the frozen schema shape.

## Decision status

Accepted (op-pierre's call; this ADR fixes the mechanics). `@python-dev` implements via
TASK-000139 (schema + migration + corpus) then TASK-000140 (config model + fan-out + init/adopt +
the `managed_paths` probe + check rule).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T12:43:45Z] Catherine Manager:
  - Override (op-pierre, 2026-06-16): ADR-141's 0.3→0.4 schema bump + _v0_3_to_v0_4 migration are NOT applied — 0.3 is still in development, so active_backends is part of 0.3 with no version bump and no migration; the config reads legacy default_backend transparently. All other ADR-141 rulings stand and are implemented (list shape, dedup, order-insignificance, repeatable --backend + none sentinel, present-only check via the managed_paths probe).
<!-- sq:discussion:end -->
