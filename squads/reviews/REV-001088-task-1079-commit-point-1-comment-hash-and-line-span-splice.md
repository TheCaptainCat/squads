---
id: REV-1088
sequence_id: 1088
type: review
title: 'TASK-1079 commit point 1: comment hash and line-span splice'
status: Approved
author: reviewer
refs:
- TASK-1079
subentities:
- local_id: F1
  title: replace_section and append_to_section corrupt CRLF regions; fix in _sections.py,
    not a bypass
  status: Verified
  severity: medium
- local_id: F2
  title: replace_comments trusts Comment.span; spans from a stripped or stale region
    splice the wrong lines
  status: Verified
  severity: medium
- local_id: F3
  title: Two line-splitting rules now coexist; ST9 hit mapping and legacy line reports
    must use one
  status: Verified
  severity: low
- local_id: F4
  title: Stale comment in format_comment and a docstring missing the edit mark
  status: Verified
  severity: low
- local_id: F5
  title: Splice table pins LF and CRLF only; add lone-CR and mixed-terminator rows
  status: Verified
  severity: low
- local_id: F6
  title: Retired-author refusal lives only in the CLI; edit_comment and remove_comment
    accept a retired slug
  status: Verified
  severity: low
- local_id: F7
  title: comment <hash> --help doubles the hash in its usage and names the argument
    hash_
  status: Verified
  severity: low
- local_id: F8
  title: AGENTS.md section teaches 'comment <hash> show ... --as', which show refuses
  status: Verified
  severity: low
created_at: '2026-10-17T01:09:55Z'
updated_at: '2026-10-17T02:12:53Z'
---
<!-- sq:body -->
## Scope

TASK-1079 ST1 and ST2, the pure discussion layer for comment hashes, checked against ADR-1013 §1, §2, §4, §7 and §8:

- `src/squads/_discussion.py`: `canonical_text`, `comment_hash`, `split_discussion` with `sequence_id` and scope, `short_hashes`, `resolve_hash`, the edit-mark header group, `legacy_header_lines` and `replace_comments`;
- the `split_discussion` callers in `_cli/_common.py`, `_services/_items.py`, `_services/_subentities.py`, `_services/_validators.py` and `_tui/_reader.py`;
- the new tests `tests/unit/test_comment_hash_and_prefix.py`, `tests/unit/test_comment_splice_by_line_span.py` and `tests/service/test_comment_hash_survives_a_retype.py`.

## What holds (driven unless marked)

- **Hashed bytes.** An independent SHA-256 over `sq-comment-1` NUL seq NUL scope NUL slug NUL ts NUL text reproduces the pinned vector. CRLF, lone CR and LF regions hash alike. The edit mark and the display name are not hash inputs.
- **Scope.** The sub-entity scope is `<kind>:<local_id>`, the same string as its discussion tag. The item and roster scope is empty (read).
- **Duplicates and short form.** Identical comments share one hash, `short_hashes` treats them as one, and `resolve_hash` returns the whole group. A wrong-scope prefix is refused with its address.
- **Retype.** The retype test goes red if a retype renumbers the item. The formatted id cannot reach the hash, because `sequence_id` is typed `int` (read).
- **Splice.** `replace_comments` is byte-exact for CRLF, lone CR and mixed terminators, at the first, middle and last position, and with a preamble, a folded legacy line, multi-line bodies and a replaced edit mark.
- **Callers.** Every `split_discussion` caller passes the item's `sequence_id`, and the sub-entity callers reuse `detail.comments`. Across the corpus, the rendered output changes for one comment only (F3).
- **Gates.** The touched tests pass (393), pyright on the touched files is clean, and ruff is clean.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1088 add-finding "…" --severity medium`; track with `sq review 1088 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — replace_section and append_to_section corrupt CRLF regions; fix in _sections.py, not a bypass

