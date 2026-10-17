---
id: ADR-1013
sequence_id: 1013
type: decision
title: Comments are edited and removed by short hash, by their author
status: Accepted
author: architect
refs:
- MILE-934:targets
- ADR-979
- FEAT-980
- ADR-981
- ADR-114
- FEAT-977
- ADR-1009
description: How comments are addressed by a derived short hash, edited and removed
  by their author only
created_at: '2026-10-15T19:31:21Z'
updated_at: '2026-10-17T02:01:33Z'
---
<!-- sq:body -->
## Context

Each claim is marked **read** (the source was read), **driven** (a command was run and its
output observed) or **inferred** (reasoned from read code, not exercised).

The operator's rulings of 2026-10-15 on this feature are, in order:

- MILE-934 at 2026-10-15T19:25:09Z;
- the amendment at 2026-10-15T19:31:40Z;
- this decision's discussion at 2026-10-15T19:54:29Z, at 2026-10-15T20:08:33Z (address
  grammar), and the later ruling on `show`.

Together they say:

- Comments can be edited and deleted, on every type.
- A comment is addressed by a short hash, the way git addresses a commit.
- The hash is computed on load over the item's sequence number, the author slug, the timestamp
  as written, and the comment text. It is never stored.
- Renders show the short form, and `--json` carries the full hash. Any unique prefix addresses a
  comment.
- An edit gives the comment a new hash, which the edit verb prints. A stale hash is refused.
- Two comments with the same author, the same second and the same text share a hash, which is
  always a mistake:
  - a write that would produce an existing hash is refused;
  - on load the duplicate is tolerated silently;
  - an edit merges the duplicates into one comment carrying the new text;
  - a delete removes all of them.
- Timestamps stay whole seconds. No millisecond fraction is added, and no existing comment is
  migrated.
- The verbs follow sq's address grammar:
  `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove`.
  - `show` takes the usual `--json`.
  - There are no `edit-comment` or `remove-comment` verbs.
- `--as` stays required. If it does not match the comment's original author, the CLI raises.

That ruling is not reopened here. This decision settles how it is built.

**The comment format** (read, `_discussion.py`). `format_comment` writes a header line at column
0, then one `  - ` bullet per message, with continuation lines indented four spaces, so no line
an author writes can sit at column 0. `split_discussion` parses a region into `Comment` records,
and any text before the first header is dropped from the parse (driven, a direct call on a region
with a stray preamble line).

ADR-979 replaces the header with ``- [<ts>] `<slug>` <name>:`` and one shared column-0 pattern.
FEAT-980 builds that, and it is not built yet: the tree still carries the legacy
`- [<ts>] <name>:` pattern (read). Timestamps are whole seconds: `clock.now()` drops
microseconds, and `clock.iso` writes `YYYY-MM-DDTHH:MM:SSZ` (read, `_clock.py`).

**No duplicate exists in this corpus** (driven). A scan of every discussion header in this squad
found 3,812 headers:

- 15 groups share an item, an author and a second. Most are per-finding closures written in one
  burst. TASK-328 ST4 holds four comments across two seconds.
- 0 groups also share the text, under the canonicalisation of §1.

The scan was checked against a known positive: a synthetic file with two identical comments and
one different one, where it reported one group. So none of the 15 same-second groups collides,
and the merge rule never fuses distinct comments that exist today.

**Writes** (read, `_services/_collab.py`, `_services/_base.py`, `_sections.py`). The only
comment writer is `CollabMixin._comment_core`. It runs `reject_markers` on every message. Then
`_section_edit_core` re-reads the item file inside `IndexStore.transaction()`, under the file
lock, and appends through `sections.append_to_section`. The reflog line is `op: "comment"`,
`delta: {"author": <slug>}`, with no content (read, `.reflog.jsonl` tail). The reflog is
gitignored and advisory (read, `.gitignore`, `docs/stability.md`).

**Verbs today** (driven, `--help` on a task and on a subtask).

- The item level has `comment` (`-m` repeatable, or `--file`, mutually exclusive, from TASK-826)
  and `comments` (read-back, `--json`, from TASK-625).
- The sub-entity level has `comment` only.
- Removal verbs are named `remove`. They confirm with `typer.confirm(..., abort=True)` unless
  `--yes` is given (read).
- FEAT-977 gives skills, roles and operators `comment` and `comments` through their address
  dispatch groups (read).

**Other facts** (read):

- **No threading.** A grep of `src/squads` for reply, replies and in_reply finds nothing outside
  bundled greeting prose.
- **The inbox keeps no state.** `CollabMixin.inbox` re-scans the current text of open items for
  `@slug` on every call.
- **`--as` is unauthenticated.** A write accepts only a live roster or operator slug, plus the
  unvalidated legacy `operator` sentinel (`require_as`, `resolve_slug_or_raise`).
- **Removal precedent** (ADR-114). Removal is a hard delete with no tombstone in the corpus. The
  reflog line's delta carries a snapshot of what was removed.

## Decision

### 1. The hash

**Inputs.** The hash takes five inputs:

- **The item's sequence number.** "The item" is the sequence number, not the formatted id. A
  retype changes the prefix (`TASK-5` becomes `BUG-5`), which would otherwise change every hash
  on the item. The sequence number is the item's identity in the index.
