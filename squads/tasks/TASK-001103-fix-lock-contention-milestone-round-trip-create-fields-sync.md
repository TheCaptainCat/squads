---
id: TASK-1103
sequence_id: 1103
type: task
title: Fix lock contention, milestone round-trip, create fields, sync wording
status: Done
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
- FEAT-1108:depends-on
- BUG-1120:fixes
description: Defects F4, F5, F9, F16, F6 and F2 from REV-1099, plus BUG-1120.
subentities:
- local_id: ST1
  title: Report index-lock waits on stderr and fail a timeout as a clean SquadsError
  status: Done
  maps_to: US1
- local_id: ST2
  title: Stop a milestone body write-back from duplicating the roll-up, and name the
    fix for a view tag
  status: Done
  maps_to: US2
- local_id: ST3
  title: Expose every declared field as a create option and store a declared default
  status: Done
  maps_to: US2
- local_id: ST4
  title: Render a type's Team workflow line for any number of authoring roles
  status: Done
  maps_to: US3
- local_id: ST5
  title: Word a regenerated pointer and the post-migrate line accurately
  status: Done
  maps_to: US3
- local_id: ST6
  title: Allow Todo to Done in the bundled sub-entity lifecycle
  status: Done
  maps_to: US4
- local_id: ST7
  title: Write the 0.17.0 CHANGELOG entries for this task's defect fixes
  status: Done
  assignee: tech-writer
  maps_to: US1
- local_id: ST8
  title: Rebuild the index when init --force runs over an existing squad
  status: Done
created_at: '2026-10-24T10:04:00Z'
updated_at: '2026-10-28T12:11:17Z'
---
<!-- sq:body -->
## Goal

Fix six defects from the adopter field report (REV-1099): F4, F5, F9, F16, F6 and F2, plus BUG-1120 (a repeated `init --force`). Each subtask names the finding it closes and holds the approach. The finding bodies on REV-1099 carry the reproductions.

## Approach

