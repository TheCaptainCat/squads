---
id: REV-1299
sequence_id: 1299
type: review
title: 0.20 tests against the CLI surface test rules
status: ChangesRequested
author: reviewer
refs:
- ADR-1172
description: '0.20 tests vs ADR-1172: F15, F17 reopened (one site each); rest verified'
subentities:
- local_id: F1
  title: Source CLI tests hard-code bundled vocabulary and fail on the override squad
    (142 failed, 118 errors)
  status: Verified
  severity: high
- local_id: F2
  title: Messages and refusals asserted by substring, prefix or one picked line instead
    of whole lines
  status: Verified
  severity: medium
- local_id: F3
  title: test_source_record reads .squads.json to assert the rebuilt index's keys
  status: Verified
  severity: medium
- local_id: F4
  title: Item files hand-written to arrange states that source pull produces
  status: Verified
  severity: medium
- local_id: F5
  title: Credential store read directly and its path computed through CredentialStore
    from src
  status: Verified
  severity: low
- local_id: F6
  title: covers markers declare a parameter the case is not about, on refusals and
    effect cases
  status: Verified
  severity: medium
- local_id: F7
  title: Shape tables of sources.toml grammar refusals and author-name escapes in
    tests/cli
  status: Verified
  severity: medium
- local_id: F8
  title: Source tests split into 11 feature modules that hold cases of other command
    groups
  status: Verified
  severity: medium
- local_id: F9
  title: Several refusals batched in one case under multi-parameter markers and a
    vague name
  status: Verified
  severity: low
- local_id: F10
  title: JSON field projections asserted instead of the whole --json object
  status: Verified
  severity: low
- local_id: F11
  title: 'Check-rule tests: an unmarked case, two breaches in one case, partial issue
    assertions'
  status: Verified
  severity: medium
- local_id: F12
  title: declare_stored_view overwrites the override, so nine stored-view cases opt
    out as bundled_only
  status: Verified
  severity: low
- local_id: F13
  title: Coverage guard requires only the bundled tree's pairs, though each test squad's
    tree has its own
  status: Verified
  severity: medium
- local_id: F14
  title: Custom type groups list Typer's completion options in their help
  status: Verified
  severity: medium
- local_id: F15
  title: Pull report counts pinned from observed output contradict the report's own
    definition
  status: Fixed
  severity: medium
- local_id: F16
  title: Twin-holder case branches its expected output on profile.host_has_badge
  status: Verified
  severity: low
- local_id: F17
  title: Later 0.20 tests add 84 substring asserts and two check cases without breaches
    markers
  status: Verified
  severity: medium
- local_id: F18
  title: 'Windows CI: self-skipping credential cases failed the coverage teardown'
  status: Verified
  severity: medium
- local_id: F19
  title: Pull counts kept by per-path bookkeeping instead of one count after the pre-pass
  status: Fixed
  severity: low
created_at: '2026-11-04T22:05:56Z'
updated_at: '2026-11-05T06:12:37Z'
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
- [2026-11-04T23:56:53Z] `python-dev` Elias Python:
  - Fixed: the eleven source CLI modules build their type maps, field maps, addresses and ids from the profile; the override squad selects the source_description view and the profile gains host_folder with its guard row.
- [2026-11-05T04:21:02Z] `reviewer` Paul Reviewer:
  - Verified at 9955faac: --squad override tests/cli tests/check 1217 passed, 171 skipped, 0 failed; remote mode on the override squad 1048 passed, 171 skipped.
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
- [2026-11-05T03:38:59Z] `python-dev` Elias Python:
  - Fixed: the listed sites compare (exit_code, output) with the whole text; the port is normalised as _checked does and the " ".join(output.split()) rewrapping is gone. Negative containment checks that the secret never leaks stay.
- [2026-11-05T04:21:03Z] `reviewer` Paul Reviewer:
  - Verified: no positive substring, prefix or rewrapped-message assert is left in the source cases (test_source_*.py, test_item_source.py, tests/cli/_source_*.py); the chmod refusal is a whole line.
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
- [2026-11-05T01:40:09Z] `python-dev` Elias Python:
  - Fixed: the rebuilt index's key-set assertion is dropped from test_source_record; after == before of show --json carries the claim.
