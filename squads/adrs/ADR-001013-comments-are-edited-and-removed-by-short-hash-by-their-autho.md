---
id: ADR-1013
sequence_id: 1013
type: decision
title: Comments are edited and removed by short hash, by their author
status: Proposed
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
updated_at: '2026-10-15T19:35:27Z'
---
<!-- sq:body -->
## Context

Each claim is marked **read** (the source was read), **driven** (a command was run and its
output observed) or **inferred** (reasoned from read code, not exercised).

The operator ruled on 2026-10-15 (MILE-934, op-pierre, 2026-10-15T19:25:09Z), and amended the
ruling at 2026-10-15T19:31:40Z. Together:

- Comments can be edited and deleted, on every type.
- A comment is addressed by a short hash, as git addresses a commit. The hash is computed on
  load over what an edit cannot change (the item, the author slug and the timestamp), and it is
  never stored. Renders show the short form, `--json` carries the full hash, and any unique
  prefix addresses a comment.
- Two comments by the same author at the same time share a hash. That is always a mistake. A
  write that would produce an existing hash is refused. On load the duplicate is tolerated
  silently. An edit merges the two into one comment carrying the new text. A delete removes
  both.
- `--as` stays required. If it does not match the comment's original author, the CLI raises.

That ruling is not reopened here. This decision settles how it is built.

**The comment format** (read, `_discussion.py`). `format_comment` writes a header line at column
0, then one `  - ` bullet per message, with continuation lines indented four spaces, so no line
an author writes can sit at column 0. `split_discussion` parses a region into `Comment` records,
and any text before the first header is dropped from the parse (driven, a direct call on a region
with a stray preamble line). ADR-979 replaces the header with ``- [<ts>] `<slug>` <name>:`` and
one shared column-0 pattern. FEAT-980 builds that, and it is not built yet: the tree still
carries the legacy `- [<ts>] <name>:` pattern (read).

**Timestamps are whole seconds** (read, `_clock.py`). `clock.now()` drops microseconds, and
`clock.iso` writes `YYYY-MM-DDTHH:MM:SSZ`. A `--at` override and the bulk importer both rebind
that clock, the importer once per event (read, the `frozen_time` fixture and the `_clock`
docstrings).

**Same author, same second, same item happens today, and those comments are distinct**
(driven, a scan of every discussion header in this squad). Of 3,789 headers, 15 groups share an
item, an author and a second:

- 12 groups span sub-entity regions. Example: a reviewer closing findings F1 and F2 of REV-67 at
  2026-06-12T13:18:12Z, which is the per-finding comment convention of FEAT-62 doing its job.
- 3 groups sit in one region. Example: TASK-328 ST4 holds four comments from one developer
  across 2026-07-08T12:30:57Z and 2026-07-08T12:30:58Z, reporting ST1, ST2, ST3 and ST4 done.
  Each has different text.

So at whole-second precision the ruling's premise does not hold. Under the merge rule, editing
one of those four comments would destroy another. That is settled in §4 and §8 below.

**Writes** (read, `_services/_collab.py`, `_services/_base.py`, `_sections.py`). The only
comment writer is `CollabMixin._comment_core`. It runs `reject_markers` on every message, then
`_section_edit_core` re-reads the item file inside `IndexStore.transaction()`, under the file
lock, and appends through `sections.append_to_section`. The reflog line is `op: "comment"`,
`delta: {"author": <slug>}`, with no content (read, `.reflog.jsonl` tail). The reflog is
gitignored and advisory (read, `.gitignore`, `docs/stability.md`).

**Verbs today** (driven, `--help` on a task and on a subtask). The item level has `comment`
(`-m` repeatable, or `--file`, mutually exclusive, from TASK-826) and `comments` (read-back,
`--json`, from TASK-625). The sub-entity level has `comment` only. Removal verbs are named
`remove` and confirm with `typer.confirm(..., abort=True)` unless `--yes` is given (read). FEAT-977
gives skills, roles and operators `comment` and `comments`, through their address dispatch groups
(read).

**No threading** (read, a grep for reply, replies and in_reply in `src/squads`, with no hits
outside bundled greeting prose). **The inbox holds no state** (read, `CollabMixin.inbox`): it
re-scans the current text of open items for `@slug` on every call. **`--as` is unauthenticated**
(read, `require_as`, `resolve_slug_or_raise`). A write accepts only a live roster or operator
slug, plus the unvalidated legacy `operator` sentinel.

