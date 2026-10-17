---
id: BUG-1028
sequence_id: 1028
type: bug
title: Atomic writer translates newlines on Windows
status: Open
author: qa
priority: low
refs:
- REV-1027
description: Text-mode open without newline='' alters line endings on Windows
created_at: '2026-10-16T07:42:11Z'
updated_at: '2026-10-16T07:42:11Z'
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
<!-- sq:discussion:end -->
