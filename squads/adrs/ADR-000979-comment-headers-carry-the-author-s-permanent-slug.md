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
updated_at: '2026-10-25T21:42:26Z'
---
<!-- sq:body -->
## Context

Every discussion comment opens with a header line that sq writes, followed by the author's
bullets. A comment is a timestamped record that only its author can edit or remove (ADR-1013).

**The legacy header named the author by display name only**: `- [<timestamp>] <name>:`, read back
by one regex. The name came from the author's role title or operator name at write time, and the
slug the author typed with `--as` was discarded. A display name can change, and once it has,
every earlier header names someone the roster no longer knows.

**Writers.** `CollabMixin._comment_core` (`_services/_collab.py`), behind `sq <type> <n>
comment`, the sub-entity `comment` verb, the roster `comment` verbs and the bulk importer. `--as`
is required and validated against the live roster plus the `operator` sentinel. Rename and retype
write system entries with the author string `squads`.

**Readers.** `split_discussion` feeds `comments` (human and `--json`), `show --comments` (styled,
plain and `--raw`), `show --json` and the sub-entity `show --json` `discussion` arrays, and the
TUI reader. `match_comment_header` feeds search and inbox region attribution. The VS Code client
parses no header; it reads `discussion[].author` from `show --json`. The inbox matches `@slug`
text and never reads the header's author.

**Surfaces that already carry a slug**: item frontmatter `author` and `assignee`, board notice
`author`, and the reflog entry each comment writes. A comment's `author` in `--json` is the only
author field that holds a display name.

**The two parsers disagreed** (driven, when this was decided): `split_discussion` matched headers
at column 0, but the search scan stripped each line first, so an indented `- [x] Done:` inside a
comment body counted as a second header for search attribution and not for `comments`.

ADR-971 made a stored slug the identity of a roster entry and declined a rename verb. This
decision puts that identity in the comment header and makes permanence a rule.

## Decision

**1. A slug is permanent.**

- The slug of every roster entity (a role, a developer role, a skill, an operator) is fixed when
  the entity is created and never changes afterwards.
- No verb, option, override, migration or repair path writes a different slug to an existing
  entry. This extends ADR-971's decision 3 from "no rename verb" to "no rename, ever".
- Display fields (title, description) stay editable. A display change never touches `item.slug`
  or the file name.

**2. The header grammar.**

```
- [2026-09-29T14:02:11Z] `architect` Robert Architect:
- [2026-09-29T14:05:40Z, edited 2026-09-29T15:00:00Z] `op-pierre` Pierre Chat:
```

```
header    = "- [" timestamp [", edited " timestamp] "] `" slug "` " name ":" EOL
timestamp = YYYY-MM-DDTHH:MM:SSZ        (what clock.iso writes)
slug      = [a-z0-9][a-z0-9-]*          (the @mention character class)
name      = one or more characters, single line
```

- The header starts at column 0. Every reader uses one shared pattern, anchored at column 0 with
  no stripping, so search attribution and `comments` agree.
- The optional `, edited <ts>` group records the last edit (ADR-1013 §4). A second edit replaces
  it, never stacks it. It is not a hash input, and `--json` carries it as `edited_ts` (`null` when
  never edited).
- The slug is delimited by backticks. A backtick cannot occur in a slug, so the slug ends
  unambiguously however the name is spelled, and markdown renders it as code. Brackets and
  parentheses were rejected because `[ts] [slug]` and `[ts] (slug)` sit next to link syntax.
  `@slug` was rejected because every header would become an inbox mention of its own author.
- Two reserved participant slugs cover authors that are not roster entries: `operator` (the
  legacy anonymous sentinel, name `Operator`) and `squads` (system entries from rename and
  retype, name `squads`).

**2a. The slug grammar, by roster type.**

```
operator slug = "op-" [a-z0-9] [a-z0-9-]*
role slug     = [a-z0-9] [a-z0-9-]*, not "operator", not "squads", not starting with "op-",
                not a group verb of `sq role`
skill slug    = [a-z0-9] [a-z0-9-]*, not a group verb of `sq skill`
```

- Creation refuses any other slug, explicit or derived, with exit 1 and nothing written, at the
  roster creation seam (`_check_roster_slug`), so `sq operator add --slug`, `sq dev add --slug`,
  role activation through an override, skill creation, the importer and any later path all pass
  through it. The message names the rule and, when one exists, the compliant form:
  `operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g.
  'op-anna')`.
- Creation does not lowercase or prefix a typed slug. A slug is permanent, so the one that is
  stored is the one that was typed and accepted. The derived operator default already complies:
  `op-` plus the slugified first name, or `op-untitled` when nothing slugifies.
