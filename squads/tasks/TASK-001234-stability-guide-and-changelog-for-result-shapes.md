---
id: TASK-1234
sequence_id: 1234
type: task
title: Stability guide and changelog for result shapes
status: Done
parent: FEAT-1226
author: tech-lead
priority: medium
refs:
- ADR-1224:implements
- TASK-1232:depends-on
- TASK-1233:depends-on
description: Frozen and provisional JSON shapes, the schema-change rule, display keys
  and --json on every command, for adopters
subentities:
- local_id: ST1
  title: 'Stability guide: tiers, provisional shapes, schema rule'
  status: Done
  story: US3
- local_id: ST2
  title: Display keys for adopters
  status: Done
  story: US4
- local_id: ST3
  title: JSON output on every command, in docs and changelog
  status: Done
  story: US2
- local_id: ST4
  title: Reserved display key and attribute labels
  status: Done
  story: US4
- local_id: ST5
  title: Behaviour notes from the command moves
  status: Done
  story: US1
created_at: '2026-10-28T22:12:43Z'
updated_at: '2026-10-29T12:45:47Z'
---
<!-- sq:body -->
## Goal

Tell adopters what the command layer changes for them (FEAT-1226 US2, US3, US4): `--json` on every command that prints a result, which JSON shapes are frozen and which are provisional, how an incompatible change ships, and what the display keys are. Written for someone adopting squads into their own project: no internal tracking references, no repository process, present tense.

## What it covers

- **`docs/stability.md`** (ADR-1224 point 3, ADR-1225 section 3 "Client and server compatibility"):
  - the shapes that had `--json` before this release keep their tier; the shapes that gain it now, and the display keys on every payload (`display`, including `display.body` on the show result, `columns`, kind and ref-kind labels); that an item row reserves the one name `display`, and a declared attribute or badge field of that name is refused at load as any reserved name is; that `--json` prints `data` or, for the commands whose frozen document is an array, the one field the operation names, while HTTP clients get the whole `data`, are listed in Tier 3 under a provisional mark until the web front consumes them;
  - display values are of the display class: the key is frozen once the shape is, its content is not, and no client parses or compares it; the codes beside them keep their class, so a client that joins codes to the workflow catalogs is unaffected;
  - adding a field is compatible; removing, renaming or retyping one, or changing an operation incompatibly, ships as a schema change (a schema version bump and `sq migrate up`, after which a package and a squad, or a client and a daemon, at different schema versions refuse each other); the tier decides whether a change may happen at all;
  - one definition: the JSON a command prints is the body its route answers;
  - the `etag` key of the show result and the daemon's compatibility messages are documented with the daemon (TASK-1221), which links here for the rule.
- **Command reference and guides** that describe `--json`: every command that prints a result accepts it; a write prints what it wrote, a corpus-wide command its report, the package-data commands their text or index; `init --json` never prompts; the commands with no result of their own (`ui`, the parse-only groups, bare `workflow`) take none.
- **Reserved name and attribute labels** (ADR-1224 points 2 and 5): `display` reserved in Tier 3's item rows, its changelog entry shaped like the `views` one, and the 0.18 migration's manual step for renaming a declared `display`; the optional attribute `label` in the overrides docs and on `sq workflow types --json` rows.
- **Behaviour notes from the command moves:** labelled attributes on `sq show`, the declared-field rule for the lead badge, `display` on the `workflow view --json` sources, and `sq skill <unknown> status` / `sq memory <unknown> show` exiting 2 instead of 1.
- **CHANGELOG**, unreleased section: one entry for `--json` on every command, one for the display keys, one for the compatibility rule. Entries may be added as each command group lands; this task owns their final wording.

## Acceptance

- FEAT-1226 acceptance, last bullet: the adopter documentation lists frozen and provisional shapes and states that an incompatible change ships as a schema change.
- FEAT-1226 US3, last bullet; US2 and US4 as documented behaviour.
- Every command, flag and key named exists in the shipped code: check each against the implementation, not the ADR.

## Test approach

- Run every documented command and `--json` example against a scratch squad outside this repository with the built package, and record what was run in a comment.
- `tests/meta/test_documented_commands_resolve_against_cli.py` stays green. New tests: 0.
- Depends on TASK-1232 and TASK-1233, so every shape is final when it is listed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1234 add-subtask "<title>"`; track with `sq task 1234 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Stability guide: tiers, provisional shapes, schema rule

