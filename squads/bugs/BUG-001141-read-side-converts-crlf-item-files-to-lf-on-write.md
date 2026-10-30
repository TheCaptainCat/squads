---
id: BUG-1141
sequence_id: 1141
type: bug
title: Read side converts CRLF item files to LF on write
status: Verified
parent: MILE-1051
author: qa
refs:
- BUG-1028
created_at: '2026-10-25T11:10:37Z'
updated_at: '2026-10-26T06:46:40Z'
priority: low
---
<!-- sq:body -->
## Reproduction

Scratch squad, clean export of HEAD 091bfb77, Linux. Rewrite an item file to CRLF (every `\n` becomes `\r\n`, 43 CRLF, 0 bare LF), then make any write to it:

    sq task 21 comment --as qa -m "hi"      -> commented on TASK-21 as qa
    file bytes afterwards: 0 CRLF, 45 bare LF

## Expected

A write touches only the region it edits. Lines it did not touch keep their original endings, so a CRLF working copy (Windows checkout with autocrlf or an eol attribute) is not rewritten as LF by a one-line comment.

## Actual

`read_text` in `src/squads/_aio.py` uses `Path.read_text(encoding="utf-8")`, which applies universal-newline translation, so the whole file is read as LF and written back as LF. The write side now writes verbatim (newline=""), which is why the loss shows up on read, on every platform.

## Notes

Split out of the read-side note on the atomic-writer bug. Same effect on the index and managed regions if their files are CRLF. Whether section and frontmatter parsing tolerate a verbatim `\r\n` once the read side is fixed is untested.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T06:45:47Z] `qa` Mara Tester:
  - Verified on the dev build. Scratch squad, task file rewritten to CRLF (44 CRLF, 0 bare LF), then one write at a time:
    - comment (+2), body, status Ready, add-subtask (+16), subtask body, subtask comment, subtask update --status, subtask update --assignee: bare-LF count stayed 0 after every verb. `sq check` ok, `sq repair` leaves 63 CRLF / 0 LF, the comment text is present.
    - Mixed file (22 CRLF / 22 LF): a comment keeps the 22 CRLF and the existing 22 LF untouched; the two inserted lines take LF (tie goes to LF, per TASK-1147 ST1).
    - LF file stays LF (0 CRLF). CRLF CLAUDE.md with the managed region: `sq sync` leaves 126 CRLF / 126 lines, user text kept.
    - Not covered: a CRLF `.squads.json` is read fine but rewritten as LF by the next write (68 LF, 0 CRLF after a comment). It is a generated, rebuildable file, so I treat it as acceptable; flag it if you want it held to the same rule.
    Moving to Verified.
<!-- sq:discussion:end -->
