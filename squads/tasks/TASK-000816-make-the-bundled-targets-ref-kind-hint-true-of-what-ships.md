---
id: TASK-816
sequence_id: 816
type: task
title: Make the bundled targets ref-kind hint true of what ships
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: medium
refs:
- TASK-798:depends-on
- TASK-799:depends-on
- ADR-775:implements
- MILE-836:targets
description: Rewrite the targets hint so the generated cheatsheet stops describing
  a view mechanism that does not exist
subentities:
- local_id: ST1
  title: Rewrite the targets hint to describe the shipped kind
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Refresh the goldens, content store and manifest entry
  status: Done
  assignee: python-dev
  story: US1
created_at: '2026-08-25T22:34:48Z'
updated_at: '2026-08-26T16:00:54Z'
---
<!-- sq:body -->
## Scope

FEAT-790 US1 — the wording of one bundled `[ref_kinds]` entry.

`_specs/workflow.toml:337` declares:

    hint = "A targets B — a membership/milestone edge; the consumer is a declared view naming this kind"

Now that the cheatsheet's kinds table is generated from the merged spec rather than hand-written,
that hint is no longer an internal note. It renders verbatim in `sq workflow`, in the `squads`
skill text every agent reads, in the AGENTS.md and cheatsheet managed sections, and in
`sq workflow ref-kinds --json`. It is adopter-facing output.

It refers to a **declared view** and to a **milestone**. Neither exists. Both are FEAT-693's, which
is not built. So the one bundled entry an adopter is most likely to read as the worked example of a
kind they could have declared themselves explains that kind in terms of a mechanism they cannot
find, cannot use, and will not find documented — and it contradicts its own row, whose Consumer
column already renders "Navigation".

The wording is spec data in `_specs/workflow.toml`, not template prose, so it belongs to whoever
owns `[ref_kinds]` rather than to the writer who reissued the contract text.

## The constraint on the fix

**A hint that promises the mechanism is not a fix.** "will be consumed by a declared view",
"reserved for milestones", or any other forward reference reproduces the defect in the future
tense, and the surfaces it renders into carry no release context to disambiguate it.

State what `targets` is in the shipped tool: a navigational membership edge with no engine binding,
whose meaning is whatever reads it. That sentence is true today and stays true the day FEAT-693
lands, so this entry never has to be revisited for that reason. Keep it to hint length — it sits in
a table cell beside nine siblings, and the sibling hints are the register to match.

The same premise appears in the TOML comment above the section (`_specs/workflow.toml:289`,
"its only consumer is a declared view naming it in its own source"). That one does not render, but
it is the same claim in the same file; correct it in the same pass rather than leaving the file
disagreeing with itself.

## What the text is frozen into

The hint is not only in the spec. Changing it moves, all in one change:

- `src/squads/_rendering/content_store.json` and the `0.14.0` entry of the template manifest —
  `workflow.toml` is one of `gen_template_manifest.py`'s `_SPEC_TOML_NAMES`, so this is a
  manifest-regenerating edit and the freshness guard will fail until it is regenerated.
- `tests/goldens/workflow_ref_kinds.json`, `tests/goldens/workflow_cheatsheet.txt`,
  `tests/goldens/workflow_cheatsheet_raw.txt`, `tests/goldens/agents_md_section.txt`.
- This repo's own generated skill copy, via `sq sync`.

Confirm that list against the tree before starting rather than trusting it: a grep for the hint's
distinctive words finds every carrier, and a carrier missed here shows up as a golden failure.

## Ordering

Do **not** run `scripts/bump_version.py`. `pyproject.toml` is at `0.14.0`, which is unshipped, and
the whole release's regenerations are keyed to it; running the bump again moves them off it.

Two other pieces of work in this release regenerate that same `0.14.0` manifest entry. One key,
last writer wins — so this regeneration has to happen with their content already in the tree, which
is what the `depends-on` edges on this item record.

## Acceptance

- The `targets` hint describes the kind in terms of what ships: navigational, no engine binding.
- It contains no forward reference to a view mechanism, a milestone type, or any other capability
  the tool does not have, in any tense.
- It would still be accurate, and would need no edit, once derived views exist.
- Its length and register match the nine sibling hints; it does not contradict its own rendered
  Consumer column.
- No other bundled ref-kind hint, label, or spec-declared string names an unbuilt capability — a
  sweep of the spec documents for forward-looking prose comes back empty (it does today, apart from
  this entry; confirm it still does).
- Every frozen copy of the text moves with it: the goldens, the content store, the `0.14.0`
  manifest entry, and this repo's generated skill text. The manifest-freshness and
  generated-agent-text guards pass and `sq sync` is a no-op afterwards.
