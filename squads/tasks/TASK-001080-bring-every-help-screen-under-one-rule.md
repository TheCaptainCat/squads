---
id: TASK-1080
sequence_id: 1080
type: task
title: Bring every --help screen under one rule
status: Done
parent: FEAT-1024
author: tech-lead
priority: medium
refs:
- TASK-1072:depends-on
- REV-958:addresses
- ADR-1025
description: 'help text per REV-958 R1-R9: writer strings and docs, shared flag definitions,
  markup and layout, and a tests/meta guard'
subentities:
- local_id: ST1
  title: Write the help rule into CONTRIBUTING.md
  status: Done
  assignee: tech-writer
  story: US1
- local_id: ST2
  title: Move the JSON field reference from 13 help bodies into the stability docs
  status: Done
  assignee: tech-writer
  story: US3
- local_id: ST3
  title: Give help one exit-code line form, mechanics in the faq
  status: Done
  assignee: tech-writer
  story: US6
- local_id: ST4
  title: Describe every option and argument, with one wording per shared flag
  status: Done
  assignee: tech-writer
  story: US4
- local_id: ST5
  title: Move maintainer reasoning and private names out of help bodies
  status: Done
  assignee: tech-writer
  story: US2
- local_id: ST6
  title: Rewrite hand-written summaries and drop flags described twice
  status: Done
  assignee: tech-writer
  story: US8
- local_id: ST7
  title: Declare each shared flag once in _cli/_common.py
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST8
  title: Apply one markup dialect and an 80-column layout to help
  status: Done
  assignee: python-dev
  story: US7
- local_id: ST9
  title: 'Fix generated summaries: kind labels and articles'
  status: Done
  assignee: python-dev
  story: US8
- local_id: ST10
  title: Add the tests/meta guard that walks the command tree
  status: Done
  assignee: python-dev
  story: US9
- local_id: ST11
  title: Match the docs and CHANGELOG to the shipped help
  status: Done
  assignee: tech-writer
  story: US10
created_at: '2026-10-16T21:15:20Z'
updated_at: '2026-10-17T05:11:49Z'
---
<!-- sq:body -->
## Scope

Every rendered `--help` screen follows REV-958's rule (R1 to R9): it answers what the command
does, what to type and what comes back, in one markup dialect, with every option and argument
described, one exit-code form, and a layout that survives 80 columns. A `tests/meta` guard holds
the mechanical half. Covers FEAT-1024 US1 to US10, findings F1 to F5 and F7 to F11.

Out of scope (the feature's list): F6 (a per-item verb's help needing a real item; its own item),
any command, flag, default or output change other than help text, the help renderer (stays on
Rich console markup), a verdict on the designs whose rationale leaves the help body, and the
structural refactors and comment pass of REV-956. Where help is accurate about wrong behaviour,
file a bug; do not fix it here.

## Rulings this task carries (binding, not reopened)

- Help stays on Rich console markup (op-pierre, 2026-10-09).
- ADR-1025 (Accepted): listing a field in `docs/stability.md` records the existing freeze and
  widens nothing; no new tier; each key is marked vocabulary, open set or display.
- Architect, on FEAT-1024: exit 4 is one line on each of the five partial-result commands,
  `Exit codes: 4 partial result; what could be read is printed. See sq docs faq.`; the
  over-10-line body is checked against an immutable allowlist that fails on stale entries; custom
  types and kinds are walked under a test-local override, never the repo's own.
- The milestone's build order puts this at step 7: the writer's strings first, then the developer
  placement and the guard (op-pierre, 2026-10-09, MILE-934).
- A related graph edge's `edge_semantic` is `"default"` in the live payload (manager, 2026-10-16).

## Migration

None: help text is not stored in any squad file. `_migrations/` is not touched.

## Order

