---
id: TASK-1103
sequence_id: 1103
type: task
title: Fix lock contention, milestone round-trip, create fields, sync wording
status: Draft
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
- FEAT-1108:depends-on
description: Defects F4, F5, F9, F16, F6 and F2 from REV-1099.
subentities:
- local_id: ST1
  title: Report index-lock waits on stderr and fail a timeout as a clean SquadsError
  status: Todo
  story: US1
- local_id: ST2
  title: Stop a milestone body write-back from duplicating the roll-up, and name the
    fix for a view tag
  status: Todo
  story: US2
- local_id: ST3
  title: Expose every declared field as a create option and store a declared default
  status: Todo
  story: US2
- local_id: ST4
  title: Render a type's Team workflow line for any number of authoring roles
  status: Todo
  story: US3
- local_id: ST5
  title: Call an older release's pointer outdated, and say what sync still does after
    migrate
  status: Todo
  story: US3
- local_id: ST6
  title: Allow Todo to Done in the bundled sub-entity lifecycle
  status: Todo
  story: US4
- local_id: ST7
  title: Write the 0.17.0 CHANGELOG entries for this task's defect fixes
  status: Todo
  assignee: tech-writer
  story: US1
created_at: '2026-10-24T10:04:00Z'
updated_at: '2026-10-24T13:20:02Z'
---
<!-- sq:body -->
## Goal

Fix six defects from the adopter field report (REV-1099): F4, F5, F9, F16, F6 and F2. Each subtask names the finding it closes and holds the approach. The finding bodies on REV-1099 carry the reproductions.

## Approach

- **F4, index-lock contention** (`src/squads/_index/_store.py`). `IndexStore.transaction()` acquires the Layer 3 `FileLock` on a worker thread with the constructor's `lock_timeout` (10 s). Acquire in two steps: a first try bounded at about one second, then, if that times out, one line on stderr (`waiting for the index lock <path>…`) and a second try for the rest of the timeout. A final `filelock.Timeout` becomes a new `SquadsError` subclass in `src/squads/_errors.py`. Its one-line message names the lock file, says nothing was written and says the command can be retried. Raise it inside the Layer 3 `try` so the proc-mutex and loop lock are still released. Update the three places that say a `filelock.Timeout` "propagates unchanged" (module docstring, `transaction()` docstring, the inline comment). The notice goes to stderr only, so `--json` stdout stays clean. `sq import -` holds one transaction, so it gets the same behaviour. The daemon (ADR-1052, not built) inherits this path, which already lives in the store.
- **F5, milestone body round-trip** (`src/squads/_services/_items.py`, `src/squads/_services/_base.py`). Builds on FEAT-1108 (TASK-1110): `show --json` `body` returns the stored text with its raw `sq:view:<name>` tags, so a write-back carries no rendered roll-up and nothing has to be stripped. The remaining fix is on the write side. In `_body_mutate`, the view-tag part of the marker check moves into the mutate closure, where the current `sq:body` region is known. An incoming view tag whose name and enabled/disabled state match a tag already placed in that region is accepted and dropped from the incoming text, and `place_view_tags` re-places it at its declared position. `reject_markers` keeps refusing every other marker before the closure runs. A view tag that is not already placed, or whose state differs, is refused with a message that names the `sq:view:<name>` line, says to leave it out because sq keeps a placed tag in place, and names `view add` / `view disable` only for a type that has those verbs. Replace with `--force`, `--append` and the import `body` op share this closure and get the same behaviour.
- **F9, create sets every declared field** (`src/squads/_cli/_create.py`, `src/squads/_services/_base.py`, `src/squads/_services/_subentities.py`). Replace the hardcoded `--priority` option with one `--<field-code>` option per field the type declares (`spec.fields_for(type)`). This mirrors what `_register_add` in `src/squads/_cli/_items.py` already does for `add-<kind>`, with help derived from the field's collection. Both the static per-type commands and `_build_create_cmd` / `_CustomCreateGroup` for custom types need it, resolved against the active spec, not the bundled one (`spec_aware_command_cls`). Values go through `svc.create(..., fields=...)`. Keep `--priority` as the flag for the `priority` field so existing scripts keep working. Defaults: `_create_core` stores `field_default(type, code)` for every omitted declared field that has one. Move `field_default` from the `_subentities` mixin to `ServiceCore` so create and add share one resolver. The import `create` op goes through `_create_core` and gets the same default. Existing items are not backfilled: frontmatter is the truth, and a null stays null until it is set.
- **F16, any number of authors** (`src/squads/_interactions/__init__.py`, `templates/claude/claude_section.md.j2`, `templates/workflow.md.j2`). `authoring_owner` returns `None` when `in_lane_owner` yields more than one slug, so the bullet disappears. Add `authoring_owners(...)`, which returns every live, titled in-lane owner with the same roster and title resolution. `in_lane_owner` returns a set, so take the order from the playbook (`create_lanes`) to keep the rendered line stable. Then make both templates loop over it. CLAUDE.md: "The **architect** and the **technical writer** author **guides** …" (a comma list with "and" for three or more). `workflow.md.j2`: one `--author` command per owner, or the slugs joined, whichever reads cleanly. Remove `authoring_owner` if nothing else calls it after this. Update the docstring that says a second author is ambiguous.
- **F6, operator subtasks close without --force** (`src/squads/_specs/workflow.toml`). Append `"Done"` to `[lifecycles.subentity.transitions] Todo`. It goes last, so the happy path (the first edge, `Todo → InProgress`) does not change. Stories share the `subentity` machine and gain the edge too, which is the ordinary case for them as well. An override that redeclares `Todo` keeps its own list.
- **F2, outdated versus drifted** (`src/squads/_services/_maintenance.py`, `src/squads/_services/_validators.py`, `src/squads/_cli/_migrate.py`, `src/squads/_cli/_common.py`). `_entry_drift_report` compares content only. Read the recorded `squads_version` from `.squads.toml` before sync stamps it. When it is older than the running version, word the line `outdated (generated by squads <old>) — regenerated by this sync`, and keep `had drifted` otherwise. Apply the same split to `sq check`'s pointer-drift line (`backend_entry_drift`, around line 1381). After `migrate up`, the `run sq sync to refresh managed files` line and `version_notice` should name what is left for sync to do. First establish from the code which files `migrate up` already regenerates (CLAUDE.md and skills per the review) and which only sync writes (agent pointers, the version stamp), then word the message from that, not from the review's guess.

