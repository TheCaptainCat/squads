---
id: TASK-1286
sequence_id: 1286
type: task
title: Scoped sources, filter expressions and cross-source links
status: Done
parent: FEAT-1285
author: tech-lead
assignee: python-dev
refs:
- ADR-1274:implements
- BUG-1284:fixes
description: Scope keys, a filter evaluated in squads, pull report counts, restricted
  issues, links across a tracker's sources
subentities:
- local_id: ST1
  title: Scope keys and the filter expression parser
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: Restricted issues skipped and counted
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST3
  title: Filter on the listing and the pull report counts
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: Single-issue commands decide scope and filter
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST5
  title: Links carry their inverse type
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST6
  title: Links and holders resolve across one tracker
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST7
  title: Probes read the scope and the filter values
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST8
  title: Docs and changelog for scoped sources
  status: Done
  assignee: tech-writer
  maps_to: US4
created_at: '2026-11-04T09:58:37Z'
updated_at: '2026-11-04T16:45:44Z'
priority: high
---
<!-- sq:body -->
## Goal

Replace the single-label source filter with a required scope on the tracker and an optional filter expression evaluated in squads, report what the pull did not turn into items, skip restricted issues, and resolve links across every source of one tracker (FEAT-1285 US1 to US4; fixes BUG-1284).

## Design

ADR-1274 section 14, the 2026-11-04 entries **Source selection**, **States under a full listing**, **What becomes an item**, **Links across sources**, **Probes** and **No migration**, plus the earlier section 14 entries they amend (**The pull diffs the listing**, **Connector decisions for GitHub and Jira**, **Unlink and relink**, **Two items holding one issue**, **Reference translation**). Rulings f6cbdfc, ec3c412 and af70274 (op-pierre) on the decision's discussion are settled; do not reopen them.

## Order and checkpoints

The subtasks run in order, one fresh developer each. Each one leaves the full gate green (pyright, ruff check and format with `--all-extras`, `tests/meta`, the source tests, `sq check`), so the next developer starts from a working tree. A subtask that changes a surface migrates every existing test and fixture that surface touches in the same pass. The documentation subtask is last and belongs to the technical writer.

## Layers and expected files

- `src/squads/_sources/`: `_spec.py`, `_loader.py`, `_registry.py`, `_connector.py`, `_gitlab.py`, `_github.py`, `_jira.py`, `_jira_cloud.py`, `_jira_dc.py`, the probe modules (`_probes.py`, `_tracker_probes.py`, `_gitlab_probes.py`, `_github_probes.py`, `_jira_probes.py`), new `_filter.py`.
- `src/squads/_services/`: `_fetch.py`, `_pull.py`, `_source_links.py`, `_source_checks.py`, `_sources_ops.py`, `_source_view.py`, `_comment_view.py`.
- `src/squads/_api/_dto/_sources.py` (the pull report), the CLI renderer of the pull report.
- `src/squads/_specs/sources.toml`, the `sq override scaffold sources` starter in `src/squads/_overrides/_service.py`.
- `tests/fixtures/sources/*/routes.json`, `tests/cli/test_source*.py`, `tests/check/test_source_rules.py`.

## Tests (about 36 new, net of the cases replaced)

CLI surface cases on the recorded loopback harness, per the test-design rule (ADR-1172): one case per behaviour plus its boundary refusals, no shape tables or cross products. The expected count is in each subtask. A behaviour no surface shows yet is tested in the subtask where it becomes visible.

## Conventions

- Code comments and docstrings: one or two sentences, present truth, no release versions, no history.
- No ticket IDs (FEAT, BUG, TASK, ADR numbers) in code, comments, test names or fixture names; name tests by behaviour.
- No schema change and no migration step (section 14, **No migration**).

## CHANGELOG

Owed by the documentation subtask; each developer subtask reports its user-visible changes on its own discussion for the technical writer.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1286 add-subtask "<title>"`; track with `sq task 1286 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Scope keys and the filter expression parser

<!-- sq:subtask:ST1:body -->
Size: L.

## Scope