- **F4, index-lock contention** (`src/squads/_index/_store.py`). `IndexStore.transaction()` acquires the Layer 3 `FileLock` on a worker thread with the constructor's `lock_timeout` (10 s). Acquire in two steps: a first try bounded at about one second, then, if that times out, one line on stderr (`waiting for the index lock <path>…`) and a second try for the rest of the timeout. A final `filelock.Timeout` becomes a new `SquadsError` subclass in `src/squads/_errors.py`. Its one-line message names the lock file, says nothing was written and says the command can be retried. Raise it inside the Layer 3 `try` so the proc-mutex and loop lock are still released. Update the three places that say a `filelock.Timeout` "propagates unchanged" (module docstring, `transaction()` docstring, the inline comment). The notice goes to stderr only, so `--json` stdout stays clean. `sq import -` holds one transaction, so it gets the same behaviour. The daemon (ADR-1052, not built) inherits this path, which already lives in the store.
- **F5, milestone body round-trip** (`src/squads/_services/_items.py`, `src/squads/_services/_base.py`). Builds on FEAT-1108 (TASK-1110): `show --json` `body` returns the stored text with its raw `sq:view:<name>` tags, so a write-back carries no rendered roll-up and nothing has to be stripped. The remaining fix is on the write side. In `_body_mutate`, the view-tag part of the marker check moves into the mutate closure, where the current `sq:body` region is known. An incoming view tag whose name and enabled/disabled state match a tag already placed in that region is accepted and dropped from the incoming text, and `place_view_tags` re-places it at its declared position. `reject_markers` keeps refusing every other marker before the closure runs. A view tag that is not already placed, or whose state differs, is refused with a message that names the `sq:view:<name>` line, says to leave it out because sq keeps a placed tag in place, and names `view add` / `view disable` only for a type that has those verbs. Replace with `--force`, `--append` and the import `body` op share this closure and get the same behaviour.
- **F9, create sets every declared field** (`src/squads/_cli/_create.py`, `src/squads/_services/_base.py`, `src/squads/_services/_subentities.py`). Replace the hardcoded `--priority` option with one `--<field-code>` option per field the type declares (`spec.fields_for(type)`). This mirrors what `_register_add` in `src/squads/_cli/_items.py` already does for `add-<kind>`, with help derived from the field's collection. Both the static per-type commands and `_build_create_cmd` / `_CustomCreateGroup` for custom types need it, resolved against the active spec, not the bundled one (`spec_aware_command_cls`). Values go through `svc.create(..., fields=...)`. Keep `--priority` as the flag for the `priority` field so existing scripts keep working. Defaults: `_create_core` stores `field_default(type, code)` for every omitted declared field that has one. Move `field_default` from the `_subentities` mixin to `ServiceCore` so create and add share one resolver. The import `create` op goes through `_create_core` and gets the same default. Existing items are not backfilled: frontmatter is the truth, and a null stays null until it is set.
- **F16, any number of authors** (`src/squads/_interactions/__init__.py`, `templates/claude/claude_section.md.j2`, `templates/workflow.md.j2`). `authoring_owner` returns `None` when `in_lane_owner` yields more than one slug, so the bullet disappears. Add `authoring_owners(...)`, which returns every live, titled in-lane owner with the same roster and title resolution. `in_lane_owner` returns a set, so take the order from the playbook (`create_lanes`) to keep the rendered line stable. Then make both templates loop over it. CLAUDE.md: "The **architect** and the **technical writer** author **guides** …" (a comma list with "and" for three or more). `workflow.md.j2`: one `--author` command per owner, or the slugs joined, whichever reads cleanly. Remove `authoring_owner` if nothing else calls it after this. Update the docstring that says a second author is ambiguous.
- **F6, operator subtasks close without --force** (`src/squads/_specs/workflow.toml`). Append `"Done"` to `[lifecycles.subentity.transitions] Todo`. It goes last, so the happy path (the first edge, `Todo → InProgress`) does not change. Stories share the `subentity` machine and gain the edge too, which is the ordinary case for them as well. An override that redeclares `Todo` keeps its own list.
- **F2, honest wording for a regenerated pointer** (`src/squads/_services/_maintenance.py`, `src/squads/_services/_validators.py`, `src/squads/_cli/_migrate.py`, `docs/backends.md`). ADR-1119 removed `squads_version` and `version_notice`, so nothing records which release wrote a pointer and sync cannot tell an older release's output from a hand edit. What remains is wording that claims no more than the content compare knows. `_entry_drift_report` says `<path>: had drifted — regenerated by this sync`, which reads as tampering; word it `<path>: out of date or edited by hand — regenerated by this sync (backend: <name>)`. `backend_entry_drift` in `_validators.py` gets the same wording for its warn line (`managed pointer is out of date or edited by hand — run sq sync`); the error line for a missing capability restriction keeps its level and its own wording. Update the docstrings and comments in `_maintenance.py` and the paragraph in `docs/backends.md` that quote "had drifted". Post-migrate line in `_cli/_migrate.py`: in the code, `migrate up` regenerates no managed file except inside the 0.11 to 0.14 runner, which rewrites only the compiled CLAUDE.md/AGENTS.md regions and the two new type skills and already says so in its summary line; the trailing repair writes items and the index only. So sync is what regenerates the agent files, and the line says that: `run sq sync to regenerate the agent files (pointers, skills, CLAUDE.md/AGENTS.md sections)`. No stored version, no outdated/drifted split.
- **BUG-1120, a repeated `init --force` leaves skills out of the index** (`src/squads/_services/_service.py`). `init` always writes an empty index (`create_empty_threaded`, counter 0). Over an existing squad, `activate_role` then finds no role item and allocates ROLE-1 to ROLE-8 again, which happen to overwrite the same files, while `seed_bundled_skills` skips every slug whose `SKILL-*-<slug>.md` already exists, so the skills are never indexed and the counter stays at 8. `refresh_managed` also writes the slug-named `<slug>.md` body files again, and nothing renames them. Any work item the squad held drops out of the index the same way, and the next id collides with it. Fix it as `adopt` does: when the squad directory already holds an index or item files, rebuild the index from disk with `svc.repair()` right after the empty index is written and before roles are activated, so existing roles are found live (`activate_role` is a no-op on them), existing skills stay indexed, and the counter resumes past the highest id. A first `init` on an empty directory is unchanged.