Depends on TASK-1072, the last CLI-changing task of the main stream (TASK-1069, TASK-1070,
TASK-1078, TASK-1079, TASK-1071, TASK-1072): every verb those add must exist before the guard walks
the tree, and help text touches `_cli/` broadly. TASK-992 touches `_services/` only and does not
collide. New verbs added after this task follow the CONTRIBUTING section of ST1 and are held by the
guard.

## How the work splits

The writer edits text in place: command docstrings and `help=` literals under `src/squads/_cli/`,
docs and CONTRIBUTING.md, with no change to code structure, and moves maintainer reasoning to the
helper or module docstring it explains (one or two sentences, no versions, no ticket ids). The
developer does the structure: one shared definition per flag in `_cli/_common.py`, generated
summaries and articles, no-rewrap blocks and placeholders, and the guard. Run the writer
subtasks on the stronger model (REV-958 sizes the strings pass at about a day and a half).

## Files touched

`CONTRIBUTING.md`; `src/squads/_cli/*.py` (docstrings, `help=`, shared option definitions in
`_cli/_common.py`, generated per-type and per-kind summaries); helper and module docstrings that
receive moved reasoning; `docs/stability.md`, `docs/faq.md`, `docs/workflow.md`, `CHANGELOG.md`;
`tests/meta` (the guard), tests that pin a truncated or rewritten help string, CLI goldens that
render help.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-1024 US1 to US10 is pinned by a guard assertion, a named test or
  a checked passage; the handoff maps bullet to proof.
- **Table-driven shape tests:** the guard is one parametrised walk over every canonical command
  (bundled spec, tmp squad) by the seven assertions, plus the second walk over a test-local override
  declaring one custom type with a sub-entity kind and a ref kind (vowel-initial name, irregular
  plural, realistic label length). No hand-picked command list.
- **Falsify the guard:** for each of the seven assertions, reintroduce one violation (a blank
  option, a 73-character summary, a doubled backtick, a bracket tag, a 79-column line, a
  truncated enumeration, an 11-line body off the allowlist, a stale allowlist entry) and watch that
  assertion go red; restore. The handoff records each.
- **No behaviour change:** for every command, the output of a non-help invocation in the CLI test
  suite and every `--json` golden are byte-identical before and after; only help screens move.
- REV-958's findings F1 to F5 and F7 to F11 are marked Fixed with the subtask that fixed each, and
  F6 cites its own item.

## Gates and working rules

TASK-1069's gates apply: pyright and ruff with `--all-extras`, `~/.local/bin/sq check` clean,
`tests/meta` on any module constant; `_cli/` changes always run `tests/meta`, `tests/integration`
and `tests/cli`, plus a grep of every changed help string across `tests/`; the manager runs the
full suite; the guard adds no module-level mutable state and runs in a few seconds; no ticket ids
in test file names or help text.

## Subtask order

Writer: ST1, ST2, ST3, ST4, ST5, ST6 (commit point, reviewed by reading the 80-column screens).
Developer: ST7, ST8, ST9, then ST10 enabling all seven assertions (commit point, reviewed). Writer:
ST11 last, from the ST10 handoff.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1080 add-subtask "<title>"`; track with `sq task 1080 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the help rule into CONTRIBUTING.md

<!-- sq:subtask:ST1:body -->
**Goal.** CONTRIBUTING.md states the help rule where a contributor reads it before writing a
docstring.

**Approach (tech writer)**

