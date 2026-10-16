---
id: MILE-1061
sequence_id: 1061
type: milestone
title: squads 0.18 - more backends
status: Draft
author: product-owner
description: Codex, Cursor and other agent backends, with a role's model held per
  backend
created_at: '2026-10-16T13:39:05Z'
updated_at: '2026-10-16T13:40:10Z'
---
<!-- sq:body -->
The backends release: squads stops being a Claude Code tool with a second, generic option, and gains the agent hosts people actually use next (Codex and Cursor first, others as they are asked for). This milestone holds the work that makes adding a backend routine and gives each backend its own model vocabulary, since a model name belongs to one provider: "opus" and "sonnet" mean nothing at OpenAI.

**Belongs here**

- New backends behind the existing `AgentBackend` ABC (`src/squads/_backends/`; `claude_code` and `agents_md` exist today). Each answers the five per-host questions in `docs/backends.md` from its own host's documentation.
- A role's model as a per-backend map: one model per backend, instead of a single value. The map's shape, its default and its migration are open design points (below), not decisions.
- The spec, override and migration work the map needs: the role spec, `.overrides/roles.toml`, and a schema migration for existing squads.
- Pointer rendering for each new host: what its configuration can express, the per-host drop-and-report of a value it cannot express, and the currency check (`render_role_entry`, `restriction_fragment`).
- The backend management surface where a new backend needs it (add, switch, list), and the conformance coverage a new backend must pass.

**Open design points (to an ADR before building)**

- The map's shape: the key (backend name versus something coarser), how a role with no entry for a backend is treated, and whether a model is a plain string or a structured value.
- The default: what a backend uses when a role names no model for it, and whether a role-level fallback value survives alongside the map.
- The migration: how a role's existing single model becomes a map entry, and which backend it is attributed to.
- Validation: how each backend declares which model names it accepts, replacing the Claude-only list.

**Does not belong here**

- The local API and daemon of the preceding milestone, and the web frontend of the following one.
- Running or testing the hosts themselves beyond what pointer files and managed sections require.
- Choosing a model on a role's behalf, or translating a model name from one provider to another.
- Backends nobody has asked for yet; they follow the same path in a later release.
- Engine or vocabulary changes the backends merely consume.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T13:39:13Z] Pierre Chat:
  - - 2026-10-16: open a squads 0.19 release aimed at adding more agent backends (Codex, Cursor and others).
    - A role's configured model must become a key-value map with one model per backend, because model names are backend-specific: "opus" and "sonnet" do not exist at OpenAI.
- [2026-10-16T13:39:14Z] Nina Product:
  - - Related items found (search: codex, cursor, backend, model). Nothing is linked by a targets ref yet.
    - Should target this milestone (once ruled on): EPIC-136 (Agent backends, management and ecosystem; it names Cursor and Windsurf backends as features under it, so it is the natural home; as an epic it frames rather than targets, so its new-backend features would carry the targets refs) and FEAT-137 (Manage backends on an existing squad; the add/switch/list surface, Draft; re-read its scope first, since it predates the roster work).
    - Context, not targets: ADR-75 (pluggable backends), ADR-133 (de-Claude-ify the ABC), ADR-697 (roster status projects through the ABC), ADR-781 and FEAT-792 (pointers name commands; Codex, Copilot and Cursor planned; Done), TASK-803 (per-host backend questions; Done; its `_VALID_MODELS` and `model_drop_warning` is the Claude-only model validation the map replaces), FEAT-16 and TASK-132 (the agents_md backend; Done).
    - No existing item covers a Codex or Cursor backend or a per-backend model map. Needed, not yet written: an ADR for the map (shape, default, migration; architect), then a feature per new backend.
    - No depends-on ref to MILE-868: backends need neither the daemon nor the frontend, and a ref would make a 0.18 slip block this release. The ordering is by release only.
- [2026-10-16T13:39:48Z] Pierre Chat:
  - - 2026-10-16: swap the release numbers, because supported backends take priority. This milestone is squads 0.18 - more backends; the web frontend (MILE-868) becomes squads 0.19. This supersedes the 0.19 numbering in the comments above.
    - This milestone does not depend on MILE-868, and MILE-868 keeps its depends-on to MILE-1051 (0.17) only.
- [2026-10-16T13:39:49Z] Nina Product:
  - MILE-868 retitled to 0.19. No depends-on from MILE-868 to this milestone: the frontend consumes the daemon API and needs nothing from the backends work. The earlier note about a 0.18 slip is moot; the ordering is by release only.
<!-- sq:discussion:end -->