<!-- sq:finding:F1:body -->
**What (driven).** `_sections.replace_section` is not an identity on a CRLF region. Inner text read from a CRLF file starts with `\r\n`, which fails the `startswith("\n")` check, so the function prepends a bare `\n`. Probe: `replace_section(doc, DISCUSSION, get_section(doc, DISCUSSION)) == doc` is `True` for LF and `False` for CRLF. The CRLF result is the open marker followed by `\n\r\n- [...`: one stray LF blank line after the open marker on every write. An emptied CRLF region becomes `\n\r\n`. The same family exists in `append_to_section`: `format_comment` joins with LF and the snippet gets a bare `\n`, so every comment appended to a CRLF file today writes LF lines into it.

**Why it matters.** ADR-1013 §7 says the service writes the spliced region through `sections.replace_section`, and CLAUDE.md invariant 3 says file content is touched only through `_sections.py`. Having ST5 write the spliced text directly to get around the bug would break the invariant and leave the bug in place for every other caller.

**Fix.** Fix it in `_sections.py`: `replace_section` should take its padding terminator from the text (the one after the open marker, else the file's), and accept a `new_inner` that already starts or ends with `\r\n`. `append_to_section` should write the snippet with the file's terminator. Add an LF/CRLF/CR identity test (`replace_section(t, tag, get_section(t, tag)) == t`) and a CRLF append test. ST5 then calls `replace_section` as the ADR says.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-17T01:13:17Z] Elias Python:
  - Fixed in _sections.py: replace_section pads with the terminator after the open marker and accepts CR/CRLF edges; append_to_section writes the snippet in the section terminator. tests/unit/test_sections_keep_the_files_line_endings.py. Reverting the fix turns 12 of its 19 tests red.
- [2026-10-17T01:38:01Z] Paul Reviewer:
  - Verified (driven): replace_section is an identity on LF, CRLF and CR regions; an emptied region keeps one terminator; append_to_section writes the section's terminator. Note: the Service reads item files with universal newlines and writes LF, so this path is reached only by direct callers; the edit path is no worse than append (whole file goes LF, and the canonical text keeps every other comment's hash).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — replace_comments trusts Comment.span; spans from a stripped or stale region splice the wrong lines

<!-- sq:finding:F2:body -->
**What (driven).** `replace_comments(region, changes)` splices at `Comment.span` without checking that the span belongs to the `region` it is given. A span is valid only against the exact string that `split_discussion` parsed. Both service read paths parse a stripped region: `read_discussion` does `get_section(...).strip("\n")`, and so does `get_subentity_detail` (`detail.comments`). So their spans are one line off against the raw `get_section` inner that ST5 will write back.

Probe (`a`, `b` built by `format_comment`):

- I parsed `stripped = raw.strip("\n")`, then called `replace_comments(raw, [(cs[1], None)])` to remove `b`. The result is `\n- [...] \`a\` A:\n  - two\n`: `b`'s bullet now sits under `a`'s header and `a`'s own text is gone. Nothing raised.
- I parsed `raw`, then spliced a region where another comment had been appended above. Removing `a` deleted the other comment instead.

**Why it matters.** This is silent corruption of authored text, the one thing ADR-1013 §7's splice exists to prevent. The stale-hash refusal only protects a caller that re-resolves against the bytes it splices.

**Fix.** Make the pure function enforce this, so it does not rely on caller discipline. Either take `(hash, entry)` pairs and parse `region` itself, or check each change before splicing: the line at `span[0]` must be a header and the re-derived hash at that span must equal `cmt.hash`. Refuse on mismatch. Add a test that feeds spans from a stripped or older region and expects a refusal.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-17T01:13:18Z] Elias Python:
  - Fixed: replace_comments takes sequence_id/scope, re-parses the region and refuses (read it again) a change whose comment is not at its span with the same hash. Four stale-string rows plus a scope/item row; reverting the check turns 5 red.
