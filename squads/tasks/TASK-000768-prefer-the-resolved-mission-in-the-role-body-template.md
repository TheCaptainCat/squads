---
id: TASK-768
sequence_id: 768
type: task
title: Prefer the resolved mission in the role body template
status: Draft
author: tech-lead
assignee: python-dev
priority: low
refs:
- ADR-766:implements
description: One-line template precedence flip plus a manifest regen that must follow
  the version bump so the prior release's entry stays intact
created_at: '2026-08-21T19:53:00Z'
updated_at: '2026-08-21T19:53:21Z'
---
<!-- sq:body -->
A one-line precedence change in the generated role body template, and a manifest regeneration whose
ordering relative to the version bump is the real content of this task.

## What changes

`src/squads/_rendering/templates/agents/role.md.j2` renders the mission as:

```
{{ description or extra.get('mission') or "_TODO: describe this role's mission._" }}
```

The item's stored `description` wins over the resolved `extra.mission`. That is the reverse of the
order the roster view uses — `_services/_base.py` builds its `RoleView` with
`mission=it.extra.get(X.MISSION, it.description)`, resolved value first, item field as the fallback.
Flip the template to match: `extra.get('mission')` first, `description` as the fallback, the `_TODO:`
placeholder last.

ADR-766's Consequences call for exactly this, for exactly this reason.

## Why this is separable, and small

Once one writer owns both the item's `description` and `extra.mission`, the two agree and the
precedence is moot — any squad that has synced since that projection landed renders the same text
either way. The change matters only to a squad that has **not** yet synced: today such a squad's
`sq role <slug> show` card prints the declared mission while the body beneath it prints the bundled
one, and this line is why. So the value is real but bounded, and it does not need to travel with the
projection work that makes it moot.

## The ordering requirement — this is the substance of the task

Editing any bundled `.md.j2` invalidates the shipped template manifest
(`src/squads/_rendering/templates_manifest.json`), which records a content hash per template per
release. `scripts/gen_template_manifest.py` regenerates it, and in write mode it performs
`manifest[version] = current_hashes` — a wholesale replacement of **one version's entire entry** —
where `version` is read straight from `[project].version` in `pyproject.toml`.

`pyproject.toml` currently reads `0.13.0`, and the manifest's `0.13.0` entry is the record of what
actually shipped in that release. Regenerating against that version therefore overwrites a released
entry with hashes from an unreleased tree, and `sq override diff` against a 0.13.0 base then compares
an adopter's customised template to content 0.13.0 never contained.

**So the three steps have one correct order, and the order is the deliverable:**

1. The version bump lands in `pyproject.toml` first (`0.13.0` → the release this work ships in).
2. Then the template edit.
3. Then `python scripts/gen_template_manifest.py`, which appends a **new** version key rather than
   rewriting an existing one.

Doing 2 before 1 is what corrupts the record, and it does so silently — the script exits 0 and
prints a success line either way.

### The gate that stops an out-of-order attempt

`tests/meta/test_override_manifest_and_stamp_freshness.py` is the manifest-freshness guard: it
asserts the shipped manifest carries a current-version hash for every bundled template with no
missing, phantom or stale entry. Edit the template without regenerating and that test fails loudly —
which is the desired behaviour, and it is the signal to check the version before reaching for the
script. `python scripts/gen_template_manifest.py --check` reports the same state without writing, and
is the safe way to look.

### The check at the end is the prior entry, not the script's exit code

Running the generator is not the acceptance. **The previous release's manifest entry must be
byte-for-byte intact when this work is finished**, and that is what gets verified:

- The `0.13.0` entry's `agents/role.md.j2` hash must still be
  `1b88019b7bed2f559e757e718a9c095fcb3edd9dff1417d61fbf62895afc6122`, and every other template hash
  under `0.13.0` must be unchanged. A diff of the manifest against the previous commit must show
  **additions only** — one new version key — and no modification inside any pre-existing key.
- A new version key exists, covering every bundled template, with a **different** `agents/role.md.j2`
  hash reflecting the edit.
- No version key is removed.

## Acceptance criteria

- The template renders the resolved mission in preference to the stored description, with
  `description` as the fallback and the `_TODO:` placeholder last.
- A test covers both directions: an item whose `extra.mission` and `description` disagree renders the
  `extra.mission` value, and an item carrying no `extra.mission` still renders its `description`.
  The placeholder still appears when neither is present.
- The three steps were performed in the order above, and the handoff comment states the version the
  manifest key was written under.
- The manifest diff is additions-only, verified as described above — including the named `0.13.0`
  `agents/role.md.j2` hash still being present and unchanged.
- `tests/meta/test_override_manifest_and_stamp_freshness.py` passes, and
  `python scripts/gen_template_manifest.py --check` reports the manifest current.
- No other bundled template's content changes as part of this work — a manifest entry may only differ
  for `agents/role.md.j2`.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Hand your adopter-facing entry text to the tech lead in your handoff
comment and it gets applied there. For this change the honest entry is small, and "no adopter-facing
entry needed" is a valid answer if that is your read — say which you think it is rather than
inventing one.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 768 add-subtask "<title>"`; track with `sq task 768 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:53:21Z] Olivia Lead:
  - Carved out of the projection work and authored on its own so the manifest hazard survives the closing of that task. Verified the mechanism from source rather than from memory: scripts/gen_template_manifest.py write mode does manifest[version] = current_hashes, a wholesale replacement of one version entry, keyed on [project].version from pyproject.toml, which still reads 0.13.0. The manifest already carries a 0.13.0 entry, so a regen today would overwrite a shipped release record and it would exit 0 while doing it.
  - The acceptance is the prior entry, not the script run: the 0.13.0 agents/role.md.j2 hash 1b88019b... must still be present unchanged and the manifest diff must be additions-only (one new version key). Named tests/meta/test_override_manifest_and_stamp_freshness.py as the gate that stops an out-of-order attempt, and --check as the safe way to look without writing.
<!-- sq:discussion:end -->
