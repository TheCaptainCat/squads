---
id: REV-1027
sequence_id: 1027
type: review
title: 'TASK-1004 end-of-task: 0.16 header migration and checkpoint fixes'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1004:addresses
- FEAT-980:addresses
- MILE-934:targets
description: End-of-task review of the 0.16 migration step, the header rewrite and
  the REV-1026 fixes
subentities:
- local_id: F1
  title: A refusal below schema 0.15 names the stamped release and says nothing was
    written after earlier runners wrote
  status: Fixed
  severity: medium
- local_id: F2
  title: An operator without full_name had headers written as its slug; the migration
    matches by title and refuses
  status: Fixed
  severity: medium
- local_id: F3
  title: The importer now refuses as operator on comment events, unlike 0.15.0 and
    --as operator
  status: Fixed
  severity: medium
- local_id: F4
  title: Line-based scan diverges from _sections when a marker shares a line with
    content
  status: Fixed
  severity: low
- local_id: F5
  title: Template-owned-skill guard now skips on post-migration state, so dropping
    those skills passes
  status: Fixed
  severity: low
- local_id: F6
  title: Deferred import cycle and a third copy of the release-that-reads-schema sentence
  status: Fixed
  severity: low
- local_id: F7
  title: ADR-979 says the rewrite goes through _sections.py; the runner replaces lines
    in bytes
  status: Fixed
  severity: info
- local_id: F8
  title: Report and docstring wording that goes stale
  status: Fixed
  severity: info
- local_id: F9
  title: 'CRLF preservation holds on POSIX only: the atomic writer translates newlines
    on Windows'
  status: WontFix
  severity: info
- local_id: F10
  title: With 0.16 as the first runner, the refusal no longer names the release that
    can change the roster
  status: Fixed
  severity: low
- local_id: F11
  title: A lone marker with non-canonical spacing is refused as sharing its line with
    text
  status: Fixed
  severity: info
- local_id: F12
  title: Fixture README and legacy-squad docstring say this build
  status: Fixed
  severity: info
created_at: '2026-10-16T07:38:49Z'
updated_at: '2026-10-16T08:04:48Z'
---
<!-- sq:body -->
## Scope

End-of-task review of TASK-1004: the 0.15 to 0.16 migration step (ST4 to ST7) and the fixes for REV-1026 F1, F2, F4, F5 and F6, read against ADR-979 and the task body. F3 of REV-1026 waits for the ADR-979 amendment and is not raised again here.

What was reviewed is the uncommitted diff under `src` and `tests`, the new modules `_migrations/_v0_15_to_v0_16.py` and `_models/_participants.py`, the new test modules and the autouse fixture in `tests/conftest.py`. Probes ran on scratch squads under the session scratchpad: the dev build through its venv entry point with `-C`, the released 0.15.0 tool from inside the scratch folder. Each claim is marked driven, read or inferred.

## What holds

- **Plan, then refuse, then write (read and driven).** `run_contributions` awaits every plan before it looks at failures, raises one `SquadsError` listing all of them, and only then runs the writers in tuple order. The step's markdown writes all happen inside the one `IndexStore(..., spec=ctx.spec)` transaction, before it commits, and the runner changes no index entry. A refusal on a 0.15 squad leaves every item file and `.squads.toml` byte-identical (the dev's hash tests, plus a driven run here).
- **The header rewriter (read and driven).** It reads bytes, splits with `splitlines(keepends=True)`, replaces only legacy header lines inside discussion regions, keeps the name's bytes and each line's own terminator (CRLF included) and writes no frontmatter. Scan and writer split lines the same way, so the line indices agree. Names are resolved by dict lookup, so regex metacharacters in a name do nothing. A set of slugs per name gives the "two entries" failure, and one slug held by two items still resolves.
- **Shapes that behave (driven, direct calls of `_scan`).** Header-shaped lines in an item body are ignored, and so are indented and fenced lines inside a comment. A sub-entity discussion nested inside its block is scanned. View tags are excluded. Empty regions produce no events. An unclosed region is a failure, with every legacy header after it still counted.
- **Escaping (read).** Failure text leaves through `handle_errors`, which escapes it with `e()`, and report lines are printed through `e()` with `soft_wrap=True`.
- **The autouse cwd fixture (read).** It is correct: `monkeypatch.chdir` into a fresh `tmp_path_factory` directory, undone at teardown, and overridden by `project`'s own later chdir. I found nothing it masks. The tests that read repository files anchor on `__file__` (`_repo_root()`), the two tests that call `Path.cwd()` chdir explicitly and restore it, and no test globs a cwd-relative path that would now come back empty. It also closes a real hazard: tests that resolved this repository's live squad from the repo root. The nine affected tests are not named anywhere on the record.
- **Rewritten tests (read and driven).** The milestone stamp assertions now read `SCHEMA_VERSION`, chain lists gained the 0.16 step, the gate-permits test makes 0.16 inert as it made 0.15 inert, and the role-mirror premise is gated to corpora older than 0.15, where it still bites. The `kept = {model}` relaxation reaches only `v0_15_discussions`, because no older corpus has a role with `is_dev`. The template-owned-skill change is F5 below.
- **Hygiene (read).** No ticket ids in source or test names. Reserved slugs are spelled once in `_participants.py`, and the runner freezes its own copies by design. Docstrings are short, apart from the info notes in F8.