## Tests

One table per behaviour. A row exists only if breaking the fix turns it red, so check each one that way. Rows are boundaries and failures, never a cross product. Each behaviour is tested at one layer; a CLI case is added only where the CLI adds behaviour (option parsing, exit code, stderr). Run `tests/meta`, `tests/integration` and `tests/cli` whatever else you select, because bundled specs and templates change.

- **F4, lock wait and timeout** (store level, the lock held from a **subprocess** with a small `lock_timeout`). Rows: lock free, no notice on stderr; lock released during the wait, the notice then the write lands; lock held past the timeout, the new `SquadsError` naming the lock file, nothing written, and a following write succeeds (the in-process locks were released). One CLI row: held past the timeout with `--json`, exit 1, one-line error on stderr, no `Traceback`, empty stdout.
- **F5, a view tag in an incoming body** (service level, replace with `--force` on a milestone). Rows: the `show --json` body written back unchanged, item file byte-identical; that body with edited prose, prose changed and one roll-up; the placed tag moved to another line, re-placed at its declared position; the tag disabled in the incoming text while enabled on disk, refused with the wording asserted; a tag not placed on this item, refused with the wording asserted; the same refusal on a type without `view add`, which names no view verb; a non-view marker, generic refusal unchanged; the unchanged write-back on a custom type whose override seeds its own view tag.
- **F5, every body write reaches the same check** (one row per entry point, the unchanged write-back only): `--append` and the import `body` op.
- **F9, create options from declared fields** (CLI, since the options are CLI). Rows: `sq create bug --severity high` stores it; `--priority` still sets priority; a custom type's override-declared field is settable by its code; an invalid value is refused.
- **F9, declared default at create** (service level). Rows: omitted with a declared default, stored (bug severity `medium`); omitted without one, null; a given value wins over the default; the import `create` op stores the default; an existing item with a null field still shows null.
- **F16, authoring roles in a Team workflow line** (unit, `authoring_owners` plus the rendered line). Rows: 0 authors, no line; 1, singular wording; 2, "A and B"; 3, comma list with "and"; an off-roster author left out; an untitled author left out. The goldens cover the bundled guides line in CLAUDE.md and AGENTS.md; one row renders `workflow.md.j2` with two authors.
- **F6, Todo to Done** (service level). One row: a subtask goes Todo to Done without `--force`. Stories share the machine and override merging is already covered, so no further rows.
- **F2, wording**. No new rows: update the existing assertions on "had drifted" and on the post-migrate line to the new text.
- **BUG-1120, init over an existing squad** (service level). Rows: a second `init --force` over a fresh squad, `sq check` clean, counter 20, no slug-named skill file left; `init --force` over a squad holding a task, the task stays indexed, roles are not duplicated, and the next id follows the highest one.

## Generated output

F6 changes the bundled lifecycle, and F16 changes the CLAUDE.md, AGENTS.md and `sq workflow` renderings. Regenerate the goldens that pin them (`tests/goldens/claude_md_section.txt`, `agents_md_section.txt` and any lifecycle-rendering golden) and the template manifest (`scripts/gen_template_manifest.py`). After release this repo's own CLAUDE.md gains a guides bullet on its next `sq sync`.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST7).

