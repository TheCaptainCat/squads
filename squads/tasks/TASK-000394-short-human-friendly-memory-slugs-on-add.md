---
id: TASK-394
sequence_id: 394
type: task
title: Short, human-friendly memory slugs on add
status: Draft
parent: FEAT-392
author: tech-lead
subentities:
- local_id: ST1
  title: Short slug derivation + --slug override
  status: Todo
  story: US2
- local_id: ST2
  title: 'Tests: derivation, override, collision, legacy resolve'
  status: Todo
  story: US2
created_at: '2026-07-15T11:47:08Z'
updated_at: '2026-07-15T11:47:29Z'
---
<!-- sq:body -->
Implements US2 of the parent feature.

## Goal

`sq memory <role> add "<fact>"` currently slugifies the entire fact, producing unwieldy handles that are awkward to type back into `show <slug>` / `forget <slug>`. Derive a short handle instead; the full fact text already lives in the entry summary and body, so the slug only needs to address the entry.

## Where

- `src/squads/_memory/_store.py` — slug derivation in `add` (currently `slugify(fact)` fed to `_unique_slug`).
- `src/squads/_cli/_memory.py` — the `add` command (`add_memory`).
- Service pass-through (`memory_add`) as needed to carry the new override.

## Requirements

- Derive a **short** slug: first few words / capped length, truncated at a word boundary (never mid-word). Not the whole fact.
- Add an optional explicit override `--slug <handle>` on `sq memory <role> add` letting the author name the slug directly instead of deriving it (slugify the override for safety).
- The full fact text stays in the entry summary/description and body — unchanged.
- Existing long-slug memories on disk continue to resolve unchanged (`show`/`forget`/`list` address by the on-disk filename slug; derivation only affects newly added entries).
- Collision disambiguation (`-2`, `-3`, ...) still applies to the new short-slug derivation via `_unique_slug`.

## Verify

- `add` with a long fact yields a short slug; the summary/body retain the full text.
- `--slug foo` uses `foo` (slugified) as the handle.
- Two short slugs that collide get `-2`.
- An existing long-slug `.md` still resolves via `show`/`forget`.
- Service-level test plus a CLI smoke test (per the testing convention).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 394 add-subtask "<title>"`; track with `sq task 394 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Short slug derivation + --slug override | US2 |
| ST2 | Todo |  | Tests: derivation, override, collision, legacy resolve | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Short slug derivation + --slug override

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Short, human-friendly memory slugs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Derive a short handle in _store.add (first few words / capped at a word boundary) instead of slugifying the whole fact; add an optional --slug override on the CLI add command, plumbed through the service. Full fact stays in summary/body; collision -2/-3 via _unique_slug preserved.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Tests: derivation, override, collision, legacy resolve

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Short, human-friendly memory slugs
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Service-level test + CLI smoke test: long fact yields a short slug (summary/body keep full text); --slug names the handle; colliding short slugs get -2; an existing long-slug memory still resolves via show/forget.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