## Tests

Service-level plus a CLI smoke per finding. Run `tests/meta`, `tests/integration` and `tests/cli` whatever else you select, because bundled specs and templates change. Falsify each new test: break the fix, watch it go red, restore it.

- F4: hold the lock from a **subprocess** (not a second in-process `FileLock`) with a small `lock_timeout`. Assert the stderr notice, the one-line error, exit 1, no `Traceback`, and nothing written. A second case releases the lock during the wait and the write lands after the notice. A third checks that `--json` stdout carries no notice.
- F5: table over body shapes × write mode (replace with `--force`, `--append`, import `body` op). Accepted: the `show --json` body written back unchanged (item file byte-identical), that body with edited prose, the placed tag moved to another line (re-placed at its declared position), the placed tag alone, and prose that merely mentions the roll-up headings; each leaves exactly one rendering in `show --full`. Refused, with the wording asserted: the tag disabled in the incoming text while enabled on disk, and a tag of an undeclared view or one not placed on this item. A non-view marker keeps the generic refusal.
- F9: table over types × fields: bug severity, priority on task, a custom type with its own badge field from an override, a type with no fields. Cases: flag given, omitted with a declared default (stored), omitted without one (null), invalid code (refused). `create --help` lists the options. The import `create` path stores the default.
- F16: table over 0/1/2/3 in-lane authors, with one author off the live roster, and one with no resolvable title. Assert both rendered surfaces.
- F6: an operator-assigned subtask and a story go Todo → Done without `--force`. A project override that redeclares `Todo` keeps its own machine.
- F2: the older-recorded-version case says outdated, a hand edit at the current version says drifted, for sync and check. Assert the post-migrate wording names what sync still writes.

## Generated output

