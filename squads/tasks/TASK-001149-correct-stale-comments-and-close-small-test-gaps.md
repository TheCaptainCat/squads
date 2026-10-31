---
id: TASK-1149
sequence_id: 1149
type: task
title: Correct stale comments and close small test gaps
status: Done
author: tech-lead
refs:
- MILE-1051:targets
- REV-1010:addresses
- REV-1029:addresses
- REV-130:addresses
- REV-105:addresses
- REV-302:addresses
- REV-236:addresses
- REV-191:addresses
- REV-201:addresses
- REV-460:addresses
description: 'Hygiene: stale comments and docstrings, client JSDoc width, README completion
  note, RUF029, six small test gaps'
subentities:
- local_id: ST1
  title: Correct the role-base and missing-body-region comments
  status: Done
- local_id: ST2
  title: Wrap client doc comments at 100 columns
  status: Done
- local_id: ST3
  title: Tighten the README shell-completion note
  status: Done
- local_id: ST4
  title: Pin repair padding from filenames and renumber stem width
  status: Done
- local_id: ST5
  title: Pin the workload exclusion of role and skill items
  status: Done
- local_id: ST6
  title: Cover seeded init and the 0.1 review shape in tests
  status: Done
- local_id: ST7
  title: Pin workflow --raw output under forced colour
  status: Done
- local_id: ST8
  title: Run RUF029 by enabling ruff preview for that rule alone
  status: Done
- local_id: ST9
  title: Correct the CLAUDE.md claim that loads fold extra.ref_kinds
  status: Done
- local_id: ST10
  title: Correct docstrings that call wired behaviour a later task
  status: Done
created_at: '2026-10-25T19:56:59Z'
updated_at: '2026-10-26T09:13:44Z'
priority: low
---
<!-- sq:body -->
## Goal

Comments, docstrings and docs say what the code does today, and a handful of small test gaps that reviews recorded are closed. No behaviour change anywhere in this task: if a subtask finds it needs one, it stops and says so.

## Owners

ST1, ST4 to ST10 python-dev; ST2 typescript-dev; ST3 tech-writer. The subtasks are independent and can run in any order.

## The test suite rebuild

FEAT-1096 is rebuilding the suite. The tests added here go into today's tree; the handoff for each test subtask lists the new test names so the rebuild's parity ledger (TASK-1111) carries them forward.

## Gates

Python: `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`, `pytest` on the touched directories with `-n 4`. Client: `npm run lint` and `npm test` in `clients/vscode`. `~/.local/bin/sq check` clean. Every new test fails when the property it pins is broken (falsify before handoff). No ticket ids in source, tests or docs; comments one or two sentences, stating present truth.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1149 add-subtask "<title>"`; track with `sq task 1149 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Correct the role-base and missing-body-region comments

<!-- sq:subtask:ST1:body -->
Owner: python-dev. Carries REV-1010 F8 and a stale comment found in `_cli/_role.py`.

- `src/squads/_cli/_role.py`, the comment above `role_base_for_show` in `show_role`: it says an unactivated developer slug "falls back to the generated pool name", but `role_base_for_show` returns `None` for any slug with no item. Reword it to what happens.
- `tests/service/test_body_written_reports_exactly_what_a_first_body_write_would_replace.py`, the `_NOT_GUARDED` comment: it says `body -m` on a file with no body region ends in an unhandled `KeyError`. Drive that state first and write down what happens now (a clean refusal or a restored region). If `body -m` now has a first-write answer for it, drop the state from `_NOT_GUARDED` so the guard is compared against it; otherwise reword the comment to the actual outcome.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-26T08:23:25Z] `python-dev` Elias Python:
  - Handoff. The `show_role` comment in `_cli/_role.py` already says what happens today (an unactivated slug resolves through the catalog, `None` here), so it needed no edit. Drove the no-body-region state: `set_body` ends in a clean `SquadsError` refusal, not a KeyError. Dropped `_NOT_GUARDED` and its stale comment from the body_written guard test, so the no-body-region state is now compared against the first-write answer (108 cases pass). No new test names.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Wrap client doc comments at 100 columns

<!-- sq:subtask:ST2:body -->
Owner: typescript-dev. Carries REV-1029 F5.

