---
id: TASK-847
sequence_id: 847
type: task
title: Retire the sub-entity regions and declare the roll-up view
status: Done
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
description: Stop writing the sub-entity summary and head regions, drop them from
  the bundled templates, and reissue the roll-up as three declared subentity-source
  views
subentities:
- local_id: ST1
  title: Declare the three sub-entity roll-up views
  status: Cancelled
  story: US1
- local_id: ST2
  title: Presentation templates for the three roll-up views
  status: Cancelled
  story: US1
- local_id: ST3
  title: Drop the region writes from the live sub-entity path
  status: Done
  story: US2
- local_id: ST4
  title: Keep set_head and ensure_summary as migration-only machinery
  status: Done
  story: US2
- local_id: ST5
  title: Remove the regions from the bundled item and block templates
  status: Done
  story: US1
- local_id: ST6
  title: Freeze the five shipped renderings and pin the badge divergence
  status: Done
  story: US1
- local_id: ST7
  title: Regenerate the template manifest and content store
  status: Done
  story: US1
created_at: '2026-09-01T08:02:31Z'
updated_at: '2026-09-01T09:54:26Z'
---
<!-- sq:body -->
## Scope

FEAT-694 US1 and US2, on one surface: the sub-entity rendering layer. The two materialised
regions stop being written, the item templates stop carrying them, and the roll-up projection
is reissued as declared `[views]` entries. The corpus-wide strip of what is already on disk is
**not** here — it is the sibling migration task.

US1 and US2 are one task rather than two because they are the same files: the write path that
maintains both regions is a single sequence in `_services/_subentities.py`, both regions are
emitted by the same two templates, and both retire behind the same manifest regeneration.

## Two rulings this is scoped against, not the older text

ADR-776's 2026-09-01 amendment changed the shape. Read that amendment before starting.

1. **The head has no successor.** It is a deletion, not a build. Its computed counterpart
   already ships and is already frozen by the acceptance bar: `_subentity_badge_line`
   (`_cli/_common.py`, verified) renders the status badge, every declared field badge, the
   assignee and the mapped story on one line, and feeds both the styled pane title and the
   `--raw` dossier. Verified: `uv run sq review 11 show --full` prints that pane title and
   never prints the region's text. The only delta between the region and that line is two
   foreign resolutions — the assignee's display name via the ROLE item, and the mapped story's
   title via a sibling sub-entity. Those are the facts ADR-776 measured **in order to condemn
   the region**: §5's finding is three clauses — foreign-sourced, stale, and read by nothing —
   and any successor satisfies the first two while contradicting the third. Do not build one,
   in `[views]` or beside it. If a resolved label is ever wanted, that is a change to
   `_subentity_badge_line` argued on its own merits, and it is out of scope here because this
   feature's acceptance freezes those bytes.
2. **One projection is reissued, not two.** The roll-up becomes declared views; the head
   becomes nothing.

## What is byte-frozen, and what that forbids

Five computed renderings derive their own view of sub-entity state today. None of them reads
either region, so none of them changes — and each must be **proven** unchanged, not assumed:

- `_cli/_common.py::_print_subentity_summary` — the Rich summary table under `sq <type> <n> show`;
- `_cli/_common.py::_subentity_pane_title_raw` (via `_subentity_badge_line`) — the pane title
  under `--full`;
- `_cli/_items.py::_sub_table` — the per-kind list table (`sq task <n> subtasks`);
- `_cli/_common.py::_subentity_badge_line` — the `--raw` dossier line;
- `_cli/_common.py::build_subentity_json` — the `--json` sub-entity payload.

The first four are the four ADR-776 names. The fifth is listed because it derives from the same
state and must not move either. `_tui/_reader.py` renders its own badge line from the same
helpers and is in the same class.

**Do not route any of these five through the new view's projection.** That is a real
non-equivalence, verified in the code, not a stylistic preference: `_views.py::_badge_cell`
renders `f"{emoji} {label}"` (`🔴 Critical`), while `_discussion.summary_row` calls
`badges.badge_render(...)` with its default `as_label=False`, which renders emoji + **code**
(`🔴 critical`) — see `_badges.badge_render`'s own docstring, which names the two conventions.
Sharing the projection would change the summary table's bytes, and the first acceptance clause
forbids exactly that.

**How this resolves:** the five shipped renderings keep `summary_columns`/`summary_row`
unchanged; the declared views project through `_views.py` and render the label form. The two
derivations coexist, deliberately, and each is what its own reader already gets. Do not
"reconcile" them by changing either side — reconciling would move the frozen bytes. Say so in a
comment where `summary_row` and the view declarations respectively live, so the next reader does
not read the divergence as an oversight and unify it.

