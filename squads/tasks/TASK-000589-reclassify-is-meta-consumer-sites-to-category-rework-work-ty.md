---
id: TASK-589
sequence_id: 589
type: task
title: Reclassify is_meta consumer sites to category + rework work_types()
status: Done
parent: FEAT-573
author: tech-lead
assignee: python-dev
refs:
- TASK-588:depends-on
created_at: '2026-07-22T12:18:09Z'
updated_at: '2026-07-22T12:54:09Z'
---
<!-- sq:body -->
## Scope

The core audit. Reclassify every `is_meta`-equivalent consumer site to the PRECISE per-site
category question, and rework the `work_types()` accessor. Depends on the constant-rename task
landing first (uses the `ROSTER_*` vocabulary). Ground the audit with
`grep -rn "item_is_roster\|work_types"`.

Each site today keys on one of two lossy lumps — `item_is_roster()` (roster-vs-not) or
`work_types()` ("non-roster = work + records"). Repoint each at the exact category predicate it
needs. The three category questions (per ADR-541): **is-roster**, **is-work** (burn-down), or
**is-records** (durable). No site may keep relying on "non-roster = work+records" where the real
intent is one specific split.

### `item_is_roster` sites — confirm each is genuinely roster-vs-not

- `_cli/_create.py:203` (self-author bypass), `_services/_validators.py:412` (agent_registered),
  `_services/_roster.py:134`, `_services/_rename.py:38,70` (rename forbidden for roster),
  `_services/_base.py:297,579,587` (slug identity / self-author) — expected to stay roster-vs-not.
- `_services/_items.py:102,248,289` — the `item_is_roster AND != ROSTER_OPERATOR` idiom
  (role/skill get pointer files / slug identity, operator does not). Keep the precise
  role-or-skill intent; confirm the predicate reads cleanly.
- `_tui/_tree.py:40` — tree grouping (roster_root vs work_root). Per ADR-541 records get their
  OWN group; this is a 3-way question. COORDINATE with FEAT-570 (UI-tree records-root work) —
  do NOT independently rewrite the tree-grouping site if FEAT-570 owns it. Confirm ownership at
  kickoff and leave a comment.

### `work_types()` sites — split by the precise question, then rework the accessor

`work_types()` = "every type whose category isn't roster" — the "non-roster = work + records"
lump. Per site, decide: does it want **is-work** (burn-down only, records excluded), or
**non-roster / creatable-trackable** (work + records, a legitimate need)?

- `_cli/__init__.py`, `_cli/_create.py` — dynamic `sq <type>` command registration. Records
  (decision/guide) ARE creatable/trackable -> genuine non-roster need.
- `_interactions/_loader.py` — playbook coverage. Determine whether the playbook covers work only
  or work+records, and point at the matching predicate.
- `_cli/_items.py:276,298`, `_services/_retype.py:44`, `_services/_rename.py` — retype/rename
  eligibility. Decide is-work vs non-roster per the retype contract.
- `_tui/_search.py:72`, `_tui/_filter.py:32,91` — search/filter type lists.
- `_cli/_items.py:142` — retype/remove availability (`item_is_roster` + `ROSTER_TYPES` fallback).

Rework outcome: `work_types()` either (a) is removed entirely if every site becomes a precise
category predicate, or (b) is renamed to a category-accurate name (e.g. a non-roster/creatable
accessor) for the few genuine "work+records" needs — plus add an is-work / is-records predicate
on `WorkflowSpec` where a site needs the narrow split. Do NOT leave a mis-named `work_types()`
that actually returns work+records. Update the module-level `_workflow.__init__` wrapper +
`__all__` and the tests in `test_workflow_reserved_vocab.py` accordingly.

## Constraints

- Behaviour-preserving: byte-identical output for the bundled spec (roster / work / records
  assignments are unchanged, so every reclassified predicate yields the same set today). This is
  a reclassification for correctness under custom specs, NOT a behaviour change. `sq check`,
  generated skills, backend pointer files, and both UI trees unaffected for the bundled spec.
- A dropped/renamed/re-prefixed custom type must be absorbed cleanly by every audited site — no
  orphan, no traceback (EPIC-538 invariant). Add/keep a test for that where practical.
- No ticket IDs in source/test names.
- Prose/docstring purge is a separate task; here only touch wording the reclassification
  mechanically rewrites.

## Gates (dev must run)

The `tui` extra MUST be installed or pyright reports ~304 false textual errors and `tests/tui`
breaks. Run all gates with `uv run --all-extras`:

`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 589 add-subtask "<title>"`; track with `sq task 589 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T12:35:29Z] Elias Python:
  - Confirmed FEAT-570 owns _tui/_tree.py's 3-way records-root grouping; left it untouched (still 2-way roster/work via item_is_roster, correct as-is pending 570).
  - Reclassified every non-roster call site to the precise question: item_is_roster stays roster-vs-not everywhere (already precise); work_types() was universally the non-roster/creatable meaning at every genuine call site (sq create registration, retype/rename eligibility, playbook coverage, TUI search/filter), so renamed WorkflowSpec.work_types()/module wrapper -> non_roster_types() rather than adding an unused narrow is-work split (no site needed it).
  - sq check byte-identical; full suite green; is_meta literal + _meta_compat.py untouched.
<!-- sq:discussion:end -->