The client's `printWidth` is 100 and Prettier does not rewrap comments. Rewrap the doc-comment lines over 100 columns: the `buildCommentHtml` JSDoc in `src/domain/previewDocument.ts` (134 columns), and the other comment lines over 100 found on HEAD in `src/domain/boardView.ts`, `metaView.ts`, `statusRole.ts`, `typeCategory.ts`, `src/sqAdapter.ts` and `src/types.ts`. Comments only; code lines are Prettier's.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-26T08:34:32Z] `typescript-dev` Ada Typescript:
  - Rewrapped every comment line over 100 columns in clients/vscode/src: itemPreviewManager.ts, types.ts, sqAdapter.ts, domain/boardView.ts, statusRole.ts, metaView.ts, typeCategory.ts, domain/previewDocument.ts. Wording unchanged; code lines untouched. awk finds no comment line over 100; lint clean, npm test 746 passed.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Tighten the README shell-completion note

<!-- sq:subtask:ST3:body -->
Owner: tech-writer. Carries REV-130 F2.

The README's shell-completion note says completion does not work through `uv run sq` because "uv run wraps the entry point in a way that the shell cannot discover". The real reason is that the shell completes a command named `sq` on the PATH, and `uv run sq` is not one. Reword that sentence; leave the install steps as they are.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-26T08:13:35Z] `tech-writer` Theo Writer:
  - Done. README note reworded: the installed script registers completion for a command named sq and runs sq from PATH, so it does not apply to uv run sq (the shell completes uv). Checked against sq --show-completion zsh (compdef _sq_completion sq; the hook execs sq). Install steps unchanged; doc guards 32 passed at -n 4.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Pin repair padding from filenames and renumber stem width

<!-- sq:subtask:ST4:body -->
Owner: python-dev. Carries REV-105 F2 and REV-302 F2.

- Repair raises the padding from the filenames: rename a created item file to a 7-digit stem (`TASK-0000007-...md`) with the stored padding at 6, run `sq repair`, assert the index padding is 7. Where: the padding recompute in `_services/_maintenance.py` repair.
- Renumber keeps filename stems padded: in `tests/integration/test_renumber_cli.py`, assert the renamed file's digit run has the index's padding width (not just that it is digits), and add a case where an item below the shifted block refers to a shifted item and the ref is rewritten.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-26T08:23:29Z] `python-dev` Elias Python:
  - Handoff. New tests: `test_repair_raises_the_stored_padding_to_the_widest_filename_stem` (tests/integration/test_repair_integrity.py) and `test_renumber_pads_renamed_stems_to_the_index_padding_and_rewrites_refs_from_below` (tests/integration/test_renumber_cli.py); `test_renumber_shifts_a_block_and_rewrites_refs_and_files` now asserts the stem digit width equals the index padding. Falsified: repair padding set to the stored floor only fails the repair test; hard-coding the renamed stem width fails both renumber tests; skipping the id rewrite fails both renumber tests.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Pin the workload exclusion of role and skill items

<!-- sq:subtask:ST5:body -->
Owner: python-dev. Carries REV-236 F2.

Workload excludes roster items. Only the operator leg is pinned (`tests/service/test_operator_lifecycle.py`). Add assertions that role and skill items assigned or authored in the squad do not appear in `sq workload` (service and `--json`), with a work item beside them that does.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-26T08:23:32Z] `python-dev` Elias Python:
  - Handoff. New tests: `test_workload_leaves_out_role_and_skill_items_even_when_assigned` (tests/service/test_search_and_workload_views.py) and `test_workload_cli_json_leaves_out_role_and_skill_items` (tests/cli/test_blocked_workload_search_cli.py), each with work items beside the roster items. Falsified by removing the roster skip in `workload`: all three workload tests fail.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Cover seeded init and the 0.1 review shape in tests

<!-- sq:subtask:ST6:body -->
Owner: python-dev. Carries REV-191 F3, REV-201 F5 and REV-130 F1.

- The default `project` fixture in `tests/conftest.py` inits with `_skip_skill_seed=True`, so most of the suite never runs the production default. Add a seeded fixture beside it, comment the default as the unseeded one, and move one or two end-to-end CLI tests (init, then create, list and check) onto the seeded fixture.
- `tests/fixtures/corpus/v0_1/` has no `reviews/` folder, so no corpus review exercises the 0.1 to 0.2 findings-skeleton insertion. Add one REV file in the pre-0.2 shape (a prose `## Findings` section, no `:findings` markers) and extend the corpus migration test to assert the skeleton and summary after `sq migrate up`.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-26T08:23:50Z] `python-dev` Elias Python:
  - Handoff, partial. Done: the 0.1 review shape. `tests/fixtures/corpus/v0_1/` gains `reviews/REV-000006-auth-module-review.md` (prose `## Findings`, no `:findings` region) and its index entry; goldens under `tests/goldens/migrated_corpus/v0_1/` regenerated (the skill ids there shift by one, expected); the corpus README line updated. New test: `test_a_pre_0_2_review_gains_an_empty_findings_container_and_keeps_its_prose` (tests/integration/test_migration_corpus.py), falsified by skipping the skeleton insertion. Finding: after `sq migrate up` the review has the empty findings container but NO summary region (ensure_summary writes none for zero findings), so the test asserts the container and the absence of a summary rather than a summary.
    NOT done: the seeded-init fixture. Seeding shifts every global id and the whole suite's expectations, and the brief and CONVENTIONS push to leave the default fixture alone; adding a seeded fixture plus moving end-to-end tests onto it is a design call (fixture name, which tests, id shift) that I did not make. Leaving this subtask at InProgress for @tech-lead to decide.
