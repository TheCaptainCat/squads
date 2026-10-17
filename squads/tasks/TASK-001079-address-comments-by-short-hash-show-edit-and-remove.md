---
id: TASK-1079
sequence_id: 1079
type: task
title: 'Address comments by short hash: show, edit and remove'
status: Done
parent: FEAT-1017
author: tech-lead
priority: medium
refs:
- TASK-1070:depends-on
- TASK-992:depends-on
- TASK-1078:depends-on
- ADR-1013
description: derived comment hash, comment <hash> show|edit|remove at every level
  by the author, hash in renders/JSON/hits, guidance and docs
subentities:
- local_id: ST1
  title: Derive the comment hash and resolve a prefix within one scope
  status: Done
  story: US2
- local_id: ST2
  title: Splice comments by line span, with the edit mark and the legacy-line refusal
  status: Done
  story: US8
- local_id: ST3
  title: Make comment a group that routes a hash to show, edit and remove
  status: Done
  story: US1
- local_id: ST4
  title: Show one comment, with a --json record
  status: Done
  story: US3
- local_id: ST5
  title: Edit a comment by its author, keeping header and position
  status: Done
  story: US4
- local_id: ST6
  title: Remove a comment by its author, with confirmation
  status: Done
  story: US5
- local_id: ST7
  title: Refuse duplicate comments on write, merge or remove them together
  status: Done
  story: US6
- local_id: ST8
  title: Record comment edits and removals in the reflog
  status: Done
  story: US7
- local_id: ST9
  title: Put the hash in every render, JSON payload, search and inbox hit
  status: Done
  story: US9
- local_id: ST10
  title: Register the comment address verbs on skills, roles and operators
  status: Done
  story: US10
- local_id: ST11
  title: Teach the address verbs in bundled guidance and the managed CLAUDE.md region
  status: Done
  story: US11
- local_id: ST12
  title: Show the comment hash and edit mark in the VS Code client
  status: Done
  assignee: typescript-dev
  story: US9
- local_id: ST13
  title: Document hash addressing in the docs, CHANGELOG and CLAUDE.md conventions
  status: Done
  assignee: tech-writer
  story: US11
- local_id: ST14
  title: Add the dated notes ADR-1013 owes to ADR-979 and ADR-981
  status: Done
  assignee: architect
  story: US11
created_at: '2026-10-16T21:12:16Z'
updated_at: '2026-10-17T02:12:55Z'
---
<!-- sq:body -->
## Scope

A comment gets a derived short hash and an address: `sq <type> <n> [<kind> <k>] comment <hash>
show|edit|remove`, and the same under `sq skill|role|operator <addr>`. Only the comment's author
edits or removes it. The hash appears in every render, JSON payload, search and inbox hit, and the
VS Code client. Covers FEAT-1017 US1 to US11. ADR-1013 is the spec; each subtask cites its
numbered sections and adds acceptance only.

Out of scope (ADR-1013 and the feature): per-bullet addressing, import events that edit or
remove, access control beyond the author match, a tombstone, a stored comment id, millisecond
timestamps, and any migration of existing comments.

## Rulings this task carries (binding, not reopened)

- The hash covers item sequence number, author slug, timestamp as written and the comment text;
  an edit gives a new hash, a stale hash is refused; timestamps stay whole seconds; nothing is
  migrated (op-pierre, 2026-10-15T19:54:29Z, ADR-1013).
- The verbs follow the address grammar, item and sub-entity alike; no `edit-comment` or
  `remove-comment` verbs (op-pierre, 2026-10-15T20:08:33Z).
- `comment <hash> show [--json]` exists (op-pierre, 2026-10-15T20:09:44Z).
- Duplicates (same author, same second, same text): refused on write, tolerated on load, merged
  on edit, removed together (op-pierre, 2026-10-15T19:31:40Z, ADR-1013 §6).
- `edit` and `remove` are allowed on system skills and roles: a comment is not generated content,
  so the TASK-1069 gate is never called (op-pierre, 2026-09-29 and 2026-10-16, FEAT-976/977).
- The author match is not a permission; no text may call it one (ADR-1013 §9).

## Migration

None. `hash` is derived and never written; the edit mark is one optional group in the header
grammar ADR-979 ships in 0.16. `src/squads/_migrations/_v0_15_to_v0_16.py` is not touched, and
the handoff confirms the diff under `_migrations/` is empty.

## Order

Depends on TASK-1070 (the roster `comment`/`comments` helpers and the skill discussion region
this extends), TASK-992 (the write-count guard and the single-write importer, which the duplicate
refusal in `_services/_import.py` sits in), and the FEAT-1054 task (same roster CLI modules, one
Python stream). TASK-1071 depends on this task: both change the comment header render. Shared
files:

| file | TASK-992 | TASK-1070 | this task |
|---|---|---|---|
| `_discussion.py` | none | none | ST1, ST2 |
| `_services/_collab.py` (`_comment_core`) | none | none | ST5, ST6, ST7 |
| `_services/_import.py` | ST3 single write | none | ST7 duplicate refusal |
| `_cli/_common.py`, `_cli/_items.py` | none | ST3 shared comment helpers | ST3 the `comment` group |
| `_cli/_skill.py`, `_cli/_role.py`, `_cli/_operator.py` | none | ST3 | ST10 |
| `_index/_reflog.py` | none | none | ST8 |
| JSON builders, `_tui/` reader, search and inbox | none | none | ST9 |
| bundled guidance templates, `_specs/playbook.toml`, manifest | none | ST2 manifest | ST11 |

## Files touched

`src/squads/_discussion.py`, `_services/_collab.py`, `_services/_import.py`, `_cli/_items.py`,
`_cli/_common.py`, `_cli/_skill.py`, `_cli/_role.py`, `_cli/_operator.py`, `_index/_reflog.py`,
the JSON builders and renders (`comments --json`, `show --json`, search, inbox, the TUI reader),
`clients/vscode` (`SqDiscussionEntry` and the preview), the bundled templates of ST11,
`_rendering/templates_manifest.json`, the managed-section golden; tests under `tests/unit`, `tests/service`,
`tests/integration`, `tests/cli`, `tests/meta` and the VS Code client tests. Docs, CHANGELOG and
the hand-authored `CLAUDE.md` line are ST13; the ADR notes are ST14.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-1017 US1 to US11 is pinned by a named test (or, for docs, a
  checked passage); the handoff maps bullet to test.
- **Table-driven shape tests**, one parametrised module per backbone table, as ADR-1013's Tests
  consequence lists:
  - *Canonicalisation* (ST1): CRLF against LF, trailing spaces and tabs, leading and trailing
    blank lines, inner blank lines in a fenced block, a NUL; plus a pinned vector.
  - *Position by shape* (ST5, ST6): first, middle, last, only comment; a region with a preamble;
    item, sub-entity and roster regions; multi-line and fenced bodies. Invariant: every other line
    of the file byte-identical after the verb.
  - *Address by level* (ST3, ST4, ST10): item, sub-entity, skill, role, operator, system skill,
    system role, by every parse shape of FEAT-1017 US1 and every prefix shape of US2.
- **Pipeline invariants:** after every `edit` and `remove`, `sq check` and `sq repair` are clean
  and delete-index-then-repair gives identical values; the hash an edit prints equals the hash a
  fresh load computes; markdown is written before the index commit and each item file once per
  transaction (the TASK-992 guard, no allowlist entry added); refusals write no file and no
  reflog line.
- **A falsified test per subtask:** break the change on purpose, watch the named test go red,
  restore; the handoff records what was broken and which test went red.
- A service-level test and a CLI smoke test per behaviour change; CLI tests assert the bare exit
  code and the printed text; `--json` stays valid under the harness colour setting.

## Gates and working rules

TASK-1069's gates apply unchanged: pyright and ruff with `--all-extras`, `~/.local/bin/sq check`
clean, `tests/meta` on any module constant, bundled-byte or import-edge change, selection derived
from the diff plus the floor for `_cli/`, `_specs/` and `_rendering/templates/` changes
(`tests/meta`, `tests/integration`, `tests/cli`), the manager runs the full suite; one-or-two
sentence comments with no versions or ticket ids; no ticket ids in test file names; help text
follows REV-958's rule (R1 to R9) as written in that review; no edits to `CHANGELOG.md`, `docs/`
or the hand-written `CLAUDE.md` outside ST13; probing only in a scratch squad under the session
scratchpad.

## Subtask order

ST1, ST2 (commit point, reviewed: the pure discussion layer); ST3, ST4, ST5, ST6 (commit point,
reviewed: the verbs at item and sub-entity level); ST7, ST8; ST9, ST10 (commit point, reviewed);
ST11; ST12 (typescript-dev) after ST9; ST13 and ST14 last, from the ST11 handoff.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1079 add-subtask "<title>"`; track with `sq task 1079 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Derive the comment hash and resolve a prefix within one scope

<!-- sq:subtask:ST1:body -->
**Goal.** Every parsed comment carries `hash` (64 lowercase hex, SHA-256) computed on load and never
written, and an address resolves a hex prefix within one scope. ADR-1013 §1 and §2.

**Approach**

- `_discussion.py`: `Comment.hash` over the UTF-8 bytes of `"sq-comment-1" NUL <sequence number>
  NUL <scope> NUL <slug> NUL <timestamp as written> NUL <canonical text>`. Sequence number, not the
  formatted id. Scope empty for the item's own discussion, `<kind>:<local_id>` for a sub-entity's,
  always empty on roster entities. The edit mark and display name are never inputs.
- Canonical text exactly per FEAT-1017 US2 (CRLF and CR to LF, trailing spaces and tabs stripped
  per line, leading and trailing blank lines dropped, inner bytes kept, no Unicode normalisation,
  joined with LF, no trailing LF; no bullet lines hashes the empty string).
