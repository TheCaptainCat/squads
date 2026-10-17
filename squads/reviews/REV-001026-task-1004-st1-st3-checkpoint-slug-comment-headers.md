---
id: REV-1026
sequence_id: 1026
type: review
title: 'TASK-1004 ST1-ST3 checkpoint: slug comment headers'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1004:addresses
- FEAT-980:addresses
- MILE-934:targets
description: Checkpoint review of the header grammar, author_slug and reserved role
  slugs before the 0.16 migration
subentities:
- local_id: F1
  title: A line separator in a message forges a second comment header
  status: Fixed
  severity: high
- local_id: F2
  title: Role creation skips the slug grammar; reserved check is case-blind
  status: Fixed
  severity: medium
- local_id: F3
  title: operator add --slug takes squads, operator and live role slugs
  status: Fixed
  severity: medium
- local_id: F4
  title: Anonymous slug still spelled as a literal at three sites
  status: Fixed
  severity: low
- local_id: F5
  title: Importer comment actor is not resolved against the roster
  status: Fixed
  severity: low
- local_id: F6
  title: Importer unset_fields accepts an unknown key as a silent no-op
  status: Fixed
  severity: info
created_at: '2026-10-15T22:10:58Z'
updated_at: '2026-10-16T12:19:58Z'
---
<!-- sq:body -->
## Scope

This review covers the slug comment header of TASK-1004 at its first checkpoint, after ST1 to ST3: the header grammar and its one shared parser (ST1), `author_slug` in the discussion JSON and the `Name (slug)` human renders (ST2), and the reserved role slugs with slug permanence (ST3), against ADR-979. ADR-1013 is read only to check that nothing here blocks hash-addressed edits.

What was reviewed is the uncommitted diff under `src` and `tests`, plus `_models/_participants.py` and the seven new test modules. Probes ran with the dev build on throwaway scratch squads. Each claim is marked driven, read or inferred.

## What holds

