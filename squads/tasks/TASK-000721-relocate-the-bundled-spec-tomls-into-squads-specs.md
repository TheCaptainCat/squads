---
id: TASK-721
sequence_id: 721
type: task
title: Relocate the bundled spec TOMLs into squads/_specs
status: Done
parent: FEAT-715
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-696:implements
- EPIC-538
- TASK-716:depends-on
description: Pure directory move of the three bundled TOMLs plus the loader, guard
  and packaging sweep
subentities:
- local_id: ST1
  title: Move the three TOMLs and repoint the loaders
  status: Done
  story: US1
- local_id: ST2
  title: Repoint the meta guards and prove the wheel ships them
  status: Done
  story: US2
- local_id: ST3
  title: Sweep stale mentions of the old bundled path
  status: Done
  story: US2
- local_id: ST4
  title: Make the wheel-path packaging assertion actually assert the path
  status: Done
  story: US2
created_at: '2026-07-31T13:37:43Z'
updated_at: '2026-07-31T16:22:47Z'
---
<!-- sq:body -->
## What to build

Relocate the three bundled spec TOMLs so the bundled-vs-override pairing reads symmetrically:
the bundled `workflow.toml` / `roles.toml` / `playbook.toml` sit together in one directory that
mirrors `.overrides/`'s own layout.

This is a **pure relocation**. No change to the content of any of the three files, no change to
override-resolution semantics, no new behaviour. With no override present, behaviour is
byte-identical to today.

## The move

From `src/squads/_bundled/` to `src/squads/_specs/` — i.e. the package the loaders address via
`importlib.resources.files(...)` becomes `squads._specs`. Carry `__init__.py` across (or write
its equivalent) so the directory stays a real package and `importlib.resources` keeps resolving
it the way it does today; the old directory is **gone**, not left as a stale duplicate.

Move the files with `git mv` so history follows them.

## The reference sweep

The scope list this task inherits is broader than the actual reference set, so sweep by
grep rather than by that list, and report what you find. Verified reference sites:

- **The three loaders** — `_workflow/_loader.py`, `_roles/_loader.py`,
  `_interactions/_loader.py` — each holds `importlib.resources.files("squads._bundled")` plus a
  module docstring naming the package. These are the only *path* references in `src/`.