**Removal precedent** (read, ADR-114): a hard delete, with no tombstone in the corpus, and a
reflog line whose delta carries a snapshot of what went.

## Decision

### 1. The hash

- **Inputs.** The item's **sequence number**, the header's author slug, and the header's
  timestamp string exactly as written. "The item" is read as the sequence number, not the
  formatted id: a retype changes the prefix (`TASK-5` becomes `BUG-5`), and every hash on the
  item would otherwise change with it. The sequence number is the item's identity in the index.
  The edit mark (§4) and the text are never inputs.
- **Canonical serialisation.** The UTF-8 bytes of
  `"sq-comment-1" NUL <sequence number in decimal> NUL <slug> NUL <timestamp>`. None of the
  fields can contain NUL. The leading tag versions the input set, so a later change of inputs is
  explicit rather than silent.
- **Function.** SHA-256, as lowercase hex: 64 characters, carried in full by `--json` as `hash`.
  This is an address, not a security property.
- **Never stored.** `split_discussion` computes it while parsing. `Comment` gains `hash: str`.
  It is never written to the `.md` file or the index.
- **Scope: the whole item.** Sub-entity regions are not an input, so every comment on an item,
  top-level or in any sub-entity, sits in one namespace. One prefix resolves across the whole
  item. A comment never moves between regions, so adding the region would buy nothing, and leaving
  it out keeps the ruling's three inputs. Roster entities are items with a sequence number and work
  the same way.
- **Legacy headers need FEAT-980 first.** The hash needs the slug, and a pre-FEAT-980 header has
  only a display name. ADR-979 §4 rules out a dual-read parser, so there is no name-based fallback.
  The schema gate keeps a 0.16 build off a 0.15 squad until the migration runs (read, ADR-979 §4),
  so in practice every header carries a slug. §9 covers a stray legacy line.

### 2. Short form and prefixes

- Renders show the first **7** hex characters. When two distinct hashes on one item share those
  7, every hash on that item is shown at the shortest length that makes them unique, as git
  does. An item would need thousands of comments before that is likely (inferred, from the
  birthday bound on 28 bits).
- An address is a hex prefix of at least **4** characters, matched case-insensitively against
  the item's hashes. A shorter prefix is refused.
- No match: `SquadsError`, `no comment a1b2 on TASK-5`.
- An ambiguous prefix, one that matches two or more **distinct** hashes, is refused. The error
  lists each candidate's short hash, author and timestamp. A duplicate group (§7) is one hash, so
  it is never ambiguous.

### 3. Verb grammar

New sibling verbs, named verb-first like `add-<kind>`. `comment` and `comments` keep their form.

```
sq <type> <n> edit-comment <hash> --as <slug> (-m <msg> ... | --file <path>)
sq <type> <n> remove-comment <hash> --as <slug> [--yes]
```

- The hash names a comment anywhere on the item (§1), so there are no sub-entity-level forms.
  Sub-entity panes in `show --full --comments` and the sub-entity `show --json` carry the hash,
  so a sub-entity comment is found and then addressed from the item.
- The same two verbs exist on skills, roles and operators through FEAT-977's address groups
  (`sq skill <addr> edit-comment <hash> ...`). Under FEAT-977, comments are not content-changing,
  so the verbs are allowed on system skills and roles.
- **Edit takes `-m` and `--file`**, with exactly the `comment` contract
  (`resolve_comment_messages`). Repeated `-m` gives one bullet per message, and `--file` gives
  one bullet. The two are mutually exclusive, `--file -` reads stdin, an empty file is refused,
  and giving neither is refused naming both flags.
- `remove-comment` confirms, showing the author, the timestamp and the first line of each comment
  it will remove (two or more for a duplicate group), unless `--yes` is given. The confirmation
  works as item `remove`'s does.
- Both verbs print what they touched, for example
  `edited a1b2c3d on TASK-5 (architect, 2026-10-15T10:00:00.123Z)`. With `--json` they emit the
  affected entries in the `comments --json` shape. For a removal, those are the entries as they
  were before.

Rejected grammars: making `comment` a group (`comment <h> edit`), because `comment -m ...` is a
leaf today; making `comments` a group, which breaks the read verb; and flags on `comment`, which
put three operations with different required inputs behind one help text.

