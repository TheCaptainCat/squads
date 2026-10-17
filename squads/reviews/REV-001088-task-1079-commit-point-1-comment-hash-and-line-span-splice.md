---
id: REV-1088
sequence_id: 1088
type: review
title: 'TASK-1079 commit point 1: comment hash and line-span splice'
status: Requested
author: reviewer
refs:
- TASK-1079
subentities:
- local_id: F1
  title: replace_section and append_to_section corrupt CRLF regions; fix in _sections.py,
    not a bypass
  status: Open
  severity: medium
- local_id: F2
  title: replace_comments trusts Comment.span; spans from a stripped or stale region
    splice the wrong lines
  status: Open
  severity: medium
- local_id: F3
  title: Two line-splitting rules now coexist; ST9 hit mapping and legacy line reports
    must use one
  status: Open
  severity: low
- local_id: F4
  title: Stale comment in format_comment and a docstring missing the edit mark
  status: Open
  severity: low
- local_id: F5
  title: Splice table pins LF and CRLF only; add lone-CR and mixed-terminator rows
  status: Open
  severity: low
created_at: '2026-10-17T01:09:55Z'
updated_at: '2026-10-17T01:11:15Z'
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
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T01:11:15Z] Paul Reviewer:
  - Five findings: F1 medium (CRLF in replace_section/append_to_section, confirmed by probe; fix in _sections.py rather than bypassing it in ST5), F2 medium (replace_comments trusts spans; spans from a stripped or stale region corrupt silently), F3-F5 low.
  - Recommended verdict: approve ST1/ST2 to commit once F4 and F5 are fixed. F1 and F2 must be fixed before ST5 writes through the splice. F3 is due before ST5 (legacy-line report) and ST9 (hit-to-hash mapping). @python-dev @manager
<!-- sq:discussion:end -->