- **The scope.** This is the empty string for the item's own discussion, and `<kind>:<local_id>`
  for a sub-entity's discussion (`finding:F2`). It is the tag that the region's discussion marker
  already carries.
- **The header's author slug.**
- **The header's timestamp string, exactly as written.**
- **The canonical text.**

The edit mark (§4) and the display name are never inputs.

**Why the scope is an input.** Without it, the same author, second and text in two scopes would
share one hash. That case is plausible: a reviewer closing F1 and F2 in one burst with the same
"Fixed in a1b2c3d." line. Today the duplicate rule would refuse the second write, and an edit
would merge comments that live in different discussions. Scoped addressing (§2) would then also
need a group that spans scopes. With the scope in the hash, a duplicate means the same comment
twice in the same discussion. That is the ruling's meaning.

No such pair exists in this corpus. The four-input scan below counted 0 groups at item level, and
item level includes every scope (driven). So adding the scope changes no answer today. It only
prevents a refusal that would be wrong.

**Cost of the scope.** If a spec renames a sub-entity kind, or its local-id prefix, the hashes in
that kind's discussions change. Hashes are derived and never stored, so only a hash someone quoted
goes stale. That is the same effect as an edit.

**Canonical text.** It is built from the comment's stored lines: every line after its header, up
to the next header or the region's close marker.

1. Line endings are normalised to LF: CRLF and lone CR become LF. A checkout with `autocrlf` must
   not change a hash.
2. Trailing whitespace (spaces and tabs) is stripped from every line. Editors strip it silently.
3. Leading and trailing blank lines are dropped. The blank lines between comments are layout, not
   text.
4. Everything else is kept byte for byte: the bullet markers (`  - `), the indentation of
   continuation lines, and inner blank lines, which a fenced block needs. The text is the stored
   markdown, not a re-rendering, so two comments that render alike but are stored differently
   hash differently.
5. There is no Unicode normalisation. Any byte change beyond steps 1 to 3 makes a different text.
6. The lines are joined with LF, with no trailing LF.

A comment with no bullet lines has the empty string as its text.

**Serialisation and function.**

- The bytes hashed are the UTF-8 encoding of
  `"sq-comment-1" NUL <sequence number in decimal> NUL <scope> NUL <slug> NUL <timestamp> NUL <canonical text>`.
- None of the first five fields can contain NUL. The text comes last, so a NUL inside it cannot
  shift a field boundary.
- The leading tag versions the set of inputs.
- The function is SHA-256 as lowercase hex: 64 characters, carried in full by `--json` as `hash`.
  It is an address, not a security property.

**Never stored.** `split_discussion` computes the hash while parsing, and `Comment` gains
`hash: str`. The hash is never written to the `.md` file or to the index.

**Roster entities** are items with a sequence number and one discussion. Their scope is always the
empty string.

**Legacy headers.** The hash needs the slug, and a header written before FEAT-980 has only a
display name. ADR-979 §4 rules out a dual-read parser, so FEAT-980 must come first, which is
already the build order. The schema gate keeps a 0.16 build off a 0.15 squad until the migration
runs (read, ADR-979 §4). §8 covers a stray legacy line.

### 2. Scope, short form, prefixes and stale hashes

- **An address resolves only within its scope.**
  - `sq <type> <n> comment <hash> ...` matches only the item's own discussion.
  - `sq <type> <n> <kind> <k> comment <hash> ...` matches only that sub-entity's discussion.
  - Prefix length, uniqueness and ambiguity are all judged within the scope.
- **Wrong scope is refused.** If a prefix matches nothing in its scope but matches in another
  scope of the same item, the command refuses and names where the comment lives:
  `no comment a1b2c3d in TASK-5's discussion; it is in subtask ST2 (sq task 5 subtask 2 comment a1b2c3d ...)`.
  The command never acts on a comment outside the scope it was given.
- **Short form.** Renders show the first **7** hex characters. When two distinct hashes in one
  scope share those 7, every hash in that scope is shown at the shortest length that makes them
  unique, as git does.
- **Prefixes.** An address is a hex prefix of at least **4** characters, matched
  case-insensitively against the scope's current hashes.
  - A token that is not 4 or more hex characters is refused as not a comment hash. The message
    says that a new comment takes `-m` or `--file`.
  - An ambiguous prefix, one that matches two or more distinct hashes, is refused. The message
    lists each candidate's short hash, author and timestamp.
  - A duplicate group (§6) is a single hash, so it is never ambiguous.
- **No match is refused:**
  `no comment a1b2c3d in TASK-5's discussion (edited or removed since it was read?)`.
- **The stale-hash refusal is the concurrency protection.** A caller holds a hash from its last
  read.
  - If another session edits that comment, the text changes and so does the hash. If another
    session removes it, it is gone. Either way the old hash no longer resolves, the call is
    refused, and the caller must read again.
  - Appends, and edits of other comments, leave the hash valid. The target is still exactly the
    comment that was read.
  - No `--expect-*` guard is needed.
- **The one residual: a short prefix can land on a different comment's new hash.**
  - A 7-hex prefix has about a 1 in 2^28 chance per comment in the scope, and a 4-hex prefix
    about 1 in 65,536.
  - The author match narrows the risk further.
  - Scripts pass the full hash from `--json`. Typed 7-character prefixes are fine for people.