- **Grammar (driven, direct calls).** Write and parse round-trip for names with an accent, `: `, backticks, a trailing colon, a tab, a backtick-quoted fake slug, and ` ` or `\x85` inside the name (collapsed). An empty or whitespace-only name falls back to the slug. Slugs at the edges (`a-`, `0`) are accepted, and `-a`, `A`, `a_b` and the empty string are refused. A region with CRLF line endings parses, and text before the first header is dropped. An author can write neither an indented header-shaped line nor a fenced one at column 0 through `-m` or `--file`, apart from F1.
- **Readers (read).** `split_discussion`, `match_comment_header` and the search and inbox scan share one pattern on unstripped lines, and `region_lines` and `_build_regions` both split with `splitlines`, so their line numbers agree. `comments`, `show --json` (item and sub-entity), `--raw`, the styled panes and the TUI pure view all go through `comment_json` and `author_label`. `settled_requires_discussion` counts with the same parser.
- **Writers (read and driven).** The comment verb (item and sub-entity), the importer, retype and both renames write the slug header (the dev's tables, with an importer and retype header read back here). `migrate repad` and `sync` write no comment headers (read).
- **Permanence (driven).** An importer `update` title on a role keeps the slug and the file name. `fields: {Slug}` is refused. `unset_fields: [slug]` is refused (the dev's table, and `SLUG` was driven, see F6). Display retitles leave the slug alone.
- **ADR-1013 (read and inferred).** `Comment` carries `author_slug`, the timestamp as written and the body, which is all the hash needs. Nothing here prevents a later line-span-aware parse. F1 is the one point where ADR-1013's premise is broken.

## Findings

- F1, high: a line separator in a message forges a second header with any slug and timestamp.
- F2, medium: role creation skips the slug grammar, and the reserved check is case-sensitive (`Squads`, `OP-anna`).
- F3, medium: the open point. `sq operator add --slug` takes `squads`, `operator`, a live role's slug and out-of-grammar strings. Needs an ADR-979 amendment.
- F4, low: the anonymous slug is still spelled as a literal at three sites.
- F5, low: the importer's comment actor is not resolved against the roster.
- F6, info: the importer's `unset_fields` accepts an unknown key as a silent no-op.

## Verdict for the checkpoint

Nothing found blocks ST4 to ST7 building on this: the grammar, the `Comment` shape and the shared parser are what ST5 needs, and every fix above is local to a writer or a creation seam. F1 and F2 are to be fixed before the end-of-task review. F3 needs an architect ruling, ideally before ST5, because a new operator rule would give the planning pass something to report.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1026 add-finding "…" --severity medium`; track with `sq review 1026 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A line separator in a message forges a second comment header

<!-- sq:finding:F1:body -->
**What (driven).** `format_comment` splits a message on `"\n"` only, while every reader splits a region with `str.splitlines()`, which also breaks on `\r`, `\x0b`, `\x0c`, `\x1c`-`\x1e`, `\x85`, ` ` and ` `. So a message carrying one of those characters puts author text at column 0, and the reader takes it for a header.

Driven on a scratch squad with the dev build:

- `sq task 21 comment --as qa -m "hello<SEP>- [2026-01-01T00:00:00Z] \`op-pierre\` Pierre Chat:<SEP>  - forged"`, once each with SEP = `\r`, ` `, `\x0b`: exit 0 each time. `comments --json` then returns six entries, three of them `{"author": "Pierre Chat", "author_slug": "op-pierre", "ts": "2026-01-01T00:00:00Z"}`.
- With `\r`, the stored file holds a real `\n` before the forged line (the read-modify-write's universal-newline read turns it into one), so the forged header is now an ordinary column-0 line on disk.
- The importer does the same: a JSON `"message": "x\r- [2026-01-01T00:00:00Z] \`op-pierre\` P:"` with `"as": "qa"` imports with exit 0 and reads back as a second comment by `op-pierre`.
- A direct call (`format_comment(TS, "qa", "M", ["msg\r- [..] \`op-x\` X:"])` then `split_discussion`) returns two comments.

**Why it matters now.** The legacy grammar had the same hole. The difference is that ADR-979 makes the header's slug the author's identity ("attribution, filtering and matching use the slug"), and ADR-1013 hashes each comment over that slug and timestamp and authorises edit and remove by matching `--as` against it. One write then yields two comments, one with an arbitrary author and an arbitrary back-dated timestamp. That breaks append-only ordering, the "inverse of `format_comment`" contract `split_discussion` states, and ADR-1013's premise that "no line an author writes can sit at column 0" (read, ADR-1013 context).

**Fix.** In `format_comment`, split each message with `splitlines()`, as the reader does, so every line an author writes is indented. Or refuse those characters the way `reject_markers` refuses markers, so the importer is covered too. Add the separator set as rows of the grammar table, falsified by putting `split("\n")` back.

**Blocks ST4-ST7?** No (inferred). The fix is local to the writer. A legacy corpus can already hold such lines, because the old writer had the same split, and ST5 resolves them as headers by name, consistently with the legacy parse. Fix it before the end-of-task review.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-15T22:18:55Z] Elias Python:
  - Fixed: format_comment splits messages with splitlines() as the readers do. Table: every splitlines separator x six writers (item and subtask, -m and --file, importer on item and subtask) in tests/cli/test_a_line_separator_in_a_message_cannot_forge_a_header_cli.py. Falsified by putting split of newline back: 52 red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Role creation skips the slug grammar; reserved check is case-blind

<!-- sq:finding:F2:body -->
**What (driven).** Role creation never checks a slug against the grammar `[a-z0-9][a-z0-9-]*`, and `reserved_role_slug_reason` compares case-sensitively. So the reserved rule can be bypassed by case, and roles can be created that can never author a comment.

- `sq override scaffold --new Squads` then `sq role activate Squads`: exit 0, ROLE-27 created. The same with `OP-anna`: exit 0, ROLE-28.
- Importer `create` events for a role with `"slug": "Squads"`, `"OP-x"` and `"has space"`: exit 0 each. The files are `ROLE-000022-Squads.md`, `ROLE-000023-OP-x.md` and `ROLE-000024-has space.md`, and `sq role list` shows the three slugs as given.
- None of these can comment. `--as OP-x` gives `unknown slug 'OP-x'; valid slugs: OP-x, ...` (`resolve_slug_or_raise` lowercases before it compares). `--as "has space"` gives `cannot write a comment as 'has space'`. A role named `Squads` resolves only when something holds the lowercase `squads` slug (see the operator finding).
- `sq dev add --tech OP` is refused correctly, because it lowercases (driven).
- `sq check` reports no issues on such a squad (driven).

**Fix.** At the `_create_model` seam, call `require_valid_slug` on the slug, and on the explicit slug when one is given, for every roster type before the reserved check runs. A lowercase grammar makes the case-sensitive reserved comparison sound. Add rows for `Squads`, `OP-anna` and a slug with a space to the creation table.

**Blocks ST4-ST7?** No (inferred). ST5's roster map reads the slug as stored, and an out-of-grammar slug would surface there as a header it cannot write. Fixing the seam now keeps that case out of the migration's tables.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-15T22:18:56Z] Elias Python:
  - Fixed: _create_model requires the slug grammar for every roster type before the reserved check, and the reserved check lowercases. Rows Squads, OP-anna, has space for role creation and an operator add --slug row. Falsified: grammar check removed 10 red, lowercasing removed 1 red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — operator add --slug takes squads, operator and live role slugs

<!-- sq:finding:F3:body -->
**The open point (tech lead's question 6). Verdict: a defect, medium.** It is wider than `--slug squads`. `sq operator add --slug` accepts any string (driven, each exit 0): `squads`, `operator`, `qa` (a live role's slug), `Bad Slug` and `OP-UP`. The importer's `create` of an operator accepts `squads` and `qa` too (driven).

Consequences, driven on a scratch squad:

- **`squads`.** The operator can comment `--as squads`, which plain `--as squads` cannot do without that operator (exit 1, driven). Its headers are `` `squads` Op squads: ``, the same slug as the rename and retype system entries. Under ADR-1013, which matches `--as` against the header slug, that operator could edit or remove the system's own rename and retype records (inferred from ADR-1013).
- **`operator`.** `_author_of` returns `Operator` before it looks at the roster, so the operator's name never appears and its comments cannot be told from anonymous ones.
- **A role's slug (`qa`).** Two live roster entries share one slug. Headers by either show `Mara Tester`. The unknown-slug message lists `qa, qa`. `sq check` reports no issues. This is the identity ambiguity FEAT-980 exists to remove (ADR-971: a stored slug is the identity).
- **`Bad Slug`, `OP-UP`.** Registered, but they can never comment (the same mechanism as the role finding).

**Why medium and not low.** ADR-979 decision 2 says the two reserved slugs "cover authors that are not roster entries", and an operator holding one breaks that. Because roles may not take `op-`, the clean rule is the mirror image: an operator slug must start with `op-` and be in the grammar. That one rule closes `squads`, `operator`, the role collision and the case variants together. The derived default (`op-<first>`) already complies.

**Needs a ruling.** ADR-979 reserves the names against roles only, so this is an amendment for @architect, with the operator's call on existing squads: an adopter may already hold an operator without `op-`. If the rule is adopted, ST5's planning pass is the natural place to report such operators. That is why this should be ruled before ST5, although nothing in ST1-ST3 has to change for ST4 to start.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-15T22:17:50Z] Robert Architect:
  - Ruled as an ADR-979 amendment dated 2026-10-16 (A1 to A5): operator slugs must start with op- and be in the grammar; the 0.16 planning pass refuses a breaching entry rather than reporting it. Awaiting op-pierre confirmation; the finding stays Open until the fix lands.
