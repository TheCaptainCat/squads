---
id: TASK-1275
sequence_id: 1275
type: task
title: Stored view bodies, escape grammar and the 0.20 schema
status: Done
parent: FEAT-1270
author: tech-lead
assignee: python-dev
refs:
- ADR-1274:implements
- MILE-1269:targets
description: Paired view tags with an escaped stored body, set_view_body, read-time
  body; schema 0.20 runner
subentities:
- local_id: ST1
  title: Paired view tags and their check findings
  status: Done
  maps_to: US1
- local_id: ST2
  title: Body writes keep stored bodies intact
  status: Done
  maps_to: US2
- local_id: ST3
  title: set_view_body and the escape grammar
  status: Done
  maps_to: US3
- local_id: ST4
  title: Projections read the stored body
  status: Done
  maps_to: US4
- local_id: ST5
  title: Schema 0.20 and its migration runner
  status: Done
  maps_to: US1
created_at: '2026-11-03T23:02:36Z'
updated_at: '2026-11-03T23:59:23Z'
priority: high
---
<!-- sq:body -->
## Goal

A view declared `stored = true` carries a stored body between a paired opening tag and end tag inside `sq:body`. The engine keeps that body intact through every body write, writes it through one service operation that escapes HTML-comment openers, and hands it unescaped to the view's transform and template on read (FEAT-1270 US1 to US4). This task also moves the schema to 0.20 with its `sq migrate up` runner: the paired tag is the first on-disk format change of the epic.

## ADR-1274 sections implemented

- §4 Stored view bodies, whole (amends ADR-880 §4 and ADR-776 §1): the `stored` declaration, the paired tag, the disabled form, the escape grammar, `set_view_body`, the placement rules for pairs, read-time expansion, check and repair.
- §12, the paired-tag findings only.
- §13 Schema 0.20 and its migration, whole, including the three pre-flight refusals (they inspect the existing corpus, so they need none of the later features).

## Scope

- `ViewSpec` gains `stored: bool = False`. Only a stored view has a pair; a non-stored view's tag is byte-for-byte what it is today.
- `_models/_markers.py` gains the close counterpart for view tags, used only for stored views. Rewrite the `VIEW` comment that says no close marker may be added: it now holds for every view whose content is derivable locally.
- The disabled stored view rewrites only the opening tag to `sq:view:<name>:disabled`; the end tag names the view and never its state; the body stays.
- The escape grammar: on write, every run of one or more `!` between `<` and `--` gains one `!`; on read, every such run of two or more loses one. Exact round trip for every input; only HTML-comment openers change on disk.
- `set_view_body(item, view, text)`: a `Service` method, not a CLI verb and not an `sq import` op. Inside `IndexStore.transaction()`; refuses a view not declared stored; escapes; writes through `_sections.py`; places an absent pair through the ADR-880 §6 routine. Its callers arrive with the pull task.
- `place_view_tags` treats a pair as one atom (strip removes the whole pair, re-insertion restores its bytes). An omitted pair is re-placed with its body; an identical pair is accepted (a `show --json` body round-trips); a pair with any other content is refused, naming the view and `sq <type> <n> show --refresh`. `reject_body_overwrite` strips pairs from both sides before comparing.
- `expand_view_tags` hands `body` (unescaped; empty string for an empty pair or a non-stored view) to the transform (ADR-1109) and the template. `show --json` returns `body` as stored and the unescaped stored body inside that view's entry under `views`.
- No read path writes a stored body: `show`, `--raw`, the TUI and the daemon's GET routes.
- `markers_balanced` accepts a balanced pair; new findings for an opening tag of a stored view with no end tag, an end tag with no opening tag, a pair outside `sq:body`, and a pair for a view not declared stored. The ADR-776 §8 repair sweep keeps every `sq:view:` tag, paired or not, off its list. The index and `sq repair` never read a stored body.
- `SCHEMA_VERSION` 0.20 and the `0.19 → 0.20` runner (ST5).

## Layers and expected files