### 3. Verb grammar

The verbs follow sq's address grammar, by the operator's ruling of 2026-10-15T20:08:33Z:

```
sq <type> <n> comment -m <msg> ... --as <slug>                 # append (unchanged)
sq <type> <n> comment --file <path> --as <slug>                # append (unchanged)
sq <type> <n> comment <hash> show [--json]
sq <type> <n> comment <hash> edit --as <slug> (-m <msg> ... | --file <path>)
sq <type> <n> comment <hash> remove --as <slug> [--yes]
sq <type> <n> comments [--json]                                # list (unchanged)

sq <type> <n> <kind> <k> comment -m ... | --file ...  --as <slug>
sq <type> <n> <kind> <k> comment <hash> show|edit|remove ...

sq skill|role|operator <addr> comment -m ... | --file ...  --as <slug>
sq skill|role|operator <addr> comment <hash> show|edit|remove ...
```

**How `comment` parses** (driven: a scratch Typer probe built on the same mechanism as
`AddressDispatchGroup`, run through `CliRunner`).

- `comment` becomes a group with `invoke_without_command=True`. Its callback keeps today's append
  options (`-m`, `--file`, `--as`).
- An `_click_resolve_command` override, the one `AddressDispatchGroup` uses for
  `sq role <addr>`, routes the first positional token to a hidden `_addr` subgroup. That
  subgroup's callback takes `HASH` and carries `show`, `edit` and `remove`.
- Results from the probe:
  - `comment -m x --as a` and `comment --file - --as a` append, exactly as now.
  - `comment --as a -m a1b2 -m edit` appends two bullets, `a1b2` and `edit`.
  - `comment a1b2c3d edit -m new --as a`, `comment a1b2c3d remove --as a --yes` and
    `comment a1b2c3d show` reach their verbs.
  - `comment` with no arguments keeps today's "provide -m or --file" error.

**A message is never mistaken for a hash.** A message only reaches sq as the value of `-m`, or
through `--file`, and the parser consumes an option's value before it looks for a positional.
Only a bare positional token is read as an address. The verb names `show`, `edit` and `remove`
contain non-hex letters, so a verb can never be mistaken for a hash either.

**A misplaced append is refused.** Options given before the hash belong to the append callback.
So `comment -m x a1b2 edit` is refused with "-m, --file and --as go after the verb", and nothing
is appended. The probe exercised this.

**A bare `comment <hash>` is refused, not defaulted to `show`.** This matches how addresses
behave today (driven):

- `sq task 826` and `sq task 826 subtask 1` with no verb both end in Click's "Missing command"
  usage error, exit 2.
- `sq role architect` with no verb exits 1 with a missing-verb message (read,
  `AddressDispatchGroup`).

A comment address follows the item and sub-entity form it sits under:

- **Error and exit code.** It exits 2 with
  `missing verb after a1b2c3d: show|edit|remove`.
- **Roster entities.** The exit code is also 2 under them, because the `comment` group is one
  implementation shared by every level.
- **Why not default to `show`.** Refusing also catches the likeliest slip, `comment "some text"`
  typed without `-m`. A default to `show` would turn that into a puzzling "no comment" lookup.
- **Probe.** It confirmed that the routing refuses before any verb runs: `comment a1b2c3d`,
  `comment cafe` and `comment "fix this"` all stopped at the missing-verb check. The probe's own
  exit code was 1, because it called `typer.Exit(1)`; the build uses the usage-error code.
- **A token that is not a hash.** In the build, such a token names the `-m` fix instead (§2).

**`comment <hash> show [--json]`** is the explicit read of one comment.

- **Rendered.** It shows one comment in the same pane as `comments` uses (styled on a TTY, and
  plain `--- … ---` when piped or with `--raw`).
  - The header line is the short hash, the display name with the slug, the timestamp, and the
    edit mark when there is one:
    `a1b2c3d · Robert Architect (architect) · 2026-10-15T10:00:00Z (edited 2026-10-15T11:20:05Z)`.
  - It is preceded by one context line naming where the comment lives: `TASK-5`, or
    `TASK-5 · subtask ST2`.
  - The body follows, as `comments` renders it.
- **JSON.** One object with exactly the keys of one `comments --json` entry (§11), plus three keys
  only a single comment needs:
  - `item`: the formatted id, `"TASK-5"`;
  - `scope`: `null` for the item's own discussion, or `"subtask:ST2"`, the same
    `<kind>:<local_id>` spelling as search and inbox locators;
  - `copies`: an integer, 1 for an ordinary comment, and the number of members for a duplicate
    group. `show` renders the first member, so a duplicate stays visible without being
    reported as an error.
- **Errors.** `show` takes no `--as`, because it is a read. An unresolvable, ambiguous or
  wrong-scope hash is refused exactly as for `edit` and `remove`.

**Which verbs exist where.**

- The sub-entity `comment` takes the same group shape inside `_register_sub_verbs`.
- On skills, roles and operators, FEAT-977's `comment` is built as the same group inside each
  `_addr` subgroup.
- FEAT-977 rules that comments are not content-changing, so `edit` and `remove` are allowed on
  system skills and roles.

**Edit input.** Edit takes `-m` and `--file` under exactly the `comment` contract
(`resolve_comment_messages`):