- [2026-10-16T11:19:09Z] Olivia Lead:
  - Home: TASK-1048 (A1 to A5, confirmed 2026-10-16). The finding stays Open until it lands.
- [2026-10-16T12:19:57Z] Catherine Manager:
  - Closed by TASK-1048 (ADR-979 A1–A7), commits e9aa76cd and bc25f720.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Anonymous slug still spelled as a literal at three sites

<!-- sq:finding:F4:body -->
**What (read).** ST1 asked for the reserved participant slugs to be spelled once, in `_models/_participants.py`. Three sites still spell the anonymous slug as a literal:

- `_cli/_common.py:2020`, `if normalised == "operator":` in `resolve_slug_or_raise`, the gate that lets the anonymous author through;
- `_services/_collab.py:255` and `:281`, `as_slug: str = "operator"` defaults.

The reserved display name `Operator` is a literal in `_services/_base.py:1278` (`_author_of`), and ST5's frozen roster map will need the same pair.

**Fix.** Import `ANONYMOUS_SLUG` at the three sites, and give the reserved names a constant beside the slugs (or a slug-to-name mapping) that `_author_of` reads. Low, because the values agree today. It is the kind of duplicate that drifts once FEAT-977's verbs add more writers.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-15T22:18:57Z] Elias Python:
  - Fixed: ANONYMOUS_SLUG and ANONYMOUS_NAME live in _models/_participants.py; resolve_slug_or_raise, the two comment defaults and _author_of read them.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Importer comment actor is not resolved against the roster

