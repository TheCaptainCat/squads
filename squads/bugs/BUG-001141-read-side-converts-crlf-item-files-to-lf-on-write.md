---
id: BUG-1141
sequence_id: 1141
type: bug
title: Read side converts CRLF item files to LF on write
status: Open
parent: MILE-1051
author: qa
priority: low
refs:
- BUG-1028
created_at: '2026-10-25T11:10:37Z'
updated_at: '2026-10-25T11:11:14Z'
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
<!-- sq:discussion:end -->
