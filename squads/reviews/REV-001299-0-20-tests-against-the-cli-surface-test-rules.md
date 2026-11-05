---
id: REV-1299
sequence_id: 1299
type: review
title: 0.20 tests against the CLI surface test rules
status: ChangesRequested
author: reviewer
refs:
- ADR-1172
description: '0.20 tests vs ADR-1172: 12 findings (1 high, 7 medium, 4 low)'
subentities:
- local_id: F1
  title: Source CLI tests hard-code bundled vocabulary and fail on the override squad
    (142 failed, 118 errors)
  status: Open
  severity: high
- local_id: F2
  title: Messages and refusals asserted by substring, prefix or one picked line instead
    of whole lines
  status: Open
  severity: medium
- local_id: F3
  title: test_source_record reads .squads.json to assert the rebuilt index's keys
  status: Open
  severity: medium
- local_id: F4
  title: Item files hand-written to arrange states that source pull produces
  status: Open
  severity: medium
- local_id: F5
  title: Credential store read directly and its path computed through CredentialStore
    from src
  status: Open
  severity: low
- local_id: F6
  title: covers markers declare a parameter the case is not about, on refusals and
    effect cases
  status: Open
  severity: medium
- local_id: F7
  title: Shape tables of sources.toml grammar refusals and author-name escapes in
    tests/cli
  status: Open
  severity: medium
- local_id: F8
  title: Source tests split into 11 feature modules that hold cases of other command
    groups
  status: Open
  severity: medium
- local_id: F9
  title: Several refusals batched in one case under multi-parameter markers and a
    vague name
  status: Open
  severity: low
- local_id: F10
  title: JSON field projections asserted instead of the whole --json object
  status: Open
  severity: low
- local_id: F11
  title: 'Check-rule tests: an unmarked case, two breaches in one case, partial issue
    assertions'
  status: Open
  severity: medium
- local_id: F12
  title: declare_stored_view overwrites the override, so nine stored-view cases opt
    out as bundled_only
  status: Open
  severity: low
created_at: '2026-11-04T22:05:56Z'
updated_at: '2026-11-04T22:19:17Z'
---
<!-- sq:body -->
Audit of the tests added or changed between v0.19.0 and 973058e5 (`git diff --name-status v0.19.0 973058e5 -- tests/`, 129 files), against ADR-1172 and the check-rule rules in CONTRIBUTING. The code was read from a detached worktree at 973058e5.

Scope covered: the eleven `tests/cli/test_source*.py` modules, `tests/check/test_source_rules.py`, `tests/daemon/test_the_credential_verbs.py`, the helpers `tests/_tracker_harness.py` and `tests/_stored_view.py`, the fixtures, and the changed `tests/cli`, `tests/check`, `tests/daemon`, `tests/cross_process` and `tests/regressions` files. `tests/meta` was read only for guard weakening.

Runs at 973058e5:
- source modules on the bundled squad: 152 passed in local, remote and routes mode;
- `tests/cli` on the override squad: 142 failed and 118 errors, all in the source modules;
- the coverage and breach guards: green on both squads.

Checked and found sound:
- No subprocess was added outside `tests/cross_process`. The tracker harness is an in-process loopback thread.
- No ticket or process words appear in test names.
- The fixtures use placeholder hosts.
- The `tests/meta` changes are import refactors plus new guards. No existing guard was loosened.
- `parametrize` in `test_source_converters.py` (three converters) and `test_source_links.py` (pull order) is legitimate.
- `test_source_links.py` imports `app` for `runner.invoke` inside a tracker callback, to interleave an unlink mid-fetch. That is a CLI arrangement no other path can produce, and it stays through the `runner` fixture.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1299 add-finding "…" --severity medium`; track with `sq review 1299 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Source CLI tests hard-code bundled vocabulary and fail on the override squad (142 failed, 118 errors)

<!-- sq:finding:F1:body -->
**Rule:** ADR-1172 Scope ("a case reaches its host through the squad's profile, never through a literal name"); CI runs `tests/cli` on the override squad (`.github/workflows/test.yml:109`, and in remote mode at `:252`).

**Measured** at 973058e5: `uv run --all-extras pytest -n 4 --squad override tests/cli` gives 142 failed, 118 errors, 853 passed, 170 skipped. Every failure and error is in the eleven `tests/cli/test_source*.py` modules. Every other `tests/cli` module passes on the override squad. On the bundled squad the same modules pass (152 passed), in local, remote and routes mode.