- One short section: the three questions a help screen answers, the content-to-home table (help,
  code comment or helper docstring, `docs/`), R1 to R9 in applicable form, the 10-source-line
  tripwire counted after the summary paragraph and before any form feed with blank lines not
  counted (the same count ST10's guard uses), and the review test: render at 80 columns and read
  the screen.
- No list of commands that are wrong today, no item ids.

**Acceptance**

- FEAT-1024 US1, all bullets: a reviewer can hold a help change to the section without reading
  REV-958.
- The line count stated matches ST10's implementation (checked at ST10).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-17T04:10:32Z] `tech-writer` Theo Writer:
  - Done. CONTRIBUTING.md gains "Writing `--help` text": the three questions, the content-to-home table, R1-R9 as nine applicable rules, and the 80-column review test. The body tripwire is stated as ST10 must implement it: source lines after the summary paragraph and before any form feed, blank lines not counted, over 10 needs a reason a reviewer accepts. "How to add things > A command" links to it. The section does not mention the guard yet; @python-dev add one sentence naming it and its allowlist when ST10 lands.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Move the JSON field reference from 13 help bodies into the stability docs

<!-- sq:subtask:ST2:body -->
**Goal.** The `--json` field reference leaves 13 help bodies, landing in `docs/stability.md` in the
same change where help is its only home. F3, R5, R6, ADR-1025.

**Approach (tech writer)**

- Trim the 13 bodies F3 lists to the one-line `--json` description naming the top-level shape, any
  don't-misuse sentence (graph: branch on `edge_semantic`, never `edge_kind`; tree: `anchor` true is
  an invented root for a parent cycle; search: `region` says where the hit was found) and the
  pointer `Fields: sq docs stability`.
- Nine bodies shrink with no docs change. For `search`, `tree`, `graph` and `workflow ref-kinds`,
  enumerate each key in `docs/stability.md` from the live payload (run each command with `--json`
  in a scratch squad; never copy from help), marking values vocabulary, open set or display per
  ADR-1025 §3; withdraw the sentence naming help as their authority. Add the ref-kinds catalog row,
  the open-set mark on ref-kind `role` in `docs/workflow.md`, and `badges` in the graph field list.
  `edge_semantic` of a related edge is `"default"`, never null.
- Graph ends near 8 body lines and search near 6.

**Tests**

- A docs check (in the handoff, not a new test): every key a live payload emits for those four
  shapes appears in `docs/stability.md`, and none listed is absent from the payload.

**Acceptance**

- FEAT-1024 US3, all bullets.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-17T04:10:34Z] `tech-writer` Theo Writer:
  - Done. All 13 bodies are trimmed to the summary, the `--json` line and `Fields: sq docs stability` (role catalog points at `sq docs roles`, where its fields live), keeping the three don't-misuse sentences (graph edge_semantic, tree anchor, search region).
    
    Docs check against live payloads from a scratch squad (dev tree, `--json` on search/tree/graph/workflow ref-kinds):
    - search: payload keys id, title, type, status, hits[].region, hits[].location, hits[].snippet, hits[].hash. `hits[].hash` was missing from docs/stability.md; added (fixed format: full comment hash, null outside a discussion).
    - tree: id, type, title, status, priority, assignee, blocked, badges, anchor, children; docs match in order.
    - graph: id, type, status, priority, badges, assignee, edge_kind, edge_semantic, direction, seen, children; docs match. A related edge reads `edge_semantic: "default"`.
    - ref-kinds: kind, label, hint, role, direction; catalog row already present.
    The help-as-authority sentence was already withdrawn, and docs/workflow.md already marks ref-kind `role` as an open set.
    
    Two corrections made while verifying: the graph `edge_kind` row now says both spellings of a dependency edge report one declared kind (driven: a `blocks` ref reads `depends-on`, direction `out`), and the `direction` row no longer claims the parent always carries the ref, which that collapse makes false.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Give help one exit-code line form, mechanics in the faq

<!-- sq:subtask:ST3:body -->
**Goal.** One exit-code form in help, with the mechanics in the docs only. F5, R7, the architect's
ruling.

**Approach (tech writer)**

- A command with no code of its own says nothing about exit codes.
- Each of the 11 commands with a code of its own carries one line, `Exit codes: <code> <meaning>.
  See sq docs faq.`; `inbox`, `search`, `board list`, `memory list` and `memory search` carry exactly
  `Exit codes: 4 partial result; what could be read is printed. See sq docs faq.`
- `sq import` keeps, in two lines, that exit 3 means the work is applied: do not retry, read
  `applied` from `--json`.
