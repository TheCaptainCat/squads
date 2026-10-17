---
id: ADR-979
sequence_id: 979
type: decision
title: Comment headers carry the author's permanent slug
status: Accepted
author: architect
refs:
- ADR-971
- FEAT-977
- MILE-934:targets
- ADR-1007
description: Header is - [ts] `slug` Name:; slugs never change; legacy headers migrated
  once; --json gains author_slug
created_at: '2026-09-29T14:33:58Z'
updated_at: '2026-10-15T20:16:59Z'
---
<!-- sq:body -->
## Context

Discussion comments are append-only history: there is no verb that edits or deletes one. Every
comment opens with a header line that sq writes, followed by the author's bullets.

**Today's header names the author by display name only** (read, `_discussion.py`):
`format_comment` writes `- [<timestamp>] <name>:`, and one regex, `_COMMENT_HEADER_RE`
(`^- \[([^\]]+)\] (.+?):$`), reads it back. The name comes from `ServiceCore._author_of`
(read, `_services/_base.py`): a role's `item.title`, an operator's `extra.full_name`, `Operator`
for the legacy `operator` sentinel, and the slug itself when nothing resolves. A display name
can change (a role's through `sq role activate --name`, read), and once it has, every earlier
header names someone the roster no longer knows. The slug the author typed with `--as` is
discarded at write time.

**Writers** (read, `rg format_comment`):

- `CollabMixin._comment_core` (`_services/_collab.py`), behind `sq <type> <n> comment`, the
  sub-entity `comment` verb and the bulk importer. `--as` is required (`require_as`) and
  validated against the live roster plus the `operator` sentinel (`resolve_slug_or_raise`),
  for agents and operators alike.
- `_services/_rename.py` and `_services/_retype.py` write system entries with the author
  string `squads`.

**Readers** (read):

- `split_discussion` feeds `sq <type> <n> comments` (human and `--json`), `show --comments`
  (styled, plain and `--raw`), `show --json` and the sub-entity `show --json` (`discussion`
  arrays of `{author, ts, body}`), and the TUI reader (`_tui/_reader.py`).
- `match_comment_header` feeds search and inbox region attribution (`_scan_comment_headers`,
  `_services/_collab.py`), which builds snippets of the form `[<ts>] <author>: <line>`.
- The VS Code client parses no header. It reads `discussion[].author` from `show --json`
  (`SqDiscussionEntry`, `isSqDiscussionEntry` checks `author`, `ts` and `body` only;
  `clients/vscode/src/types.ts`, `sqAdapter.ts`) and renders it in the preview.
- The inbox matches `@slug` text and never reads the header's author.

**Surfaces that already carry a slug** (read): item frontmatter `author` and `assignee`, board
notice `author` (`sq board post --as`), and the reflog entry each comment writes
(`store.log("comment", …, {"author": as_slug})`). A comment's `author` in `--json` is the
only author field that holds a display name.

**The two parsers disagree** (driven, a direct call of both functions on one region):
`split_discussion` matches headers at column 0, but `_scan_comment_headers` strips each line
first, so an indented `- [x] Done:` inside a comment body counts as a second header for
search attribution and not for `comments`.

**The corpus** (driven, a survey of every discussion header plus `sq role list --json` and
`sq operator list --json`): eleven distinct names, each equal to exactly one live role title
or operator full name, plus `Operator`. No `squads` system entry has been written yet.

ADR-971 made a stored slug the identity of a roster entry and declined a rename verb. This
decision puts that identity in the comment header and makes permanence a rule.

## Decision

**1. A slug is permanent.**

- The slug of every roster entity (a role, a developer role, a skill, an operator) is fixed
  when the entity is created and never changes afterwards.
- No verb, option, override, migration or repair path writes a different slug to an existing
  entry. This extends ADR-971's decision 3 from "no rename verb" to "no rename, ever".
- Display fields (title, full name, description) stay editable. A display change never
  touches `extra.slug`, `item.slug` or the file name.

**2. The header grammar.**

```
- [2026-09-29T14:02:11Z] `architect` Robert Architect:
- [2026-09-29T14:05:40Z] `op-pierre` Pierre Chat:
```

```
header    = "- [" timestamp "] `" slug "` " name ":" EOL
timestamp = YYYY-MM-DDTHH:MM:SSZ        (what clock.iso writes)
slug      = [a-z0-9][a-z0-9-]*          (the @mention character class)
name      = one or more characters, single line
```

- The header starts at column 0. Every reader uses one shared pattern, anchored at column 0
  with no stripping:
  ``^- \[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] `([a-z0-9][a-z0-9-]*)` (.+):$``
- The slug is delimited by backticks. A backtick cannot occur in a slug, so the slug ends
  unambiguously however the name is spelled, and markdown renders it as code. Brackets and
  parentheses were rejected because `[ts] [slug]` and `[ts] (slug)` sit next to link syntax.
  `@slug` was rejected because every header would become an inbox mention of its own author.
- An operator slug is written as it is stored (`op-pierre`). It needs no special form: the
  `op-` prefix already marks it.
- Two reserved participant slugs cover authors that are not roster entries: `operator` (the
  legacy anonymous sentinel, name `Operator`) and `squads` (system entries from rename and
  retype, name `squads`). No role may be created with either slug, or with a slug that starts
  with `op-`, which is reserved for operators.

**3. The pretty name is a snapshot for display.**

- The writer resolves the name at write time exactly as `_author_of` does today, collapses any
  line break to a space, and falls back to the slug when the name is empty.
- Nothing reads the name for identity: attribution, filtering and matching use the slug.
- A header whose name differs from the entity's current name is correct history, not drift.
  Nothing rewrites it later.

**4. Legacy headers are migrated once; there is no dual-read parser.**

The decision is op-pierre's. squads has no adopters yet, and every migration is deleted when
1.0 ships. A dual-read parser would stay in the codebase for good, to serve a state that exists
only until the migration runs, while the migration's code goes away with the rest.

Display names are taken never to have changed, so each legacy name resolves to the slug of the
entry that holds it now. The migration:

- scans every discussion region (top-level and each sub-entity's) for column-0 lines in the
  legacy grammar;
- resolves each name against every role item (live and retired, by `item.title`), every
  operator item (live and retired, by `extra.full_name`, falling back to its title), and the
  two reserved names `Operator` and `squads`;
- rewrites only the header line, through `_sections.py`, into the new grammar. The comment's
  bullets stay byte-identical, and a header already in the new grammar is skipped.

It fails loudly rather than guessing:

- Resolution runs over the whole corpus before anything is written.
- A name that matches no entry, a name that matches two or more slugs, and a column-0 line in
  a discussion region that looks like a header but whose timestamp is not in the grammar each
  count as a failure.
- On any failure, nothing is written and `sq migrate up` exits 1 with a `SquadsError` that
  lists every failure, one per line, then a count:
  `<squad-relative file>:<line>: 'Hugo Ops' matches no roster entry` and
  `<squad-relative file>:<line>: 'Sam Lee' matches 2 entries: op-sam, qa`.
- The migration's `manual` runbook names the remedy: add or reactivate the missing entry
  (retired entries already count), or give one of the colliding entries a distinct display name
  for the run. There is no option that maps a name to a slug by hand.

Invariant 3 holds. The header is sq's own attribution line, written by `format_comment` and
never by an author. The migration changes nothing an agent wrote.

**5. `--json` gains `author_slug`.**

- Every `discussion` entry (`show --json` for an item and a sub-entity) and every
  `comments --json` entry gains `author_slug`. `author` keeps the display name.
- This is additive under Tier 3. `author` cannot be retyped to a slug, which is why the new
  key is explicit, even though item frontmatter's `author` already holds a slug.
- Search and inbox JSON are unchanged: their snippets are display text.
- The human renders (`comments`, `show --comments`, `--raw`, the TUI) show the name followed by
  the slug.

**6. What permanence means on each write path.**

- **`update` verbs (FEAT-977).** Retitling or redescribing a skill, role or operator edits
  display fields only. The work-item retitle path (`_rename` in `_services/_items.py`) re-derives
  `item.slug` from the new title and moves the file (read); a roster item never takes that path.
  No `update` verb takes a `--slug` option. The comment verbs FEAT-977 adds to roster entities
  write this grammar.
- **Creation** is the only place a slug is chosen: derived per ADR-971, or explicit through
  `sq operator add --slug`.
- **Reuse after purge.** A slug freed by `rm --purge` may be taken by a new entity. Creation
  does not check comment history, so headers written before the purge then show the new
  entity's slug. That ambiguity is accepted.
- **Overrides.** A role override binds by file name to an existing slug, and the slug is pinned
  to that file name (read, per ADR-971). A `slug` key in an override document that differs from
  its file name is refused with an error naming the file, not silently discarded. A catalog
  override that stops declaring an entry does not rename the items created from it.
- **Retype and rename** (`sq <type> <n> retype`, `sq migrate rename-type`) refuse roster types
  (read, `_services/_retype.py`, `_services/_rename.py`), so they never reach a roster slug.
  Their system entries are written with the `squads` slug.
- **`sq repair`** rebuilds identity from frontmatter (`extra.slug`, then the file name) and
  never derives or writes a slug.

> **Note 2026-10-15 (ADR-1007):** `sq repair` rebuilds identity from the core `slug` key, then the
> file name; there is no `extra.slug`. Operators store no `full_name`: the 0.16 runner folds it into
> `title`, taking its value when the two differ, so a lookup of an operator by `title` after the
> flattening returns the name `extra.full_name` held before it (inferred from ADR-1007 decision 9).
> See ADR-1007 decisions 2 and 8.

## Consequences

- **Schema.** `SCHEMA_VERSION` becomes `0.16`, with a 0.15 to 0.16 migration registered as
  version `0.16.0`. If another 0.16 corpus migration lands in the same release, both run in
  the same step.
- **Code.** `format_comment` takes the slug and the name. `Comment` gains `author_slug`.
  `split_discussion`, `match_comment_header` and `_scan_comment_headers` share the one
  column-0 pattern, which also fixes the stripped-line mismatch search has today. Role
  creation refuses `operator`, `squads` and any slug starting with `op-`.
- **Tests.** Table-driven header parsing (names with colons, backticks, accents; an indented
  checkbox that is not a header), a round trip for each writer, and migration preflight
  failures for each failure kind, with no file written.
- **Docs.** `docs/stability.md` Tier 1 gains the header grammar and the slug permanence rule,
  and Tier 3 notes `author_slug`. The comment line in `docs/internals.md` ("Discussion,
  @mentions, inbox") changes to the new grammar. `docs/migration.md` and the 0.16 CHANGELOG
  describe the migration and its failure report.
- **VS Code client.** It parses no header and ignores extra fields, so it keeps working
  unchanged. Showing the slug in the preview means adding an optional `author_slug` to
  `SqDiscussionEntry`. It must stay optional, because an older `sq` omits it.
- **Pretty names drift by design.** After a display rename, old headers show the old name and
  new headers the new one, both under the same slug.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:35:26Z] Robert Architect:
  - @op-pierre for your call. Written from your direction: permanent slugs, a slug-anchored header, and a single migration with no dual-read parser (your ruling, relayed by the manager). Open questions:
    - Slug reuse after `rm --purge`. Nothing stops a new entity from taking a purged slug, and old headers would then name the newcomer. My recommendation: creation refuses a slug that appears as an author in any comment header. This is derived from history, so nothing new is stored.
    - Delimiter. I chose backticks. Brackets and parentheses sit next to markdown link syntax, and `@slug` would make every header an inbox mention.
    - Reserved slugs. `operator` and `squads` become reserved participant slugs that no role can take. Should a role slug starting with `op-` also be refused?
    - Migration failures. The ADR leaves no escape hatch: fix the roster and re-run. Say if you want a `--map "Name=slug"` override instead.
- [2026-09-29T14:39:42Z] Pierre Chat:
  - Slug reuse after rm --purge: allowed (accept the ambiguity).
  - Delimiter: backticks.
  - Reserved: also refuse a role slug starting with op-.
  - Migration failures: fix the roster and re-run; no --map flag.
- [2026-09-29T14:57:04Z] Pierre Chat:
  - Accepted.
<!-- sq:discussion:end -->