- repeated `-m` gives one bullet per message, and `--file` gives one bullet;
- the two are mutually exclusive, and `--file -` reads stdin;
- an empty file is refused, and giving neither is refused, naming both flags.

**Output.**

- `edit` prints the new hash, which is the next address:
  `edited a1b2c3d on TASK-5 (architect, 2026-10-15T10:00:00Z); now 9f8e7d6`.
- An edit whose canonical text is unchanged keeps the hash, writes nothing, and says so.
- `remove` prints what it removed.
- With `--json`, both verbs emit the affected entries in the `comments --json` shape: the new entry
  for an edit, and the old entries for a removal.

**Confirmation.** `remove` confirms, as item `remove` does, unless `--yes` is given. The prompt
shows the author, the timestamp and the first line of every comment it will remove. A duplicate
group means two or more.

**Help.** `comment --help` must describe both forms: append with `-m`/`--file`, or
`<hash> show|edit|remove`. The probe's default help showed only `COMMAND [ARGS]`, which does not
say that. The help text is a deliverable, under the help-surface rules of REV-958.

### 4. What an edit preserves

- **Preserved:**
  - the header's timestamp, slug and display-name snapshot (ADR-979 §3);
  - the comment's position.
- **Replaced:** every bullet. An edit replaces the whole comment, and bullets are not addressed
  one by one. `comments --json` `body` is rendered markdown, not valid `-m` input to feed back
  unchanged.
- **The edit mark is kept.** The header records the last edit time inside the brackets, before
  the slug:

  ```
  - [2026-10-15T10:00:00Z, edited 2026-10-15T11:20:05Z] `architect` Robert Architect:
  ```

  - The new hash does not replace the mark. A hash changes, but a reader cannot tell from it that
    an edit happened, or when.
  - The mark cannot be derived from the `.md` file, and the reflog is local and gitignored.
  - A reader who quoted a comment has to be able to see that it changed.
  - The mark goes before the slug, because the name is free text running to the final colon. A
    second edit replaces it.
  - The mark is not a hash input: it describes the edit, not the comment.
  - `--json` gains `edited_ts`, which is `null` when the comment was never edited. Renders show
    `(edited <ts>)`.
  - This extends ADR-979 §2's grammar by one optional group, and both ship in 0.16.

### 5. Removal

- A removal is a hard delete of the header line and every line up to the next header or the
  region's close marker. No tombstone is left in the file (ADR-114's line). An emptied region
  keeps its markers.
- There is no threading, so a removal never strands a reply.
- A hash quoted elsewhere in prose names a version of a comment. It stops resolving once that
  comment is edited or removed. The squads skill tells authors that a quoted hash pins the text
  they read.

### 6. Duplicates

A duplicate group is every comment in one scope with the same hash: the same author, the same
timestamp string and the same canonical text. In other words, the same comment written twice in
the same discussion.

- **On write.** `_comment_core` computes the new comment's hash under the lock, before writing,
  against every comment in the target scope. A match is refused:
  `TASK-5 already has this comment by architect at 2026-10-15T10:00:00Z (a1b2c3d)`.
  - The check covers `comment` at every level and the bulk importer, all of which go through
    `_comment_core`.
  - For the importer, the refusal aborts the import's transaction like any other refusal
    (inferred).
  - An edit that would make a comment equal to another in its scope is refused in the same way.
  - Two different comments in the same second hash differently, and both are accepted. So are
    identical comments in different scopes.
- **On load.** Tolerated silently. Each member is listed in order and carries the same hash.
  `sq check` does not report it, by ruling.
- **On edit.** The first member in file order keeps its position and header, and takes the new
  text and the edit mark. Every other member is removed. All members share the slug, so one
  author match covers the whole group.
- **On delete.** Every member is removed, and the confirmation lists them all.
- **In this corpus there are none** (driven, Context). Neither rule touches any comment that
  exists today.

### 7. Marker-safe splice

- Every new message passes `reject_markers` before any write, as in `_comment_core`.
- `_discussion` gains one pure function that takes a region and returns it with the given comments
  replaced or removed.
  - It works on each comment's exact **line span**, never by re-rendering the parsed list. So
    preamble text and every other comment stay byte-identical.
  - A duplicate group lies within one scope, so a call touches exactly one region.
  - The service writes that region through `sections.replace_section`, inside
    `_section_edit_core`.
  - Invariant 3 holds.
- The edited header and bullets come from `format_comment`, extended for the edit mark. They are
  never assembled at the call site.
- The new hash is computed from the lines as written, so the verb prints what a fresh load
  computes.

### 8. Legacy lines

A 0.16 build meets a slug-less header only after a hand edit or a merge from a 0.15 branch
(inferred, §1).

- Such a line does not match the pattern, so the parser folds it into the comment before it, as
  text. That comment's hash then covers the stray line (inferred, from `split_discussion`'s
  accumulation rule).
- Editing or removing that comment would take the legacy text with it.
- So both verbs refuse when any discussion region of the item holds a column-0 line that starts
  with `- [` but does not match the grammar. This is the "looks like a header" test of the
  migration's third failure kind.
- The error names the file and the line. Nothing is written.

### 9. Author match

- `--as` resolves as it does for `comment`, and must equal the header's slug. Otherwise the
  command exits 1:
  `a1b2c3d on TASK-5 was written by architect; --as qa cannot edit it`.
