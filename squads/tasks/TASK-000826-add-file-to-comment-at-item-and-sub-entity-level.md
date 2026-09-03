---
id: TASK-826
sequence_id: 826
type: task
title: Add --file to comment at item and sub-entity level
status: Done
author: tech-lead
priority: high
refs:
- BUG-825:fixes
- MILE-836:targets
description: comment accepts only -m, unlike body; the one input path silently runs
  shell substitutions
subentities:
- local_id: ST1
  title: Wire --file into both comment commands
  status: Done
- local_id: ST2
  title: Cover the comment input-source contract in tests
  status: Done
- local_id: ST3
  title: Teach the agent-facing guidance to use --file for comments
  status: Done
created_at: '2026-08-26T11:24:45Z'
updated_at: '2026-08-26T16:01:10Z'
---
<!-- sq:body -->
## Description

`sq <type> <n> comment` and `sq <type> <n> <kind> <k> comment` accept only `-m/--message`.
Neither takes `--file`, while `body` takes it at both levels. Verified in
`src/squads/_cli/_items.py`: `comment` (line 441) and `s_comment` (line 986) declare
`message: list[str] = typer.Option(..., "-m", "--message", …)` and no `file` parameter,
whereas `body` (lines 417-418) and `s_body` (lines 964-965) declare both and resolve them
through `resolve_body(message or None, file)`.

The failure is clean, not silent: `sq bug 825 comment --as tech-lead --file /dev/null`
exits 2 with a `No such option: --file` panel on stderr and empty stdout (reproduced
directly, not through a pipe).

## Why this outranks a missing convenience flag

`-m` is the only input path for comments, and an unescaped backtick inside a
double-quoted `-m` argument is substituted by the shell before `sq` ever runs. A probe
authored with a backtick-quoted `sq check` inside the message stored
`run the [check output] command to verify unescaped`: the shell **executed** the enclosed
command and spliced its output into the argument. Not text quietly dropped — a command
quietly run and its output written into the permanent record. `sq check` reports clean
afterwards because markers and structure are intact, so nothing in the tool detects it.
Every long or code-bearing comment currently goes through that one path. `body` already
has the escape hatch; comments do not.

## Survey: is `comment` the only gap?

Checked before scoping. Every long-option name declared under `src/squads/_cli/` was
enumerated; the prose-body inputs are `-m/--message` sites, and all of them pair it with
`--file` except the two comment commands:

- has both: `create` (3 sites, `_create.py` 114/117, 368/371, 449/452), item `body`
  (`_items.py` 417/418), sub-entity `body` (964/965), `add-<kind>` body seeding
  (785/791), `sq board post` (`_board.py` 43/44), `sq skill … body` (`_skill.py` 150/151)
- file-only by design: `sq memory <role> add` (`_memory.py` 155) takes the one-line fact
  as a positional argument and the write-up via `--file`
- missing `--file`: item `comment` and sub-entity `comment` — these two, nothing else

Near-misses deliberately out of scope: `--desc`, `--title`, `--when-to-use` are
single-line metadata fields, not prose bodies. So this is a two-command fix, not a
sweep.

## Behaviour to deliver

1. Both comment commands accept `--file PATH`, sharing the same content-source
   resolution the body commands use (`resolve_body`/`resolve_body_optional` in
   `_cli/_common.py`) rather than a second parallel implementation.
2. `-m` and `--file` are **mutually exclusive**, mirroring `body` exactly: supplying both
   is a clean `SquadsError` (exit 1) naming both flags. Nothing about comments argues for
   merging the two sources, and one shared error string keeps the two surfaces honest.
3. `--file -` reads stdin, mirroring `body`.
4. Repeated `-m` keeps its current meaning — one bullet per message
   (`_discussion.format_comment`). A file is **one** message: a single bullet whose
   continuation lines stay indented at the bullet's content column, so blank lines and
   fenced code blocks survive intact. The file content is not split into bullets on blank
   lines — shredding fenced blocks would defeat the reason `--file` exists here. `--file`
   is therefore not repeatable, and one invocation appends exactly one discussion entry.
