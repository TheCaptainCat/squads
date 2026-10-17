---
id: BUG-957
sequence_id: 957
type: bug
title: Out-of-region view tag is invisible to show/check/view rm
status: Verified
author: qa
priority: low
refs:
- MILE-934:targets
- REV-952
created_at: '2026-09-15T09:34:39Z'
updated_at: '2026-09-29T16:05:43Z'
---
<!-- sq:body -->
## Symptom

A `sq:view:<name>` tag sitting outside an item's `sq:body` region is invisible on three
surfaces at once: it does not render, `sq check` says nothing about it, and `sq view rm`
reports it as absent (exit 0) while it is still on disk. Verified directly on a scratch squad,
one milestone, toggling only where the tag sits:

| tag position | renders | `sq check` | `sq view rm` |
|---|---|---|---|
| inside `sq:body` | yes (1) | clean | removes it |
| outside `sq:body` | no (0) | clean (silent) | "was not present, nothing to do", exit 0 |

`sq view rm`'s message is a false statement about the file: the tag is present, just not
where the region-scoped `remove_unpaired_marker` looks. An operator reading that message
concludes the document is clean when it is not.

Mechanism: `read_body` scopes `expand_view_tags` to the `sq:body` region's content, and
`remove_unpaired_marker`/`template_seeded_view_names` are likewise region-scoped by design.
None of the three surfaces looks outside the region a tag would need to sit in to render.

## Reachability — verified, three routes

Not theoretical; all three are tool-supported and were driven end to end on throwaway
squads:

1. **Project template override.** `sq override scaffold items/task.md.j2`, then move
   `sq:view:milestone_rollup` to after `sq:body:end` in the override. `sq check` accepts the
   override with no complaint. Every item created from it afterwards
   (`sq create task ...`) carries the tag out of region from the moment it's created, with
   zero `sq check` findings on that file. Confirmed on the created item: 0 renders,
   `sq check` clean, `sq view rm milestone_rollup` → "was not present, nothing to do", exit 0,
   tag still in the file.
2. **`sq adopt` over hand-authored markdown.** A raw item file written with the tag already
   placed after `sq:body:end` and imported with `sq adopt` is accepted with no complaint
   ("imported: 1 existing item(s)"). Same three-surface result as above on the adopted item.
3. **Hand edits to an existing item's file.** Moving an in-region tag to just after
   `sq:body:end` on an already-`sq create`d item reproduces the identical three-surface
   result. (Direct hand-editing of `.md` files bypasses `sq`'s own marker-safe-edit
   invariant, but the file still parses and is accepted by every read path.)

All three routes were actually reachable as described; none needed to be ruled out.

## The obvious remedy makes it worse

Once a tag sits out of region, `sq <type> <n> view add <name>` — the natural next thing an
operator or agent would try — inserts a **second**, in-region copy: `view add` and `view rm`
share the same region-scoped primitive (`insert_unpaired_marker` /
`remove_unpaired_marker`). Verified on the scratch squad: tag count goes 1 → 2, the item now
renders (1, restored) but `sq check` immediately reports a duplicate-marker error naming
`sq:view:milestone_rollup` at error level — a defect
`sq check` had said nothing about a moment earlier. So the tool's own suggested fix trades a
silent problem for a loud one rather than resolving it.

## Not in scope here

The 0.14→0.15 corpus migration's handling of this same shape (skip + report the item id
rather than duplicate the tag) is already fixed — landed this session. This bug is about the
general invisibility of an out-of-region view tag across `show`/`check`/`view rm`/`view add`,
not about that migration.

## Suggested direction (not prescriptive)

`sq check` reporting a view tag that sits outside the region it can render/be managed from,
naming the remedy, would turn all of these silences into one visible finding without widening
any writer's scope — the same shape the migration fix above already uses for its own skip.
The actual fix (report-only vs. teaching the writers to reconcile placement) is a design call
for whoever picks this up, not decided here.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:49:32Z] `python-dev` Elias Python:
  - Fixed: sq check warns on a view tag outside sq:body (also in template overrides); view add and view disable refuse instead of placing a duplicate. view rm no longer exists, so disable is the verb that used to misreport.
- [2026-09-29T14:24:02Z] `manager` Catherine Manager:
  - Reopened for REV-975 findings.
- [2026-09-29T14:36:22Z] `python-dev` Elias Python:
  - Review fix: the duplicate-tag message names a remedy that works when a copy sits outside sq:body.
- [2026-09-29T16:05:39Z] `qa` Mara Tester:
  - Verified by QA against c5331f42 (src clean at the time of the drives), dev tree via uv run, scratch squads. Driven on a milestone, tag position x surface: in body (renders, check clean, disable/add work), before sq:body, after sq:body:end, inside the discussion region, two copies (one in, one out). Out-of-region rows: 0 renders, check warns naming the tag, disable and add exit 1 with a message that says where the tag is; the two-copy row is a check error (exit 3); tag count unchanged everywhere. Released 0.15.0 contrast: check silent, view add duplicated the tag (2). Routes driven: template override (check warns on the .j2), sq adopt, hand edit; the disabled-form tag is caught too. Note for the record: the remedy says to move the tag inside sq:body, and no sq verb can do that (report-only, as ruled).
<!-- sq:discussion:end -->