- The match is on the slug, never the name (ADR-979 §3).
- System entries (`squads`) cannot be matched by any `--as`, so they are immutable.
- A retired author's comments are frozen until that author is reactivated, because a write takes
  only a live slug.
- `--as operator` matches the legacy anonymous comments.
- The slug reuse after `rm --purge` that ADR-979 accepted extends to editing.
- `--as` is unauthenticated. The match stops mistakes but does not control access, and the docs
  must not call it a permission.

### 10. Reflog

- Two new ops join the closed `REFLOG_OPS` vocabulary: `comment_edit` and `comment_remove`.
- Each delta holds one entry per comment touched:
  `{"author": <slug>, "hash": <full, before>, "region": <tag>, "ts": <ts>, "before": <body>}`.
  - `comment_edit` adds `"after_hash"`.
  - `before` follows ADR-114's gone-item snapshot.
- `docs/stability.md`'s op table gains both rows. The field set is unchanged.

### 11. Mentions, inbox, search, JSON and renders

- **Mentions and inbox.** Nothing extra is built. The inbox is a live scan, so a mention added by
  an edit appears, and a removed one disappears silently, with no re-notification. The docs say
  so.
- **JSON.** All of the following is additive under Tier 3.
  - Every `comments --json` entry, and every `discussion` entry in `show --json` (item and
    sub-entity), gains four keys:
    - `hash`: 64 hex characters, the address;
    - `short_hash`: the rendered form, at its scope-unique length;
    - `edited_ts`: `null` when the comment was never edited.
    - With FEAT-980's `author_slug`, an entry is then
      `{author, author_slug, ts, edited_ts, hash, short_hash, body}`.
  - `comment <hash> show --json` returns that entry plus `item`, `scope` and `copies` (§3).
  - `edit --json` and `remove --json` return entries in the same shape.
  - Search and inbox hits that land in a comment gain that comment's `hash`. Their locator token
    (`subtask:ST2:discussion#1`) already names the scope, so a hit carries everything needed to
    build the address `sq task 5 subtask 2 comment <hash> ...`. The token itself is unchanged.
- **Renders.** Every human render puts the short hash first in each comment header, because that
  is the token a reader types after `comment`. This covers `comments`, `show --comments` (styled,
  plain and `--raw`), sub-entity `show`, the TUI reader, and `comment <hash> show`. A sub-entity
  pane shows the hashes of its own scope, which is the scope its address resolves in.
- **VS Code** (TASK-464). `SqDiscussionEntry` gains optional `hash` and `edited_ts`, and the
  preview shows the short hash and the edit mark. Both stay optional, because an older sq omits
  them.

## Consequences

- **Code.**
  - `_discussion`: `Comment.hash`, `Comment.edited_ts`, the text canonicalisation, the pattern's
    edit-mark group, `format_comment`, the line-span splice, and the legacy-line check.
  - `_services/_collab.py`: the duplicate check in `_comment_core`, plus the edit and remove
    cores.
  - `_cli/_items.py` (item level and `_register_sub_verbs`) and the roster `_addr` groups: `comment` becomes the group of §3, with `show`, `edit` and `remove`.
  - `_index/_reflog.py`: the two ops.
  - The JSON builders and the renders.
- **Schema.** `hash` is derived. The header grammar gains one optional part, the edit mark,
  alongside ADR-979's grammar in 0.16. Nothing is migrated, and the 0.16 migration step is
  untouched.
- **Tests.**
  - **Canonicalisation, table-driven:**
    - CRLF against LF;
    - trailing spaces and tabs;
    - leading and trailing blank lines;
    - inner blank lines in a fenced block;
    - a NUL in the text.

    Each must produce the hash the rules say. A pinned vector (fixed inputs, fixed expected hex)
    guards the serialisation.
  - **Position and shape, table-driven:**
    - first, middle and last comment, and the only comment;
    - a region with a preamble;
    - sub-entity and roster regions;
    - multi-line and fenced bodies.

    Every other line must stay byte-identical after an edit or a removal.
  - **Hash behaviour:**
    - the hash stays stable across a retype;
    - an edit changes it, and the verb prints the value a reload computes;
    - a stale hash is refused after an edit and after a removal from another session;
    - an edit to the same text is a no-op.
  - **Prefix resolution:** unique, ambiguous, too short, unknown, and a wrong-scope refusal that names the right address.
  - **Parsing:**
    - `comment -m`, `comment --file` and `comment` with no arguments behave as before;
    - a bare `comment <hash>` exits 2;
    - `comment -m x <hash> edit` is refused with nothing appended;
    - a message that looks like hex is never taken as an address;
    - `show` renders, and its `--json` record has the keys of §3 at every level.
  - **Duplicates:**
    - refused on write and on edit;
    - two different texts in the same second both accepted;
    - a group merged on edit;
    - an identical comment in two scopes accepted, each with its own hash;
    - a group removed together.
  - **Refusals:**
    - a wrong author;
    - a retired author;
    - a `squads` entry;
    - a legacy-shaped line;
    - a marker in the new text.