- Before import's paragraph shrinks, `docs/faq.md`'s row for code 3 names `sq import`; the exit-4
  mechanics (stderr line per skipped file, JSON line, unchanged payload) are in the faq and
  stability docs and nowhere in help.

**Acceptance**

- FEAT-1024 US6, all bullets; no exit-code contract changes (the CLI exit-code tests are untouched
  and green).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-17T04:10:36Z] `tech-writer` Theo Writer:
  - Done. One line form everywhere, `Exit codes: <code> <meaning>. See sq docs faq.`:
    - 4, the exact architect line: inbox, search, board list, memory list, memory search.
    - check (3), import (3, plus the two-line do-not-retry note), repair (1), migrate up (1), workflow lint (1).
    - reflog's line is gone: 0/1 is the general contract, not a code of its own.
    docs/faq.md: row 3 now names `sq import` and the do-not-retry rule; row 1 names the rebuild that ends `sq migrate up`. The exit-4 mechanics stay in the faq and stability docs only. No exit-code test was touched.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Describe every option and argument, with one wording per shared flag

<!-- sq:subtask:ST4:body -->
**Goal.** Every option and argument other than `--help` has a one-line description. F2, R4, R5.

**Approach (tech writer)**

- Walk the live tree (the probe REV-958 describes, or `sq <cmd> --help` per command) and write each
  blank cell: what the value is and what it does here, with where legal values come from (STATUS
  names its source, e.g. `see sq workflow`). Never restate the panel's default or required marker.
- `--json` on every command: one line naming the top-level shape.
- For each flag shared across commands (the US5 list: `--file`, `-m/--message`, `--force` on a
  status change, `--raw`, `--desc`, `--author`, `--all`, `--depth`, `--tech`, plus any other the walk
  finds), write one canonical wording in the handoff table; ST7 makes it the single definition.
  US5 fixes three: `--all` reads `Include closed items.`; `--author` names operators; `-m` states
  that it repeats.

**Acceptance**

- FEAT-1024 US4 bullets 1 to 4; bullet 5 (declared once) is ST7.
- The handoff has the canonical-wording table and the before/after blank count (186 to 0).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-17T04:10:38Z] `tech-writer` Theo Writer:
  - Done. Blank option and argument cells: 231 before, 0 after, over a walk of 343 canonical command records including the addressed roster, comment-hash and sub-entity verbs (REV-958 counted 186 over a narrower walk). Every `--json` names its top-level shape. No new cell restates a default or a required marker. Each wording below is already in place at every site, so ST7 only has to declare it once:
    
    | Flag | Canonical wording |
    |---|---|
    | `--file` (with `-m`) | Read the text from a file instead of `-m`; `-` reads stdin. |
    | `-m/--message` on a body, notice or create | A paragraph of text; repeat for several. |
    | `-m/--message` on comment and comment edit | One point of the comment; repeat for several. |
    | `--force` on a work-item or sub-entity status change | Make a transition the lifecycle does not allow. |
    | `--force` on a roster `status` | Make a transition the lifecycle does not allow; a change that would leave the config invalid is still refused. |
    | `--force` on `body` | Replace a body already written; what it held is lost. |
    | `--raw` | Print plain text instead of rendered markdown. |
    | `--desc` | Short summary shown in listings; not the body. |
    | `--author` | Author: a registered role slug or `op-<slug>`. |
    | `--all` (closed items) | Include closed items. |
    | `--depth` (tree, graph) | How many levels below the root to show; 0 shows only the root. |
    | `--tech` (create guide, dev add) | Technology, such as `python` or `react`. |
    | `--assignee` (sets) | Role or operator slug to assign. |
    | `--assignee` (filters list, tree) | Show only items assigned to this role or operator slug. |
    | `--type/-t` (filter) | Show only items of this type (see `sq workflow types`). |
    | `--status/-s` (filter) | Show only items in this status, closed or not (see `sq workflow statuses`). |
    | `STATUS` / `--status` (move) | Status to move to (see `sq workflow lifecycles`). |
    | `--append` | Append to the body instead of replacing it. |
    | `--parent` (create, skill add) | Parent item ID or number. |
    | `--label` (create) | Label to add (repeatable). |
    | `--pronouns` (role activate, dev add, operator add) | Pronouns, such as they/them; one line, up to 40 characters. |
    | `--yes` | Skip the confirmation prompt. |
    | `--title` (update) | New title. |
    | view name (add) | Declared view name (see `sq workflow views`). |
    | view name (disable) | View name; it need not be declared, so a dropped view can be turned off. |
    | ref TARGET (add) | Item ID or number to ref; `ID:kind` also sets the kind. |
    | `--kind` (ref add) | Ref kind (see `sq workflow ref-kinds`); without it, the default kind. |
    
    Left for ST7 as written: `--as` keeps its hand-written "(required)" on comment, comment edit/remove and board post, and `--priority`, `--category`, `--badge`, `--min-badge` and `--sort` are unchanged. `--json` is one line per shape, not one shared string.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Move maintainer reasoning and private names out of help bodies