## Findings

- F1, medium: a refusal on a squad stamped below 0.15 sends the adopter to the stamped release and says nothing was written, but earlier runners already rewrote files.
- F2, medium: an operator with no `full_name` had its headers written as its slug, but the migration matches it by title, so it refuses, and the MANUAL remedy would misattribute.
- F3, medium: the importer now refuses `"as": "operator"` on comment events, a regression against 0.15.0 and against `--as operator`.
- F4, low: the line-based scan diverges from `_sections` when a marker shares a line with content.
- F5, low: the template-owned-skill guard now skips on post-migration state, so a migration that drops those skills passes.
- F6, low: a deferred import cycle and a third copy of the "release that reads schema" sentence.
- F7, info: ADR-979 says the rewrite goes through `_sections.py`; the implementation replaces lines in bytes.
- F8, info: report and docstring wording that goes stale.
- F9, info: the CRLF-preservation claim holds on POSIX only.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1027 add-finding "…" --severity medium`; track with `sq review 1027 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A refusal below schema 0.15 names the stamped release and says nothing was written after earlier runners wrote

<!-- sq:finding:F1:body -->
**What (driven).** A copy of `tests/fixtures/corpus/v0_11` with one unresolvable legacy header (`Nobody Known`) added to TASK-3's discussion, then `run_pending_migrations()` on the dev build. The run raises:

```
tasks/TASK-000003-implement-auth.md:57: 'Nobody Known' matches no roster entry
1 problem(s) found.
  'Nobody Known': 1 header(s) in 1 file(s)
Correct the roster with a squads release that reads schema v0.11 (v0.11.0 is one), or correct the line by hand, then run `sq migrate up` again; ... The earlier steps of this run have already been applied, so running again is safe.
Nothing was written and the schema is unchanged.
The squad is still at schema v0.11: ...
```

`diff -rq` against the fixture shows the earlier runners had already written: role and skill files changed, and new skill items such as `SKILL-000009-sq-contract.md` were created.

**Why it is wrong.** The stamp is only written at the end of `run_pending_migrations`, so `ctx.paths.config.schema_version` inside the runner is still the stamp from before the run (`0.11`), not `0.15`. That causes three problems:

- The remedy sends the adopter to `v0.11.0` to fix the roster, but the files are already in the 0.15 shape. An old tool writing over a newer-shaped corpus is how this project has corrupted indexes before (inferred). The step's own MANUAL says the opposite: "A squad stamped below 0.15 is first brought to 0.15 with the 0.15.0 release."
- "Nothing was written and the schema is unchanged" comes right after "the earlier steps of this run have already been applied". The first half of that line is false below 0.15.
- The `schema_tuple(schema) < (0, 15)` branch is the only one that adds the earlier-steps sentence, and its remedy is the wrong one.

**Fix.** Below 0.15, name the release that reads schema 0.15 (`release_reading_schema("0.15")`), which is what the MANUAL and the tech lead's question 2 prescribe. Keep the line "Nothing was written" only when this step is the first runner of the run. Pin the full message of `test_a_refusal_below_0_15_says_the_earlier_steps_were_applied`: it asserts the earlier-steps fragment today, but not the release it names.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T07:49:19Z] `python-dev` Elias Python:
  - Fixed: the step no longer claims the whole run wrote nothing or names a release; run_pending_migrations adds, for a step that is not the run's first, 'Earlier steps of this run have already been applied ... change the roster with a squads release that reads schema v0.15 (v0.15.0 is one)'. The step says 'This step wrote nothing and the schema stamp is unchanged.' Test pins both. Falsified (note dropped): 1 red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — An operator without full_name had headers written as its slug; the migration matches by title and refuses