- `_registry.py`: each `ConnectorEntry` declares its scope keys beside its sides: gitlab@v4 `project` and `group`, github@v3 `repository`, both Jira versions `jql`.
- `_spec.py`: `SourceSpec` drops the string `filter`, carries the one scope (key and value) and the parsed filter (side to expression), empty when absent.
- New `_filter.py`: the tokenizer and parser of the section 14 EBNF (`not` tightest, then `and`, then `or`, left-grouping; bare words ASCII-only; quoted values with only `\"` and `\\` escapes; LF and CRLF as whitespace; lowercase keywords only, another case refused) and the evaluation of an expression against the values of one side. Parse errors carry a 1-based line and column counted in characters; an unclosed `(` is reported at its own column.
- `_loader.py` refusals, each naming the source and, for the filter, the side (`sources.<name>.filter.<side>`): no scope key, two, an empty value, another connector's scope key (an unknown key), listing the keys the version takes; `filter` not a table, an empty table, a side value not a string, a side the version does not have (listing its sides), an empty or whitespace-only expression, every malformed-expression class of section 14 **Refusals at load**. A string `filter` (the development-build form) fails saying `filter` is a table and naming the version's scope keys.
- Connectors take the scope instead of `source_filter` and list the whole scope, every state, with no tracker-side condition: GitLab `/projects/<url-encoded path>/issues` or `/groups/<url-encoded path>/issues`, GitHub `/repos/<owner>/<repo>/issues` (pull requests still skipped), Jira the version's JQL search with the `jql` value. `_fetch.connector_for` passes the scope.
- The probes keep working on the scope with the least change (the "filter readable" probe reads the scope); their full rework is the probes subtask.
- `src/squads/_specs/sources.toml` and the scaffold starter in `_overrides/_service.py`: no label filter anywhere; the starter's worked example declares a scope key and a commented filter table, and loads.
- Fixtures and tests: every `routes.json` listing route moves to its scope endpoint; every test `sources.toml` declares a scope key instead of `filter`.
- The filter loads and is validated here; the pull applies it in the filter subtask. A source with no filter selects every issue of its scope.

## Acceptance

- A source with zero or two scope keys, or a string `filter`, is refused at load with the message above; `sq check` reports the sources document as not loading.
- A malformed expression is refused with its line and column; a multi-line TOML literal-string expression loads.
- `grep -rn 'source_filter\|filter = "' src/squads tests/fixtures` finds no label filter.
- Full gate green; the existing source tests pass on the migrated fixtures.

## Tests (about 8 new)

Through `sq source list` loading the document: scope key missing, two scope keys, a foreign scope key, the string `filter` form; a filter side the version lacks; a valid multi-line expression loads; malformed expressions grouped by class (lexical, syntax, parenthesis) with their positions. The scaffold test asserts the starter loads.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Restricted issues skipped and counted

<!-- sq:subtask:ST2:body -->
Size: M.

## Scope

- GitLab: an issue with `confidential: true` is treated as not returned by the listing, the single-issue fetch and the lookup; a note with `internal: true` is skipped like a restricted Jira comment.
- Jira (both versions): an issue carrying a security level (`fields.security` set) is treated as not returned, everywhere the connector returns issues. The existing restricted-comment rules stay.
- GitHub: no change (no per-issue restriction).
- No source key pulls restricted issues; there is no opt-out.
- The connector's listing result (`SourceFetch` in `_connector.py`) counts the restricted issues it dropped, and the pull report carries the count: a `restricted` field on `SourcePullReport` in `src/squads/_api/_dto/_sources.py` and `restricted <n>` on the source's line when non-zero.
- An item whose issue becomes restricted reads as `gone`, is reported and stays (the existing gone path).
- Fixtures: add a confidential issue and an internal note to `tests/fixtures/sources/gitlab/routes.json`, a security-level issue to both Jira route files.

## Acceptance

- A pull over a scope holding a confidential GitLab issue, or a Jira issue with a security level, creates no item for it and its line says `restricted 1`; `--json` carries `restricted: 1`.
- An internal GitLab note is not imported as a comment.
- A held issue that becomes restricted is reported `gone` and its item stays.
- Full gate green.

## Tests (about 4 new)

In `tests/cli/test_source_pull.py` or `test_source_comments.py`: GitLab confidential issue skipped and counted; GitLab internal note skipped; Jira security-level issue skipped and counted; held issue turned restricted reads gone.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Filter on the listing and the pull report counts

<!-- sq:subtask:ST3:body -->
Size: L.

## Scope