- [2026-11-05T04:21:04Z] `reviewer` Paul Reviewer:
  - Verified: the record cases no longer open .squads.json; the rebuild is proved through show --json.
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
- [2026-11-05T01:40:10Z] `python-dev` Elias Python:
  - Fixed: the valid record, the source:platform comment header and the renamed author_name are arranged with the tracker harness and source pull (the author-name case bumps updated_at on the note and the issue, and the pull refreshes the attribute). Malformed and duplicate records stay hand-written.
- [2026-11-05T04:21:05Z] `reviewer` Paul Reviewer:
  - Verified: the valid record and the source author come from a pull through the harness (tests/cli/_source_record.py:pulled); hand edits remain only for states no command writes.
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
- [2026-11-05T01:40:10Z] `python-dev` Elias Python:
  - Fixed: tests/cli/test_source.py and tests/daemon/test_the_credential_verbs.py no longer import CredentialStore. The expected path comes from a credential_file fixture beside credentials_home; stored values are read back through set --json and remove --json; the file is opened only for its modes and the secret's absence after remove.
- [2026-11-05T04:21:06Z] `reviewer` Paul Reviewer:
  - Verified: no CredentialStore import in tests/cli or tests/daemon; values read back through sq source credential --json, the file only for its modes, path from the fixture.
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
- [2026-11-05T01:40:11Z] `python-dev` Elias Python:
  - Partly fixed: the load refusals no longer declare an unrelated pair (the CLI keeps one case on source list), and the priority refusal in test_source_ownership declares --<field> beside --title. Still open: test_source_identities declares --set for a case that also asserts the effect of the derived --links map option, and no pair names a map option (derived_names covers fields, target kinds and create-time str/list/date attributes only), so a --links marker is stale in the coverage guard. Needs a ruling on a map-option derivation.
- [2026-11-05T03:38:57Z] `python-dev` Elias Python:
  - Fixed: the override squad declares a map attribute (links) on its reference type, the profile names it (map_type, map_attr), and the surface derives it as --<attribute:map>; test_source_identities now splits the --set refusal (declares --set) from the effect case (declares --<attribute:map>), and test_source_ownership declares --title, --<field> and --desc in one case each.
- [2026-11-05T04:21:07Z] `reviewer` Paul Reviewer:
  - Verified: load refusals are 32 breaches("sources_loads") cases in tests/check; the field refusal declares --<field>, the map effect --<attribute:map>. The guard side of the map pair is F13.
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
- [2026-11-05T01:40:11Z] `python-dev` Elias Python:
  - Fixed: the sources.toml grammar and load refusals are 30 sources_loads cases in tests/check/test_source_rules.py, one per distinct message (rows repeating a message at another column, character or scope key dropped). tests/cli/test_source_scope.py keeps the four documents that load; the author-name parametrize is two cases (quote plus control character, and no name).
- [2026-11-05T04:21:08Z] `reviewer` Paul Reviewer:
  - Verified: one case per distinct message; the author-name table is two cases.
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
- [2026-11-05T04:10:57Z] `python-dev` Elias Python:
  - - Cases moved to the module of the command each declares (1388 collected on both squads before and after, same ids).
    - source leaf modules: test_source_pull (pull, incl. converters and connector pulls), test_source_check, test_source_list, test_source_credential (set, remove).
    - test_item_source: `<type> source unlink|relink`.
    - Other groups: test_show, test_operator, test_item_verbs, test_comment_verbs, test_inbox_mine, test_import, test_check, test_repair, test_role, test_override, test_workflow.
    - Dissolved: test_source, _comments, _connectors, _converters, _identities, _links, _ownership, _record, _scope.
    - Shared arrangements: tests/cli/_source_{checks,comments,connectors,declared,links,ownership,pulls,record}.py, imported as modules.
- [2026-11-05T04:21:09Z] `reviewer` Paul Reviewer:
  - Verified: every case sits in the module of the key it declares (source leaves: pull, check, list, credential; <type> source in test_item_source.py). 1388 cases collected before (fb523e99) and after on both squads, same function names.
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
- [2026-11-05T03:38:58Z] `python-dev` Elias Python:
  - Fixed: the five relink refusals are five cases named for their refusal, each declaring the one parameter it is about; the relink effect case declares --json plus source; the scope cases declare issue; the ownership refusals are one case each (title, mapped field, comment edit, comment remove, --as, import).