**Cause:** the cases spell bundled vocabulary and carry no `bundled_only`:
- the type map in every `sources.toml` the cases write (`issue = "task"`, `bug = "task"`, `Story = "task"`), and `maps.fields.priority`. The override squad refuses it at load with "'issue' -> 'task' is not an item type" (82 hits) and "maps.fields.priority: no item type has this field" (55 hits);
- addresses and ids: `["task", "2", "show", ...]`, `create task`, `TASK-2`, `retype bug` (`test_source_ownership.py:124`), `[items.task.attributes]` (`test_source_identities.py:112`).

The 118 errors are the teardown check ("covers declares pairs no call reached"), which fires because the arrange step already failed.

**Fix:** build each `sources.toml` map target, field map and address from the `profile` fixture (`P.ref`, `P.ref_prefix`, a badge field and its values), the way `test_item_verbs.py` does. Give `bundled_only` with a reason only to a case that is genuinely about bundled spelling. Then run the override job.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Messages and refusals asserted by substring, prefix or one picked line instead of whole lines

<!-- sq:finding:F2:body -->
**Rule:** ADR-1172 rule 5 ("the whole message line or the JSON object, not a substring that would survive a wrong message"; "a refusal is asserted by its whole message lines, never by a substring"). CONTRIBUTING repeats the rule.

**Sites** (`in`, `startswith`/`endswith`, or a single line picked out of a longer output):
- `tests/cli/test_source.py:114, 126, 141, 228`
- `tests/cli/test_source_check.py:211-215, 227, 274, 312, 353, 370, 504`
- `tests/cli/test_source_comments.py:152, 203`
- `tests/cli/test_source_identities.py:65, 77, 95, 97, 105, 121`
- `tests/cli/test_source_links.py:80-81, 97-99, 117, 211, 319-320, 348, 350, 651`
- `tests/cli/test_source_pull.py:263, 265, 291, 306, 330, 411, 522, 541, 626, 731`
- `tests/cli/test_source_record.py:44` (only the first line of `sq check`)
- `tests/cli/test_source_scope.py:242-243`
- `tests/cli/test_migrate.py:358-359` (the refusal about the `source` alias)

Several of these are refusals (`test_source.py:114/126/228`, `test_source_identities.py:65-105`, `test_source_comments.py:203`, `test_source_pull.py:263/306/522/541`, `test_migrate.py:358`), which is the case the rule names explicitly.

**Not a defect:** a negative containment check that the secret never leaks (`SECRET not in ...`, `test_the_credential_verbs.py:48`) is a property of the whole output, not a substring stand-in for a message. Keep those.

**Fix:** compare `(exit_code, output)` with the whole expected text. Normalise the tracker's port the way `_checked` does at `test_source_check.py:45-48`, and drop the `" ".join(output.split())` rewrapping so that line breaks are asserted too.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — test_source_record reads .squads.json to assert the rebuilt index's keys

<!-- sq:finding:F3:body -->
**Rule:** ADR-1172 rule 5: "A test never opens `.squads.json`".

**Site:** `tests/cli/test_source_record.py:59-73`, in `test_repair_rebuilds_the_index_of_sourced_items_to_the_one_it_replaces`. The test unlinks the index, which is a legitimate arrange step. It then reads the rebuilt `.squads.json` and asserts its top-level key set (`schema_version`, `counter`, `padding`, `items`).

**Fix:** drop the key-set assertion. The comparison `after == before` of both items' `show --json` already proves the rebuild through the CLI. If the claim is that the index holds no source data, that claim belongs to a `tests/meta` guard over the index model, not to a CLI case.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Item files hand-written to arrange states that source pull produces

<!-- sq:finding:F4:body -->
**Rule:** ADR-1172 rule 5: "A test writes an item file ... directly only to arrange a state that no CLI path can produce".

**Sites** where a CLI path exists (`source pull` through `tests/_tracker_harness.py`):
- `tests/cli/test_source_record.py:52-73` (`_mirror` with a *valid* record): a pull writes exactly this record.
- `tests/cli/test_source_record.py:93-107`: the test rewrites a comment header to `source:platform`, yet `test_source_pull.py:610` shows that a pull writes comments with the author slug `source:platform`.
- `tests/cli/test_source_comments.py:184-186`: the test renames `author_name` in an attribute line by hand. A tracker note whose author name changes, with `updated_at` bumped and pulled again, should produce the same state (`test_source_pull.py:168` shows that edits are pulled in place). If the pull deliberately does not refresh author attributes, say so in the test docstring. The hand edit is then the only path.

**Legitimate, keep:** malformed or duplicate records that no command writes (`test_source_record.py:36`, `test_source_pull.py:279-283` twin holder, `tests/check/test_source_rules.py` `_mirror`, the stored-view pairs).

