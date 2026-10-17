---
id: FEAT-1017
sequence_id: 1017
type: feature
title: Comments are shown, edited and removed by short hash
status: Done
author: product-owner
refs:
- ADR-1013:implements
- MILE-934:targets
- FEAT-980:depends-on
- FEAT-977:depends-on
description: 'Address a comment by derived short hash: comment <hash> show|edit|remove,
  by its author, on every type'
subentities:
- local_id: US1
  title: As an agent, I want a comment address grammar beside comment -m
  status: Todo
- local_id: US2
  title: As an agent, I want a short hash that addresses one comment
  status: Todo
- local_id: US3
  title: As a reader, I want to show one comment, with --json
  status: Todo
- local_id: US4
  title: As an author, I want to edit my own comment
  status: Todo
- local_id: US5
  title: As an author, I want to remove my own comment
  status: Todo
- local_id: US6
  title: As an agent, I want duplicate comments handled predictably
  status: Todo
- local_id: US7
  title: As an operator, I want edits and removals in the reflog
  status: Todo
- local_id: US8
  title: As an adopter, I want edits that keep markers and other lines intact
  status: Todo
- local_id: US9
  title: As a tool author, I want the hash in every render, JSON and hit
  status: Todo
- local_id: US10
  title: As an operator, I want the same verbs on skills, roles, operators
  status: Todo
- local_id: US11
  title: As an adopter, I want the docs, guidance and notes updated
  status: Todo
created_at: '2026-10-15T20:17:43Z'
updated_at: '2026-10-17T02:12:56Z'
---
<!-- sq:body -->
## Problem

A comment that is wrong, leaks something or was posted to the wrong item cannot be corrected: the discussion only grows, and a comment has no address, so nobody can point at one, read it back alone, fix it or take it down.

## Capability

Implements the accepted decision on comment addressing: a comment is shown, edited and removed by a short hash, only by its author, on every type. The decision is the spec; the stories below cite its numbered sections and add acceptance only.

## Scope

- The address grammar `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove` and the hash itself (decisions 1, 2, 3).
- `show`, `edit` and `remove`, with the author match, the edit mark and the duplicate rules (decisions 3 to 6, 9).
- Marker-safe line-span splices and the two reflog ops (decisions 7, 8, 10).
- The hash in every render, in `comments --json`, in `show --json`, in search and in inbox hits, plus the VS Code client fields (decision 11).
- Roster types: skills, roles and operators (decision 3).
- Documentation, bundled guidance and the dated notes the decision lists.

## Out of scope

Per-bullet addressing. Import events that edit or remove. Access control beyond the author match: `--as` is unauthenticated, and no text may call the match a permission. A tombstone on removal. A stored comment id. Any migration of existing comments, and any millisecond timestamp.

## Sequencing

Needs the slug header (the hash takes the slug) and the roster comment verbs (this work extends them), and changes bundled guidance, so it comes after the 0.16.0 bump. Order in the release: after the verb parity feature, before the pronouns and invocability features. It adds nothing to the schema or the migration runner; the edit mark extends the header grammar by one optional group, shipped in the same release as the slug header. Editing and removing a comment on a system skill or role is allowed: a comment is not generated content, so the refusal on content-changing verbs does not apply (rulings on the origin feature).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1017 add-story "As a <role>, I want … so that …"`; track with `sq feature 1017 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent, I want a comment address grammar beside comment -m

<!-- sq:story:US1:body -->
Acceptance (decision 3):
- `comment` is a group whose callback keeps today's append options. `comment -m`, `comment --file`, `comment --file -` and repeated `-m` behave exactly as before, and `comment` with no arguments keeps the "provide -m or --file" error.
- The first bare positional token routes to a hidden address subgroup carrying `show`, `edit` and `remove`; the same group shape exists at item level, in the sub-entity verb registration (`sq <type> <n> <kind> <k> comment <hash> ...`) and under each roster address group.
- A message is never taken as an address: `comment --as a -m a1b2 -m edit` appends two bullets (`a1b2` and `edit`); a message that looks like hex, given through `-m` or `--file`, appends.
- A bare `comment <hash>` and `comment "some text"` exit 2 with `missing verb after <token>: show|edit|remove`; the same exit code at item, sub-entity and roster level; nothing is written.
- A token that is not 4 or more hex characters is refused as not a comment hash, and the message says a new comment takes `-m` or `--file`.
- `comment -m x <hash> edit` is refused with "-m, --file and --as go after the verb", and nothing is appended.
- `comment --help` describes both forms: append with `-m`/`--file`, and `<hash> show|edit|remove`; the help surface follows the project's help-surface rules.
- There are no `edit-comment` or `remove-comment` verbs. `comments` and `comments --json` are unchanged apart from the keys in the render story.
- Tests are table-driven over item, sub-entity and roster levels, and over the shapes above.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent, I want a short hash that addresses one comment