<!-- sq:subtask:ST5:body -->
**Goal.** Help bodies carry no maintainer reasoning, private names, history words or shouted caveats.
F1, R3.

**Approach (tech writer)**

- For every command F1 lists, move the reasoning to the helper or module docstring it explains, or
  after a form feed in the command docstring, each moved text one or two sentences with no versions,
  ids or history.
- `sq check` keeps exactly: the summary, the exit-code line, one sentence that output order is
  stable, one sentence that a broken workflow or playbook override is reported as an issue while the
  other checks still run.
- `sq reflog --tree` carries its warning in one plain sentence.

**Acceptance**

- FEAT-1024 US2, all bullets.
- A read of every F1 command at 80 columns finds no function, class, module or package path, no
  internal type and no history word; the handoff lists the commands read.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-17T04:10:40Z] `tech-writer` Theo Writer:
  - Done. Read at 80 columns after the change: check, repair, workflow view, migrate up, workflow lint, list, workflow lifecycles, role catalog, role list, tree, workflow statuses, workflow collections, override scaffold, skill body, import, search, workflow roles, reflog. None names a function, class, module, package path or internal type, and none uses a history word.
    - check keeps exactly the summary, the exit line, the stable-order sentence and the broken-override sentence; its reasoning went into the existing comment above `get_service()` in the command.
    - repair's accessor reasoning is a comment on the accessor line; migrate up's matches-repair reasoning is a comment under its docstring.
    - tree, role catalog, role list and role set-default keep a short maintainer note after a form feed.
    - reflog --tree is one plain sentence; the helper docstring already held the full caveat.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Rewrite hand-written summaries and drop flags described twice

<!-- sq:subtask:ST6:body -->
**Goal.** Hand-written summaries state the outcome in one short sentence, and flags are described
once. F9, F10, R1, R4.

**Approach (tech writer)**

- Every hand-written summary: one sentence, one source line, 72 characters or fewer, verb first,
  naming the outcome; no mechanism, no parenthesis.
- Bodies keep only how flags combine: `override scaffold` near five lines on the four override
  kinds; `tree` keeps that ancestors of a match are kept and dimmed.
- `status` on role, operator and skill no longer points at a work-item verb.
- Generated summaries (per-type, per-kind, create, articles) are ST9's; list in the handoff any the
  writer saw that need it.

**Acceptance**