- `_fetch.py` / `_pull.py`: the parsed filter is evaluated on each listing row; the sides it names are ANDed. A listed issue the filter rejects and no item holds is ignored, never written, logged or named, and counted.
- The state compared and stored for a listed issue is the one the pull would write: the tracker's `open` or `closed` when accepted, `out-of-filter` when rejected (section 14, **States under a full listing**). An out-of-filter item is not refetched on every pull, and one the filter accepts again is.
- Held and rejected: `out-of-filter`, refreshed like any held issue. Held and not listed: fetched once by ID, `out-of-filter` when returned, `gone` when not. The report line says which way out ("rejected by the filter", "outside the scope"), decided at pull time and never stored.
- The type decision moves to the listing row, before any detail fetch: a selected issue mapping to no type is counted, one mapping to two different types is named on one line with the values found, on every pull (ruling af70274). Neither costs a detail fetch.
- `SourcePullReport`: `filtered_out` and `skipped_no_type` counts; the renderer prints `filtered out <n>` and `skipped <n> (no type)` on the source's line when non-zero. The per-issue line for an unmapped issue is replaced by the count.

## Acceptance

- With `filter.labels = 'a and not b'`, only issues carrying `a` and not `b` become items; the others are counted `filtered out`; `--json` carries the counts.
- A held issue whose labels the filter now rejects reads `out-of-filter` with "rejected by the filter"; a held issue missing from the scope listing but returned by ID reads `out-of-filter` with "outside the scope"; one not returned reads `gone`. The two reasons and `gone` read differently on the report.
- A second pull with nothing changed fetches no detail for out-of-filter items (assert on the harness request log).
- An issue mapping to no type is counted, never named; one mapping to two types is named with its values; neither triggers a detail fetch.
- Full gate green.

## Tests (about 7 new)

In `tests/cli/test_source_pull.py`: filter selects and counts; two sides ANDed; rejected held issue out-of-filter; left the scope out-of-filter vs gone; unchanged out-of-filter not refetched; no-type count with no detail fetch; two-type issue named. Replace the existing per-issue unmapped-type case rather than adding beside it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Single-issue commands decide scope and filter

<!-- sq:subtask:ST4:body -->
Size: M.

## Scope

- `_connector.py`: a connector method saying whether one issue is in the source's scope without listing it: GitLab from its key (project path equals `project`, or starts with `<group>/`), GitHub from its key (repository equals `repository`, ignoring case), Jira with one search `id = <id> AND (<jql>)`. Implemented in `_gitlab.py`, `_github.py`, `_jira.py`.
- `_fetch.py`: the single-issue fetch (`fetch_issue`, used by `show --refresh` and `relink`) decides selection from that method and the filter evaluated on the issue, and never lists the whole scope.
- `_source_links.py`: `show --refresh` and `relink` apply the resulting state (`open`/`closed`, `out-of-filter`, `gone`) as a pull would. The unlink warning names the scope and the filter: an issue still in the scope and accepted by the filter is imported again by the next pull, and the remedy names both levers.
- Relink by immutable ID on GitLab still resolves only an issue the scope lists (section 14, **GitLab fetches one issue by project path and number**); relink by key uses the in-scope check.
- Fixtures: the Jira search route for the in-scope query, in both Jira route files.

## Acceptance

- `show --refresh` on an item whose issue the filter now rejects sets `out-of-filter`; on one whose issue moved outside the scope sets `out-of-filter`; neither command requests the scope listing (assert on the harness request log), except GitLab relink by immutable ID.
- `relink` of an issue outside the scope, or rejected by the filter, links it with state `out-of-filter`.
- The unlink warning reads in terms of scope and filter.
- Full gate green.

## Tests (about 4 new)

In `tests/cli/test_source_links.py`: refresh with the filter rejecting; refresh with the issue outside the scope (GitLab key); Jira in-scope search used by relink; the existing unlink-warning case updated in place.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Links carry their inverse type

<!-- sq:subtask:ST5:body -->
Size: M.

## Scope

- `_connector.py`: `Link` carries the link type as read from the host and its inverse, as read from the other end.
- Connectors fill the inverse: GitLab fixed (`blocks` and `is_blocked_by`, `relates_to` both ways), GitHub fixed (`blocking` and `blocked_by`), Jira from the link type's `outward` and `inward` phrases. Every connector returns a link on both of its issues.
- `_pull.py`, `Compiler.links()`: host to target from `maps.links[type]`, target to host from `maps.links[inverse]`, each only when mapped, so a link gives the same refs whichever end is read. `has_ref` keeps a ref made from both ends single. Lookups stay within the host source here; the cross-source subtask widens them.
- Fixtures: record each fixture link on both of its issues in every `routes.json`.

