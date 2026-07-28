---
id: BUG-668
sequence_id: 668
type: bug
title: 'Non-atomic .md write: kill mid-write destroys the source of truth'
status: Verified
author: qa
severity: high
refs:
- ADR-663
created_at: '2026-07-27T14:39:58Z'
updated_at: '2026-07-28T07:25:06Z'
---
<!-- sq:body -->
## Symptom

A process killed while a squad-data `.md` file is being written (timeout, background-stop,
OOM, container teardown) can leave that file truncated or empty on disk — not merely
disagreeing with the index, but with its own content destroyed. The same partial state is
also visible to a concurrent reader with no crash involved at all: `sq check` running while
another process is mid-write can observe the identical half-written bytes.

## Root cause

Every write to squad data — item `.md` files (`_itemfile.py`), sub-entity/retype/rename
rewrites, board notices (`_board/_store.py`), memory entries (`_memory/_store.py`) — goes
through one primitive, `_aio.write_text` (`src/squads/_aio.py:32-34`):

```
async def write_text(path: Path, text: str) -> None:
    await to_thread(lambda: path.write_text(text, encoding="utf-8"))
```

This is a bare `Path.write_text`: open-with-truncate, write, close. No temp file, no
`os.replace`, no `fsync` — unlike the index's own `_atomic_write`
(`src/squads/_index/_store.py:385-403`), which already does tmp-write + fsync + `os.replace`
as one thread hop. A kill between open-truncate and close leaves on disk exactly whatever
prefix of the new text had been flushed — anywhere from 0 bytes to the whole file minus a
tail.

`sq repair` cannot heal this: repair rebuilds the index *from* the markdown (invariant #1),
so a markdown file that is itself destroyed has nothing to rebuild from — repair does not
fail loudly, it silently drops the item from the index as "no markdown file found" and the
corrupted file becomes a permanent orphan (see repro).

Two shapes the truncation takes, both confirmed below:

- The cut lands inside the frontmatter block, before its closing `---`. `_scan_for_check`
  (`src/squads/_services/_maintenance.py:892-899`) finds no closing delimiter at all, so
  `split_frontmatter` returns an empty dict; `fid = data.get("id")` is falsy and the file is
  reported `error … file has no \`id\` in frontmatter`.
- The cut lands inside the body, after the frontmatter closed intact. The item still has a
  valid `id`, but any sq marker straddling the cut point is left half-written, reported as
  an unclosed-marker error by `_marker_issues`.

I could not reproduce a bare `yaml.YAMLError` escaping `split_frontmatter` from a single
truncated write: its regex requires a literal closing `---` line, and because the
frontmatter dict is fully serialized in memory before any byte reaches disk, a truncated
write structurally can only stop before that closing line exists (bucket above) or land
at/after it, in which case the whole dict was already written and parses fine. I scanned
every truncation length of a realistic frontmatter+body blob (a multi-line `refs` list, an
`extra` dict) through the real `split_frontmatter` and found no cut that raised it.

## Repro

Forked a child process against a throwaway squad; the child monkeypatched
`squads._aio.write_text` in-memory (no source file changed) to open the target file, write
only a fixed-fraction prefix of the intended text, `fsync`, and immediately `SIGKILL` itself
before writing the rest — then ran `Service.set_status()` for real, so the mutation went
through the actual code path (`update_frontmatter` → the patched `write_text`), not a
hand-written stand-in for the outcome.

- Cut at 30% of the write (inside the frontmatter block): child died (signal 9); on-disk
  file was 120 bytes, ending mid–`created_at:` value, no closing `---` anywhere.
  `sq check` reported `error … file has no \`id\` in frontmatter` *and* `error BUG-19: in
  index but no markdown file found` (exit 3). `sq repair` then dropped the item from the
  index entirely (`warn BUG-19: indexed but no markdown file found (deleted?)`) — `sq bug 19
  show` afterward: `no item with number 19`, `sq list -a` no longer lists it. The file is
  still on disk, still corrupted, and no `sq` command can recover its content — no rename, no
  ID reuse; just gone from the board.
- Cut at 55% of the write (after the frontmatter's closing `---`, inside the body): child
  died (signal 9); on-disk file was 220 bytes, frontmatter intact (`status: InProgress`) but
  body cut mid-word inside the sq:body section, before its close marker. `sq check` reported
  an unclosed-marker error plus (because the index commit never ran) a status-drift warning
  for the item — exit 3.

Both runs used a disposable squad created just for this; nothing under the real project
board was touched.

## Severity

High. This is worse than a drift the index can be repaired back to: it destroys the one
artifact (`invariant #1`) that `sq repair` depends on to reconstruct anything, and it is
reachable by exactly the interruption pattern (background-stop, timeout, OOM) that this
project's own agent workflow produces routinely, not an exotic timing window.

## Proposed fix

Route every squad-data write through one atomic primitive — temp file in the same directory,
flush, fsync, `os.replace`, one thread hop with no `await` between fsync and rename — the
shape `_atomic_write` already uses for the index, so a killed process can no longer truncate
the source of truth and no reader can ever observe a partially written file.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
