---
id: TASK-000089
sequence_id: 89
type: task
title: sq override command group + staleness stamps, hash manifest, and sq check drift
status: Done
parent: FEAT-000014
author: tech-lead
priority: high
refs:
- TASK-000091:blocks
description: scaffold/diff/update/list; override-base stamp; per-release content-hash
  manifest; sq check version-drift warn + missing-marker error
subentities:
- local_id: ST1
  title: override-base stamp + per-release content-hash manifest in package data
  status: Done
  story: US3
- local_id: ST2
  title: 'sq check: version-drift warn + missing-marker error'
  status: Done
  story: US3
- local_id: ST3
  title: sq override scaffold/diff/update/list command group
  status: Done
  story: US3
created_at: '2026-06-12T20:57:11Z'
updated_at: '2026-06-12T22:08:30Z'
---
<!-- sq:body -->
Staleness + authoring-UX task for FEAT-000014 (ADR-000085 §3, the `sq override` group, and Consequences 'sq check gains two override checks'). This is the durable-contract command surface.

**Goal.** Ship the entire user-owned override upgrade path: a provenance stamp, the per-release hash manifest, drift detection in `sq check`, and the `sq override` command group — so an upgrade never silently breaks overrides and the team merges by hand then re-stamps.

**Scope — stamping + manifest.** (1) Scaffolded overrides carry `<!-- squads:override-base:<squads_version> -->` (reuses the managed-file stamping convention; inert to rendering). (2) Ship a **generated per-release content-hash manifest of each bundled template** as package data — used both for drift detection AND to recover the base-version bundled template for the diff Δ-upgrade view. Wire its generation into the build (templates ship as package data; verify in build).

**Scope — sq check (two levels, in `_services/_maintenance.py::check`).** (a) **Version drift → warn**: if an override's `override-base` is older than the running `squads_version` AND the bundled counterpart actually changed between those versions (per the hash manifest), emit `CheckIssue('warn', '<.overrides path>', 'override may be stale: bundled <name> changed since v<base>; run `sq override diff <name>`, merge, then `sq override update <name>`')`. An old stamp alone, with an unchanged bundled counterpart, is **silent**. (b) **Structural breakage → error**: an overridden item/role template missing a required `<!-- sq:* -->` marker region is an `error` (breaks Invariant 3). A valid override is never downgraded to error just for being old, and always renders (no silent fallback to the bundle).

**Scope — sq override group (joins the 1.0 contract; warning text + stamp format are part of it).** `scaffold <name>` — copy the named bundled template (`items/task.md.j2`, `agents/role.md.j2`, …) or a role (`--role <slug>`) into `.overrides/`, stamped with the current `override-base`; refuses to clobber unless `--force`; ONLY command that writes override bodies. `diff [<name>]` — read-only two-delta view: **Δ-mine** (override vs current bundled) + **Δ-upgrade** (base-version bundled, reconstructed from the manifest, vs current bundled); all drifted overrides if no name. `update [<name>]` — re-stamp `override-base` to current `squads_version` and NOTHING else (body untouched — overrides are never auto-rewritten); no name = re-stamp every structurally-valid override (bulk acknowledge). `list` — every present override with kind (template/role), `override-base`, and state (`current`/`drifted`/`broken`).

**Acceptance.** Full staleness loop covered by tests: a drift warning from `sq check` → `sq override diff` renders both deltas → hand-merge → `sq override update` re-stamps and the warning clears; vs a missing-marker override (error). Plus `sq override list`/`scaffold` behaviour (incl. `--force` clobber guard) and the manifest-based base-version recovery. `sq migrate` still never touches `.overrides/`.

