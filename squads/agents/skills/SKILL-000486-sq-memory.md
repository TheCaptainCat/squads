---
id: SKILL-486
sequence_id: 486
type: skill
title: sq-memory
status: Active
author: sq-memory
description: 'Your role''s committed memory notebook and the team bulletin board:
  check your index at the start of a run, jot one fact per memory, prune what''s stale
  or wrong, post/clear board notices, and the memory-vs-board boundary. Use whenever
  you learn something worth remembering, or need to announce something to the whole
  team.'
created_at: '2026-07-18T21:49:05Z'
updated_at: '2026-07-18T21:49:05Z'
extra:
  slug: sq-memory
---
<!-- sq:body -->
# sq-memory — your role's memory and the team board

Your role has a committed memory: small facts you've learned while working on this project —
timing quirks, gotchas, conventions. It's yours (`squads/agents/memory/<role>/`) and survives
across sessions.

## Check it at the start of a run

Before you start, run `sq memory <role> list` to browse your role's memory index — one line per
memory, slug + description. If a line looks relevant, pull the full entry with `sq memory <role> show
<slug>` before acting on it.

## One fact per memory

Each memory holds **one** small fact, not a running log. Learn two things? That's two memories.
If you catch yourself writing "and also," split it. A good memory reads in one glance and its
body fits in a few lines.

## Prune what's stale or wrong

Memory rots if it's write-only. Remove entries that are out of date, wrong, or superseded using
`sq memory <role> forget <slug>` — a smaller trustworthy pool beats a large stale one. Forgetting
deletes the entry (history stays in git).

## The memory-vs-board boundary

Memory is **personal and learned** — something you discovered doing the work on your role. The
**board is shared** — for project-wide conventions or team announcements that belong on one
surface, not in every role's pool. When deciding what to write: is this mine (learned), or the
team's (shared)? Personal facts go to memory; shared announcements go to the board.

## The summary-vs-body split

`sq memory <role> add "<fact>"` takes the positional argument as the memory's snappy one-line
**summary** — the `summary:` field, and what `list`/`search` show in the index. It is not the
place for the whole fact: keep it to a single glance-readable line. The detailed write-up — the
reasoning, the example, the "why" — goes in the **body**, via `--file` (a path, or `-` for
stdin). Name the memory's handle explicitly with `--slug` instead of letting it get derived (and
possibly truncated) from the summary text — a clean, stable slug beats an auto-generated one.

## Memory command surface

```
sq memory <role> list                              # browse the index
sq memory <role> search <query>                     # find by content
sq memory <role> show <slug>                        # read one in full
sq memory <role> add "<summary>" [--file f] [--slug s]  # jot a new memory
sq memory <role> forget <slug>                      # prune a stale or wrong one
```

`<role>` is a positional subject (`sq memory python-dev list`), consistent with `sq inbox <role>` /
`sq mine <role>`. Memory is addressed by its own stable slug, not by position in the index.

## The board — post there instead, when it's shared

When something belongs on the shared side of the boundary above, it goes on the **team bulletin
board**, not into anyone's memory — a single announcement everyone sees, not one entry copy-pasted
into every role's pool. Run `sq board list` at the start of a run to see current notices, content
and all.

A good notice is **short and prescriptive** — a sentence or two saying what to do or watch out for,
not a narrative. Set `--until` whenever the notice has a natural expiry (a freeze, a temporary
heads-up) so it comes down on its own instead of turning into stale clutter someone else has to
notice and remove. If a notice stops applying before its `--until` (or has none), `clear` it
yourself rather than leaving it for someone else to puzzle over.

```
sq board post -m "<notice>" [--until <date>] [--as <slug>]  # post a notice
sq board list                                                # current (unexpired) notices
sq board clear <n>                                           # take one down
```

`--as` attributes the post (an agent role slug, or `op-<slug>` for a human); `<n>` in `clear` is the
notice's positional ordinal from the current `sq board list`, not a stored id.

<!-- sq:body:end -->