<!-- sq:finding:F2:body -->
**What (driven).** In a scratch squad, the released 0.15.0 tool imports `{"op":"create","type":"operator","title":"Ann Person","slug":"op-ann","as":"manager"}`. The operator file it writes has no `extra` block, so there is no `full_name`. Then `sq task 21 comment --as op-ann -m hello` writes this header:

```
- [2026-10-16T07:36:53Z] op-ann:
```

The released `_author_of` returns `participant.extra.get(FULL_NAME, slug)`, so the writer falls back to the slug. On a copy of that squad, the dev build's `sq migrate up` exits 1 with `tasks/TASK-000021-target.md:27: 'op-ann' matches no roster entry`.

**Why.** `_read_roster` names an operator `extra.full_name`, falling back to its title (`Ann Person`). The released writer fell back to the slug. So a registered, live operator that the released importer created refuses the whole migration. The MANUAL remedy, "add it back under that name", would create a second operator whose display name is `op-ann`, and the headers would then resolve to that new entry's slug: a misattribution, not a fix. The only working remedy is a frontmatter hand edit that sets `full_name: op-ann`.

The test `test_an_operator_without_a_full_name_resolves_by_its_title` injects `- [ts] Zoë Müller:` for such an operator. The released writer can never produce that header, so the test pins an unreachable shape and misses the one that happens.

The "a legacy name that is only a slug matches no entry" rule was argued for unregistered importer actors (tech lead's question 4). This is a registered entry whose name the writer itself set to the slug.

**Fix.** Resolve each name the way the released writer named the author: an operator by `extra.full_name`, else its slug. Keep the title as an extra key if wanted. This needs a one-line amendment to ADR-979 decision 4, which says "falling back to its title". Replace the test row with the released writer's actual header.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T07:49:21Z] `python-dev` Elias Python:
  - Fixed: an operator is known by extra.full_name, else its slug, as the released writer wrote it. Test now imports an operator without full_name and migrates the header '- [ts] op-ann:'. MANUAL says so. Falsified (title fallback back): 1 red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The importer now refuses as operator on comment events, unlike 0.15.0 and --as operator

<!-- sq:finding:F3:body -->
**What (driven).** On a scratch squad, the dev build's `sq task 21 comment --as operator -m "interactive anon"` exits 0. An import of `{"op":"comment","target":"TASK-21","message":"import anon","as":"operator"}` exits 1:

```
line 1: cannot comment as 'operator': that slug is reserved
1 issue(s) found — nothing written.
```

The released 0.15.0 importer wrote any actor verbatim (the dev's own ST1 note), so this file imported before. The same import file still accepts `"as": "operator"` on `create` and `update` events. Only comment events refuse it.

**Why it matters.** `operator` is the anonymous author, which ADR-979 decision 2 keeps as a reserved participant slug with the name `Operator`. `resolve_slug_or_raise` still lets it through for `--as`. REV-1026 F5 suggested "the live roster plus `operator`, with `squads` refused as an actor". The fix refuses both, so a bulk history import that attributes comments to the anonymous author breaks. The message is also inaccurate: `operator` is reserved against roles, not against comments.

**Fix.** Refuse only `squads` as an importer comment actor, as F5 suggested, and add an `operator` comment row to the importer table. Alternatively, record a ruling that the anonymous author is no longer accepted by the importer, and list it as an adopter-visible change for the tech writer. Falsify the fix by restoring the `operator` refusal.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T07:49:23Z] `python-dev` Elias Python:
  - Fixed: the importer refuses only squads as a comment actor; operator imports again (table row). Falsified (operator refused again): 1 red.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Line-based scan diverges from _sections when a marker shares a line with content

<!-- sq:finding:F4:body -->
**What (driven, direct calls of `_scan`, compared with `_sections.get_section`).** `_scan` opens a region on a line and then `continue`s, and it looks for a close marker only on later lines. `_sections` finds regions by offset. The two disagree when a marker shares a line with content:

- the discussion open marker and its close marker on one line (sq:discussion then sq:discussion:end): `get_section` returns an empty region, while `_scan` reports `discussion region `discussion` is not closed`. It also treats every later line of the file as inside the region, so a header-shaped line quoted further down the body is counted as a legacy header.
- a header on the open marker's line (sq:discussion immediately followed by `- [ts] X:`): `_scan` returns no event, but the live reader sees the header as the first line of the region. The run completes and stamps 0.16 with that legacy header still in place, unreadable afterwards. That is the outcome the task calls out for an unclosed region.
- A legacy comment carrying a ` ` (the F1 hole existed in the old writer too): failure line numbers count `splitlines` lines, so they are off from what an editor shows, and the "indent it" remedy does not match what the adopter sees.

**Severity.** Low. No sq writer produces the first two shapes; they come only from hand edits. ST7 found none in this repository's squad.

**Fix.** After opening a region, check the rest of the opener line for its close marker and for a header. Or derive region spans from `_sections` offsets and map them to line numbers. Add both shapes to the shape table.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T07:49:26Z] `python-dev` Elias Python:
  - Fixed: the scan refuses a discussion marker that shares its line with text (open and close on one line, header after the open marker, text before the close marker) with 'the marker of discussion region ... shares its line with text'; MANUAL lists it. Three shape rows. Falsified: 3 red. Not changed: failure line numbers still count splitlines lines.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Template-owned-skill guard now skips on post-migration state, so dropping those skills passes

