---
id: TASK-1006
sequence_id: 1006
type: task
title: Document the comment header grammar and its migration
status: Done
parent: FEAT-980
author: tech-lead
assignee: tech-writer
priority: medium
refs:
- ADR-979:implements
- TASK-1004:depends-on
description: Stability tiers 1 and 3, internals, the 0.16 migration section and CHANGELOG
  entries for slug-bearing comment headers
subentities:
- local_id: ST1
  title: State the header grammar and slug permanence in the contract
  status: Done
  story: US5
- local_id: ST2
  title: Describe the 0.16 migration and write the changelog entries
  status: Done
  story: US5
created_at: '2026-10-12T06:48:46Z'
updated_at: '2026-10-16T08:39:08Z'
---
<!-- sq:body -->
## Scope

Story 5 of FEAT-980: the adopter documentation for the comment header that names its author's
slug (ADR-979). The engine work is the task this one depends on; this task describes the
format an adopter's files now have, the rule that a slug never changes, the new JSON key, and
what `sq migrate up` does to an existing squad, including what it prints when it refuses.

Owner: the tech writer. The developer's handoff comment on the engine task lists every
adopter-visible change with its exact text (the grammar, each changed render, `author_slug`,
each refusal, the migration's report, its failure report and its `MANUAL` text). That list is
the input. Each claim is still checked against a scratch squad before it is written.

## Subtasks

- **ST1, the contract.** `docs/stability.md` and `docs/internals.md`: the header grammar, slug
  permanence, `author_slug`.
- **ST2, the upgrade.** The 0.16 section of `docs/migration.md`, the CHANGELOG entries, and a
  review of the `MANUAL` text the command prints.

ST1 first: ST2 links to its sections.

## Acceptance (whole task)

- Story 5, every clause, each subtask covering the ones it names.
- **Every command and every quoted message is run before it is written**, with the dev build,
  in a scratch squad nested under the session scratchpad. The handoff labels each claim as
  driven or read.
- **The reader test.** Following only `docs/migration.md`, take a squad the released tool
  wrote with comments from a role, an operator and a retired role, upgrade it, and reach a
  clean `sq check`. Then repeat on a copy whose roster no longer holds one author, read the
  refusal, apply the documented remedy and complete the run. Record the commands.
- **A stale-claim sweep, table-driven.** For each statement this change retires (a header is
  the timestamp and the full name; a discussion entry in `--json` is `author`, `ts` and
  `body`; the author is resolved from `--as` to the role's full name and the slug is not
  kept), search every file under `docs/`, the README and the CHANGELOG's unreleased section,
  on whitespace-collapsed text, and validate each search on the previous wording first. The
  handoff lists each statement, where it was, and what replaced it.
- Adopter docs carry no item references and no development-process content. Each sentence
  passes the stranger test: true and meaningful for a reader who never saw the change.

## Gates and working rules

- `uv run --all-extras pytest tests/meta` passes: the gate that documented commands resolve
  against the CLI, and the gate against stray item references in docs.
- `~/.local/bin/sq check` is clean before handback.
- No source or test file is edited. That includes the `MANUAL` string in the migration
  runner: proposed wording goes to the engine task as a comment, and the developer applies it.
  A doc claim the build contradicts is reported there too, not worked around in prose.
- `docs/migration.md` describes the 0.16 step as one step that checks every part before it
  writes any file. This task creates that section with the comment-header part in it; write it
  so that a later part of the same step is added as a paragraph, not as a second section.
- The writer never runs `sq migrate`, `sq repair` or `sq sync` on this repository's own squad,
  with any build. Any probe script starts with `set -euo pipefail`, an absolute `cd` into its
  scratch folder, and an exit if `pwd` is under `/home/pchat/projects/squads`. The dev build is
  called by the absolute path of its virtual-environment entry point, with the scratch squad
  as the working directory, never from the repository root.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1006 add-subtask "<title>"`; track with `sq task 1006 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — State the header grammar and slug permanence in the contract

<!-- sq:subtask:ST1:body -->
**Goal.** The stability contract and the internals page describe a comment header as it is
now written, say that a slug is permanent, and name `author_slug`.

**Approach**

- `docs/stability.md`, Tier 1 (the durable file format):
  - the header grammar, as a block an adopter can match against their own files: the line
    form, what the timestamp, the slug and the name may hold, that the header starts at the
    left margin, and that the slug is the identity while the name is a snapshot taken when the
    comment was written;
  - the two reserved author slugs (`operator` for a comment with no named author, `squads` for
    an entry the tool writes itself) and that `op-` is reserved for operators;
  - the permanence rule: a roster entry's slug is chosen when the entry is created and no
    command, override or migration changes it afterwards; display fields stay editable; a slug
    freed by a purge may be taken by a new entry, and older comments then read as that entry's.
- `docs/stability.md`, Tier 3 (`--json` shapes): each discussion entry of `show --json`, for
  an item and for a sub-entity, and each entry of `comments --json`, carries `author_slug`
  beside `author`; `author` is still the display name; search and inbox output is unchanged.
- `docs/internals.md`, "Discussion, @mentions, inbox": the comment line uses the new grammar,
  and the sentence on how the author is resolved says the slug is stored and the name is
  resolved at write time.
- Any other page the stale-claim sweep of the task body finds.

**Checks**

- Each example header in the docs is produced by the dev build in a scratch squad and pasted,
  never typed: one for a role, one for an operator, one written with `--as operator`.
- The grammar block is checked against the pattern in the source by matching it on those
  three lines and on a line that must not match (an indented checkbox).
- The `--json` examples are the build's own output.

**Acceptance**

- Story 5: Tier 1 gains the header grammar and the slug permanence rule; Tier 3 notes
  `author_slug`; the comment line in `docs/internals.md` uses the new grammar.
- The sweep table is in the handoff, each search validated on the previous wording.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Describe the 0.16 migration and write the changelog entries

<!-- sq:subtask:ST2:body -->
**Goal.** An adopter upgrading an existing squad knows what the migration rewrites, what it
prints when it cannot, and what to do then; and the changelog says what changed.

**Approach**

- `docs/migration.md`, a section for the 0.16 step:
  - what the step does to comment headers: only the header line changes, in every discussion
    of every item and sub-entity; a comment's own lines and the frontmatter do not;
  - that every name is resolved before any file is written, and that on a failure nothing is
    written, the schema is unchanged and the command exits 1;
  - the failure report, quoted from a real run: one line per header for each kind (a name that
    matches no entry, a name that matches several, a timestamp the tool does not write), the
    count, and the per-name lines;
  - the remedy for each kind, and the fact an adopter most needs: until the migration
    completes this release runs nothing on the squad but the three `sq migrate` commands, so
    roster changes are made with the release the squad is stamped for;
  - that there is no option to map a name to a slug by hand, and that the command can be run
    again safely.
- `CHANGELOG.md`, the unreleased section:
  - **Changed**: the comment header grammar; the human renders that now show the slug; search
    attribution for a comment holding an indented line that looks like a header;
  - **Added**: `author_slug` in the discussion JSON; the refusal of reserved role slugs;
  - the migration, with a pointer to the migration page for the failure report.
- **The `MANUAL` text** printed by `sq migrate chlog v0.15.0..v0.16.0`: read it as an adopter
  who has just been refused, check each remedy by performing it with the released tool on a
  scratch squad, and post proposed wording as a comment on the engine task. The page and the
  runbook must agree on every remedy.

**Checks**

- The quoted failure report is the output of a real refused run, and the documented remedies
  are the ones performed in the task body's reader test.
- Each remedy names the release that can perform it, and no sentence tells the adopter to run
  a command that this release refuses on a squad it has not yet migrated.
- CHANGELOG entries describe the tool for an adopter: no item references, nothing about how
  the change was built.

**Acceptance**

- Story 5: `docs/migration.md` and the CHANGELOG describe the migration and its failure
  report.
- The runbook review is posted, and the page and the runbook agree after the developer's
  reply.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T06:50:47Z] `tech-lead` Olivia Lead:
  - 2026-10-12: authored for story 5 of FEAT-980. Left in Draft, no writer briefed. Depends on TASK-1004, whose handoff comment is this task's input. It creates the 0.16 section of the migration page; TASK-991 then adds to it, which reverses the sentence in TASK-991's working rules.