- [2026-10-17T01:38:02Z] Paul Reviewer:
  - Verified (driven): spans parsed from a stripped region, and a sequence-number mismatch, are both refused with the read-again message; the service splices the same raw get_section string it parsed.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Two line-splitting rules now coexist; ST9 hit mapping and legacy line reports must use one

<!-- sq:finding:F3:body -->
**What (driven).** The discussion layer now splits lines on CR, LF and CRLF only (`_LINE_RE`). Other code still uses `str.splitlines()`, which also breaks on U+2028, U+2029, `\x0b`, `\x0c`, `\x1c`-`\x1e` and `\x85`:

- the search and inbox region scan (`_build_regions`, `_scan_comment_headers` in `_services/_collab.py`);
- `sections.region_lines`;
- the 0.16 header migration.

The narrower rule is right for the hash, because ADR-1013 §1 allows no change beyond CR/LF. But line numbers now disagree between surfaces on any file that holds one of those characters.

**Rendered output (driven).** Checked by parsing every discussion region in this corpus with the HEAD parser and with the new one, after rewriting legacy headers in memory: 3,541 regions and 4,456 comments. Exactly one comment differs, REV-1026's checkpoint comment. Its literal U+2028 used to render as a line break and now stays in the body. That is the more faithful output and needs no fix.

**Fix.** Before ST9 maps a hit's header line to a comment hash, and before ST5 reports `legacy_header_lines` as a file line, pick one line rule for those paths. That means the discussion rule, or an explicit offset translation. Add a row with a U+2028 in a comment body to the hit-to-hash test so the two cannot drift.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-17T01:29:59Z] Elias Python:
  - Fixed for the readers ST5 and ST9 use: sections.split_lines (CR, LF, CRLF) now backs region_lines, the search and inbox region scan and the discussion layer. 4 new rows (U+2028, form feed, VT, NEL) go red if region_lines reverts to str.splitlines. The 0.16 header migration still uses str.splitlines: the task says that file is not touched, so I left it. @manager rule if you want it changed.
- [2026-10-17T01:38:20Z] Paul Reviewer:
  - Readers verified (read): region_lines, the search and inbox scan and the discussion layer use sections.split_lines. Reopened for the manager's ruling that the 0.16 header migration moves to split_lines too; it still calls str.splitlines in _tally_file, _write_headers and _strip_eol.
  - Dry run (driven): copied this squad, then ran the dev build's migrate up, sync and check with -C. The migration rewrote 4,467 headers in 933 files and check is clean. The migration's _scan, run under str.splitlines and under split_lines over all 1,139 pre-migration files, gives identical events with 0 files differing, REV-1026 included. That scan was first checked on a known positive: a U+2028 with a header-shaped tail yields 2 events under splitlines and 1 under split_lines. So the move changes nothing in this corpus. The REV-1026 difference is on the reader side only.
- [2026-10-17T01:41:32Z] Elias Python:
  - Fixed: the 0.16 header migration reads lines through split_lines and strips only CR/LF. A separator inside a line no longer makes a header of the text after it; reverting the migration turns 4 new rows red.
- [2026-10-17T02:03:53Z] Paul Reviewer:
  - Verified. The migration's _tally_file, _write_headers and _strip_eol now use split_lines (read). The new separator rows for U+2028, form feed, VT and NEL pass. On a fresh copy of this squad, the dev build's migrate up, sync and check rewrote 4,484 headers in 933 files, and check is clean (driven).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Stale comment in format_comment and a docstring missing the edit mark

<!-- sq:finding:F4:body -->
**What (read).**

- `format_comment` still says "split as the readers do" over `msg.splitlines()`. The readers no longer split that way: the writer now splits on more characters than the parser. That is safe, since it can never put an author's line at column 0, but the comment is false. Reword it to state the reason, for example "split on every line break `str.splitlines` knows, so no line an author writes can land at column 0".
- `split_discussion`'s docstring gives the header as ``- [TIMESTAMP] `slug` Author:`` with no optional `, edited <ts>` group, which this change adds.

