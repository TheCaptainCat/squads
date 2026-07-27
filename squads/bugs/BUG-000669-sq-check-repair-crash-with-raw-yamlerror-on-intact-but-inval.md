---
id: BUG-669
sequence_id: 669
type: bug
title: sq check/repair crash with raw YAMLError on intact-but-invalid frontmatter
status: InProgress
author: qa
severity: high
refs:
- BUG-668
created_at: '2026-07-27T14:56:34Z'
updated_at: '2026-07-27T22:14:07Z'
---
<!-- sq:body -->
## Symptom

`sq check` crashes with a raw, unhandled `yaml.YAMLError` (full Python
traceback, internal file paths and all) instead of a clean `SquadsError`
message, when an item's frontmatter block has an intact closing `---`
delimiter but the YAML between the delimiters is itself malformed. `sq
repair` crashes the same way on the same input.

## Root cause

`split_frontmatter` (`src/squads/_sections.py`) calls `yaml.safe_load` on the
matched frontmatter block with no `try`/`except` around it:

```
def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    loaded = yaml.safe_load(m.group(1))
    ...
```

`_scan_for_check` (`src/squads/_services/_maintenance.py`) calls this
(via `read_frontmatter`) directly while scanning every item file on disk,
with nothing catching a parse failure. The exception propagates up through
`Service.check()` to the CLI's `command` wrapper
(`src/squads/_cli/_common.py`), which only catches `SquadsError` — anything
else is left to surface as Python's default unhandled-exception traceback,
and the process exits 1 with no actionable message.

The same `read_frontmatter` call, with the same lack of a catch, is also on
`sq repair`'s disk-scan path (`_rebuild_index_from_disk`) and on
`sq renumber`'s (`_scan_records`, shared by the repad flow) — so all three
disk-scanning commands crash the same way, not just `check`. `sq show` and
`sq list` are unaffected: they resolve items from the index
(`.squads.json`) and never re-parse the `.md` frontmatter, so a corrupt file
is invisible to them until something actually re-scans disk.

## Reproduction

In a throwaway squad, created a task, then hand-edited its `.md` to leave
the closing `---` intact but inject invalid YAML between the delimiters
(the shape a badly resolved merge conflict leaves behind):

```
---
id: TASK-19
sequence_id: 19
type: task
<<<<<<< HEAD
title: Repro task
status: Draft
=======
title: Repro task (renamed)
status: InProgress
>>>>>>> feature-branch
author: qa
created_at: '2026-07-27T14:54:18Z'
updated_at: '2026-07-27T14:54:18Z'
---
```

Running `sq check` against this squad exits 1 and prints a full Rich
traceback ending in:

```
ScannerError: while scanning a simple key
  in "<unicode string>", line 4, column 1:
    <<<<<<< HEAD
    ^
could not find expected ':'
  in "<unicode string>", line 5, column 1:
    title: Repro task
    ^
```

with dozens of frames through `anyio`/`asyncio`/`yaml` internals and
absolute paths under the venv — not the clean `error: ...` line every other
`sq` failure produces. `sq repair` on the same file exits 1 with the
identical traceback shape. `sq list` and `sq task 19 show` against the same
corrupted file both succeed normally (they read the index, not the file).

## Scope note

This is adjacent to but distinct from BUG-668: BUG-668 is a **write-path**
bug where a killed process truncates/destroys the `.md` file. This is a
**read-path** bug where the file is fully intact (valid delimiters, no
truncation) but its content is invalid YAML — a hand-edit, a badly resolved
merge conflict, or a `.md` restored from a partial patch, not a crash
during `sq`'s own write. The atomic-write fix for BUG-668 does not touch
this: an intact-but-wrong file was never a torn write to begin with, so
durability work on the write path can't close this. The fix belongs on the
**read path**: wrap the `yaml.safe_load` call (in `split_frontmatter` or at
its call sites) and raise a `SquadsError` naming the offending file, so a
malformed frontmatter block becomes a clean, actionable error on `check`,
`repair`, and `renumber` alike, instead of a raw traceback.

## Severity

High. A raw traceback out of this repo's must-pass gate (`sq check`) is a
real defect on its own, but the bigger issue is that it also crashes `sq
repair` — the tool an operator reaches for specifically *because* something
on disk looks wrong. The trigger isn't exotic: a hand-edit, a merge
conflict left unresolved, or a partially-applied patch are all realistic
ways an otherwise-intact file ends up with invalid YAML between valid
delimiters.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