- [2026-10-26T08:25:27Z] `python-dev` Elias Python:
  - Correction to my earlier comment: the seeded-init part is now done too, so nothing is left. `tests/conftest.py` gains a `seeded_project` fixture (init with the bundled skills seeded) beside `project`, whose docstring now names it the unseeded default. New test: `test_a_seeded_squad_creates_lists_and_checks_clean` (tests/cli/test_a_seeded_squad_creates_lists_and_checks_clean.py): seeded init, skills present, create, list, check clean; falsified by swapping in the unseeded `project` fixture (the precondition fails). No existing test was moved, so no id expectations changed. Gates: pyright 0 errors, ruff check and format clean on src and tests, pytest -n 4 green on every tests directory (the new file and the conftest docstring were verified on tests/meta and the file itself after the last full pass).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Pin workflow --raw output under forced colour

<!-- sq:subtask:ST7:body -->
Owner: python-dev. Carries REV-460 F1.

`sq workflow --raw` prints no escape codes even when colour is forced. The autouse fixture strips `FORCE_COLOR`, `CLICOLOR_FORCE` and `PY_COLORS`, so today's test cannot tell. Add one test in `tests/cli/test_workflow_raw_markdown_golden.py` that sets `FORCE_COLOR=3` for its own run (monkeypatch after the fixture) and asserts no ANSI escape and no box-drawing in the output. If the fixture makes that impossible, say so in the handoff instead of weakening the fixture.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-26T08:23:36Z] `python-dev` Elias Python:
  - Handoff. New test: `test_workflow_raw_has_no_escape_codes_even_when_colour_is_forced` (tests/cli/test_workflow_raw_markdown_golden.py). The autouse fixture is not weakened: the shared console is built once at import, so an in-process FORCE_COLOR cannot reach it; the test runs the installed `sq` in a subprocess with FORCE_COLOR=3 and TTY_COMPATIBLE removed, asserts the non-raw render does carry escapes (precondition), then that `--raw` has no escape and no box-drawing. Falsified by printing the raw path through rich Markdown: it fails.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Run RUF029 by enabling ruff preview for that rule alone

<!-- sq:subtask:ST8:body -->
Owner: python-dev. ADR-153 puts `RUF029` (async function without `await`) in the lint set, but it is a ruff preview rule and `pyproject.toml` enables no preview, so `select = ["RUF", …]` never runs it.

**Recommendation: enable it, preview scoped to that one rule.** The ADR already says the rule runs only with preview enabled for it, and dropping it would leave the async-colouring check unenforced. In `[tool.ruff.lint]`: `preview = true`, `explicit-preview-rules = true` (so only preview rules selected by exact code run; the `RUF` prefix does not pull in other preview rules), and `extend-select = ["RUF029"]`. `[tool.ruff.lint] preview` affects lint only, not `ruff format`.

**Measured on release/0.17 HEAD (2026-10-25, ruff 0.15.16, read-only runs):** with that configuration every new finding is `RUF029`; no other rule changes. `src/` has 2 hits, both async-signature conformance, which ADR-153 allows a targeted `# noqa: RUF029` for: `_async` in `_wrap_sync` (`_migrations/_registry.py`) and the 0.16 to 0.17 `migrate` runner (`_migrations/_v0_16_to_v0_17.py`; that noqa goes when TASK-1153 ST5 gives the runner real IO). `tests/` has 178 hits: async test functions with no `await`, which `anyio_mode = "auto"` runs on the event loop. Add `RUF029` to the `"tests/*"` per-file ignores rather than rewriting them while FEAT-1096 rebuilds the suite; say so in the comment above the ignore.

A bare `ruff check .` also lints `.claude/worktrees/` (untracked, not gitignored) and reports several hundred more hits there; run the gate from a tree without worktrees, or with `--exclude .claude`, when comparing counts.