<!-- sq:finding:F5:body -->
**What (read and driven).** `test_every_template_owned_skills_stored_body_converges_onto_its_tag` changed `assert template_owned, ...` into `pytest.skip(...)`. `template_owned` is computed from the index after `run_pending_migrations()`. So if a migration regressed and dropped every template-owned skill item from a corpus, this test would now skip for that corpus instead of failing. A run with `-rs` shows that the new skip fires today only for `v0_15_discussions`.

**Severity.** Low, because the migrated-corpus goldens would still catch deleted skill files (inferred). But it is the "assertion went vacuous" pattern the test-audit notice lists.

**Fix.** Decide the skip from the corpus before the migration (no template-owned skill in the copy before the run), or skip by corpus name for `v0_15_discussions`, and keep the assertion for every other row.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T07:49:28Z] `python-dev` Elias Python:
  - Fixed: the template-owned-skill test decides its skip from the corpus before the migration and asserts after. Falsified (migration deletes the skill files): the test fails among 7 red.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Deferred import cycle and a third copy of the release-that-reads-schema sentence

<!-- sq:finding:F6:body -->
**What (read).** `_failure_notes` imports `release_reading_schema` from `_migrations._registry` inside the function, because the registry imports this module at load time. That adds a runtime import cycle (runner to registry to runner), while CLAUDE.md asks for an acyclic graph and a `TYPE_CHECKING` import where an edge would close a cycle. The function also builds the third copy of the sentence `a squads release that reads schema v{schema} (v{release} is one)`; the other two are in `_services/_maintenance.py`, at `_index_full_refusal` and `_pre_runner_refusal`.

**Fix.** Let the step raise its failure lines, and let `run_pending_migrations` append the remedy sentence, as it already appends "The squad is still at schema …". That removes the cycle and the copy, and puts the release choice of F1 in one place. Alternatively, pass the reader string on `MigrationContext`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T07:49:30Z] `python-dev` Elias Python:
  - Fixed: the runner has no registry import; the remedy sentence is gone from the step. The reader phrase 'a squads release that reads schema vX (vY is one)' now exists once (_reader_phrase in _maintenance.py), used by the pre-runner refusal, the index-full refusal and the earlier-steps note. Structural, no falsification.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — ADR-979 says the rewrite goes through _sections.py; the runner replaces lines in bytes

<!-- sq:finding:F7:body -->
**What (read).** ADR-979 decision 4 says the migration "rewrites only the header line, through `_sections.py`", and the ST5 brief says "the edit goes through `_sections`". `_write_headers` instead reads bytes and replaces whole lines, using `_sections.find_markers` only to find regions. The byte-level approach is arguably the safer one for keeping terminators and every other byte, and the tests prove that. But it is an unrecorded deviation from an Accepted decision, and invariant 3 in CLAUDE.md says the same thing as the ADR.

