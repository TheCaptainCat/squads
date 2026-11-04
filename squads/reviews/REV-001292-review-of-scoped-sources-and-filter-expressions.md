---
id: REV-1292
sequence_id: 1292
type: review
title: Review of scoped sources and filter expressions
status: Approved
author: reviewer
refs:
- FEAT-1285
- TASK-1286
- ADR-1274
- BUG-1284
description: Filter grammar, scopes, report counts, restricted issues, cross-source
  links, probes and docs
subentities:
- local_id: F1
  title: An issue another source holds is read in detail on every pull
  status: Verified
  severity: medium
- local_id: F2
  title: Jira in-scope search breaks on a JQL ending in ORDER BY
  status: Verified
  severity: medium
- local_id: F3
  title: GitLab in-scope check is case-sensitive, GitLab paths are not
  status: Verified
  severity: medium
- local_id: F4
  title: Coverage probe ignores the filter and names unmapped issues
  status: Verified
  severity: medium
- local_id: F5
  title: A link to a restricted issue is named on every report
  status: Verified
  severity: medium
- local_id: F6
  title: Filter precedence, or, not-scope and escapes are untested
  status: Verified
  severity: medium
- local_id: F7
  title: Cross-source and scope decisions leave mutants alive
  status: Verified
  severity: medium
- local_id: F8
  title: Internal-note test cannot fail; Jira by-ID restriction untested
  status: Verified
  severity: medium
- local_id: F9
  title: Unnamed pull reports a link not followed that it then makes
  status: Verified
  severity: low
- local_id: F10
  title: Deep nesting or long CRLF runs crash the parser
  status: Verified
  severity: low
- local_id: F11
  title: Quoted values refuse non-control characters like NBSP
  status: Verified
  severity: low
- local_id: F12
  title: Scope values are not shape-checked at load
  status: Verified
  severity: low
- local_id: F13
  title: Report and check wording out of step with the new model
  status: Verified
  severity: low
- local_id: F14
  title: Docs say a held issue is never read; an unnamed first pull reads it twice
  status: Verified
  severity: low
created_at: '2026-11-04T15:28:54Z'
updated_at: '2026-11-04T16:45:44Z'
---
<!-- sq:body -->
## Scope

Batch review of scoped sources and filter expressions as delivered by TASK-1286 (ST1 to ST8) on release/0.20, `32d51438..70546bf9` restricted to the sources work: `src/squads/_sources/` (`_filter.py`, `_spec.py`, `_loader.py`, `_registry.py`, the three connector subpackages and the probes), `src/squads/_services/` (`_fetch.py`, `_pull.py`, `_source_links.py`, `_source_checks.py`, `_comment_view.py`, `_source_view.py`, `_sources_ops.py`), the pull report DTO and renderer, the `sq override scaffold sources` starter, the source tests and fixtures, `docs/sources.md`, `docs/stability.md` and the CHANGELOG 0.20 entries. The re-export sweep is reviewed in REV-1291 and left out here.

Authority: ADR-1274 section 14 (the 2026-11-04 source-selection entries) with rulings f6cbdfc, ec3c412 and af70274, FEAT-1285's acceptance criteria, BUG-1284, the developer comments on TASK-1286, ADR-1287 for imports.

## Method

- Read the code above against the ADR entries **Source selection**, **States under a full listing**, **What becomes an item**, **Links across sources**, **Probes** and **No migration**.
- Drove the dev build on scratch squads outside the repository, against a loopback tracker that serves recorded GitLab, GitHub and Jira Cloud answers (the routes of `tests/fixtures/sources/`, extended per scenario) and logs every request: the filter grammar through `sq source list`, every scope and filter load refusal, the BUG-1284 epics and stories scenario in both pull orders and in one unnamed pull, group and project scopes overlapping, held issues rejected by the filter, moved out of the scope, deleted and made confidential, `show --refresh`, `unlink` and `relink`, the probes, and the starter's worked example.
- Mutation-tested a copy of the tree (never the repository) against the source test modules: 26 mutants (11 survived) over filter evaluation, cross-source resolution, scope decisions and restricted skipping.
- Gates on the copy: ruff check and format clean, pyright clean on the sources modules; no cross-package private import (ADR-1287).

## What holds

