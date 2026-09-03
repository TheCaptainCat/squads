---
id: BUG-789
sequence_id: 789
type: bug
title: No guidance tells agents to read item .md files via sq, not directly
status: Verified
author: qa
refs:
- FEAT-694:blocks
- MILE-836:targets
description: Guidance covers write-protection for item .md files but never states
  reads must go through sq
created_at: '2026-08-24T17:46:07Z'
updated_at: '2026-09-01T08:05:15Z'
---
<!-- sq:body -->
## Symptom

Every agent-facing carrier of the "`.md` files are sq-managed" rule states it for
**writes only** — it tells an agent not to hand-edit the file, but never tells the
agent not to *read* the file directly instead of going through `sq … show`. Four
carriers checked, all write-only:

- `src/squads/_rendering/templates/claude/claude_section.md.j2:161` — "the `.md`
  files are sq-managed — never edit them by hand."
- `src/squads/_rendering/templates/agents/squads_skill.md.j2:44` — "never
  hand-edit frontmatter or the `<!-- sq:* -->` markers."
- `src/squads/_rendering/templates/agents/item_skill.md.j2:51` — "never edit them
  by hand."
- `src/squads/_rendering/templates/workflow.md.j2:74` — "never hand-edit them."

The `squads` skill's "Read back with `sq <type> <n> show --full --comments`"
line only frames the CLI as how you check what you just wrote — never as "the
file itself is not a valid read surface." Nothing anywhere says an agent must
not `cat`/open the `.md` directly to learn an item's state.

## Aggravating factor: the tool hands out the very path it means you not to open

`sq bug 183 show` prints a `file:` line in its own header panel with the on-disk
path:

```
│ file:                                                                          │
│ bugs/BUG-000183-sq-json-emits-ansi-and-breaks-json-parsing-when-force-color.   │
│ md                                                                             │
```

So the same command that models "use the CLI" also surfaces the raw path,
inviting exactly the shortcut the (missing) guidance should forbid.

## Why it gets worse: ADR-776

ADR-776 (Proposed, `sq decision 776 show --full --comments`) collapses the
sub-entity roll-up summary and the `:head` badge line from materialised body
regions to computed projections — driven finding in its own body: "Four
computed renderings of the sub-entity projection ship, and none of them reads
the body ... The two materialised regions are read by exactly one kind of
reader — a person or an agent opening the raw file." Once that lands, the body
regions disappear from the file entirely. Today, reading the file directly is a
bad habit that happens to still work (the regions are there, just possibly
stale per ADR-776's own drift findings on `:head`). After ADR-776 lands, reading
the file directly returns strictly less than the CLI: no sub-entity roll-up at
all, so an agent that opens the file can conclude an item has no sub-entities
when it does.

## Scope

This bug is about the guidance/observability gap, not about ADR-776's
projection design (that's tracked on ADR-776 itself). Two things need
attention here:

1. Every agent-facing carrier of the sq-managed-files rule (the four listed
   above, and any other carrier of the same rule) should state the read-side
   half explicitly: item `.md` files are read through `sq <type> <n> show`,
   never opened directly.
2. Nothing today enforces or even hints at this at the point of temptation —
   `show`'s `file:` line hands out the path with no accompanying caution, and
   there is no mechanism that would catch an agent opening the file instead of
   using the CLI.

Open question for the tech lead, left undecided here: is (2) something a
check/gate can plausibly catch at all — this is about an agent's tool-use
choice outside of any sq-tracked artifact, not a property of the squad's own
files — or is this necessarily documentation-only (fix the guidance in the
four carriers, and reconsider whether `show`'s `file:` line should carry a
caveat)? Don't presume the answer; scope the fix once that's settled.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-24T17:47:06Z] Pierre Chat:
  - Reading the markdown files directly is forbidden: agents must use the CLI. If nothing told an agent that, that is a bug in squads. It gets more useful once the materialised views are live.
- [2026-08-24T20:33:10Z] Olivia Lead:
  - Fix scoped as TASK-793 (fixes ref), assigned to the tech-writer and Ready. Bug stays Open until it lands.
  - Answering the open question left for me: (2) is not gate-able. Whether an agent opens a file instead of running the CLI is a property of its tool-use outside any sq-tracked artifact, so no check rule can observe it — this is documentation-only. The `file:` line stays as it is per the operator: after ADR-776 a human resolving a merge is its one legitimate reader.
  - The sweep for other carriers found three more bundled templates (role.md.j2, the two .claude pointers) and seven doc lines beyond the four you cited; all are in TASK-793.
<!-- sq:discussion:end -->
