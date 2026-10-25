---
id: REV-1139
sequence_id: 1139
type: review
title: 'TASK-1136: help, assignee, JSON, hint, cache fixes'
status: Approved
author: reviewer
refs:
- TASK-1136
description: Review of cda7d0ed
subentities:
- local_id: F1
  title: Help as a spec-declared option's value skips resolution and crashes
  status: Verified
  severity: medium
- local_id: F2
  title: Import update accepts assignee with clear_assignee, and an empty assignee
  status: Verified
  severity: low
- local_id: F3
  title: Clearing an absent assignee still writes on the sub-entity verb and import
  status: Verified
  severity: low
- local_id: F4
  title: Bare item update reports updated and writes (pre-existing)
  status: Verified
  severity: low
- local_id: F5
  title: Three new test rows cannot fail through the code they cover
  status: Verified
  severity: low
- local_id: F6
  title: Diff-relative wording in the verb-help test file
  status: Verified
  severity: info
- local_id: F7
  title: An empty --title corrupts the index beyond sq repair (pre-existing)
  status: Verified
  severity: high
- local_id: F8
  title: An import update event with no field still writes updated_at
  status: Verified
  severity: low
- local_id: F9
  title: Sub-entity add stores a whitespace-only title
  status: Verified
  severity: low
- local_id: F10
  title: A title of only format characters is accepted and renders blank
  status: Verified
  severity: info
- local_id: F11
  title: The CHANGELOG dates the empty-title defect to 0.16.0 without evidence
  status: Verified
  severity: low
created_at: '2026-10-25T09:43:59Z'
updated_at: '2026-10-25T11:06:46Z'
---
<!-- sq:body -->
## Scope

Commit cda7d0ed on release/0.17: verb `--help` without resolving the address, item `--clear-assignee`, `override diff --json` with nothing drifted, the task ref-kind hint, and the spec-keyed custom-type command caches.

## What was driven

Scratch squads, dev tree (`uv run --all-extras sq`):

- `--help` after the verb, after nested `subtask N <verb>`, `comment HASH show`, `ref add`, on group level, on role/skill/operator addresses, with wrong-type and missing numbers, and on a squad behind the schema: all render, exit 0. `-m --help`, `--title --help` and `show -- --help` stay non-help and resolve the address. `-h` is not a help option of this CLI, unchanged.
- `--assignee ""`, whitespace only, `--assignee x --clear-assignee`, `--clear-assignee` alone and with other fields, on items and subtasks; the import `update` event with `clear_assignee` true, false, `"yes"`, `"maybe"`, and with `assignee` alongside.
- `override list --json` and `override diff --json` with no overrides, a current override, a named diff, and a missing name: stdout is always one JSON value on success; errors go to stderr.
- Manifest: only the 0.17.0 `_specs/workflow.toml` hash changed; `gen_template_manifest.py --release-gate` and `seed_content_store.py --check` pass, no blob missing for any key.
- `SpecKeyedCache` in one process over two squads declaring `widget` with different aliases: the other squad's alias is refused, verbs follow the invoked squad. The key is identity on a held reference, so no id reuse; one entry per type name, so no growth across runs. The spec object is new on every invocation, so the cache serves only within one run. The root-context memo was not touched.
- The commit's own tests: 30 passed.

## Result

ST3, ST4 and ST5 hold. ST1 has one shape where an invocation that is not a help request skips resolution and crashes. ST2 holds on the CLI; the import path and the sub-entity verb disagree with it. Findings below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1139 add-finding "…" --severity medium`; track with `sq review 1139 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Help as a spec-declared option's value skips resolution and crashes

<!-- sq:finding:F1:body -->
`HelpAwareGroup.resolve_command` decides whether the verb got `--help` with `help_requested(args[1:], root)`, whose value-option table `_value_options_of` walks only the static command tree. The `--<field-code>` options that sub-entity `add`/`update` build from the live spec are not in that tree. When such an option takes `--help` as its value, Click parses it as a value (not a help request), but the scan reads it as help: the item and sub-entity callbacks skip resolution, `ctx.obj` stays `{}`, and the verb runs without an id.

Reproduction (scratch squad, override `[subentity_kinds.finding] fields = [{ code = "impact", label = "Impact", collection = "severity", required = true, default = "medium" }]`):

    sq create review R --author manager          # REV-2
    sq review 2 add-finding F1 --impact high
    sq review 2 finding 1 update --impact --help
    # exit 1, traceback ending in KeyError: 'id'