- One resolver: a prefix of 4 or more hex characters, case-insensitive, against the scope's
  current hashes. Unique match, ambiguous (list each candidate's short hash, author, timestamp),
  no match (`no comment <hash> in <ID>'s discussion (edited or removed since it was read?)`), and
  a match only in another scope of the same item (refused, naming that address; never acts outside
  the given scope).
- Short form: 7 characters; when two distinct hashes in a scope share 7, every hash in that scope
  renders at the shortest unique length. One function, used by every render and JSON builder.
- Nothing is written to a `.md` file or the index; the meta guard on stored fields stays green.

**Tests**

- The task body's canonicalisation table and a pinned vector (fixed inputs, fixed expected hex).
- Prefix table: unique, ambiguous, too short, non-hex, unknown, wrong scope, upper case.
- A hash stable across a retype (same sequence number); a 7-character collision built by
  monkeypatching the digest, asserting the scope widens.

**Falsify.** Hash the formatted id instead of the sequence number: the retype row goes red. Skip
the trailing-space strip: its canonicalisation row goes red. Resolve across scopes: the wrong-scope
row goes red. Change the domain prefix: the pinned vector goes red. Restore each.

**Acceptance**

- FEAT-1017 US2, all bullets.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-17T01:04:51Z] `python-dev` Elias Python:
  - Done: Comment.hash/edited_ts/span, canonical_text, short_hashes, resolve_hash (src/squads/_discussion.py); tests/unit/test_comment_hash_and_prefix.py + tests/service/test_comment_hash_survives_a_retype.py.
  - Falsified (new tests red): no trailing-space strip 2; domain tag changed 12; sequence number dropped 13; scope dropped 2; resolve across scopes 2; short form not widened 2. The retype row guards the contract but cannot go red at this layer (the formatted id never reaches the parser).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Splice comments by line span, with the edit mark and the legacy-line refusal

<!-- sq:subtask:ST2:body -->
**Goal.** The discussion layer can replace or remove given comments in a region by exact line span,
with the edit mark in the header, and refuses a region holding a legacy-shaped line. ADR-1013 §4,
§7, §8.

**Approach**

- Extend the header pattern with the optional edit mark inside the brackets, before the slug:
  ``- [<ts>, edited <ts>] `<slug>` <name>:``. Parse it into `Comment.edited_ts` (`None` when
  absent). `format_comment` gains the mark; no call site assembles a header.
- One pure function in `_discussion.py` takes a region and a mapping of comments to their
  replacement (or removal) and returns the new region, working on each comment's line span (header
  to the next header or the region end), never re-rendering the parsed list. Removal leaves no
  blank-line residue beyond the layout the region already had; an emptied region keeps its
  markers.
- A legacy-line check: any column-0 line starting with `- [` that does not match the header
  grammar, in any discussion region of the item, makes `edit` and `remove` refuse, naming the file
  and the line.

**Tests**

- The task body's position-by-shape table driven directly on the pure function: every other line
  byte-identical; removal residue matches the original layout; a preamble is preserved.
- Header round-trip: no mark, one mark, a second edit replacing the mark; the mark never changes the
  hash.
- Legacy-line table: slug-less 0.15 header, a `- [` prose line at column 0, an indented `- [` line
  (accepted).

**Falsify.** Re-render the parsed list instead of splicing: the preamble row goes red. Append a
second mark instead of replacing: the second-edit row goes red. Accept indented and column-0 lines
alike: the legacy table goes red. Restore each.

**Acceptance**

- FEAT-1017 US8 bullets 2 to 5 (the pure function, `format_comment`, byte-identity, the legacy-line
  refusal); bullet 1 lands with ST5.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-17T01:04:53Z] `python-dev` Elias Python:
  - Done: format_comment edit mark, header grammar group, replace_comments by line span, legacy_header_lines (src/squads/_discussion.py); tests/unit/test_comment_splice_by_line_span.py (242 rows).
  - Falsified (new tests red): second edit appends a mark 2; indented lines count as legacy 2; replacement ignores the header line ending 55; removal keeps the comment trailing blank lines 64.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Make comment a group that routes a hash to show, edit and remove

<!-- sq:subtask:ST3:body -->
**Goal.** `comment` becomes a group whose callback keeps today's append, and whose first bare
positional token routes to a hidden address subgroup carrying `show`, `edit` and `remove`, at item
and sub-entity level. ADR-1013 §3.

**Approach**

- In `_cli/_items.py` (item level and `_register_sub_verbs`), make `comment` a group with
  `invoke_without_command=True` and the existing `-m`, `--file`, `--as` options; route the first
  positional token through the same `_click_resolve_command` override `AddressDispatchGroup` uses
  to a hidden subgroup whose callback takes `HASH`. Build it once as a helper in `_cli/_common.py`,
  so ST10 registers the same group on roster entities.
- Exit codes and messages per FEAT-1017 US1: bare `comment <hash>` and `comment "some text"` exit 2
  with `missing verb after <token>: show|edit|remove`; a non-hex or short token is refused as not a
  comment hash and says a new comment takes `-m` or `--file`; `comment -m x <hash> edit` is refused
  with "-m, --file and --as go after the verb" and appends nothing.
