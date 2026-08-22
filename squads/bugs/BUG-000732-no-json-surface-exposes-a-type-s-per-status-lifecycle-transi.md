---
id: BUG-732
sequence_id: 732
type: bug
title: No JSON surface exposes a type's per-status lifecycle/transitions
status: Verified
author: qa
priority: medium
severity: medium
refs:
- FEAT-334:addresses
created_at: '2026-08-03T08:51:02Z'
updated_at: '2026-08-21T16:57:33Z'
---
<!-- sq:body -->
A machine client cannot resolve which statuses a given item type accepts, or the transitions between them, from any `--json` surface.

**Reproduction**

- `sq workflow types --json` rows are `{type, order, prefix, reserved, category, fields, labels}` (`src/squads/_cli/_workflow_cmd.py::TYPE_CATALOG_FIELDS`) — no lifecycle reference at all, even though `ItemSpec.lifecycle` (a string naming an entry in `WorkflowSpec.lifecycles`) exists server-side (`_workflow/_models.py`).
- `sq workflow statuses --json` rows are `{status, role, badge}` (`STATUS_CATALOG_FIELDS`) — a flat, squad-wide vocabulary with no per-type edges: it tells you every declared status's role/badge, never which types accept it or what it can move to/from.
- The full picture — initial state, every state, every edge — genuinely exists (`WorkflowSpec.machine_for(item_type)` returns a `Lifecycle` with `.initial`/`.transitions`; `linearize_lifecycle()` walks it deterministically) and **is** rendered, but only as a markdown/mermaid diagram inside `sq workflow show` (`workflow.md.j2`, "## Type lifecycles" section) — not machine-readable.
- The only other place any of this leaks out is an invalid-transition refusal, and even that only gives the flat allowed-status set for the type, not edges from the current status: `sq task <n> status Approved` on a task currently `Draft` →
  `error: 'Approved' is not a valid status for task (allowed: Blocked, Cancelled, Done, Draft, InProgress, InReview, Ready)`.

Verified all of the above by reading `_workflow_cmd.py`/`_workflow/_models.py` and by driving `sq workflow types --json`, `sq workflow statuses --json`, and an invalid transition against a throwaway squad.

**Actual vs expected:** actual — no `--json` client can answer "what statuses can a `task` be in?" or "from `Draft`, what can a `task` become?" without parsing the markdown/mermaid `sq workflow show` output. Expected — the same information available to a human reading `sq workflow show` is available to a script via a `--json` flag, matching every other workflow catalog (`types`, `collections`, `statuses`, `roles`).

**Impact:** the whole point of the frozen `--json` catalogs (per their own docstrings) is that a client consumes a contract instead of scraping. `clients/vscode` already consumes `sq workflow types --json` and `sq workflow statuses --json` for type/status metadata (`domain/typeCategory.ts`, `domain/statusRole.ts`, `domain/badgeCatalog.ts`, etc.) — any future feature needing a status quick-pick or a "what can this move to" UI has no contract to build on today and would have to scrape mermaid or shell out to `sq <type> <n> status <bogus>` and parse the refusal string, which is fragile and was never designed as an API.

**Fix direction:** `TYPE_CATALOG_FIELDS` is additive (client contract doc calls out "all present, never omitted, so the key set is stable across every object" — adding a new key is backward compatible, not breaking), so adding a `lifecycle` field to each `sq workflow types --json` row is a legal, low-risk extension: `{"initial": <status>, "states": [...], "transitions": [[src, dst], ...]}`, built directly from the existing `machine_for(item_type)` / `lifecycle_states_in_order` / `lifecycle_edges` helpers already used by `workflow.md.j2` — no new computation, just a new serialization of data that already exists. An alternative is a dedicated `sq workflow lifecycles --json` surface (mirroring the `collections`/`roles` pattern) if a reviewer prefers not to grow `types` rows further; either is reasonable, the edges need to land *somewhere* machine-readable.