- `scripts/bump_version.py` was not run; `pyproject.toml` still reads `0.14.0`.
- `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 816 add-subtask "<title>"`; track with `sq task 816 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Rewrite the targets hint to describe the shipped kind | US1 |
| ST2 | Done | python-dev | Refresh the goldens, content store and manifest entry | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rewrite the targets hint to describe the shipped kind

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Rewrite the `targets` entry's `hint` in `src/squads/_specs/workflow.toml:337` so it describes the
kind as it ships: a navigational membership edge, no engine binding, its meaning supplied by
whatever reads it.

The current text — "a membership/milestone edge; the consumer is a declared view naming this
kind" — names two things that do not exist, and it renders verbatim to adopters and to every agent
that reads the `squads` skill.

Rules for the replacement:

- No forward reference, in any tense. A hint that promises the mechanism instead of describing the
  kind reproduces the defect.
- True today, and still true unchanged once derived views exist. That is the test — if the sentence
  would need editing the day that feature lands, it is the wrong sentence.
- Hint length and hint register: it sits in a table cell beside nine siblings, and it must not
  contradict its own row, whose Consumer column renders "Navigation".

Correct the same claim in the section comment at `:289` in the same pass, so the file does not
disagree with itself. That comment does not render, but it is the same sentence.

Done when the entry reads as a description of a shipped kind, with nothing in it that depends on
unbuilt work.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Refresh the goldens, content store and manifest entry

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Move every frozen copy of the hint text with the edit, in the same change.

`workflow.toml` is one of `scripts/gen_template_manifest.py`'s `_SPEC_TOML_NAMES`, so the string is
content-addressed into `src/squads/_rendering/content_store.json` and the manifest's `0.14.0`
entry, and it is pinned in four goldens: `tests/goldens/workflow_ref_kinds.json`,
`workflow_cheatsheet.txt`, `workflow_cheatsheet_raw.txt` and `agents_md_section.txt`. This repo's
own generated skill copy moves via `sq sync`.

Find the carriers yourself — grep the tree for the hint's distinctive words rather than working
from that list. A carrier missed here surfaces as a golden failure, so treat a green run of the
goldens plus the manifest-freshness and generated-agent-text guards as the proof, not the list.

Two constraints on the regeneration:

- **Do not run `scripts/bump_version.py`.** `pyproject.toml` is at `0.14.0`, unshipped, and the
  release's regenerations are all keyed to that version.
- The `0.14.0` manifest entry is regenerated wholesale by other work in this release too. One key,
  last writer wins — regenerate with their content already in the tree.

Done when the goldens, the content store, the manifest entry and the generated skill text all
carry the new wording, every guard passes, and `sq sync` is a no-op.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T22:35:59Z] Olivia Lead:
  - Its own task rather than a line on an existing one: the wording is spec data in _specs/workflow.toml, so it belongs to the ref_kinds owner, and every candidate host is already past authoring. Parented to FEAT-790 / US1, where the entry is declared. Swept the spec documents for other prose assuming unbuilt capabilities — targets is the only one.
- [2026-08-25T23:11:13Z] Olivia Lead:
  - Ordering constraint from ADR-777 D1-D3, recorded here because this task regenerates the manifest. The generators write mode still sweeps orphaned blobs, which is destructive whenever [project].version names a version that has already shipped. 0.14.0 is unshipped and untagged, so regenerating today is safe and this task is unblocked.
  - If v0.14.0 is tagged before this lands, it stops being safe: the regeneration would rewrite a shipped entry and sweep that releases own revisions. So either regenerate before the tag, or after TASK-822 removes the sweep. Not filed as depends-on because nothing in this tasks own work waits on TASK-822 — it is a tag-day constraint, not a code dependency.
- [2026-08-26T09:15:54Z] Elias Python:
  - Rewrote both lines in _specs/workflow.toml (:288 comment, :337 hint): targets is now described as a navigational membership edge with no engine binding, meaning set by whatever reads it — no forward reference to a view or milestone; the Consumer column already read Navigation so the two now agree.
  - Regenerated the frozen copies: gen_template_manifest.py (0.14.0 entry only — verified via git diff), content_store.json (one new blob inserted), the four goldens (workflow_ref_kinds.json, workflow_cheatsheet.txt, workflow_cheatsheet_raw.txt, agents_md_section.txt via UPDATE_GOLDENS=1), and sq sync for this repo's skill copy (second sync run is a no-op).
  - Regeneration orphaned the old workflow.toml blob in the content store (0.14.0 untagged, so per the script's own docs this is safe); ran git fetch --tags + seed_content_store.py --rebuild to drop it — 1 dropped, 0 restored, no other version's entries moved. --check and --release-gate both now pass clean.
  - tests/meta full (314→319 after including the golden/cheatsheet-targeted modules) + workflow_raw_markdown_golden + json_output_shape + workflow_ref_kinds_cli + workflow_cheatsheet_static_dynamic_split: 319 passed. pyright/ruff check/ruff format clean. sq check clean.
  - Did not touch docs/workflow.md:611 or docs/overrides.md:534, which carry the same 'declared view naming the kind' claim by hand — out of scope (task named the three spec TOMLs, not docs/); flagging for a follow-up.
  - pyproject.toml still 0.14.0, bump_version.py not run, nothing tagged.
<!-- sq:discussion:end -->