- `comment --help` describes both forms; `comments` and `comments --json` are unchanged here.
- The verbs' bodies arrive in ST4 to ST6; this subtask wires them to stubs that ST4 replaces, so the
  grammar lands tested on its own.

**Tests**

- Parse table, item and sub-entity levels by shape: `-m`, repeated `-m`, `--file`, `--file -`, no
  arguments, `-m a1b2 -m edit` (two bullets), a hex-looking message via `--file`, bare `<hash>`,
  bare text, short token, non-hex token, `-m x <hash> edit`. Each cell: bare exit code, message,
  file hash (changed only on append).

**Falsify.** Let the callback read a positional as a message: the hex-message rows go red. Return
exit 1 for a bare hash: those rows go red. Restore each.

**Acceptance**

- FEAT-1017 US1, all bullets, at item and sub-entity level (roster level is ST10).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-17T01:30:08Z] `python-dev` Elias Python:
  - Done: CommentGroup and register_comment_group (src/squads/_cli/_common.py) at item, sub-entity and roster level; tests/cli/test_comment_group_grammar.py (30 rows, parse table x item/sub-entity).
  - Falsified (new tests red): bare hash exits 1 instead of 2: 4; options before the verb allowed: 4.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Show one comment, with a --json record

<!-- sq:subtask:ST4:body -->
**Goal.** `comment <hash> show [--json]` renders one comment with its context line, or one JSON
record. ADR-1013 §3 (`show`).

**Approach**

- Render through the pane `comments` uses (styled on a TTY; plain `--- ... ---` when piped or with
  `--raw`), preceded by the context line (`TASK-5`, or `TASK-5 · subtask ST2`). The header carries
  the short hash, display name with slug, timestamp, and `(edited <ts>)` when edited.
- `--json`: exactly the keys of one `comments --json` entry (`author`, `author_slug`, `ts`,
  `edited_ts`, `hash`, `short_hash`, `body`) plus `item`, `scope` (`null` or `<kind>:<local_id>`)
  and `copies` (member count of a duplicate group; the first member is rendered). Build it from the
  same builder ST9 extends, never a second dict literal.
- No `--as`. Refusals reuse ST1's resolver messages.

**Tests**

- Key-set table at item and sub-entity level: exact key equality (not a superset), `scope` value,
  `copies` 1 and 2; valid JSON with `FORCE_COLOR` set.
- Render table: TTY, piped, `--raw`; edited and unedited.

**Falsify.** Add one extra key to the record: the exact-key assertion goes red. Render the context
line without the sub-entity part: its row goes red. Restore each.

**Acceptance**

- FEAT-1017 US3, all bullets, at item and sub-entity level.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-17T01:30:09Z] `python-dev` Elias Python:
  - Done: show and show --json; comment_json/comments_json extended with edited_ts, hash, short_hash (one builder for every surface); tests/cli/test_comment_show_by_hash.py. Goldens comments, task_show, feature_show, subtask_st1_show regenerated: only the three keys added.
  - Falsified (new tests red): extra key in the record: 2; context line without the sub-entity part: 2.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Edit a comment by its author, keeping header and position

<!-- sq:subtask:ST5:body -->
**Goal.** `comment <hash> edit --as <slug> (-m ... | --file ...)` replaces the comment's bullets, by
its author only, keeping its header and position and adding the edit mark. ADR-1013 §4, §9.

**Approach**

- An edit core in `_services/_collab.py` beside `_comment_core`, under the lock and inside
  `_section_edit_core`: resolve the hash (ST1), run the legacy-line check (ST2), `reject_markers`
  on every new message, the author match on the slug (`--as operator` matches legacy anonymous
  comments; a `squads` entry never matches; a retired author is refused until reactivated), then
  splice through ST2's pure function and `sections.replace_section`.
- Input follows `comment`'s contract (repeated `-m` gives one bullet each, `--file` one bullet,
  mutually exclusive, `--file -` reads stdin, empty file refused, neither refused naming both).
- Unchanged canonical text: keep the hash, write nothing, add no mark, and say so. An edit that
  would equal another comment in its scope is refused.
- Output: `edited <hash> on <ID> (<slug>, <ts>); now <hash>`, the new hash computed from the lines
  as written; `--json` emits the new entry in the `comments --json` shape.

**Tests**

- The task body's position-by-shape table through the service and the CLI: every other line
  byte-identical, header timestamp/slug/name preserved, mark present.
- Refusal table: wrong author, retired author, `squads` entry, legacy line, live marker in the
  message, stale hash after an edit, edit equal to another comment. Each: bare exit 1, message,
  file hash unchanged, no reflog line.
- Printed hash equals a fresh load's; the no-op edit writes nothing.

**Falsify.** Match on the display name instead of the slug: the renamed-author row goes red. Skip
`reject_markers` on edit: the marker row goes red. Write on a no-op edit: its file-hash assertion
goes red. Restore each.

**Acceptance**