### 4. Timestamp precision

**Whole seconds are not intended.** At that precision the duplicate refusal fires on two quick
scripted comments, and the corpus shows such pairs are routine and distinct (Context).

- **New headers carry milliseconds:** `2026-10-15T10:00:00.123Z`. The header grammar's timestamp
  becomes `YYYY-MM-DDTHH:MM:SS[.fff]Z`. The shared pattern accepts the optional fraction, which
  extends ADR-979 §2. The header reads its own millisecond clock value. `clock.now()` keeps its
  whole-second truncation for every other field (inferred: that truncation is relied on elsewhere,
  so it is not changed globally).
- With a millisecond header, two `sq` processes cannot write the same author's comment in the same
  millisecond, because each write holds the squad lock (inferred). The refusal then fires only on
  a real duplicate:
  - a replayed write;
  - two `--at` invocations naming the same instant;
  - an import whose source holds two comments with the same author and timestamp on one item.
  
  An `--at` value or an imported timestamp is taken as given, so `.000` is appended when it has no
  fraction.
- Existing whole-second headers stay valid as written. The hash takes the literal timestamp
  string, so `12:30:57Z` and `12:30:57.000Z` are different inputs.

### 5. What an edit preserves

- **Preserved:** the header's timestamp, slug and display-name snapshot (ADR-979 §3), and so the
  hash. The comment keeps its position.
- **Replaced:** every bullet. An edit is a whole-comment replacement. Bullets are not
  individually addressable. `comments --json` `body` is rendered markdown, so it is not valid to
  feed back unchanged as `-m`.
- **Marked:** the header records the last edit time inside the brackets, before the slug:

  ```
  - [2026-10-15T10:00:00.123Z, edited 2026-10-15T11:20:05.456Z] `architect` Robert Architect:
  ```

  The mark goes before the slug because the name is free text running to the final colon. A
  second edit replaces the mark. The mark is not a hash input. `--json` gains `edited_ts`, which
  is `null` when the comment was never edited, and renders show `(edited <ts>)`.

### 6. Removal