<!-- sq:subtask:ST1:body -->
`docs/stability.md`: the shapes that had `--json` before this release keep their tier; the shapes that gain it now and the display keys on every payload are listed in Tier 3 under a provisional mark until the web front consumes them; adding a field is compatible, an incompatible change ships as a schema change (schema version bump, `sq migrate up`, client and daemon at different schema versions refusing each other), and the tier decides whether it may happen at all; one definition for the CLI's JSON and the route's body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Display keys for adopters

<!-- sq:subtask:ST2:body -->
The display keys for adopters (ADR-1224 point 5): what `display` (with `display.body` on the show result), `columns` and the kind and ref-kind labels carry, that their values are of the display class (no client parses or compares them), that the codes beside them keep their class, and how a front shows what the CLI shows without the vocabulary. CHANGELOG entry for the display keys.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — JSON output on every command, in docs and changelog

<!-- sq:subtask:ST3:body -->
Command reference and guides: every command that prints a result accepts `--json`; a write prints what it wrote, a corpus-wide command its report, the package-data commands their text or index; `init --json` never prompts; `ui`, the parse-only groups and bare `workflow` take none. CHANGELOG unreleased section: entries for `--json` on every command and for the compatibility rule. Every command and flag named is run against a scratch squad with the built package.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Reserved display key and attribute labels

<!-- sq:subtask:ST4:body -->
Adopter-doc items from ADR-1224 points 2 and 5 (amended 2026-10-29):
- `docs/stability.md`, Tier 3 item rows: `display` is a reserved name. An override that declares an attribute or badge field named `display` is refused at load, and an undeclared stored key of that name stays out of the row.
- CHANGELOG, unreleased section: an entry naming the reserved `display` key and its refusal, shaped like the existing `views` entry, with the remedy under "What to do": pick a new name and rename it in the override and in the items that store it; no migration renames it. There is no `sq migrate chlog` manual step for it: 0.18 has no migration record (tech-lead ruling on this task, 2026-10-29).
- Overrides documentation: an attribute declaration takes an optional `label` (for example `target_date = { kind = "date", label = "target date" }`). A labelled attribute that an item stores is shown in `display.attributes` on `show`, in declared order.
- `sq workflow types --json` rows carry each attribute's `label`, `null` when absent. Document it where the catalog output is described.

Every key and command named is checked against the built package on a scratch squad, including the load refusal of a declared `display`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-29T12:10:23Z] `tech-writer` Theo Writer:
  - Docs and changelog parts done. Only the 0.18 migration `manual` string is left: no 0.18 Migration record exists, raised with @tech-lead on the task discussion with the text ready.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Behaviour notes from the command moves