- FEAT-1017 US4, all bullets, and US8 bullet 1 (`reject_markers` on edit).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-17T01:30:11Z] `python-dev` Elias Python:
  - Done: Service.edit_comment/find_comment, edit verb; tests/service/test_comment_edit_by_hash.py (position x shape x level x preamble, refusals), tests/cli/test_comment_edit_and_remove_by_hash.py. Written through sections.replace_section.
  - Falsified (new tests red): match display name as well as slug 1; skip reject_markers 1; write on a no-op edit 2; skip the legacy-line check 1.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Remove a comment by its author, with confirmation

<!-- sq:subtask:ST6:body -->
**Goal.** `comment <hash> remove --as <slug> [--yes]` hard-deletes the comment, by its author only,
after a confirmation. ADR-1013 §5, §9.

**Approach**

- A remove core beside ST5's, sharing its resolve, legacy-line check and author match (one helper,
  same error shape). Removes the header line and every line to the next header or the region's
  close marker through ST2's pure function. No tombstone; an emptied region keeps its markers.
- Without `--yes`, confirm, showing author, timestamp and first line of each comment to be removed
  (a duplicate group lists every member). Declining exits non-zero and writes nothing.
- Prints what it removed; `--json` emits the removed entries in the `comments --json` shape.

**Tests**

- The position-by-shape table: every other line byte-identical, including a preamble; no blank-line
  residue beyond the original layout.
- Refusal and prompt table: wrong author, retired author, `squads` entry, decline at the prompt,
  `--yes`, a second `remove` with the same hash (no match).

**Falsify.** Leave a blank line where the comment was: the residue assertion goes red. Skip the
author match on remove: the wrong-author row goes red. Restore each.

**Acceptance**

- FEAT-1017 US5, all bullets.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-17T01:30:12Z] `python-dev` Elias Python:
  - Done: Service.remove_comment, remove verb with prompt/--yes/--json; tests/service/test_comment_remove_by_hash.py, CLI rows in the shared CLI module.
  - Falsified (new tests red): skip the author match in the removal core 2; skip the confirmation 1. Dropping the preflight author check alone stays green by design (the core re-checks under the lock).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Refuse duplicate comments on write, merge or remove them together

<!-- sq:subtask:ST7:body -->
**Goal.** Duplicate comments (same scope, same hash) are refused on write, tolerated on load, merged
on edit and removed together. ADR-1013 §6.

**Approach**

- In `_comment_core`, under the lock and before writing, refuse a comment whose hash already exists
  in the target scope: `<ID> already has this comment by <slug> at <ts> (<hash>)`. The bulk importer
  reaches the same check through its comment op; the refusal aborts the import transaction like any
  other refusal (in the single-write apply loop TASK-992 leaves).
- Load: members listed in file order with the same hash; `sq check` does not report them.
- Edit (ST5): the first member keeps position and header and takes the text and mark; the others
  are removed; one author match covers the group. Remove (ST6): every member goes, and the prompt
  lists them all. `copies` in `show --json` (ST4) counts them.

**Tests**

- Groups built by hand-written file content. Table: write identical (refused), two texts in one
  second (both accepted), identical text in two scopes (both accepted, distinct hashes), load (both
  listed), `sq check` (clean), edit (merged), remove (all gone), import of a duplicate (whole
  import refused, nothing written).

**Falsify.** Check only the item scope on write: the sub-entity duplicate row goes red. Keep the
second member on edit: the merge row goes red. Restore each.

**Acceptance**

- FEAT-1017 US6, all bullets.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-17T01:44:15Z] `python-dev` Elias Python:
  - Done: duplicate refusal in _comment_core (so the importer reaches it under its single write), group merge on edit, group removal, copies in show --json; tests/service/test_duplicate_comments.py plus one CLI row.
  - Falsified (new tests red): no duplicate check 3; check skipped for sub-entity discussions 1; second member kept on edit 1.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Record comment edits and removals in the reflog

<!-- sq:subtask:ST8:body -->
**Goal.** `comment_edit` and `comment_remove` join the closed reflog op vocabulary, one delta entry
per comment touched. ADR-1013 §10.

**Approach**

- `_index/_reflog.py`: add both ops to `REFLOG_OPS`. Delta entries `{author, hash (full, before),
  region, ts, before}`, `comment_edit` adds `after_hash`; `before` follows the gone-item snapshot
  item removal uses.
- A merged group on edit and a group removal record one entry per member. A no-op edit and every
  refusal write no reflog line.

**Tests**

- One test per op asserting op and delta fields; a group row each; a no-op and a refusal row
  asserting no line; the closed-vocabulary test lists both ops.

**Falsify.** Log a no-op edit: its row goes red. Drop `after_hash`: the edit row goes red. Restore
each.

**Acceptance**

