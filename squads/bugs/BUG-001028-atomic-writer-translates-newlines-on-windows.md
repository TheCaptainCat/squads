---
id: BUG-1028
sequence_id: 1028
type: bug
title: Atomic writer translates newlines on Windows
status: Verified
author: qa
priority: low
refs:
- REV-1027
- MILE-1051:targets
description: Text-mode open without newline='' alters line endings on Windows
created_at: '2026-10-16T07:42:11Z'
updated_at: '2026-10-25T11:12:04Z'
---
<!-- sq:body -->
## Mechanism (read from the code, not run on Windows)

`atomic_replace_sync` in `src/squads/_aio.py:96` opens its temp file with `tmp.open("w", encoding="utf-8")`. The default `newline=None` translates every `\n` to `os.linesep` on write. On native Windows that turns LF files into CRLF, and a `\r\n` already present in the text into `\r\r\n`.

`atomic_write_text` (`_aio.py:110`) wraps the same core, so every item `.md`, the index commit and the managed regions go through this one open. `write_text` (`_aio.py:70-76`, `path.write_text(..., encoding="utf-8")`) has the same default.

The read side is similar: `read_text` (`_aio.py:57`) uses `path.read_text(encoding="utf-8")`, which applies universal-newline translation on every platform. Whether a CRLF file survives on POSIX therefore depends on which readers feed the writer. This was not checked here.

## Impact

Line endings are not kept byte for byte on Windows. The release 0.16 comment-header migration rewrites every file that carries a comment (881 in this repository) through this writer. On Windows, LF files would be rewritten as CRLF and CRLF lines as `\r\r\n`, so the whole-file diff would not be header lines only. The CRLF claim in the migration MANUAL and its tests hold on POSIX only.

The problem predates the migration and applies to every sq write. Raised by review finding F9 of REV-1027.

## Suggested fix

- Pass `newline=""` to `tmp.open(...)` in `atomic_replace_sync` so the text is written verbatim, and to `write_text` (use `path.open("w", encoding="utf-8", newline="")`).
- Decide the read side deliberately: reading with `newline=""` keeps `\r\n` in memory, so check that the section and frontmatter code tolerates it.
- Add a test that writes text containing `\n` and `\r\n` and compares the bytes on disk. Run it on a Windows CI runner, or by monkeypatching `os.linesep`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:33Z] `tech-lead` Olivia Lead:
  - Write side no longer reproducible by reading release/0.17 HEAD: commit 0d389e5c passes `newline=""` to both `atomic_replace_sync` and `write_text` in `src/squads/_aio.py`, so text is written verbatim on every platform. Read side unchanged: `read_text` still uses `Path.read_text(encoding="utf-8")` (universal newlines), so a CRLF file read through it comes back as LF and is rewritten as LF. Not driven on Windows or POSIX.
  - @qa please judge whether the read-side normalisation is a defect of its own (new bug) or intended, and set this bug status.
- [2026-10-25T11:11:13Z] `qa` Mara Tester:
  - Verified write side at HEAD 091bfb77: _aio.py lines 79 and 96 pass newline="" in write_text and atomic_replace_sync. Read-side CRLF-to-LF conversion confirmed (CRLF item file rewritten as LF after a comment on Linux); split out as BUG-1141. Windows itself not driven.
<!-- sq:discussion:end -->