## Acceptance

- Within one source, pulling only the target end of a `blocks` link (the host issue already held and unchanged) makes the ref on the host's item.
- A Jira `is blocked by` read from the inward side with the default `blocks = "blocks"` makes the ref from the outward issue's item.
- Reading a link from both ends yields one ref, not two.
- An unmapped link type makes no ref and no line.
- Full gate green.

## Tests (about 3 new)

In `tests/cli/test_source_pull.py` (or the links module): the ref made from the target end on GitLab; the Jira inward phrase; both ends read once.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Links and holders resolve across one tracker

<!-- sq:subtask:ST6:body -->
Size: L.

## Scope

- One tracker: two sources are on the same tracker when their normalised base URLs are equal (`normalise_base_url` in `_sources/_credentials.py`, the credential store key). Build the union of `(name, id)` and `(name, key)` lookups over every declared source on the host source's tracker when a command compiles, from `sources.toml`; nothing is stored. An item whose source is not declared matches nothing.
- `_pull.py`, `Compiler`: link targets, items created earlier in the same run and the new-issue decision use the tracker-wide lookup.
- One holder: a pull creates an item only when no item on its tracker holds the issue; a source whose scope lists an issue another source's item holds leaves it and reports `held by <ID> of source <other>`.
- Reference translation (`_source_view.py`, `_comment_view.py`) and relink's "already held" check (`_source_links.py`) use the same tracker-wide lookup.
- `_source_checks.py`: `source_id_unique` reports two items holding one issue of one tracker, across sources.
- A dropped link is reported: a mapped link whose other end no item on the tracker holds makes one line per host issue, `<key>: <n> link(s) not followed, no item holds <target key>, …`.

## Acceptance

- The BUG-1284 scenario: an `epics` source and a `stories` source on one base URL, each scoped to the same project with a filter on its label, both mapping to one type. `sq source pull epics` reports the link not followed; `sq source pull stories` makes the ref on the epics item, without the epics issue changing. The test fails on the tree before this subtask (state in the handback that it was run and seen to fail).
- Overlapping scopes (a group and a project in it): the second source creates nothing for an issue the first holds and reports `held by`.
- `sq check` reports `source_id_unique` for two items of two sources on one tracker holding one issue.
- A tracker reference in a description resolves to an item held by another source of the same tracker.
- Relink of an issue another source's item holds is refused naming that item.
- Full gate green; comment on BUG-1284 citing the regression test, asking qa to verify it.

## Tests (about 6 new)