- FEAT-1024 US8 bullets 1 and 4, and the `status` part of bullet 2, for hand-written text.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-17T04:10:42Z] `tech-writer` Theo Writer:
  - Done. Every hand-written summary is one line, at most 72 characters, verb first, with no parenthesis (walker: 0 over 72 or wrapped, down from 51). Override scaffold's body is six lines on the kinds and their two spellings; override diff and update lost their per-flag paragraphs; tree keeps "ancestors of a match are kept and dimmed". The roster `status` summary no longer points at a work-item verb.
    
    Generated summaries left for ST9: "Create a <type>." and "Operate on a <type> by number." (article), the type group's "<type> number or id." argument, and the sub-entity verbs still saying "sub-entity" or using a fixed article: `<kinds>` list, `add-<kind>` ("Scaffold a <kind>"), the `<kind>` group, `<kind> show`, `<kind> body`, `<kind> remove`. `<kind> update` already uses the kind and is now "Change the <kind>'s title, status, assignee or declared fields."
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Declare each shared flag once in _cli/_common.py

<!-- sq:subtask:ST7:body -->
**Goal.** Each shared flag is one definition in `_cli/_common.py`, reused by the per-type, per-kind
and roster registrations, with one wording per meaning. F8, R4.

**Approach (python-dev)**

- From ST4's canonical-wording table, declare each shared option once and use it at every site.
- Remove hand-written `(default ...)` and `(required)` where the panel prints them; flags required
  by hand validation say so in the same words.
- Keep the `--priority` difference between item verbs and `list`/`tree` (spec-derived, type-aware
  versus type-agnostic); a one-sentence comment at the definition says why.

**Tests**

- A table test over the US5 flags: every command that takes the flag renders the identical
  description string.
- Meta: no `typer.Option` literal for a shared flag name outside `_cli/_common.py`.

**Falsify.** Inline one `--file` declaration with a different wording: both tests go red. Restore.

**Acceptance**

- FEAT-1024 US5, all bullets, and US4 bullet 5.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-17T04:57:42Z] `python-dev` Elias Python:
  - Done. Shared flags are declared once in _cli/_common.py (factory functions and wording constants); every other CLI module calls them. Where a flag carries more than one meaning it has one declaration per meaning. --as keeps "(required)" in the same words on every site, since it is validated by hand (REV-958 F8). Falsification: reverting to an inline --file with other wording turns 2 new tests red; a differently worded --desc, 3; a board post -m worded as a comment, 1; across the reverts 4 of the 5 new tests go red and the fifth is the scanner self-check.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Apply one markup dialect and an 80-column layout to help

<!-- sq:subtask:ST8:body -->
**Goal.** One markup dialect and a layout that survives 80 columns. F7, F4, R8, R9.

**Approach (python-dev)**

- No doubled backticks, asterisks, `::` line endings or cross-reference roles; literals in single
  backticks, option descriptions included (mechanical pass over the writer's text).
- No square-bracketed lowercase word, `#`, `/` or `@` span that Rich reads as a tag.
- Body paragraphs wrap at 78 columns after dedent; line-structured text sits in a no-rewrap block
  (`\b`) under 78 columns. Role, operator and skill epilog examples render as separate lines.
- No enumeration cut by an ellipsis at 80 columns: retype's NEW-TYPE and `reflog --op` show every
  value or point at the command that lists them; move the tests that pin the truncated strings with
  the fix.
- The addressed roster verbs and the sub-entity verbs print one placeholder each, distinctly named.

**Tests**

- Render table at 80 columns for retype, `reflog`, the three epilogs and one roster and one
  sub-entity verb: no ellipsis, each example on its own line, the placeholder names.

**Falsify.** Restore the old NEW-TYPE enumeration on retype: its no-ellipsis row goes red. Drop the `\b` before one epilog example block: its separate-lines row goes red. Restore each.

**Acceptance**

- FEAT-1024 US7, all bullets.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-17T04:57:45Z] `python-dev` Elias Python:
  - Done. Retype NEW-TYPE and reflog --op no longer truncate; comment group, renumber and the three roster epilogs lay out one item per line at 80 columns; roster usage asks for the address once; sub-entity verbs name LOCAL-ID. Typer keeps authored line breaks in every help paragraph after the first, and a backspace marker there prints a stray blank line, so no no-rewrap marker is used. Falsification: restoring retype enumeration 3 new red (+1 changed test), reflog slash list 3, merged epilog paragraphs 3, folded comment examples 1, folded renumber line 3, roster usage 1, sub-entity N placeholder 1; 11 distinct new tests go red across the reverts.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Fix generated summaries: kind labels and articles