- **`tests/meta/test_bundled_toml_packaging.py`** — its `_ASSETS` table names the package
  string three times. This is also the check that proves the relocated directory still ships in
  the wheel: it asserts each asset is readable via `importlib.resources` **and** present in a
  freshly built wheel. Confirm it still passes for real (it `skip`s when `uv` is missing or the
  build fails — a skip is not a pass; read the outcome, don't assume it).
- **`tests/meta/test_no_bundled_roster_status_literal_outside_the_spec_layer.py`** — its
  `_EXEMPT_DIR_NAMES` exempts `_bundled` and `_migrations`. Repoint the first at the new
  directory name and update the docstring that explains why it is exempt.
- **Doc, docstring, and comment mentions** of the old path anywhere in `src/`, `tests/`, and
  `docs/`.

Two things the inherited list gets wrong, worth confirming rather than trusting either way:

- **The migration runners do not reference this path.** `_v0_4_to_v0_5.py` and
  `_v0_8_to_v0_10.py` import `bundled_skill_slugs` / `skill_description` from `_interactions` —
  a similar *name*, not the bundled package path. Their frozen-literal carve-out (a runner pins
  the vocabulary of the schema version it transforms and must never read the live spec) is
  untouched by a directory move, and this task must not disturb it. Confirm by grep, then say
  so.
- `_services/_maintenance.py`, `_services/_service.py`, `_backends/_claude_code/_backend.py`,
  and `_overrides/_service.py` likewise match only on `seed_bundled_skills` /
  `bundled_template_content` / `_required_markers_from_bundled` — function names, not the
  package path. Verify before editing; do not rename a function to chase a grep hit.

## Packaging

The wheel target ships `packages = ["src/squads"]`, so files inside the package directory are
included without a manifest entry — but **prove it, don't reason about it**: run `uv build` and
confirm all three TOMLs are in the wheel, and that the packaging meta test passes for real
rather than skipping. If the build does need a config change, make the smallest one.

## Acceptance

- The three TOMLs exist at the new location; the old directory no longer exists.
- All three loaders resolve the new location; `uv run --all-extras pytest` is green with no
  path-not-found regressions.
- `uv build` ships all three files as package data, verified through the existing packaging
  check rather than by inspection alone.
- Both `tests/meta` guards pass against the new path, and the roster-literal guard still fires
  when it should (see falsification below).
- No content change to any of the three TOMLs — prove it with a diff of the moved files against
  their previous bytes.
- `sq check` clean.

## Testing

No new behaviour, so no new behavioural test is owed — the existing suite plus the two meta
guards are the instrument. What **is** owed is falsification of the guards you repointed:

- Temporarily plant a bare `"Active"` string constant in a non-exempt module under `src/squads/`
  and confirm the roster-literal guard fails; remove it and confirm it passes. A guard whose
  exemption path was edited without being falsified is a guard that may now exempt everything.
- Temporarily point one `_ASSETS` entry at a filename that does not exist and confirm the
  packaging test fails rather than skipping.

Report both directions in this task's discussion.

## Conventions

- No `from __future__ import annotations` (Python 3.14 / PEP 649); keep the import graph
  acyclic.
- Type aliases use PEP-695 `type X = …`, never bare assignment.
- If a new module-level dict or list appears, `tests/meta`'s mutable-state guard fires —
  allowlist it as a CODE constant with a one-line reason rather than restructuring. Run
  `tests/meta` before handing back.
- Name tests by behaviour. No ticket or item IDs in `src/` or `tests/`, including filenames.
- Errors subclass `SquadsError`; fail closed rather than tracebacking.
- Strict gate, with the extras on every command:
  `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`
  A bare `uv run` prunes the optional `tui` extra and floods pyright with false import errors.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 721 add-subtask "<title>"`; track with `sq task 721 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Move the three TOMLs and repoint the loaders

<!-- sq:subtask:ST1:body -->
Move the three bundled TOMLs and repoint the loaders.

`workflow.toml`, `roles.toml`, and `playbook.toml` move from `src/squads/_bundled/` to
`src/squads/_specs/`, so the package the loaders address via `importlib.resources.files(...)`
becomes `squads._specs`. Carry `__init__.py` across (or write its equivalent) so the directory
stays a real package and `importlib.resources` keeps resolving it exactly as it does today. The
old directory is **gone** afterwards, not left as a stale duplicate.

Use `git mv` so history follows the files. No content change to any of the three — prove that
with a diff of the moved files against their previous bytes, not by inspection.

Repoint the three loaders — `_workflow/_loader.py`, `_roles/_loader.py`,
`_interactions/_loader.py` — each of which holds an `importlib.resources.files("squads._bundled")`
call plus a module docstring naming the package. These are the only path references in `src/`.
If a fourth loader for the playbook override exists by the time this runs, it moves with them.

Acceptance: all three loaders resolve the new location; `uv run --all-extras pytest` is green
with no path-not-found regressions; the moved files are byte-identical to their previous
contents; nothing under `src/squads/` still names the old package.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Repoint the meta guards and prove the wheel ships them

<!-- sq:subtask:ST2:body -->
Repoint the two `tests/meta` guards and prove the wheel still ships the relocated files.

- **`tests/meta/test_bundled_toml_packaging.py`** — its `_ASSETS` table names the package string
  three times. This is also the check that proves the relocated directory still ships as package
  data: it asserts each asset is readable via `importlib.resources` **and** present in a freshly
  built wheel. It `skip`s when `uv` is missing or the build fails, and a skip is not a pass —
  read the outcome rather than assuming it.
- **`tests/meta/test_no_bundled_roster_status_literal_outside_the_spec_layer.py`** — its
  `_EXEMPT_DIR_NAMES` exempts the old directory alongside `_migrations`. Repoint the first entry
  and update the docstring explaining why it is exempt.

The wheel target ships the whole package directory, so files inside it are included without a
manifest entry — but prove it rather than reasoning about it: run `uv build` and confirm all
three TOMLs are in the wheel. If the build genuinely needs a config change, make the smallest
one.

**Falsify both guards after repointing them**, because an exemption path edited without
falsification may now exempt everything:

- plant a bare `"Active"` string constant in a non-exempt module under `src/squads/`, confirm the
  roster-literal guard fails, remove it, confirm it passes;
- point one `_ASSETS` entry at a filename that does not exist, confirm the packaging test fails
  rather than skipping, then restore it.

Report both directions in the parent task's discussion.

Acceptance: both guards pass against the new path and both were observed failing when they
should; `uv build` ships all three TOMLs, verified through the packaging check running for real.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sweep stale mentions of the old bundled path

<!-- sq:subtask:ST3:body -->
Sweep every remaining mention of the old path, and confirm the near-misses are not references at
all.

Grep `src/`, `tests/`, `docs/`, and `CLAUDE.md` for the old directory name and fix each hit:
docstrings, inline comments, and prose. The inherited scope list for this work is broader than
the real reference set, so sweep by grep and report what you actually find rather than editing
the list's entries on faith.

Two claims in that list to confirm and then correct on the record:

- **The migration runners do not reference this path.** `_v0_4_to_v0_5.py` and
  `_v0_8_to_v0_10.py` import `bundled_skill_slugs` / `skill_description` from `_interactions` — a
  similar *name*, not the bundled package path. Their frozen-literal carve-out (a runner pins the
  vocabulary of the schema version it transforms and must never read the live spec) is untouched
  by a directory move, and nothing here may disturb it.
- `_services/_maintenance.py`, `_services/_service.py`, `_backends/_claude_code/_backend.py`, and
  `_overrides/_service.py` likewise match only on `seed_bundled_skills`,
  `bundled_template_content`, and `_required_markers_from_bundled` — function names, not the
  package path. Verify before editing; do not rename a function to chase a grep hit.

Anything adopter-facing under `docs/` must stay adopter-facing: an internal package path belongs
in contributor-facing text, not in a page written for people adopting the tool. If a `docs/` hit
turns out to be internal detail that should never have been published, say so rather than
silently updating the string.

Acceptance: no stale mention of the old package path anywhere in the repo; the two claims above
are confirmed by grep and recorded in the parent task's discussion; `sq check` clean.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make the wheel-path packaging assertion actually assert the path

<!-- sq:subtask:ST4:body -->
The wheel-membership check in `tests/meta/test_bundled_toml_packaging.py` passes while asserting
almost nothing, and this is the check the relocation's acceptance leans on as its proof that the
documents still ship as package data at the path the loaders address.

Two defects, both in the instrument:

- **The package path is never read.** `test_asset_ships_in_the_built_wheel` is parametrized over
  `_ASSETS`, whose first element is the package, but the assertion is
  `any(filename in n for n in names)` — a bare filename substring match against the wheel manifest.
  The asset shipping at *any* wheel path passes. Substituting a package that has never existed
  (`squads._totally_made_up`) leaves it green against the real built wheel.
- **A failed build reports green.** A non-zero build exit calls `pytest.skip`, so a broken build is
  indistinguishable from a passing one in the suite's result.

The companion `test_asset_is_accessible_via_importlib_resources` is path-correct but resolves
against the source tree under an editable install, so it cannot cover the wheel. Between the two,
nothing in the repo asserts that the documents ship at the package path the loaders actually
address: a packaging change that shipped them one directory over would keep the suite green and
break only on an adopter's install.

- Derive the expected wheel path from the table entry already there — `package.replace(".", "/")`
  plus the filename — and assert *that* against the manifest, so changing `package` changes the
  verdict.
- Make a build failure a failure rather than a skip.
- **Falsify both.** A wrong package and a wrong filename must each go red. This is a check that
  passed while asserting nothing, so a fix that is not falsified proves exactly as much as the
  check did.

`pyproject.toml` is **correct and out of scope** — the packaging configuration was never the
problem, and the built wheel does ship the documents at the right path. The defect is in the test.

Acceptance: substituting a wrong package into `_ASSETS` fails the test; substituting a wrong
filename fails it; a build that returns non-zero fails rather than skips; the real wheel still
passes. Each of the first three demonstrated by falsification, not by inspection.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-07-31T16:16:18Z] Elias Python:
  - Fixed via REV-723 F1: assertion now derives the full wheel path from (package, filename) and fails on wrong package/filename; wheel build failure hard-fails instead of skipping; wheel built once per session for all three assets. Falsified both directions (wrong package, wrong filename -> red; simulated build failure -> fail not skip; missing uv -> clean skip) then restored to green.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T15:33:06Z] Elias Python:
  - Moved: git mv src/squads/_bundled/{__init__.py,workflow.toml,roles.toml,playbook.toml} -> src/squads/_specs/ (git diff on the four moved files is empty — byte-identical). Old dir gone.
  - Repointed: 3 loaders (_workflow/_loader.py, _roles/_loader.py, _interactions/_loader.py) — docstring + importlib.resources.files("squads._specs").
  - Guard sweep by grep, not the inherited list: only 3 tests/meta files actually reference the path (test_bundled_toml_packaging.py, test_no_bundled_roster_status_literal_outside_the_spec_layer.py's _EXEMPT_DIR_NAMES, test_bundled_documents_are_splat_ref_addressable.py). test_override_manifest_and_stamp_freshness.py does NOT — it reads squads._rendering (Jinja templates), an unrelated bundled asset; left untouched. Also repointed 3 tests/unit/test_specmerge_*.py helpers with the same literal (not meta guards but real regressions if left).
  - Falsified all three real guards: packaging (bad filename -> both parametrized tests red incl. wheel-membership, not skip; restored -> green), roster-literal (planted "Active" in _util.py -> red; removed -> green, 7 passed), splat-addressability (planted a quoted "a.b" key into the real roles.toml -> red; reverted -> git diff empty, green).
  - uv build: wheel and sdist both ship squads/_specs/{__init__.py,workflow.toml,roles.toml,playbook.toml}; no _bundled remnants in either artifact.
  - Stale-mention sweep (grep, not the list): src/ and tests/ clean of squads._bundled. Remaining 'bundled' hits everywhere are function/var names (seed_bundled_skills, _load_bundled_spec, bundled_template_content, _required_markers_from_bundled) — confirmed by reading, untouched. Migration runners confirmed: only import bundled_skill_slugs/skill_description by name, no path ref, frozen-literal carve-out undisturbed. docs/ had zero hits. CONTRIBUTING.md had 2 stale squads/_bundled/*.toml path mentions (contributor-facing, correctly the place for this detail) — fixed to squads/_specs/.
  - Naming judgement: kept test_bundled_documents_are_splat_ref_addressable.py's name — 'bundled' describes what the docs are (shipped defaults vs. overrides), not where they live; the move doesn't change that. No collision: squads._specs didn't exist before (only _specmerge.py).
  - Gates: pyright 0 errors, ruff check clean, ruff format clean, pytest tests/meta 70 passed no skips, uv build wheel+sdist verified, sq check clean. Also spot-ran the 3 repointed specmerge unit tests + loader/override unit tests (101 passed) — did not run the full suite per brief.
  - No pyproject.toml change needed — packages = ["src/squads"] already covers the new dir; proven by the wheel/sdist listing, not reasoned.
  - FYI, not mine: ADR-696 shows as concurrently modified in git status (another agent's activity) — untouched by me.
  - ST1/ST2/ST3 all Done. Leaving TASK-721 InProgress for you.
- [2026-07-31T15:35:19Z] Catherine Manager:
  - Relocation landed and committed (e1ef838): git recorded all four files as renames, 18 insertions against 18 deletions, uv build confirms squads/_specs/* in wheel and sdist with no _bundled remnants, three tests/meta guards falsified individually, full suite 2230 passed / 6 skipped. Awaiting review.
- [2026-07-31T16:10:14Z] Paul Reviewer:
  - Reviewed on REV-723 — recommended Approve, three findings, none in the moved code. Byte identity, rename history, the reference sweep and all three guard falsifications independently reproduced; the wheel was additionally installed into a clean virtualenv and all three loaders plus sq init driven from it. pyright 0 errors, ruff and format clean, the six repointed test files 99 passed with 0 skips.
  - Two corrections to the record for whoever reads this next: there are three tests/meta files holding the path, not four — test_override_manifest_and_stamp_freshness.py matched only on test function names containing the word bundled and reads squads._rendering, an unrelated asset. And the three tests/unit specmerge helpers did hold the literal and were absent from the inherited scope list; catching them by grep was load-bearing, not incidental.
  - F2 on REV-723 is the one with a live cost: TASK-718 and TASK-716 bodies still send their implementer to src/squads/_bundled/workflow.toml. @tech-lead worth repointing before 718 is dispatched, since the sequencing was arranged specifically so 718 would be written against the final path. @architect ADR-696 Guard clause names the retired path too (F3).
- [2026-07-31T16:15:23Z] Olivia Lead:
  - Added ST4 for the wheel-packaging check REV-723 F1 reports: the assertion matches a bare filename, so the package element of each _ASSETS tuple is never read and the asset shipping at any wheel path passes; separately a failed build skips rather than fails. Acceptance requires the assertion be driven by the package path and demands falsification of a wrong package AND a wrong filename, since this is a check that passed while asserting nothing. pyproject.toml is correct and out of scope — the config was never the problem, the test was.
<!-- sq:discussion:end -->
