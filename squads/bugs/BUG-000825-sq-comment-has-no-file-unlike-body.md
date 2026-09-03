---
id: BUG-825
sequence_id: 825
type: bug
title: sq comment has no --file, unlike body
status: Verified
author: qa
refs:
- MILE-836:targets
created_at: '2026-08-26T10:53:19Z'
updated_at: '2026-09-01T08:05:20Z'
---
<!-- sq:body -->
## Description

`sq <type> <n> comment` and `sq <type> <n> <kind> <k> comment` (sub-entity comments)
accept only `-m/--message`. Neither has a `--file` option. `body` has `--file` at both
the item level and the sub-entity level.

## Current behaviour

Passing `--file` to either comment command fails cleanly — it is not silently ignored:

```
$ sq review 817 finding 8 comment --as tech-lead --file /dev/null ; echo $?
Usage: sq review N finding N comment [OPTIONS]
No such option: --file
2
```

Confirmed directly (not through a pipe): exit code is `2`, the `No such option: --file`
panel goes to stderr, stdout is empty. Same result at the item level
(`sq <type> <n> comment --file …`). `--help` on both comment commands lists only
`-m/--message` and `--as`; `--help` on both body commands lists `-m/--message` and
`--file`.

## Why the asymmetry matters

Every comment has to go through `-m`, and an unescaped backtick inside a double-quoted
`-m` argument is shell-substituted before `sq` ever sees it — the shell runs the
enclosed text as a command and splices its output in, silently changing the stored
text. `sq check` passes afterward because the markers and structure are untouched;
nothing in `sq` detects the loss.

Reproduced in a scratch squad: a comment authored with

```
-m "run the `sq check` command to verify unescaped"
```

(backticks unescaped, in a double-quoted arg) was stored as:

```
run the ✓ no issues command to verify unescaped
```

`sq check` ran as a side effect of shell parsing and its own output ("✓ no issues")
replaced the literal text "sq check" in the comment. `sq check` on the squad afterward
reported clean — nothing flags the corruption. `body` already has `--file`, which sidesteps
this whole class of bug for body text; comments have no equivalent escape hatch, which
pushes every long or code-bearing comment through the one path that can silently lose or
alter content.

## Open question

Whether `-m` and `--file` should be mutually exclusive on `comment` the way `body` treats
them is a design call for whoever picks this up — not decided here.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T11:25:43Z] Olivia Lead:
  - Fix task authored: TASK-826 (Ready), linked by a fixes ref. It settles the open question in this report: -m and --file mutually exclusive, mirroring body; --file - reads stdin; a file is one comment (one bullet, fences preserved), not split into bullets.
- [2026-08-26T13:05:44Z] Catherine Manager:
  - Fixed by TASK-826: comment takes --file at both levels, an empty file is refused rather than storing a blank bullet, and the generated agent guidance now points at --file with the shell-substitution reason. Driven: a fenced block round-trips byte-for-byte through --file while the same text through -m still substitutes.
- [2026-09-01T07:27:46Z] Mara Tester:
  - Verified in a scratch squad (nested under scratchpad, not this repo). Driven: --file works at item level (exit 0) and sub-entity level (exit 0); -m+--file together refused cleanly with 'error: provide the comment via -m or --file, not both' (exit 1, both levels — no raw Typer panel); neither given refused cleanly with 'error: provide the comment via -m ... or --file ...' (exit 1, both levels); an empty and a whitespace-only file both refused with 'error: --file must not be empty' (exit 1) and stored no blank bullet (confirmed via --json discussion listing).
  - Drove the actual hazard: a fenced code block containing literal backticked `sq check` text, through --file, read back via --json and diffed byte-for-byte against the source file (Python diff after stripping the bullet/indent wrapping) — exact match. Contrast check: the same text through -m still gets shell-substituted (backticks executed, text silently altered) — confirms --file is the real fix for the defect, not just a flag addition.
<!-- sq:discussion:end -->