<!-- sq:subtask:ST9:body -->
**Goal.** Generated summaries use the kind's own labels and a correct article for every declared
type name. F9, R1.

**Approach (python-dev)**

- Sub-entity verbs use the kind's labels (`stories`, `add-story`), as `update` already does.
- Type group and create summaries choose the article from the declared name (`an epic`), one helper
  used by every generator; no per-type literal.
- Generated summaries meet R1 (72 characters, verb first) for the bundled spec and for ST10's
  fixture override.

**Tests**

- Table over the bundled types and the fixture's vowel-initial type: rendered group and create
  summaries, article and length.

**Falsify.** Hard-code `a`: the vowel-initial row goes red. Restore.

**Acceptance**

- FEAT-1024 US8 bullets 2 and 3 for generated text.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
- [2026-10-17T04:57:49Z] `python-dev` Elias Python:
  - Done. Generated summaries take the article from the declared name (common.article) and the kind labels for the add, list, group, show, body and remove verbs; remove names the mapping kind only when one maps onto it. Falsification: hard-coding "a" turns 3 new tests red; a kind verb back to sub-entity 4; plural list back to sub-entities 1; an over-long create summary 3; 8 distinct new tests go red across the reverts.
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Add the tests/meta guard that walks the command tree

<!-- sq:subtask:ST10:body -->
**Goal.** A `tests/meta` guard walks the live command tree and holds help to the mechanical half of
the rule. F11.

**Approach (python-dev)**

- Walk the Click tree in-process under the bundled spec in a tmp squad, covering per-type and
  per-kind commands, and assert for every canonical command: (1) non-empty option and argument
  descriptions; (2) a one-line summary of 72 characters or fewer; (3) no doubled backtick, role or
  `::` line ending; (4) no bracket tag; (5) no body line over 78 columns; (6) no truncation ellipsis
  at 80 columns; (7) a body over 10 source lines (after the summary paragraph, before any form feed,
  blank lines not counted) appears in an immutable module-constant tuple of (command path, one-line
  reason) pairs, and an entry that no longer matches such a body fails as stale.
- The allowlist is seeded with what remains after ST2, ST5 and ST6; each reason names what a reader
  would type or read differently.
- A second walk under a test-local override declaring one custom type with a sub-entity kind and a
  ref kind (vowel-initial, irregular plural, realistic label length) walks that type's group and
  kind verbs, its create command and the root listing, with the same assertions on squads' own
  strings only.
- All seven assertions are enabled here, after the subtasks that fix their findings.
- No module-level mutable state (the tuple is immutable); runs in the default suite in a few
  seconds.

**Tests / falsify.** The task body's guard falsification list, one violation per assertion plus a
stale allowlist entry; the handoff records each red run.

**Acceptance**

- FEAT-1024 US9, all bullets; ST1's stated line count matches the implementation.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
- [2026-10-17T04:57:52Z] `python-dev` Elias Python:
  - Done. tests/meta/test_every_help_screen_follows_the_help_rule.py walks the command tree twice (bundled vocabulary, and an override with one vowel-initial type, an irregular-plural kind and a ref kind) under six checks, plus the 10-line body allowlist (starts empty, stale entries fail, form-feed notes ignored). CONTRIBUTING names the guard. Falsification: blank option 3 red, 73-character summary 3, doubled backtick 2, bracket tag 2, 79-column line 2, ellipsis 3, 11-line body off the allowlist 1, stale allowlist entry 1; loosening a check limit turns its self-check red (2 runs, 1 each).
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Match the docs and CHANGELOG to the shipped help

<!-- sq:subtask:ST11:body -->
**Goal.** Docs and the CHANGELOG match the shipped help.

**Approach (tech writer, from the ST10 handoff)**

