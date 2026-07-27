---
id: TASK-673
sequence_id: 673
type: task
title: Malformed frontmatter and config fail cleanly, not with a traceback
status: Draft
author: tech-lead
refs:
- BUG-669:fixes
- TASK-672:depends-on
description: Guard the unguarded YAML and TOML parses on the read path so a hand-edited
  or merge-broken file produces a clean error naming it, instead of a raw traceback.
subentities:
- local_id: ST1
  title: Guard the .squads.toml parse
  status: Todo
- local_id: ST2
  title: CLI-layer tests pinning the clean failure
  status: Todo
- local_id: ST3
  title: Guard the frontmatter parse and name the file
  status: Todo
created_at: '2026-07-27T21:07:24Z'
updated_at: '2026-07-27T21:45:59Z'
---
<!-- sq:body -->
A `.md` whose frontmatter is malformed YAML *with an intact closing delimiter* — a hand-edit, a badly
resolved merge conflict, a file restored from a partial patch — raises a raw `yaml.YAMLError` out of
the read path. `handle_errors`/`command` in `_cli/_common.py` only catch `SquadsError`, so the user
gets a full Rich traceback with venv paths and `anyio`/`yaml` internals instead of the clean
`error: …` line every other `sq` failure produces.

Fixes BUG-669. Read it first — it has the reproduction and the shape of the corrupt file.

## Why it matters more than a cosmetic traceback

It escapes `sq repair` too, which is the tool an operator reaches for *precisely because* something
on disk looks wrong. And the corruption is invisible until then: `sq list` and `sq <type> N show`
resolve from `.squads.json` and never re-parse the `.md`, so nothing warns until a command rescans
disk — at which point it crashes instead of reporting.

## Read path, not write path

This is distinct from the torn-write defect the atomic-write work closed, and that work cannot fix
it: the file here is fully intact — valid delimiters, no truncation — and its *content* is invalid
YAML. It was never a torn write.

One clarification so the boundary is not mis-drawn: `_sections.replace_frontmatter` also calls
`split_frontmatter`, so a mutation of a corrupt item hits the same parse. Guarding inside
`split_frontmatter` covers that for free, and it should — a mutation of a corrupt file should fail
with the same clean message. That is not "extending the fix into the write path"; it is one guard at
the parse, benefiting every caller. Do not add write-path logic.

## Scope: derive the call-site list from a fresh grep

The bug body was written from inspection and names three commands. It undercounts. **Start from
`grep -rn "split_frontmatter(\|read_frontmatter(" src/`** and work the real list; what follows is
what that grep showed when this was written, as a floor rather than a specification.

Live callers of the unguarded parse, and the commands they sit under:

| Call site | Reached by |
|---|---|
| `_itemfile.read_frontmatter` → `_maintenance` scan/confirm paths | `sq check` |
| `_maintenance._rebuild_index_from_disk` | `sq repair` |
| `_maintenance._scan_records` | `sq renumber`, `sq migrate repad` |
| `_maintenance._apply_remap` | `sq renumber`, `sq repair --renumber` |
| `_backends/_claude_code/_backend.py` managed-skill read | **`sq sync`** |
| `_board/_store.py` notice read | **`sq board list`** |
| `_memory/_store.py` entry read (×2) | **`sq memory list` / `show`** |
| `_sections.replace_frontmatter` | any mutation of the corrupt item |

The four in bold are not in the bug body. `board list` and `memory list` matter out of proportion to
their size: this project's own agents run both at the start of every session, so a corrupt notice or
memory entry greets an agent with a traceback before it does anything.

Migration runners under `_migrations/` also call it. Leave them alone — frozen, one-shot,
operator-driven code, preceded by the runbook's version-control rollback point.

## A second, wider instance of the same defect

`_paths.load_config` parses `.squads.toml` with a bare `tomllib.load(fh)`; only the
`ValidationError` from `SquadsConfig.from_toml_dict` below it is caught. A malformed `.squads.toml`
therefore raises a raw `tomllib.TOMLDecodeError`.

Its blast radius is larger than the frontmatter one: path resolution runs in the root CLI callback,
so **every** `sq` command crashes with a traceback, including the ones an operator would try in order
to diagnose it. Same trigger class (hand-edit, merge conflict), same missing guard, same one-line
fix, and every other TOML loader in the codebase (`_roles/_loader`, `_roles/_resolver`,
`_interactions/_loader`, `_workflow/_loader` ×3) already catches `TOMLDecodeError` and re-raises a
`SquadsError` — this one is the outlier. Follow their message shape rather than inventing a new one.

