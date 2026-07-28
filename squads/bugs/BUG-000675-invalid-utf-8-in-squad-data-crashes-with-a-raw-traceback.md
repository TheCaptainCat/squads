---
id: BUG-675
sequence_id: 675
type: bug
title: Invalid UTF-8 in squad data crashes with a raw traceback
status: Verified
author: qa
severity: high
refs:
- BUG-669
created_at: '2026-07-27T22:27:38Z'
updated_at: '2026-07-28T07:25:09Z'
---
<!-- sq:body -->
## Symptom

`sq check`, `sq repair`, `sq board list`, and effectively every other command crash with a
raw, unhandled `UnicodeDecodeError` (full Python traceback, internal file paths and all)
instead of a clean error line, when a squad-data file on disk contains bytes that are not
valid UTF-8 — an item `.md`, a board notice `.md`, or `.squads.toml` itself.

## Root cause

This is a read-path defect, one layer below BUG-669 and untouched by its fix. BUG-669's fix
(TASK-673) wraps the *parse* step — `yaml.safe_load`/`tomllib` decoding an already-decoded
string — in a `try`/`except` that raises a clean `SquadsError`. Invalid UTF-8 fails one step
earlier, at the *read*, before any parser runs:

- `_aio.read_text` (`src/squads/_aio.py`) is `path.read_text(encoding="utf-8")` with no
  `try`/`except`. Every item-file scan (`_scan_for_check` in `_services/_maintenance.py`) and
  every board-notice read goes through it. A non-UTF-8 byte raises `UnicodeDecodeError`
  there, before `read_frontmatter`/`split_frontmatter` (and TASK-673's new guard around
  `yaml.safe_load`) ever see any text.
- `_paths.py::load_config` opens `.squads.toml` in binary mode and hands the raw bytes to
  `tomllib.load`, which does its own internal UTF-8 decode (`b.decode()`) before TOML
  parsing starts. That decode raises the same bare `UnicodeDecodeError` — the existing
  `except tomllib.TOMLDecodeError` in `load_config` never sees it, because decoding fails
  before the TOML grammar is even reached.

Neither the write side landing on `release/0.12.2` (the atomic-write primitive, the `check`
confirm round, the task-local transaction context) nor TASK-673's parse-error wrapping
touches this: both operate strictly downstream of a successful UTF-8 decode. The write path
also can't cause it by construction — every write in this codebase originates from a Python
`str` that was already valid Unicode — the bytes have to arrive some other way (a hand-edit,
a bad merge, a restore from a partial patch, a copy from a different encoding).

## Repro

Threw a bug item, a board notice, and the project's `.squads.toml` at this in a disposable
squad under `/tmp`, each corrupted by inserting one `0x80` byte (an invalid UTF-8 lead byte)
into otherwise-intact prose:

- Item `.md`: `sq check` and `sq repair` both raised `UnicodeDecodeError: 'utf-8' codec can't
  decode byte 0x80 in position 196: invalid start byte` as a full traceback, exit 1.
- Board notice `.md`: `sq board list` raised the identical shape of traceback
  (`_aio.read_text` → `Path.read_text` → `UnicodeDecodeError`), exit 1.
- `.squads.toml`: `sq list` raised `UnicodeDecodeError` from inside `tomllib._parser.load`'s
  own `b.decode()` call, exit 1 — this one hits before the CLI even resolves which command
  was requested, so it is not limited to `check`/`repair`/`board list`; any command run
  against a squad whose config has this problem fails the same way.

## Severity

High, matching BUG-669's read-path sibling: same user-visible symptom (a raw traceback
instead of a clean, actionable error), same breadth (the item scan every `sq check`/`sq
repair` does, board reads, and — via `.squads.toml` — essentially every command), and the
same trigger class (a hand-edit or restore introducing bytes the tool never wrote itself).

## Proposed fix

Wrap the read step, not just the parse step: `_aio.read_text` (and `_paths.py::load_config`'s
binary read) should catch `UnicodeDecodeError` and raise a `SquadsError` naming the offending
file, mirroring TASK-673's `yaml.safe_load`/`tomllib.load` wrapping one layer up.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
