---
id: REV-1050
sequence_id: 1050
type: review
title: 'BUG-1046 fix: check reports an invalid role catalog'
status: Approved
author: reviewer
refs:
- BUG-1046
description: Review of the sq check role catalog validation fix
subentities:
- local_id: F1
  title: Wrong-typed sections and non-UTF-8 crash check
  status: Fixed
  severity: medium
- local_id: F2
  title: Per-slug test variant uses an off-roster slug
  status: Fixed
  severity: medium
- local_id: F3
  title: Skip hides catalog-independent per-slug findings
  status: Fixed
  severity: low
- local_id: F4
  title: Playbook loader shares the crash class
  status: WontFix
  severity: low
- local_id: F5
  title: Catalog validated twice; stale docstring
  status: Fixed
  severity: low
created_at: '2026-10-16T11:22:25Z'
updated_at: '2026-10-16T12:21:52Z'
---
<!-- sq:body -->
Review of commit 8797c128 on branch `worktree-agent-adb998e0d11286bfb`: `sq check` now loads the merged role catalog whenever `.overrides/roles.toml` exists and reports a `SquadsError` refusal as an error on that file, skipping the per-slug role checks while the catalog is invalid.

Method: drove every shape below with the worktree build in scratch squads under the session scratchpad (`sq init --default-names`, claude backend), compared with the released 0.15.0 where it mattered, ran the new and changed tests with `-n0` (49 passed), and mutation-tested the changed fixtures through a pytest plugin, with no edits to the worktree.

What holds:
- The bug's reproduction now reports one error on `.overrides/roles.toml`, exit 3 in both `--json` and human output, with and without per-slug files, including with a dev on the roster.
- Refusal shapes outside the test table that the loader turns into a `SquadsError` are all reported: deselecting the default role through `[selected].roles`, a shadowed role with a model outside the vocabulary, a duplicate slug, two defaults, a wrong-typed `[dev]` or `dev = 3`, a non-table `selected`, and a bundle given as a string.
- The developer's claim about workflow and playbook overrides holds for the reporting gap: an unknown key, malformed TOML and wrong-typed tables each come back as a `workflow` or `playbook` error at exit 3.
- Cost: about 0.5 ms per catalog load, measured. `check_override_issues` loads the catalog twice, and only when the override file exists. That is negligible against a check of about 0.8 s.
- The three changed fixtures still catch regressions. Making every override bundle count as a shadow fails the add-only lifecycle test and the uniformity test. Ignoring bundles fails the bundle-shadow test. Each old fixture was an invalid catalog, because a new role left out of `all` is refused, so rewriting them was correct.
- Hygiene: comments are one or two sentences, with no ticket IDs or versions.

What does not hold is in the findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1050 add-finding "…" --severity medium`; track with `sq review 1050 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Wrong-typed sections and non-UTF-8 crash check

<!-- sq:finding:F1:body -->
Some invalid catalogs make `sq check` crash with a traceback instead of reporting an error on `.overrides/roles.toml`. `_roles_catalog_invalid_issue` catches only `SquadsError`, and the loader lets other exceptions through. Each shape below was driven with the worktree build on a fresh default-names squad and no per-slug file. Each printed a Rich traceback to stdout under `--json`, with no JSON and exit 1, where 3 was expected:

- `bundles = ["all"]` gives `AttributeError: 'list' object has no attribute 'items'` (`_build_catalog`, `raw.get("bundles", {}).items()`).
- `bundles = 3` gives `AttributeError: 'int' object has no attribute 'items'`.
- `roles = 3` gives `TypeError: 'int' object is not iterable`.
- A non-UTF-8 byte anywhere in the file gives `UnicodeDecodeError`. `_read_raw_override` catches `TOMLDecodeError` and `OSError`, but `UnicodeDecodeError` is a `ValueError`.

`sq role list` crashes the same way on these files. The released 0.15.0 check already crashed on them too, so the crash is older than this fix. But the bug's expected behaviour is that check reports an invalid merged catalog as an error on the file whenever it exists, and these shapes still do not get one. The new table has no row for a top-level section of the wrong type or for an undecodable file.

Fix: make the loader turn these into `SquadsError`. That means rejecting a non-table `bundles`, a non-array `roles` and a decode error in `_read_raw_override`, which also fixes `sq role list`. Then add these rows to the test table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Per-slug test variant uses an off-roster slug

<!-- sq:finding:F2:body -->
The `per-slug-file` variant does not exercise the path the bug reported, so removing the skip does not fail it. The `project` fixture inits with `roles_spec="minimal"`, so only `manager` is on the roster, and the test writes `.overrides/roles/qa.toml`. For a slug with no roster item, `_check_role_override_resolves` builds no base and catches the refusal itself, so the result is a `qa.toml` error, never the `corpus` error. The test only looks at `roles.toml` and `corpus` items, so that duplicate goes unnoticed.