**Test.** `uv run --all-extras ruff check .` clean with the new config; then remove one `noqa` and confirm `RUF029` fires on it (proves the rule is live), restore.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-26T08:23:39Z] `python-dev` Elias Python:
  - Handoff. pyproject.toml `[tool.ruff.lint]`: `preview = true`, `explicit-preview-rules = true`, `extend-select = ["RUF029"]`, and RUF029 added to the `tests/*` ignores with a comment. `ruff check src tests` found one src hit, `_async` in `_wrap_sync`, now `# noqa: RUF029`; the 0.16 to 0.17 runner has real IO and needs no noqa. Proved live: removing that noqa makes RUF029 fire (1 error), restored. Format check unaffected. pyright 0 errors, ruff check and format clean on src and tests.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Correct the CLAUDE.md claim that loads fold extra.ref_kinds

<!-- sq:subtask:ST9:body -->
Owner: python-dev.

`CLAUDE.md` ("Conventions / gotchas", the "Refs carry their kind inline" bullet) says the pre-0.2 `extra.ref_kinds` map "is read transparently and folded by `from_frontmatter`". It is not: `Item.from_frontmatter` reaches `fold_legacy_kinds` through `_read_refs`, which always passes an empty map (`_models/_item.py`), so a stored `extra.ref_kinds` is never read on load. Only the migrations fold it (`_migrations/_v0_1_to_v0_2.py`, `_migrations/_v0_15_to_v0_16.py`).

- Reword the bullet: the legacy map is folded by `sq migrate up`, and the read path does not read it.
- The bullet sits in the hand-written part of `CLAUDE.md`, above the `squads:start` marker, so no template, manifest or golden changes; check that `claude_section.md.j2` carries no copy of the claim.
- `fold_legacy_kinds`' `legacy` parameter and its docstring ("whether it arrived via the legacy map") describe a map no live caller passes. Drop the parameter and the clause, or reword the docstring; state the choice in the handoff. No behaviour change either way.

**Test.** None new; `tests/meta` and `tests/unit` on `_models/_item.py` pass. Grep the removed wording across the repo after the edit.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
- [2026-10-26T08:23:43Z] `python-dev` Elias Python:
  - Handoff. CLAUDE.md bullet reworded: the legacy map is folded by `sq migrate up` only, the read path never reads it (hand-written part only; `claude_section.md.j2` carries no copy of the claim). Choice on `fold_legacy_kinds`: dropped the `legacy` parameter (single caller passed `{}`), docstring rewritten; also removed the `{}` in the meta test's sample source. tests/meta and tests/unit pass. Grep for the old wording finds it only in this task's own body.
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Correct docstrings that call wired behaviour a later task

<!-- sq:subtask:ST10:body -->
Owner: python-dev. Three docstrings call wired behaviour "not yet wired" or "a later task".

- `_workflow/_models.py`, `SubentityKindSpec.placeholder`: says the `None` fallback derivation is "not yet wired — a later task". It is wired: `_discussion.body_placeholder` falls back to `_generic_placeholder(kind)`. Say that `None` falls back to the generic kind-derived placeholder (`_discussion.body_placeholder`).
- `_services/_import.py`, module docstring: "The CLI command itself is a separate concern (a later task)". `sq import` exists (`_cli/_import.py`). Name it instead.
- `_services/_results.py`, the pre-pass result docstring: "exactly what `--dry-run` (a later task) prints". `--dry-run` exists (`_cli/_import.py`, `_result_json(..., dry_run=...)`). Drop the parenthesis.

Before handing back, scan `src/` for the same class ("not yet", "later task", "a later") with whitespace-collapsed docstrings, not a line grep, and fix or list each further hit.

**Test.** None; comments only.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
- [2026-10-26T08:23:46Z] `python-dev` Elias Python:
  - Handoff. Fixed the three docstrings: `SubentityKindSpec.placeholder` (falls back to `_discussion.body_placeholder`), the `_services/_import.py` module docstring (names `sq import`, `_cli/_import.py`), and the `--dry-run` parenthesis in `_results.py`. Whitespace-collapsed scan of src for "not yet", "later task", "a later" and similar: every other hit is legitimate (e.g. "not yet migrated", "a later read"); no further stale hit.
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T22:06:40Z] `tech-lead` Olivia Lead:
  - Added ST8 (RUF029 not active: recommend enabling preview for that rule alone; measured 2 src and 178 test hits), ST9 (CLAUDE.md wrongly says loads fold extra.ref_kinds; the line is outside the managed region, so no template or golden change) and ST10 (three docstrings call wired behaviour a later task), all from the 2026-10-25 ADR audit.
- [2026-10-26T09:13:44Z] `manager` Catherine Manager:
  - All ten subtasks Done; REV-1161 Approved with F1–F3 Verified; full suite 15620 passed, pyright 0 errors at 7ac783a4. Accepted under the operator's delegation.
<!-- sq:discussion:end -->