**Fix.** Record it: add a dated comment on ADR-979, or a clause in the pending amendment, saying the rewrite is a line replacement inside regions found by `_sections` markers. No code change needed.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T07:43:52Z] `architect` Robert Architect:
  - Recorded on ADR-979 as a 2026-10-16 note under decision 4: the rewrite replaces whole header lines in the raw bytes, keeping each line terminator, with _sections markers used only to find regions (byte preservation, header-line-only edits). No code change.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Report and docstring wording that goes stale

<!-- sq:finding:F8:body -->
**What (read).**

- The report line of a completed run reads `3885 comment header(s) to rewrite in 881 file(s)` (ST7) after the rewrite has happened. The brief asked for "headers rewritten". Use the past tense in a completed run.
- The module docstring of `_v0_15_to_v0_16.py` says "The one contribution today rewrites each comment header". It goes stale as soon as TASK-990 appends a contribution. Describe the contribution without "one" and "today".
- The registry docstring points at `_v0_15_to_v0_16` as the example of a contribution list, which goes stale at the next release's step.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T07:49:32Z] `python-dev` Elias Python:
  - Fixed: completed-run report reads 'N comment header(s) rewritten in M file(s)'; module and registry docstrings no longer say 'the one contribution today' or point at this step as the example. Falsified (old wording): 2 red.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — CRLF preservation holds on POSIX only: the atomic writer translates newlines on Windows

<!-- sq:finding:F9:body -->
**What (read).** `_aio.atomic_replace_sync` opens its temp file with `open("w", encoding="utf-8")` and the default `newline=None`, which turns `\n` into `os.linesep` on write. On native Windows, a CRLF line the runner keeps byte-for-byte would be written as `\r\r\n`, and every LF file would become CRLF. So "line terminators preserved" and "the whole-file diff is header lines only" hold on POSIX only, and the CRLF test proves them only there. This is not new to this task: every sq write goes through that primitive. The migration makes it worse by rewriting every file that carries a comment (881 in this repository).

**Fix.** Out of this task's scope: `newline=""` in the atomic writer is the general fix, and it deserves its own item. Noted here so the CRLF claim in the MANUAL and the tests is not read as cross-platform.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T07:42:28Z] `qa` Mara Tester:
  - WontFix here: home is BUG-1028.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — With 0.16 as the first runner, the refusal no longer names the release that can change the roster

<!-- sq:finding:F10:body -->
**What (driven).** A 0.15 squad written by the released tool, with one unresolvable header added, run through the dev build's `sq migrate up`. Exit 1, and the remedy line now reads:

```
Correct the roster, or correct the line by hand, then run `sq migrate up` again; `sq migrate chlog v0.15.0..v0.16.0` has the steps.
This step wrote nothing and the schema stamp is unchanged.
The squad is still at schema v0.15: ...
```

The F1/F6 fix moved the release name into `_earlier_steps_note`, which only fires when the step is not the run's first. When the 0.16 step is the first runner (the common case: a squad at 0.15), the message no longer says which release can change the roster. The ST5 brief asked for it ("the message names that release, as the refusals of TASK-954 do"). An adopter who follows "Correct the roster" with the build they just ran gets refused by the schema gate.

**Severity.** Low. The chlog pointer leads to the MANUAL, which says it, and nothing is written.

**Fix.** Append the reader phrase for the stamped schema in the first-runner case too, for example `change the roster with a squads release that reads schema v0.15 (v0.15.0 is one)`, from the same `_reader_phrase`. Pin it beside the earlier-steps test.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T08:01:17Z] `python-dev` Elias Python:
  - Fixed: a step that is the run's first refusal now adds 'Change the roster with a squads release that reads schema v0.15 (v0.15.0 is one).' through _reader_phrase; pinned in the first-step test. Falsified: 1 red.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — A lone marker with non-canonical spacing is refused as sharing its line with text

<!-- sq:finding:F11:body -->
**What (driven, direct call of `_scan`).** `MARKER_RE` accepts any whitespace inside a marker (optional whitespace on both sides of the tag). The new shared-line check compares the stripped line against the canonical form only. So a region marker alone on its line but spaced differently (the sq:discussion tag with no space after the opening dashes, or two spaces around sq:discussion:end) is refused with "the marker of discussion region `discussion` shares its line with text", although there is no text on the line.

Refusing is right: the live `get_section` does a literal find on the canonical form and returns `None` for that region, so sq could not read it either. Only the wording misleads: an adopter looking at a line that holds only a marker is told to move text that does not exist.

