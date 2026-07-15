---
id: REV-395
sequence_id: 395
type: review
title: 'EPIC-316 surfacing model: push-into-managed-files vs pull-at-startup'
status: Approved
author: reviewer
refs:
- FEAT-315:addresses
- FEAT-317:addresses
- FEAT-392:addresses
- ADR-314:addresses
- REV-388
- REV-391
subentities:
- local_id: F1
  title: Push boot-surfacing + unconditional directive vs conditional sections = dangling
    reference on fresh installs
  status: Fixed
  severity: high
- local_id: F2
  title: The .index.jsonl becomes readerless once surfacing is removed — derived data
    stored for no consumer
  status: Fixed
  severity: high
- local_id: F3
  title: 'Resolution (Full): role-sheet pull-at-startup; rip out boot-surfacing and
    drop the .index.jsonl machinery'
  status: Fixed
  severity: high
- local_id: F4
  title: sq-memory skill still teaches push-at-boot surfacing — contradicts the pull
    directive (F1 relapse)
  status: Fixed
  assignee: python-dev
  severity: high
- local_id: F5
  title: Stale .index.jsonl references survive in the two content-model docstrings
  status: Fixed
  assignee: python-dev
  severity: low
created_at: '2026-07-15T12:22:49Z'
updated_at: '2026-07-15T13:14:40Z'
---
<!-- sq:body -->
Design review of how EPIC-316 shared team knowledge (agent memory + the bulletin board) reaches an agent at the start of a run.

## Scope
The **surfacing model**: how a memory pool (FEAT-315) and the board (FEAT-317) get in front of an agent, and the per-folder `.index.jsonl` roll-up (ADR-314) that today feeds it.

## What ships today (verified)
- **Boot-surfacing PUSHES content into managed files.** The role-pointer renders a `{% if memory_lines %}` `## Your memory` block (`_rendering/templates/claude/pointer_agent.md.j2`); the CLAUDE.md / AGENTS.md managed sections render a `{% if board_lines %}` `## Board` block (`claude/claude_section.md.j2`, `agents_md/agents_section.md.j2`). The lines come from `_backends/_memory_surface.py::memory_index_lines` and `_backends/_board_surface.py::board_notice_lines`, wired in both backends (`_claude_code/_backend.py`, `_agents_md/_backend.py`).
- **The index has exactly one reader.** `_memory/_store.py::read_index` is the sole consumer of `.index.jsonl`, and its sole caller is `_memory_surface.py` (boot-surfacing). Confirmed by grep: `read_index` -> one definition, one call site.
- **The user-facing CLI never reads the index.** `sq memory list/search/show` (`_memory/_store.py::list_entries`/`search`) and `sq board list/clear` (`_board/_store.py::list_notices`) read the `.md` files directly (glob + `split_frontmatter`). The index is pure boot-surfacing scaffolding.
- **The engagement directive is unconditional but its targets are conditional.** `agents/role.md.j2` tells every agent to "review your `## Your memory` index and the team `## Board` — both surfaced earlier in your boot context" with no `{% if %}` guard, while the sections it names only render when `memory_lines`/`board_lines` are non-empty.

## Verdict
The push-into-managed-files model is the wrong shape. Findings F1/F2 below give the technical case; F3 is op-pierre's directed resolution (recorded verbatim in a discussion comment on this review). Changes requested — do not fix here; fix-tasks come later.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 395 add-finding "…" --severity medium`; track with `sq review 395 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Push boot-surfacing + unconditional directive vs conditional sections = dangling reference on fresh installs |
| F2 | 🟠 high | Fixed |  | The .index.jsonl becomes readerless once surfacing is removed — derived data stored for no consumer |
| F3 | 🟠 high | Fixed |  | Resolution (Full): role-sheet pull-at-startup; rip out boot-surfacing and drop the .index.jsonl machinery |
| F4 | 🟠 high | Fixed | python-dev | sq-memory skill still teaches push-at-boot surfacing — contradicts the pull directive (F1 relapse) |
| F5 | 🟢 low | Fixed | python-dev | Stale .index.jsonl references survive in the two content-model docstrings |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Push boot-surfacing + unconditional directive vs conditional sections = dangling reference on fresh installs

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Problem.** The boot-engagement directive in `agents/role.md.j2` is unconditional:

> "Before you start, review your `## Your memory` index and the team `## Board` — both surfaced earlier in your boot context — and apply anything relevant."

But the sections it names are conditional. `## Your memory` renders only under `{% if memory_lines %}` (`claude/pointer_agent.md.j2`), and `## Board` only under `{% if board_lines %}` (`claude/claude_section.md.j2`, `agents_md/agents_section.md.j2`). `memory_lines`/`board_lines` are empty whenever the role's pool has no memories and the board has no live notices.