**Fix:** arrange these three states with the harness and `source pull`, and read the result through `comments --json` / `show --json`.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Credential store read directly and its path computed through CredentialStore from src

<!-- sq:finding:F5:body -->
**Rule:** ADR-1172 rule 5 lists every file a test may read: the generated agent files, scaffolded override files, the add/track hint, and the item files `migrate up` rewrote. "No other file is read." The CLI tests also take the store's location from `src`.

**Sites:**
- `tests/cli/test_source.py:13` imports `CredentialStore`. It is used to compute the expected `path` at `:46` and to read or chmod the store at `:161-169, 178, 213, 223, 228-229`.
- `tests/daemon/test_the_credential_verbs.py:10, 49, 76`, the same pattern for the route tests (rules 4-6 apply).

The modes `0600`/`0700` and the absence of the secret after `remove` are the security contract of `credential set|remove`, and no CLI output shows them. The reads are therefore defensible, but the ADR does not admit them. The expected `path` is circular: the test computes it with the same function the command uses, so a wrong store location passes.

**Fix:** (a) @architect: amend rule 5 to name the per-user credential store as an output file of the `source credential` verbs (the parallel of the override files). (b) Take the store path from the command's own `--json` output (`credential set --json` prints `path`), or from the `credentials_home` fixture's documented layout, never from `CredentialStore()`.

`SquadPaths` at `test_source.py:12` is only a type annotation of the `project` fixture. It is not a breach.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — covers markers declare a parameter the case is not about, on refusals and effect cases

<!-- sq:finding:F6:body -->
**Rule:** ADR-1172 rule 3: "A refusal declares the parameter it is about", not a parameter the call happens to pass. The same rule holds for an effect case: each parameter whose effect is asserted is declared.

**Sites:**
- `sources.toml` load refusals declared on an unrelated pair. The refusal is about the document, not the argument or the flag:
  - `tests/cli/test_source.py:89, 105, 117, 129`: `covers("source credential remove", "source")`;
  - `tests/cli/test_source_connectors.py:385` (same pair) and `:403`, `covers("source list", "--json")`;
  - `tests/cli/test_source_scope.py`: all 16 cases from `:39` to `:307` declare `covers("source list", "--json")`.
- `tests/cli/test_source_ownership.py:50` declares `<type> update --title`, but also asserts a refusal of the derived field option (`--priority`, which is `--<field>`) and a success of `--desc`.
- `tests/cli/test_source_identities.py:108` declares `<type> update --set`, but also asserts the effect of the derived map option `--links`.

**Fix:** declare the pair each assertion is about: `--<field>` for the priority refusal, and the derived option's name for `--links`. The document-load refusals are not CLI parameters at all. Their home is the open question in the layout finding: @architect, rule on whether they are CLI cases (with which key) or a separate set like `tests/check/`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Shape tables of sources.toml grammar refusals and author-name escapes in tests/cli

<!-- sq:finding:F7:body -->
**Rule:** ADR-1172 rule 1, plus the rejected "per-type parametrised table" option and the Context on the shape axis ("cross products of parametrised tables (position x shape x layer)"). Each boundary refusal is one case. A table of input shapes that yield the same message is the volume the ADR removes.

**Sites:**
- `tests/cli/test_source_scope.py`: inline tables run through `_refusals`/`_listed`:
  - `:141-152`: four rows of "a character outside the grammar" (one message, with the character and position varied; the `\n` and `\r\n` rows give the same line and column);
  - `:156-176`: five rows;
  - `:181-201`: five rows;
  - `:204-212`: three rows (two of them the same "'(' is not closed" at different columns);
  - `:217-233`;
  - `:246-279`: six scope-shape rows, four of them the same `gitlab_shape` message;
  - `:307-321`.
- `tests/cli/test_source_comments.py:121-138`: `parametrize` over four escaping shapes of one unmatched author name (quote, backslash, control characters, empty).

**Judged acceptable, not part of this finding:**
- `test_source_converters.py:126`: three converters, each a distinct implementation with its own effect;
- `test_source_links.py:502-507`: host-first or target-first pull order, a genuine order interaction under rule 1.

**Fix:** keep one row per distinct refusal message (the CLI contract). Drop the rows that repeat a message at another position or with another character. For the author name, keep one case whose name carries both a quote and a control character, plus the empty-name case if its output differs. If the grammar's shape coverage is wanted, @architect should decide its home. It is not the CLI surface suite.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Source tests split into 11 feature modules that hold cases of other command groups