Both are one-line edits in `src/squads/_discussion.py`.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-17T01:13:19Z] Elias Python:
  - Fixed: format_comment comment and split_discussion docstring. No behavior, no test.
- [2026-10-17T01:38:02Z] Paul Reviewer:
  - Verified (read).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Splice table pins LF and CRLF only; add lone-CR and mixed-terminator rows

<!-- sq:finding:F5:body -->
**What (read, then driven).** The position-by-shape splice table in `tests/unit/test_comment_splice_by_line_span.py` crosses LF and CRLF only. The canonicalisation table covers a lone CR, but the splice does not. I probed these cases outside the suite, and all were byte-exact:

- lone-CR removal at the first, middle and last position;
- a mixed file (CRLF header, LF body, LF neighbours) for both edit and removal;
- a region where a legacy header is folded into the comment above it;
- a whitespace-only trailing line.

None of them is pinned by a test, so a later change to `_LINE_RE` or to the terminator logic in `replace_comments` would go unnoticed.

**Fix.** Add `"cr": "\r"` to `EOLS`, and add one mixed-terminator row asserting that the replaced comment takes its header's terminator while its neighbours keep theirs byte-for-byte.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-17T01:13:20Z] Elias Python:
  - Fixed: cr added to the splice table and two mixed-terminator rows. Narrowing the line rule to LF turns 114 red.
- [2026-10-17T01:38:04Z] Paul Reviewer:
  - Verified (read, and the targeted suite passes).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Retired-author refusal lives only in the CLI; edit_comment and remove_comment accept a retired slug

<!-- sq:finding:F6:body -->
**What (driven).** A retired author is refused only in the CLI (`resolve_actor_or_raise` in `_cli/_common.py`). Probe on a scratch copy: after archiving `tech-writer`, `sq task N comment <hash> edit --as tech-writer` exits 1 with "is retired". But `Service.edit_comment(..., as_slug="tech-writer")` called directly succeeds and writes the edit. `remove_comment` has the same shape.

**Judgement.** The CLI is the wrong home for this half of the rule. ADR-1013 §9 states the author match and the retired-author freeze as one rule, yet the author match lives in the service (`_require_comment_author`) and the freeze lives in the CLI. Any other service caller, such as the TUI or a future import op, gets one half without the other. It matches how append works today (`svc.comment` does not check either), so it is not a regression, which is why this is low.

**Fix.** Resolve the live slug inside `edit_comment` and `remove_comment`, next to `_require_comment_author`, through the same roster lookup the CLI uses. Add a service-level refusal row for a retired author. Moving the append check as well is optional, and could be its own cleanup.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-17T01:41:33Z] Elias Python:
  - Fixed: edit_comment and remove_comment resolve the live author in the service (retired and unknown slugs refused). Removing the check turns 2 new rows red; the direct-service rows also cover a name given as the slug.
- [2026-10-17T01:43:17Z] Elias Python:
  - Correction: removing the service-level live-author check turns 3 tests red (the 2 new retired rows and the name-as-slug row).
- [2026-10-17T02:03:55Z] Paul Reviewer:
  - Verified (read, and the tests pass). edit_comment and remove_comment call _require_live_author before the lock: a retired slug is refused with the reactivate hint, and an unknown slug is refused too. The retired rows for edit and remove assert the file bytes are unchanged.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — comment <hash> --help doubles the hash in its usage and names the argument hash_

<!-- sq:finding:F7:body -->
**What (driven).** `sq task N comment <hash> --help` prints the usage `sq task N comment <hash> [OPTIONS] HASH COMMAND [ARGS]...`, so the hash token appears twice. Its Arguments table names the argument `hash_`, which is the Python parameter name leaking through. `comment --help` itself is good: it describes both the append form and the `HASH show|edit|remove` form.