- [2026-11-05T04:21:10Z] `reviewer` Paul Reviewer:
  - Verified: one case per refusal, each named for it, single-parameter markers.
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
- [2026-11-05T03:39:00Z] `python-dev` Elias Python:
  - Fixed: pull reports, source check documents, comment lists, inbox entries, operator documents, workflow views and the show documents of pulled items are compared whole, built by small helpers (tests/cli/_pulled.py: item, shown_item, without_digests; tests/cli/_output.py: pull_report, pull_document, alice_document, MANAGER_ROW). Only the comment content digest is set aside (checked as a prefix pair), and the tracker address and etag as _shown did. Kept as picked: ids of list rows (membership claim) and the source record of the out-of-scope items 4 and 5 of the filter case.
- [2026-11-05T04:21:11Z] `reviewer` Paul Reviewer:
  - Verified for the listed sites. Four leftover projections are folded into F16.
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
- [2026-11-05T03:59:32Z] `python-dev` Elias Python:
  - Fixed in the working tree: body_written stored-pair case declares its marker with a clean pre-state; source_declared split in two; comment_attributes_valid and markers_balanced assert the whole array via issue(); partial assertion dropped.
- [2026-11-05T04:21:12Z] `reviewer` Paul Reviewer:
  - Verified for the listed sites. Two new unmarked check cases from later work are in F17.
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
- [2026-11-05T03:59:32Z] `python-dev` Elias Python:
  - Fixed in the working tree: declare_stored_view merges into the existing override (and adds the view to a [selected].views list); the nine bundled_only markers are gone and the cases pass on both squads; show cases moved to populated_project, repair case addressed through the profile.
- [2026-11-05T04:21:13Z] `reviewer` Paul Reviewer:
  - Verified: declare_stored_view merges into the existing override; the nine cases run on both squads.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Coverage guard requires only the bundled tree's pairs, though each test squad's tree has its own

<!-- sq:finding:F13:body -->
**Rule:** ADR-1172 rule 3. The coverage guard "enumerates the tree with `_help_tree.command_nodes()` for each test squad". The 2026-11-05 amendment adds that it "requires a declaration only for the bundled tree's pairs" and treats the override squad's map pairs as known.

**Measured** at 9955faac:
- `_surface()` (`tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py:112`) builds `Surface(bundled.pairs, bundled.leaves, squad_known() - bundled.known)`.
- `squad_known()` (`tests/_cli_surface.py:342-356`) adds only the `--<attribute:map>` derivation. It does not walk the override tree.
- My probe built the override squad's tree with its spec bound (the known positive `<type> update --<attribute:map>` showed up) and compared it with the bundled tree. Other pairs exist only on the override squad:
  - `<type> <kind> update --no-<field>`, from a kind field that is not required. No test declares it. A marker naming it would be reported stale, so it cannot be declared at all.
  - `--install-completion` / `--show-completion` on `<type>` and `create <type>`. That is a product defect, recorded as a separate finding.

**Judgement:** the guard is wrong, and the amendment wrote its gap into the ADR. The original sentence is the right rule. A pair that exists only on the override squad is surface that no test is required to cover. That gap is exactly what running the suite on a second squad was meant to close.

**Fix:**
- The guard enumerates every test squad's tree (bundled, and override with its spec bound), requires the union of their pairs, and reports a marker as stale only when it is in neither tree.
- `squad_known` goes away.
- The `invoke` fixture records against the tree of the squad the run is on.
- @architect: revert the "requires a declaration only for the bundled tree's pairs" sentence of the 2026-11-05 amendment.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-11-05T05:56:46Z] `reviewer` Paul Reviewer:
  - Verified at 2734e068: the guard requires the union of both trees (all_squads_surface). Removing the marker at tests/cli/test_subentity_verbs.py:1118 makes it report "undeclared: sq <type> <kind> update --no-<field>"; restored, 42 passed.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Custom type groups list Typer's completion options in their help

<!-- sq:finding:F14:body -->
**Defect (product, found by the F13 probe):** in a squad whose workflow override declares its own types, every custom type's group and its create command list Typer's `--install-completion` and `--show-completion`. The bundled types do not.

**Reproduced** at 9955faac on the override test squad (`tests/_override_populated.init_override_populated`):
- `sq create job --help` lists `--install-completion` and `--show-completion`;
- `sq job --help` lists both as well.

On the bundled squad, neither `sq task --help` nor `sq create task --help` lists them. `EXCLUDED_PARAMS` (`tests/_cli_surface.py:48-51`) excludes them only on the root key `""`.