Measured: a pytest plugin replaced `check_override_issues` with a version without the `catalog_invalid` skip, and all 10 cases of `tests/cli/test_check_reports_an_invalid_role_catalog_override.py` still passed. Under the same change, a minimal-roster scratch squad reported `roles.toml` plus `roles/qa.toml` when the per-slug file was `qa.toml`. When it was `manager.toml`, the squad reported only `corpus: could not scan the corpus` and lost the catalog finding. That `corpus` output is the bug's reproduction.

Fix: write the per-slug file for a slug that is on the roster (`manager.toml` under this fixture), and assert that no issue names a `.overrides/roles/` path.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Skip hides catalog-independent per-slug findings

<!-- sq:finding:F3:body -->
`check_override_issues` skips all of `_check_role_toml_override_issues` while the catalog is invalid. Only its resolve step (`_check_role_override_resolves`) depends on the catalog. The missing-stamp error and the stale-stamp warning read only the file's stamp and the roster item.

Driven: on a default-names squad with a valid catalog, an unstamped `.overrides/roles/qa.toml` (`model = "opus"`) is an error on that file. Add the invalid catalog from the bug's reproduction and check reports only the `roles.toml` error, so the `qa.toml` error stays hidden until the catalog is fixed and check runs again. The exit code is non-zero either way, so nothing passes that should fail. But `sq check` is meant to report everything it can see at once, not stop at the first problem.

Suggested: keep the stamp checks running and gate only the `_check_role_override_resolves` call on the catalog being valid.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Playbook loader shares the crash class

<!-- sq:finding:F4:body -->
The developer is right that workflow and playbook overrides are reported through `open_service`. But the playbook loader crashes the same way as F1 on top-level values of the wrong type. On a default-names squad, `.overrides/playbook.toml` containing `types = 3`, `types = [1]` or `[types]` with `epic = 3` makes `sq check --json` print an `AttributeError` traceback and exit 1. The workflow loader reports every wrong-typed shape tried (`statuses = 3`, `statuses = [1]`, `items = [1]`, `[items] task = 3`) as `workflow config invalid` at exit 3.

This is outside BUG-1046's scope. Recommend a separate bug for the playbook loader.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T12:21:22Z] Mara Tester:
  - Home: BUG-1057 (reproduced on the dev build).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Catalog validated twice; stale docstring

<!-- sq:finding:F5:body -->
Two small points in `src/squads/_overrides/_service.py`:
- `_roles_catalog_invalid_issue` runs twice per check: once in `check_override_issues` for the skip, then again inside `_check_roles_catalog_override_issues`. It costs about 0.5 ms per load, measured, so the cost does not matter, but the duplication does. Computing it once and passing the result in would remove both the second parse and the risk of the two calls disagreeing.
- The docstring of `_check_roles_catalog_override_issues` still says it mirrors the workflow and playbook checks "exactly". It now also validates the merged document, which those two do not do, so that sentence is no longer true.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:23:09Z] Paul Reviewer:
  - Verdict: ChangesRequested, because two medium findings are open. F1: a wrong-typed bundles/roles section or a non-UTF-8 file still crashes check with a traceback (exit 1) instead of an error on roles.toml. F2: the per-slug test variant uses an off-roster slug, so all 10 cases still pass with the skip removed.
  - Lows: F3 the skip hides the catalog-independent stamp checks, F4 the playbook loader has the same crash class (recommend a separate bug), F5 a duplicate catalog load and a stale docstring. The bug repro is fixed, the workflow and playbook reporting claim holds, the cost is negligible and the changed fixtures still catch regressions.
  - @python-dev F1 and F2 to fix, F3 and F5 recommended. @manager F4 needs a bug from qa.
- [2026-10-16T11:27:33Z] Elias Python:
  - Fixed in c268f945 on worktree-agent-adb998e0d11286bfb. F1: loader raises SquadsError for non-table bundles, roles neither array nor table, and non-UTF-8 (rows added; reverting the loader turns 8 of 19 red). F2: per-slug variant uses manager.toml and asserts no .overrides/roles/ issue (without the skip, 10 of 19 red). F3: only the resolve step is skipped; new test covers an unstamped manager.toml. F5: catalog loaded once per check; docstring corrected. F4 left for its own bug.
- [2026-10-16T12:21:50Z] Catherine Manager:
  - Approved: F1–F3 and F5 Fixed (falsification counts on each), F4 WontFix with home BUG-1057. Merged as 52bf5b89; full suite 10,643 passed, 0 failed.
<!-- sq:discussion:end -->