In `tests/cli/test_source_links.py` and `tests/check/test_source_rules.py`: the regression scenario with the dropped-link line and the heal; one holder across overlapping scopes; reference translation across sources; relink refusal across sources; `source_id_unique` across sources (extend the existing case's tracker setup rather than duplicating it).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Probes read the scope and the filter values

<!-- sq:subtask:ST7:body -->
Size: M.

## Scope

- The access probe reads the scope: an unknown or unreadable GitLab project or group, GitHub repository or Jira JQL fails, naming its key; this blocks every fetching command (section 14, **Access probes before every fetch**).
- An empty scope is a warning; a filter that accepts no listed issue is a warning.
- Every value a filter expression names is checked like the map keys: it must exist on its side of the tracker; on a side the tracker cannot list, it is a warning when no issue in the scope carries it.
- Files: `_tracker_probes.py` (the shared probe flow, the filter-text helpers renamed to the scope), `_gitlab_probes.py`, `_github_probes.py`, `_jira_probes.py`, `_probes.py`, `_services/_source_links.py` (`_checklist`). Probe messages and their remedies name the scope key or the filter side, never a label filter.
- Fixtures: an unreadable-scope route and an empty-scope route per connector where the case needs one.

## Acceptance

- `sq source check` on a GitLab source naming an unknown project fails naming `project`; on a GitHub unknown repository fails naming `repository`; on a Jira JQL the tracker rejects fails naming `jql`.
- An empty scope and a filter matching nothing are warnings, and the check exits as a warning does.
- A filter value missing on a listable side fails; on an unlistable side it is a warning when no scoped issue carries it.
- `grep -rn 'filter readable\|filter_text' src/squads/_sources` finds nothing.
- Full gate green.

## Tests (about 4 new)

In `tests/cli/test_source_check.py`: unreadable scope per connector family (one case naming the key); empty scope warning; filter matching nothing warning; filter value missing on its side. Update the existing filter-probe cases in place.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Docs and changelog for scoped sources

<!-- sq:subtask:ST8:body -->
Size: M.

## Scope

Adopter-facing text for scoped sources, per the list owed in ADR-1274 section 14 **No migration**:

- `docs/sources.md`: the key table (scope keys, `filter` optional); the filter expression grammar with precedence, quoting and the TOML literal-string advice, with examples; the "`filter` is required" paragraph replaced by the scope rule; each connector's filter bullet replaced by its scope key and listing; restricted issues and internal notes; the states; the `filtered out`, `skipped (no type)` and `restricted` counts; an unmapped type as the way to leave issues out; links resolved across one tracker's sources and from either end; the dropped-link line; the unlink warning's remedy; the Jira link bullet.
- `CHANGELOG.md`, unreleased section: the external-sources entry with each connector's scope key and a filter expression per side; the no-type count replacing the per-issue report (an issue mapping to two types is still named); the `sq source pull`, `source unlink` and `sq source check` entries ("the scope readable").
- `docs/stability.md`: the `sources.toml` grammar, the filter expression grammar included.
- Read the scaffold starter (`sq override scaffold sources` in a scratch squad) and its worked example for prose quality; report any wording fix to the developer's subtask rather than editing code.

## Acceptance

- Every item of the owed list is covered; no internal references (no item IDs, no development-process wording); present truth only.
- Every TOML example in the docs loads (verify in a scratch squad nested under the scratchpad, never under /tmp directly).
- `sq check` clean.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T09:59:02Z] `tech-lead` Olivia Lead:
  - Broke FEAT-1285 into eight ordered subtasks, one fresh developer each, each leaving the gate green; design is ADR-1274 section 14 with rulings f6cbdfc, ec3c412 and af70274.
  - ST1 moves listing to the scope endpoint because the load refusal of the string filter forces it; the filter loads in ST1 and is applied in ST3. Tests are CLI surface (about 36 new), the parser included.
  - ST6 carries the BUG-1284 regression test; ST8 is the tech writer's, last. @python-dev start with ST1.
- [2026-11-04T10:09:02Z] `python-dev` Elias Python:
  - ST1 done: scope keys and filter expression parser.
  - Registry declares scope keys per connector version; SourceSpec carries scope (key, value) and the parsed filter (side to expression, empty when absent); new _sources/_filter.py holds the tokenizer, parser and evaluation; the loader refuses missing/two/foreign/empty scope, string or empty filter, unknown side, empty and malformed expressions with source, side, line and column.
  - Connectors take the scope and list the whole scope in every state: GitLab project/group issues endpoint, GitHub repository issues endpoint, Jira jql. Probes read the scope (messages say scope, not filter). Scaffold starter and fixtures migrated; filter is loaded and validated but not applied by the pull yet.
  - For the tech writer: sources.toml needs a scope key (project|group, repository, jql) and an optional [sources.<name>.filter] table with one expression per side; a string filter or a missing scope fails at load; source check wording now says scope.
- [2026-11-04T10:35:47Z] `python-dev` Elias Python:
  - - ST2 done: GitLab confidential issues and Jira (both versions) issues with a security level are treated as not returned by the listing, single fetch and lookup; GitLab internal notes are not imported. The pull report counts dropped ones: `restricted <n>` on the source line when non-zero, `restricted` in --json. A held issue turning restricted reads gone and its item stays.
    - ST3 done: the filter is evaluated on each listing row, sides ANDed. Unheld rejected issues are counted (`filtered out <n>`, `filtered_out`) and never named or written. Held and rejected reads out-of-filter "(rejected by the filter)"; held and not listed but returned by ID reads out-of-filter "(outside the scope)"; not returned reads gone. Unchanged out-of-filter items are not read in detail again; one the filter accepts again reads open.
    - No-type issues are counted (`skipped <n> (no type)`, `skipped_no_type`) with no detail fetch and no per-issue line; an issue mapping to two types is named with its values on every pull, also without a detail fetch.
    - For the tech writer: new --json fields restricted, filtered_out, skipped_no_type on each source report.
