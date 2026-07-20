---
id: TASK-494
sequence_id: 494
type: task
title: scopes ref kind + role-skill preload resolver
status: Done
parent: FEAT-491
author: tech-lead
refs:
- ADR-492:implements
- BUG-490:fixes
description: Add scopes ref kind; service resolver unions system membership + inverted
  scopes edges into both role artifacts
subentities:
- local_id: ST1
  title: Resolve a role's preload set from system membership + scopes edges
  status: Done
  story: US3
created_at: '2026-07-20T08:59:18Z'
updated_at: '2026-07-20T09:56:26Z'
---
<!-- sq:body -->
## Scope

Introduce the data model and resolution that let a skill declare which roles preload it —
implementing ADR-492 Pillar 3's mechanism (the user-facing verbs land in the sibling
link/unlink task; this task is the foundation both it and full `sq sync` build on).

### 1. `scopes` ref kind

Add `scopes` to `VALID_REF_KINDS` (`_models/_item.py`). It is a first-class, reviewed addition
to the closed vocabulary — read "this skill scopes to that role". The edge is stored as a
forward edge on the **skill**: `SKILL.refs += ROLE-n:scopes` (reuses the `ID:kind` ref shape,
no new storage). `sq check` then treats it as a known kind and gets dangling-ref detection for
free.

### 2. Service-layer role→skill resolver

Keep `_interactions.skills_for_role(slug)` pure and index-blind (layering — it cannot see the
index). Add a **service-layer** resolver that, for a role `R`:

- takes system membership from `skills_for_role(R.slug)`, then
- unions in the inverted scope edges: `SquadsDB.backrefs(R.id)` filtered to skills whose ref to
  `R.id` carries kind `scopes` (backrefs is kind-agnostic, so the resolver filters by kind),
  mapped to their slugs,
- deduped, **system-first then scoped**; scoped skills in a deterministic order (lexical by
  slug) so output is stable.

### 3. Flow the resolved list to both role artifacts

The resolved list must drive **both** surfaces a role's preload set appears in, replacing the
direct `interactions.skills_for_role(role.slug)` call:

- the pointer `skills:` YAML (`generate_role_entry` in the Claude Code backend), and
- the role body `## Skills` section (rendered from the role item's `extra[skills]`).

Plumb it through `BackendContext` the way `skill_paths` already flows (e.g. a
`role_skills: dict[slug, list[str]]` map populated by `refresh_managed`); `generate_role_entry`
reads the resolved list from the context, falling back to `skills_for_role` when absent (the
backend must not import the index). Store the resolved list into the role item's
`extra[skills]` so the body renders it. Keep `extra[skills]` a pure re-derivable cache — it is
always recomputable from system membership + scopes edges, so `repair` needs no new logic.

## Acceptance

- With no scope edges, every role's resolved preload set is byte-identical to today's
  `skills_for_role` output (no behaviour change until a skill is scoped).
- A `SKILL → ROLE:scopes` edge causes that role's resolved set (pointer YAML **and** role body
  `## Skills`) to include the skill; unrelated roles are unchanged.
- `sq check` recognises `scopes` (no "unknown ref kind" warning) and flags a `scopes` edge to a
  non-existent/removed role as a dangling ref.
- The pointer YAML and the role-body `## Skills` list stay identical to each other for the same
  role.
- Tests: resolver unit (union/dedup/order; kind filtering), and a second-backend (AGENTS.md)
  consistency check proving the resolved list — not a direct `skills_for_role` call — is the
  source for both backends. Name tests by behaviour, not by ticket id.

## Code sites

- `src/squads/_models/_item.py` — `VALID_REF_KINDS`.
- `src/squads/_services/` — new resolver (service layer, has index access).
- `src/squads/_backends/_base.py` — `BackendContext` (new resolved-skills field).
- `src/squads/_backends/_claude_code/_backend.py` — `generate_role_entry` (consume the resolved
  list); `_services/_base.py::refresh_managed` / `_maintenance.py` (populate the context).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 494 add-subtask "<title>"`; track with `sq task 494 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Resolve a role's preload set from system membership + scopes edges | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Resolve a role's preload set from system membership + scopes edges

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a squad author, I want to scope a custom skill to one or more roles so exactly those agents preload it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
scopes ref kind + service resolver: for role R, union skills_for_role(R) with skills carrying R:scopes (kind-filtered backrefs), dedup system-first then scoped; the resolved list is the single source for both the pointer skills: YAML and the role body ## Skills (via BackendContext), consistent across backends.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T09:45:35Z] Elias Python:
  - Files: _models/_item.py (VALID_REF_KINDS += scopes); _services/_base.py (resolved_skills_for_role resolver + _role_skills_map + refresh_managed wiring); _services/_maintenance.py (sync() computes role_skills once, persists extra.skills via _refresh_role_skills_extra, builds a role-scoped BackendContext for generate_role_entry); _backends/_base.py (BackendContext.role_skills + resolved_skills_for() fallback); _backends/_claude_code/_backend.py + _backends/_agents_md/_backend.py (generate_role_entry consumes ctx.resolved_skills_for instead of calling skills_for_role directly); agents_md/role_entry.md.j2 (renders the Skills list so the second-backend consistency is testable).
  - Resolver: skills_for_role(slug) unioned with backrefs(role.id) filtered to the scopes kind (ref_id_matches + split_ref), mapped to skill slugs, deduped system-first then lexical-scoped-tail. Carrier: BackendContext.role_skills: dict[slug, list[str]], with resolved_skills_for(slug) falling back to the pure skills_for_role when the map has no entry for that slug (bare/pre-resolver ctx sites, e.g. activate_role/add_dev) — no behaviour change with zero scope edges.
  - Gates: pyright + ruff check/format clean; tests/meta -q: 23 passed; targeted -k 'skill or scope or role or backend or sync': 274 passed; sq check clean (pre-existing 'managed files at 0.10.0' banner confirmed present before this task's changes via git stash). No ticket IDs in the diff.
  - @manager ready for review.
- [2026-07-20T09:54:44Z] Elias Python:
  - F1 fixed: _services/_base.py — split resolved_skills_for_role into a pure _resolve_role_skills(slug, role, db) core (no I/O) plus a thin standalone wrapper that loads the index once. _role_skills_map now loads the index once and builds every role's resolved list from that single db snapshot (mirrors _skill_paths's single-load shape) instead of calling resolved_skills_for_role per role — sync goes from 1+2N index parses to 2 total (one in _role_skills_map, one earlier in the ensure_scaffold pass). resolved_skills_for_role(slug) still works standalone (e.g. for the future link-hook path) with one load, not two.
  - Output unchanged: system-first, sorted scoped tail, kind-filtered — same tests pass unmodified.
  - Gates: pyright clean, ruff check/format clean, tests/meta -q: 23 passed, tests -k 'scope or role or backend or sync' -q: 231 passed, sq check clean.
  - @manager fix applied, ready for re-review.
<!-- sq:discussion:end -->
