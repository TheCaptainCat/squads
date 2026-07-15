<!-- sq:body -->
# sq-memory — your role's committed notebook

Your role has its own committed notebook of small facts you've learned while working on this
project — things worth remembering before a run that don't belong in a formal doc: a timing
quirk, a gotcha, a convention someone corrected you on. It's **yours** (`squads/agents/memory/
<role>/`, one folder per role) and it's committed to the repo, so it survives across sessions,
checkouts, and machines.

## Check it at the start of a run

Your role's memory index — one line per memory, slug plus a short description — is surfaced into
your context automatically at boot. You don't have to go looking for it: skim those lines before
you start work, the same way you'd skim a note left for yourself. Index in, content on recall — if
a line looks relevant, pull the full entry with `sq memory <role> show <slug>` before you act on it.
An empty pool surfaces nothing, which is fine — it just means you haven't written anything down yet.

## One fact per memory

Each memory should hold exactly **one** small, self-contained fact — not a running log, not a
grab-bag of loosely related notes. If you learn two things, that's two memories. Small and
specific beats long and general: a good memory reads in one glance from the index line alone, and
its full body still fits in a few lines. When you catch yourself writing "and also…" inside a
memory, split it.

## Prune what's stale or wrong

Memory rots if it's write-only. When you notice an entry that's out of date, superseded, or was
simply wrong, remove it with `sq memory <role> forget <slug>` rather than leaving it to mislead the
next run — a smaller, trustworthy pool beats a large, stale one. Forgetting is a real deletion (the
history stays in git), not something that happens as a side effect of reading.

## The memory-vs-board boundary

Memory is **personal and learned** — something you individually picked up while doing the work,
scoped to your own role's pool. It is not the place for facts that are **cross-cutting or apply to
the whole team** — a project-wide convention, an announcement everyone needs to see. Knowledge like
that belongs on a shared, team-wide surface instead of being copy-pasted into every role's pool one
entry at a time. When you're about to jot something down, ask: *is this mine, learned from doing my
own work — or is this something the whole team needs to know?* The former is memory; the latter
belongs somewhere shared, not duplicated per role.

## Command surface

```
sq memory <role> list                     # browse the index
sq memory <role> search <query>           # find by content
sq memory <role> show <slug>              # read one in full
sq memory <role> add "<fact>" [--file f]  # jot a new memory
sq memory <role> forget <slug>            # prune a stale or wrong one
```

`<role>` is a positional subject (`sq memory python-dev list`), consistent with `sq inbox <role>` /
`sq mine <role>`. Memory is addressed by its own stable slug, not by position in the index.

<!-- sq:body:end -->