- [2026-10-16T08:19:53Z] `tech-writer` Theo Writer:
  - - @manager ST1 and ST2 done; task to InReview. Nothing committed; no Python or test file edited. Files: `docs/stability.md`, `docs/internals.md`, `docs/migration.md`, `CHANGELOG.md`. Gates: `tests/meta` 356 passed; the doc-reading unit tests and `tests/cli/test_docs_cli.py` 18 passed; anchors checked; `sq check` clean.
      - **ST1 (stability.md, internals.md).** Tier 1 gains "Comment headers" (three headers pasted from the dev build: role, operator, `--as operator`; the grammar block; left-margin rule; slug is identity and name a snapshot; the reserved `operator` and `squads`; no role may take those or an `op-` slug, with the real refusal) and "A roster slug never changes" (fixed at creation, display names are not identity, an override cannot rename with the real refusal, a purged slug can be taken again). Tier 3 gains a "Discussion entries" bullet for `author_slug`. internals.md's comment line uses the new grammar and says the slug is stored and the name resolved at write time. Nothing from the pending A1-A6 amendment is stated as a rule; the only `op-` statement is the role refusal the code has today, plus the migration report line for an operator without `op-`, described as a report with nothing refused.
      - **ST2 (migration.md, CHANGELOG).** A new "Upgrading to 0.16: the schema step" section: a step-level intro (checks every part before writing, exits 1 with every problem listed, fix with an earlier release, the below-0.15 case) and a "Comment headers name the author's slug" part. A later part goes in as another `###` under the same `##`, with no new `## Upgrading to 0.16` section. CHANGELOG [0.16.0]: Added `author_slug` and the reserved role slugs; Changed: BREAKING header grammar + migration + `Name (slug)` renders, roster slug permanence (importer retitle keeps slug and file name), importer comment-actor checks, search attribution; Fixed: a `\r` or other line separator in `-m` can no longer start a second comment.
      - **MANUAL review** posted on TASK-1004 for @python-dev: six wording changes (role matched by name not title; real path shapes; remedy commands; the duplicate-name remedy has no verb in either release, so it is a frontmatter edit; the release sentence below 0.15; a missing bullet for the malformed-marker failure). The migration page already uses the corrected remedies.
      - **Reader test (driven).** A 0.15.0 squad (comments from role `architect`, operator `op-zo` with an accented name, `--as operator`, and role `qa` on a subtask, `qa` then archived). Following migration.md: `sq migrate up` (exit 0, 4 headers in 1 file), `chlog`, `sq check` clean, `sq sync`, `sq check` clean, diff header lines only. Copy two: 0.15.0 `sq role qa rm --purge`, dev `sq migrate up` refused (exit 1, git tree clean), 0.15.0 `sq role catalog` then `sq role activate qa --name "Mara Tester"`, dev `sq migrate up` exit 0, `check` clean, `sync`, `check` clean.
      - **Also driven:** all five failure kinds and their remedies (bad timestamp then indent; two entries then frontmatter edit; dev role and operator re-add with `--slug`; unclosed region; shared-line and malformed marker), the below-0.15 refusal and remedy on a copy of the v0_11 corpus, the operator-without-`op-` report line, `comments --json` and item/sub-entity `show --json` keys, `show --raw` and `comments` renders, search JSON identical to 0.15.0 on an unmigrated twin, the search attribution fix (0.15.0 says comment 5 "(Done, x)", the dev build says comment 4), `--as`/importer refusals, importer roster retitle keeping the file name, the override slug refusal, purged-slug reuse. **Read, not driven:** the TUI discussion tab; role refusal through `sq import` and a catalog entry; importer retitle for a skill; a header-shaped line in an item body being left alone; inbox JSON being unchanged against 0.15.0 (the dev build's inbox row has no author field).
      - **Stale-claim sweep** (docs/, README, CHANGELOG [0.16.0], whitespace-collapsed; each pattern checked against a known positive first): "header is timestamp + full name" was at internals.md (comment line) and is replaced by the new grammar; "the author is resolved from --as to the role's full name" was at internals.md and is replaced by the stored-slug sentence; "a discussion entry is author, ts, body" had no hit in docs/README/CHANGELOG (pattern validated on the earlier wording `{author, ts, body}`); Tier 3 now states the four keys.
      - **Observed, not changed:** `sq override scaffold --new squads` (and `operator`) writes a role override that `sq role activate` then refuses; the scaffold could refuse the reserved slugs up front. The dev build reports `squads 0.15.0` in its version and the gate message, which is expected before the release bump; the docs quote no version line.
- [2026-10-16T08:34:59Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1031: ChangesRequested on two medium findings (F1 the reserved-slug wording in Tier 1 and the CHANGELOG; F2 the CHANGELOG stamped-release remedy). @tech-writer for F1, F2, F4-F7; @python-dev for F3 (MANUAL example). @manager
- [2026-10-16T08:38:26Z] `tech-writer` Theo Writer:
  - REV-1031 F1, F2, F4, F5, F6 and F7 fixed (docs/stability.md, CHANGELOG.md, docs/tutorial.md section 4 sentence only) and marked Fixed; F3 and F8 untouched. tests/meta plus the doc tests: 374 passed. New claims driven with the dev build except the VS Code preview rule (read). @reviewer @manager
- [2026-10-16T08:39:07Z] `manager` Catherine Manager:
  - Moved to Done under the manager's delegation: REV-1031 Approved.
<!-- sq:discussion:end -->
