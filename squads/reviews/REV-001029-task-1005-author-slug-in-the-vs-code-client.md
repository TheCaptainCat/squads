---
id: REV-1029
sequence_id: 1029
type: review
title: 'TASK-1005: author_slug in the VS Code client'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1005:addresses
- FEAT-980:addresses
description: Review of the client's optional author_slug guard, preview render and
  canary coverage
subentities:
- local_id: F1
  title: Canary's sub-entity half checks nothing
  status: Fixed
  severity: medium
- local_id: F2
  title: Optional author_slug in canary breaks file's own policy
  status: Fixed
  severity: low
- local_id: F3
  title: 'squadDir comment: stale branch, inexact -C'
  status: Fixed
  severity: low
- local_id: F4
  title: Older-payload test runs on a mixed fixture
  status: Fixed
  severity: low
- local_id: F5
  title: New doc-comment lines exceed 100 columns
  status: Fixed
  severity: low
created_at: '2026-10-16T08:12:14Z'
updated_at: '2026-10-16T08:17:17Z'
---
<!-- sq:body -->
Review of the VS Code client change that reads an optional `author_slug` on discussion entries and shows it in the preview (ADR-979 decision 5). Scope: the uncommitted diff under `clients/vscode`. `docs/` and `CHANGELOG.md` are out of scope.

## What holds

- **Guard.** `isSqDiscussionEntry` accepts an absent key or a string and rejects `null`, a number and an object. The engine always emits a string (`_discussion.comment_json`), so rejecting `null` blanks nothing a real `sq` sends. The table runs at item and sub-entity level.
- **Render.** The slug appears only when non-empty and different from the name, and it is escaped like the name. The exact-HTML rows cover the ADR's cases, and the empty-slug row goes beyond them.
- **Stylesheet.** `.sq-comment-slug` sets only the monospace family, which matches the `code` rule. It takes the muted colour and the smaller size from `.sq-comment-header`.
- **Export.** Exporting `isSqDiscussionEntry` follows the other guards the canary already imports from `sqAdapter`.
- **Deleted escaping test.** Its coverage is replaced. The escaping row asserts the exact header for an escapable name and slug, which is stronger than the old `toContain` and `not.toContain` checks. The old test's title also named the timestamp, but it never fed an escapable one, so nothing was lost there.
- **Exact key set.** The canary will go red on the next key the engine adds to a discussion entry. That is the file's stated policy for tree, graph and list ("a superset assertion cannot fail on an added key"). ADR-1025's open set is about a key's values, not new keys. An addition under Tier 3 is still meant to turn this layer red so that the client decides to model the key or to ignore it.
- **Hygiene.** The new comments and test names carry no ticket IDs and no versions.

## Gates (driven)

- `npm run check`: clean.
- `npm test`: 35 files, 705 tests passed.
- `npm run test:canary`: 76 passed, run against `.venv/bin/sq` (the dev build; its `--version` prints 0.15.0).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1029 add-finding "…" --severity medium`; track with `sq review 1029 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Canary's sub-entity half checks nothing

<!-- sq:finding:F1:body -->
`test/canary/skewCanary.test.ts`: the live test is named "every discussion entry, on the item and on a sub-entity, has the keys the client reads", but the sub-entity loop never runs. The scratch task has no sub-entity: `beforeAll` runs no `add-subtask`, so `parsed.subentities` is empty. The loop also reads `sub.discussion ?? []`, so a sub-entity without a `discussion` key would pass too.

Sub-entity discussion is a separate emission site in the engine (`build_subentity_json` in `_cli/_common.py`, alongside `build_item_json`).

**Failure scenario.** An engine change drops or renames `author_slug`, or `discussion`, on sub-entity entries only. The canary stays green while its name claims the case is covered. The unit tests in `sqAdapter.test.ts` exercise only the client guard against hand-written payloads, never the live shape.

**Fix.** In the test, add a subtask to the scratch task and post a sub-entity-scoped comment on it (`sq task <n> subtask ST1 comment`). Assert that `sub.discussion` is present and non-empty before the loop, and drop the `?? []`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T08:16:07Z] Ada Typescript:
  - Fixed: the live canary adds a subtask and a sub-entity comment, asserts non-empty sub.discussion, no fallback. Falsified: removing the sub comment turns the canary red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Optional author_slug in canary breaks file's own policy

<!-- sq:finding:F2:body -->
`assertDiscussionEntryKeys` requires `author_slug` only when the entry already has it. The file header states the opposite rule for keys that are optional in the client: `badges` and `anchor` are "required here on purpose: this layer's job is to describe what the current `sq` actually emits, not what the client can survive."