- [2026-11-04T10:38:09Z] `op-pierre` Pierre Chat:
  - Request (2026-11-04): the gitlab, github and jira connector modules move into _sources/_gitlab, _sources/_github and _sources/_jira subpackages, each re-exporting its public names from its __init__.py (an exception to the no-re-export rule, recorded in CLAUDE.md and the INITS_WITH_CODE guard).
- [2026-11-04T10:40:25Z] `python-dev` Elias Python:
  - Moved the platform modules into subpackages with git mv (no behaviour change):
    - _gitlab/: _connector.py, _probes.py; init re-exports GitLabConnector
    - _github/: _connector.py, _probes.py; init re-exports GitHubConnector
    - _jira/: _connector.py, _cloud.py, _dc.py, _probes.py, _adf.py, _wiki.py; init re-exports JiraCloudConnector, JiraDcConnector, adf, jira_wiki
    - Shared modules stay in _sources/. The registry and converter tables now name the subpackages. INITS_WITH_CODE, the vocabulary tracker-enum paths and CLAUDE.md are updated.
    - Gates: pyright, ruff check and format clean; source CLI tests, tests/check and tests/meta: 981 passed.
- [2026-11-04T10:45:59Z] `manager` Catherine Manager:
  - Paused after ST3 and the connector subpackage move (18251834): the codebase-wide re-export sweep op-pierre ruled on ADR-78 runs first, since ST4-ST7 touch the same imports.
- [2026-11-04T14:15:59Z] `manager` Catherine Manager:
  - Resumed after the re-export sweep (TASK-1289, fe524f16): ST4 onward follow ADR-1287 (import through package inits, new names added to the _sources re-exports) and use self.credentials for the credential store.
- [2026-11-04T14:26:04Z] `python-dev` Elias Python:
  - - ST4 done: `show --refresh` and `relink` decide scope without listing it. A connector method `in_scope` reads the issue's key (GitLab project or group path, GitHub repository ignoring case) or runs one search `id = <id> AND (<jql>)` on Jira. The filter is then applied as a pull would: an issue the filter rejects, or one outside the scope, is stored `out-of-filter`; relink links such an issue the same way. GitLab relink by immutable ID still resolves through the scope listing. The unlink warning now reads: "<key> is still in the scope of source '<name>' and accepted by its filter: the next `sq source pull` imports it again as a new item; to prevent that, narrow the scope or the filter in sources.toml, or change the issue on the tracker so neither selects it".
    - ST5 done: a link carries its type as read from the issue and its inverse (GitLab blocks/is_blocked_by, relates_to both ways; GitHub blocking/blocked_by; Jira outward/inward phrases). A ref is made host to target from maps.links[type] and target to host from maps.links[inverse], each only when mapped, so a link gives the same refs whichever end is read and one ref when both are read. Pulling only the blocked end of a link now makes the ref on the held blocking item.
    - For the tech writer: no new config keys or output fields; the only user-visible text is the unlink warning above. Fixtures: Jira in-scope search routes, GitLab link recorded on both issues.
- [2026-11-04T14:36:51Z] `python-dev` Elias Python:
  - - ST6 done: links, references and holders resolve across every source on one tracker (same normalised base URL).
    - A link whose other end is held by another source's item now makes its ref, from either end and in either pull order.
    - A pull creates no item for an issue another source's item holds; its line reads `<key>: held by <ID> of source '<other>'` (or names the source creating it in the same pull).
    - A mapped link whose other end no item holds adds one line per host issue: `<key>: <n> link(s) not followed, no item holds <target key>, ...`. Existing reports that listed an issue next to an unheld link target now carry that line.
    - A tracker reference in a description or comment reads as the item another source of the tracker holds; `relink` refuses an issue held by another source's item, naming it.
    - `sq check` `source_id_unique` groups by tracker: the message reads `of sources 'a', 'b'` when the holders belong to different sources.
    - For the tech writer: the held-by and not-followed lines above; nothing is stored, no config change.