It is folded in here as its own subtask because it is the same defect on the same read path and
splitting it would leave half a fix; the bug as filed does not mention it.

## The error message

Name the offending file. Someone hitting this has a broken `.md` somewhere in a folder of hundreds
and needs to know which one — a clean message that does not say *which* file is barely better than
the traceback, which at least contained a line number.

Design note the implementer will hit immediately: `split_frontmatter(text)` takes text, not a path,
so it cannot name the file by itself. Give it an optional source label (the callers that have a path
pass it; `read_frontmatter` already takes one) rather than catching at each of the call sites — one
guard, one message shape. Where a caller genuinely has no path, the message degrades to naming the
parse failure alone.

Include enough of the underlying parse error to be actionable — YAML's own message carries the line
and column within the block, which is the thing that lets someone find the merge marker.

## Out of scope, deliberately

- **Recovery.** No attempt to repair, quarantine, or partially parse a malformed file. The user
  fixes the file; `sq` just says which one and why.
- **`check` continuing past the bad file.** Today one corrupt file aborts the whole scan, so the rest
  of the board stays unseen. Reporting it as a per-file `CheckIssue` and continuing would be better
  for `check` specifically, and would fit the single-source issue class exactly — but it changes
  `check`'s contract, and it is not what this fix is for. Worth raising separately; do not do it here.
- **Invalid UTF-8.** A file that is not decodable at all raises `UnicodeDecodeError` from the read
  helper, one layer above this parse. Same class of gap, different trigger, not this ticket.

## Sequencing

Lands **after** TASK-672. This touches `_sections.py` and callers in `_services/_maintenance.py`,
where 672's dev is working; 667 and 247 come later and touch neighbouring code. Nothing here depends
on 672's logic — it is purely a collision-avoidance ordering.

## Acceptance

Pin the **user-visible** outcome, not the exception type. A test asserting only
`pytest.raises(SquadsError)` would pass while the CLI still printed a traceback, so every one of
these is asserted at the CLI layer:

- A malformed-but-closed frontmatter produces a single clean `error: …` line naming the file, and
  the documented exit code — no traceback, no venv paths, no `anyio`/`yaml` frames — from `sq check`,
  `sq repair` and `sq renumber` at minimum, and from every other command in the table above.
- A malformed `.squads.toml` produces the same clean shape from an ordinary command, not a
  `TOMLDecodeError` traceback.
- The message names the offending file and carries the parse error's own location detail.
- A well-formed board with no corrupt file behaves exactly as before: no new output, unchanged exit
  codes, unchanged messages.
- `uv run sq check` clean; the suite green under `uv run --all-extras`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 673 add-subtask "<title>"`; track with `sq task 673 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Guard the .squads.toml parse |  |
| ST2 | Todo |  | CLI-layer tests pinning the clean failure |  |
| ST3 | Todo |  | Guard the frontmatter parse and name the file |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Guard the .squads.toml parse

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Guard the `.squads.toml` parse — the same defect with a wider blast radius.

`_paths.load_config` does:

    with config_path.open("rb") as fh:
        data = tomllib.load(fh)

with no guard. Only the `ValidationError` from `SquadsConfig.from_toml_dict` below it is caught, so a
malformed `.squads.toml` raises a raw `tomllib.TOMLDecodeError`.

This is worse than the frontmatter case rather than a footnote to it: path resolution runs in the
root CLI callback, so *every* `sq` command crashes with a traceback — including the ones an operator
would reach for to work out what is wrong. There is no command that still works.

Every other TOML loader in the codebase already handles this: `_roles/_loader`, `_roles/_resolver`,
`_interactions/_loader` and `_workflow/_loader` (three sites) each catch `TOMLDecodeError` and
re-raise a `SquadsError`. This one is the outlier. Match their message shape — name the file, carry
the decoder's own position detail — rather than inventing a new phrasing for the same failure.

Note this is not in BUG-669 as filed; it was found while mapping the call sites for that fix.

Acceptance:
- A malformed `.squads.toml` produces a clean `error: …` line naming the file, from an ordinary
  command, with the documented exit code and no traceback.
- The message shape matches the existing TOML loaders rather than being a one-off.
- A well-formed config resolves exactly as before.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — CLI-layer tests pinning the clean failure

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Pin the outcome a user actually sees, at the CLI layer.

A test asserting `pytest.raises(SquadsError)` at the service layer would pass while the CLI still
printed a traceback — the exception type was never the defect. Assert what reaches the terminal.

**Fixtures.** Two corrupt-file shapes, both realistic and both *intact*, not truncated:

- an item `.md` with valid `---` delimiters and unresolvable YAML between them — the merge-conflict
  shape from the bug's reproduction (`<<<<<<< HEAD` markers) is the one to use, since that is how
  this actually reaches a user;
- a `.squads.toml` with a syntax error.

**Per command.** For the frontmatter case, drive each affected command and assert a single clean
`error: …` line naming the file, the documented exit code, and no traceback: `sq check`, `sq repair`,
`sq renumber` at minimum, plus `sq sync`, `sq board list` and `sq memory list`, whose corrupt-input
paths the bug body missed. For the config case, any ordinary command will do — the failure is in
resolution, before the command runs.

Assert the *absence* of a traceback explicitly, not just the presence of the message: check that the
output carries no `Traceback`, no venv path fragment, and no `yaml`/`tomllib` frame. That is the
regression this ticket exists to prevent, and only an explicit assertion catches it if someone later
re-raises the underlying error.

Verify exit codes on a bare invocation (`cmd >/dev/null 2>&1; echo $?`) — a pipeline masks the
status, and this repo has been misled by that before.

**The negative case.** A clean board produces byte-identical output and exit codes to before, across
the same commands. The guard must be invisible when nothing is wrong.

Name tests by the behaviour they pin, never by a ticket id.

Acceptance:
- Every command in the table refuses cleanly on a corrupt file, asserted through the CLI.
- No output contains a traceback, a venv path, or a parser frame.
- Exit codes asserted bare, not through a pipe.
- A clean board is unaffected across the same commands.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Guard the frontmatter parse and name the file

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Guard the frontmatter parse, once, where every caller reaches it.

`_sections.split_frontmatter` calls `yaml.safe_load(m.group(1))` with nothing around it. Wrap it,
and raise a `SquadsError` carrying both the offending file and the parse error's own location
detail — YAML's message includes the line and column inside the block, which is what lets someone
find the merge marker or the bad indent.

**Naming the file needs a source label.** `split_frontmatter(text)` takes text, not a path, so it
cannot name the file on its own. Add an optional source parameter and have callers that hold a path
pass it — `read_frontmatter` already takes one, and most service callers have `item_file(...)` in
hand. Do **not** catch at each of the ~10 live call sites: one guard, one message shape, and no way
for a future caller to forget.

Where a caller genuinely has no path to pass, the message degrades to naming the parse failure
without a filename. That is acceptable; silently having no guard is not.

Work the call-site list from a fresh `grep -rn "split_frontmatter(\|read_frontmatter(" src/` rather
than from the table in the task body — that table is a floor, written at planning time.

Two boundaries:

- `_sections.replace_frontmatter` calls `split_frontmatter` too, so a mutation of a corrupt item
  starts failing cleanly as well. That is the guard working, not scope creep — do not add any
  write-path logic to preserve the old behaviour.
- Migration runners under `_migrations/` also call it. Leave them frozen; they inherit the guard
  through the shared function and need no edit.

Acceptance:
- One guarded parse; no `try`/`except` around `yaml` at any call site.
- The raised error is a `SquadsError` naming the file and including the parse error's location.
- Every live caller that has a path passes it.
- A well-formed file parses exactly as before, with no behaviour or signature change visible to
  callers that pass no source.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T21:09:05Z] Olivia Lead:
  - Cut from BUG-669. Scope is the read-path parse guard: one guarded parse in `split_frontmatter` with an optional source label so the error names the file (it takes text, not a path — that is the first thing an implementer hits), plus CLI-layer tests that assert the absence of a traceback rather than just the exception type.
  - Two things the bug body does not have. The call-site list undercounts: beyond check/repair/renumber it also reaches `sq sync` (the backend's managed-skill read), `sq board list` and `sq memory list` — the last two matter because this project's agents run them at the start of every session, so a corrupt notice greets an agent with a traceback. And `_paths.load_config` parses `.squads.toml` with a bare `tomllib.load`, so a malformed config tracebacks on EVERY command including the ones you would try to diagnose it; every other TOML loader in the codebase already guards this, that one is the outlier. Folded in as its own subtask.
  - REFS NOT SET — `ref add` fails against the current working tree (`TypeError: update_frontmatter() missing 1 required positional argument: 'base'`, TASK-672's dev mid-edit). Verified no half-applied state: file and index both show refs empty, subentities agree. @manager please run once the tree builds: `uv run sq task 673 ref add BUG-669 --kind fixes` and `uv run sq task 673 ref add TASK-672 --kind depends-on`.
<!-- sq:discussion:end -->