- **Bundled guidance.** The comment lines in these files gain `comment <hash> show|edit|remove` and the "read again
  after a refusal" rule:
  - `workflow.md.j2`;
  - `views/squads_skill.md.j2`;
  - `claude/claude_section.md.j2`;
  - `agents_md/agents_section.md.j2`;
  - `agents/operator.md.j2`;
  - `views/role_definition.md.j2`;
  - `_specs/playbook.toml`.

  (Read, from a grep for comment examples.) These are bundled files, so this work comes after the
  0.16.0 bump.
- **Docs** (tech writer):
  - `docs/stability.md`: the extended Tier 1 header, the Tier 3 `hash` and `edited_ts`, the hash
    definition, and the two reflog ops;
  - `docs/internals.md`: the comment-format line, around line 288;
  - the README command list, around line 299;
  - `docs/recipes.md`: inbox hits carry a hash.
- **Out of scope:**
  - per-bullet addressing;
  - import events that edit or remove;
  - access control beyond the author match.

## The append-only statement: dated notes owed

The discussion stops being append-only. What those lines rely on still holds: a dated comment
records state at a point in time, only its author can change it, and it keeps its timestamp. The
wording does not.

- **CLAUDE.md line 160** (Conventions, "No status/lifecycle prose in bodies") says "the discussion
  is an append-only history". The line is hand-authored, so it is reworded in place: the
  discussion is a timestamped history that only each comment's author can correct.
- **CLAUDE.md line 340** (the managed region, orchestration loop step 5) says "the discussion is
  an append-only log".
  - It is changed in `templates/claude/claude_section.md.j2` line 116, and the managed-section
    golden is regenerated. The rendered file is never edited.
  - `agents_md/agents_section.md.j2` has no such line (driven, grep).
- **ADR-979** gets dated notes in two places:
  - the first sentence of its Context: "Discussion comments are append-only history: there is no
    verb that edits or deletes one";
  - §2, for the optional edit mark.
- **ADR-981 §1**, the "No denormalisation" bullet: "Discussion text is append-only history". It
  gets a dated note: the conclusion stands, because an edit keeps the name snapshot and never
  writes a pronoun into a header.
- ADR-114, ADR-117, ADR-295, ADR-314 and ADR-663 use "append-only" of the reflog or the board, not
  of discussions, and are unaffected (read). ADR-263's use sits in a discussion comment, which is
  exempt.

## Build order

The 0.16 main stream as of 2026-10-15:

1. TASK-954
2. ADR-1009
3. FEAT-980
4. the 0.16.0 bump
5. the ADR-1007 flattening
6. TASK-989
7. TASK-990
8. FEAT-976
9. FEAT-977
10. FEAT-961 and FEAT-966

This work goes **after FEAT-977 and before FEAT-961**:

- it needs FEAT-980's slug header, because the hash takes the slug;
- it changes bundled guidance, so it comes after the bump;
- FEAT-977 creates the roster comment verbs it extends.

It adds nothing to FEAT-980 and touches neither the schema nor the migration runner. It has no
feature or task yet.

## Alternatives

- **Positional index (`#n`)**, from the ruling of 2026-10-15T19:25:09Z. Rejected by the
  amendment of 2026-10-15T19:31:40Z. An index shifts when an earlier comment is deleted, so it
  can point at another comment between a read and a write. The guards drafted for it
  (`--expect-digest`, `--expect-ts`) went with it.
- **A hash over fixed fields only (item, slug, timestamp), with millisecond timestamps.**
  Rejected by the ruling of 2026-10-15T19:54:29Z.
  - Without the text, two distinct comments by one author in one second collide, and the corpus
    holds 15 such groups. Avoiding that needed millisecond headers and a migration that renumbered
    the existing collisions.
  - With the text in the hash:
    - only a true duplicate collides;
    - timestamps stay whole seconds;
    - nothing is migrated;
    - the stale-hash refusal protects against concurrent edits for free.
- **The formatted id as the item input.** Rejected: a retype would change every hash on the item.
- **One hash namespace per item, with no scope input**, from the previous draft. Rejected after the
  grammar ruling of 2026-10-15T20:08:33Z, which scopes each address to its discussion. With no
  scope in the hash, identical comments in two scopes would collide, and a duplicate group could
  span scopes that no single address can reach (§1).
- **Sibling verbs `edit-comment` and `remove-comment`.** Rejected by the ruling of
  2026-10-15T20:08:33Z, in favour of the address grammar.
- **A bare `comment <hash>` defaulting to `show`.** Rejected (§3): bare item and sub-entity
  addresses are refused today, and the refusal catches a forgotten `-m`.
- **Dropping the edit mark, since the hash already changes.** Rejected (§4). A hash change shows
  neither that an edit happened nor when.
