---
id: FEAT-315
sequence_id: 315
type: feature
title: Agent memory — committed per-role notebook surfaced at boot
status: InProgress
parent: EPIC-316
author: product-owner
refs:
- ADR-314:implements
subentities:
- local_id: US1
  title: As an agent, I can jot a small learned fact to my role's memory so it persists
    for future runs
  status: Todo
- local_id: US2
  title: As an agent, my role's memory index is surfaced at boot so relevant facts
    don't slip past me
  status: Todo
- local_id: US3
  title: As an agent, I can list, search, and show my role's memories to pull full
    content when relevant
  status: Todo
- local_id: US4
  title: As an agent or operator, I can prune a stale or wrong memory so the pool
    stays trustworthy
  status: Todo
- local_id: US5
  title: As a teammate, committed per-role memory arrives on checkout and merges cleanly
    across branches
  status: Todo
- local_id: US6
  title: As an agent, the sq-memory skill teaches the memory workflow and curation
    discipline
  status: Todo
created_at: '2026-07-06T16:05:08Z'
updated_at: '2026-07-15T08:03:06Z'
---
<!-- sq:body -->
# Agent memory

A per-role, committed notebook of small, agent-authored facts — *what an agent has learned*
about working on this project ("the scale suite takes ~4 min, don't re-run it to reslice output";
"pyright runs in strict mode"). Each role owns its own pool; a python-dev's memory is the
python-dev's.

## Why

The knowledge an agent accumulates today either lives locally in Claude Code's own memory (per-user,
per-machine — a teammate's agent never sees it) or has to be wedged into `CLAUDE.md` (a formal repo
intro) or an item's discussion (per-work-item, and it piles up until facts slip past the agent's
attention). There's no lightweight, shared, durable home for "small things worth remembering before a
run." Being **committed to the repo** is the whole point: a fresh checkout or a new teammate's agent
inherits the accumulated per-role memory, and it travels with the project across machines and branches.

## Shape

- **Storage & id model** are fixed by the accompanying decision (file-per-memory, slug-named, under
  `squads/agents/memory/<role>/`, a generated per-role `.index.jsonl` roll-up — one line per memory,
  entry schema `{slug, filename, description}` — entirely off the global counter and outside
  `.squads.json`). This feature builds the behaviour on top of that.
- **Retrieval is pull-with-a-nudge.** The per-role `.index.jsonl` is surfaced at role-boot (one line
  per memory) so the agent always knows the pool exists and roughly what's in it; full content is
  fetched on demand. Index in, content on recall. Memory is **slug-addressed** (`show <slug>`) — line
  position in the index is not load-bearing for recall.
- **Command surface** (role is a positional subject, consistent with `sq inbox <role>` / `sq mine
  <role>`):

  ```
  sq memory <role> list                     # browse the index
  sq memory <role> search <query>           # find by content
  sq memory <role> show <slug>              # read one in full
  sq memory <role> add "<fact>" [--file f]  # jot a new memory
  sq memory <role> forget <slug>            # prune a stale/wrong one
  ```

- A guiding **skill** (`sq-memory`) teaches the workflow and the curation discipline: check your
  index at the start of a run, one fact per memory, prune what's wrong, and the memory-vs-board
  boundary (personal-learned → memory; cross-cutting/announcement → the board).

## Boundary

Cross-cutting facts that apply to everyone (e.g. a repo-wide commit convention) are **not** memory —
they belong on the team bulletin board (a separate, complementary capability) so they live once
rather than duplicated into every role's pool. This feature is agent-scoped memory only; the board is
out of scope here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 315 add-story "As a <role>, I want … so that …"`; track with `sq feature 315 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an agent, I can jot a small learned fact to my role's memory so it persists for future runs |
| US2 | Todo |  | As an agent, my role's memory index is surfaced at boot so relevant facts don't slip past me |
| US3 | Todo |  | As an agent, I can list, search, and show my role's memories to pull full content when relevant |
| US4 | Todo |  | As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy |
| US5 | Todo |  | As a teammate, committed per-role memory arrives on checkout and merges cleanly across branches |
| US6 | Todo |  | As an agent, the sq-memory skill teaches the memory workflow and curation discipline |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an agent, I want to jot a small learned fact to my role's memory so it persists for future runs.

**Acceptance**
- `sq memory <role> add "<fact>"` creates a slug-named markdown file under `squads/agents/memory/<role>/`, slug derived from the fact.
- `--file <path>` supplies a longer body instead of inline text.
- The entry carries light frontmatter (summary, created_at) over a freeform body; NO global-counter id is allocated.
- The role's `.index.jsonl` is regenerated to include the new entry (one `{slug, filename, description}` line).
- Two memories added on separate branches produce independent files with no merge conflict.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent, my role's memory index is surfaced at boot so relevant facts don't slip past me

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an agent, I want my role's memory index surfaced at the start of a run so relevant facts don't slip past me.

**Acceptance**
- At role-boot the agent's own role `.index.jsonl` (one line per memory) is surfaced into its context through the active backend, not hard-coded.
- Only the index is surfaced, not full bodies (index in, content on recall).
- Memory is slug-addressed (`show <slug>`); line position in the index carries no meaning and is not relied on.
- An empty pool surfaces nothing — no noise.
- Surfacing goes through the backend abstraction so a non-Claude backend does the equivalent.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an agent, I can list, search, and show my role's memories to pull full content when relevant

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an agent, I want to list, search, and show my role's memories so I can pull full content when relevant.

**Acceptance**
- `sq memory <role> list` prints the role's `.index.jsonl` entries (one line per memory: slug, filename, description).
- `sq memory <role> search <query>` returns memories whose content matches.
- `sq memory <role> show <slug>` prints one memory's full body, addressed by slug — not by index position.
- Role is a positional subject; an unknown role or slug raises a clean SquadsError, not a stack trace.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an agent or operator, I want to prune a stale or wrong memory so the pool stays trustworthy.

**Acceptance**
- `sq memory <role> forget <slug>` removes the file and regenerates the role's `.index.jsonl`.
- Forgetting a non-existent slug raises a clean error.
- The removal is a real git file deletion (history retained in git log), never a side effect of a read.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a teammate, committed per-role memory arrives on checkout and merges cleanly across branches

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As a teammate, I want committed per-role memory to arrive on checkout and merge cleanly across branches so shared knowledge travels with the project.

**Acceptance**
- Memory files under `squads/agents/memory/` are committed (not gitignored).
- Two branches each adding a distinct memory merge with no conflict.
- Two branches editing the SAME memory surface an honest git conflict (correct to resolve by hand).
- Memory lives outside `.squads.json`; `sq repair` neither rebuilds nor disturbs it.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an agent, the sq-memory skill teaches the memory workflow and curation discipline

<!-- sq:story:US6:head -->
**Status:** ⚪ Todo
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
As an agent, I want the sq-memory skill to teach the memory workflow and curation discipline so the pool does not rot.

**Acceptance**
- A managed `sq-memory` skill exists and is generated like the other skills.
- It documents: check your index at run start; one fact per memory; prune stale/wrong entries; and the boundary (personal-learned -> memory, cross-cutting -> board).
- It is cross-role behaviour (surfaced to all roles), not a per-type `sq-<type>` skill.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-13T09:10:33Z] Nina Product:
  - Aligned to ADR-314's accepted design: INDEX.md -> generated .index.jsonl ({slug, filename, description} per line); memory stays slug-addressed, not positional. Shape + US1-US4 updated.
<!-- sq:discussion:end -->
