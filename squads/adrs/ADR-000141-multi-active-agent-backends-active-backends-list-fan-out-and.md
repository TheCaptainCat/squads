---
id: ADR-141
sequence_id: 141
type: decision
title: 'Multi-active agent backends: active_backends list, fan-out, and the check-present
  rule'
status: Accepted
author: architect
refs:
- FEAT-138
- TASK-139
- TASK-140
- FEAT-16
- ADR-133
- FEAT-137
- ADR-541
description: 'Replace singular default_backend with active_backends: list[str]; fan-out
  over all active backends; stays on schema 0.3 with NO bump — a legacy default_backend
  is read transparently as a one-element list (no migration runner); present-only
  sq check via a new read-only managed_paths ABC probe'
created_at: '2026-06-16T09:44:28Z'
updated_at: '2026-10-25T21:36:45Z'
---
<!-- sq:body -->
## Context

A squad may maintain several agent backends at once (e.g. both `CLAUDE.md` and `AGENTS.md`), so
`.squads.toml` names a list of active backends rather than one default backend. This is the config
shape the stability contract freezes at 1.0. ADR-133 made the `AgentBackend` ABC backend-neutral,
so the two built-in backends are symmetric enough to run side by side. This decision resolves
FEAT-137's single-vs-multiple question in favour of **multiple active backends** and fixes the
mechanics: the config model, fan-out, the init surface, the `sq check` rule, and deactivation.

Two facts from the code ground the rulings below:

- **The built-in backends write disjoint file sets.** `claude_code` owns `CLAUDE.md`, the `.claude/`
  pointers and settings; `agents_md` owns `AGENTS.md` and its staging files. **No two backends write
  the same path.**
- **`sq check` must be read-only**, but `ensure_scaffold` and `write_managed` *write*. Checking that a
  backend's files are present needs a pure probe.

## Decision

### 0. Config model & TOML shape

- `SquadsConfig.active_backends: list[str]`, defaulting to `["claude_code"]` (`_models/_config.py`).
  `[]` is valid: an empty list is a legal value (a sq-only squad), not a misconfiguration.
- `to_toml()` emits a TOML array: `active_backends = ["claude_code", "agents_md"]` (or
  `active_backends = []`).

### 1. No schema bump — back-compat by transparent read

`active_backends` needs no schema change and no migration runner. Back-compat for the legacy singular
`default_backend` key is a **tolerant read** in `from_toml_dict`, never a rewrite of files on disk:

- `default_backend = "X"` (any non-empty string) is read as `active_backends = ["X"]`.
- **Missing or empty `default_backend`** is read as **`active_backends = ["claude_code"]`**, not `[]`.
  An absent key meant "fell back to the default", i.e. claude_code was active, so the faithful read
  preserves that. `[]` (sq-only) is a **deliberate** choice an operator makes explicitly (`sq init
  --backend none`), so an existing agent-file-bearing squad is never silently turned into a sq-only
  one (that would orphan a `CLAUDE.md` the user relies on). **Empty is reachable only by intent,
  never implicitly.**
- If `active_backends` is present, it is used as-is and a present `default_backend` is discarded.
  The read is idempotent.

### 2. Order & dedup

- **Order is not significant.** Because the backends write **disjoint** paths, fan-out order can
  never change the bytes on disk; code must not rely on it. Should a future backend ever overlap
  another's path, that collision is a backend design bug, not a config-order semantic —
  `active_backends` order is explicitly not a last-writer-wins tiebreak.
- **De-duplicate on read, preserving first-occurrence order.** `["claude_code", "claude_code"]` is
  treated as `["claude_code"]`: a repeated entry is a no-op, not an error. A field validator on the
  model does it, and **every consumer iterates the deduped list**.
- **Unknown backend names** surface as the registry's `SquadsError` when fan-out resolves them (a
  hand-corrupted config). No further validation is mandated here.

### 3. init / adopt → list

- **`sq init`/`sq adopt` take a repeatable `--backend` option**, defaulting to `["claude_code"]`
  when omitted, which seeds `active_backends` directly:
  - `sq init` → `["claude_code"]`.
  - `sq init --backend claude_code --backend agents_md` → `["claude_code", "agents_md"]`.
  - **`sq init --backend none`** → `active_backends = []` (the sq-only squad). The literal token
    `none` (case-insensitive) is the sentinel for "no backends"; combining it with a real backend
    name is a `SquadsError`.
- This is the **minimal seed grammar**. Lifecycle management of the list on an existing squad is
  FEAT-137's.
- The init summary lists the active backends, or `(none)`.

### 4. The `sq check` rule — "managed files present"

- **The read-only ABC probe:**

  ```python
  @abstractmethod
  def managed_paths(self, ctx: BackendContext) -> list[str]:
      """Root-relative paths this backend OWNS and that sq check expects to exist.
      Read-only: must not create or modify any file."""
  ```

  Each backend returns the root-relative paths of its fixed top-level managed files, **without
  writing them** — the files whose absence means this backend was never scaffolded or synced. For
  `claude_code` that includes `CLAUDE.md` and `.claude/settings.json`; for `agents_md`, `AGENTS.md`.