**Failure scenario.** A dev-build change stops emitting `author_slug`. The canary passes, because an entry without the key matches the fallback set. The only thing that catches the regression is the Python golden.

The task brief asked for a canary that passes with and without the key, so the divergence is deliberate. It is not written down, though, and the next reader will see it as inconsistent with the precedent a hundred lines above. **Fix:** either add a sentence to the `DISCUSSION_ENTRY_KEYS` comment explaining why this key diverges from the `badges`/`anchor` rule, or require the key and accept that the canary goes red against a pre-slug `sq`, as it already would for tree nodes.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T08:16:08Z] Ada Typescript:
  - Fixed: author_slug is required in the canary key set; self-test row flipped. Falsified: the canary against released sq 0.15.0 (no key) goes red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — squadDir comment: stale branch, inexact -C

<!-- sq:finding:F3:body -->
`src/domain/squadDir.ts`, the doc comment on `resolveSquadDir`: it still says it "mirrors `_paths.py::resolve`'s config-walk-up branch". Today `resolve` has one path, the `.squads.toml` walk-up from `client_cwd` (read, `_paths.py:119`), so "branch" implies alternatives that no longer exist.

The new clause, "`sq` selects the squad with `-C <path>`", is also inexact. `-C` sets the directory the walk-up starts from. It does not name a squad directly.

**Failure scenario.** A reader looks in `_paths.py` for the other branches, or assumes `-C` takes a squad directory and passes one.

**Fix.** Use the wording the writer suggested on the task: "Resolve the active squad directory for workspaceRoot, or undefined when no .squads.toml is found (mirrors _paths.py::resolve, the .squads.toml walk-up)."
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T08:16:09Z] Ada Typescript:
  - Fixed: comment reworded to the writer's text.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Older-payload test runs on a mixed fixture

<!-- sq:finding:F4:body -->
`test/fixtures/show-json.json` now carries `author_slug` on its first discussion entry and not on its second. No real `sq` emits that mix: the dev build puts the key on every entry, and a pre-slug `sq` puts it on none. The test in `sqAdapter.test.ts` that uses this fixture is titled "accepts the committed older-sq payload, where one entry has no author_slug".

**Failure scenario.** A reader takes the fixture for a captured older payload, or for a current one, and reasons from it about what `sq` emits. Neither reading is true. The all-absent case, which the task's "older payload" bullet asks for, is covered only by the hand-written key-absent rows, not by a committed payload.

The brief asked for the mix, so this is not a correctness defect. **Fix:** retitle the test to say what it proves (a payload where some entries lack the key), or keep the committed fixture as an all-absent older payload and put the mix in an inline payload.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T08:16:10Z] Ada Typescript:
  - Fixed: fixture reverted to all-absent; the test asserts no entry carries a slug. No falsification (retitle/data only).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — New doc-comment lines exceed 100 columns

<!-- sq:finding:F5:body -->
The client's `printWidth` is 100, and Prettier does not rewrap comments. Three new or edited doc-comment lines run past that:

- `src/domain/previewDocument.ts:592` (138 columns, the `buildCommentHtml` JSDoc first line)
- `src/domain/squadDir.ts:130` (122)
- `src/types.ts:173` (103)

The surrounding comments in each file wrap at 100.

**Failure scenario.** None at runtime. The lines read badly in a 100-column editor, and the drift spreads to the next edit nearby.

**Fix.** Rewrap the three lines at 100 columns.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T08:16:11Z] Ada Typescript:
  - Fixed: the three doc-comment lines wrapped at 100 columns.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:12:57Z] Paul Reviewer:
  - Verdict: ChangesRequested on F1 (medium): the canary test claims sub-entity coverage, but no sub-entity exists in the scratch squad, so that loop never runs.
  - F2 to F5 are low: an undocumented divergence from the canary key policy, the squadDir comment wording, a misleading older-payload test title, and comment lines over 100 columns.
  - Guard, render, escaping, stylesheet and the guard export are sound. The exact key set going red on an added key is the intended policy. Gates: npm run check clean; npm test 705/705; canary 76/76 against .venv/bin/sq.
  - @typescript-dev please fix F1, ideally with F2 to F5 in the same pass.
- [2026-10-16T08:17:16Z] Catherine Manager:
  - Approved: F1–F5 Fixed. Re-ran npm run check (clean), npm test (705 passed) and the canary against the dev build (76 passed). The canary requires author_slug, which is correct because CI provisions sq from this repo. TASK-1005 stays InReview for op-pierre's visual check in the dev host.
<!-- sq:discussion:end -->