- [2026-11-04T14:45:47Z] `python-dev` Elias Python:
  - - ST7 done: `sq source check` and the access probes read the scope and the filter values.
    - An unknown or invisible scope fails access naming its key: `the scope project 'platform/nope' does not exist or is not visible to the token` (same for `repository`, `group`), fix `correct \`project\` of source '<name>' in sources.toml`. A scope the tracker rejects (Jira JQL, HTTP 4xx) reads `the scope jql '...' is not accepted: ...`, fix `correct \`jql\` of source '<name>' in sources.toml`. Both block every fetching command.
    - Empty scope stays a warning: fix now `create an issue in the scope, or correct \`<key>\` of source '<name>' in sources.toml`.
    - New vocabulary warning when the filter accepts no listed issue: `the filter accepts none of the <n> issue(s) of the scope`, fix `correct it in [sources.<name>.filter] in sources.toml`; exit 0.
    - Every value a filter names is checked like a map key: `filter.<side>: '<value>' is not among the tracker's <labels|issue types|...>` fails on a listable side (fix `correct it in [sources.<name>.filter] in sources.toml, or create it on the tracker`); on an unlistable side it warns `... is carried by no issue in the scope, so it cannot be confirmed among the tracker's ...`.
    - Wording: "in-filter issue" in the map-key warning becomes "issue in the scope"; the vocabulary pass line reads `every value the maps and the filter name exists on the tracker` when a filter is declared (unchanged otherwise). Coverage lines read "in-scope".
- [2026-11-04T14:56:55Z] `tech-writer` Theo Writer:
  - - ST8 done: docs and CHANGELOG for scoped sources, written from the code at bff7de64 and the tests' asserted wording.
      - `docs/sources.md`: key table (one scope key, `filter` optional) and the scope rule with its load refusals; a new "Which issues become items" section (scope table per connector, filter semantics, grammar with precedence, quoting and the TOML literal-string advice, a multi-line example, load refusals with line/column, the type map and the no-type count, the two-type line, restricted issues and internal notes); the probe lines (scope failures, empty-scope and filter-accepts-none warnings, filter values checked like map keys); the pull report (`restricted`, `filtered out`, `skipped (no type)`, the held-state table with both out-of-filter reasons vs gone, `--json` counts); a "Links across sources" section (one tracker, one holder and `held by`, either end, links not followed); `show --refresh`/relink deciding scope without listing; the new unlink warning and its remedy; `source_id_unique` across sources; each connector's scope, restriction and link bullet (Jira inward/outward).
      - `docs/stability.md`: the `sources.toml` grammar with the scope keys, the filter grammar (EBNF) and what stays stable; pull `--json` gains `restricted`, `filtered_out`, `skipped_no_type`. `docs/README.md` index line updated.
      - `CHANGELOG.md` 0.20: external-sources entry reworded; new entries for scopes, filter expressions, the type map count, restricted issues and links across one tracker; connector, pull, check, unlink/relink and `sq check` entries updated. No label `filter` remains.
      - Every TOML example loads in a scratch squad; `tests/meta` 748 passed.
    - Scaffold starter (`_overrides/_service.py`), wording for @python-dev: say "ASCII letters" for a bare word; "The pull lists every issue of it" could read "every issue of the scope, open and closed"; the worked example filters on `type::bug`/`type::story` but maps `labels` `bug`, so those issues reach no type and are only counted. Suggest mapping `"type::bug" = "bug"` or aligning the filter.
    - Message wording, optional: `the keyword 'or' is written in lowercase; quote the value ("OR") ...` reads as if `OR` were lowercase; "keywords are lowercase: write 'or', or quote the value ..." is clearer. The docs quote the current message.
- [2026-11-04T14:59:18Z] `python-dev` Elias Python:
  - Scaffold starter and filter message reworded per the writer: starter says "ASCII letters", the pull lists "every issue of the scope, open and closed", and the worked example maps "type::bug" = "bug" and "type::story" = "feature" to match its filter. Lowercase-keyword refusal now reads: keywords are lowercase: write 'or', or quote the value ("OR") to match it (line, column kept); test and docs/sources.md quotation updated.
- [2026-11-04T15:31:03Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1292: changes requested, 13 findings (8 medium, 5 low). @tech-lead the medium ones are F1 to F8.
- [2026-11-04T16:45:44Z] `manager` Catherine Manager:
  - Done: REV-1292 approved. The live run against a real GitLab instance is the remaining check, tracked on TASK-1278.
<!-- sq:discussion:end -->
