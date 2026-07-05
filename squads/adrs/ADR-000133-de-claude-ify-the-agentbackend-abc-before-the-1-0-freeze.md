---
id: ADR-133
sequence_id: 133
type: decision
title: De-Claude-ify the AgentBackend ABC before the 1.0 freeze
status: Accepted
author: architect
priority: high
refs:
- FEAT-16
- TASK-131
description: Rename generate_*_pointer→generate_*_entry, move claude_dir/claude_md
  ownership into the Claude backend, and register built-in backends via an explicit
  import list. Apply CC-001/002/004 cosmetics alongside.
created_at: '2026-06-15T13:16:56Z'
updated_at: '2026-06-15T13:18:11Z'
---
<!-- sq:body -->
## Context

The `AgentBackend` ABC (`src/squads/_backends/_base.py`) is 1.0 stability-contract
material (flagged on FEAT-13). The conformance suite written under TASK-131
(`tests/test_backend_conformance.py`) exercised the contract against the only existing
backend (`claude_code`) and surfaced six Claude-isms, catalogued CC-001..CC-006 in the
comment at the bottom of TASK-131 and in the suite footer.

Three are cosmetic (docstring/comment only); three are structural (method names, a
path-ownership seam, and the registration story). Because the ABC freezes at 1.0, this
is the last clean window to fix the structural items without a migration. This ADR rules
on all six so the developer can apply them mechanically with no further design calls.

Constraints honoured: import graph stays acyclic; the conformance suite must stay green
for `claude_code`; nothing moves into `.squads.json` as a source of truth (Invariant 1);
backends stay pluggable and nothing outside a backend reaches into `.claude/` (Invariant 6).

## Decision

Accepted. Apply all six. Mechanical changes per item below.

### CC-003 — Rename the ABC entry-point methods (STRUCTURAL)

Rename, on `AgentBackend` and everywhere it is referenced:

- `generate_role_pointer`  →  `generate_role_entry`
- `generate_skill_pointer`  →  `generate_skill_entry`

Rationale: "pointer" is a Claude-Code file mechanic (a thin file that @-includes the real
definition). A future AGENTS.md backend has no pointers — it writes a section into one
file. `entry` is neutral: a Claude backend returns a pointer-file artifact, an AGENTS.md
backend returns a section-update artifact, both still return a single `Artifact`.
`entry` (over `artifact`) keeps the name distinct from the `Artifact` return type and
reads well for "the role's/skill's entry in the agent surface". Signatures are otherwise
unchanged.

Exact edits (rename only — no behaviour change):

1. `src/squads/_backends/_base.py` — rename the two `@abstractmethod` defs (the
   `_pointer` → `_entry` suffix). Also update their docstrings to drop "thin pointer
   file" wording, e.g.
   - role: `"""Write the backend's entry for a role (loads the role's real definition)."""`
   - skill: `"""Write the backend's entry for a skill (loads the skill's real definition)."""`
2. `src/squads/_backends/_claude_code/_backend.py` — rename the two concrete method defs
   (lines 181, 200). The Claude impl bodies are unchanged: it still writes `.claude/`
   pointer files and returns the same `Artifact`s. The Claude backend's own private
   helpers and the `"agent"`/`"skill_pointer"` Artifact.kind strings stay as-is (those are
   legitimately Claude-internal vocabulary).
3. Update all call sites to the new names:
   - `src/squads/_services/_items.py` lines 169, 171
   - `src/squads/_services/_roster.py` lines 49, 74, 105
   - `src/squads/_services/_maintenance.py` lines 85, 88
4. `tests/test_backend_conformance.py` — rename every `generate_role_pointer` /
   `generate_skill_pointer` call (the `TestGenerateRolePointer` / `TestGenerateSkillPointer`
   test methods and the round-trip test) to the new names. The class names and the
   section-header comments may be renamed to match (e.g. `TestGenerateRoleEntry`) but that
   is optional polish; the call rename is mandatory for the suite to compile.
5. Any other test that calls these methods directly — none found outside the conformance
   suite (service-layer tests go through `sync`/roster commands, which are covered by 3).