**Fix.** Set the hidden `_addr` group's name, or the `options_metavar`/usage, so the usage reads `sq task N comment HASH COMMAND [ARGS]...`, and give the argument a display name of `HASH`. Add a help-text assertion at item and sub-entity level, under REV-958's help-surface rules.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-17T01:41:34Z] Elias Python:
  - Fixed: usage reads "comment HASH COMMAND [ARGS]..." and the argument is named hash. Reverting the display name turns 2 new help rows (item and sub-entity) red.
- [2026-10-17T02:03:57Z] Paul Reviewer:
  - Reopened. The group usage is fixed: comment a1b2c3d --help reads 'comment HASH COMMAND [ARGS]...'. The leaf verbs still repeat the hash (driven): 'sq task N comment HASH HASH show [OPTIONS]', and the same for edit and remove, at item and roster level ('sq role <slug|id|n> ADDR comment HASH HASH edit'). The Arguments table now names the argument 'hash TEXT': metavar HASH is lost there. Fix the leaf usage too (for example, have CommentGroup return the real token or an empty name, so the hash group's own usage piece is not repeated), and add a leaf --help row.
- [2026-10-17T02:08:36Z] Elias Python:
  - Reopened and fixed: each verb reads "comment HASH show [OPTIONS]" (the group drops its own argument from child usage paths) and the table keeps a HASH column. Reverting turns 9 tests red (verb usage item/sub-entity, roster, hash help).
- [2026-10-17T02:08:41Z] Elias Python:
  - Correction: reverting the usage fix turns 7 tests red, not 9.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — AGENTS.md section teaches 'comment <hash> show ... --as', which show refuses

<!-- sq:finding:F8:body -->
**What (driven).** `agents_md/agents_section.md.j2` line 47, and therefore `tests/goldens/agents_md_section.txt` line 296, teaches:

`sq <type> 3 comment <hash> show|edit|remove --as <your-slug>`

`show` takes no `--as`. On a scratch squad, `sq task N comment <hash> show --as reviewer` exits 2 with "No such option: --as". So the AGENTS.md section teaches one of its three commands wrongly. The other templates get it right: `workflow.md.j2` shows `edit --as <your-slug> -m "…"`, and the squads skill and role guidance say `edit` and `remove` take `--as`.

**Fix.** Use the same form as the workflow cheatsheet, `sq <type> 3 comment <hash> edit --as <your-slug> -m "…"   # also show, remove`, or split the line into `show` and `edit|remove --as`. Regenerate the golden and the manifest, and add a row to `tests/cli/test_guidance_teaches_comment_hash_verbs.py` that runs each taught comment command shape, or at least asserts that `show` is never followed by `--as`.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-17T02:08:37Z] Elias Python:
  - Fixed: AGENTS.md template now lists "comment <hash> show" and "comment <hash> edit|remove --as <your-slug>" on separate lines; the other templates were already correct. Manifest regenerated, --check clean, rebuild dropped 1 orphan. Restoring the wrong line turns 7 tests red (golden, migrated-corpus, guidance).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T01:11:15Z] Paul Reviewer:
  - Five findings: F1 medium (CRLF in replace_section/append_to_section, confirmed by probe; fix in _sections.py rather than bypassing it in ST5), F2 medium (replace_comments trusts spans; spans from a stripped or stale region corrupt silently), F3-F5 low.
  - Recommended verdict: approve ST1/ST2 to commit once F4 and F5 are fixed. F1 and F2 must be fixed before ST5 writes through the splice. F3 is due before ST5 (legacy-line report) and ST9 (hit-to-hash mapping). @python-dev @manager
- [2026-10-17T01:11:54Z] Catherine Manager:
  - Rulings: F1 fix replace_section and append_to_section in _sections.py to keep the file's line endings (no bypass). F2 verify header and hash at each span before splicing, refuse on mismatch. F3 one splitting rule everywhere: CR, LF and CRLF only (search, region_lines, migration), in the subtask that first needs it. F4, F5 fix.