- The grammar matches the EBNF for every class of input tried: precedence parses as ruled, lowercase keywords only, `OR` and `Not` refused with their column, LF and CRLF as whitespace, a lone CR refused, `\"` and `\\` the only escapes, an unclosed `(` reported at its own column, line and column counted in characters across lines.
- Every scope and filter load refusal of section 14 fires with the source, the side and the keys or sides listed; the string `filter` form names the scope keys; the starter's worked example loads once uncommented.
- BUG-1284 is fixed: with an epics source and a stories source on one tracker, the ref appears on the second pull in either order, without the host issue changing, and a later pull heals an earlier-dropped link. Trailing-slash base URLs share the tracker.
- States: rejected-by-filter, outside-the-scope and gone read three different ways; an out-of-filter item is not read in detail again; an issue the filter accepts again, or a deleted issue restored, returns to `open`.
- Restricted content: a confidential issue's title, an internal note and a filter-rejected issue's title reach no squad file and no report text (grep of the squad after each pull).
- `restricted`, `filtered out` and `skipped (no type)` counts, and the two-type line, appear on every pull with no detail fetch for either.
- The suite grows by about 38 test functions, close to the 36 planned, all through the CLI on the recorded harness.

## Findings

Thirteen findings: eight medium, five low. The ranked list is in the findings table; each body has where, the reproduced scenario and the fix.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1292 add-finding "…" --severity medium`; track with `sq review 1292 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — An issue another source holds is read in detail on every pull

<!-- sq:finding:F1:body -->
**Where:** `src/squads/_services/_pull.py`, `PullMixin._fetch_one_source` builds `stored` and `linked` from the pulled source's own items only; `_fetch._triage` then treats an issue held by another source of the tracker as new.

**Reproduced:** sources `epics` (filter `epic`) and `stories` (filter `story`) on one GitLab project; issue #16 carries both labels. After `epics` creates FEAT-3 for it, every pull of `stories` requests `/projects/77/issues/16/notes` and `/links` before reporting `platform/api#16: held by FEAT-3 of source 'epics'`, on the second and every later pull too (request log). The same holds for a `group` source overlapping a `project` source: every issue of the project the group source selects and maps is read in detail by it on every pull, changed or not (driven: a `group = "platform"` source beside a `project = "platform/api"` source, unchanged tracker, the group pull requests `/issues/12/notes` and `/links`). When the second source maps such an issue to no type it is counted `skipped (no type)` although an item holds it.

ADR-1274 section 14 says a held issue costs its listing row only, and that the overlapping source "leaves it to that source"; `docs/sources.md` and the CHANGELOG `sq source pull` entry say only an issue to create or a changed one is read in detail. `test_a_source_leaves_an_issue_another_source_of_its_tracker_holds_and_says_so` asserts the line, not the requests, so it passes.

**Fix:** decide holding tracker-wide on the listing row: build the held set over every peer source (`SourcesSpec.peers`) in `_fetch_one_source`, and let `_triage` report `held by` from the row with no detail fetch and no count. Assert on the harness request log in the existing held-by case.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-04T15:39:21Z] `python-dev` Elias Python:
  - A source now reads in detail no issue another source of its tracker holds: the held set is built across the tracker's sources and the issue costs its listing row, reported held by (_fetch._triage, _pull).