- Models: `src/squads/_models/_markers.py`, `src/squads/_models/_schema.py`
- Workflow spec: `src/squads/_workflow/_models.py` (`ViewSpec.stored`), `src/squads/_workflow/_validity.py` (view checks), `src/squads/_specs/workflow.toml` (grammar comment only; no bundled view becomes stored here)
- Section engine: `src/squads/_sections.py`, `src/squads/_view_tags.py`, `src/squads/_views.py`
- Services: `src/squads/_services/_base.py` (`reject_body_overwrite`), `src/squads/_services/_items.py` (body write, `read_body`), `src/squads/_services/_views.py` (`view add`/`disable`, `set_view_body`), `src/squads/_services/_maintenance.py` (marker balance, repair sweep), `src/squads/_services/_check_rules.py` (rule table), `src/squads/_services/_item_read_dto.py` (`views` entry body)
- API: `src/squads/_api/_dto/_display.py` or `_items.py`, wherever a view entry is shaped
- Migrations: `src/squads/_migrations/_registry.py`, new `src/squads/_migrations/_v0_19_to_v0_20.py`, new `tests/fixtures/corpus/v0_19/`
- Tests: `tests/cli/test_item_verbs.py`, `tests/cli/test_show.py`, `tests/cli/test_migrate.py`, `tests/cli/test_repair.py`, `tests/check/test_corpus_integrity_rules.py` (or the module holding `markers_balanced`)

## Tests (about 13 new)

Per subtask below. A stored view exists only through an override in this task (the bundled `source_description` view comes with the pull task), so the cases run on a squad whose override declares `[views.<name>] stored = true` with its own template, and on item files carrying a pair written as fixture text. The escape-on-write case (forged `sq:body` end tag) needs a writer: `set_view_body` has no surface until the pull, so that case is the pull task's (ADR-1172: a behaviour goes to the task where it becomes visible). Existing view and show goldens must pass unchanged: that is the proof the bundled views did not move.

## Schema bump

This task carries the bump to 0.20. The migration stays open until 0.20 is published: later tasks that need a pre-flight case extend this runner rather than adding a bump.

## CHANGELOG

Report to the tech writer, in the handback comment: the `stored` view grammar, the paired tag and its disabled form, the refusal a body write now gives, the new `sq check` findings, `--json` view entries carrying `body`, the schema 0.20 bump and the migration's `manual` text.

## Depends on

Nothing in this epic. First in the chain.

## Size

L.

## Working rules