**Cause (inferred, not traced):** the Typer app built per custom type keeps Typer's default `add_completion=True`. The help-rule guard's custom-vocabulary tree does not catch it either.

**Fix:** build the custom type groups with `add_completion=False`, like the bundled ones. The F13 guard over the override tree then holds it. @qa: please file the bug.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-11-05T05:56:47Z] `reviewer` Paul Reviewer:
  - Verified at 2734e068: on the override test squad, sq job --help and sq create job --help list no completion option (0 lines, 2 before).
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Pull report counts pinned from observed output contradict the report's own definition

<!-- sq:finding:F15:body -->
**Question asked:** are the counts that round 3 pinned in the filter-lost, dropped-event and secondary-source cases what the product should report? No. Each one matches the code, not the report's own definition. `SourcePullReport` (`src/squads/_api/_dto/_sources.py:62-78`): "how many it refreshed or left as they were"; `filtered_out`: "listed issues the filter rejected that no item holds".

**1. A gone item is counted nowhere.**
- `test_a_linked_issue_the_filter_lost_is_out_of_filter_or_gone_and_its_item_stays` (`tests/cli/test_source_pull.py:737-769`) pins `refreshed=1, unchanged=2` for four held items. Items 4 and 5 both have their record rewritten (out-of-filter and gone).
- The gone path (`src/squads/_services/_pull.py:599-609`) emits a `SourceEvent` but increments neither counter.
- Expected: `refreshed=2`, or the DTO states that gone items are reported only by their line.

**2. A dropped issue is counted as refreshed.**
- `test_an_issue_whose_events_were_dropped_is_fetched_and_reported_again` (`:1276-1302`) pins `refreshed=1` while every event of #13 was dropped and nothing was written.
- The conversion path restores the counts on a drop (`_pull.py:142-150`), but the import pre-pass (`_without_failing_issues`, `:640-680`) discards `created` and leaves `refreshed` as it was.
- Expected: `refreshed=0, unchanged=1`.
- `test_a_dropped_link_…` (`:1305-1327`) pins `refreshed=1` on both pulls. Item 2's link is held back with its stored time, so whether the second pull writes anything needs checking (inferred, not measured).

**3. `filtered_out` counts an issue a peer source's item holds.**
- With two split sources on one tracker (`:520-583`), each report has `filtered_out=1` for the other source's issue, including after both pulls, when an item holds it.
- `_triage` (`src/squads/_services/_fetch.py:95-116`) checks only this source's holdings.

**Fix:** @tech-lead with @product-owner: rule what each counter means, write it in the DTO docstrings, fix the code or the docstring to match, and pin the ruled values in these cases.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-11-05T05:56:49Z] `reviewer` Paul Reviewer:
  - Reopened at 2734e068. One re-pinned count still follows the code instead of ADR-1274 §14.
    
    - `test_a_dropped_link_keeps_the_host_issue_to_be_fetched_and_reported_again` (`tests/cli/test_source_pull.py:1421-1445`) pins `refreshed=1, dropped=1` on both pulls.
    - A probe of the same steps (my own, not in the suite) found that `show --json` of item 2 and `reflog --json` are byte-identical before and after each of the two pulls. The pull wrote nothing.
    - The probe was checked against a known positive: an `updated_at` bump alone changes both outputs and reports `refreshed=1`.
    - §14: refreshed is an issue for which "the pull applied at least one change"; unchanged is one for which "the pull wrote nothing". #12's only change is its link, and that was dropped. The record event is set back to the stored time, so it writes nothing.
    - Expected: `unchanged=1, dropped=1`, with the link drop still named on #12's line. Fix the counting (an issue whose surviving events change nothing is unchanged) and re-pin.
    
    The other re-pinned cases match §14:
    - filter-lost: `refreshed=1, unchanged=2, gone=1`, four issues;
    - dropped-event: `unchanged=1, dropped=1`;
    - split sources: `held_elsewhere`.
    
    The unnamed pull of split sources still shows `filtered_out=1`. That is the accepted gap (7b2edef).
    
    Note for @architect: §14 says a held-elsewhere issue "is named on a held-by line". The code (`_fetch.py:116-119`) and `docs/sources.md:457` name it only when the filter accepts it. Align §14 with them, or the code with §14.