- [2026-10-17T01:38:34Z] Paul Reviewer:
  - Commit point 2 (2a16e94b), all driven on a scratch copy of this squad. Grammar: comment HASH show|edit|remove works at item, sub-entity, role and system-skill level. A bare hash exits 2 at every level. A misplaced -m before the hash exits 2 and appends nothing. A short or non-hex token exits 2 and names -m. A wrong-scope hash is refused and the message names the right address.
  - Edit: the author is matched by slug, not by display name. A header whose display name equals another slug still refuses that slug and accepts the real one. reject_markers runs on the new text. A no-op edit leaves the file byte-identical. The mark follows the ADR-1013 grammar, and a second edit replaces it instead of adding one. A stale hash is refused afterwards. A legacy line in any discussion of the item refuses both edit and remove, names the correct file line, and writes nothing. The legacy anonymous `operator` slug can edit its own comments.
  - Remove: a wrong author is refused. Declining the prompt exits 1 with the file untouched. Only the comment lines and updated_at change. JSON: comments --json, show --json (item and sub-entity), comment show --json and the goldens gain exactly edited_ts, hash and short_hash. The show record adds item, scope and copies. sq check and repair are clean afterwards.
  - Judgements. CRLF: no finding. The Service reads item files with universal newlines and writes LF, so the edit path converts a CRLF file exactly as append already does, and the canonical text keeps every other comment hash stable. Sub-entity comments verb: no gap. FEAT-1017 keeps `comments` unchanged, and a sub-entity discussion is listed with hashes by show --comments and show --json. Retired authors: F6, low.
  - F1, F2, F4 and F5 are Verified. F3 is reopened only for the migration ruling; the dry run shows no change in this corpus. F6 and F7 are low. Targeted tests pass: 1,016. Recommended verdict: approve, with F3, F6 and F7 to fix before the next commit point. @manager @python-dev
- [2026-10-17T02:04:11Z] Paul Reviewer:
  - Commit point 3, checked on a fresh migrated copy of this squad. Duplicates (driven, with --at): the same text in the same second and scope is refused, at item and sub-entity level, and so is a variant with trailing spaces. The same text in the item and in two subtasks is accepted, each with its own hash. An edit that would equal an existing comment is refused. An import holding two identical comments is refused whole and writes nothing (read: the import test, under the single-write hold).
  - Reflog (driven): one comment_edit line and one comment_remove line per change. Each delta is {comments: [{author, hash, region, ts, before}]}, and the edit adds after_hash. A no-op edit and a refused edit write no line. sq reflog --json parses.
  - Hash surfaces (driven): search hits carry hash, null in a body or title. A hit on a comment continuation line, and a hit in a sub-entity discussion, both carry the hash that comments --json and subtask show --json report. Inbox hashes run parallel to lines and regions. The raw, plain, sub-entity and TUI renders put the short hash first. JSON goldens gain only hash and hashes; text goldens change only by the leading short hash and the new guidance.
  - The migrate test strips only hash and hashes, and only from our output, before comparing with the released-tool reference: legitimate, since every other key is still compared and the hashes are pinned elsewhere. Guidance: no ticket ids, and the grammar is correct apart from the AGENTS.md show --as line (F8). F3 and F6 are Verified. F7 is reopened because the leaf verb usage still doubles HASH. The 825 targeted tests pass, including tests/meta, where the reflog op-table test already passes.
  - Recommended verdict: Approved. Only F7 and F8 remain, both low and both local help or guidance text. @manager @python-dev
- [2026-10-17T02:12:53Z] Catherine Manager:
  - Approved: F1-F6 verified by the reviewer; F7 and F8 fixed with falsified tests; full suite 13169 passed, 0 failed.
<!-- sq:discussion:end -->
