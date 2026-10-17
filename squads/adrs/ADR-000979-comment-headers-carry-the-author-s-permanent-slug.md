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
updated_at: '2026-10-17T02:01:31Z'
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

> **Amended 2026-10-16 (A1, A2):** the reservation above binds roles only. An operator slug must
> also start with `op-`, and a slug names one author across roles and operators; skills are
> outside that namespace. See **Amendments — 2026-10-16**.

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

> **Amended 2026-10-16 (A4):** the resolution step gains a roster check that runs before any
> header is resolved, and an entry that breaks A1 or A2 is a failure of the same kind as the
> ones listed above: nothing is written. See A4.

> **Amended 2026-10-16 (A6):** a legacy name that matches no title is then matched against
> operator slugs, because the released 0.15.0 writer named an operator without a full name by
> its slug. See A6.

> **Note 2026-10-16 (REV-1027 F7):** the header rewrite does not go through `_sections.py`. It
> reads each item file as raw bytes, uses `_sections.find_markers` only to locate the discussion
> regions, and replaces each legacy header line whole, keeping that line's own terminator (LF
> or CRLF). Two reasons. Byte preservation: every byte outside the replaced header lines,
> the comment's bullets and line endings included, comes out identical. Header-line-only
> edits: `_sections.py` offers whole-region edits on decoded text (`replace_section`,
> `append_to_section`) and no single-line replace (read), so going through it would re-emit
> every discussion region to change one line in it. Invariant 3 holds in substance: the lines
> replaced are sq's own attribution lines, never an author's prose.

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

> **Amended 2026-10-16 (A1):** creation through `sq operator add --slug` and through the bulk
> importer applies the operator rule of A1, at the same seam as the role rule. See A1.

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

## Amendments — 2026-10-16