- [2026-11-05T06:06:48Z] `reviewer` Paul Reviewer:
  - Behaviour checked at 3dd2fd80: the dropped-link case now pins unchanged=1, dropped=1. A probe agrees for dry and real pulls, with and without a real change on the issue. test_source_pull.py passes on both squads. The held-by row of ADR-1274 §14 is aligned (5bcf9890). Left Fixed, not Verified: the counting is a special case, and the general count after the pre-pass is F19.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Twin-holder case branches its expected output on profile.host_has_badge

<!-- sq:finding:F16:body -->
**Rule:** ADR-1172 Scope ("one marker declares the same pair on both squads", with cases reaching their host through the profile) and rule 5 (the whole JSON object).

**Site:** `tests/cli/test_source_pull.py:814-860`, `test_two_items_holding_one_issue_are_both_refreshed_and_no_third_is_made`. The twin is created as `profile.host`. The expected `lines` then branch on `if profile.host_has_badge` (`:846-853`):
- the override run alone asserts a second behaviour ("<badge> skipped, <host> items have no such field");
- the bundled run alone asserts its absence.

The case tests different behaviour per squad. The field-skipped behaviour is held on one squad only, inside an unrelated case, under the name of another behaviour.

**Judgement:** a defect. A profile flag that selects the expected output turns one case into two squad-specific cases.

**Fix:**
- Make the twin the reference type (`profile.ref`), so both squads expect the same lines.
- Give the field-skipped line its own case, named for it, through a profile entry for a type that lacks the badge field on both squads.

**Leftover projections in the source cases**, which belong in the same fix: `test_source_pull.py:858` (`(twin_row["title"], twin_row["source"])`), `:1044` (`first["source"]`), `test_source_credential.py:59` (`removed["removed"]`), and `test_item_verbs.py:1811-1827` (map attribute values). Compare whole objects there too.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-11-05T05:56:48Z] `reviewer` Paul Reviewer:
  - Verified: the twin is the reference type, so both squads expect the same lines; the field-skipped line has its own case (test_source_pull.py:928). The needs_parent branch only arranges a parent and asserts nothing different, so it is fine.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Later 0.20 tests add 84 substring asserts and two check cases without breaches markers

<!-- sq:finding:F17:body -->
**Rule:** ADR-1172 rule 5 (whole lines, never a substring) and CONTRIBUTING's check-rule rules (each test declares `breaches`).

**Scope:** 0.20 tests added after the first audit (973058e5..9955faac) by work other than TASK-1300 (the injected skills and raw output commits). Lines moved within the diff are excluded.

**Sites:** 84 `in` / `not in` / `startswith` / `endswith` asserts, by module:
- `tests/cli/test_role.py`: 31
- `test_migrate.py`: 13
- `test_item_verbs.py`: 13
- `test_skill.py`: 9
- `test_init.py`: 6
- `test_sync.py`: 5
- `test_repair.py`: 4
- `test_show.py`: 3

Negative absence checks (a secret, an escape code or a stripped region that must not appear) are fine. The positive containment asserts are the defect, for example `test_init.py` (`'"type": "note"' in declared.output`) and `test_item_verbs.py` (`f"- **file:** {TASK_PATH}\n" in output`).

Two check-rule tests carry no `breaches` marker and run the report once:
- `tests/check/test_source_rules.py:657`, `test_prose_that_names_the_attribute_tag_is_not_an_attribute_line`;
- `:682`, `test_a_body_example_naming_an_undeclared_source_author_is_not_a_comment` (commit 2a11964b).

**Fix:**
- Compare whole lines or whole documents at the positive sites.
- Fold the two check boundaries into the `comment_attributes_valid` and `source_author_declared` breach cases, as sibling items that must not be reported.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-11-05T05:56:49Z] `reviewer` Paul Reviewer:
  - Reopened at 2734e068 for one site. tests/cli/test_role.py:1625 still has the positive substring assert  f"## {profile.host.title()} items" in before  on the whole role show output (override squad). It should test membership in before.splitlines(), like the rewrites at :1670 and :1685. The other 32 kept asserts are legitimate: 29 absence checks, test_migrate.py "... agent files regenerated" in lines (membership in a list of lines), and two whole-document containments of role show output in the generated AGENTS.md (test_init.py, test_migrate.py), which rule 5 allows reading. Mutation sample on the rewrites: 4 product-string breaks (playbook line, playbook heading, migrate footer, single-line refusal) gave 12 red cases; all restored. The two check cases are folded into breach cases.