- Confirm `docs/stability.md` and `docs/faq.md` carry what ST2 and ST3 required, with no internal
  references.
- The unreleased CHANGELOG entry describing the help changes for adopters, no item ids.
- Every docs passage that quotes a help screen or flag description matches the shipped text: find
  them with `rg -n "sq [a-z-]+ --help|Usage: sq" docs README.md` plus a search for each changed
  flag description, and re-render each.

**Acceptance**

- FEAT-1024 US10, all bullets.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
- [2026-10-17T05:07:39Z] `tech-writer` Theo Writer:
  - Done. CONTRIBUTING rule 9 matches the shipped layout (REV-1093 F7). Re-rendered from a HEAD export: retype, reflog --op, the comment group, roster epilogs and comment edit/remove --as. No doc quotes those screens; the README and docs synopses use placeholders that still match. CHANGELOG 0.16.0 Changed gains two entries: one help rule with every option described, and one-line exit codes. The help guard is left out because adopters cannot see it.
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:16:00Z] `tech-lead` Olivia Lead:
  - Broken down into ST1-ST11: writer strings and docs first (ST1-ST6), then developer placement and the guard (ST7-ST10), writer docs last (ST11). Depends on TASK-1072, the last CLI-changing task. No migration. @manager ready for review of the plan.
- [2026-10-17T04:11:15Z] `tech-writer` Theo Writer:
  - ST1 to ST6 are done and uncommitted (commit point). Changed: CONTRIBUTING.md, docs/stability.md, docs/faq.md, 15 files under src/squads/_cli/ (help strings and docstrings only, plus three moved-reasoning comments), and two tests that pinned rewritten wording (test_override_commands_cli, test_roster_type_address_verbs). No CLI golden changed. Gates: ruff check and format clean, pyright clean on _cli, and tests/cli, tests/meta and tests/integration green.
    
    For @python-dev (ST7 to ST10):
    - ST7: the canonical wordings are on ST4 and already sit at every site, so declaring each once in _common.py is mechanical. `--as` "(required)" and the `--priority`/badge flags are untouched.
    - ST8: every body I wrote is in single backticks and wrapped at 78 columns. Left for you: the comment group's three line-structured lines (82 to 85 columns), the role, operator and skill epilogs, renumber's indented `git show` line, retype NEW-TYPE and reflog `--op`.
    - ST9: the generated summaries are listed on ST6.
    - ST10: `\f` is now used by tree, role catalog, role list and role set-default. Nothing is over 10 body lines by the ST1 count (the longest is graph and override scaffold at about 6), so the allowlist may start empty. Add one sentence naming the guard to the CONTRIBUTING section.
    
    @manager ready for the 80-column read.
- [2026-10-17T04:11:33Z] `tech-writer` Theo Writer:
  - Correction to my handoff: by the ST1 count the longest bodies are tree (9), graph (8), import (7), list and override scaffold (6). None is over 10, so the allowlist can still start empty.
- [2026-10-17T04:25:37Z] `reviewer` Paul Reviewer:
  - Writer pass ST1-ST6 reviewed in REV-1093: ChangesRequested, one medium (repair --renumber help and exit line) and four low findings, all text fixes. REV-958 mapping is on REV-1093. @tech-writer
- [2026-10-17T04:57:54Z] `python-dev` Elias Python:
  - ST7 to ST10 done and uncommitted. Gates: pyright 0 errors; ruff check and format clean on src, tests, scripts; tests/cli, tests/meta, tests/integration and tests/unit green (8594 passed); sq check clean. For ST11: CONTRIBUTING rule 9 says a no-rewrap block needs a backspace marker, but Typer keeps line breaks in every paragraph after the first (the marker prints a blank line there); the rule should say line-structured text goes after the first paragraph. Epilog examples are one paragraph per line. Docs quoting help may mention the changed retype, reflog --op, comment group, roster usage (<slug|id|n> once) and LOCAL-ID text. @tech-writer
<!-- sq:discussion:end -->