5. Omitting both sources stays a clean, non-traceback error that names both flags. `-m` is
   currently a required Typer option, so making it optional must not turn a missing
   message into a traceback or a silently empty comment.
6. An empty or whitespace-only file is refused with a clean error, not appended as an
   empty bullet. Note that today `resolve_body` returns `""` for an empty file (it only
   raises when both sources are absent) and the service's guard only rejects an *empty
   list* of messages — so an empty file would currently slip through as a blank bullet.
7. File content passes the same marker guard as `-m` content: a file containing an sq
   marker tag is refused exactly as an inline message is.
8. `--as` remains required at both levels; authorship, mention extraction, and the
   discussion tag routing (item vs sub-entity) are unchanged.

Do not redesign the discussion format. The implementer picks the plumbing.

## Acceptance criteria

- `sq <type> <n> comment --as <slug> --file PATH` and
  `sq <type> <n> <kind> <k> comment --as <slug> --file PATH` both append the file's
  content as one comment, exit 0, and read back verbatim through
  `sq <type> <n> show --full --comments` — including a fenced code block with internal
  blank lines.
- `--file -` reads stdin at both levels.
- `-m` together with `--file` exits 1 with the shared "not both" message at both levels.
- Neither source given exits 1 with a message naming `-m` and `--file` at both levels.
- An empty or whitespace-only file exits 1 with a clean error and leaves the discussion
  unchanged.
- A file whose content contains an sq marker tag is refused the same way an inline
  message is.
- Repeated `-m` still produces one bullet per message; a `--file` comment produces one.
- `--help` on both comment commands lists `-m/--message` and `--file`.
- Full suite green; `pyright` and `ruff` clean under `--all-extras`; `sq check` clean.

## Coordination

A developer is working in `src/squads/_backends/` and on the check validators on another
task. `src/squads/_cli/` is expected to be free, but confirm before starting rather than
assuming — and expect the shared helpers in `_cli/_common.py` to be the contended surface
if anything is.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 826 add-subtask "<title>"`; track with `sq task 826 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Wire --file into both comment commands

<!-- sq:subtask:ST1:body -->
Add a `--file` option to the item-level `comment` command and the sub-entity-level
`comment` command in `src/squads/_cli/_items.py` (the two commands built by `_cmd_comment`
and by the sub-verb registrar), resolving content through the existing shared helper in
`_cli/_common.py` rather than a second implementation.

Both must end up with the same content-source contract the body commands already have:
mutually exclusive with `-m`, `--file -` reads stdin, and a clean error when neither is
given (`-m` is currently a required Typer option at both levels, so relaxing it must not
turn a missing message into a Typer exit-2 panel or an empty comment).

A file is one message, not many: pass it to the service as a single-element message list
so `format_comment` renders one bullet and indents its continuation lines, keeping blank
lines and fenced code blocks inside the list item. Reject empty or whitespace-only file
content with a clean error — the current helper returns an empty string for an empty file
and the service guard only rejects an empty list, so that case needs an explicit refusal.
File content goes through the same marker guard as inline messages.

Leave authorship (`--as`), mention extraction, and item-vs-sub-entity discussion routing
untouched.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Cover the comment input-source contract in tests

<!-- sq:subtask:ST2:body -->
Add CLI coverage mirroring the existing body input-source tests
(`tests/cli/test_body_content_source_and_mutual_exclusion_cli.py` and
`tests/cli/test_subentity_body_input_parity_cli.py`), so the comment surface is pinned at
both levels rather than only where it was first wired.

Cover, at the item level and the sub-entity level: content read from a real file; content
read from stdin via `--file -`; `-m` plus `--file` refused with exit 1; neither source
given refused with exit 1 and a message naming both flags; an empty or whitespace-only
file refused with the discussion left unchanged; a file containing an sq marker tag
refused the same way an inline message is.

Include a round-trip case whose file holds a fenced code block with internal blank lines
and a line of prose after it, asserting it reads back verbatim through
`show --full --comments` — that is the shape the whole change exists to carry, and a
single-line fixture would not catch a bullet-splitting regression. Also assert repeated
`-m` still yields one bullet per message while a `--file` comment yields one.