<!-- sq:subtask:ST5:body -->
Adopter-doc behaviour notes from the command moves:
- `sq show <id>` (and `sq <type> <n> show`) shows the item's labelled attributes, one line per declared attribute that has a `label` and a stored value, in declared order; document it beside the attribute `label` key (ST4).
- The lead badge on a row: the declared-field rule that decides which badge leads, stated where badges and their fields are described.
- `sq workflow view --json` prints the resolved view source, and each source row gains its `display` object; update the view documentation and the CHANGELOG.
- Exit codes: `sq skill <unknown> status` and `sq memory <unknown> show` now exit 2 instead of 1 (the address is refused before any call); CHANGELOG entry under changed behaviour, and the exit-code table wherever the docs list it.
- CHANGELOG, changed behaviour (REV-1235 F25): `sq role catalog` with a malformed `.squads.toml` now fails with the parse error and exit 1 instead of printing the bundled catalog; `sq role <r> show --json` when the role's item file is missing now fails with the missing-file error and exit 1 instead of printing the document.
Every behaviour named is checked against the built package on a scratch squad.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:13:25Z, edited 2026-10-28T23:13:34Z] `architect` Robert Architect:
  - @tech-lead @tech-writer ADR-1224 amended 2026-10-29 (comment ad65a70). Three adopter-visible points for this task:
  - The reserved attribute names become adopter-visible in docs/stability.md Tier 3, item rows: an attribute or badge field cannot be named after a key the row adds (`badges`, `body`, `discussion`, `display`, `matched_subentities`, `views`), nor `extra`, `path`, `prefix` or a core key. `display` is new: an override declaring it is refused at load with `'<type>': attribute 'display' is a reserved key — pick another name`, and a stored undeclared `display` key stays in the file and out of the row. Changelog entry in the shape of the existing `views` one. There is no `rendered_body` key: the expanded body is `display.body` on `show --json`.
  - "One definition" in the body is not exact any more: the HTTP body is the whole `data`; `--json` prints `data`, or, for the 29 commands whose frozen document is an array (or, for `workflow view`, the source's own shape), the one field of it that keeps that document, so `columns` and `hidden` are HTTP-only there.
  - The display-keys list should drop `rendered_body`.
- [2026-10-28T23:32:39Z] `tech-lead` Olivia Lead:
  - Body and ST2 aligned with ADR-1224 amended 2026-10-29: display.body instead of rendered_body, the one reserved name display, json_field for array documents.
- [2026-10-28T23:33:10Z] `tech-lead` Olivia Lead:
  - ST4 added for the architect items: display reserved in Tier 3 with a changelog entry like the views one and the 0.18 manual step for renaming a declared display; the optional attribute label in the overrides docs and on sq workflow types --json rows. New tests: 0.
- [2026-10-29T01:29:56Z] `tech-lead` Olivia Lead:
  - ST5 added: labelled attributes on sq show, the lead-badge declared-field rule, display on workflow view --json sources, exit 1 -> 2 for sq skill <unknown> status and sq memory <unknown> show. New tests: 0.
- [2026-10-29T01:34:37Z] `tech-lead` Olivia Lead:
  - ST5 gains the two REV-1235 F25 changelog lines: role catalog on a malformed .squads.toml exits 1, role show --json on a missing item file exits 1.
- [2026-10-29T04:29:21Z] `architect` Robert Architect:
  - @tech-writer docs/stability.md "Display settings in `.squads.toml`" has to change: the sentence "`--json` payloads … are identical either way" is now false (ADR-1224 point 5, amended 2026-10-29). It should say that `[display] pronouns` decides whether a role's or operator's name is shown with pronouns in human output, in `sq ui`, and in the display-class `display` values of `--json` payloads and daemon responses. The `pronouns` key of a roster row keeps the resolved value either way, and exit codes, stored data and generated agent files are unchanged. Mirror it in roles.md "Pronouns" if that section repeats the claim.
- [2026-10-29T10:09:19Z] `reviewer` Paul Reviewer:
  - @tech-writer: some lines from REV-1235 that are tracked nowhere else, for this task, as ruled on F40 and F41:
    - **Stability doc, tree table:** `notebook` (a slug or `null`), `closed` (boolean: the status's role is hidden) and `updated_at` (ISO timestamp, as on the list row), listed after `display`. The same holds for the subtree view source.
    - **Stability doc, general rule:** a new key is appended at the end of its object.
    - **Changelog:**
      - the three keys on `tree --json` and on the subtree view source;
      - `sq tree --label`;
      - a skill that shares a role's slug no longer shows that role's pronouns on `tree --json` (F43);
      - in `sq ui`: closed items under a closed-status filter, the unknown-assignee toast, and F44's `@`-assignee match. If F45 is ruled (a), the group order following the type order goes in too.
- [2026-10-29T11:12:17Z] `manager` Catherine Manager:
  - Also in scope: REV-1235 F56 (CLAUDE.md: _spans.py, SQUADS_SPANS, scripts/bench_local_mode.py) and F58 (add the local-mode benchmark to the releasing runbook, numbers recorded with the release). Mark both Fixed on REV-1235 when done.
- [2026-10-29T12:09:10Z] `tech-writer` Theo Writer:
  - - Delivered, by subtask:
      - ST1: `docs/stability.md` Tier 3 states that every result-printing command takes `--json`, what `--json` prints (the result object, or its `items`/`source` field for the array documents), the change rule (append a key after the last one; anything else is a schema change, the class decides whether it may happen), and a provisional list.
      - ST2: Tier 3 "Display keys" (`display`, `columns`, the labels, the display class); CHANGELOG Added entry.
      - ST3: CHANGELOG Added entry for `--json` on every command, `{entry, …}`, reports, `init --json`, and `ui`/bare `workflow` refusing it; the "Commands that stay human-output-only" list is gone from stability.md.
      - ST4: `display` reserved in Tier 3 item rows, the attribute grammar and overrides.md (with the current refusal text); attribute `label` in overrides.md, stability.md and on the `workflow types --json` rows; CHANGELOG entries for both. The 0.18 migration `manual` step is not written: see the next comment.
      - ST5: labelled attributes on `show` (overrides.md); the declared-field rule for the lead badge (overrides.md, "Where a field's badge shows"); `display` on `workflow view --json` rows (stability.md, workflow.md); the exit 2 change, F25's two lines, and the removal prompts in the CHANGELOG.
      - Comments from the architect, reviewer and manager: the pronouns sentence in stability.md and roles.md; the tree table rows (`display`, `notebook`, `closed`, `updated_at`) and the append-at-end rule; CHANGELOG lines for `sq tree --label`, the three tree keys, the skill pronouns fix, the `sq ui` changes (F44, F45), tolerant view rendering, `sq check` override compile, and faster `show`/`list`/`tree` (no figures).
      - CLAUDE.md and docs/internals.md: the 20 `Service` bases, `get_service`/`require_current_schema`/`PENDING`/`open_service` removed, the write guard, the lazy command table and its guard, `_spans.py`/`SQUADS_SPANS`, `scripts/bench_local_mode.py` (CLAUDE.md only), the command lifecycle through `LocalApi`.
    - Checked on scratch squads with the dev tree at 8b9dc64b, compared with the released 0.17.0 where a change was claimed: `create`, `status`, `ref add`/`ref rm`, `body`, comment add, `retype`, `set-default`, sub-entity `update`, `memory add` `--json` shapes; `list`, `tree`, `search`, `graph`, `refs`, `stories`, `workload`, `role list`, `dev list`, `workflow statuses`/`types` keys; `tree --label`; `--json` on `repair`, `sync`, `docs`, `workflow show`/`lint`, `migrate help`/`chlog`; `ui --json` and `workflow --json` (exit 2); `memory ghost show` and `skill ghost status` (dev 2, released 1); the removal prompt on stderr (dev) and stdout (released) for item, story and comment removal; `role catalog` on a malformed `.squads.toml` (dev 1, released 0); `role reviewer show --json` with its file deleted (dev 1, released 0); a broken `views/role_definition.md.j2` override (`role manager show` exit 0 with the warning, `sq check` reporting the compile error); a declared `display` attribute and badge field (refused), a stored undeclared `display` (kept in the file, out of the row); a labelled attribute on `show` and `workflow types --json`; `[display] pronouns = false` on `role list --json` and `tree --json`. Not run: `sq ui` (F44 and F45 come from the review's headless captures).
    - `tests/meta` passes (688).
- [2026-10-29T12:09:17Z] `tech-writer` Theo Writer:
  - - @tech-lead ST4 asks for the 0.18 migration's `manual` step (an adopter who declares `display` renames it in the override and in the items that store it). `_migrations/_registry.py` has no 0.18 record (`SCHEMA_VERSION` is still 0.17), so per ST4 I am raising it rather than creating one. Text ready for when a record exists:
      - "**Rename a declared `display` attribute or badge field.** `display` is a key every `--json` item row adds, so a workflow override that declares it is refused at load. Pick a new name, rename it in `.overrides/workflow.toml` and in every item file that stores it, then run `sq repair`. No migration renames it."
    - Until then the same instruction sits in the CHANGELOG's `display` entry, under "What to do".
- [2026-10-29T12:14:44Z] `tech-lead` Olivia Lead:
  - Ruling on ST4 (2026-10-29): **(a)**. The CHANGELOG "What to do" line is enough. 0.18 gets no migration record and no schema bump for the reserved `display` name.
    - **Why.** Nothing in the corpus changes, so a record would be a stamp-only runner. ADR-1225 section 3 names the cost of that: every adopter is forced through `sq migrate up`, and every 0.17 client is locked out, for a rename most squads never need. The adopter who does need it gets the remedy at the moment it matters, in the load refusal itself (`… rename the attribute in the workflow override and in the items that store it`). The CHANGELOG entry repeats it under "What to do". A rule the adopter can predict: a reserved name is refused at load and the message says what to do, as for `views`.
    - **FEAT-1140 does not bump the schema in 0.18.** `Squads-Schema` sends the package's current `SCHEMA_VERSION`, and ADR-1225 bumps the schema only for an incompatible DTO or route change. 0.18's payloads are additive over 0.17's frozen `--json`, and a local daemon is keyed per version. No 0.18 task plans a bump (checked TASK-1218 to 1238). So no record belongs there either.
    - **The first 0.18 change that does bump the schema carries the writer's text** (17a9545) as its `manual` string.
    - **ST4 re-scoped:** the `sq migrate chlog` manual step is dropped. The rest of ST4 is delivered per the writer's record, and I checked the CHANGELOG entry (the reserved-name entry with its refusal text and "What to do"). ST4 is closed.
    - @architect ADR-1224 point 2 still says "the 0.18 migration's manual step (`sq migrate chlog`) tells an adopter…". Please amend that clause to "the load refusal and the changelog's What to do line tell an adopter…", or overrule this.
- [2026-10-29T12:45:47Z] `manager` Catherine Manager:
  - Done: docs and CHANGELOG reviewed (REV-1235 F56, F58, F61-F67 verified, F25/F44 noted), BUG-1239's line folded in, narration sweep clean.
<!-- sq:discussion:end -->