<!-- sq:finding:F8:body -->
**Rule:** ADR-1172 rule 6: "one module per command group, named for that group's behaviour". `test_item_verbs.py` holds `<type> …`, `test_comment_verbs.py` holds `<host> comment …`, and so on.

**Finding:** `source` has eleven modules (`test_source.py`, `_check`, `_comments`, `_connectors`, `_converters`, `_identities`, `_links`, `_ownership`, `_pull`, `_record`, `_scope`). They are organised by feature, not by command group, and they hold cases of other groups. These are the sites (covers key and line):
- `test_source.py:54, 72`: `override scaffold`.
- `test_source_check.py:278, 320`: `source pull`; `:298`: `<type> show --refresh`; `:357`: `operator update`.
- `test_source_comments.py:65, 108, 121, 142`: `<host> comments`; `:159`: `inbox`; `:177, 195`: `<host> comment`.
- `test_source_connectors.py:126, 252`: `<type> show`; `:517`: `operator update`.
- `test_source_identities.py:36-102`: `operator update`; `:108`: `<type> update`.
- `test_source_links.py:58, 84, 102, 122, 328, 367, 385, 625, 672`: `<type> show`; `:188-691`: `<type> source unlink|relink`, which are item verbs; `:639`: `workflow view`.
- `test_source_ownership.py:50, 69, 83, 102-103, 123`: `<type> update`, `<type> body`, `<host> comment`, `import`, `<type> retype`.
- `test_source_pull.py:513`: `import`; `:633`: `<type> show`.
- `test_source_record.py:35, 51, 76, 92`: `check`, `repair`, `role add`, `<host> comments`.
- `test_source_scope.py:236`: `check --json`. This one also duplicates the `sources_loads` breach test (`tests/check/test_source_rules.py:158`) and asserts by substring. Drop it.

**Fix:** move each case into the module of the group its key names. Then either merge the `source …` cases into one `test_source.py`, or have @architect amend rule 6 to allow one module per leaf of a large group (`test_source_pull.py`, `test_source_check.py`, `test_source_credential.py`, …). That amendment is worth making: one `source` module would run past 3,000 lines.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Several refusals batched in one case under multi-parameter markers and a vague name

<!-- sq:finding:F9:body -->
**Rule:** ADR-1172 rule 1 ("A combination test names the interaction in its function name"), rule 3 ("One marker, several parameters, is only for an interaction"), and rule 6 ("Test function names state the behaviour").

**Sites:**
- `tests/cli/test_source_links.py:244`, `test_relink_refuses_an_item_that_still_holds_a_record_or_no_source_made_and_more`: five distinct refusals in one case (a record still held, not sourced, the wrong source, a key already held, a malformed key). The marker names `source` and `issue` with no interaction between them, and "and_more" hides what is tested.
- `tests/cli/test_source_links.py:214`: `covers("<type> source relink", "source", "issue", "--json")` on an effect case. Required arguments appear in every case and are not a combination, so the marker should be the `--json` pair plus a single argument pair.
- `tests/cli/test_source_links.py:403, 422, 441, 654, 690`: the same three-element `(source, issue)` marker on single-behaviour cases.
- `tests/cli/test_source_ownership.py:50, 83`: two or three refusals batched per case.

**Fix:** one case per refusal, each named for its refusal and declaring the parameter the refusal is about. Use `covers(key, "source")` and `covers(key, "issue")` as separate markers where each effect is asserted.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — JSON field projections asserted instead of the whole --json object

<!-- sq:finding:F10:body -->
**Rule:** ADR-1172 rule 5: assert "the JSON object". A projection of a few fields survives a wrong or extra field, just as a substring survives a wrong message.

**Sites:** field projections in place of the whole `--json` document: `[(r["created"], r["refreshed"]) ...]`, `shown["views"][...]["body"]`, `[c["author"] for c in ...]` and the like. By module (line numbers of the asserts):
- `test_source_pull.py`: 64 sites, from `:103` to `:807`;
- `test_source_links.py`: 36, from `:97` to `:687`;
- `test_source_connectors.py`: 34, from `:62` to `:579`;
- `test_source_check.py`: 15 (`:114-141, 244, 247, 347-353, 371`);
- `test_source_comments.py`: 9;
- `test_source_converters.py:50-52, 80`;
- `test_source_record.py:67, 105`;
- `test_source_ownership.py:131`;
- `test_source.py:83`;
- `test_source_scope.py:132`;
- `tests/cli/test_workflow.py` (`test_views_json_marks_a_view_that_keeps_a_stored_body`, the `if row["stored"]` filter).

