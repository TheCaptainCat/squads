---
id: TASK-57
sequence_id: 57
type: task
title: Guard all prose inputs against literal sq marker syntax (comments, sub-entity
  titles)
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-56:fixes
subentities:
- local_id: ST1
  title: Add one shared marker-syntax guard; apply to comment messages and sub-entity
    titles (create + update)
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Tests for marker-syntax guard on newly-guarded paths
  status: Done
  assignee: python-dev
created_at: '2026-06-12T08:18:43Z'
updated_at: '2026-07-06T15:18:19Z'
---
<!-- sq:body -->
## Problem

`sq <type> <n> body` and the sub-entity `... body` paths already reject marker syntax
("body must not contain sq marker comments") via `sections.find_markers`. Several **other**
prose inputs that land inside marker-delimited regions have no such guard, so an author can
inject a well-formed marker tag (an HTML-comment-wrapped `sq:` tag) that breaks the file's
marker integrity. `sq check` then reports duplicate / unclosed markers, and a later
marker-based section edit can match the injected tag and corrupt the file. Observed live on
FEAT-40 (see BUG-56); repaired by hand as a one-off.

Backtick-wrapping is NOT a neutralizer: `_sections.find_markers` matches a well-formed tag
anywhere in the text, code spans included. Rejection is the only safe option.

## Unguarded input paths (all must be closed)

1. **Comment messages** — `_services/_collab.py::comment`. Messages flow through
   `_discussion.format_comment` and are appended verbatim into the `:discussion` region
   (`append_to_section`). No guard. This is the path that bit us on FEAT-40.
   Reachable from EVERY item type's `comment` command and from `--story/--subtask/--finding`
   targeted discussion comments.

2. **Sub-entity titles** — `_services/_subentities.py::_add_block` (story/subtask/finding
   create) and `::_update_block` (the `--title` flag). The title is NOT guarded today (only
   the optional `body` is, via `_reject_markers`). The title renders into TWO marker regions:
   - the block heading `### <local-id> - <title>` (inside the block's open/close markers),
     re-rendered from the stored frontmatter title by `discussion.set_heading` on EVERY block
     mutation (status/assignee change included);
   - the `:head` summary table row (`set_head` / `render_summary`).
   Because the heading is re-derived on every write, a title-injected marker is PERSISTENT and
   re-corrupts the file on each touch — strictly worse than the one-time comment append.

   Reachable from: `sq feature <n> add-story`, `sq task <n> add-subtask`,
   `sq review <n> add-finding`, and the corresponding `... update --title` flags.

## Confirmed SAFE (no change needed - but assert with a test)

- Item-level `update --title` / `--description` (`_services/_items.py::update`): title only
  drives the slug/frontmatter and the on-disk filename; description is a frontmatter field.
  Neither is injected into a `:body` or other marker-delimited region (the item templates do
  not render description into the body marker block). Frontmatter is written as YAML via
  `update_frontmatter`, not through the section machinery.
- Already-guarded body paths: item `body` (set + create), and sub-entity body
  (`_set_block_body`, `_add_block` body arg) - these stay as-is.

## Contract for the fix

- Add ONE shared guard (reuse / promote the existing check - e.g. lift `_reject_markers`
  into a single shared helper so item body, sub-entity body, comment, and titles all call the
  same code). On detecting a well-formed marker tag in the input, raise `SquadsError` with a
  message from the SAME family as the existing body guard, e.g. the existing
  "must not contain sq marker comments" wording.
- The message MUST point the author at a safe formulation: write the tag WITHOUT its
  HTML-comment wrapper (plain prose, the way this very task body refers to `sq:body`), since
  it is the comment wrapper that `find_markers` keys on. Make clear backticks do NOT help.
- Apply the guard to:
  - comment messages (each `-m` message) in `_collab.py::comment`, BEFORE the section append;
  - sub-entity `title` on create (`_add_block`) and on update (`_update_block`).
- Keep the guarded body paths unchanged in behaviour (same message); ideally they end up
  calling the same shared helper.
- Reject BEFORE any mutation / file write so a bad input never partially lands (the comment
  path mutates inside `_locked_section_edit`; validate the messages up front).

## Acceptance

- A comment containing a well-formed marker tag is rejected with the shared `SquadsError`;
  the item file is untouched and `sq check` stays clean.
- Creating / updating a story / subtask / finding with a marker tag in its TITLE is rejected;
  the heading and `:head` table never receive an injected tag.
- A backtick-wrapped marker tag is ALSO rejected (regression guard for the "code span is not
  safe" trap).
- Item title / description update still works with bracket / backtick content that is not a
  marker tag (no false positives).
- Existing body-guard behaviour and message unchanged.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; full
  `uv run pytest` green, with new service-level + CLI smoke tests for each newly-guarded path.

## Pointers

- Guard primitive: `_sections.find_markers` (matches only well-formed tags - strict).
- Existing guards to unify: `_services/_base.py` (create body), `_services/_items.py::set_body`,
  `_services/_subentities.py::_reject_markers` (already a helper - good seed for the shared one).
- Comment path: `_services/_collab.py::comment` + `_discussion.format_comment`.
- Title -> region render: `_discussion.set_heading` / `set_head` / `render_summary`, driven by
  `_subentities.py::_write_block_file`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 57 add-subtask "<title>"`; track with `sq task 57 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Add one shared marker-syntax guard; apply to comment messages and sub-entity titles (create + update) |  |
| ST2 | Done | python-dev | Tests for marker-syntax guard on newly-guarded paths |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add one shared marker-syntax guard; apply to comment messages and sub-entity titles (create + update)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Lift the existing marker-syntax rejection into one shared helper (seeded from _subentities.py::_reject_markers, using _sections.find_markers) and apply it, before any mutation, to comment messages in _collab.py::comment and to sub-entity titles on create (_add_block) and update (_update_block). Raises SquadsError in the same 'must not contain sq marker comments' family, pointing the author at the unwrapped formulation and noting backticks do not neutralize. Existing body-guard paths converge on the same helper.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Tests for marker-syntax guard on newly-guarded paths

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Tests: each newly-guarded path rejects marker tags (incl. backtick-wrapped); item title/description false-positive guard; body behaviour unchanged.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T08:26:59Z] Elias Python:
  - Implementation complete. Shared guard reject_markers(text, what) promoted to _services/_base.py; comment, title, and body paths all call it. Tests and linters green.
  - Handing off to @reviewer and @qa for verification.
<!-- sq:discussion:end -->