**Fix (optional).** When the stripped line is a lone marker that is not in the canonical form, say "is not written in the form sq writes (one space on each side of the tag)". Or widen the MANUAL bullet to "a discussion marker not on a line of its own, in the form sq writes".
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T08:01:19Z] `python-dev` Elias Python:
  - Fixed: a lone marker not spelled as sq writes it reads 'is not a well-formed sq marker (one space on each side of the tag)'; shared-line stays for text beside a marker. Two shape rows. Falsified: 2 red.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Fixture README and legacy-squad docstring say this build

<!-- sq:finding:F12:body -->
**What (read).** In the delivered prose of the diff, two phrases only make sense to someone who knows which tree was checked out when they were written:

- `tests/fixtures/corpus/README.md`, the `v0_16/` row: "the real `sq migrate up` of this build against a scratch copy of the frozen `v0_15` fixture". After the next release, "this build" names nothing. The neighbouring rows say "the real 0.14→0.15 migration". Write "the real 0.15→0.16 `sq migrate up`".
- `tests/_legacy_squad.py` module docstring: "the roster this build can create". Write "the roster the current code can create", or just "a roster".

The rest of the sweep came back clean. I read the added docstrings, comments, `MANUAL`/`SUMMARY`, the preamble, the refusal strings, test module docstrings and test names in the diff, and found no phase, round or pass language, no reviewer or finding references, no ticket ids, and no versions in docstrings outside the migration runner.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T08:01:21Z] `python-dev` Elias Python:
  - Fixed: 'this build' removed from the v0_16 README row (now 'the real 0.15→0.16 sq migrate up') and the _legacy_squad docstring. Prose only.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T07:40:43Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. Three medium findings, each driven on a scratch squad: F1, a refusal below schema 0.15 names the stamped release (v0.11.0 on the v0_11 corpus) and says nothing was written after earlier runners wrote; F2, an operator the released importer created without full_name had its headers written as its slug, so the migration refuses and the MANUAL remedy would misattribute; F3, the importer refuses as operator on comment events, a regression against 0.15.0 and --as operator.
  - Low and info: F4 (scan vs _sections when a marker shares a line), F5 (template-owned-skill guard skips on post-migration state), F6 (deferred import cycle, third reader-sentence copy), F7 (ADR-979 says through _sections.py), F8 (stale wording), F9 (CRLF claim POSIX-only).
  - What holds: plan-all-then-refuse, header-lines-only rewrite with name bytes and terminators kept, no frontmatter writes, markdown before the index commit, and the autouse cwd fixture (correct, nothing masked found). REV-1026 F3 not re-raised. Targeted run of the four migration test modules: 70 passed. @python-dev F1 to F3 (and F4 to F6 if taken); F2 and F7 need an ADR-979 line, so @architect.
- [2026-10-16T07:42:18Z] `qa` Mara Tester:
  - F9 closed WontFix here: tracked as BUG-1028, which is its home.
- [2026-10-16T07:57:25Z] `reviewer` Paul Reviewer:
  - Re-verified against the original repros: F1 (probe_below on v0_11 now names the release that reads 0.15 and limits the nothing-written line to this step), F2 (a released-tool operator without full_name migrates as op-ann), F3 (importer accepts as operator, refuses squads), F4 (both shared-line shapes now refuse with a line-numbered message the MANUAL covers), and F5/F6/F8 read. All hold. Targeted re-run of six modules: 123 passed.
  - Three new findings, none medium: F10 low (with 0.16 as the first runner the refusal no longer names the release that can change the roster), F11 info (a lone marker with non-canonical spacing is refused as sharing its line with text), F12 info (this build in the fixture README and the legacy-squad docstring). The narration sweep found nothing else.
  - Recommend Approved: no medium-or-worse finding is open. I left the Approved transition to @manager: a reviewer approving its own review skips the two-party gate. @python-dev F10 to F12 are small and can land with the commit.
- [2026-10-16T08:04:46Z] `manager` Catherine Manager:
  - Approved on the reviewer's recommendation after its re-verification pass. All findings Fixed, F9 WontFix with home BUG-1028. Full suite 10,410 passed, 0 failed; pyright and ruff clean; migration dry run on a copy of the live squad rewrote 3,908 headers in 882 files with header-only changes.
<!-- sq:discussion:end -->