A hard delete of the header line and every line up to the next header or the region's close
marker, with no tombstone in the file (ADR-114's line). An emptied region keeps its markers.
There is no threading, so a removal never strands a reply. Because hashes are stable, a hash
cited in prose elsewhere stays valid until that very comment is removed. The squads skill tells
authors to cite comments by short hash.

### 7. Duplicates

A duplicate group is every comment on the item with the same hash: the same author and the same
timestamp string.

- **On write.** `_comment_core` computes the new header's hash against every comment on the item,
  under the lock, before writing. A match is refused:
  `TASK-5 already has a comment by architect at 2026-10-15T10:00:00.123Z (a1b2c3d)`. The same
  check covers `comment`, the sub-entity `comment`, roster `comment` and the bulk importer,
  because they all go through `_comment_core`. For the importer this aborts the import's
  transaction like any other refusal (inferred).
- **On load.** Tolerated silently. Each member is listed in order and carries the same hash.
  `sq check` does not report it (by ruling).
- **On edit.** The first member in file order keeps its position and header, takes the new text
  and the edit mark. Every other member is removed. Every member has the same slug, so one author
  match covers the group.
- **On delete.** Every member is removed. The confirmation (§3) lists them all.
- **The existing collisions.** The 15 groups in this corpus (Context) are distinct comments that
  the ruling would merge or delete together. The 0.16 migration step, which already rewrites every
  header (ADR-979 §4), also separates them. Within each group, in file order, it gives the headers
  the fractions `.000`, `.001`, `.002` and so on. That keeps the order, keeps each timestamp
  inside its true second, and leaves the bullets byte-identical. This is a small addition to
  FEAT-980 US3, and it is the operator's call (Discussion). Without it, those comments merge on
  the first edit of any one of them.

### 8. Marker-safe splice

- Every new message passes `reject_markers` before any write, as in `_comment_core`.
- `_discussion` gains one pure function that takes a region and returns it with given comments
  replaced or removed. It works on each comment's exact **line span**, never by re-rendering the
  parsed list, so preamble text and every other comment stay byte-identical. The service writes
  each touched region through `sections.replace_section` inside `_section_edit_core`. A duplicate
  group can span regions, so one call may touch several regions of one file in one write.
  Invariant 3 holds.
- The edited header and bullets are produced by `format_comment`, extended for the edit mark and
  the millisecond timestamp, and never assembled at the call site.

### 9. Legacy lines

A 0.16 build meets a slug-less header only after a hand edit or a merge from a 0.15 branch
(inferred, §1). Such a line does not match the pattern, so the parser folds it into the comment
before it. Editing or removing that comment would take the legacy text with it (inferred, from
`split_discussion`'s accumulation rule). So both verbs refuse when any discussion region of the
item holds a column-0 line that starts with `- [` but does not match the grammar. This is the
"looks like a header" test of the migration's third failure kind. The error names the file and
line. Nothing is written.

### 10. Author match

- `--as` resolves as `comment` resolves it, and must equal the slug in the header. If it does
  not, the command exits 1 with
  `a1b2c3d on TASK-5 was written by architect; --as qa cannot edit it`.
- The match is on the slug, never the name (ADR-979 §3).
- System entries (`squads`) cannot be matched by any `--as`, so they are immutable.
- A retired author's comments are frozen until the author is reactivated, because a write takes
  only a live slug.
- `--as operator` matches legacy anonymous comments.
- The slug reuse after `rm --purge` that ADR-979 accepted extends to editing.
- `--as` is unauthenticated. The match stops mistakes. It does not control access, and docs must
  not call it a permission.

### 11. Reflog

- Two new ops in the closed `REFLOG_OPS` vocabulary: `comment_edit` and `comment_remove`.
- Each delta holds one entry per touched comment:
  `{"author": <slug>, "hash": <full>, "region": <tag>, "ts": <ts>, "before": <body>}`. `before`
  is the previous text, after ADR-114's gone-item snapshot.
- `docs/stability.md`'s op table gains both rows. The field set does not change.

### 12. Mentions, inbox, search, JSON and renders

- **Mentions and inbox.** Nothing extra is built. The inbox is a live scan, so a mention added by
  an edit appears and a removed one disappears silently. There is no re-notification. Docs say so.
- **JSON.** `hash` and `edited_ts` are added to every `comments --json` entry and every
  `discussion` entry in `show --json` (item and sub-entity). Search and inbox hits that land in a
  comment gain that comment's `hash`. Their `discussion#<n>` locator token is unchanged. All of this
  is additive under Tier 3.
- **Renders.** Human renders put the short hash first in each comment header: `comments`,
  `show --comments` (styled, plain and `--raw`), sub-entity `show`, and the TUI reader.
- **VS Code** (TASK-464). `SqDiscussionEntry` gains optional `hash` and `edited_ts`, and the
  preview shows the short hash and the edit mark. Both stay optional, because an older sq omits
  them.

### 13. Concurrency

A hash does not shift when another comment is removed, so the positional race goes away, and with
it any guard. The remaining case is two sessions of one author editing the same comment, which is
an ordinary last-write-wins under the lock. It is accepted.

## Consequences

- **Code.**
  - `_discussion`: `Comment.hash` and `Comment.edited_ts`; the pattern with the fraction and the
    edit mark; `format_comment`; the line-span splice; the legacy-line check.
  - `_clock`: a millisecond reading for headers.
  - `_services/_collab.py`: the duplicate check in `_comment_core`, plus edit and remove cores.
  - `_cli/_items.py` and the roster address groups: the two verbs.
  - `_index/_reflog.py`: two ops.
  - The JSON builders and the renders.
- **Schema.** `hash` is derived. The header grammar gains two optional parts, the fraction and the
  edit mark, and both ship in 0.16 beside ADR-979's grammar. The only migration work is §7's
  disambiguation, inside the existing 0.16 step.
- **Tests.**
  - Table-driven over position and shape: first, middle and last comment; the only comment; a
    region with a preamble; sub-entity and roster regions; multi-line and fenced bodies. Every
    other line must stay byte-identical after an edit or a removal.
  - Hash stability across an edit and a retype.
  - Prefix resolution: unique, ambiguous, too short, and unknown.
  - Duplicate groups: refused on write; merged on edit, within one region and across regions;
    removed together.
  - Refusals: a wrong author, a retired author, a `squads` entry, a legacy-shaped line, and a
    marker in the new text.
  - The migration's disambiguation of an existing collision.
  - Tests that write two comments under `frozen_time` must advance the clock between them, or
    expect the refusal.
- **Bundled guidance.** The comment lines in `workflow.md.j2`, `views/squads_skill.md.j2`,
  `claude/claude_section.md.j2`, `agents_md/agents_section.md.j2`, `agents/operator.md.j2`,
  `views/role_definition.md.j2` and `_specs/playbook.toml` gain the two verbs (read, a grep for
  comment examples). These are bundled files, so the work comes after the 0.16.0 bump.
- **Docs** (tech writer):
  - `docs/stability.md`: the extended Tier 1 header, the Tier 3 `hash` and `edited_ts`, and the
    two reflog ops.
  - `docs/internals.md`, the comment format line at line 288 or so.
  - The README command list, at line 299 or so.
  - `docs/recipes.md`, on inbox hits now carrying a hash.
- **Out of scope.** Per-bullet addressing, import events that edit or remove, and access control
  beyond the author match.

## The append-only statement: dated notes owed

The discussion stops being append-only. What those lines rely on still holds: a dated comment
records state at a point in time, only its author can change it, and it keeps its timestamp. The
wording does not hold.

- **CLAUDE.md line 160** (Conventions, "No status/lifecycle prose in bodies"): "the discussion is
  an append-only history". The line is hand-authored, so it is reworded in place: the discussion
  is a timestamped history that only each comment's author can correct.
- **CLAUDE.md line 340** (the managed region, orchestration loop step 5): "the discussion is an
  append-only log". Change it in `templates/claude/claude_section.md.j2` line 116 and regenerate
  the managed-section golden, never the rendered file. `agents_md/agents_section.md.j2` has no
  such line (driven, grep).
- **ADR-979.** The first sentence of Context ("Discussion comments are append-only history: there
  is no verb that edits or deletes one") needs a dated note. §2 needs a dated note for the
  optional fraction and edit mark. §4 needs one for the disambiguation step, if the operator takes
  it.
- **ADR-981 §1**, the "No denormalisation" bullet: "Discussion text is append-only history".
  Its dated note says the conclusion stands, because an edit keeps the name snapshot and never
  writes a pronoun into a header.
- ADR-114, ADR-117, ADR-295, ADR-314 and ADR-663 say "append-only" of the reflog or the board, not
  of discussions, and are unaffected (read). The use in ADR-263 is in a discussion comment, which
  is exempt.

## Build order

The 0.16 main stream as of 2026-10-15 is TASK-954, ADR-1009, FEAT-980, the 0.16.0 bump, the
ADR-1007 flattening, TASK-989, TASK-990, FEAT-976, FEAT-977, then FEAT-961 and FEAT-966.

- **The verbs go after FEAT-977 and before FEAT-961.** They need FEAT-980's slug header, they
  change bundled guidance (so after the bump), and FEAT-977 creates the roster comment verbs.
- **Two pieces belong in FEAT-980 if this decision is accepted before it starts:**
  - the millisecond fraction in the shared pattern and in `format_comment`;
  - §7's disambiguation in the 0.16 migration step.

  FEAT-980 is next but one in the stream, so this matters now. Shipping millisecond headers early
  costs nothing. Adding them later means amending the same pattern and migration a second time.

The verbs have no feature or task yet.

## Alternatives

- **Positional index (`#n`)**, the original ruling of 2026-10-15T19:25:09Z. Rejected by the
  operator's amendment of 2026-10-15T19:31:40Z: an index shifts when an earlier comment is deleted,
  so between a caller's read and its write it can point at another comment. The author match could
  not catch that when both comments shared an author. The optional guards drafted for it
  (`--expect-digest`, `--expect-ts`) go with it.
- **The formatted id as the item input.** Rejected: a retype would change every hash on the item.
- **The region as a hash input.** Rejected: comments never move between regions, so it adds
  nothing. Leaving it out keeps one namespace per item and needs no sub-entity verbs.
- **Whole-second timestamps.** Rejected: the duplicate refusal would fire on routine scripted
  comments, and the merge rule would fuse distinct ones (Context).
- **A stored comment id.** Rejected by the ruling: the hash is never stored.
- **No edit mark.** Rejected. A reader could not tell that a comment changed, and only the local
  reflog would know.
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
<!-- sq:discussion:end -->