**Severity:** Medium. Not a correctness bug — nothing returns wrong data — but a real capability gap: the stated purpose of the `--json` catalogs (avoid client-side scraping) is undermined for exactly the one axis (lifecycle) a status-aware UI would need most. No current shipped client feature is blocked today (checked `clients/vscode/src/*` — no code path reads/needs transition edges yet), which is why this doesn't rise to High.

**Release:** 0.14. This is a net-new, additive surface, not a fix to broken behaviour, and 0.13 is already being descoped; a clean additive `--json` field/command is exactly the kind of work that can wait a release without cost.

**Affected surfaces:** `sq workflow types --json` (`src/squads/_cli/_workflow_cmd.py`), `sq workflow statuses --json` (same file), `src/squads/_workflow/_models.py` (the underlying `Lifecycle`/`WorkflowSpec.machine_for` data already computed and available).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T15:37:18Z] Robert Architect:
  - Shape settled by ADR-738 (Proposed): a dedicated `sq workflow lifecycles --json` catalog — `{lifecycle, initial, states, transitions}`, one row per declared lifecycle — plus a `lifecycle` reference key on the type row. Not the machine inlined per type row: the bundled spec has 8 lifecycles for 10 types and 3 kinds, and sub-entity kinds bind lifecycles too with no type row to carry them, so inlining publishes the same machine twice in two shapes.
  - `transitions` is `[{from,to}]` in `lifecycle_edges()` order (a positional pair cannot grow a named key; a status-keyed map has no frozen key set). `states` is `lifecycle_states_in_order()` — deliberately not `linearize_lifecycle`'s prettier spine ordering, whose side-state canonicalization is keyed on bundled status names. 0.14 stands, as this bug proposed.
- [2026-08-15T15:11:39Z] Elias Python:
  - Heads-up for whoever implements this: `lifecycle_edges` no longer exists. It was orphaned when the cheatsheet stateDiagram was removed (vulture flagged it, filed as REV-736 F51) and I deleted it rather than allowlist genuinely dead code. `lifecycle_states_in_order` stays — it has a live caller — so re-deriving the edges is a six-line comprehension over it. The fix direction in this body is otherwise unchanged.
- [2026-08-21T12:35:50Z] Pierre Chat:
  - In scope for 0.14.0: op-pierre pulled all five open bugs into the next release, overriding the earlier per-bug deferral to a later cycle.
- [2026-08-21T12:35:56Z] Pierre Chat:
  - Implement ADR-738 in full: both new catalogs (lifecycles and subentity-kinds) and both type-row reference keys, not just the lifecycles half this bug asks for.
- [2026-08-21T15:17:09Z] Catherine Manager:
  - Fix landed in 8f5b267 on release/0.14 (TASK-749). Verified: sq workflow lifecycles --json now publishes all 8 declared lifecycles with initial/states/transitions, the type and kind rows have a catalog to join, and the docs forward reference is retired. The tech lead audit found the shipped subentity-kinds catalog and both type-row keys already match ADR-738 sections 3 and 5, so no further catalog work is outstanding. Awaiting QA verification.
- [2026-08-21T16:57:02Z] Mara Tester:
  - Drove sq workflow lifecycles --json: publishes {lifecycle,initial,states,transitions} for all 8 bundled lifecycles (adr, agent, bug, finding, guide, review, subentity, work).
  - Answered the bug's own two questions purely by joining sq workflow types --json's lifecycle key (task -> work) to the lifecycles catalog: task's live statuses = [Draft, Ready, InProgress, Cancelled, Blocked, InReview, Done]; from Draft -> [Ready, InProgress, Cancelled]. No source scraping.
  - Drove a project override declaring a new lifecycle (lifecycles.incident + items.incident with lifecycle="incident", the workflow.toml worked example): sq workflow lint passes, the catalog grows to 9 entries including incident with correct initial/states/transitions, and the new type's lifecycle key joins to it.
<!-- sq:discussion:end -->