- [2026-11-05T06:06:48Z] `reviewer` Paul Reviewer:
  - Verified at 3dd2fd80: tests/cli/test_role.py:1625 now tests membership in before.splitlines(). test_role.py passes on both squads.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Windows CI: self-skipping credential cases failed the coverage teardown

<!-- sq:finding:F18:body -->
**Defect** (added at the tech lead's request for the record, comment 145d6da). `test (windows-latest)` and `remote-mode (windows-latest)` on the release PR (run 41932646293) had three teardown errors, `covers declares pairs no call reached`, on the credential cases that skip on Windows:
- `test_credential_set_reads_each_value_from_stdin_and_stores_it_privately`;
- `test_credential_set_ignores_what_a_crash_left_and_tightens_an_open_directory`;
- `test_a_store_other_users_can_read_is_refused_naming_chmod`.

**Cause:** `_posix_modes_only()` calls `pytest.skip` after `invoke` is set up, and the teardown then found the declared pairs unreached.

**Fix (ST2):** a `pytest_runtest_makereport` wrapper (`tests/conftest.py:220-223`) keeps each phase's report, and `call_was_skipped` (`tests/_helpers.py:86-89`) skips the pair check in both the `invoke` and `check_json` teardowns. ADR-1172 rule 3 records the exception.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-11-05T04:21:32Z] `reviewer` Paul Reviewer:
  - Verified at 9955faac: with sys.platform forced to win32 during the call (a probe plugin, not in the suite), the three cases are skipped with no teardown error (1 passed, 3 skipped). Not run on a Windows runner.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Pull counts kept by per-path bookkeeping instead of one count after the pre-pass

<!-- sq:finding:F19:body -->
**Rule:** ADR-1274 §14: an issue is `refreshed` only if the pull wrote something for it, and `unchanged` if it wrote nothing.

**Site:** `src/squads/_services/_pull.py:721-743`, `_count_unwritten_as_unchanged`. After the pre-pass it moves an issue from refreshed to unchanged when a link of the issue was dropped and every surviving event is a `source` record equal to the stored one.

**Why it holds today:**
- Compile emits only events that change something: the title only when it changed, the record only when it differs, and likewise the description and comments.
- `_keeping_stored_time` is the one place after compile that can turn an event into a no-op.

The special case therefore gives the right counts. My probe (not in the suite) checked the dropped-link steps with no other change and with a changed description: `--dry-run` and the real pull agree, unchanged 1 without a change and refreshed 1 with it, and the reflog agrees.

**The defect is the design.** The refreshed/unchanged count is kept by four pieces of bookkeeping:
- the counters incremented in `issue()`;
- their restore in `attempt()` on a conversion failure;
- `uncount()` on a dropped issue;
- this demotion.

Each one guards one path. A future post-compile rewrite would need a fifth.

**General implementation:**
- `_keeping_stored_time` drops a `source` event whose kept record equals the stored one.
- The pull counts once, after the pre-pass: a held issue with at least one surviving event is refreshed, otherwise unchanged; an issue with none of its compiled events surviving is dropped.
- That replaces `refreshed_labels`, the restore, the refreshed half of `uncount` and this function.

Counting from the actual writes does not fit: `_apply_events` reports touched ids whether or not an event changed anything, and `--dry-run` writes nothing yet must report the same counts.

**Fix:** implement the single count after the pre-pass. The existing count cases (`tests/cli/test_source_pull.py`) are the regression net and need no new case.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->
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
- [2026-11-04T23:37:58Z] `tech-lead` Olivia Lead:
  - @reviewer: please add a finding for the Windows CI failure, so the finding trail is complete. ST2 of TASK-1300 holds the fix.
    - Jobs: `test (windows-latest)` and `remote-mode (windows-latest)` on the release PR (run 41932646293), three errors at teardown, all `covers declares pairs no call reached`: `test_credential_set_reads_each_value_from_stdin_and_stores_it_privately`, `test_credential_set_ignores_what_a_crash_left_and_tightens_an_open_directory`, `test_a_store_other_users_can_read_is_refused_naming_chmod`.
    - Cause: `_posix_modes_only()` in `tests/cli/test_source.py:34-37` calls `pytest.skip` inside the test body, after the `invoke` fixture is set up. No command runs, so the fixture's teardown (`tests/conftest.py:285-291`) finds the declared pairs unreached and fails the test.
    - The same trap waits for any case that skips at run time (`tests/cli/test_sync.py:146`, `tests/cli/test_daemon.py:207`), and `check_json` (`tests/check/conftest.py`) has the same teardown shape. The planned fix makes both teardowns pass over a test whose call phase was skipped.
- [2026-11-05T03:43:39Z] `manager` Catherine Manager:
  - For the re-review: ADR-1172 rule 3 says the coverage guard walks the tree for each test squad, while the guard's _surface() walks only the bundled tree and treats the override squad's map pairs as known, not required (the architect's note on ADR-1172). Judge whether the guard or the ADR sentence is wrong and record a finding.
- [2026-11-05T04:21:33Z] `reviewer` Paul Reviewer:
  - - Re-review at 9955faac: F1-F12 and F18 (the Windows teardown) are Verified. Recommended verdict: changes requested, for five new findings.
    - Runs:
      - bundled main set (meta, cli, check, daemon, regressions): 2258 passed, 4 skipped;
      - `--squad override tests/cli tests/check`: 1217 passed, 171 skipped;
      - override squad in remote mode: 1048 passed, 171 skipped;
      - collection: 1388 cases on both squads, before (fb523e99) and after the move, same function names.
    - The question on rule 3 (4a1500e): the guard is wrong, not the ADR's original sentence. The override tree has a pair no test can declare (`<type> <kind> update --no-<field>`). See F13; @architect, please revert the "bundled tree only" sentence of the 2026-11-05 amendment.
    - The F13 probe also found a product defect: custom type groups list the completion options (F14). @qa, please file the bug.
    - The round 3 pull counts follow the code, not the report's definition: a gone item is counted nowhere, a dropped issue counts as refreshed, and `filtered_out` counts a peer source's issue (F15). @tech-lead, please get a ruling with @product-owner.
    - `host_has_badge`: a profile flag that selects the expected output; see F16.
    - F17 covers 0.20 tests added after the first audit by the injected skills work.
    - The Approved transition stays with the approver in any case: this review's author does not approve it.
- [2026-11-05T04:22:49Z] `product-owner` Nina Product:
  - F15: counter definitions ruled on ADR-1274 (comment dated 2026-11-05): every issue lands in exactly one counter; new counters gone, dropped, held_elsewhere; filtered_out means no item of any source holds it.
- [2026-11-05T04:23:06Z] `architect` Robert Architect:
  - @reviewer F13: ADR-1172 rule 3 corrected in place: the guard requires the union of both test squads' trees, a one-squad pair is checked against the squad that has it, and the invoke teardown skips a pair only the other squad has. The guard and fixture code still need the fix.
- [2026-11-05T04:27:37Z] `tech-lead` Olivia Lead:
  - F13 to F17 are scheduled on TASK-1310 (Draft), one subtask each. F14 still has no bug item: @qa, please file it so ST1 can ref it.
- [2026-11-05T05:57:06Z] `reviewer` Paul Reviewer:
  - - Final re-review at 2734e068: F13, F14 and F16 are Verified. F15 and F17 are reopened, each for one site. Recommended verdict: changes requested.
    - F15: the dropped-link case pins `refreshed=1`, but both pulls write nothing to item 2 (probe checked against a known positive). Under ADR-1274 §14 that is `unchanged=1`, so the counting and the pin need a fix. The other re-pinned cases match §14. The two accepted gaps (7b2edef) stand. @architect: §14's held-by naming differs from the code and the docs; please align one with the other.
    - F17: one positive substring remains at `tests/cli/test_role.py:1625`. The other 32 kept asserts are legitimate. The mutation sample on the rewrites came out red: 12 cases from 4 breaks.
    - REV-1307 F6 and F7 are Verified, forced from Deferred.
    - @python-dev, for the two one-site fixes. The Approved transition stays with the second party.
- [2026-11-05T05:57:38Z] `manager` Catherine Manager:
  - The held-by naming: the code and docs/sources.md stand (a held-elsewhere issue the filter rejects is counted but not named, like filtered out); ADR-1274 §14 aligns to that. F15's dropped-link case and F17's last site go to python-dev.
- [2026-11-05T06:06:49Z] `reviewer` Paul Reviewer:
  - Re-review at 3dd2fd80: F17 Verified. F15 behaviour holds, and the ADR-1274 §14 held-by alignment is confirmed. F15 stays Fixed because the counting is a special case; F19 (low) records the general single-count design. Recommended verdict: changes requested, until F19 is fixed or ruled WontFix/Deferred. @python-dev @tech-lead
<!-- sq:discussion:end -->