Before this commit the address resolved first and the value reached the field check, which refuses it cleanly (inferred from the code, not driven on the parent commit). The same skip also lets `sq review 999 add-finding X --impact --help` run without checking 999 exists; it is stopped only because no badge code is `--help`.

Expected: an invocation that is not a help request always resolves its address. Decide from the leaf command Click actually resolved (its own params, including spec-built ones), not from a table of static option names; add a row where `--help` is the value of a spec-declared option.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T09:59:58Z] `python-dev` Elias Python:
  - Fixed: an address that fails to resolve while help looks requested is deferred (UnresolvedAddress) and raised on first read, so a non-help call never runs without it; row added for --help as a spec-declared option value
- [2026-10-25T10:12:56Z] `reviewer` Paul Reviewer:
  - Verified on 6935e9b1: rev1136/f repro now exits 1 with 'unknown severity' (existing review) or 'no item with number 999', no traceback. The deferred error survives nested sub-entity and comment-hash callbacks (extend_obj); no ctx.obj.get or dict copy left that would swallow it. A non-help call cannot succeed unresolved: only spec-built badge options are misread, and their value --help is always refused.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Import update accepts assignee with clear_assignee, and an empty assignee

<!-- sq:finding:F2:body -->
The CLI now refuses `--assignee x --clear-assignee` and an empty `--assignee`, but the import `update` event accepts both shapes and clears silently.

    {"op":"update","target":"TASK-22","assignee":"qa","clear_assignee":true,"as":"tech-lead"}
    # imported 1 event(s); assignee removed, "qa" never checked
    {"op":"update","target":"TASK-22","assignee":"","as":"tech-lead"}
    # imported 1 event(s); assignee removed

`Service._update_model` gives `clear_assignee` precedence over `assignee`, and still maps `assignee=""` to a clear. So an import file can contradict itself and get no issue line, and there are two spellings of a clear where the CLI allows one.

Expected: the import check phase reports both shapes as issues, with the same meaning as the CLI refusals, and nothing is written.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T10:00:00Z] `python-dev` Elias Python:
  - Fixed: UpdateEvent refuses an empty assignee and assignee with clear_assignee as import issues
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Clearing an absent assignee still writes on the sub-entity verb and import

<!-- sq:finding:F3:body -->
On an item, `--clear-assignee` with no assignee now prints `<ID> has no assignee to clear` and writes nothing. The sub-entity verb and the import event do not follow:

    sq task 22 add-subtask S2
    sq task 22 subtask 2 update --clear-assignee
    # "updated TASK-22 ST2", updated_at bumped in the file

    {"op":"update","target":"TASK-22","clear_assignee":true,"as":"tech-lead"}   # item unassigned
    # "imported 1 event(s)", updated_at bumped

The task aligned the two verbs on the empty-assignee refusal; the no-op case is left split, so the same flag reports a write on one verb and not on the other.

Expected: a clear on something with no assignee is a no-op on every path: no write, no "updated".
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T10:00:03Z] `python-dev` Elias Python:
  - Fixed: a clear with no assignee writes nothing on the sub-entity verb and the import update event
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Bare item update reports updated and writes (pre-existing)

<!-- sq:finding:F4:body -->
Not introduced by this commit, but the same defect class as ST2 and next to its code. `sq <type> <n> update` with no option prints `updated <ID>` and bumps `updated_at`:

    sq task 22 update
    # updated TASK-22  tasks/TASK-000022-t-two.md; only updated_at changes

The sub-entity verb refuses the same call with `nothing to update (pass at least one field ...)` through `_guard_update`; the item verb has no such guard. The task goal says the CLI never reports a change it did not make.

Expected: the item verb refuses an empty update the way the sub-entity verb does. Needs a home if not fixed here.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T10:00:05Z] `python-dev` Elias Python:
  - Fixed: a bare item update fails with nothing to update and writes nothing; CHANGELOG line added
- [2026-10-25T10:12:57Z] `reviewer` Paul Reviewer:
  - Verified: bare update and update --force alone now exit 1 'nothing to update', file unchanged; the CHANGELOG line is true as written.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Three new test rows cannot fail through the code they cover

<!-- sq:finding:F5:body -->
Three rows that cannot fail through the code they cover:

- No row pins the value boundary of the help hook. Replacing `help_requested(args[1:], ...)` in `HelpAwareGroup` with a plain `"--help" in args` keeps every new test green, although `sq task 22 comment --as qa -m --help` would then skip resolution and crash. A row where `--help` is an option's value (static, and spec-declared per the help-hook finding) belongs in the ST1 table.
- `test_create_in_a_later_run_uses_the_squad_it_names`: `_build_create_cmd` does not read the spec (field options come from `get_params` at parse time, the folder from the service), so the old class-level dict passes this test too. The handback already says the create cache has no observable row; then the test should not exist as coverage of it.
- The `("a","wa"), ("a","wa")` row passes by rebuilding: the spec object is new on every invocation, so `SpecKeyedCache` never hits across runs. It proves the same squad keeps answering, not that the cache serves it.

Also, the ST1 test file splits one behaviour across four functions (help table, wrong-type, behind-schema help, behind-schema gate) where one table with a squad column would do.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T10:00:07Z] `python-dev` Elias Python:
  - Fixed: value-boundary row added, create-cache row and same-squad row dropped (no input fails them), ST1 tests folded into one table
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Diff-relative wording in the verb-help test file

<!-- sq:finding:F6:body -->
Prose in the new tests that only makes sense next to the diff:

- `tests/cli/test_verb_help_renders_without_a_resolvable_address_cli.py` module docstring: "Without `--help` the same commands still fail as before."
- Test names `test_a_number_of_another_type_is_still_refused_without_help` and `test_a_squad_behind_the_package_is_still_gated_without_help`: "still".

A reader without the diff cannot see the "before". State the present rule: without `--help` the address is resolved, and a wrong-type number or a behind-schema squad is refused.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T10:00:10Z] `python-dev` Elias Python:
  - Fixed: test names and docstrings state the present rule
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — An empty --title corrupts the index beyond sq repair (pre-existing)

<!-- sq:finding:F7:body -->
Existed before this commit (reproduced on the released 0.16.0), found while probing the new "nothing to update" guard. `sq <type> <n> update --title ""` is accepted: it prints `updated <ID>`, renames the file to `*-untitled.md` and writes `title: ''`. The index model requires a non-empty title, so the next command on the squad fails:

    sq create task T --author manager      # TASK-2
    sq task 2 update --title ''
    # updated TASK-2  tasks/TASK-000002-untitled.md
    sq list
    # error: corrupt index .squads.json (1 problem(s)); run `sq repair` ...
    sq repair
    # error: ... title: String should have at least 1 character ... fix the file and repair again

One CLI call leaves every command failing, `sq repair` cannot recover it, and the only fix is a hand edit of the item file. An import `update` event with `"title": ""` does the same. Related shapes: `--title "   "` is accepted and stores a blank title; the sub-entity `update --title ""` answers `nothing to update` although a field was passed (the shape BUG-1085 fixed for `--assignee`); `sq create task ''` fails with a raw pydantic message and URL.

Expected: an empty or whitespace-only title is refused before any write, on item and sub-entity `update`, on `create` and on import, with a message naming the flag.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-25T10:33:52Z] `python-dev` Elias Python:
  - Fixed: require_title at create, item rename and sub-entity update (import reaches them); blank title fails with 'title must not be empty', exit 1, no write. '!!!' is valid (untitled slug) and repair rebuilds it; the unrecoverable case was a hand-invalid empty title in frontmatter.
- [2026-10-25T10:45:00Z] `reviewer` Paul Reviewer:
  - Verified on 9b2ec16e: empty, spaces, NBSP, em space, newline and tab are refused on create, item update, subtask update, import create and update, role update and operator/skill add; the index stays loadable throughout. '!!!' is stored and survives repair. Retype and rename do not set titles.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — An import update event with no field still writes updated_at

<!-- sq:finding:F8:body -->
The import analogue of the bare-update fix: an `update` event that names only its target is applied and rewrites the item's `updated_at`.

    {"op":"update","target":"TASK-2","as":"manager"}
    # update: 1, imported 1 event(s); file changed (updated_at only)

The CLI now refuses the same request with `nothing to update`, and an import clear with nothing to clear already writes nothing.

Expected: the check phase reports an `update` event with no field as an issue, and nothing is written.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-25T10:33:54Z] `python-dev` Elias Python:
  - Fixed: an import update event naming no field is an issue (nothing to update); nothing written.
- [2026-10-25T10:45:01Z] `reviewer` Paul Reviewer:
  - Verified: an update event with no field, only force, clear_assignee false or an empty add_labels is now an issue and nothing is written.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Sub-entity add stores a whitespace-only title

<!-- sq:finding:F9:body -->
Adding a sub-entity with no title is a designed, tested state (`title: ''`, a body-only story), and it is sound: the sub-entity model stores an empty title and the index loads it. The gap is the third shape. `add-story '   '` is accepted and stores `title: '   '`, a title that is neither empty nor readable:

    sq feature 6 add-story '   '
    # stored as   title: '   '   (renders blank in the roll-up table)