This is a pure mechanical rename: grep for `generate_role_pointer` and
`generate_skill_pointer` across `src/` and `tests/` and replace all occurrences. No
caller passes these by string/getattr, so the rename is complete once grep is clean.

### CC-005 — Path-ownership seam: backend owns its own root files (STRUCTURAL)

Chosen option: **A (backend owns its own path resolution), refined.** The Claude-specific
properties leave the shared `SquadPaths`; `SquadPaths` exposes only the generic project
root. The Claude backend derives `.claude/` and `CLAUDE.md` from `ctx.root` itself.

Rejected: Option B (a registry hook for a declared "config file" path) over-generalises —
backends differ in *shape* (Claude has a dir + a markdown file; AGENTS.md has one root
file), so a single declared path doesn't fit; defer that abstraction until the second
backend actually exists. Option C (rename-in-place) was rejected because keeping
agent-config paths in the shared module still lets non-backend code reach them, which is
exactly the Invariant-6 leak we are closing.

Exact edits:

1. `src/squads/_paths.py` — delete the `claude_dir` and `claude_md` properties (lines
   ~65-72, including the `# --- claude integration (project-level) ---` comment). Update
   the `root` field comment on `SquadPaths` (line 43) to drop the `CLAUDE.md, .claude/`
   enumeration, e.g. `root: Path  # project root (holds .squads.toml)`.
2. `src/squads/_backends/_claude_code/_backend.py` — add two module-level constants and
   resolve the paths locally from `ctx.root`:
   - constants near the existing `_AGENTS` block:
     `_CLAUDE_DIR = ".claude"` and `_CLAUDE_MD = "CLAUDE.md"`.
   - replace every `ctx.paths.claude_dir` with `(ctx.root / _CLAUDE_DIR)` and every
     `ctx.paths.claude_md` with `(ctx.root / _CLAUDE_MD)`. Occurrences: lines 31, 98, 99,
     110, 182, 202, 219, 223. Prefer a single local `cdir = ctx.root / _CLAUDE_DIR` at the
     top of each method that uses it more than once (`ensure_scaffold` already does this —
     extend the pattern), to keep the diff readable.
   `BackendContext.root` already exposes `self.paths.root`, so no new context plumbing is
   needed and no import edge is added (the backend already imports from `_paths` only via
   the `SquadPaths` type on `BackendContext`; that stays). Import graph unchanged.
3. `src/squads/_cli/_main.py` line 185 — this is the one non-backend reader of
   `sp.claude_dir` (the init summary panel), and an existing Invariant-6 leak. Fix it
   without re-introducing the property: drop the path from the line and keep it
   backend-neutral, e.g.
   `lines.append("[bold]agent backend:[/bold] " + sp.config.default_backend + " (pointers + squads skill + CLAUDE.md)")`.
   Do **not** add a back-channel from the CLI into the backend's private path constants;
   the init summary is cosmetic and the backend name is sufficient. (If a future backend
   wants to advertise the exact files it wrote, the `Artifact` list returned by
   `ensure_scaffold`/`write_managed` is the proper seam — out of scope here.)
4. Tests reading `project.claude_dir` / `project.claude_md` / `svc.paths.claude_dir`:
   `tests/test_backend_claude.py`, `tests/test_service.py`, `tests/test_skills.py`,
   `tests/test_operators.py`, `tests/test_agent_naming.py`. These are Claude-backend tests
   asserting Claude file layout — that is legitimate (they test the concrete backend, not
   the ABC). Replace the helper access with direct root composition: define a tiny local
   helper or inline `project.root / ".claude"` and `project.root / "CLAUDE.md"` (whatever
   the `project`/`svc` fixture exposes for the root — they already have `.root`). Keep the
   assertions themselves unchanged. The conformance suite (`test_backend_conformance.py`)
   must NOT gain any `.claude`/`CLAUDE.md` reference — it stays backend-neutral and keeps
   reaching only through `ctx.root / artifact.path`.

Net effect: `SquadPaths` no longer names Claude anywhere; the only code that knows about
`.claude/` and `CLAUDE.md` is the Claude backend (and its dedicated tests). A future
AGENTS.md backend composes `ctx.root / "AGENTS.md"` the same way, owning its own root file
cleanly. Invariant 6 restored.

