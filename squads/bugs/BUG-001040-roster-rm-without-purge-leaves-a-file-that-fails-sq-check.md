---
id: BUG-1040
sequence_id: 1040
type: bug
title: Roster rm without --purge leaves a file that fails sq check
status: Fixed
author: qa
refs:
- REV-1034
created_at: '2026-10-16T09:01:13Z'
updated_at: '2026-10-16T11:20:13Z'
priority: medium
---
<!-- sq:body -->
## Repro

```
$ sq skill 12 rm
removed SKILL-12
$ sq check
error SKILL-12: on disk but not in index (run `sq repair`)
(exit 3)
```

Same for `sq operator <addr> rm` (`error OP-25: on disk but not in index`). `sq role <addr> rm` shares `remove_item`. `sq repair` then re-indexes the file, so the removed entry comes back.

## Expected

`rm` leaves the squad passing its own check. Either `rm` deletes the item file by default, or without `--purge` it archives/unlinks it in a way `sq check` and `sq repair` accept (with Archived as the soft-removal route, which docs/roles.md already describes as the way to retire an entry).

## Why this is a defect, not intended behaviour

- `remove_item` (`_services/_items.py` ~716) only unlinks the file under `if purge:`. The comment above it justifies unlink-before-commit ordering and says an orphan file is what `sq repair` heals by re-indexing, "resurrecting the removed item"; it describes a crash window, not a designed default.
- The CLI help ("Remove a skill (and its pointer; --purge also deletes the markdown)") and docs/roles.md (72, 122, 140: `rm [--purge]`) never say that a plain `rm` leaves the squad failing `sq check`. docs/stability.md only mentions `--purge` for slug reuse. Nothing documents the orphan state as a feature.
- Work items use `remove_work_item`, which always unlinks. The roster types are the odd ones out.
- The frontmatter is the source of truth (CLAUDE.md invariant 1), so an "removed" item whose file remains is not removed from the corpus's point of view; the next `sq repair` resurrects it.

The decision to make (architect/tech lead): purge by default, or make plain `rm` refuse and point at `status Archived` / `--purge`. Either way the docs need one sentence (REV-1034 F8 covers the doc side).

Found in the docs audit (REV-1034, F8 and its summary).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:16:27Z] `op-pierre` Pierre Chat:
  - 2026-10-16: a plain rm (no --purge) refuses, and the message says exactly what to run.
- [2026-10-16T11:20:13Z] `python-dev` Elias Python:
  - Fixed on branch worktree-agent-adaaa829aeaea66dd, commit d3a7da9d: plain rm on a role, skill or operator now refuses and names the --purge command and the status Archived alternative. Work-item remove already always unlinks, so it has no such flaw. Docs still show rm [--purge] as optional (docs/roles.md, README.md, docs/stability.md); left for the writer.
<!-- sq:discussion:end -->