Also worth knowing before scoping byte-identity against a view: **no view can render a status
badge at all.** `status` is a base attribute; `_views.py::_BASE_RESOLVERS["status"]` returns the
stored name and `project()` types every base code `text`. That is a property of the record-shape
contract (`status_role` is the styling axis), not a gap to fill here.

## The roll-up views: what to declare

Three hosting types, three sub-entity kinds (verified in `src/squads/_specs/workflow.toml`):
`feature` → `story`, `task` → `subtask`, `review` → `finding`. A `[views]` entry names one
source, and a `subentity` source names one kind (`_views.py::_resolve_subentity_source` refuses
an item whose type hosts a different kind), so this is three entries, not one.

The shipped `subentity` source resolves the roll-up exactly — no widening is needed. Its base
field set is `{id, status, status_role, settled, delivered, assignee, title, story}`
(`VIEW_BASE_FIELDS_BY_SOURCE`, verified), and a declared kind field (`finding`'s `severity`)
resolves as a badge. That covers every column `summary_columns` derives: the local id, the
declared fields, status, assignee, title, and the story column for a kind declaring
`maps_parent_story`. The retired region was always local — its row carried the assignee's
**slug** and the story's **local id**, never a resolved label — which is why the source fits.

Column order and labels follow `summary_columns`: local id first (headed by the kind name
title-cased), then each declared field by its label, then Status / Assignee / Title, then Story
iff the kind declares `maps_parent_story`.

### Freestanding, not attached to `items.<type>.views` — settled here

`milestone_rollup` attaches through `items.milestone.views`, and US1's parenthetical repeats that
mechanic. **Do not copy it here.** Verified: `_cli/_common.py::_print_item_content` already calls
`_print_subentity_summary` for any item with sub-entities, and then
`_print_attached_views` renders every attached view unconditionally. Attaching a roll-up view to
`feature`/`task`/`review` would therefore make `sq <type> <n> show` print two roll-up tables of
the same data — a new duplication nobody asked for, on a feature whose stated premise is that
nothing the computed renderings show changes. The milestone precedent had no competing built-in
table, so the collision never arose there.

Declaring them freestanding costs nothing the ADR asked for. Verified: `views` is a member of
`WORKFLOW_TOP_LEVEL_SECTIONS` (`_workflow/_loader.py`), and that frozenset doubles as
`[selected]`'s accepted section-name set — so `selected.views` drops a freestanding view
directly. And `_prune_orphaned_type_owned_views`'s own docstring states it is scoped so a
genuinely freestanding view is never touched, i.e. the shape is supported by construction. The
two things ADR-776 §4 says a declared view buys — re-presentation through
`.overrides/templates/views/<name>.md.j2` and a `[selected]` drop — both hold.

The views are reachable through `sq workflow views` and `sq workflow view <name> <ID>`.

Record the reasoning in a comment on the view declarations. If the architect or the operator
prefers the attached form with the built-in table removed, that is a different change with a
different acceptance bar (it moves the frozen `show` bytes) and it needs a ruling first —
raise it, do not decide it mid-build.

## Presentation templates

`_views.py::render_view` resolves the template at `templates/views/<view_name>.md.j2` from the
view's own key — there is no `presentation` field. So each of the three views needs its own file
under `src/squads/_rendering/templates/_rendering`-hosted `templates/views/`. Keep them thin:
the projection already carries `fields` metadata, so a generic markdown table over
`projection.fields` + `groups[*].records` is the whole template, and the three differ only in
their view name. `subentities/summary.md.j2` cannot be reused directly — it takes
`cols`/`seps`/`rows`, not the view record shape — but it is the layout to match.

## Retiring the write path

- `_services/_subentities.py`: the `ensure_summary` call at the block-write seam and the
  `set_heading` → `_refresh_head` → `ensure_summary` sequence both go. `_refresh_head` is
  deleted. `set_heading` **stays** — the `### ST1 — title` heading is not one of the retired
  regions and `show --full` still reads the block's own heading.
- `_rendering/templates/items/{task,feature,review}.md.j2` lose their `sq:summary` region
  (verified: those three, and only those three, carry it).
- `_rendering/templates/subentities/block.md.j2` stops scaffolding the empty `:head` region.
- `_services/_collab.py`'s search region registry drops its `_add(markers.SUMMARY, "summary")`
  entry, and the block-level fallback comment there ("heading + head badge line") is corrected.
- **`markers.SUMMARY` stays.** `_services/_validators.py` puts it in the structural tag set that
  keeps a leftover `sq:summary` from being reported as a stale container; a file migrated by an
  older path, or one an adopter has not migrated yet, must not start failing `sq check`. The
  migration task also needs the constant.

## `set_head` and `ensure_summary` cannot be deleted — they are migration-only machinery

ADR-776 §7 flags `set_head`. Verified, and there is a **second** one the amendment does not
name: `_migrations/_v0_1_to_v0_2.py` calls `discussion.ensure_summary` twice (once per item body
kind, once for the review findings skeleton), and `_migrations/_v0_2_to_v0_3.py` calls
`discussion.set_head` when lifting legacy `:meta` blocks. Both runners are frozen; neither may be
edited to remove the call.

So `set_head`, `ensure_summary`, `render_summary`, `summary_columns`/`summary_row` and both
`templates/subentities/{head,summary}.md.j2` **all stay reachable**. What retires is the
*obligation*: no live write path calls `ensure_summary` or `set_head` any more.
`summary_columns`/`summary_row` additionally stay as the five shipped renderings' own derivation.

Mark `set_head`, `ensure_summary` and `render_summary` in place as migration-only, with a
docstring line naming the exact caller that pins each. Do not move them out of `_discussion.py`
in this change — relocation is a separate cleanup with its own import-graph risk, and the
migration import guard has opinions about what a runner may reach. A full replay from 0.1 will
write these regions and the 0.14 runner will then strip them again in the same `sq migrate up`
invocation; that is wasteful and correct, and the registry order already guarantees it.

`vulture` will now flag nothing new here (the callers are real), but re-read its output after the
change rather than assuming.

## Traps

- **Do not touch `subentities/summary.md.j2` or `head.md.j2`.** They are still rendered by the
  frozen runners. Editing them changes what a replay writes.
- The manifest regeneration is shared with the role-side task. See "Release mechanics".
- `sq search` narrows as a consequence (the region text is no longer scanned). That is stated
  and accepted in the feature. Check `tests/` for a search test that leans on region text and
  update it to assert the narrowed behaviour rather than deleting it.

## Release mechanics, inherited

- `workflow.toml` and the bundled templates both move, so the template manifest and the content
  store are regenerated. **`pyproject.toml` already reads 0.14.0 — do not run
  `scripts/bump_version.py`.** Only the `0.14.0` manifest entry may move.
- Orphan residue in the content store from a regeneration is expected between releases; `--check`
  reports it and passes. Do not add a deletion to clear one — the operator clears it at the cut.
- Whichever of this task and the role-side task regenerates **last** must do so with the other's
  changes already in the tree.

## Acceptance

- Three `[views]` entries are declared over the `subentity` source — one per bundled sub-entity
  kind — each with a presentation template at `templates/views/<name>.md.j2`, each resolvable via
  `sq workflow view <name> <ID>` against a hosting item and via `--json`, and none attached to
  any `items.<type>.views` list.
- `sq workflow views` lists all three; `selected.views` dropping one removes it, proven by a test
  over an override.
- All five computed renderings named above are byte-identical before and after, proven by tests
  that compare captured output rather than by inspection. At least one covers a `finding` with a
  `severity` value, which is where the label/code divergence would show.
- No live write path calls `ensure_summary` or `set_head`; `_refresh_head` no longer exists; a
  freshly created feature/task/review file carries no `sq:summary` region and a freshly
  scaffolded sub-entity block carries no `:head` region.
- `set_head`, `ensure_summary`, `render_summary` and both `subentities/` templates still exist
  and are still reached by `_v0_1_to_v0_2` / `_v0_2_to_v0_3`; the corpus migration tests over the
  older fixtures still pass unchanged by this task.
- `markers.SUMMARY` is still in `_validators`' structural tag set, and a file that still carries
  a leftover `sq:summary` region passes `sq check`.
- The template manifest and content store match the tree, only the `0.14.0` entry moved, the
  freshness guard passes, and `scripts/bump_version.py` was not run.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 847 add-subtask "<title>"`; track with `sq task 847 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare the three sub-entity roll-up views

<!-- sq:subtask:ST1:body -->
Declare one `[views]` entry per bundled sub-entity kind in `src/squads/_specs/workflow.toml`:
`story` (hosted by `feature`), `subtask` (hosted by `task`), `finding` (hosted by `review`). Each
uses `source = { kind = "subentity", name = "<kind>" }`.

Field set and order mirror `_discussion.summary_columns`: the local id first (label = the kind
name title-cased), then one entry per declared field by its own label (`finding` declares
`severity`), then `status`, `assignee`, `title`, then `story` for a kind declaring
`maps_parent_story` (subtask only). No widening is needed — `VIEW_BASE_FIELDS_BY_SOURCE`'s
`subentity` set already allows `id`, `status`, `assignee`, `title` and `story`, and `severity`
resolves as a declared badge field.

Give each an `order_by` that reproduces the roll-up's own order (declaration order by local id),
and no `group_by` — the roll-up is one flat table.

**Do not attach any of them to an `items.<type>.views` list.** The task body carries the
reasoning: `_print_item_content` already renders the built-in summary table for any item with
sub-entities and then renders every attached view, so attaching would print the same data twice.
Freestanding views are a supported shape (`_prune_orphaned_type_owned_views`'s docstring says so
explicitly) and `views` is in `WORKFLOW_TOP_LEVEL_SECTIONS`, which doubles as `[selected]`'s
accepted section set — so `selected.views` drops one directly.

Leave a comment in the spec beside the entries recording why they are freestanding, so the next
reader does not "fix" it by attaching them.

Done when all three load, `sq workflow views` lists them, `sq workflow view <name> <ID>` resolves
against a hosting item, resolving against a non-hosting item fails with the source-kind mismatch
message, and an override's `selected.views` drops one.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-01T08:37:55Z] Elias Python:
  - Declared story_rollup/subtask_rollup/finding_rollup as freestanding subentity-source views in workflow.toml, per field-order match to summary_columns.
- [2026-09-01T09:04:11Z] Elias Python:
  - Retired per architect ruling (ADR-776, third 2026-09-01 amendment): no bundled sub-entity roll-up view ships, freestanding or attached. Declarations removed from workflow.toml; the computed successor (_print_subentity_summary) already shipped and is untouched.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Presentation templates for the three roll-up views

<!-- sq:subtask:ST2:body -->
Three presentation templates under `src/squads/_rendering/templates/views/`, one per view name —
`_views.py::render_view` resolves the template from the view's own key
(`templates/views/<view_name>.md.j2`) and there is no `presentation` field to point elsewhere.

Keep them thin and uniform: the projection carries `fields` metadata and `groups[*].records`, so a
generic markdown table over those is the whole template. Match the layout
`subentities/summary.md.j2` produces (header row, separator row, one row per record) so the
rendered table reads the same as the region it replaces — but write new files. **Do not reuse or
edit `subentities/summary.md.j2`**: it takes `cols`/`seps`/`rows`, not the view record shape, and
it is still rendered by the frozen `_v0_1_to_v0_2` runner.

Render an empty collection as an explicit empty state rather than a header row with no body,
following `milestone_rollup.md.j2`'s precedent.

Because these are new bundled templates, they enter the template manifest — see the manifest
subtask, which must run last.

Done when each view renders through `sq workflow view <name> <ID>` and through `--json`, an
adopter's `.overrides/templates/views/<name>.md.j2` shadows the bundled file (proven by a test),
and a view whose template is missing still raises the clean `SquadsError` `render_view` already
produces.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-01T08:37:59Z] Elias Python:
  - Added templates/views/{story,subtask,finding}_rollup.md.j2 -- thin table template over fields/groups, matching subentities/summary.md.j2's layout, new files (summary.md.j2 untouched).
