---
id: TASK-773
sequence_id: 773
type: task
title: Report a role name diverging from its recorded init name
status: Draft
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-754:implements
description: An sq check rule so an already-damaged squad is told, reading only on-disk
  data and repairing nothing
created_at: '2026-08-21T21:06:35Z'
updated_at: '2026-08-21T21:07:06Z'
---
<!-- sq:body -->
A squad whose operator-set role name was already reverted by an earlier sync has no way to learn
that from `sq` — it sits silently pinned to the bundled default, and the only surviving copy of the
chosen name is in a config table nothing reads after `sq init`. Report the divergence so the adopter
is told.

## What to report

A role item whose `extra.full_name` differs from that slug's `[init.names]` entry in `.squads.toml`.
Both sides are already on disk; this compares them and says so.

Message shape: name the slug, the value the config records, and the value the item currently
carries, so the adopter can act without going digging. Point at the recovery that works — writing
the recorded name into `.overrides/roles/<slug>.toml` as `full_name` and running `sq sync`, which is
the one path that holds.

## Hard boundaries

- **Reads only data already on disk.** No new stored field, no new file, no migration.
- **Makes nothing authoritative.** `[init.names]` stays outside the resolution order per ADR-754 A2:
  it is the input that produced the item's stored name, not a competing source, and this report must
  not turn it into one. A reader of the new rule must not come away thinking the config table wins.
- **Repairs nothing.** No write, no heal, no `--fix`. An automatic restore from `[init.names]` is
  refused by A3, because it would resurrect names adopters have since changed deliberately.
- **Reports absence of a `[init.names]` entry as nothing at all.** A slug the table never covered is
  not a divergence, and neither is a squad with no table.
- **Not a precondition for the underlying fix**, and it must not assume the fix has landed: the rule
  is correct and useful on a squad in either state.

## Level

Pick the issue level deliberately and state the choice in the handoff. The consideration: an
adopter's CI may gate on `sq check`, so an error level turns a historical, already-happened data
loss into a build failure they cannot clear without editing files — whereas a warning tells them
without blocking. Whichever you choose, the reasoning goes in the handoff, not just the code.

## Surfaces

- `src/squads/_services/_validators.py` — the squad-global rule family (`_roster_config_integrity`
  and its neighbours) is the right home for a config-versus-roster comparison; follow that shape
  rather than inventing a new hook.
- `src/squads/_models/_config.py` — where `[init.names]` is modelled, read-only here.
- Tests alongside the existing `sq check` rule coverage.

## Acceptance criteria

- A squad where `[init.names]` records a name and the role item carries a different one is reported,
  naming the slug, both values, and the recovery.
- A squad where they agree reports nothing.
- A squad with no `[init.names]` table at all, and a slug absent from an existing table, both report
  nothing.
- A retired role, and a slug in the table with no roster item, are each handled deliberately —
  covered by a test, whichever way you decide, with the choice stated.
- A developer role is handled deliberately: `sq dev add` does not write `[init.names]`, so state and
  test what the rule does for a dev slug rather than letting it fall out of the implementation.
- The rule reads no file it does not already have in hand and writes nothing — assert that the
  config and every item file are byte-identical after a `sq check` run.
- **This repository's own `sq check` stays clean**: its `.squads.toml` carries no `[init.names]`
  table, so the rule cannot fire here. Confirm that rather than assume it.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Hand your adopter-facing entry text to the tech lead in your handoff
comment and it gets applied there.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 773 add-subtask "<title>"`; track with `sq task 773 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T21:07:06Z] Olivia Lead:
  - Report-only item per ADR-754 A3, linked. Boundaries in the body: reads on-disk data, makes nothing authoritative ([init.names] stays outside the resolution order per A2), repairs nothing, and does not assume the fix has landed. Left the issue level to the dev with the CI-gating consideration spelled out and the reasoning required in the handoff. Pointed at _services/_validators.py squad-global rule family as the home. Noted this repo cannot trip the rule — its .squads.toml carries no [init.names] table (verified).
<!-- sq:discussion:end -->