- [2026-11-04T16:37:51Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven (epics/stories on one project, request log): the stories pull reads no notes or links of #16 and reports held by FEAT-3 of source epics, on every pull; a second pull of each source names no issue the other holds. Mutants: elsewhere check off fails the overlap case (detail_reads asserted); held-by before filter fails test_a_second_pull_of_two_split_sources_names_no_issue_the_other_holds.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Jira in-scope search breaks on a JQL ending in ORDER BY

<!-- sq:finding:F2:body -->
**Where:** `src/squads/_sources/_jira/_connector.py`, `JiraConnector.in_scope`: `f"id = {issue.id} AND ({self._filter()})"`.

**Reproduced:** a `jira@cloud-v3` source with `jql = "labels = squads ORDER BY created DESC"`. The pull works (the JQL is sent as written), and `sq task 2 show --refresh` sends `id = 10042 AND (labels = squads ORDER BY created DESC)` (request log). JQL takes `ORDER BY` only at the end of a query, never inside parentheses, so a real Jira rejects that search with HTTP 400 and `show --refresh` and `relink` fail on a scope the pull and the probes accept. The rejection itself is inferred from the JQL grammar; the harness accepts any JQL.

A JQL copied from a saved Jira filter usually ends with `ORDER BY`, so this is the common shape, not an edge.

**Fix:** split a trailing `ORDER BY` clause off the scope before wrapping it (it is irrelevant to an in-scope test), or refuse `ORDER BY` in `jql` at load with a message saying the pull orders nothing. Record the choice in ADR-1274 section 14 (the entry gives the query as `id = <id> AND (<jql>)`) and in docs/sources.md's Jira scope bullet. One connector case with an `ORDER BY` scope.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-04T15:48:39Z] `python-dev` Elias Python:
  - A jql with an ORDER BY clause outside a quoted string is refused at load; the JQL is sent as written (_loader).
- [2026-11-04T16:37:52Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: ORDER BY (any case, across a line break, at the very end) refused at load with the ADR message; order by inside double or single quotes, an escaped quote, border/byline all load. Mutants: check off, and check ignoring quotes, each fail the jql scope case.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — GitLab in-scope check is case-sensitive, GitLab paths are not

<!-- sq:finding:F3:body -->
**Where:** `src/squads/_sources/_gitlab/_connector.py`, `GitLabConnector.in_scope`: `path == self._scope.value` and `path.startswith(f"{self._scope.value}/")`.

**Reproduced:** a `project = "Platform/API"` source on a loopback GitLab that answers that path as GitLab does (paths resolve case-insensitively) and returns keys in their canonical case, `platform/api#12`. The pull creates TASK-2 `open`. `sq task 2 show --refresh` then reports `platform/api#12: out-of-filter (outside the scope); TASK-2 stays`, and the next pull sets it back to `open` (`refreshed 1`). A relink by key of such an issue links it `out-of-filter`. The same applies to a `group` written in another case.

GitHub's check ignores case; GitLab's does not, though GitLab namespaces and project paths are case-insensitive. The ADR entry says "equals" for GitLab, so the gap is in the decision as well.

**Fix:** compare GitLab paths case-insensitively (`casefold()` on both sides, for `project` equality and the `group/` prefix), and amend the section 14 single-issue bullet to say so. A case-insensitive GitHub-style test for GitLab in the existing refresh-outside-scope case.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-04T15:48:40Z] `python-dev` Elias Python:
  - The GitLab in-scope check compares the project path and the group/ prefix ignoring case (_gitlab/_connector).
- [2026-11-04T16:37:53Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: project Platform/API and group Platform both keep platform/api#12 and platform/sub/web#3 open on show --refresh and on the next pull (unchanged). Mutants: no folding, or folding the key only on one side, fail the another-case refresh test. Folding only the key side survives because the fixture key is already lowercase; not a gap given the tracker returns canonical keys.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Coverage probe ignores the filter and names unmapped issues

<!-- sq:finding:F4:body -->
**Where:** `src/squads/_sources/_tracker_probes.py`, `_coverage`, `_unmapped_types`, `_unknown_authors`, `_unmapped_labels`: they run over `self._listing()`, the whole scope.

**Reproduced:** source `epics` with `filter.labels = 'epic'` and `maps.types.labels.epic = "feature"`. `sq source check epics` warns `3 in-scope issue(s) map to no single type: platform/api#13, platform/api#15, platform/api#17` (two of them rejected by the filter, one intentionally unmapped) and lists the keys of filter-rejected issues among an author's issues. On a source scoped to a whole project and filtered to a few labels, the warning names every other issue of the project on every run.

Ruling ec3c412 makes leaving a value out of the map the way to leave issues out ("counted, not reported on every pull"), and section 14 says a rejected issue is never named. The coverage probe contradicts both: the intended setup can never reach the coverage pass line, and `sq source check` names what the pull is careful not to.

**Fix:** run the coverage probes over the selected issues (those `Expected.filter` accepts), and turn the no-type warning into a count without keys, or drop it, since `skipped (no type)` already reports it. Update docs/sources.md's coverage description. Adjust the existing coverage case rather than adding one.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-04T15:39:22Z] `python-dev` Elias Python:
  - The coverage probes run over the filter-selected issues; issues with no type are counted, several-type ones named (_tracker_probes._coverage).
- [2026-11-04T15:48:44Z] `python-dev` Elias Python:
  - Adjusted per the manager decision: source check counts selected issues mapping to no type on the coverage pass line (informational, not a warning); several types stays a warning (_tracker_probes._coverage).
- [2026-11-04T16:37:54Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d with the manager adjustment. Driven: coverage names no filter-rejected issue; selected issues with no type are a pass-line count (on its own pass line when another coverage line warns); a two-type issue is a warning naming it. Mutant: probes over the whole listing fails test_the_coverage_probes_read_only_the_issues_the_filter_selects. Note, not a defect: the author warning still names a selected issue that maps to no type.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A link to a restricted issue is named on every report

<!-- sq:finding:F5:body -->
**Where:** `src/squads/_services/_pull.py`, `Compiler.links` (the `unheld` line); `src/squads/_sources/_gitlab/_connector.py`, `links()` keeps every link record.

**Reproduced:** issue #12 links `blocks` to #14, a confidential issue. The pull counts #14 `restricted 1` and creates nothing for it, then prints `platform/api#12: 2 link(s) not followed, no item holds platform/api#13, platform/api#14`, and repeats the key of the confidential issue each time #12 changes, since no item can ever hold it. The report thereby names a restricted issue, and the line's promise (docs: "The ref is made when that issue is pulled"; CHANGELOG: "makes its ref when that issue is pulled") is false for it. Jira links to an issue under a security level behave the same way. Only the key leaks, not the title (checked: no title or note text of #14 reaches any squad file).

**Fix:** GitLab's link record carries `confidential`; drop such a link in the connector as the listing drops the issue (optionally counted with `restricted`). Jira's link record does not carry the security level, so either accept that and say in docs/sources.md that a link to an issue the tracker restricts is reported as not followed, or leave restricted targets out of the line where the connector can tell. Pin it with one case on the GitLab fixture.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-04T15:48:41Z] `python-dev` Elias Python:
  - The GitLab connector drops a link whose record is confidential: no ref, no line, no count; Jira keeps the key-only line.
- [2026-11-04T16:37:55Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: #12 blocks #13 and confidential #14; the report names only #13, nothing of #14 reaches the squad (grep). Mutant: confidential drop off fails test_a_link_to_a_confidential_issue_makes_no_ref_and_no_line. Jira limit documented as ruled.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Filter precedence, or, not-scope and escapes are untested

<!-- sq:finding:F6:body -->
**Where:** `src/squads/_sources/_filter.py` (`Disjunction.matches`, `_Parser._disjunction`/`_conjunction`/`_negation`, `_Lexer._quoted`); the filter cases in `tests/cli/test_source_pull.py` and `tests/cli/test_source_scope.py`.

**Reproduced (mutation, on a copy):** each of these mutants passes all 122 source tests:

- `Disjunction.matches` evaluating `all` instead of `any` (an `or` behaves as `and`);
- `and` and `or` swapped in the parser, so `or` binds tighter than `and` (`a or b and not c` reads `(a or b) and not c`);
- `not` taking a whole disjunction (`not a or b` reads `not (a or b)`);
- a quoted escape kept with its backslash (`"x\"y"` matches the label `x\"y`).

The pull tests evaluate only `squads and not bug`, a single-value side and `incident`; the parser tests check refusals and that a valid expression loads, never what it means. The precedence ruled in ec3c412 and written into `docs/stability.md` as stable is therefore not pinned by any behaviour.

**Fix:** one pull case whose expression exercises precedence and `or` together, e.g. `labels = 'a or b and not c'` over issues chosen so the ruled reading and each wrong reading create different items, plus a quoted value with an escape that matches a label holding `"`. One case, not a table.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-04T16:02:29Z] `python-dev` Elias Python:
  - Pinned by test_a_filter_reads_not_before_and_and_and_before_or and test_a_quoted_filter_value_takes_an_escaped_quote_and_backslash_as_one_character (test_source_pull); each of the four mutants (or as and, precedence swapped, not over a disjunction, escapes kept) now fails them.
- [2026-11-04T16:38:07Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Re-applied the four mutants on a worktree (161 source tests): or as all, and/or precedence swapped, not over a disjunction each fail test_a_filter_reads_not_before_and_and_and_before_or; escape kept with its backslash fails the escaped-quote test.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Cross-source and scope decisions leave mutants alive

<!-- sq:finding:F7:body -->
**Where:** `tests/cli/test_source_links.py`, `tests/cli/test_source_pull.py`; the code paths `Compiler.other_holder` (`created_before`), `GitLabConnector.in_scope` (group), `GitHubConnector.in_scope`, `relink_item` (outside the scope), `unlink_item` (`closed`).

**Reproduced (mutation, on a copy):** each mutant passes all 122 source tests:

- `other_holder` ignoring `created_before`: in one unnamed pull of two overlapping sources neither of which holds an issue yet, both create an item for it, the duplicate the one-holder rule exists to prevent;
- GitLab `in_scope` for a `group` comparing the path for equality (every subgroup issue then reads outside the scope on `show --refresh`);
- GitHub `in_scope` returning `True` (the GitHub scope decision is untested);
- relink deciding acceptance without `fetch.changed` (an issue outside the scope relinked `open` instead of `out-of-filter`; only the filter-rejected relink is tested);
- the unlink warning shown for `open` only, not `closed`.

**Fix:** pin each by extending an existing case rather than adding modules: the overlap case also runs one unnamed pull on a fresh squad and asserts one item; the refresh-outside-scope case gets a group-scoped variant with a subgroup key; the Jira relink case's sibling for GitHub; the relink-out-of-filter case also relinks an issue outside the scope; the unlink-warning case uses a closed issue.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-04T16:02:30Z] `python-dev` Elias Python:
  - Pinned in test_source_links (one unnamed pull of overlapping sources, group-scope refresh, relink outside the scope, unlink of a closed issue) and test_source_connectors (GitHub refresh in another repository); the five mutants named all fail a new test.
- [2026-11-04T16:38:08Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Re-applied the five mutants: other_holder ignoring created_before, GitLab group compared by equality, GitHub in_scope True, relink accepting without fetch.changed, unlink warning for open only; each fails its new case (one unnamed pull of overlapping sources, group-scope refresh, GitHub moved repository, relink outside the scope, unlink warning).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Internal-note test cannot fail; Jira by-ID restriction untested

<!-- sq:finding:F8:body -->
**Where:** `tests/cli/test_source_pull.py`, `test_an_internal_note_is_not_imported_as_a_comment`; the Jira by-ID restricted path in `src/squads/_sources/_jira/_connector.py`, `_issue_by`.

**Reproduced (mutation, on a copy):**

- Removing `or record.get("internal")` from the GitLab note filter passes every source test. The test builds its internal note as `{**notes[0], "internal": True}`, and `notes[0]` of issue 12 in `gitlab/routes.json` is a system note (`system: true`), so the copy is skipped as a system note whatever the internal rule does. The test cannot fail.
- Letting `_issue_by` ignore `fields.security` (a held Jira issue that gains a security level is returned by ID instead of reading `gone`) passes every source test; only the listing path is pinned.

The behaviour itself is right: driven on the dev build, an internal non-system note on GitLab is not imported.

**Fix:** build the internal note from a human note (`notes[1]`, or set `system: False` explicitly); add the by-ID case to the existing Jira security-level case (the held issue gains a security level on its by-ID route and reads `gone`).
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-11-04T16:02:30Z] `python-dev` Elias Python:
  - The internal note is now built from the human note with system false, and a Jira refresh of an issue that gains a security level reads gone; both mutants fail their tests.
- [2026-11-04T16:38:09Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Re-applied: internal rule removed fails test_an_internal_note_is_not_imported_as_a_comment (note now built from a human note); Jira by-ID ignoring security fails the refresh-gains-a-security-level case.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Unnamed pull reports a link not followed that it then makes

<!-- sq:finding:F9:body -->
**Where:** `src/squads/_services/_pull.py`, `Compiler.links` (the `not followed` line), with `_compile_and_apply` compiling the sources of an unnamed pull one after the other.

**Reproduced:** the BUG-1284 setup (`epics` and `stories` on one project, #12 `blocks` #13), fresh squad, one `sq source pull` with no name. The report reads `epics: … platform/api#12: 2 link(s) not followed, no item holds platform/api#13, …`, while the same pull creates TASK-4 for #13 under `stories` and writes `refs: TASK-4 (blocks)` on FEAT-2. Same with a project source and a group source. The line is false in the pull that prints it.

**Fix:** decide the `not followed` lines after every source of the pull has compiled (collect the unheld targets per host, then drop those any later compile created), or word the line so it does not claim the link was dropped. Add the assertion to the either-order case's unnamed variant.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-11-04T15:39:23Z] `python-dev` Elias Python:
  - Not-followed lines are decided after every source of the pull compiled, dropping targets a later source created (_pull._report_unfollowed).
- [2026-11-04T16:38:10Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: one unnamed pull on a fresh squad prints no not-followed line for #13 and FEAT-2 carries refs TASK-4 (blocks); #16 gets one item. Mutant: report decided per source fails test_an_unnamed_pull_reports_no_link_unfollowed_that_a_later_source_makes.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Deep nesting or long CRLF runs crash the parser

<!-- sq:finding:F10:body -->
**Where:** `src/squads/_sources/_filter.py`: `_Parser` recurses per `(` and per `not`, and `_Lexer._skip_blanks` recurses once per CRLF.

**Reproduced:** `sq source list` and `sq check` on a `sources.toml` whose filter holds 1,200 `not `, 600 nested parentheses, or 1,500 CRLF line breaks in a row: each crashes with a Rich traceback ending in `RecursionError: maximum recursion depth exceeded`. `sq check` should report `sources_loads` instead. About 250 nested parentheses are enough.

The input is the adopter's own file, so this is robustness, not exposure.

**Fix:** make `_skip_blanks` a loop, and either cap nesting (refuse past a depth such as 64 with a `FilterSyntaxError` at the offending column) or catch `RecursionError` in `parse_expression` and raise a `FilterSyntaxError`.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-04T15:39:24Z] `python-dev` Elias Python:
  - Nesting of not and parentheses is refused past 64 with line and column, and blank skipping is a loop (_filter).
- [2026-11-04T16:38:11Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: 1200 not, 600 parentheses and 64+1 mixed nesting refused with line and column; exactly 64 loads; 1500 CRLF loads; sq check reports sources_loads, no traceback. Mutant: depth check off fails the two nesting cases.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Quoted values refuse non-control characters like NBSP

<!-- sq:finding:F11:body -->
**Where:** `src/squads/_sources/_filter.py`, `_Lexer._quoted` (`not char.isprintable()`) and `_Lexer._next`'s message.

**Reproduced:** through `sq source list`, `labels = "\"a b\""` (a no-break space) and `"\"a​b\""` (a zero-width space) are refused with `a control character or line break inside a quoted value`. Neither is a control character. `str.isprintable()` is false for every separator but the space and for format characters, so these labels cannot be matched at all. Outside quotes, `U+0000` or `U+202E` gets the advice `quote the value`, which the quoted form then refuses too.

`docs/stability.md` and ADR-1274's EBNF promise any character but `"`, `\` or a control character inside quotes. Refusing format characters (bidirectional overrides) may well be wanted, but then the grammar and the message should say so.

**Fix:** test `unicodedata.category(char) == "Cc"` for the control rule, or keep the stricter rule and amend the ADR, `docs/stability.md` and `docs/sources.md` together, with a message naming what is refused. Give the outside-quotes message for a control or format character no "quote the value" advice.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-11-04T15:48:42Z] `python-dev` Elias Python:
  - Quoted values refuse only Unicode Cc and unescaped quote or backslash; outside quotes a control character gets no quote advice (_filter).
- [2026-11-04T16:38:12Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: inside quotes NBSP, ZWSP, U+202E and U+2028 load; BEL, NEL and LF refused. Outside quotes NBSP and U+202E get quote advice, U+0000 and U+0085 do not. Mutant: isprintable rule back fails test_a_quoted_value_takes_any_character_but_a_control_one.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Scope values are not shape-checked at load

<!-- sq:finding:F12:body -->
**Where:** `src/squads/_sources/_loader.py`, `_scope_of` (only non-empty is checked); `src/squads/_sources/_github/_connector.py` builds the listing path with `quote(scope.value, safe="/")`.

**Reproduced:** `repository = "acme/../../orgs/acme"` loads, and `sq source check` sends `GET /api/v3/repos/acme/../../orgs/acme/issues` (request log). A server that normalises the path serves `/api/v3/orgs/acme/issues`, the organisation listing that ruling ec3c412 keeps out until verified live (inferred; the harness does not normalise). `repository = "acme"` or a value with spaces loads too, and `in_scope` can then never match, so every `show --refresh` reads `out-of-filter`.

**Fix:** check each scope's shape at load: `repository` exactly `owner/repo` of `[\w.-]` segments with no `.` or `..` segment; GitLab `project` and `group` as slash-separated path segments with no empty, `.` or `..` segment. Refuse otherwise naming the expected shape. Extend the existing scope refusal case.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-11-04T15:48:43Z] `python-dev` Elias Python:
  - Scope values are shape-checked at load by key, naming the source, key and shape (_loader._scope_value_problem).
- [2026-11-04T16:38:13Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: acme/../../orgs/acme, acme, acme/api/x, spaces, leading/trailing/doubled slash, a dot segment, non-ASCII, a one-segment project all refused naming key and shape; acme/api, Acme-1/my.repo_x, a/b/c/d, one-segment group load. Mutants: shape check off and dot segments allowed each fail the shape case.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Report and check wording out of step with the new model

<!-- sq:finding:F13:body -->
**Where and reproduced:**

- `src/squads/_services/_source_checks.py`: `sq check` reports an `out-of-filter` item as `the tracker no longer lists platform/api#12 (out-of-filter)`. Under a full listing, an issue rejected by the filter is still listed; only "outside the scope" fits.
- `src/squads/_services/_fetch.py`, `fetch_referenced_issue`: `sq feature 3 source relink epics gid://gitlab/Issue/9005` for an issue the scope no longer lists answers `source 'epics' has no issue 'gid://…' that its credential can read`. The credential can read it; GitLab resolves an immutable ID only through the scope listing (section 14). Say so and name the key form.
- `src/squads/_services/_fetch.py`, `_triage`: the two-type line prints a Python list, `(['feature', 'task'])`, also quoted in docs/sources.md and the CHANGELOG.
- `src/squads/_services/_source_links.py`: relink of an issue another source's item holds says `already held by TASK-4` without the holder's source, while the pull's line names it (`held by FEAT-3 of source 'epics'`).

**Fix:** reword each (`is out-of-filter: the filter rejects it or it left the scope`; `… is not in the scope's listing; relink it by its key`; `maps to several types: feature, task`; `already held by TASK-4 of source 'stories'`), and update the quoted lines in docs/sources.md and the CHANGELOG.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-11-04T15:48:44Z] `python-dev` Elias Python:
  - Reworded the out-of-filter check message, the GitLab ID relink refusal, the two-type line and the relink holder's source.
- [2026-11-04T16:38:14Z] `reviewer` Paul Reviewer:
  - Verified at cfe5833d. Driven: sq check says platform/api#16 is out-of-filter: the filter rejects it or it left the scope; relink by an unlisted GitLab ID names the key form (a missing key keeps the credential message); relink of #16 names FEAT-3 of source epics; the two-type line reads feature, task. Mutants on the relink holder and GitLab ID messages fail their tests.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Docs say a held issue is never read; an unnamed first pull reads it twice

<!-- sq:finding:F14:body -->
**Where:** `docs/sources.md` (The pull: "An issue an item of another source of the tracker holds costs only its listing row: it is never read in detail"; Links across sources, One holder: "It decides this on the listing row and reads nothing more of the issue", followed by the in-this-pull form of the line) and the CHANGELOG `sq source pull` and links entries ("reads nothing of it beyond its listing row"). Code: `PullMixin.pull_sources` fetches every source before any compiles, so `_fetch_one_source` builds `elsewhere` from the items the squad held when the pull started.

**Reproduced:** epics and stories on one GitLab project, #16 labelled both, fresh squad, one `sq source pull` with no name. The request log shows `/projects/77/issues/16/notes` and `/links` read twice, once by each source; the stories line then says `platform/api#16: held by the item source 'epics' creates in this pull`. The docs put that line right after "reads nothing more of the issue", so the reader takes it to cost the listing row too. It costs one detail read per overlapping issue, on the first pull that creates it only; later pulls read nothing (driven).

**Fix:** either word the docs and CHANGELOG to say the rule holds for an issue an item holds when the pull starts (an issue an earlier source of the same pull creates is read by both), or, since sources are fetched one after the other, add the IDs an earlier peer source of the pull wants and maps to one type to the later sources' `elsewhere`. The wording is the smaller change.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-11-04T16:39:36Z] `tech-writer` Theo Writer:
  - Reworded docs/sources.md (The pull; One holder per issue) and both CHANGELOG entries: an issue another source already holds costs only its listing row; within the pull that first creates it, every source that selects it reads it.
- [2026-11-04T16:45:43Z] `manager` Catherine Manager:
  - Verified: docs/sources.md and the CHANGELOG now say an issue already held as the pull starts costs only its listing row, and that every source selecting it reads it within the pull that first creates it.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T15:31:02Z] `reviewer` Paul Reviewer:
  - - Batch review of TASK-1286 done: 13 findings, 8 medium and 5 low, no high. Verdict: changes requested. BUG-1284 is fixed in both pull orders and heals on a later pull; the grammar, the load refusals, the three held states and restricted-content handling hold under probing.
    - Behaviour to fix first: F1 (a source re-reads in detail every issue another source of its tracker holds, on every pull), F2 (Jira single-issue search breaks on a JQL ending in ORDER BY), F3 (GitLab in-scope check is case-sensitive, so show --refresh and the pull flip-flop), F4 (the coverage probe ignores the filter and names every unmapped issue), F5 (a link to a restricted issue is named on every report).
    - Tests: F6 to F8 are mutants that survive the source suite (filter precedence and `or`, one holder within an unnamed pull, the group and GitHub scope checks, the internal-note test, which cannot fail). F9 to F13 are low: a false not-followed line in an unnamed pull, parser recursion, quoted non-control characters, scope shapes, wording.
    - F2, F3 and F11 also need a line in ADR-1274 section 14 (@architect). @tech-lead please route the fixes to @python-dev; docs and CHANGELOG lines quoted in F1, F5 and F13 follow the fix (@tech-writer).
- [2026-11-04T15:34:34Z] `architect` Robert Architect:
  - @python-dev ADR-1274 §14 now rules F2, F3, F5, F11 and F12 (entry **Scope values, quoted characters and restricted link targets**):
    - F2: refuse a `jql` holding the words `order` `by` (any case) outside a JQL quoted string at load, saying the pull lists the scope in no order; no stripping.
    - F3: GitLab `in_scope` compares `project` and the `group/` prefix ignoring ASCII case.
    - F11: inside quotes refuse only category Cc (plus unescaped `"`/`\`); outside quotes, "quote the value" advice for anything a quoted value accepts, none for a control character.
    - F5: drop a GitLab link whose record is `confidential` in the connector (no ref, no line, no count); Jira stays as is, documented as a limit.
    - F12: shape-check scope values at load (segments `[A-Za-z0-9_.-]+`, not `.`/`..`; GitLab `project` 2+, `group` 1+, GitHub `repository` exactly 2; no empty/leading/trailing `/`, no whitespace), naming source, key and shape.
    @tech-writer the docs owed are listed at the end of the entry.
- [2026-11-04T16:08:05Z] `tech-writer` Theo Writer:
  - Docs brought to the scoped-sources fixes (docs/sources.md, docs/stability.md, CHANGELOG 0.20.0); every quoted message checked against src/ and the tests.
    
    - Held issues: an issue another source of the tracker holds costs only its listing row, falls in no count and gets a `held by` line; the in-this-pull form (`held by the item source 'X' creates in this pull`) is documented.
    - `sq source check` coverage reads only filter-selected issues and never names a rejected one; no-type issues are an informational count on the pass line (`2 selected issue(s) map to no type and are skipped by the pull`), several types a warning (`platform/api#12 maps to several types: bug, task`).
    - Links: not-followed lines are decided after every source of the pull; a GitLab link to a confidential issue makes no ref, line or count; the Jira security-level limit (named by key only) is in Restricted issues, Links across sources and the Jira bullet.
    - Filter: nesting limit of 64 with its message; inside quotes only Cc and unescaped `"`/`\` are refused (NBSP, zero-width, bidi controls stand for themselves); outside quotes the control-character message has no quote advice. The stability.md EBNF defines a control character as Cc.
    - Scope: per-key path shapes and the load message, `jql` with ORDER BY refused at load (otherwise sent as written, replacing "squads does not read the JQL"), GitLab paths compared ignoring ASCII case. Same in the stability.md sources.toml grammar.
    - Reworded lines quoted: sq check out-of-filter, relink by GitLab ID, relink holder with its source, the two-type and two-value pull lines (comma-joined).
    
    Gates: tests/meta 748 passed; sq check clean.
    
    Open point for @tech-lead: `_fetch._triage` checks "held elsewhere" before the filter, so in an epics/stories split each pull of one source names every issue the other holds, even the ones its own filter rejects (read, not driven). The docs describe the line without promising it is limited to selected issues.
- [2026-11-04T16:11:07Z] `python-dev` Elias Python:
  - - Fixed the `held by` noise. `_fetch._triage` now applies the source's own filter first: an issue it rejects is counted as filtered out whether or not another source holds it, and the `held by` line is only for selected issues. Test: `test_a_second_pull_of_two_split_sources_names_no_issue_the_other_holds` (epics/stories split, second pull of each); it failed before the fix with `platform/api#13: held by TASK-3 of source 'stories'`.
    - Scaffold (`sq override scaffold sources`) wording changed. Scope bullet now adds: "Paths are segments of ASCII letters, digits and `_-.` joined by `/`: `group/subgroup/project` (gitlab `project`, two or more segments; `group`, one or more) and `owner/repo` (github). A `jql` takes no `ORDER BY`: the pull lists the scope in no order." Filter bullet now adds: "a quoted value refuses only control characters and an unescaped `"` or `\`."
    - Gates: pyright, ruff check, ruff format clean; pytest source/check/meta 1036 passed; sq check clean.
- [2026-11-04T16:38:36Z] `reviewer` Paul Reviewer:
  - Fix verification at cfe5833d: F1 to F13 Verified. Each finding re-driven on scratch squads against the loopback tracker (request logs, messages); the 11 mutants that survived before (F6 to F8) now each fail a test, and a mutant per fix (F1 to F5, F9 to F13 and the held-by order) fails too. Gates: ruff and pyright clean on the sources and services packages.
  - One new low finding, F14: the docs and CHANGELOG say an issue another source holds is never read in detail, but in one unnamed first pull an issue an earlier source creates is read by both sources. A wording fix closes it.
  - @manager I recommend approving once F14 is ruled (fixed or WontFix); nothing else blocks. @tech-writer F14 is likely yours.
- [2026-11-04T16:45:44Z] `manager` Catherine Manager:
  - Approved: F1-F14 Verified; full suite 2200 passed.
<!-- sq:discussion:end -->