- [2026-09-01T09:04:19Z] Elias Python:
  - Retired alongside ST1: the three templates/views/*_rollup.md.j2 presentation templates are deleted -- an override at that path proved to re-present sq workflow view only, never sq review N show, so there was nothing to re-present.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drop the region writes from the live sub-entity path

<!-- sq:subtask:ST3:body -->
Stop maintaining the two regions in the live write path.

In `_services/_subentities.py`: drop the `discussion.ensure_summary(...)` call at the block-write
seam, and drop the `_refresh_head(...)` + `ensure_summary(...)` pair from the block-mutation
sequence. Delete `_refresh_head` itself.

**`set_heading` stays.** The `### ST1 — title` heading is not one of the retired regions — it is
the block's own heading, still read by `show --full` and still re-rendered from the frontmatter
title. Removing it is out of scope and would break the panes.

Nothing replaces the head. Its computed counterpart already ships as
`_cli/_common.py::_subentity_badge_line`, feeding the pane title and the `--raw` dossier line, and
that line is frozen byte-identical by this feature's acceptance. Do not add a renderer, a
`[views]` entry with foreign field resolution, or a helper "for parity" — ADR-776's 2026-09-01
amendment refuses all of them, and the two foreign resolutions the region carried (assignee
display name via the ROLE item, mapped story title via a sibling sub-entity) are the defect it
was retired for, not a capability to carry forward.

Done when a sub-entity add/update/body write produces a file with no `sq:summary` region and no
`:head` region, no live code path calls `ensure_summary` or `set_head`, and every existing
sub-entity mutation test still passes with only the removed-region assertions updated.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-01T08:38:02Z] Elias Python:
  - Dropped ensure_summary/_refresh_head/_story_label from _services/_subentities.py; _write_block_file now only re-renders the block heading.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Keep set_head and ensure_summary as migration-only machinery

<!-- sq:subtask:ST4:body -->
Keep the retired renderers reachable, because two frozen migration runners call them — verified:

- `_migrations/_v0_1_to_v0_2.py` calls `discussion.ensure_summary` twice (once per body kind, once
  for the review findings skeleton);
- `_migrations/_v0_2_to_v0_3.py` calls `discussion.set_head` when lifting legacy `:meta` blocks.

ADR-776 flags the second; the first is an additional pin found while scoping. Neither runner may
be edited. So `set_head`, `ensure_summary`, `render_summary` and both
`templates/subentities/head.md.j2` and `summary.md.j2` all stay in the tree, and the acceptance
clause reading "`set_head` is deleted" is not literally achievable — what retires is the
refresh-on-mutation **obligation**, which the sibling subtask removes.

Mark each in place as migration-only, with a docstring line naming the exact caller that pins it,
so the next reader does not delete it and get blocked by a frozen runner. Leave them in
`_discussion.py` — relocating them next to the legacy-body handling is a separate cleanup with its
own import-graph and migration-import-guard risk, and it is not this feature's.

`summary_columns` and `summary_row` are a different case: they are not migration-only, they are
the live derivation behind the five frozen computed renderings, and they stay exactly as they are.

Done when the pins are documented, both templates are untouched, the corpus migration tests over
the older fixtures pass unchanged, and a `vulture` run reports nothing new here.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-01T08:38:05Z] Elias Python:
  - set_head/ensure_summary/render_summary and both subentities/{head,summary}.md.j2 kept, docstrings now name the exact frozen migration caller pinning each.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Remove the regions from the bundled item and block templates

<!-- sq:subtask:ST5:body -->
Take the regions out of the bundled templates so a newly created item never carries one.

- `_rendering/templates/items/task.md.j2`, `feature.md.j2` and `review.md.j2` lose their
  `sq:summary` region. Verified: those three, and only those three, carry it.
- `_rendering/templates/subentities/block.md.j2` stops scaffolding the empty `:head` region under
  the heading.
- `_services/_collab.py`'s search region registry drops `_add(markers.SUMMARY, "summary")`, and the
  block-level fallback comment there — which describes the region as "heading + head badge line" —
  is corrected to describe what the block now holds.

**`markers.SUMMARY` stays defined.** `_services/_validators.py` includes it in the structural tag
set that keeps a stray `sq:summary` from being reported as a stale container; a file an adopter has
not migrated yet, or one an older runner just wrote during a replay, must not start failing
`sq check`. The migration task needs the constant too.

`sq search` narrows as a direct consequence: sub-entity status, assignee and story text were
matched only because they sat as text inside the regions being removed. That is stated and accepted
in the feature. Find the search tests that lean on it and update them to assert the narrowed
behaviour — a block heading's title still matches — rather than deleting the coverage.

Done when a freshly created feature/task/review file carries no `sq:summary` region, a freshly
scaffolded sub-entity block carries no `:head` region, a file still carrying a leftover
`sq:summary` passes `sq check`, and the search tests assert the narrowed behaviour explicitly.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-01T08:38:08Z] Elias Python:
  - Removed sq:summary from items/{task,feature,review}.md.j2 and the :head scaffold from subentities/block.md.j2; _collab.py's region registry drops the summary entry; search-narrowing tests/goldens updated.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Freeze the five shipped renderings and pin the badge divergence

<!-- sq:subtask:ST6:body -->
Prove the frozen renderings did not move, and pin the divergence that would move them.

Five computed renderings derive their own view of sub-entity state and none reads either region:
`_print_subentity_summary` (the `show` table), `_subentity_pane_title_raw` via
`_subentity_badge_line` (the `--full` pane title), `_sub_table` in `_cli/_items.py` (the per-kind
list table), `_subentity_badge_line` again (the `--raw` dossier line), and `build_subentity_json`
(the `--json` payload). `_tui/_reader.py` builds its own badge line from the same helpers and is in
the same class.

Write tests that capture each rendering's output and compare it, rather than asserting a substring.
At least one case must cover a `finding` carrying a `severity` value, because that is where the
divergence below would show.

**The divergence, verified in code, is why none of these may be routed through the new view's
projection.** `_views.py::_badge_cell` renders `f"{emoji} {label}"` — `🔴 Critical`. The shipped
`_discussion.summary_row` calls `badges.badge_render(...)` with its default `as_label=False`, which
renders emoji + **code** — `🔴 critical`. `badge_render`'s own docstring names the two conventions
(list/panel/summary versus head/pane-title). Sharing the projection therefore changes the summary
table's bytes, which the first acceptance clause forbids. US1's claim that this is "not a behaviour
change either way" is wrong in that one direction.

**Resolution, settled:** the five shipped renderings keep `summary_columns`/`summary_row`
unchanged; the declared views render the label form through `_views.py`. The two derivations
coexist deliberately. Do **not** reconcile them by changing either side — reconciling moves the
frozen bytes. Leave a short comment at `summary_row` and beside the view declarations recording
that the divergence is intentional, so it is not read later as an oversight and unified.

Related fact worth recording in the same comment, because it bears on anyone scoping byte-identity
against a view: **no view can render a status badge at all.** `status` is a base attribute,
`_BASE_RESOLVERS["status"]` returns the stored name, and `project()` types every base code `text`.
That is a property of the record-shape contract (`status_role` is the styling axis), not a gap.

Done when a test would fail if either rendering's bytes moved, and the intentional divergence is
documented at both ends.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-09-01T08:38:11Z] Elias Python:
  - New tests/unit/test_computed_subentity_renderings_are_stable.py pins exact bytes for show/--full/--raw/--json/list-table on a severity finding, plus the badge-line/json in-memory (no-file) proof; badge-divergence documented at summary_row and the view declarations.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Regenerate the template manifest and content store

<!-- sq:subtask:ST7:body -->
Regenerate the template manifest and the content store, last.

`workflow.toml` gains the view declarations, three new `templates/views/*.md.j2` files appear, and
three item templates plus `subentities/block.md.j2` change — all of which the manifest covers.

- **`pyproject.toml` already reads 0.14.0, an unreleased version. Do not run
  `scripts/bump_version.py`.** The version bump before the manifest regeneration is already
  satisfied.
- Only the `0.14.0` manifest entry may move. Diff the manifest and confirm no earlier release's
  entry changed; a regeneration that rewrites a shipped release's entry corrupts it.
- A blob left unreferenced in the content store by this regeneration is expected residue between
  releases — `--check` reports it and passes. Do not add a deletion to clear one; the operator
  clears it at the cut.
- This regeneration must happen with the role-side task's `role.md.j2` change already in the tree
  if that task lands first, and vice versa. Whichever of the two goes last owns the final
  regeneration; the earlier one may need re-running.

Done when `python scripts/gen_template_manifest.py --check` passes, the manifest diff touches only
the `0.14.0` entry, and the override freshness guard test is green.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-09-01T08:38:14Z] Elias Python:
  - Regenerated the manifest (python scripts/gen_template_manifest.py); only the 0.14.0 entry moved, --check passes, 2 expected orphan blobs reported (not cleared, per convention).
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T08:39:36Z] Elias Python:
  - Implemented per the 2026-09-01 ADR-776 amendment: the roll-up is reissued as three freestanding views, the head has no successor.
    
    Removed:
    - `ensure_summary`/`_refresh_head`/`_story_label` calls from `_services/_subentities.py`'s write path (add/status/assignee/update/remove) -- `_write_block_file` now only re-renders the block's own heading.
    - `sq:summary` from `items/{task,feature,review}.md.j2`; the `:head` scaffold from `subentities/block.md.j2`.
    - `_collab.py`'s `_add(markers.SUMMARY, "summary")` search-region entry (`markers.SUMMARY` itself stays, still in `_validators`' structural tag set).
    
    Stayed as migration-only machinery (docstrings now name the exact frozen caller pinning each): `set_head` (`_v0_2_to_v0_3`), `ensure_summary` (`_v0_1_to_v0_2`, twice), `render_summary`, and both `subentities/{head,summary}.md.j2` templates -- none touched.
    
    Views declared (workflow.toml), freestanding as specified, one comment block explaining why:
    - `story_rollup` (feature -> story), `subtask_rollup` (task -> subtask, +Story column), `finding_rollup` (review -> finding, +Severity badge) -- each `source = {kind="subentity", name=...}`, `order_by=["id"]`, field order/labels matching `summary_columns`. Presentation templates at `templates/views/<name>.md.j2` (new files, generic table over `fields`/`groups`, `_(none yet)_` empty state per `milestone_rollup`'s precedent).
    - Verified: `sq workflow views` lists all four bundled views; `sq workflow view finding_rollup <id>` resolves and renders label-form badges (`🔴 Critical`), diverging deliberately from the summary table's code-form (`🔴 critical`) -- documented at both `summary_row` and beside the view declarations, per your instruction not to reconcile them.
    
    Freestanding was right. Verified in code: `_print_item_content` already prints the built-in sub-entity summary unconditionally, then every attached view -- attaching would double-print. `views` is in `WORKFLOW_TOP_LEVEL_SECTIONS` so `selected.views` drops a freestanding one directly, and `_prune_orphaned_type_owned_views` only ever touches a *type-attached* bundled view, so these three are untouched by a type deselect (an accepted tradeoff, not a bug -- flagging per your ask, not deciding it).
    
    Five frozen renderings: new `tests/unit/test_computed_subentity_renderings_are_stable.py` pins exact bytes (not substrings) for `show`/`--full`/`--raw --full`/list-table on a `finding` carrying `severity`, plus a bare-`SubEntity`/`SubentityDetail` proof (no file, no `Item`) that `_subentity_badge_line`/`_subentity_pane_title_raw`/`build_subentity_json` need none of it. None of `_cli/_common.py`/`_cli/_items.py` were touched, so byte-identity holds by construction -- these five never read a body region to begin with.
    
    Manifest regenerated last (your `role.md.j2` change was already in the tree); only the 0.14.0 entry moved, `--check` passes. Two orphan blobs remain in the content store (old `role.md.j2` and `workflow.toml` hashes) -- expected residue per the release-mechanics note, left for the operator's cut, not cleared here.
    
    Consequence, accepted per the task: `sq search`/`sq inbox` narrow -- a sub-entity's status/assignee/story text is no longer scanned (it was only ever visible as roll-up-table prose). Updated `tests/goldens/search_login.json` and `search_login`'s underlying scenario; the sub-entity's own heading (title) is still matched.
    
    Undone: the corpus strip (TASK-849, already on the board) -- deliberately out of scope here, per your note that a live re-materialising write path would have undone it. `tests/meta` had 5 pre-existing-pattern failures, all in `test_override_manifest_and_stamp_freshness.py`, all traced to the 2 legitimate orphan blobs above (confirmed 0 orphans at HEAD before this session); not a regression in this change.
    
    @reviewer for review; @architect re: the freestanding-vs-attached call above.
- [2026-09-01T08:54:57Z] Robert Architect:
  - Ruled, and it changes the delivery. ADR-776 has a third 2026-09-01 amendment: **no bundled sub-entity roll-up view ships** — not freestanding, not attached. Your freestanding-vs-attached call was right on its own terms; the question underneath it was whether a bundled declaration belongs at all, and it does not.
    
    Why: the roll-up's computed successor already ships and you left it untouched (`_print_subentity_summary`, called unconditionally by `_print_item_content`). So the declared view is a second rendering of computed data, reachable only through `sq workflow view` — while naming bundled vocabulary an adopter is free to change. Driven on a scratch squad: an override that is only `[subentity_kinds.finding] fields = []` fails the whole CLI, not just the view. The two buys claimed for it don't land either — an override at `.overrides/templates/views/finding_rollup.md.j2` re-presents `sq workflow view` and changes nothing under `sq review <n> show`; the `[selected]` drop is the un-brick step, not a capability. TASK-830 found this and removed its bundled views for the same reason.
    
    What changes here (small, and mostly subtraction):
    
    - ST1 + ST2 retire: drop the three `[views]` entries and the freestanding-rationale comment block from `workflow.toml`, delete `templates/views/{story,subtask,finding}_rollup.md.j2`. `milestone_rollup` stays exactly as it is — amendment §6 says why the cases separate.
    - ST6 stays as delivered. Keep the badge-convention note at `summary_row`; its "beside the view declarations" half has no home now, so fold what it said into that one note. Drop the three-line view coda at the end of `test_show_full_raw_json_and_list_table_pin_exact_bytes_for_a_severity_finding` — everything above it passes unchanged.
    - Tests asserting the declarations: `test_workflow_views_cli.py::test_the_default_catalog_carries_the_bundled_rollup_views_and_nothing_else`, `test_view_declaration_referential_checks.py::test_milestone_rollup_is_the_one_bundled_view_that_is_type_attached`, and `tests/goldens/workflow_views.json`.
    - ST7 re-runs last, after that and after the role-side task.
    
    ST3/ST4/ST5 are unaffected — the write-path retirement, the migration-only pins and the template strip all stand.
    
    Driven, this is the whole red gate: with the three declarations removed, all 15 coupling failures pass (`test_subentity_field_flags_follow_the_active_spec` 8, `test_workflow_subentity_kinds_cli` 6, `test_badge_collections` 1). The other 4 in your 19 are not the coupling and are yours to close separately — the two marker-count floors (`test_marker_injection_guard`, `test_marker_recognition_across_prefix_casings`) are ST5's region removal costing 2 markers per sub-entity; the two roster-drift ones belong to the role-side change.
    
    @python-dev to apply. @reviewer the review holds otherwise.
- [2026-09-01T09:04:44Z] Elias Python:
  - Applied the ruling (ADR-776, third 2026-09-01 amendment): no bundled sub-entity roll-up view ships, freestanding or attached.
    
    Subtraction:
    - Removed the three `[views.*_rollup]` entries and the freestanding-rationale comment block from `workflow.toml` (byte-identical to before this task now, confirmed via `git diff`). `milestone_rollup` untouched.
    - Deleted `templates/views/{story,subtask,finding}_rollup.md.j2`.
    - Reverted `tests/cli/test_workflow_views_cli.py`, `tests/unit/test_view_declaration_referential_checks.py`, `tests/goldens/workflow_views.json` to their pre-task state (`git checkout`).
    - Dropped the three-line view coda from `test_show_full_raw_json_and_list_table_pin_exact_bytes_for_a_severity_finding` in `tests/unit/test_computed_subentity_renderings_are_stable.py` -- everything above it (the exact-bytes proof for show/--full/--raw/--json/list-table) stands unchanged.
    - ST1/ST2 subtasks moved Done -> Cancelled with the reasoning on each.
    
    Kept: the badge-convention divergence note now lives solely at `summary_row` (`_discussion.py`) -- folded in what the view-declarations comment used to say, since that side no longer exists. ST3/ST4/ST5 stand untouched (write-path retirement, migration-only pins, template strip).
    
    Fixed, mine: the two marker-count floors (`test_marker_recognition_across_prefix_casings.py`, `test_marker_injection_guard.py`) -- both asserted a fixed marker-per-block count that assumed the `:head` region; recomputed (6 markers/block, not 8) and verified against actual production output rather than guessed.
    
    Re-ran the manifest last: `python scripts/gen_template_manifest.py --check` is current, diff touches only the `0.14.0` entry (confirmed by hunk location), 30 artifacts (down from 33).
    
    Numbers against your named baseline:
    - The 15 coupling failures (`test_subentity_field_flags_follow_the_active_spec` 8, `test_workflow_subentity_kinds_cli` 6, `test_badge_collections` 1): all 15 pass now (51/51 across the three files).
    - My 2 marker floors: fixed, both files fully green.
    - The 2 roster-drift ones: not mine, still red, in a file neither tracked nor touched by me (`tests/unit/test_role_base_from_item_dispatches_by_role_kind.py`, a pyright error) plus a newer untracked file from the same concurrent work (`tests/integration/test_role_override_reaches_managed_files_before_a_healing_sync.py`, 2 stray-ticket-ref hits: `§3`, `BUG-8`) -- surfaced in tests/meta's full run but not mine to fix per your file boundaries.
    - `tests/meta` full: 259 passed, 7 failed -- the 2 roster-drift above, plus the same 5 orphan-content-store-residue failures I flagged before your message (unrelated to this reversion; `git diff HEAD` on `content_store.json` shows 2 legitimate orphans from the required manifest regen, expected residue per the release-mechanics note, not cleared here).
    - Targeted (33 files spanning subentities/views/search/inbox/migrations/override/show/json-golden/markers/badges): 495 passed, 0 failed.
    - `uv run --all-extras pyright`: 0 errors on everything I touched; 1 error remains, in the same untracked concurrent-work file named above.
    - `ruff check .` / `ruff format --check .`: clean.
    - `sq check`: clean.
    
    TASK-847 stays InReview.
    
    @reviewer the review holds; @architect confirming the ruling landed as specified.
<!-- sq:discussion:end -->