- **Group verbs.** A role or skill slug equal to a group verb of its `sq` group (`activate`,
  `catalog`, `list` for roles; `add` for skills) is refused, because the pointer's `sq role <slug>
  show` / `sq skill <slug> show` could not address it. Only group verbs are reserved; the verbs
  that follow an address (`show`, `rm`, …) come after the slug and do not collide. The sets are
  held as `ROLE_GROUP_VERBS` and `SKILL_GROUP_VERBS` in `_models/_participants.py`, because the
  models layer cannot import the CLI, and a `tests/meta` guard asserts each equals the verbs
  registered on its group, in both directions. Operators are already closed: every operator slug
  starts with `op-`, and no `sq operator` verb does.

**2b. One author namespace: roles and operators; skills are outside it.**

- The author namespace is every role (developer roles included) and every operator, live and
  retired, plus the two reserved participant slugs. A slug in it names exactly one author, which
  is what lets ADR-1013 match an author by slug equality.
- Uniqueness inside it follows from the grammar: role and operator slugs are disjoint by prefix,
  both exclude the reserved slugs, and creation refuses a duplicate within a type.
- Skills are not in it. A skill never authors anything: `--as` resolves against roles and
  operators only. The bundled `squads` skill holds the system slug, which a shared namespace would
  contradict. A skill slug is unique among skills and in its grammar, and otherwise unconstrained.
- `sq check`'s `agent_registered` builds its set from roles and operators only.
- `squads` resolves for no actor: `--as squads` is refused by every comment writer, the importer
  included, so system entries stay immutable by rule. `operator` always resolves to the anonymous
  author before the roster is read.

**2c. `sq check` reports a roster entry that breaks 2a or 2b.**

Creation cannot produce such an entry, but one can arrive through a hand-edited file or a merge
of two branches that each added an operator under one slug. `roster_slug_valid`, a squad-global
rule, always on at `error` (it cannot be selected, deselected or levelled, like every always-on
squad-global member), reports each role and operator, live or retired, whose slug is outside its
grammar or shared with another entry of the namespace, and each role or skill whose slug is a group
verb. One issue per entry, naming the item, the slug, the rule broken and, for a shared slug, the
other holders: `OP-12: operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5`.
It reports and never gates a write, because the remedy runs through creation and removal: `sq
operator <id> rm --purge`, then `sq operator add` under the same name, which takes a compliant
slug (or, for a role or skill, a renamed project file activated again and the old entry purged).
Headers already written keep the old slug.

**3. The pretty name is a snapshot for display.**

- The writer resolves the name at write time from the author's role or operator `title`,
  collapses any line break to a space, and falls back to the slug when the name is empty.
- Nothing reads the name for identity: attribution, filtering and matching use the slug.
- A header whose name differs from the entity's current name is correct history, not drift.
  Nothing rewrites it later; an edit keeps the timestamp, slug and name snapshot.

**4. Legacy headers are migrated once; there is no dual-read parser.**

The decision is op-pierre's. A dual-read parser would stay in the codebase for good to serve a
state that exists only until the migration runs. The 0.15 to 0.16 migration:

- scans every discussion region (top-level and each sub-entity's) for column-0 lines in the
  legacy grammar;
- checks every role and operator item, live and retired, against 2a and 2b before any header is
  resolved; a breach is one line per entry, in the same report as the header failures;
- resolves each legacy name by the key the 0.15 writer put in a header: a role by its title; an
  operator by its full name, or by its slug when it had none; plus the reserved names `Operator`
  and `squads`. A name that matches no key fails, and a name that matches two keys fails as a
  collision;
- rewrites only the header lines. It reads each item file as raw bytes, uses
  `_sections.find_markers` only to locate the discussion regions, and replaces each legacy header
  line whole, keeping that line's terminator (LF or CRLF), so every byte outside the replaced
  lines comes out identical. A header already in the new grammar is skipped. The edit mark is
  never written by the migration.

It fails loudly rather than guessing. Resolution and the roster check run over the whole corpus
before anything is written. On any failure nothing is written and `sq migrate up` exits 1 with a
`SquadsError` that lists every failure, one per line, then a count:
`<squad-relative file>:<line>: 'Hugo Ops' matches no roster entry`,
`<squad-relative file>:<line>: 'Sam Lee' matches 2 entries: op-sam, qa`, and
`operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5`.
The migration's `manual` runbook names the remedies, run with the release the squad is stamped
for: add or reactivate the missing entry (retired entries already count), give one of two
colliding entries a distinct display name for the run, or purge and re-add a non-compliant
operator under the same full name (a plain `rm` is not enough: the reconcile would index the file
again). There is no option that maps a name to a slug by hand.

Invariant 3 holds in substance: the lines replaced are sq's own attribution lines, never an
author's prose.

**5. `--json` carries `author_slug`.**

- Every `discussion` entry (`show --json` for an item and a sub-entity) and every
  `comments --json` entry carries `author_slug` beside `author`, which keeps the display name.
- This is additive under Tier 3. `author` cannot be retyped to a slug, which is why the key is
  explicit, even though item frontmatter's `author` already holds a slug.
- Search and inbox JSON are unchanged: their snippets are display text.
- The human renders (`comments`, `show --comments`, `--raw`, the TUI) show the name followed by
  the slug.

**6. What permanence means on each write path.**

- **`update` verbs.** Retitling or redescribing a skill, role or operator edits display fields
  only. The work-item retitle path re-derives `item.slug` from the new title and moves the file; a
  roster item never takes that path. No `update` verb takes a `--slug` option.
- **Creation** is the only place a slug is chosen: derived per ADR-971, or explicit through
  `sq operator add --slug` or `sq dev add --slug`, under 2a.
- **Reuse after purge.** A slug freed by `rm --purge` may be taken by a new entity. Creation does
  not check comment history, so headers written before the purge then show the new entity's slug.
  That ambiguity is accepted, and it extends to editing (ADR-1013 §9).
- **Overrides.** A role override binds by file name to an existing slug, and the slug is pinned to
  that file name. A `slug` key in an override document that differs from its file name is refused
  with an error naming the file. A catalog override that stops declaring an entry does not rename
  the items created from it.
- **Retype and rename** refuse roster types, so they never reach a roster slug. Their system
  entries are written with the `squads` slug.
- **`sq repair`** rebuilds identity from the core `slug` frontmatter key, then the file name, and
  never derives or writes a slug.

## Consequences

- **Schema.** The header grammar and the slug rules came with the 0.16 schema and its 0.15 to
  0.16 migration step.
- **Code.** `format_comment` takes the slug and the name, `Comment` carries `author_slug`, and
  `split_discussion`, `match_comment_header` and the search scan share the one column-0 pattern.
- **Docs.** `docs/stability.md` Tier 1 carries the header grammar, the slug grammar and the
  permanence rule, and Tier 3 notes `author_slug`.
- **VS Code client.** It parses no header and ignores extra fields. Showing the slug in the
  preview reads an optional `author_slug`, optional because an older `sq` omits it.
- **Adopter-visible.** `sq operator add --slug` and the importer refuse a slug that does not start
  with `op-`, a role or skill cannot take its group's verbs as a slug, and a squad holding a
  non-compliant operator does not migrate to 0.16 until it is replaced.
- **Pretty names drift by design.** After a display rename, old headers show the old name and new
  headers the new one, both under the same slug.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:35:26Z] `architect` Robert Architect:
  - @op-pierre for your call. Written from your direction: permanent slugs, a slug-anchored header, and a single migration with no dual-read parser (your ruling, relayed by the manager). Open questions:
    - Slug reuse after `rm --purge`. Nothing stops a new entity from taking a purged slug, and old headers would then name the newcomer. My recommendation: creation refuses a slug that appears as an author in any comment header. This is derived from history, so nothing new is stored.
    - Delimiter. I chose backticks. Brackets and parentheses sit next to markdown link syntax, and `@slug` would make every header an inbox mention.
    - Reserved slugs. `operator` and `squads` become reserved participant slugs that no role can take. Should a role slug starting with `op-` also be refused?
    - Migration failures. The ADR leaves no escape hatch: fix the roster and re-run. Say if you want a `--map "Name=slug"` override instead.
- [2026-09-29T14:39:42Z] `op-pierre` Pierre Chat:
  - Slug reuse after rm --purge: allowed (accept the ambiguity).
  - Delimiter: backticks.
  - Reserved: also refuse a role slug starting with op-.
  - Migration failures: fix the roster and re-run; no --map flag.
- [2026-09-29T14:57:04Z] `op-pierre` Pierre Chat:
  - Accepted.
- [2026-10-15T22:17:49Z] `architect` Robert Architect:
  - - 2026-10-16: amended for REV-1026 F3, additions only (three dated notes plus "Amendments — 2026-10-16", A1 to A5); status untouched.
    - A1: an operator slug is `op-[a-z0-9][a-z0-9-]*`, refused otherwise at the roster creation seam (operator add --slug, importer). No silent lowercasing.
    - A2: one author namespace, roles plus operators plus the two reserved slugs; skills are outside it (the bundled SKILL-200 already holds `squads`, driven). agent_registered stops counting skill slugs.
    - A3: new `roster_slug_valid` check, error, report-only, remedy `sq operator <id> rm --purge` then `operator add`.
    - A4: the 0.16 planning pass refuses, not report-only: before the run a breaching operator can be purged and re-added under the same name and its legacy headers resolve to the new slug; after it the slug is fixed in history. An out-of-grammar slug would also produce header lines the new pattern does not match. This changes ST5 as briefed. This squad is unaffected (op-pierre only, driven).
    - A5: ADR-1013's match stays slug equality; `--as squads` is refused by every writer including the importer actor, `operator` is always the anonymous author.
    - @manager for op-pierre's confirmation: this changes what an adopter may type (operator add --slug) and makes a non-compliant operator block `sq migrate up`. Route A4 to @python-dev for ST5 once confirmed.
- [2026-10-16T07:43:46Z] `architect` Robert Architect:
  - - 2026-10-16: two additions for REV-1027, additions only; status untouched.
      - A6 (REV-1027 F2): the 0.16 migration resolves a legacy name by title first and, failing that, by an operator's slug, because the released 0.15.0 writer wrote an operator without `full_name` as its slug (`- [ts] op-ann:`). A dated note under decision 4 points to it. A6 is part of the pending amendment and is subject to op-pierre's confirmation together with A1 to A5.
      - Note under decision 4 (REV-1027 F7): the header rewrite replaces whole header lines in the raw bytes, keeping each line's terminator, with `_sections.find_markers` used only to locate regions; reason: byte preservation and header-line-only edits, which `_sections.py`'s whole-region API does not give.
      - @manager for op-pierre's confirmation of A1 to A6; once confirmed, A6 goes to @python-dev with REV-1027 F2.
- [2026-10-16T11:16:25Z] `op-pierre` Pierre Chat:
  - 2026-10-16: confirmed the amendment A1–A6 as drafted (A1 operator slugs op-…; A2 one author namespace, skills excluded; A3 roster_slug_valid check; A4 the 0.16 migration refuses a non-conforming operator slug; A5 --as squads refused everywhere; A6 slug fallback when no title matches).
- [2026-10-16T11:53:31Z] `architect` Robert Architect:
  - - 2026-10-16: two additions for REV-1055, additions only; status untouched.
      - Note under A3 (F5): `roster_slug_valid` is squad-global, always on at a fixed `error`, not selectable; "on by default" reads as "always on". Reason: an identity check, and selectable squad-global rules would be an engine change.
      - A7 (F7): role activation and skill creation refuse a slug equal to a group verb of `sq role` (`catalog`, `list`, `activate`) or `sq skill` (`add`), read from the registered commands; `roster_slug_valid` also reports an entry that already holds one; the 0.16 migration does not refuse on it.
      - @manager A7 needs op-pierre's confirmation, as A6 did: it changes what an adopter may name a project role or skill.
- [2026-10-16T11:56:42Z] `op-pierre` Pierre Chat:
  - 2026-10-16: confirmed A7 (roles and skills refuse a slug equal to their group's verbs, like operators).
- [2026-10-17T02:01:31Z] `architect` Robert Architect:
  - 2026-10-17: two dated notes owed under ADR-1013 (The append-only statement), from TASK-1079 ST14; body and status untouched.
    - **Context, first sentence** ("Discussion comments are append-only history: there is no verb that edits or deletes one"). Since ADR-1013, a comment can be edited and removed by its author through `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove`, and the same on `sq skill|role|operator <addr>`. What this decision relied on still holds: a comment is a timestamped record, only its author (matched by slug, ADR-1013 §9 and A5 here) can change it, and an edit keeps its timestamp, slug and display-name snapshot (§3).
    - **§2, the header grammar.** The header gains one optional group inside the brackets, after the timestamp: ``- [<ts>, edited <ts>] `<slug>` <name>:``. It records the last edit only: a second edit replaces the mark, it never stacks. It is not a hash input and needs no migration; the 0.16 header migration writes no mark. `--json` carries it as `edited_ts` (null when never edited).
- [2026-10-25T21:42:26Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. A1-A7 and the REV-1027/1055 notes folded into 2a-2c and 4 (operator op- grammar, author namespace, roster_slug_valid, group-verb slugs, migration as built), the ADR-1013 edit mark folded into the grammar, append-only context corrected.
<!-- sq:discussion:end -->