- **A stored comment id.** Rejected by the ruling: the hash is never stored.
- **A tombstone on removal.** Rejected, following ADR-114.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T19:31:52Z] Robert Architect:
  - 2026-10-15: drafted from the op-pierre ruling on MILE-934 (2026-10-15T19:25:09Z). @manager, the points that need the operator's call:
    
    1. **Concurrency guard (the risk section).** An index read before another actor removes an earlier comment points one further, and the author match does not catch it when both comments share an author. That is the common case: an agent cleaning up its own comments. Recommended: an optional `--expect-digest` flag, with a derived `digest` key in the JSON, checked under the lock. Alternative: `--expect-ts`, which is readable by humans but cannot separate two comments from one author in the same second (driven). Accept A, B, both, or neither.
    2. **Edit mark.** The header keeps its original timestamp and gains `, edited <ts>` inside the brackets. That extends ADR-979's Tier 1 grammar by one optional group, with no migration impact. The `--json` output gains `edited_ts`.
    3. **Verb names.** `edit-comment` and `remove-comment` are siblings of `comment` at item, sub-entity and roster level, and the sub-entity level gains a `comments` read verb. `remove-comment` takes several indexes, resolved against one load, so a caller removing several comments does not hit shifted indexes.
    4. **Frozen comments.** System entries (`squads`) and the comments of retired authors become uneditable, because `--as` takes only a live slug.
    
    Settled without needing a ruling:
    - Indexes are 1-based and equal to search's existing `discussion#<n>`. Each sub-entity discussion has its own numbering.
    - Edits and removals work on the whole comment only. There is no threading.
    - A region holding a legacy-shaped header line is refused.
    - Two reflog ops record each change, with a snapshot of the previous text (the ADR-114 pattern).
    - The inbox follows edits on its own, because it is a live scan.
    - `reject_markers` runs on every new message.
    
    Build order: after FEAT-977, before FEAT-961. There is no feature or task yet.
    
    Dated notes owed once this decision is accepted (I have not edited them):
    - CLAUDE.md lines 160 and 340. Line 340 is changed through `claude_section.md.j2` line 116.
    - ADR-979, in its Context and §2.
    - ADR-981 §1.
- [2026-10-15T19:35:27Z] Robert Architect:
  - 2026-10-15: the body has been redone for the operator's amendment of 2026-10-15T19:31:40Z, which addresses comments by short hash. My comment above is superseded: the positional index and the concurrency guard (`--expect-digest`, `--expect-ts`) are gone and are recorded under Alternatives. @manager, these points need the operator's call:
    
    1. **Whole seconds break the duplicate premise (driven).** This squad has 3,789 comment headers. In 15 groups, two or more distinct comments share an item, an author and a second. 12 of those groups are per-finding closures written in one burst. In 3 groups the comments sit in the same region; TASK-328 ST4, for example, has four different comments across two seconds. Under the merge rule, editing one of them destroys another. Proposed:
       - New headers carry milliseconds (`...:00.123Z`). This is an optional fraction in ADR-979's grammar, and only the header reads it.
       - The 0.16 migration gives each existing collision `.000`, `.001` and so on, in file order, with the bullets kept byte-identical.
       
       Both pieces belong in FEAT-980. FEAT-980 is next but one in the stream, so this needs a ruling before it starts.
    2. **"The item" means the sequence number**, not the formatted id. A retype would otherwise change every hash on the item.
    3. **The hash is scoped to the whole item.** Sub-entity regions are not an input, so `sq <type> <n> edit-comment <hash>` and `remove-comment <hash>` reach any comment on the item, and no sub-entity-level verbs are needed.
    
    Settled without needing a ruling:
    - SHA-256 over `sq-comment-1 NUL seq NUL slug NUL ts`.
    - The short form is 7 hex characters, widened per item when needed. A prefix must be at least 4 characters, and an ambiguous one is refused with the candidates listed.
    - The hash needs the slug, so FEAT-980 comes first, which is already the order.
    - An edit keeps the timestamp and adds `, edited <ts>` to the header.
    - `reject_markers` runs on every new message.
    - Two reflog ops record each change, with a snapshot of the previous text.
    - The inbox follows edits on its own, because it is a live scan.
    
    Build order for the verbs is unchanged: after FEAT-977, before FEAT-961. The dated notes owed (CLAUDE.md lines 160 and 340 via the template, ADR-979, ADR-981) are not written yet.
- [2026-10-15T19:54:29Z] Pierre Chat:
  - 2026-10-15: the comment hash covers the text too: item sequence number, author slug, timestamp as written, and the comment text. An edit gives the comment a new hash (printed by the edit verb), and a stale hash is refused. Duplicates are therefore same author, same second, same text. Timestamps stay whole seconds, and no millisecond fraction or migration of existing comments is needed.
- [2026-10-15T19:56:22Z] Robert Architect:
  - 2026-10-15: I revised the body to follow the op-pierre ruling of 2026-10-15T19:54:29Z. The comment text is now a hash input: `"sq-comment-1" NUL seq NUL slug NUL ts NUL text`. @manager, the changes:
    
    - **Canonical text** (§1). The text is the comment's stored lines after its header, normalised as follows:
      - CRLF and CR are converted to LF;
      - trailing spaces and tabs are stripped from each line;
      - leading and trailing blank lines are dropped;
      - bullet markers, indentation and inner blank lines are kept byte for byte;
      - there is no Unicode normalisation;
      - the lines are joined with LF, with no trailing newline.
    - **Edit and concurrency.** An edit prints the new hash. A stale hash, meaning one taken before the comment was edited or removed, does not resolve and is refused. That refusal is the concurrency protection, so the ADR has no guard flag. The remaining risk is that a 4-character prefix lands on a different comment's new hash. To avoid it, scripts pass the full hash from `--json`.
    - **Duplicates now mean the same author, the same second and the same text.** The four rules are reworded for that definition. An edit whose new text would duplicate another comment is refused. I re-ran the scan on 3,812 headers. Groups identical in all four inputs: **0**. The 15 same-second groups all differ in text. The scan reported one group on a synthetic known positive, so the zero is real.
    - **Dropped:** the millisecond fraction, the migration renumbering and the extra FEAT-980 pieces. The slug dependency stays. The "fixed fields plus milliseconds" option is recorded under Alternatives as rejected, citing this ruling.
    - **The edit mark is kept.** A changed hash does not show that an edit happened, or when.
    
    ADR status was not changed.