<!-- sq:story:US2:body -->
Acceptance (decisions 1, 2):
- `Comment.hash` is computed by the discussion parser and is never written to a `.md` file or the index.
- The bytes hashed are the UTF-8 encoding of `"sq-comment-1" NUL <sequence number> NUL <scope> NUL <slug> NUL <timestamp as written> NUL <canonical text>`; the function is SHA-256 as 64 lowercase hex characters. The sequence number, not the formatted id, is the item input, so a retype leaves every hash on the item unchanged. The scope is empty for the item's own discussion and `<kind>:<local_id>` for a sub-entity's; roster entities always use the empty scope. The edit mark and the display name are never inputs.
- Canonical text: CRLF and lone CR become LF; trailing spaces and tabs are stripped from every line; leading and trailing blank lines are dropped; bullet markers, continuation indentation and inner blank lines are kept byte for byte; no Unicode normalisation; lines joined with LF, no trailing LF; a comment with no bullet lines hashes the empty string.
- A table-driven test covers CRLF against LF, trailing spaces and tabs, leading and trailing blank lines, inner blank lines in a fenced block, and a NUL in the text, each producing the hash the rules say. A pinned vector (fixed inputs, fixed expected hex) guards the serialisation.
- An address resolves only within its scope. A hex prefix of at least 4 characters is matched case-insensitively against that scope's current hashes.
- Renders show the first 7 hex characters; when two distinct hashes in one scope share those 7, every hash in that scope is shown at the shortest length that makes them unique.
- An ambiguous prefix is refused, listing each candidate's short hash, author and timestamp. A prefix matching nothing is refused: `no comment <hash> in <ID>'s discussion (edited or removed since it was read?)`.
- A prefix that matches nothing in its scope but matches in another scope of the same item is refused and names the address where the comment lives; the command never acts outside the scope it was given.
- A stale hash is refused: after an edit of that comment, and after its removal from another session. An append, or an edit of another comment, leaves the hash valid.
- Tests cover unique, ambiguous, too-short, unknown and wrong-scope prefixes, case-insensitivity, and a hash stable across a retype.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a reader, I want to show one comment, with --json

<!-- sq:story:US3:body -->
Acceptance (decision 3, `show`):
- `sq <type> <n> [<kind> <k>] comment <hash> show` renders one comment in the pane `comments` uses (styled on a TTY; plain `--- ... ---` when piped or with `--raw`).
- A context line precedes it: `TASK-5`, or `TASK-5 · subtask ST2`. The header line carries the short hash, the display name with the slug, the timestamp and, when edited, `(edited <ts>)`. The body follows as `comments` renders it.
- `show` takes no `--as`.
- `--json` returns one object with exactly the keys of one `comments --json` entry (`author`, `author_slug`, `ts`, `edited_ts`, `hash`, `short_hash`, `body`) plus `item` (the formatted id), `scope` (`null` for the item's own discussion, otherwise `<kind>:<local_id>` such as `subtask:ST2`) and `copies` (1 for an ordinary comment, the member count for a duplicate group; the first member is rendered).
- An unresolvable, ambiguous or wrong-scope hash is refused exactly as for `edit` and `remove`.
- Tests assert the record's keys at item, sub-entity and roster level, and `--json` stays valid JSON under the harness colour setting.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an author, I want to edit my own comment

<!-- sq:story:US4:body -->
Acceptance (decisions 3, 4, 9):
- `comment <hash> edit --as <slug> (-m <msg> ... | --file <path>)` replaces every bullet of the comment. Input follows `comment`'s contract: repeated `-m` gives one bullet per message, `--file` gives one bullet, the two are mutually exclusive, `--file -` reads stdin, an empty file is refused, and giving neither is refused naming both flags.
- The author match is on the slug, never the name. `--as` not equal to the header's slug exits 1: `<hash> on <ID> was written by <slug>; --as <other> cannot edit it`. `--as operator` matches the legacy anonymous comments.
- A `squads` entry cannot be edited by any `--as`. A retired author's comment is refused until that author is reactivated.
- The header's timestamp, slug, display-name snapshot and the comment's position are preserved. The header records the last edit inside the brackets, before the slug, ``- [<ts>, edited <ts>] `<slug>` <name>:``; a second edit replaces the mark; the mark is not a hash input.
- The edit prints the new hash, equal to the value a fresh load computes: `edited <hash> on <ID> (<slug>, <ts>); now <hash>`. With `--json` it emits the new entry in the `comments --json` shape.
- An edit whose canonical text is unchanged keeps the hash, writes nothing, adds no edit mark and says so.
- An edit that would make the comment equal to another comment in its scope is refused.
- Tests, table-driven over position and shape: first, middle, last and only comment; a region with a preamble; sub-entity and roster regions; multi-line and fenced bodies. Every other line of the file stays byte-identical. Further tests: wrong author, retired author, `squads` entry, hash printed equals reload, stale hash refused after an edit.
- Docs and guidance never call the author match a permission.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an author, I want to remove my own comment

<!-- sq:story:US5:body -->
Acceptance (decisions 5, 9):
- `comment <hash> remove --as <slug> [--yes]` hard-deletes the header line and every line up to the next header or the region's close marker. No tombstone is left. An emptied region keeps its markers.
- The author match, `squads` immutability and retired-author refusal are the same as for `edit`, with the same error shape.
- Without `--yes` it confirms; the prompt shows the author, the timestamp and the first line of every comment it will remove. A duplicate group lists two or more. Declining exits non-zero and writes nothing.
- It prints what it removed. With `--json` it emits the removed entries in the `comments --json` shape.
- A removed comment's hash stops resolving; a second `remove` with the same hash is refused as no match.
- Tests, table-driven over position and shape as for `edit`: every other line stays byte-identical, including a preamble, and the removal leaves no blank-line residue beyond the layout the file already had.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an agent, I want duplicate comments handled predictably

<!-- sq:story:US6:body -->
Acceptance (decision 6):
- A duplicate group is every comment in one scope with the same hash: same author, same timestamp string, same canonical text.
- On write: the check runs in `_comment_core` under the lock before writing, against every comment in the target scope, and refuses with `<ID> already has this comment by <slug> at <ts> (<hash>)`. It covers `comment` at every level and the bulk importer; for the importer the refusal aborts the import's transaction like any other refusal.
- On write: two different texts in the same second are both accepted; an identical comment in two scopes is accepted and each gets its own hash.
- On load: a group is tolerated silently. Each member is listed in file order and carries the same hash. `sq check` does not report it.
- On edit: the first member in file order keeps its position and header and takes the new text and the edit mark; every other member is removed. One author match covers the group.
- On remove: every member is removed, and the confirmation lists them all.
- An edit that would equal another comment in its scope is refused.
- Tests build a group by hand-written file content, then assert each rule above, including `copies` in `show --json`.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — As an operator, I want edits and removals in the reflog

<!-- sq:story:US7:body -->
Acceptance (decision 10):
- `comment_edit` and `comment_remove` join the closed reflog op vocabulary.
- Each delta holds one entry per comment touched: `{author, hash (full, before), region, ts, before}`; `comment_edit` adds `after_hash`. `before` follows the gone-item snapshot used by item removal.
- A merged duplicate group on edit and a group removal each record one entry per member.
- A no-op edit and every refusal write no reflog line.
- A test per op asserts the line's op and delta fields, and a test asserts the closed vocabulary lists both.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — As an adopter, I want edits that keep markers and other lines intact

<!-- sq:story:US8:body -->
Acceptance (decisions 7, 8):
- Every new message passes `reject_markers` before any write, on `edit` as on `comment`; a message containing a live marker tag is refused and nothing is written.
- One pure function in the discussion module takes a region and returns it with given comments replaced or removed, working on each comment's exact line span and never by re-rendering the parsed list. The service writes the region through the section replace inside the existing section-edit transaction, so the markdown is written before the index commit.
- The edited header and bullets come from `format_comment`, extended for the edit mark, and are never assembled at a call site.
- Preamble text and every other comment stay byte-identical after an edit or removal.
- `edit` and `remove` refuse when any discussion region of the item holds a column-0 line starting with `- [` that does not match the header grammar; the error names the file and the line and nothing is written.
- Tests cover the marker refusal, the legacy-shaped line refusal, a region with a preamble, and the integrity gate (`sq check` and `sq repair` clean after each verb).
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — As a tool author, I want the hash in every render, JSON and hit

<!-- sq:story:US9:body -->
Acceptance (decision 11):
- Every `comments --json` entry, and every `discussion` entry in `show --json` at item and sub-entity level, gains `hash` (64 hex), `short_hash` (the scope-unique rendered form) and `edited_ts` (`null` when never edited), alongside `author` and `author_slug`.
- Search and inbox hits that land in a comment gain that comment's `hash`; the locator token (`subtask:ST2:discussion#1`) is unchanged and is enough to build the address.
- Every human render puts the short hash first in each comment header: `comments`, `show --comments` (styled, plain and `--raw`), sub-entity `show`, the TUI reader and `comment <hash> show`. A sub-entity pane shows the hashes of its own scope. An edited comment shows `(edited <ts>)`.
- The inbox is unchanged in mechanism: a mention added by an edit appears, a removed one disappears silently, with no re-notification.
- The VS Code `SqDiscussionEntry` gains optional `hash` and `edited_ts`; the preview shows the short hash and the edit mark; an older sq that omits them is still accepted.
- Tests assert the keys and the first-token render at every level, and that the hash in a hit resolves to its comment through the address.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — As an operator, I want the same verbs on skills, roles, operators

<!-- sq:story:US10:body -->
Acceptance (decision 3, roster types):
- `sq skill|role|operator <addr> comment <hash> show|edit|remove` work, with the same grammar, scope (the empty scope), hash, author match, duplicate and reflog rules as items.
- `comment -m`, `comment --file` and `comments` on those types keep the behaviour the verb parity feature gave them.
- `edit` and `remove` are allowed on system skills and roles, since a comment is not generated content; the content-changing refusal does not apply.
- The shared group means the bare `comment <hash>` exit code is 2 here too.
- Tests run each verb on a skill, a role and an operator, including a system skill and a system role.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->

<!-- sq:story:US11 -->
### US11 — As an adopter, I want the docs, guidance and notes updated

<!-- sq:story:US11:body -->
Acceptance (Consequences, "Bundled guidance", "Docs", "The append-only statement"; authored by the tech writer, the guidance and notes by their owners):
- Bundled guidance: the comment lines in `workflow.md.j2`, `views/squads_skill.md.j2`, `claude/claude_section.md.j2`, `agents_md/agents_section.md.j2`, `agents/operator.md.j2`, `views/role_definition.md.j2` and `_specs/playbook.toml` gain `comment <hash> show|edit|remove` and the rule to read again after a refusal. The squads skill tells authors that a quoted hash pins the text they read.
- The CLAUDE.md managed-region line "the discussion is an append-only log" (orchestration loop, step 5) is changed in `templates/claude/claude_section.md.j2`, never in the rendered CLAUDE.md; the managed-section golden and the template manifest are regenerated and `sq sync` leaves the rendered file matching.
- The hand-authored CLAUDE.md line in the Conventions list ("No status/lifecycle prose in bodies") that calls the discussion an append-only history is reworded in place: the discussion is a timestamped history that only each comment's author can correct.
- ADR-979 gets dated notes on the first sentence of its Context (discussions are no longer append-only) and on its header section for the optional edit mark. ADR-981 gets a dated note on its "No denormalisation" bullet: the conclusion stands, because an edit keeps the name snapshot and never writes a pronoun into a header. Notes are discussion comments dated with a full ISO date.
- `docs/stability.md`: the extended Tier 1 header, Tier 3 `hash`, `short_hash` and `edited_ts`, the hash definition, the two reflog ops in the op table; `docs/internals.md` comment-format line; the README command list; `docs/recipes.md` (inbox hits carry a hash); the unreleased CHANGELOG section. The docs say the author match is not a permission and that a mention removed by an edit gives no notification.
- Adopter-facing text carries no item IDs and no build-process narration.
<!-- sq:story:US11:body:end -->

#### Discussion

<!-- sq:story:US11:discussion -->
<!-- sq:story:US11:discussion:end -->
<!-- sq:story:US11:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:19:07Z] Nina Product:
  - 2026-10-15: drafted from ADR-1013 and the operator's rulings of 2026-10-15. @manager, eleven stories cover the grammar, hash, show, edit, remove, duplicates, reflog, marker-safe splice, renders and JSON, roster types, and docs with the dated notes. Left in Draft; no tasks created. Build order: after the verb parity feature, before the pronouns feature.
- [2026-10-16T19:50:28Z] Nina Product:
  - 2026-10-16 readiness pass: added a problem statement; scope, out-of-scope and acceptance already follow ADR-1013 (Accepted) and its op-pierre rulings (hash inputs, address grammar, show --json). FEAT-980 is Done and FEAT-977 is Ready. System skills and roles allow edit/remove, consistent with FEAT-976 (comments are not content-changing). No open question. Moved to Ready.
<!-- sq:discussion:end -->
