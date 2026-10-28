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
updated_at: '2026-10-27T21:05:28Z'
---
<!-- sq:body -->
## Context

The `AgentBackend` ABC (`src/squads/_backends/_base.py`) is 1.0 stability-contract material. It
carries six Claude-isms from its first backend (`claude_code`), catalogued CC-001..CC-006 under
TASK-131.

Three are cosmetic (docstring/comment only); three are structural (method names, a path-ownership
seam, and the registration story). Because the ABC freezes at 1.0, they are settled before the
freeze, without a migration. This decision rules on all six.

Constraints honoured: the import graph stays acyclic; nothing moves into `.squads.json` as a source of truth (Invariant 1); backends stay
pluggable and nothing outside a backend reaches into `.claude/` (Invariant 6).

## Decision

### CC-003 — The ABC entry-point methods are named `*_entry`, not `*_pointer` (STRUCTURAL)

The two entry points are `generate_role_entry` and `generate_skill_entry`.

"Pointer" is a Claude-Code file mechanic (a thin file that leads to the real definition). The
AGENTS.md backend has no pointers — it writes a section into one file. `entry` is neutral: the
Claude backend returns a pointer-file artifact, the AGENTS.md backend a section-update artifact, and
both return a single `Artifact`. `entry` (over `artifact`) keeps the name distinct from the
`Artifact` return type and reads well for "the role's/skill's entry in the agent surface". The
backends' own private helpers and their `Artifact.kind` strings (`"agent"`, `"skill_pointer"`, …)
are backend-internal vocabulary and keep Claude-shaped names where they are Claude's.

### CC-005 — Each backend owns the paths of its own root files (STRUCTURAL)

Chosen option: **the backend owns its own path resolution.** `SquadPaths` exposes only the generic
project root and names no harness; the Claude backend derives `.claude/` and `CLAUDE.md` from
`ctx.root` itself, from constants private to it, and the AGENTS.md backend composes `AGENTS.md` the
same way. Non-backend code — the init summary included — never names a backend's files; a caller
that needs to know what a backend wrote reads the `Artifact` list it returns.

Rejected: a registry hook declaring one "config file" path per backend over-generalises — backends
differ in *shape* (Claude has a directory and a markdown file; AGENTS.md has one root file).
Renaming the properties in place was rejected because keeping agent-config paths in the shared
module still lets non-backend code reach them, which is exactly the Invariant-6 leak this closes.

### CC-006 — Built-in backends are a literal registry table (STRUCTURAL)

`_backends/_registry.py` maps each built-in backend's name to its class in a literal table; adding a
backend is one row. There is no registration side effect on import and no entry-points plugin
discovery (ADR-1128). Plugin discovery adds packaging machinery and import-time surprise for no
current benefit, and the literal table is simpler, fully type-checked, and trivially extensible.

### CC-001 / CC-002 / CC-004 — Backend-neutral wording (COSMETIC)

The ABC's comments and docstrings describe backend-neutral behaviour:

- CC-001 — `Artifact.kind` is documented as a backend-specific category (e.g.
  `agent | skill | config | index`), not a list of Claude's file kinds.
- CC-002 — `write_managed` (re)writes roster- and version-dependent files: the managed skill
  definitions and the backend's project-level config section, not "the CLAUDE.md section".
- CC-004 — `BackendContext.rel` / `root_relative` are path helpers for `Artifact` paths and
  backend-owned file references, not "for pointers".

The `Artifact.kind` values a backend produces are not part of the ABC — `kind` is backend-specific
vocabulary.

## Consequences

- The ABC surface that freezes at 1.0 is backend-neutral in both names and docstrings; the
  AGENTS.md backend implements it without inheriting Claude file mechanics.
- `SquadPaths` is harness-free; path ownership for agent-surface files sits inside each backend,
  which is what Invariant 6 requires.
- Adding a backend is the backend itself plus one row in the registry table.
- The method names and the path seam are part of the stability contract's backend surface.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T21:36:44Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten from edit instructions to the decision as it stands. CC-003 and CC-005 hold. For CC-006, the `register()` self-registration hook no longer exists: the registry is a literal table (ADR-1128). Dropped the line-number edit lists and the verification-gate step.
- [2026-10-27T21:05:28Z] `architect` Robert Architect:
  - Removed the test-suite clauses (op-pierre ruling 2026-10-27, FEAT-1096); the decision is unchanged.
<!-- sq:discussion:end -->