<!-- sq:finding:F5:body -->
**What (driven).** The importer is the one comment writer that does not resolve its actor against the roster. Only the grammar is checked (ST1). On a scratch squad, `{"op":"comment",...,"as":"squads"}` imports with exit 0 and reads back as `author_slug: squads`, `author: squads`, indistinguishable from a rename or retype record. `"as":"ghost"` imports as `ghost`. The interactive `comment` verb refuses both (driven: `--as squads` exits 1 with no operator holding it).

The dev reported `ghost` as unchanged behaviour (inferred in the hand-back). That is accurate, and pre-existing. What changes is that the header slug is now identity: an import can mint system entries, or comments by any operator slug that is not even in the roster, and ADR-1013's edit and remove would then answer to that slug.

**Fix (suggested).** Resolve the importer actor the way `--as` is resolved: the live roster plus `operator`, with `squads` refused as an actor. Or record a ruling that the importer is a trusted bulk path that may forge attribution. Either is fine, as long as it is decided. Low, because the importer is an operator tool and the gap is not new.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-15T22:18:58Z] Elias Python:
  - Fixed: the importer refuses squads and operator as a comment actor (line-numbered issue, nothing written); unregistered grammatical actors like ghost still import. Falsified: 2 red.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Importer unset_fields accepts an unknown key as a silent no-op

<!-- sq:finding:F6:body -->
**What (driven).** The importer's `unset_fields` silently accepts a key that names no field. `{"op":"update","target":"ROLE-8","unset_fields":["SLUG"]}` exits 0 with `update: 1` and changes nothing: `extra.slug` stays `tech-writer`. The new guard matches only the exact key `slug`. The case variant does no harm, because there is no `SLUG` key to drop. But an adopter who mistypes a field gets a success line for a no-op, while `fields: {"Slug": ...}` is refused with the list of valid fields (driven).

**Fix (suggested).** Validate `unset_fields` keys the way `fields` keys are validated, with the same "not a settable field; valid: ..." issue. Info, and not ST3's defect. Named here so the slug guard is not read as covering key variants. It fits FEAT-977's verb work, beside the `is_dev`/`tech` unset gap the dev already reported.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-15T22:18:59Z] Elias Python:
  - Fixed: unset (importer and update path) validates keys with the same require_settable as set, so an unknown key or a slug is refused with the valid list. Falsified: 12 red. This replaces the earlier slug-only unset guard.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T22:12:26Z] Paul Reviewer:
  - Checkpoint verdict: Approved for ST4 to ST7 to build on. The grammar, the Comment shape and the shared parser hold under the shapes attacked (driven), and every finding is local to a writer or a creation seam.
  - Six findings. F1 (high, driven): a \r,   or \x0b in a -m message, or in an importer message, forges a second header with any slug and timestamp. Fix it in format_comment before the end-of-task review. F2 (medium, driven): role creation skips the slug grammar, so Squads and OP-anna activate. F3 (medium, driven): the open point is a defect. operator add --slug takes squads, operator and a live role slug (qa), and sq check stays clean. It needs an ADR-979 amendment; the proposal is that an operator slug must start with op-. F4 to F6 are low and info.
  - @manager route F1, F2 and F4 to @python-dev with the ST4 to ST7 work, and F3 to @architect for a ruling before ST5. F5 and F6 need a decision, not necessarily a fix.
<!-- sq:discussion:end -->