Decisions 1 to 6 stand as ruled. A1 to A5 rule the case REV-1026 finding F3 raised, A6 the case of
REV-1027 finding F2, and A7 the case of REV-1055 finding F7. Decision
2 reserves `operator`, `squads` and `op-` against roles, and says nothing about operators. The
text above is unedited apart from the dated notes that point here. Evidence is marked **driven**
(run on this repository's squad with the released `sq`, or recorded as driven on REV-1026),
**read** (source read) or **inferred**.

**The gap** (driven, REV-1026 F3). `sq operator add --slug` and the importer's operator `create`
accept `squads`, `operator`, a live role's slug (`qa`), `Bad Slug` and `OP-UP`. An operator
holding `squads` writes headers identical to rename and retype entries. One holding `operator`
is shown as `Operator`, because `_author_of` answers the anonymous slug before it reads the
roster (read, `_services/_base.py`). One holding `qa` gives two live entries one slug, and
`sq check` reports nothing. One holding `Bad Slug` or `OP-UP` can never comment. Each breaks the
statement decision 2 rests on: the two reserved slugs cover authors that are not roster entries,
and a slug is an author's identity.

### A1 — An operator slug starts with `op-` and is in the grammar

```
operator slug = "op-" [a-z0-9] [a-z0-9-]*
role slug     = [a-z0-9] [a-z0-9-]*, not "operator", not "squads", not starting with "op-"
skill slug    = [a-z0-9] [a-z0-9-]*
```

- Operator creation refuses any other slug, explicit or derived, with exit 1 and nothing
  written. That is `sq operator add --slug`, the importer's operator `create`, and any path
  added later, because the rule sits at the roster creation seam that already holds the role
  rule (read, `_check_roster_slug` in `_services/_base.py`). The message names the rule and,
  when one exists, the compliant form: `operator slug 'Anna' must start with 'op-' and be
  lowercase letters, digits and hyphens (e.g. 'op-anna')`.
- Creation does not lowercase or prefix a typed slug. A slug is permanent (decision 1), so the
  one that is stored is the one that was typed and accepted.
- The derived default already complies: `op-` plus the slugified first name, or `op-untitled`
  when nothing slugifies (driven, a direct call of `operator_slug` on an accented name, a
  non-Latin name and a punctuation-only name).
- The one rule closes every case of the gap. `squads` and `operator` do not start with `op-`. A
  role slug cannot start with `op-` (decision 2), so no operator slug can equal a role slug.
  `Bad Slug` and `OP-UP` are outside the grammar.

### A2 — One author namespace: roles and operators; skills are outside it

- **The author namespace** is every role (developer roles included) and every operator, live
  and retired, plus the two reserved participant slugs. A slug in it names exactly one author.
  This is what lets ADR-1013 match an author by slug equality.
- Uniqueness inside the namespace follows from three rules, and no new cross-type check is
  needed at creation: A1 and decision 2 make the role and operator slug sets disjoint by
  prefix and exclude the reserved slugs from both, and creation already refuses a duplicate
  within a type (read, `_refuse_duplicate_slug` in `_services/_roster.py`).
- **Skills are not in it.** A skill never authors anything: `--as` resolves against roles and
  operators only (read, `resolve_slug_or_raise`), and a skill is addressed only under
  `sq skill`. The bundled `squads` skill already holds the system slug (driven,
  `sq skill squads show` is SKILL-200 on this squad), so a skill slug cannot share the author
  namespace without a contradiction already shipped. A skill slug is unique among skills and in
  the grammar (REV-1026 F2's seam), and is otherwise unconstrained.
- **Consequence.** `sq check`'s `agent_registered` builds its set from every roster type,
  skills included (read, `registered_slugs` in `_services/_validators.py`), so an item whose
  author or assignee names a skill passes. The set becomes roles and operators.

### A3 — `sq check` reports a roster entry that breaks A1 or A2

- After A1 creation cannot produce such an entry. One can still arrive: a hand-edited file, or
  two branches that each added an operator under the same slug and were then merged (inferred,
  the same way ID collisions arrive).
- A new squad-global rule, `roster_slug_valid`, on by default at `error`, reports each role and
  operator, live or retired, whose slug is outside its grammar in A1, or that shares its slug
  with another entry of the namespace. One issue per entry, naming the item, the slug, the rule
  broken and, for a shared slug, the other holders:
  `OP-12: operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5`.
- **It reports and never gates a write**, for the reason `default_designation_duplicated`
  gives (read): the remedy runs through creation and removal, and a gate on a later unrelated
  write would lock the squad out of that remedy.
- **The remedy** is in the message: `sq operator <id> rm --purge`, then `sq operator add` under
  the same name, which takes a compliant slug. Headers already written keep the old slug:
  decision 1 lets nothing rewrite them, and decision 6 already accepts the ambiguity of a purged
  slug's history. Addressing by id matters, because a slug matching a group verb cannot be
  addressed by slug (read, `sq operator --help`).

> **Note 2026-10-16 (REV-1055 F5):** `roster_slug_valid` is a squad-global rule. It runs on
> every `sq check` at a fixed `error`, outside any type's selection, so it cannot be deselected
> or given another level; read "on by default" above as "always on". Every squad-global rule
> works this way (read, `SQUAD_GLOBAL_CATALOG` and `ValidatorEngine.report` in
> `_services/_validators.py`), `default_designation_duplicated` included. Two reasons. It is an
> identity check: an adopter has no legitimate reason to let one slug name two authors, which
> breaks ADR-1013's match. And a switch would need squad-global rules to become selectable, an
> engine change this amendment does not make.

### A4 — The 0.16 migration refuses; it does not only report

The planning pass checks the roster before it resolves any header, and an entry that breaks A1
or A2 is a failure. Report-only is not enough, for three reasons:

- **It is the last point where the fix is clean** (inferred, from decision 4). A legacy header
  names its author by display name. Before the run, a non-compliant operator can be purged and
  added again under the same name, and its headers resolve to the new `op-` slug. After the run
  every header carries the slug and decision 1 forbids rewriting it, so the old slug is fixed in
  the history for good.
- **An out-of-grammar slug breaks the corpus** (read, the new pattern). A composed header such
  as ``- [ts] `Bad Slug` Name:`` does not match the pattern, so the reader does not see a header,
  and that comment's lines join the comment before it.
- **A reserved or shared slug fixes a false identity in place** (inferred, from ADR-1013 §9).
  Headers rewritten to `squads` become system entries that no `--as` can edit; headers
  rewritten to `operator` become anonymous; headers rewritten to `qa` become editable by
  whoever holds `qa`.

What the run does:

- Every role and operator item, live and retired, is checked against A1 and A2 before any
  header is resolved. A breach is one line per entry, file-level, in the same report as the
  header failures, and counts toward the same exit 1 with nothing written:
  `operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5`.
- Each entry is reported once. The headers that name it are not also listed one per line.
- The `manual` runbook adds the remedy, run with the release the squad is stamped for (the gate
  lets only `sq migrate up`, `help` and `chlog` past): `sq operator <id> rm --purge`, then
  `sq operator add "<the same full name>"`, then `sq migrate up` again. The purge is required:
  a plain `rm` drops the index entry and keeps the file, and the run's reconcile indexes the file
  again (read, `remove_item` in `_services/_items.py`). Open items assigned to the old slug are
  reassigned with `update --assignee`. An item's `author` keeps the old slug, which `sq check`'s
  `agent_registered` then names.
- A role that breaks decision 2 or the grammar is reported the same way. Its remedy is the
  project role file renamed to a compliant slug and the role activated again, with the old one
  purged.
- This repository's squad holds one operator, `op-pierre`, and no role in breach (driven,
  `sq operator list` and `sq role list`), so the check costs it nothing.

### A5 — ADR-1013's author match

- The match stays slug equality (ADR-1013 §9). A1 and A2 are what make equality mean the same
  author. Where A3 reports a shared slug, the match cannot tell the holders apart, and the
  remedy is A3's, not a stronger match.
- **`squads` resolves for no actor**, whatever the roster holds. `--as squads` is refused by
  every comment writer, the importer's `as` included, so system entries stay immutable by rule
  and not because no roster entry happens to hold the slug. Rename and retype keep writing it
  internally. The rest of REV-1026 F5 (an importer actor not in the roster) is not ruled here.
- **`operator` always resolves to the anonymous author** before the roster is read, as
  `resolve_slug_or_raise` and `_author_of` already do (read). A roster entry holding it is A3's
  report, never an identity.

### A6 — A legacy name resolves by title, then by an operator's slug

This rules REV-1027 finding F2. The released 0.15.0 writer named an operator by
`extra.full_name`, falling back to its slug (read, `_author_of` in 0.15.0). An operator the
released importer created without a full name therefore has headers such as
`- [2026-10-16T07:36:53Z] op-ann:` (driven, REV-1027 F2). Decision 4 resolves an operator by
its full name, falling back to its title, so the run refuses on a registered, live operator,
and the remedy in its `manual` (add the entry back under that name) would create a second
operator whose display name is `op-ann` and attribute the headers to it.

- Each legacy name is matched first against the titles decision 4 lists: every role's
  `item.title`, every operator's full name or title, and the two reserved names `Operator` and
  `squads`.
- Only when no title matches is the name matched against the slugs of every operator item,
  live and retired. A match resolves to that operator's slug.
- A title match always wins. A name that matches a title and another entry's operator slug
  resolves by the title and is not a collision.
- A name equal to a role slug, or to no slug in the roster, still matches no entry. The rule
  for importer actors that are not in the roster stands.
- The name's bytes are kept, as for every rewritten header:
  ``- [2026-10-16T07:36:53Z] `op-ann` op-ann:``.

> **Note 2026-10-16 (A6 as built):** the 0.16 migration narrows A6. It keys each operator by
> its `extra.full_name`, or by its slug only when it has no full name, and never by its title;
> a role stays keyed by its title (read, `_read_roster` in `_migrations/_v0_15_to_v0_16.py`,
> and that step's `manual`). A name that matches no key fails as before, and a name that matches
> two keys fails as a collision, so a role title equal to the slug of an operator without a full
> name is refused, not resolved by the title. Read "title, then any operator's slug" above, and
> the matching proof under "What the amendments oblige", in that sense. Two reasons. The key is exactly what the
> released 0.15.0 writer put in a header: `extra.full_name`, falling back to the slug only when
> it is absent (read, `_author_of` in 0.15.0), so every header that writer produced still
> resolves, `op-ann:` included. And a stray name that happens to equal the slug of an operator
> who has a full name is not silently attributed to that operator; it is refused with the
> manual's remedy.

### A7 — A role or skill slug is not a verb of its `sq` group

Added 2026-10-16 for REV-1055 finding F7.

**The gap** (driven, REV-1055 F7). `.overrides/roles/list.toml` activates as ROLE-21 with exit
0, then `sq role list show` fails with `Got unexpected extra argument(s) (show)`: the group verb
wins. The generated agent pointer tells the agent to run `sq role <slug> show` (read,
`pointer_agent.md.j2`), and a skill pointer `sq skill <slug> show` (read,
`pointer_skill.md.j2`), so for such an entry the one instruction the pointer carries cannot
work. `sq role --help` and `sq skill --help` already state that a slug matching a group verb is
unaddressable by slug (read), which documents the hole without closing it. Operators are
already closed: A1 puts every operator slug under `op-`, and no `sq operator` verb starts with
it.

- Role activation and skill creation refuse a slug equal to a group verb of `sq role` (today
  `catalog`, `list`, `activate`) or of `sq skill` (today `add`), with exit 1 and nothing
  written. The check sits at the roster creation seam beside the role rule of A1
  (`_check_roster_slug`), so the override path, the importer and any later path all pass
  through it.
- The verb set is read from the CLI group's registered commands, not a hand-kept list, so a
  verb added later is covered without an edit here.
- Only group verbs are reserved. The verbs that follow an address (`show`, `rm`, `regen`, …)
  come after the slug and do not collide.
- `roster_slug_valid` (A3) also reports a role or skill whose slug is a verb of its group,
  because an entry can already hold one (an override activated before this rule, or a verb a
  later release adds). The remedy names the entry by id: rename the project role file or skill
  to another slug, activate or add it again, and purge the old entry. A skill stays outside the
  author namespace (A2); this rule is about addressing, not identity.
- The 0.16 migration does not refuse on it. A verb slug breaks no header: the composed header
  matches the pattern and names one author.
- Developer roles are unaffected: a `<tech>-dev` slug ends in `-dev`, and no group verb does.

Note, 2026-10-16 (REV-1055 F8). The verb set is not read from the CLI at runtime. It is held as
two constants, `ROLE_GROUP_VERBS` and `SKILL_GROUP_VERBS` in `_models/_participants.py`,
because the models layer sits below the CLI and cannot import the Typer app; this is the same
arrangement as `RESERVED_CLI_VERBS` in `_workflow/_models.py`. A meta test
(`tests/meta/test_roster_group_verbs_match_the_live_command_table.py`) asserts each constant
equals the verbs registered on its group, so it fails in both directions: a verb dropped from
the group, or a verb added to it without the constant. The guard is equivalent to a runtime
read for every released build, since no build ships with the constants out of step with the
command table. The difference is where a new verb is caught: it fails CI until the constant is
edited, rather than being covered silently. Reading the verbs at runtime would need a layering
change and buys nothing a release could observe.

### What the amendments oblige

- Operator creation refuses a slug outside `op-[a-z0-9][a-z0-9-]*`, on every path, with nothing
  written. A table: `squads`, `operator`, `qa` with role `qa` live, `Bad Slug`, `OP-UP`, `op-`,
  `op--x` refused; `op-anna` and the derived default accepted.
- `agent_registered` reads roles and operators only.
- `roster_slug_valid` reports each breaching or shared entry, live and retired, at `error`, and
  gates no write.
- The 0.16 planning pass refuses on a breaching entry, reports it once per entry before any
  header resolves, and the `manual` names the purge-and-add remedy. Proof: each breach kind,
  alone and beside header failures, with every file hashing identically before and after.
- `--as squads` is refused by every comment writer, the importer included, even when an entry
  holds `squads`.
- Adopter-visible: `sq operator add --slug` and the importer refuse a slug that does not start
  with `op-`, and a squad holding such an operator does not migrate until it is replaced.
  `docs/migration.md`, the 0.16 CHANGELOG and `docs/stability.md` Tier 1 (beside the header
  grammar) say so.
- The 0.16 planning pass resolves a legacy name by title, then by operator slug (A6). Proof: the
  header the released 0.15.0 writer actually writes for an operator without a full name
  migrates to that operator's slug, a title match beats an operator-slug match, and a name
  equal only to a role slug still fails.
- Role activation and skill creation refuse a slug equal to a group verb of `sq role` or
  `sq skill`, held in step with the registered commands (A7 note), and `roster_slug_valid` reports an entry that
  already holds one (A7). Proof: `list`, `catalog`, `activate` refused as role slugs through an
  override, `add` refused as a skill slug, nothing written; a hand-made role slugged `list`
  reported by `sq check`; `show` accepted.
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
- [2026-10-15T22:17:49Z] Robert Architect:
  - - 2026-10-16: amended for REV-1026 F3, additions only (three dated notes plus "Amendments — 2026-10-16", A1 to A5); status untouched.
    - A1: an operator slug is `op-[a-z0-9][a-z0-9-]*`, refused otherwise at the roster creation seam (operator add --slug, importer). No silent lowercasing.
    - A2: one author namespace, roles plus operators plus the two reserved slugs; skills are outside it (the bundled SKILL-200 already holds `squads`, driven). agent_registered stops counting skill slugs.
    - A3: new `roster_slug_valid` check, error, report-only, remedy `sq operator <id> rm --purge` then `operator add`.
    - A4: the 0.16 planning pass refuses, not report-only: before the run a breaching operator can be purged and re-added under the same name and its legacy headers resolve to the new slug; after it the slug is fixed in history. An out-of-grammar slug would also produce header lines the new pattern does not match. This changes ST5 as briefed. This squad is unaffected (op-pierre only, driven).
    - A5: ADR-1013's match stays slug equality; `--as squads` is refused by every writer including the importer actor, `operator` is always the anonymous author.
    - @manager for op-pierre's confirmation: this changes what an adopter may type (operator add --slug) and makes a non-compliant operator block `sq migrate up`. Route A4 to @python-dev for ST5 once confirmed.
- [2026-10-16T07:43:46Z] Robert Architect:
  - - 2026-10-16: two additions for REV-1027, additions only; status untouched.
      - A6 (REV-1027 F2): the 0.16 migration resolves a legacy name by title first and, failing that, by an operator's slug, because the released 0.15.0 writer wrote an operator without `full_name` as its slug (`- [ts] op-ann:`). A dated note under decision 4 points to it. A6 is part of the pending amendment and is subject to op-pierre's confirmation together with A1 to A5.
      - Note under decision 4 (REV-1027 F7): the header rewrite replaces whole header lines in the raw bytes, keeping each line's terminator, with `_sections.find_markers` used only to locate regions; reason: byte preservation and header-line-only edits, which `_sections.py`'s whole-region API does not give.
      - @manager for op-pierre's confirmation of A1 to A6; once confirmed, A6 goes to @python-dev with REV-1027 F2.
- [2026-10-16T11:16:25Z] Pierre Chat:
  - 2026-10-16: confirmed the amendment A1–A6 as drafted (A1 operator slugs op-…; A2 one author namespace, skills excluded; A3 roster_slug_valid check; A4 the 0.16 migration refuses a non-conforming operator slug; A5 --as squads refused everywhere; A6 slug fallback when no title matches).
- [2026-10-16T11:53:31Z] Robert Architect:
  - - 2026-10-16: two additions for REV-1055, additions only; status untouched.
      - Note under A3 (F5): `roster_slug_valid` is squad-global, always on at a fixed `error`, not selectable; "on by default" reads as "always on". Reason: an identity check, and selectable squad-global rules would be an engine change.
      - A7 (F7): role activation and skill creation refuse a slug equal to a group verb of `sq role` (`catalog`, `list`, `activate`) or `sq skill` (`add`), read from the registered commands; `roster_slug_valid` also reports an entry that already holds one; the 0.16 migration does not refuse on it.
      - @manager A7 needs op-pierre's confirmation, as A6 did: it changes what an adopter may name a project role or skill.
- [2026-10-16T11:56:42Z] Pierre Chat:
  - 2026-10-16: confirmed A7 (roles and skills refuse a slug equal to their group's verbs, like operators).
- [2026-10-17T02:01:31Z] Robert Architect:
  - 2026-10-17: two dated notes owed under ADR-1013 (The append-only statement), from TASK-1079 ST14; body and status untouched.
    - **Context, first sentence** ("Discussion comments are append-only history: there is no verb that edits or deletes one"). Since ADR-1013, a comment can be edited and removed by its author through `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove`, and the same on `sq skill|role|operator <addr>`. What this decision relied on still holds: a comment is a timestamped record, only its author (matched by slug, ADR-1013 §9 and A5 here) can change it, and an edit keeps its timestamp, slug and display-name snapshot (§3).
    - **§2, the header grammar.** The header gains one optional group inside the brackets, after the timestamp: ``- [<ts>, edited <ts>] `<slug>` <name>:``. It records the last edit only: a second edit replaces the mark, it never stacks. It is not a hash input and needs no migration; the 0.16 header migration writes no mark. `--json` carries it as `edited_ts` (null when never edited).
<!-- sq:discussion:end -->