- FEAT-1017 US7, all bullets.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-17T01:44:16Z] `python-dev` Elias Python:
  - Done: comment_edit and comment_remove in REFLOG_OPS, one line per change with a comments delta (author, hash, region, ts, before; after_hash on edit); tests/service/test_comment_reflog.py.
  - Falsified (new tests red): log a no-op edit 1; drop after_hash 1.
  - Note: tests/meta/test_reflog_op_vocabulary_has_one_source.py fails until docs/workflow.md op table gains both rows (ST13, docs are not mine).
- [2026-10-17T01:44:22Z] `python-dev` Elias Python:
  - Correction: dropping after_hash turns 3 tests red, not 1.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Put the hash in every render, JSON payload, search and inbox hit

<!-- sq:subtask:ST9:body -->
**Goal.** The hash appears in every render, JSON payload and hit. ADR-1013 §11.

**Approach**

- `comments --json` and every `discussion` entry of `show --json` (item and sub-entity) gain `hash`,
  `short_hash` (ST1's scope-unique form) and `edited_ts`, from one builder.
- Search and inbox hits landing in a comment gain that comment's `hash`; the locator token is
  unchanged.
- Every human render puts the short hash first in each header: `comments`, `show --comments`
  (styled, plain, `--raw`), sub-entity `show` (its own scope's hashes), the TUI reader, and
  `comment <hash> show`; an edited comment shows `(edited <ts>)`.
- The inbox mechanism is unchanged: a mention added by an edit appears, a removed one disappears,
  no re-notification.
- Regenerate every CLI golden that pins a comment header or a JSON entry; the expected diff is the
  new first token and the three keys, confirmed line by line in the handoff.

**Tests**

- Keys table by surface (comments, show item, show sub-entity, search hit, inbox hit): exact key
  sets.
- First-token render table by surface and mode; a hit's hash resolves to its comment through the
  address.

**Falsify.** Compute `short_hash` per item instead of per scope: the collision row goes red. Omit
the hash from the TUI reader: its row goes red. Restore each.

**Acceptance**

- FEAT-1017 US9, all bullets except the VS Code client (ST12).
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
- [2026-10-17T01:49:13Z] `python-dev` Elias Python:
  - Done: hash, short_hash and edited_ts on every JSON entry; hash first in the plain, raw, styled, sub-entity and TUI renders; hash on search hits and "hashes" on inbox; hits map to comments through split_discussion on the one line rule. Goldens regenerated (comments, task_show, feature_show, subtask_st1_show, inbox_manager, search_login, item_show_raw): only the new keys and the new first token changed.
  - Falsified (new tests red): TUI reader without the hash 1; short hash length wrong 13; search hit without hash 2; raw render without hash 1; line scan back on str.splitlines 1 (U+2028 row).
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Register the comment address verbs on skills, roles and operators

<!-- sq:subtask:ST10:body -->
**Goal.** `sq skill|role|operator <addr> comment <hash> show|edit|remove` work with the item rules,
in the empty scope, on system skills and roles too. ADR-1013 §3 (roster types).

**Approach**

- Register ST3's `comment` group helper on the roster `_addr` groups, replacing TASK-1070's append-
  only `comment` registration while keeping its behaviour for `-m`, `--file` and `comments`.
- No TASK-1069 gate call: a comment is not generated content.
- Role addressing keeps `_require_id`.

**Tests**

- The address-by-level table's roster rows: each verb on a project skill, a system skill, a project
  role, a system role and an operator, with the parse shapes of ST3 (bare `<hash>` exits 2 here
  too).
- TASK-1070's roster comment tests stay green unchanged.

**Falsify.** Route roster `edit` through the gate: the system skill and system role rows go red.
Use the item scope string on a roster entity: the hash-equality row goes red. Restore each.

**Acceptance**

- FEAT-1017 US10, all bullets.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
- [2026-10-17T01:49:14Z] `python-dev` Elias Python:
  - Done: the roster _addr groups already register the shared comment group; tests/cli/test_roster_comment_verbs_by_hash_cli.py runs show/edit/remove over every roster shape (system skill and role included, no gate) and the grammar refusals; TASK-1070 roster tests unchanged and green.
  - Falsified (new tests red): gate edit/removal on skills 4; item scope string on a roster entity 13.
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Teach the address verbs in bundled guidance and the managed CLAUDE.md region

<!-- sq:subtask:ST11:body -->
**Goal.** Bundled guidance teaches `comment <hash> show|edit|remove` and the read-again rule, and the
managed `CLAUDE.md` region stops calling the discussion append-only. ADR-1013 Consequences and "The
append-only statement".

**Approach**

- The comment lines in `workflow.md.j2`, `views/squads_skill.md.j2`, `claude/claude_section.md.j2`,
  `agents_md/agents_section.md.j2`, `agents/operator.md.j2`, `views/role_definition.md.j2` and
  `_specs/playbook.toml` gain the address verbs and the rule to read again after a refusal. The
  squads skill says a quoted hash pins the text the author read.
- The orchestration-loop step 5 line ("the discussion is an append-only log") is changed in
  `templates/claude/claude_section.md.j2`, never in the rendered `CLAUDE.md`.
- Regenerate the template manifest and the managed-section golden; `sq sync` on a scratch squad
  renders a matching region. This repository's `CLAUDE.md` follows at the operator's next sync.
- No text calls the author match a permission.

**Tests**

- Rendered-golden assertions on the squads skill, the managed section and the AGENTS.md section;
  the manifest freshness test; fresh init against migrate-then-sync with the roster held constant.

**Falsify.** Leave the manifest stale: the freshness test goes red. Edit the rendered `CLAUDE.md`
only: the managed-section golden goes red. Restore each.

**Acceptance**

- FEAT-1017 US11 bullets 1 and 2.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
- [2026-10-17T01:59:01Z] `python-dev` Elias Python:
  - Done: address verbs, the read-again rule and "a quoted hash pins the text its author read" added to workflow.md.j2, views/squads_skill.md.j2, claude/claude_section.md.j2 (step 5 no longer says append-only), agents_md/agents_section.md.j2, agents/operator.md.j2, views/role_definition.md.j2 and the task entry of playbook.toml. Manifest regenerated, --check clean, seed_content_store --rebuild dropped 6 orphans, --release-gate passes. Goldens updated: managed sections, workflow cheatsheet (cooked and raw), migrated-corpus CLAUDE.md, skill_body_sq-task, playbook_spec. tests/cli/test_guidance_teaches_comment_hash_verbs.py pins the text.
  - Falsified (new tests red): stale manifest 7 of tests/meta; original claude_section template 10 (guidance, managed-section and migrated-corpus goldens).
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->

<!-- sq:subtask:ST12 -->
### ST12 — Show the comment hash and edit mark in the VS Code client

<!-- sq:subtask:ST12:body -->
**Goal.** The VS Code client reads and shows the comment hash and edit mark, and still accepts an
older sq that omits them. ADR-1013 §11.

**Approach**

- `SqDiscussionEntry` gains optional `hash` and `edited_ts`; the preview shows the short hash first
  in each comment header and the edit mark when present.
- An entry without the fields renders as today.
- The skew canary floor follows the new keys only where the client consumes them.

**Tests**

- Client unit tests: an entry with both fields, with neither, with `edited_ts` null.
- The skew canary against the dev-tree sq, resolved as the canary already does.

**Falsify.** Make `hash` required: the older-sq row goes red. Restore.

**Acceptance**

- FEAT-1017 US9 bullet on the VS Code client.
<!-- sq:subtask:ST12:body:end -->

#### Discussion

<!-- sq:subtask:ST12:discussion -->
<!-- sq:subtask:ST12:discussion:end -->
<!-- sq:subtask:ST12:end -->

<!-- sq:subtask:ST13 -->
### ST13 — Document hash addressing in the docs, CHANGELOG and CLAUDE.md conventions

<!-- sq:subtask:ST13:body -->
**Goal.** Adopter docs, the CHANGELOG and the hand-authored `CLAUDE.md` line describe hash
addressing and corrections by the author. ADR-1013 "Docs" and "The append-only statement".

**Approach (tech writer, from the ST11 handoff)**

- `docs/stability.md`: the extended Tier 1 header, Tier 3 `hash`, `short_hash`, `edited_ts`, the
  hash definition, and the two reflog ops in the op table.
- `docs/internals.md` comment-format line; the README command list; `docs/recipes.md` (inbox hits
  carry a hash); the unreleased CHANGELOG entry.
- The docs say the author match is not a permission and that a mention removed by an edit gives no
  notification.
- The hand-authored `CLAUDE.md` Conventions line ("No status/lifecycle prose in bodies") is
  reworded in place: the discussion is a timestamped history that only each comment's author can
  correct.
- Official-docs rule: no item ids, no build-process narration; present truth only.

**Acceptance**

- FEAT-1017 US11 bullets 3, 5 and 6.
- Every command shown was run in a scratch squad and its output matches.
- `rg -n -i "append-only" docs README.md CLAUDE.md` returns no passage calling the discussion
  append-only.
<!-- sq:subtask:ST13:body:end -->

#### Discussion

<!-- sq:subtask:ST13:discussion -->
<!-- sq:subtask:ST13:discussion:end -->
<!-- sq:subtask:ST13:end -->

<!-- sq:subtask:ST14 -->
### ST14 — Add the dated notes ADR-1013 owes to ADR-979 and ADR-981

<!-- sq:subtask:ST14:body -->
**Goal.** ADR-979 and ADR-981 carry the dated notes ADR-1013 owes them.

**Approach (architect)**

- ADR-979: a dated discussion note on the first sentence of its Context (discussions are no longer
  append-only) and one on its header section for the optional edit mark.
- ADR-981: a dated note on its "No denormalisation" bullet: the conclusion stands, because an edit
  keeps the name snapshot and never writes a pronoun into a header.
- Notes are discussion comments with a full ISO date; bodies are not edited.

**Acceptance**

- FEAT-1017 US11 bullet 4.
- `~/.local/bin/sq check` clean afterwards.
<!-- sq:subtask:ST14:body:end -->

#### Discussion

<!-- sq:subtask:ST14:discussion -->
- [2026-10-17T02:01:55Z] `architect` Robert Architect:
  - 2026-10-17: done. Dated notes posted as discussion comments, bodies untouched: ADR-979 (Context first sentence; §2 optional edit mark, replaced not stacked), ADR-981 (§1 No denormalisation: conclusion stands, an edit keeps the name snapshot and writes no pronoun), and ADR-1013 (implementation settlements: one CR/LF/CRLF split_lines rule incl. the 0.16 migration, the reflog {"comments": [...]} delta with after_hash on edit, the retired-author freeze in the service, the edit mark replaced on re-edit). @manager
<!-- sq:subtask:ST14:discussion:end -->
<!-- sq:subtask:ST14:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:15:59Z] `tech-lead` Olivia Lead:
  - Broken down into ST1-ST14. Depends on TASK-1070, TASK-992 (importer and write guard) and TASK-1078 (same roster CLI files); TASK-1071 now depends on this task (both change the comment header render). No migration, per ADR-1013. @manager ready for review of the plan.
- [2026-10-17T01:59:02Z] `python-dev` Elias Python:
  - Facts for ST12 (VS Code): every discussion entry in comments --json and in show --json (item and sub-entity) now has edited_ts (null or ts), hash (64 hex) and short_hash (scope-unique, at least 7). Human headers read "<short> [<ts>] Name (slug)" plus " (edited <ts>)". Search hits have "hash" (null outside a comment); inbox entries have "hashes" parallel to lines/regions.
  - Facts for ST13 (docs): header grammar gains an optional ", edited <ts>" before the slug; hash = SHA-256 over "sq-comment-1", item sequence number, scope ("" or kind:local_id), slug, header timestamp, canonical text (CR/LF/CRLF equal, trailing spaces and tabs stripped, outer blank lines dropped). Verbs: comment <hash> show [--json|--raw] | edit --as (-m|--file) [--json] | remove --as [--yes] [--json]; prefix of 4+ hex, case-insensitive, per discussion; stale hash refused; duplicates refused on write and import, tolerated on load, merged on edit, removed together; show --json adds item, scope, copies. Reflog: comment_edit and comment_remove, delta {"comments": [{author, hash, region, ts, before[, after_hash]}]}. docs/workflow.md op table needs both rows: tests/meta/test_reflog_op_vocabulary_has_one_source.py fails until it has them. Lines are broken at CR, LF, CRLF only (all readers). Author match is a guard against a slip, not a permission; a mention removed by an edit is not re-notified.
  - Facts for ST14 (architect): the edit keeps the display name snapshot; no pronoun is written into a header; no migration step changed except the 0.16 header migration now reads lines through the one CR/LF/CRLF rule (REV-1088 F3).
- [2026-10-17T02:01:36Z] `typescript-dev` Ada Typescript:
  - ST12 done. Preview comment header now shows the short hash first (full hash as tooltip) and an "(edited <ts>)" mark after the timestamp; entries without the keys render as before. Guard accepts hash, short_hash, edited_ts (null or string) as optional. Gates: tsc, eslint, prettier clean; vitest 715 passed; canary (pinned to the working-tree sq) 84 passed, with the discussion-entry keys now requiring the three new ones. Operator: in the dev host open a task preview with comments and check the hash, its tooltip and the edit mark on an edited comment.
- [2026-10-17T02:06:04Z] `tech-writer` Theo Writer:
  - ST13 docs written, not committed. Probed on a working-tree copy (2a16e94b plus the uncommitted changes). @manager
    
    - docs/workflow.md: `comment_edit` and `comment_remove` rows in the reflog op table (now eighteen). `tests/meta/test_reflog_op_vocabulary_has_one_source.py` passes (4 passed). New section "Addressing a comment by its hash": verbs, scope, author-only (a guard, not a permission), the edit mark, the stale-hash refusal, and inbox reading the current text with no notification.
    - docs/stability.md: the header grammar with `, edited <ts>`; a new "Comment hashes" section (definition, canonical text, short hash and prefix widening, scope, duplicates); both ops in the reflog table; the discussion entry keys (`edited_ts`, `hash`, `short_hash`), the `show --json` extras, search `hash` and inbox `hashes`.
    - Also internals.md, recipes.md, README. CHANGELOG: one Added entry; the earlier `author_slug` entry now gives the final key set.
    - Driven: show/edit/remove at item, sub-entity, role, skill and operator level; prefix case and length; the wrong-scope message; the author refusal; the new hash after an edit and the old one refused; a no-op edit; a second edit replacing the mark; remove with the prompt and --yes; the --json payloads; the reflog deltas; the duplicate refusal through import; inbox `hashes`; search `hash` (null outside a comment).
    - Not done here: the hand-authored CLAUDE.md conventions line is outside my brief (docs, README and CHANGELOG only), so it needs another owner. Found: `sq task N comment HASH show --help` still prints `Usage: sq task N comment HASH HASH show`, although F7 says the doubled hash was fixed.
<!-- sq:discussion:end -->