- **The `backend_reconciled` rule** (a squad-global validator in `_services/_validators.py`, ADR-541):
  for **each active, deduped backend**, every `managed_paths` entry that does not exist on disk is a
  finding naming the path and `sq sync`, reported at **error** by default.
  - **Empty `active_backends = []` → no check fires** (nothing to verify; a sq-only squad is clean).
  - **Deactivated backends are not checked** — only names currently in `active_backends` are probed,
    so a removed backend's lingering files are neither verified nor flagged.

- **Present, not current.** `sq check` proves scaffolding exists; it does not re-render a backend's
  content and diff it (expensive, and `write_managed` is not idempotent-by-diff). `sq sync` is the
  tool that refreshes content. A currency check can be added later without a config change, so it
  is not frozen at 1.0.

- **Why a probe on an ABC about to freeze:** the ABC has no other read-only way to ask a backend
  which files it owns, and reusing `ensure_scaffold`/`write_managed` would make `check` mutate the
  tree. `managed_paths` is the smallest possible addition: one pure method, returning data the
  backend already knows, covered by the conformance suite ("read-only, and its paths exist after a
  sync").

### 5. Deactivation = ignore, not delete

Removing a backend from `active_backends` leaves its on-disk files **untouched**; `sync` stops
refreshing them and `check` stops probing them (§4). Active removal and cleanup of a backend's files
is FEAT-137's.

## Consequences

- **Invariants honoured.** Backends stay pluggable (Inv 6) — fan-out goes through the ABC and the
  registry, never reaching into `.claude/` directly. Nothing new lands in `.squads.json`
  (`active_backends` lives in `.squads.toml`, the durable config). `managed_paths` is implemented by
  both backends, so the parametrized conformance suite covers both.
- **Every backend-touching path fans out**: scaffold, managed-file refresh and `sync` iterate the
  deduped active list, and an empty list is a clean no-op everywhere.
- **The 1.0 contract freezes** the `active_backends: list[str]` shape — including empty `[]`
  (sq-only) and deactivation-ignore semantics — as part of the durable `.squads.toml` surface, with
  the present-only check rule and the `none` init sentinel.
- **Forward door left open:** a currency check and backend-management commands can be added later
  without touching the frozen shape.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T12:43:45Z] `manager` Catherine Manager:
  - Override (op-pierre, 2026-06-16): ADR-141's 0.3→0.4 schema bump + _v0_3_to_v0_4 migration are NOT applied — 0.3 is still in development, so active_backends is part of 0.3 with no version bump and no migration; the config reads legacy default_backend transparently. All other ADR-141 rulings stand and are implemented (list shape, dedup, order-insignificance, repeatable --backend + none sentinel, present-only check via the managed_paths probe).
- [2026-06-17T08:39:11Z] `architect` Robert Architect:
  - Corrected the stale 0.3→0.4 migration framing in this ADR's body to the shipped no-bump reality (mirrors the FEAT-138 correction in commit 6538396). Title and summary no longer claim a migration; §1 was rewritten from 'Migration mapping (SCHEMA 0.3 → 0.4)' to 'No schema bump — back-compat by transparent read (no migration)'; the Context sentence about TASK-139 making 'no further design calls' was reframed; added a Correction note. Verified against code: SCHEMA_VERSION stays 0.3, no _v0_3_to_v0_4 runner, no to_schema=0.4 in the registry, and _config.py reads legacy default_backend transparently as a one-element active_backends list. The decision itself was implemented and stands; only the abandoned migration mechanics were corrected. Status kept Accepted. TASK-139 confirmed Cancelled. sq check clean.
- [2026-08-03T08:51:17Z] `architect` Robert Architect:
  - Citation refreshed, every ruling verified unchanged. The `sq check` rule moved rather than changed: `_check_backends` is now the named pluggable validator `_backend_reconciled` in `_services/_validators.py` (ADR-541s validator framework), and its docstring records the old name. Behaviour intact — one error per missing `managed_paths` entry per active deduped backend, no check at all for an empty `active_backends`, deactivated backends not probed. Also confirmed live: dedup validator, tolerant legacy `default_backend` read, TOML array, repeatable `--backend`, and the `none` sentinel with its combination refusal. Section 1s "SCHEMA_VERSION stays 0.3" reads as history; the claim it was making is "this decision requires no schema change". `related` edge added to ADR-541.
- [2026-10-25T21:36:45Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Removed the Decision status, Correction and Amendment sections, the TASK-139/140 and line-number references, and 'SCHEMA_VERSION stays 0.3'. The check is the `backend_reconciled` validator, error by default.
<!-- sq:discussion:end -->