- [2026-10-15T20:08:33Z] Pierre Chat:
  - 2026-10-15: the verbs follow the sq address grammar: sq <type> <n> comment <hash> edit|remove, and on a sub-entity sq <type> <n> <kind> <k> comment <hash> edit|remove. No edit-comment / remove-comment verbs.
- [2026-10-15T20:09:44Z] Pierre Chat:
  - 2026-10-15: comment <hash> also takes show, with the usual --json flag: sq <type> <n> [<kind> <k>] comment <hash> show [--json].
- [2026-10-15T20:11:45Z] Robert Architect:
  - 2026-10-15: I revised the body for the address-grammar ruling (2026-10-15T20:08:33Z) and the ruling that `comment <hash>` also takes `show`. @manager, the changes:
    
    - **Grammar.**
      - The form is `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove`, and the same on `sq skill|role|operator <addr>`.
      - `comment -m`, `comment --file` and `comments` are unchanged.
      - I drove a scratch Typer probe on the `AddressDispatchGroup` mechanism. It showed that `comment` can be a group whose callback keeps the append options, with a positional token routed to a hidden `_addr` group.
    - **Parsing.**
      - A message is never taken as a hash, because it only arrives as the value of `-m` or through `--file`.
      - The verb names contain non-hex letters, so a verb is never taken as a hash either.
      - `comment -m x <hash> edit` is refused, and nothing is appended.
    - **Bare `comment <hash>` is refused, not defaulted to `show`.**
      - Today `sq task 826` and `sq task 826 subtask 1` exit 2 with "Missing command" (driven), so a comment address follows them with exit 2.
      - The refusal also catches `comment "text"` typed without `-m`.
    - **`show`.**
      - It renders one comment in the same pane as `comments`: the short hash, name, slug, timestamp and edit mark, after a context line such as `TASK-5 · subtask ST2`.
      - Its `--json` is one `comments --json` entry plus `item`, `scope` (`null` or `subtask:ST2`) and `copies`.
      - List entries gain `hash`, `short_hash` and `edited_ts`.
    - **Scope.**
      - An address resolves only in its own discussion.
      - A hash from another scope is refused, and the message names the address where the comment lives.
      - **The scope is now a hash input:** `"sq-comment-1" NUL seq NUL scope NUL slug NUL ts NUL text`, where scope is empty or `kind:local_id`.
      - Without it, identical text from one author in the same second, such as "Fixed in a1b2c3d." posted to F1 and F2, would be refused as a duplicate, and a duplicate group could span scopes that no single address can reach.
      - The corpus has 0 such pairs (driven), so no answer changes today.
      - The cost: renaming a kind or its prefix changes that kind's hashes. That is acceptable, since hashes are never stored.
    - **Rejected:**
      - sibling verbs, citing the ruling;
      - one namespace per item;
      - a bare address defaulting to `show`.
    
    I did not change the ADR status.
- [2026-10-15T20:17:06Z] Pierre Chat:
  - 2026-10-15: accepted.
- [2026-10-17T02:01:33Z] Robert Architect:
  - 2026-10-17: where the build settled points this decision left open, from TASK-1079 ST14 (read in the tree; review evidence in REV-1088). Additions only; body and status untouched.
    - **One line rule.** §1 normalises CR, LF and CRLF for the hash but named no splitter. `sections.split_lines` breaks at CR, LF and CRLF only (never U+2028, form feed, VT or NEL, which `str.splitlines` also breaks at), and it is the one rule for the discussion layer, `region_lines`, the search and inbox region scan, and the 0.16 header migration (REV-1088 F3). The migration change altered nothing in this corpus (REV-1088, driven dry run); a separator inside a line no longer makes a header of the text after it.
    - **Reflog delta shape.** §10 gave the per-comment entry, not its container. The delta of `comment_edit` and `comment_remove` is `{"comments": [{"author", "hash", "region", "ts", "before"}, ...]}`, one entry per member of the group touched, with `hash` the full hash before the change, `region` the discussion marker tag, and `after_hash` added on each entry of an edit. The op rows go in both `docs/stability.md` (§10) and the `docs/workflow.md` op table, which `tests/meta/test_reflog_op_vocabulary_has_one_source.py` pins.
    - **The retired-author freeze lives in the service.** §9 states the author match and the freeze as one rule; both are enforced in `Service.edit_comment` and `remove_comment` (the live-author check next to the slug match), so a caller other than the CLI cannot edit or remove a retired author's comment (REV-1088 F6). The anonymous `operator` slug passes it; an unknown slug is refused.
    - **The edit mark is replaced, not stacked.** §4's "a second edit replaces it" holds as built: an edit re-renders the header through `format_comment` with the original timestamp, slug and name and one fresh `edited <ts>`, whatever mark was there before.
    - No migration step changed except the line rule above; the header migration writes no edit mark.
<!-- sq:discussion:end -->