**Impact.** Every new adopter's default state is an empty pool and an empty board. So out of the box the directive points an agent at two sections that were never rendered — a dangling instruction ("go read the thing that isn't there") on exactly the first-run experience we most want to be clean. It only stops dangling once someone has posted a notice or committed a memory.

**Root cause is the model, not the guard.** The obvious patch — gate the directive with the same `{% if %}` — is the wrong fix: it hard-codes the boot snapshot into the managed file, so the agent only ever sees what existed at the last `sq sync`, not what's live now. The push-into-managed-files approach forces a choice between a stale snapshot and a dangling pointer. F3 removes the choice.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The .index.jsonl becomes readerless once surfacing is removed — derived data stored for no consumer

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Problem.** The per-folder `.index.jsonl` roll-up exists solely to feed boot-surfacing. Verified reader graph:

- `_memory/_store.py::read_index` is the **only** consumer of a memory pool's `.index.jsonl` — one definition, one caller.
- That caller is `_backends/_memory_surface.py::memory_index_lines` (boot-surfacing) — nothing else.
- The user-facing CLI never touches the index: `sq memory list/search/show` go through `list_entries`/`search`, which glob the `.md` files and `split_frontmatter` them directly; `sq board list/clear` go through `_board/_store.py::list_notices`, same shape. The board's index is written (`_board/_store.py` `regenerate_index`) but never read back anywhere.

**Impact.** Remove boot-surfacing (F3) and `read_index` loses its only caller — the index becomes **readerless**. At that point everything that maintains it is maintaining data nobody consumes:

- the generator `_content_index.py` (`regenerate` / `regenerate_from_content_files` / `parse_index`);
- the write-path regeneration on every `save`/`forget` (`_memory/_store.py`) and every board `post` (`_board/_store.py`);
- the `sq sync` / `sq repair` pass `_services/_maintenance.py::_regenerate_content_indexes`;
- the option-B committed-index decision (REV-388) and the merge-conflict-handling fix (BUG-390) — both only matter because a committed, regenerated index invites merge conflicts.

This is stored/derived data kept in sync for no reader — the "don't store what you can derive" smell, and it drags a whole merge-conflict class (BUG-390) along with it. The two things that actually need the pool contents (boot engagement, and the CLI) either will read the `.md` files live (F3) or already do.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Resolution (Full): role-sheet pull-at-startup; rip out boot-surfacing and drop the .index.jsonl machinery

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Resolution — directed by op-pierre (see the discussion comment for his own words). Full scope.**

Replace push-into-managed-files with a **pull-at-startup** model, and drop the now-readerless index.

**1. Pull model.** The role sheet instructs every agent, unconditionally, to run `sq memory <its-slug> list` and `sq board list` at the start of a run and apply anything relevant. The command is always valid — an empty pool/board just lists nothing — so the instruction never dangles (fixes F1) and the agent always sees live content, never a `sq sync`-time snapshot.

**2. Rip out boot-surfacing.**
- Delete `_backends/_memory_surface.py` and `_backends/_board_surface.py`.
- Delete `_memory/_store.py::read_index` (F2: its only caller is gone).
- Remove the `{% if memory_lines %}` `## Your memory` block from `claude/pointer_agent.md.j2` and the `{% if board_lines %}` `## Board` block from `claude/claude_section.md.j2` and `agents_md/agents_section.md.j2`.
- Remove the backend wiring (`memory_index_lines` / `board_notice_lines` imports and the context they build in `_claude_code/_backend.py` and `_agents_md/_backend.py`).
- Rewrite the `role.md.j2` directive to the pull instruction in (1).

**3. Drop the `.index.jsonl` entirely (F2 cascade).** Storage becomes plain slug-named `.md` files (memory) and short-hash-named `.md` files (board), with no per-folder roll-up.
- Delete `_content_index.py` and the `regenerate` / `regenerate_from_content_files` / `parse_index` / `IndexEntry` surface.
- Remove index regeneration from the memory write/forget paths and the board post path.
- Remove `_regenerate_content_indexes` from `_services/_maintenance.py` (`sq sync` / `sq repair`).
- Retire the option-B committed-index design (REV-388) and the merge-conflict handling (BUG-390) — dropping the committed index eliminates that merge-conflict class at its root rather than handling it.

**Amendments this implies (to be reflected when fix-tasks land):**
- **ADR-314** — the storage/id model: the `.index.jsonl` roll-up is removed; storage is plain `.md` files only.
- **FEAT-315 US2 / FEAT-317 US2** — the "surfaced at boot" behavior changes from push-into-managed-files to pull-at-startup.
- **FEAT-392 US1** — the boot engagement nudge points at a live `sq …` list, not the rendered `## Your memory` / `## Board` sections.