- Fixed: a write that waits on the index lock now says so on stderr. Past the timeout it ends in a one-line error naming the lock file, saying nothing was written and the command can be retried, instead of a traceback.
- Fixed: a body read from `show --json` can be written back with `body --force`, `--append` or an import `body` op. An unchanged, already-placed view tag in it is accepted and kept in place, so a milestone keeps exactly one live roll-up. A view tag that is not placed on the item, or whose state differs, is refused with a message saying to leave the tag line out.
- Added: `sq create <type>` takes one option per field the type declares (for example `sq create bug --severity high`). An omitted field with a declared default stores that default (a new bug gets `severity: medium`). Existing items are unchanged.
- Fixed: a type with two or more authoring roles keeps its Team workflow line in CLAUDE.md and AGENTS.md, naming all of them. Bundled guides now get the line (architect and technical writer).
- Changed: a subtask or story can go from Todo straight to Done. Overrides that redeclare `Todo` are unaffected.
- Changed: sync and check describe a regenerated pointer as "out of date or edited by hand" instead of "had drifted". The post-migrate message says `sq sync` regenerates the agent files.
- Fixed: running `sq init --force` again over an existing squad keeps its items, roles and skills indexed, so `sq check` stays clean and new ids do not collide.
- No migration.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1103 add-subtask "<title>"`; track with `sq task 1103 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Report index-lock waits on stderr and fail a timeout as a clean SquadsError

<!-- sq:subtask:ST1:body -->
Closes REV-1099 F4. Two-step acquire in `IndexStore.transaction()`: about one second, then a one-line stderr notice naming the lock file, then the rest of `lock_timeout`. The final `filelock.Timeout` becomes a `SquadsError` subclass that names the lock file and says nothing was written and the command can be retried, with the locks still released and no traceback. Update the three docstring and comment sites that say the timeout propagates unchanged. Test by holding the lock from a subprocess, and check `--json` stdout stays clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Stop a milestone body write-back from duplicating the roll-up, and name the fix for a view tag

<!-- sq:subtask:ST2:body -->
Closes REV-1099 F5. Builds on FEAT-1108 (TASK-1110): `show --json` `body` there returns the stored text with its raw `sq:view:<name>` tags, so nothing rendered reaches a write-back and no stripping of rendered text is needed. What remains is the write side. In `_body_mutate` (`src/squads/_services/_items.py`), move the view-tag part of the marker check into the closure, where the current region is known: an incoming view tag whose name and enabled/disabled state match a tag already placed in the current `sq:body` region is accepted and dropped from the incoming text, and `place_view_tags` re-places it at its declared position as it does today. `reject_markers` still refuses every other marker before the closure runs. A view tag that is not already placed, or whose state differs, is refused with a message that names the `sq:view:<name>` line, says to leave it out because sq keeps a placed tag in place, and names `view add` / `view disable` only for a type that has those verbs. The same closure serves replace with `--force`, `--append` and the import `body` op. Tests: one table on the view-tag check through replace with `--force` (unchanged write-back, edited prose, moved tag, state mismatch refused, unplaced tag refused, refusal on a type without view verbs, non-view marker, custom type with an override-seeded tag), plus one unchanged write-back row each for `--append` and the import `body` op. The task's Tests section lists the rows.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Expose every declared field as a create option and store a declared default

<!-- sq:subtask:ST3:body -->
Closes REV-1099 F9. `sq create <type>` takes one `--<field-code>` option per field the type declares, against the active spec, for both bundled and custom types. `--priority` stays as the flag for the `priority` field. `_create_core` stores the field's default when the option is omitted, through one `field_default` moved to `ServiceCore`, and the import `create` op shares it. Existing items are not backfilled.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Render a type's Team workflow line for any number of authoring roles

<!-- sq:subtask:ST4:body -->
Closes REV-1099 F16. Add `authoring_owners` (live and titled, in playbook order) and loop over it in `claude_section.md.j2` and `workflow.md.j2`, so two or more authors render as one line naming all of them instead of dropping it. Table over 0 to 3 authors, an off-roster author and an untitled one. Regenerate the CLAUDE.md and AGENTS.md goldens and the manifest.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Word a regenerated pointer and the post-migrate line accurately