### CC-006 — Backend registration: explicit built-in import list (STRUCTURAL)

Chosen mechanism: **explicit import list in the registry** for built-in backends; keep the
existing `register()` decorator/function as the self-registration hook that third-party
backends call on import. Reject entry-points plugin discovery for 1.0: it adds packaging
machinery and import-time surprise for zero current benefit (one backend, a second
in-tree); the explicit list is simpler, fully type-checked, and trivially extensible. We
can layer entry-points discovery on later without changing the `register()` contract — so
this choice is not a dead end.

Exact edits:

1. `src/squads/_backends/_registry.py` — replace the single hard-coded
   `importlib.import_module("squads._backends._claude_code")` inside `get_backend` with a
   module-level tuple of built-in backend module paths and a one-shot loader that imports
   them all (so adding a backend = one line). Concretely:
   - add a module-level constant:
     `_BUILTIN_BACKEND_MODULES = ("squads._backends._claude_code",)`
   - add a private idempotent loader that imports each module in the tuple for its
     `register()` side-effect (guard with a module-level `_loaded` flag so repeated
     `get_backend` calls don't re-import), and call it at the top of `get_backend` in
     place of the current inline import.
   - keep `register()` and `_REGISTRY` exactly as they are; third-party backends still
     self-register by being imported and calling `register(MyBackend)`.
   When the AGENTS.md backend lands (TASK-132), registering it is a single tuple entry:
   `("squads._backends._claude_code", "squads._backends._agents_md")`.
2. No change to `_backends/_claude_code/__init__.py` — it already calls
   `register(ClaudeCodeBackend)` on import, which is exactly the contract the import list
   relies on. Keep it.
3. Import graph: the registry imports backend *packages by string at call time* (not at
   module top level), so no new static import edge is introduced and no cycle is possible.

### CC-001 / CC-002 / CC-004 — Cosmetic (IN SCOPE, apply alongside)

These need no design decision and SHOULD ship in the same change so the ABC is internally
consistent after the rename:

- CC-001 — `src/squads/_backends/_base.py` line 18: change the `Artifact.kind` comment
  from `# agent | skill | settings | claude_md` to a backend-neutral example, e.g.
  `# backend-specific category, e.g. agent | skill | config | index`.
- CC-002 — `_base.py` `write_managed` docstring (line ~73): replace
  "…the skill + CLAUDE.md section." with backend-neutral wording, e.g.
  "(Re)write roster/version-dependent files: the managed skill definitions and the
  backend's project-level config section."
- CC-004 — `_base.py` `BackendContext.rel` / `root_relative` docstrings (lines ~53-59):
  drop "for pointers"; e.g. rel → "Project-root-relative, forward-slash path (for
  Artifact paths and backend-owned file references)." and root_relative → "Root-relative
  path to an item's markdown file (for backend-owned file references)."

The `Artifact.kind` string values produced by the Claude backend (`"settings"`,
`"claude_md"`, `"skill_pointer"`, `"agent"`, `"skill_body"`) are NOT part of the ABC and
stay unchanged — `kind` is documented as backend-specific vocabulary and the conformance
suite only asserts it is non-empty.

## Consequences

- The ABC surface that freezes at 1.0 is backend-neutral in both names and docstrings; a
  second backend can implement it without inheriting Claude file mechanics.
- `SquadPaths` is Claude-free; path ownership for agent-surface files sits inside each
  backend, restoring Invariant 6 (incl. fixing the pre-existing `_cli/_main.py` leak).
- Adding a backend is a one-line registry edit plus the backend's own `register()` call.
- Verification gate after applying: `uv run pyright && uv run ruff check . &&
  uv run ruff format --check . && uv run pytest` — the conformance suite must stay green
  for `claude_code` and the Claude-backend tests must still assert Claude layout via
  `ctx.root` composition.
- Stability-contract note (do NOT file as a separate item): these ABC method renames and
  the path-seam change are a FEAT-13 stability-contract deferral — they are exactly the
  kind of pre-1.0 contract settling FEAT-13 was flagged to absorb. Reflect them there
  once the change is merged; no new sub-entity needed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