**Not implemented here.** This review is the record; fix-tasks are authored later. Findings articulate the technical case backing op-pierre's directive.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — sq-memory skill still teaches push-at-boot surfacing — contradicts the pull directive (F1 relapse)

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟠 High
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Rewrote both passages in memory_skill.md.j2 to pull form (sq memory <role> list / sq board list at start of a run); regenerated squads/agents/skills/sq-memory.md + templates_manifest.json.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Stale .index.jsonl references survive in the two content-model docstrings

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Dropped the .index.jsonl clause from _memory/_model.py and _board/_model.py docstrings.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T12:24:43Z] Pierre Chat:
  - The if-gated push-surfacing is a terrible idea. Injecting memory and board content into the managed pointer/CLAUDE/AGENTS files means it's either a stale snapshot from the last sync or a dangling directive when it's empty — and empty is every new install's default.
  - Just tell the role sheet to list the board and memory at startup. Every agent runs `sq memory <its-slug> list` and `sq board list` at the start of a run and applies what's relevant. Always fresh, works when empty, nothing duplicated into managed files, nothing to go stale.
  - Do the full version: once surfacing is gone the .index.jsonl has no reader, so drop it too — storage is just the slug/hash-named .md files. That also kills the index merge-conflict problem at the root instead of patching around it (BUG-390 / the option-B design in REV-388).
- [2026-07-15T12:24:53Z] Paul Reviewer:
  - ChangesRequested. F1 (dangling directive on fresh installs) and F2 (readerless .index.jsonl) verified against source; both trace to the push-into-managed-files model. F3 records op-pierre's directed resolution — pull-at-startup + drop the index (Full scope). Findings are the technical backing; this review is the record, fix-tasks come later. Amends ADR-314, FEAT-315/FEAT-317 US2, and FEAT-392 US1.
- [2026-07-15T13:06:14Z] Paul Reviewer:
  - Verification of the TASK-396/397 rip-out (uncommitted on release/0.9). The index/surfacing CODE is fully and correctly removed — F2's core is resolved and F3's mechanical steps are done:
  - RESOLVED: _content_index.py / _memory_surface.py / _board_surface.py deleted; read_index + regenerate_from_content_files + regenerate_index gone; maintenance _regenerate_content_indexes/_memory_role_folders + both call sites removed; the four templates stripped of the ## Your memory / ## Board / per-role Memory blocks; role.md.j2 rewritten to the unconditional pull (sq memory <slug> list / sq board list), valid on empty pools. Stores read the .md files directly. Git-merge tests keep the .md-merge substance and drop only the index-conflict parts. Gates clean: pyright 0/0/0, ruff + format clean, sq check clean. No orphaned code refs (the one tests/ grep hit is the false-positive 'memory_surface_an_honest_conflict' test NAME). BUG-390 is genuinely obsolete — its subject (a committed conflicted .index.jsonl) no longer exists.
  - NOT resolved — two orphans the rip-out left behind (see F4/F5), both from the same scope gap: TASK-396 enumerated a fixed template/docstring list that missed these surfaces.
  - F4 (high): the sq-memory skill itself (memory_skill.md.j2 -> committed squads/agents/skills/sq-memory.md) still teaches the push-at-boot model — 'surfaced into your context automatically at boot ... you don't have to go looking'. That is F1's defect relapsed into the very skill governing memory/board use, and it contradicts the new pull directive. Keeping REV-395 in ChangesRequested for this.
  - F5 (low): _memory/_model.py and _board/_model.py docstrings still cite the generated .index.jsonl roll-up ADR-314 says no longer exists.
  - Not approving. Once F4/F5 land (rewrite the skill passages to the pull form + regenerate; drop the roll-up clause from the two docstrings), the rip-out fully resolves F1/F2/F3.
- [2026-07-15T13:07:10Z] Catherine Manager:
  - Dispatching @python-dev on F4 + F5. F4 (high): rewrite the two push-surfacing passages in memory_skill.md.j2 (the 'surfaced automatically at boot, you don't have to go looking' bits for both memory + board) to the PULL form — run sq memory <slug> list / sq board list at the start of a run — matching role.md.j2; then regenerate the on-disk sq-memory skill + manifest. F5 (low): drop the stale '.index.jsonl roll-up' clause from _memory/_model.py + _board/_model.py docstrings.
- [2026-07-15T13:14:40Z] Catherine Manager:
  - All findings resolved by the re-architecture (commit 7c9050b): F1/F2 removed (push-surfacing + the readerless .index.jsonl gone), F3 implemented (pull-at-startup role directive), F4/F5 fixed (skill + docstrings). Full suite green, no residual push/index language. Approving.
<!-- sq:discussion:end -->