F6 changes the bundled lifecycle, and F16 changes the CLAUDE.md, AGENTS.md and `sq workflow` renderings. Regenerate the goldens that pin them (`tests/goldens/claude_md_section.txt`, `agents_md_section.txt` and any lifecycle-rendering golden) and the template manifest (`scripts/gen_template_manifest.py`). After release this repo's own CLAUDE.md gains a guides bullet on its next `sq sync`. TASK-1106 (F14) and TASK-1098 also change `claude_section.md.j2`, so sequence goldens and manifest regeneration rather than running them in parallel.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST7).

- Fixed: a write that waits on the index lock now says so on stderr. Past the timeout it ends in a one-line error naming the lock file, saying nothing was written and the command can be retried, instead of a traceback.
- Fixed: a body read from `show --json` can be written back with `body --force`, `--append` or an import `body` op. An unchanged, already-placed view tag in it is accepted and kept in place, so a milestone keeps exactly one live roll-up. A view tag that is not placed on the item, or whose state differs, is refused with a message saying to leave the tag line out.
- Added: `sq create <type>` takes one option per field the type declares (for example `sq create bug --severity high`). An omitted field with a declared default stores that default (a new bug gets `severity: medium`). Existing items are unchanged.
- Fixed: a type with two or more authoring roles keeps its Team workflow line in CLAUDE.md and AGENTS.md, naming all of them. Bundled guides now get the line (architect and technical writer).
- Changed: a subtask or story can go from Todo straight to Done. Overrides that redeclare `Todo` are unaffected.
- Changed: sync and check call a pointer from an older release "outdated", not "drifted". The post-migrate message says what `sq sync` still has to do.
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
Closes REV-1099 F5. Builds on FEAT-1108 (TASK-1110): `show --json` `body` there returns the stored text with its raw `sq:view:<name>` tags, so nothing rendered reaches a write-back and no stripping of rendered text is needed. What remains is the write side. In `_body_mutate` (`src/squads/_services/_items.py`), move the view-tag part of the marker check into the closure, where the current region is known: an incoming view tag whose name and enabled/disabled state match a tag already placed in the current `sq:body` region is accepted and dropped from the incoming text, and `place_view_tags` re-places it at its declared position as it does today. `reject_markers` still refuses every other marker before the closure runs. A view tag that is not already placed, or whose state differs, is refused with a message that names the `sq:view:<name>` line, says to leave it out because sq keeps a placed tag in place, and names `view add` / `view disable` only for a type that has those verbs. The same closure serves replace with `--force`, `--append` and the import `body` op. Tests, table-driven over body shapes × write mode (replace with `--force`, `--append`, import `body` op): the `show --json` body written back unchanged (file byte-identical, `show --full` shows one roll-up); that body with edited prose (prose changes, one roll-up); the tag moved to another line (re-placed at its declared position); the tag alone; the tag disabled in the incoming text while enabled on disk (refused); a tag of an undeclared view or one not placed on this item (refused, wording asserted); a non-view marker (generic refusal unchanged); prose that only mentions the roll-up headings (accepted as prose). Run the round trip on a milestone and on a custom type whose override seeds its own view tag. A system role or skill body stays refused by the roster rule, which `--force` never lifts.
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
### ST5 — Call an older release's pointer outdated, and say what sync still does after migrate

<!-- sq:subtask:ST5:body -->
Closes REV-1099 F2. Sync and `sq check` read the recorded `squads_version` before stamping. A pointer regenerated over an older release's output is reported as `outdated (generated by squads <old>)`, and a hand edit at the current version still as `had drifted`. The post-migrate line and `version_notice` name what only sync writes, established from the code first.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Allow Todo to Done in the bundled sub-entity lifecycle

<!-- sq:subtask:ST6:body -->
Closes REV-1099 F6. Append `Done` to `[lifecycles.subentity.transitions] Todo` in the bundled `workflow.toml`, last, so the happy path is unchanged. An operator-assigned subtask, and a story, then close without `--force`. An override that redeclares `Todo` keeps its own machine. Regenerate the lifecycle-rendering goldens and the manifest.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Write the 0.17.0 CHANGELOG entries for this task's defect fixes

<!-- sq:subtask:ST7:body -->
Covers REV-1099 F4, F5, F9, F16, F6 and F2 in the CHANGELOG. Write the entries in the 0.17.0 section from this task's CHANGELOG substance and the developer's handback, describing what an adopter now sees. Mapped to US1 for the board; it covers US1 to US4.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