- Work in your own git worktree off `origin/release/0.20`.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects (grep the names you changed across `tests/`) plus the floor (`tests/meta`, `tests/cli`, `tests/check` for any change under `_specs/`, `_rendering/templates/` or `_cli/`), and `~/.local/bin/sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. Each new check rule gets its `@pytest.mark.breaches(...)` case. Falsify each new test once (break the code, see it red, restore) and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change; confirm the working version is 0.20.0 first and stop to ask if it is not.
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history (the migration runner excepted). No ticket IDs or process words in test or file names.
- No bundled type, kind, field, status or view literal in code outside `_specs/` and `_migrations/`.
- CHANGELOG and adopter docs are the tech writer's: report, do not edit `CHANGELOG.md` or `docs/`.
- Use `~/.local/bin/sq` for board operations; the dev tree only through `uv run --project <repo> sq -C <scratch>` on a scratch squad under the session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1275 add-subtask "<title>"`; track with `sq task 1275 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Paired view tags and their check findings

<!-- sq:subtask:ST1:body -->
`ViewSpec.stored` (default `false`) and the paired form of the view tag: `_models/_markers.py` gains the view close tag, recognised only for a view declared stored; `_view_tags.py` reads a pair, opening tag to end tag, as one view with a stored body. `view add` on a stored view places an empty pair; `view disable` rewrites only the opening tag to `:disabled` and keeps the end tag and the body. `markers_balanced` accepts a balanced pair; new findings: an opening tag of a stored view with no end tag, an end tag with no opening tag, a pair outside `sq:body`, a pair for a view not declared stored. The ADR-776 §8 repair sweep never lists a `sq:view:` tag; the index and `sq repair` never read a stored body.

Tests (5): `view add` then `view disable` on an override-declared stored view keeps the fixture body byte for byte (one case, both verbs); one `breaches` case per new finding (4). The repair-never-reads property is held by the existing repair golden plus a pair in the fixture corpus.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Body writes keep stored bodies intact

<!-- sq:subtask:ST2:body -->
The ADR-880 §6 routine in `place_view_tags` treats a pair as one atom: stripping removes the whole pair, re-insertion restores its bytes. A new body that omits a pair gets it re-placed at its view's position with its stored body; one carrying the identical pair is accepted, so a `show --json` body round-trips; one carrying a pair with other content is refused, naming the view and `sq <type> <n> show --refresh`. `reject_body_overwrite` (`_services/_base.py`) strips pairs from both sides before comparing prose.

Tests (3): `body -m` with text omitting the pair keeps it byte for byte; `body --file` fed the `show --json` body is accepted unchanged; `body -m` carrying an altered pair is refused with the view name and the remedy.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — set_view_body and the escape grammar

<!-- sq:subtask:ST3:body -->
The escape grammar (ADR-1274 §4): on write every run of one or more `!` between `<` and `--` gains one `!`; on read every such run of two or more loses one. Exact round trip; only HTML-comment openers change on disk. `set_view_body(item, view, text)` on `Service` (`_services/_views.py`): inside `IndexStore.transaction()`, refuses a view not declared stored, escapes the text, writes the pair through `_sections.py`, places it through the ADR-880 §6 routine when absent. Not a CLI verb, not an `sq import` op, no operation in `_api/_ops.py`.

Tests (0 here): the method has no surface until the pull seeds `source_description`. The forged `sq:body` end tag case, and the escape round trip, are the pull task's first cases; say so in the handback. The read side of the grammar is covered by ST4 on fixture text.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Projections read the stored body

<!-- sq:subtask:ST4:body -->
`expand_view_tags` at `read_body` hands the view's transform (ADR-1109) and its template the unescaped stored body as `body`; an empty pair or a non-stored view gets an empty string. `show --json` returns `body` as stored (pairs with their escaped text) and the unescaped stored body in that view's entry under `views`. No read path writes a stored body: `show`, `--raw`, the TUI and the daemon's GET routes.

Tests (3): `show` on an override stored view whose template prints `body` renders the fixture text with an escaped opener restored; `show --json` carries the escaped pair in `body` and the unescaped text under `views`; a daemon GET of that item leaves the file byte-identical (extend `tests/daemon/test_a_get_never_mutates.py` with a pair-bearing item rather than a new module). Bundled view goldens pass unchanged.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Schema 0.20 and its migration runner

<!-- sq:subtask:ST5:body -->
`SCHEMA_VERSION` becomes `"0.20"` and `_migrations/_registry.py` gains the `0.19 → 0.20` runner `_v0_19_to_v0_20.py`, which writes nothing to item files. Its pre-flight runs over the whole corpus before the stamp and refuses, listing every case: an item frontmatter carrying a top-level `source` key (now core); a role whose slug is `source` (now reserved); a discussion line directly after a comment header that matches the comment-attribute grammar of ADR-1274 §5. Remedies go in the runner's `manual` text. A squad clear of all three is stamped and carried unchanged.

New fixture corpus `tests/fixtures/corpus/v0_19/`. Bring this repository's squad up with the released tool only when the operator says so: the manager owns running `sq migrate up` on the live board.

Tests (2): `migrate up` on the clean 0.19 fixture stamps 0.20 and leaves every item file byte-identical; a corpus carrying all three cases is refused with all three listed (collect-all) and nothing stamped.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T23:30:35Z] `python-dev` Elias Python:
  - Handback from @python-dev. All five subtasks Done; the task stays InProgress. Nothing committed.
    
    **Step 0.** Version bumped to 0.20.0 with scripts/bump_version.py; the template manifest was regenerated and its 0.19.0 entry compares equal to the one in tag v0.19.0 (the regen only added 0.20.0). Empty `## [0.20.0]` heading added to CHANGELOG.md.
    
    **Files changed (src).** New: `_view_bodies.py` (escape/unescape, pair recognition, `ViewPair`), `_migrations/_v0_19_to_v0_20.py`. Edited: `_models/_markers.py` (`view_close_marker`, `view_close_name`, VIEW comment), `_models/_schema.py` (0.20), `_workflow/_models.py` (`ViewSpec.stored`), `_specs/workflow.toml` (grammar comment), `_view_tags.py` (pair-aware strip/place/expand, `altered_view_pairs`, `with_view_inner`, `body_region_span`), `_views.py` (`body` to the template, `view_data` entry), `_transform.py` (`body` keyword), `_services/_views.py` (`set_view_body`, `render_view` body), `_services/_items.py` (refusal for an altered pair), `_services/_check.py` (pair findings under markers_balanced), `_services/_maintenance.py` (repair sweep skips every view tag), `_migrations/_registry.py`.
    
    **Tests added (13).** Fixture corpus `tests/fixtures/corpus/v0_19/` (carries a `sq:view:head` pair, which also proves the repair sweep leaves a pair alone); helper `tests/_stored_view.py`.
    - migrate up: clean 0.19 squad stamps 0.20, item files byte-identical; a corpus with all three cases is refused with all three listed, nothing stamped (2).
    - check, `breaches("markers_balanced")`: opening tag of a stored view with no end tag; end tag with no opening; pair outside sq:body; pair for a view not declared stored (4).
    - `<type> view add`/`view disable` name: body kept byte for byte (1); `<type> body` --message: omitted pair re-placed (1); --file --force: the show --json body accepted (1); altered pair refused with view name and `show --refresh` (1).
    - show --raw: template reads the unescaped body (1); show --json: escaped pair in `body`, unescaped text under `views` (1).
    - tests/daemon/test_a_get_never_mutates.py extended with a pair-bearing item (no new module).
    Each was falsified once (code broken, test red, code restored).
    
    **Adjusted goldens.** schema "0.19"->"0.20" in test_reflog and test_workflow; the vocabulary digest in test_workflow changed because `ViewSpec` gained `stored`; test_migrate gets the 0.20.0 entry and `v0.14.0..v0.20.0`; `_bundled_documents.MIGRATIONS` gets the 0.20.0 entry; the import-edge table gets 5 rows.
    
    **Decisions to confirm.**
    1. ADR-1274 says the unescaped body goes "inside that view's entry under views", but `views.<name>` is the transform's output (a dict or a list). For a stored view the entry is now `{"body": <unescaped>, "data": <transform output or null>}`; a non-stored view's entry is unchanged. A stored view with no transform also gets an entry.
    2. `body` reaches a transform as an opt-in keyword like `item` and `spec` (a `**kwargs` transform gets it too); `sq workflow view` passes the stored body as well.
    3. `reject_body_overwrite` itself compares nothing; the callers strip tags through `strip_view_tags`, which now takes a pair whole, so no change was needed there.
    4. A tag of a stored view with no end tag is kept as written by a body write (reported by `sq check`), not silently completed; only a first placement writes an empty pair.
    5. `set_view_body` has no surface until the pull: it was exercised by hand (forged sq:body end tag, `<!!--` and `<!---` runs round-trip exactly, undeclared view refused, template reads the unescaped text). The forged-end-tag and escape round-trip cases belong to the pull task.
    
    **Gates.** pyright: 0 errors, 0 warnings, 0 informations. ruff check: All checks passed! ruff format --check: 546 files already formatted. pytest tests/meta tests/cli tests/check tests/daemon/test_a_get_never_mutates.py -n 4: 1854 passed. `sq check`: no issues. Full suite not run.
    
    **For the changelog (@tech-writer).**
    - `[views.<name>] stored = true`: for a view whose content comes from outside the squad; its tag is a pair `sq:view:<name>` ... `sq:view:<name>:end` inside sq:body. `view disable` rewrites only the opening tag to `:disabled`; the end tag and the body stay.
    - Escape grammar: every `!` run between `<` and `--` gains one `!` on write and loses one on read; only HTML-comment openers change on disk.
    - Body writes: a body that omits a pair gets it back unchanged; one carrying the identical pair is accepted (a show --json body round-trips); one carrying other pair text is refused: `the body carries a stored body for view '<name>' that differs from the one stored on <id>. A stored view body is written only by `sq <type> <n> show --refresh`: leave the pair out of the body, or send it back unchanged`.
    - sq check (markers_balanced): stored-view tag with no end tag; end tag with no opening tag; pair outside sq:body; pair for a view not declared stored. The repair sweep never lists a `sq:view:` tag.
    - show --json: `body` as stored; under `views`, a stored view's entry is `{"body", "data"}`. A transform or template reads the unescaped text as `body` (empty for an empty pair or a non-stored view).
    - Schema 0.20 (migration 0.20.0): `sq migrate up` writes nothing and refuses, listing every case, an item with a top-level `source` key, a role slug `source`, or a line directly under a comment header shaped like an attribute line (an HTML comment holding sq:attrs and a payload). Manual text: rename the key, give the role another slug, reword or remove the line. A vocabulary digest and `--json` schema_version change with the bump.
    
    **Open.** The migration stays open for the later tasks' pre-flight cases. Writer: CHANGELOG and docs/ untouched.
- [2026-11-03T23:59:23Z] `manager` Catherine Manager:
  - Accepted: REV-1280 approved with all findings verified; full suite 2005 passed, 2 skipped; gates and sq check clean. Moved to Done under the operator's delegation of the loop.
<!-- sq:discussion:end -->