Name the files by behaviour, not by ticket.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Teach the agent-facing guidance to use --file for comments

<!-- sq:subtask:ST3:body -->
The fix only reduces the risk if the guidance an agent reads tells it to use `--file` for
long or code-bearing comments. Today the generated guidance points at `--file` for bodies
and shows comments as `-m` only.

Update the relevant Jinja templates under `src/squads/_rendering/templates/` — the squads
skill, the workflow cheatsheet partial, and the CLAUDE.md/AGENTS.md managed sections all
carry comment examples — so the comment line mentions `--file` alongside `-m`, with a
short note that a message containing backticks or a code fence belongs in a file. Edit the
templates, never the rendered files; the rendered CLAUDE.md region and the pointer files
are regenerated by `sq sync`.

Regenerate the affected goldens under `tests/goldens/` (the skill bodies, the workflow
cheatsheet, and the managed-section snapshots) and check the rendered output reads
naturally rather than mechanically.

If `docs/` shows a comment example where the file form is the better advice, update it in
the adopter's voice — describing the tool, with no reference to this repo's process or
tracker.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T11:25:42Z] Olivia Lead:
  - Standalone by design: no open feature covers CLI input surfaces (checked every non-terminal feature), so this is purely-technical work linked to the defect by a fixes ref rather than parented.
  - Scope settled before authoring: the two comment commands are the only prose-body inputs in the CLI without --file; --desc/--title/--when-to-use are single-line metadata and stay out.
- [2026-08-26T12:34:10Z] Elias Python:
  - Implemented all three subtasks.
    
    - `--file` added to both `comment` commands, resolved via new `resolve_comment_messages` in `_cli/_common.py` (shares `_read_source_file` with `resolve_body*`); `-m` now optional so "neither given" reaches the shared SquadsError, not a Typer exit-2 panel. `-m`+`--file` -> "not both" (exit 1). File is one bullet (list of 1), never joined/split, so fenced blocks with blank lines survive.
    - Empty/whitespace-only file: refused with "--file must not be empty" (exit 1), discussion untouched — deliberate, since a comment has no meaningful empty form (unlike body).
    - Marker guard: file content flows through the same `messages` list as `-m`, so `reject_markers` catches it identically — no separate wiring needed.
    - Drove the original hazard in a scratch squad: `--file` round-tripped a fenced code block containing literal `sq check` verbatim; the same text via unescaped-backtick `-m` got shell-substituted into "run the ✓ no issues command..." — confirmed the fix addresses the actual defect, not just the flag gap.
    - ST3: updated workflow.md.j2, squads_skill.md.j2, claude_section.md.j2, agents_section.md.j2 to show `--file` alongside `-m` for comments, with the backtick/shell-substitution rationale. Regenerated the 4 affected goldens (workflow_cheatsheet[_raw], claude_md_section, agents_md_section) — only those 4 changed. docs/ comment examples are all short prose (no backticks/code) so none needed the file-form callout.
    - Manifest: ran gen_template_manifest.py (only the 0.14.0 entry moved, 4 new blobs), then `git fetch --tags && seed_content_store.py --rebuild` (dropped 3 pre-existing orphans, none of mine), then `--release-gate` — passes clean.
    - Tests: new `tests/cli/test_comment_content_source_and_mutual_exclusion_cli.py` (16 cases, item+sub-entity level: file/stdin/both/neither/empty/marker/bullet-count/fenced round-trip). `tests/meta` 258 passed. `tests/cli/ tests/service/ tests/unit/` + the squads-skill integration test: 3218 passed, 2 failed — both in `test_unreadable_files_degrade_per_file_cli.py::test_repair_recovers...`/`test_a_clean_board_exits_0...`, tracing into `_services/_maintenance.py::repair` (`ValueError: too many values to unpack`), which is TASK-828's in-flight repair-path work, not touched by me. pyright/ruff/ruff-format clean on everything I touched. `sq check` clean.
    
    Nothing left undone on this task's scope. @reviewer
<!-- sq:discussion:end -->