**Fix:** compare the whole object. Normalise only what varies by run, as `_shown` does (tracker address, `etag`). Build the expected report or comment with a small helper per module, like `issue(...)` in `tests/check/_arrange.py`, so that the whole document stays readable.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Check-rule tests: an unmarked case, two breaches in one case, partial issue assertions

<!-- sq:finding:F11:body -->
**Rule:** CONTRIBUTING's check-rule rules: each test declares `breaches(...)`; it runs `check_json` on the arranged state asserting `[]`, then after *one* breaching change; it asserts the whole JSON array built with `issue(...)`.

**Sites:**
- `tests/check/test_prose_rules.py:166`, `test_a_body_holding_only_a_stored_view_body_is_still_unwritten`: no `breaches` marker. It is the only unmarked test in `tests/check` apart from `test_baseline.py`. It asserts the breach first and the clean state second.
- `tests/check/test_source_rules.py:86-123`, `source_declared`: two breaching changes (disabled, then undeclared) in one case.
- `tests/check/test_source_rules.py:261-284`, `comment_attributes_valid`: asserts a projection (`len`, `rule`, `level`, `item`) plus a `re.fullmatch` on the message, not `issue(...)`. Under the frozen clock the timestamp is fixed. If it is not fixed, normalise it.
- `tests/check/test_source_rules.py:134`: an extra partial assertion. It is harmless, because the whole array follows.
- `tests/check/test_corpus_integrity_rules.py:480-499`: asserts only the `markers_balanced` messages, filtered out of the array.

**Fix:** declare `breaches("body_written")`, or fold the stored-pair boundary into the existing `body_written` case as a sibling item that must not be reported. Split `source_declared` into two cases. Assert the whole array with `issue(...)` in the last two.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — declare_stored_view overwrites the override, so nine stored-view cases opt out as bundled_only

<!-- sq:finding:F12:body -->
**Rule:** ADR-1172 Scope: cases reach their host through the profile and run on both squads. CONTRIBUTING: `bundled_only` carries the reason a case is about one squad's own spelling.

**Sites:** nine stored-view cases carry `bundled_only("the stored view is declared by an override")`:
- `tests/cli/test_item_verbs.py:1323, 1340, 1360, 1372, 1400, 1415`;
- `tests/cli/test_show.py:289, 317`;
- `tests/cli/test_repair.py:297`.

They already address through `P.ref`/`P.ref_prefix`. The real reason they cannot run on the override squad is that `tests/_stored_view.py:20-27` (`declare_stored_view`) *overwrites* `.overrides/workflow.toml`, which erases the override squad's own vocabulary. That is not about bundled spelling, so the override job silently loses the stored-view surface.

**Fix:** make `declare_stored_view` append its `[views.<name>]` table to the existing override (or merge it), then drop the nine `bundled_only` markers. `test_repair.py:297` also spells `task 3`. Switch it to the profile.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T22:10:24Z] `reviewer` Paul Reviewer:
  - - 12 findings (1 high, 7 medium, 4 low). Recommended verdict: changes requested. The review stays open for the fixes.
    - F1 is the blocker: the override-squad CI job (`--squad override tests/cli`) is red at 973058e5 because of the source modules alone.
    - Three questions for @architect: the home of the `sources.toml` load and grammar refusals (F6, F7), whether rule 6 may allow one module per leaf of a large group (F8), and whether rule 5 should admit the per-user credential store as command output (F5).
    - @tech-lead: please schedule the fix task(s). F1 first.
- [2026-11-04T22:18:09Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-04) on the three questions in this review:
      - Rule 6: a large command group may have one test module per leaf command (`test_source_pull.py`, `test_source_check.py`, …). Each case lives in the module of the command it declares, so cases about other command groups move to those groups' modules.
      - Credentials: tests read stored credentials back through `sq source credential … --json`. The file itself is read only for what no command shows (its 0600 mode), with the path from the test's own fixture, not from `CredentialStore` in `src`.
      - `sources.toml` load and grammar refusals: one case per distinct message in `tests/check` under `breaches("sources_loads")`. The CLI keeps a single case showing that a command refuses when `sources.toml` does not load.
- [2026-11-04T22:19:17Z] `architect` Robert Architect:
  - ADR-1172 amended for the three rulings in 5673927 (rules 1, 5, 6). F5-F8 can be fixed against it. CONTRIBUTING.md needs one matching line (not edited): its "one breach test per rule" should say a load rule gets one case per distinct message. @tech-lead
<!-- sq:discussion:end -->