`update --title '   '` on the same story is now refused with `title must not be empty`, so add and update disagree on whitespace. `update --title ''` is refused as well, so a story created without a title cannot be returned to that state.

Expected: sub-entity add normalises a whitespace-only title to the empty title (or refuses it), so the stored states are a real title or none.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-25T10:56:27Z] `python-dev` Elias Python:
  - Fixed: a blank sub-entity title is stored as none on add and update (subentity_title); head and summary render after the clear (show --full row)
- [2026-10-25T11:05:43Z] `reviewer` Paul Reviewer:
  - Verified on d7927710: spaces, ZWSP, BOM and mixed blanks on add-story, story update and an import add-story event all store title ''; update --title '' returns a story to no title.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A title of only format characters is accepted and renders blank

<!-- sq:finding:F10:body -->
`require_title` tests `title.strip()`, which handles Unicode whitespace (NBSP, em space, newline and tab are all refused, as driven). A title made only of format characters, which Python does not treat as whitespace, is accepted on create, item update and sub-entity update:

    sq create task $'​' --author manager    # zero-width space -> TASK-3, files as -untitled.md
    sq create task $'﻿' --author manager    # BOM -> TASK-4

Both round-trip through `sq repair`, so this does not corrupt anything. They show as blank titles in `sq list` and the roll-ups. Info: treat Unicode format characters (category Cf) as blank in the guard if that is the intent of "empty".
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-25T10:56:30Z] `python-dev` Elias Python:
  - Fixed: one is_blank helper (whitespace or Cf) behind require_title and subentity_title
- [2026-10-25T11:05:44Z] `reviewer` Paul Reviewer:
  - Verified: ZWSP, BOM, ZWSP+space and a lone soft hyphen are refused on create and import create; 'x' followed by ZWSP is accepted.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The CHANGELOG dates the empty-title defect to 0.16.0 without evidence

<!-- sq:finding:F11:body -->
The new CHANGELOG entry opens "Since 0.16.0, `sq <type> <n> update --title ''` printed `updated` ...". I reproduced the defect on 0.16.0 only, and that does not show it started there. `Item.title` has been `NonEmpty` since v0.1.0, and the update path passes `title` straight through with `if title is not None` in v0.12.0, v0.14.0 and v0.15.0 (read, not driven). So the defect very likely predates 0.16.0.

Expected: drop the version, or state only what was shown ("In 0.16.0 and earlier releases"). The CHANGELOG belongs to the tech writer.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-25T10:56:32Z] `python-dev` Elias Python:
  - Fixed: CHANGELOG says 'In earlier releases', no version named
- [2026-10-25T11:05:45Z] `reviewer` Paul Reviewer:
  - Verified: the entry says 'In earlier releases', and each of its claims holds as driven.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T09:44:30Z] `reviewer` Paul Reviewer:
  - Verdict: changes requested. F1 is a crash on a non-help invocation; F2-F3 leave the import and sub-entity paths out of step with the new CLI rule; F4 needs a home; F5-F6 are test hygiene. @tech-lead
- [2026-10-25T10:13:08Z] `reviewer` Paul Reviewer:
  - Re-review of 6935e9b1: F1-F6 Verified (driven; 28 targeted tests pass). CHANGELOG lines for clear-assignee and bare update are true as written. Not approved: F7 (high, pre-existing) and F8 (low) are new. F7 needs a fix or a named home before this review settles. @manager
- [2026-10-25T10:45:08Z] `reviewer` Paul Reviewer:
  - Re-review of 9b2ec16e: F7 and F8 Verified (25 targeted tests pass). Not approved yet: F9 (low), F10 (info) and F11 (low, a CHANGELOG claim) are new and open. @manager
- [2026-10-25T11:05:46Z] `reviewer` Paul Reviewer:
  - Settling pass on d7927710: F1-F11 all Verified, 40 targeted tests pass, nothing material open. Recommended verdict: Approved. I am leaving the transition to the approver because I authored this review (two-party gate). @manager
- [2026-10-25T11:06:13Z] `manager` Catherine Manager:
  - Approved: F1-F11 Verified by the reviewer at d7927710; full suite green (14168 passed).
- [2026-10-25T11:06:46Z] `manager` Catherine Manager:
  - Approved: F1-F11 Verified by the reviewer at d7927710; full suite green (14168 passed).
<!-- sq:discussion:end -->