<!-- sq:subtask:ST5:body -->
Closes REV-1099 F2, reduced by ADR-1119: with `squads_version` and `version_notice` gone, sync cannot tell an older release's output from a hand edit, so the outdated/drifted split is dropped and no stored version comes back. What is left is wording only. Sync's line becomes `<path>: out of date or edited by hand — regenerated by this sync (backend: <name>)` and `sq check`'s warn line `managed pointer is out of date or edited by hand — run sq sync`; the capability-restriction error keeps its wording. The post-migrate line says `run sq sync to regenerate the agent files (pointers, skills, CLAUDE.md/AGENTS.md sections)`, since `migrate up` regenerates none outside the 0.11 to 0.14 runner. Update the docstrings, `docs/backends.md` and the existing test assertions that quote the old text; no new tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Allow Todo to Done in the bundled sub-entity lifecycle

<!-- sq:subtask:ST6:body -->
Closes REV-1099 F6. Append `Done` to `[lifecycles.subentity.transitions] Todo` in the bundled `workflow.toml`, last, so the happy path is unchanged. A subtask, an operator-assigned one included, and a story then close without `--force`. An override that redeclares `Todo` keeps its own machine. Regenerate the lifecycle-rendering goldens and the manifest.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Write the 0.17.0 CHANGELOG entries for this task's defect fixes

<!-- sq:subtask:ST7:body -->
Covers REV-1099 F4, F5, F9, F16, F6 and F2, and BUG-1120, in the CHANGELOG. Write the entries in the 0.17.0 section from this task's CHANGELOG substance and the developer's handback, describing what an adopter now sees. Mapped to US1 for the board; it covers US1 to US4 and the bug.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Rebuild the index when init --force runs over an existing squad

<!-- sq:subtask:ST8:body -->
Closes BUG-1120. In `init` (`src/squads/_services/_service.py`), when the squad directory already holds an index or item files, rebuild the index from disk with `svc.repair()` after the empty index is written and before roles are activated, as `adopt` does. Existing roles are then found live, existing skills stay indexed, `seed_bundled_skills` skips them correctly, no slug-named `<slug>.md` body file is left behind, and the counter resumes past the highest id, so work items stay indexed and new ids do not collide. A first `init` on an empty directory is unchanged. Tests: the two service-level rows in the task's Tests section.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:40:02Z] `tech-lead` Olivia Lead:
  - Realigned for dispatch: F2 rewritten against ADR-1119 (wording only, ST5), Tests section rewritten as one table per behaviour with boundary and failure rows, BUG-1120 added as ST8 with a fixes ref. FEAT-1108 is Done, so the depends-on is satisfied. Moved Draft to Ready.