**Dependencies.** Builds on T1 (`.overrides/` layout + loader: `scaffold` writes into it, `check`/`diff` read from it) and on T2 for the role surface (`scaffold --role`, role state in `list`). Sequence AFTER T1; T2 can land in parallel but role-override coverage in `list`/`scaffold --role` lands here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 89 add-subtask "<title>"`; track with `sq task 89 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | override-base stamp + per-release content-hash manifest in package data | US3 |
| ST2 | Done |  | sq check: version-drift warn + missing-marker error | US3 |
| ST3 | Done |  | sq override scaffold/diff/update/list command group | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — override-base stamp + per-release content-hash manifest in package data

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq check: version-drift warn + missing-marker error

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq override scaffold/diff/update/list command group

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:54:56Z] Elias Python:
  - Shipped TASK-000089: sq override command group, staleness stamps, and hash manifest.
  - **What was built:**
    - `src/squads/_overrides/_manifest.py` — manifest loader using `importlib.resources`; reads `squads._rendering/templates_manifest.json` (package data); provides `template_changed_since()`, `current_template_hash()`, `bundled_template_content()`, `base_version_template_content()`.
    - `src/squads/_overrides/_stamp.py` — read/write the `<!-- squads:override-base:<version> -->` stamp for template files and the `# squads:override-base:<version>` comment for role TOML files.
    - `src/squads/_overrides/_service.py` — `scan_overrides`, `scaffold_template`, `scaffold_role`, `diff_override`, `update_stamp`, `check_override_issues`; the full staleness loop logic.
    - `src/squads/_cli/_override.py` — the `sq override` Typer sub-typer: `scaffold`, `list`, `diff`, `update`; `list` and `diff` support `--json`.
    - `src/squads/_rendering/templates_manifest.json` — initial manifest for v0.3.0 (20 templates).
    - `scripts/gen_template_manifest.py` — generator script; run before `uv build` on each release.
  - **sq check integration:** two new checks wired into `_services/_maintenance.py::check()` — version-drift WARN + missing-marker ERROR. FEAT-000015 exit-code contract preserved: errors exit 3, warnings exit 0.
  - **FEAT-000013 deferral:** left a comment on FEAT-000013 with the verbatim list of contract surfaces frozen here (layout, precedence, stamp format, diff semantics, manifest, exit codes).
  - **@devops NOTE — BUILD ACTION REQUIRED:** Wire `python scripts/gen_template_manifest.py` into the release pipeline before `uv build` on every release. The manifest (`src/squads/_rendering/templates_manifest.json`) ships automatically as package data (confirmed in wheel). Without running the generator before each release, newly-changed templates will not be recorded and drift detection will be silent. Verify with: `python -m zipfile -e dist/squads-*.whl /tmp/whl/ && cat /tmp/whl/squads/_rendering/templates_manifest.json | head -5`.
  - **Tests:** 63 new tests in `tests/test_override_commands.py` covering: manifest hash functions; stamp read/write (templates + TOML); scaffold (creates, refuses clobber, --force, unknown raises, all item types); scan_overrides (empty, current, broken, role, multiple); diff (Δ-mine, Δ-upgrade, same-version, role, unknown kind); update_stamp (re-stamps, body untouched, skips broken, bulk, role, missing raises); sq check (clean, warn on missing stamp, error on missing markers, exit3/exit0 contract); full staleness loop; migrate does not touch .overrides/; CLI smoke for all four subcommands including --json shapes.
  - **Suite green:** 540 passed, 1 skipped. pyright clean, ruff clean. `uv build` confirms manifest ships.
  - @reviewer Ready for review.
- [2026-06-12T22:01:59Z] Paul Reviewer:
  - Review REV-000097: APPROVED. The sq override group, override-base stamps, hash manifest, and sq check drift integration faithfully implement ADR-000085 §3.
  - Verified (behaviour, not just presence): scaffold stamps current version + refuses clobber + invalidates engine cache; diff renders BOTH Δ-mine and Δ-upgrade; update re-stamps only (body untouched); list reports current/drifted/broken. FEAT-000015 exit-code contract INTACT — warn-level override issues keep exit 0, only missing-marker errors contribute to exit 3, tested both human and --json paths. Marker safety confirmed (stamp not seen by find_markers). sq migrate proven not to touch .overrides/. Suite 540 passed / 1 skipped, pyright+ruff clean, uv build ships manifest + 20 templates, manifest regenerates byte-stable.
  - 5 non-blocking findings (2 medium, 3 low), none high. Recommend closing before 1.0: F1 — add a guard test that the shipped manifest's current-version entry matches the bundle for all 20 templates (today the silent-drift-miss the @devops note warns about is unguarded — feature fails open if the generator isn't re-run); F2 — golden-pin override list/diff --json in tests/goldens per the FEAT-000015/TASK-000084 convention (currently only key-set-asserted). F3-F5 are polish/recorded deferrals. @devops note re: the manual generate-before-build step is real — F1 is the fix that makes it self-enforcing.
- [2026-06-12T22:07:12Z] Elias Python:
  - Closed REV-000097 F1, F2, F3 (F4/F5 deferred as instructed).
  - **F3 (low) — docstring fix**: corrected the exit-code claim in scripts/gen_template_manifest.py — the no-op path exits 0 (not 1); docstring now matches the code.
  - **F1 (medium) — manifest-freshness guard**: added test_manifest_freshness_all_bundled_templates in tests/test_override_commands.py. It walks the installed package-data tree, compares every template's sha256 against the manifest entry for the current version, and asserts no missing / no extra templates. A stale-manifest release (templates changed but script not re-run) now fails the build.
  - **F2 (medium) — golden-pin override list/diff --json**: added inv(['override', 'scaffold', 'items/task.md.j2']) to the golden_squad fixture (no ID counter impact — scaffold writes files, not sq items), then added test_golden_override_list and test_golden_override_diff in tests/test_golden_json.py. Generated tests/goldens/override_list.json (state=current, no timestamps/abs-paths) and tests/goldens/override_diff.json (delta_mine shows stamp prepended, delta_upgrade empty, base_available=true — all deterministic). The override diff golden shape is non-trivial: it pins name/kind/base_version/base_available/delta_mine/delta_upgrade.
  - Suite: 543 passed, 1 skipped (up from 540 — 3 new tests). pyright and ruff clean.
<!-- sq:discussion:end -->