- [2026-10-24T20:12:29Z] `python-dev` Elias Python:
  - Implementation done; gates and tests below. ST7 (CHANGELOG) left to the tech writer.
    
    **What changed per subtask**
    - ST1 (F4): `IndexStore` takes the file lock in two steps (`_acquire_file_lock`): about 1 s quiet, one stderr line `waiting for the index lock <path>…`, then the rest of `lock_timeout`. A final timeout raises the new `IndexLockTimeoutError` (`_errors.py`; names the lock file, nothing written, retry). Raised inside the proc-mutex try, so locks are released. `overwrite()` (repair) shares the helper. Docstring/comment sites updated.
    - ST2 (F5): `_body_mutate` checks incoming view tags inside the closure against the tags placed in the current `sq:body` region (`views.unplaced_view_tags`). A matching tag (name and state) is dropped from the incoming text and `place_view_tags` puts it back; any other view tag is refused with a message naming the `sq:view:<name>` line, "leave it out", and the `view add`/`view disable` commands only when the view resolves for that host type. Non-view markers still get the generic refusal (`reject_non_view_markers`). Replace, `--append` and the import `body` op share the closure; the import pre-pass uses the same marker check.
    - ST3 (F9): `sq create <type>` gets one `--<field-code>` option per declared field, resolved against the active spec in `get_params` (static and custom types, aliases). `--priority` is unchanged. The values travel through `ctx.meta` into `svc.create(fields=...)`. `field_default` moved to `ServiceCore`; `_create_model` stores the declared default for every omitted field (bug severity `medium`), which the import `create` op shares. The duplicated custom-type command body now reuses `_make`. `sq create guide` is untouched (guide declares no fields).
    - ST4 (F16): `authoring_owner` replaced by `authoring_owners` (live, titled, lane order from `create_lanes`); both templates loop over it. CLAUDE.md: "The **architect** and the **technical writer** author **guides**"; workflow cheatsheet: "**Architect** or **Technical writer** -> ... `--author architect|tech-writer`".
    - ST5 (F2): sync says `out of date or edited by hand — regenerated by this sync (backend: <name>)`; check warn says `managed pointer is out of date or edited by hand — run sq sync`; the capability-restriction error is unchanged. Post-migrate line says `run sq sync to regenerate the agent files (pointers, skills, CLAUDE.md/AGENTS.md sections)`. `docs/backends.md` updated.
    - ST6 (F6): `Done` appended to `[lifecycles.subentity.transitions] Todo`.
    - ST8 (BUG-1120): `init` rebuilds the index with `svc.repair()` when the squad folder already holds an index or item files, before roles are activated.
    
    **Generated output**: goldens regenerated (`claude_md_section`, `agents_md_section`, `workflow_cheatsheet`, `list`, `tree`, `workflow_lifecycles`; list/tree gain bug `severity: medium` from the new create default); manifest through `gen_template_manifest.py`, then `seed_content_store.py --rebuild` to drop the two superseded 0.17.0 blobs; `--release-gate` passes. Existing tests that asserted the old wording, the old view-tag refusal text, or Todo-to-Done being forbidden were updated.
    
    **Tests added**: store lock wait/timeout (subprocess holder) + one CLI row; view-tag write-back table plus append and import rows; create option table (CLI) and default table (service); authoring owners table + rendered lines; Todo to Done; init over an existing squad (two rows). Each new row was falsified by breaking the fix; two guard rows pass either way (a non-view marker keeps the generic refusal, an existing null field is not backfilled).
    
    **CHANGELOG substance**: as written in this task's CHANGELOG section; two additions worth stating: the create default applies to the import `create` op too, and `sq create` option help lists the collection codes. No migration.
    
    @tech-writer ST7 is yours.
- [2026-10-24T20:12:37Z] `python-dev` Elias Python:
  - Follow-up: git status summary is 22 src files, 6 goldens plus manifest and content store, 8 new test files, ~15 existing tests adjusted. `tests/service/test_index_locking.py` is deleted (unstaged): it asserted the old raw timeout and the new `test_index_lock_wait_and_timeout.py` supersedes it. Nothing committed. Fast gates: pyright, ruff check, ruff format all clean; unit, service, integration, cli and meta green apart from the two tests fixed after the last run (re-run alone, green). Full suite is yours.
- [2026-10-24T20:29:18Z] `tech-writer` Theo Writer:
  - - ST7 done: 0.17.0 CHANGELOG entries written (Added: create field options + stored defaults; Changed: Todo to Done, pointer/post-migrate wording; new Fixed section: index-lock wait/timeout, milestone write-back, multi-author line, repeated `init --force`). Each claim checked in scratch squads on the dev build; the old round-trip and repeated-init behaviour reproduced on released 0.16.
    - Docs: `docs/faq.md` gains a lock wait/timeout entry; `docs/workflow.md` (guides authors, Todo to Done in the sub-entity table, body write-back, create options and defaults); `docs/overrides.md` (create option, field-level default, team workflow line names every author).
    - Outside my scope, for whoever owns README.md: its `sq create` synopsis lists only `--priority`, and its sub-entity line says `Todo → InProgress → Done` without the direct edge.
<!-- sq:discussion:end -->
