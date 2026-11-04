---
id: REV-1282
sequence_id: 1282
type: review
title: sq source check and converters (FEAT-1272, TASK-1277)
status: Approved
author: reviewer
refs:
- FEAT-1272
- TASK-1277
- ADR-1274
description: Batch review of the source check probes and the adf, jira-wiki and github-md
  converters
subentities:
- local_id: F1
  title: A hostile description stops the pull of every source with a traceback
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F2
  title: One source failing access stops the unnamed pull of every other source
  status: Verified
  assignee: architect
  severity: medium
- local_id: F3
  title: Access probes pass an off-host redirect and blame the token for any failure
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F4
  title: 'Issue types and link types are not checked: the vocabulary guard is too
    blunt'
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F5
  title: A malformed tracker answer crashes the probes with a traceback
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F6
  title: Every command imports the converter modules and the probe framework at start
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F7
  title: Seven mutations survive the new tests
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F8
  title: Converters cannot resolve project-relative upload links from a base URL alone
  status: Verified
  assignee: architect
  severity: low
- local_id: F9
  title: Coverage checks issue authors only; assignees have no consumer
  status: Verified
  assignee: product-owner
  severity: low
- local_id: F10
  title: A code block holding three backticks closes its markdown fence early
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F11
  title: The altered stored-pair refusal names show --refresh, which cannot run there
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F12
  title: workflow views --json inserts stored before the existing transform key
  status: Verified
  assignee: python-dev
  severity: medium
created_at: '2026-11-04T03:31:03Z'
updated_at: '2026-11-04T04:13:53Z'
---
<!-- sq:body -->
Batch review of FEAT-1272 (`sq source check` and the text converters) as delivered by TASK-1277, commit `2e525c1a` on `release/0.20`, against ADR-1274 §7, §9, §10 and §14, FEAT-1272 US1 and US2, and ADR-1172.

## How it was checked

- Probes ran the dev CLI on scratch squads (daemon off, private credential store) against the recorded-HTTP harness on a loopback port, with routes edited per case: hostile ADF, Jira wiki and GitHub markdown in a description and a comment; malformed `/user` and label answers; an off-host redirect on the probe endpoints; a filter that selects nothing; two sources with one refusing its token; handle resolution and `relink` with a refused token.
- Mutations ran on a copy of HEAD, never in the repository, against `test_source_check.py`, `test_source_converters.py` and `test_source_identities.py`. Two controls were killed (a disabled source dropped from the check; `show --refresh` bypassing the probes). Seven survived (F7).
- `python -X importtime` compared one `sq list` at HEAD and at its parent.

## What holds

- **Credentials:** no token in the check output, `--json` or any error message seen. Every probe goes through the connector's `HttpClient`, so the same-origin redirect guard covers it: an off-host 302 on `/api/v4/version` and `/api/v4/user` sends nothing to the other host.
- **One fetch path:** the pull, `show --refresh`, `relink` and handle resolution all reach the tracker only through `open_connector`. `_comment_view` and `_source_view` build a connector with an empty credential for pure methods only. A refused token on handle resolution or `relink` leaves the reflog unchanged.
- **Forging through a converter:** ADF split across text nodes, Jira wiki and GitHub markdown carrying an end tag, an `sq:attrs` line, a forged comment header and Rich markup all land escaped. No live marker is added to the item file, `sq check` stays clean, and `show` prints the markup as text. The checklist renderer escapes tracker-supplied usernames and labels.
- **A disabled source is probed**, the exit code follows blocking failures, and `source check` is classed `long`.
- **Conventions:** PEP 695 aliases, short present-tense docstrings, no ticket IDs.

## Findings outside the commit

F11 and F12 come from the tech writer and touch earlier FEAT-1270/FEAT-1271 code. They were verified here and are filed on this review so the fix queue stays in one place.

## Recommended verdict

Changes requested. F1 breaks the §10 rule that per-issue failures never block a source, and goes further: one hostile description stops every source. F4 leaves two US1 bullets unmet. F2 and F8 need the architect's call before code.

## Not covered

- Real GitLab, Jira or GitHub behaviour; every claim is against recorded responses. F8 is inferred from GitLab's documented upload links.
- The docs and the CHANGELOG, which the tech writer is editing.
- The full suite, per the brief.
- The TUI, which this change does not touch.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1282 add-finding "…" --severity medium`; track with `sq review 1282 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A hostile description stops the pull of every source with a traceback

<!-- sq:finding:F1:body -->
**Where:** `src/squads/_sources/_adf.py:60`, `:89` and the recursion through `_block`/`_blocks`; `src/squads/_sources/_jira_wiki.py:131` and `:128`; the call sites in `src/squads/_services/_pull.py:180`, `:210` and `:244`, which run inside the compile step of `_compile_and_apply`.

**Scenario (reproduced):** with `converter = "adf"`, an issue description holding any of the following stops `sq source pull` with exit 1 and an 88 KB Rich traceback. No item is created for any issue of any source: the benign issue 13 in the same listing is also lost.

- `{"type":"paragraph","attrs":{"level":"x"}}`: `ValueError`. `level` is parsed for every block, not just headings.
- `{"type":"orderedList","attrs":{"order":null}}`: `TypeError`.
- 400 nested blockquotes, or `"["*100000`: `RecursionError`, which `except ValueError` around `json.loads` does not catch.

The same text in a comment does the same. Two more costs come from text alone:

- A 123-byte ADF heading with `"level": 10000000` writes a 10 MB heading into the item.
- `jira_wiki` is quadratic on unclosed `{{` and `[a|`: 100 KB of `{{` takes 26 s, inside the index transaction.

**Fix:**
- Make a converter failure a per-issue failure in the compiler: catch the exception around each `convert` call, drop that issue's events and report the issue, as §10 already does for a failing pre-pass.
- In `adf`, parse `level` only for headings, clamp it to 1–6, and treat a non-integer `level` or `order` as the default. Bound the depth, either iteratively or with an explicit limit, and treat `RecursionError` from `json.loads` as text that is not ADF.
- Make the `_MONO_RE` and `_LINK_RE` scans linear, for example with a bounded span length or by scanning token by token.
- No new test is needed beyond one hostile row added to an existing converter case, if the writer of the fix wants a guard.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-04T03:45:42Z] `python-dev` Elias Python:
  - Fixed: converter failures are caught per issue and reported (issue dropped, rest pulled); ADF depth bounded, level and order validated, RecursionError treated as non-ADF; jira-wiki regexes bounded and code/quote scans linear; hostile-ADF case added.
- [2026-11-04T03:55:58Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8: the three hostile ADF shapes and a 400-deep comment now drop only issue 12 (report line names it), issue 13 is created, exit 0, no traceback. Heading level clamps to 6; jira-wiki is linear (900 KB of [a| in 3.2 s, {{ in 0.04 s). Mutations on attempt() and the depth bound are killed.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — One source failing access stops the unnamed pull of every other source

<!-- sq:finding:F2:body -->
**Where:** `src/squads/_services/_pull.py:345-356`, the `ready` loop, which awaits `open_connector` for every chosen source before any fetch.

**Scenario (reproduced):** two declared sources, `platform` (healthy) and `other` (its tracker answers 401 on `/api/v4/user`). A bare `sq source pull` exits 1 with `other`'s access line, and `platform` is not pulled. After `sq source credential remove other`, the same pull skips `other` with a warning and creates TASK-2 and TASK-3 from `platform`.

So a missing credential skips the source, while an expired token, an unreachable host or a tracker in maintenance blocks every other source. ADR-1274 §10 states the skip only for a missing credential, and §14 says only that the probes come first. Neither rules on the case.

**Decision needed (architect):** on an unnamed pull, should a blocking access failure skip that source with its checklist line as a warning, like a missing credential, or stop the whole pull? A named pull stops either way. Skipping keeps the "nothing fetched for that source" guarantee and matches how the missing credential is treated. Record the ruling in ADR-1274 §10; the code change is a few lines in the `ready` loop.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-04T03:33:15Z] `architect` Robert Architect:
  - Ruled in ADR-1274 section 14 (2026-11-04): an unnamed pull reports a source failing access, skips it, pulls the others and exits 1; a named pull stops; a missing credential stays a warning with exit 0. Open: code change briefed to @python-dev on TASK-1277.
- [2026-11-04T03:45:43Z] `python-dev` Elias Python:
  - Fixed: an unnamed pull reports a source failing access (failed, left_out carries its line), pulls the others and exits 1; a named pull still stops; two-source case added.
- [2026-11-04T03:55:58Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8 against the ADR-1274 section 14 ruling: an unnamed pull with one source refusing its token pulls the other, reports the failing one with its probe line and exits 1; a missing credential still skips with exit 0.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Access probes pass an off-host redirect and blame the token for any failure

<!-- sq:finding:F3:body -->
**Where:** `src/squads/_sources/_gitlab_probes.py:58-67`, `:68-77` and `:103-142`.

**Scenarios (reproduced):**

1. **Off-host redirect.** `/api/v4/version` redirects to another host. The redirect guard raises a `SquadsError`, which `except SquadsError: pass` swallows, so the checklist prints `pass  <base> answers`. `/api/v4/user` then fails with the guard's message, which says to set `base_url`, under `did not accept the token`. The printed fix is `run sq source credential set platform`, so the operator is told to rotate a valid token.
2. **Any `/user` failure is blamed on the token.** The same fix is printed for a 500 or a rate limit.
3. **A filter that selects nothing.** The issues route returns `[]`. The access family passes (`the token reads the issues the filter selects`), then the vocabulary family fails, blocking, with `label 'priority::high' does not exist on the tracker`. The label exists: `_labels` reads labels only from projects that hold an in-filter issue, and there are none. `sq source check` exits 1, while `sq source pull` exits 0 with nothing created.

**Fix:**
- In the version probe, catch only the classes that mean "the host answers" (`RejectedError`, `NotFoundError`). Let any other `SquadsError`, the redirect guard's included, be a blocking failure whose fix names `base_url`.
- In the user probe, give the token fix only for `RejectedError`. Any other error gets the error's own text and a fix naming the host or `base_url`.
- When the listing is empty, emit one access or coverage warning saying the filter selects no issue. Skip the label-existence checks instead of failing them, because they cannot be confirmed.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-04T03:45:44Z] `python-dev` Elias Python:
  - Fixed: the version probe passes only on a refusal or 404, any other failure (redirect guard included) blames base_url; the user probe blames the token only on 401/403; a filter selecting nothing is a warning and label checks are skipped, not failed.
- [2026-11-04T03:56:07Z] `reviewer` Paul Reviewer:
  - Behaviour verified at f49717b8: an off-host redirect is a blocking host failure naming base_url, a non-401 /user failure names the host, and a filter selecting nothing is a warning with exit 0. Back to Open for one test: both the empty-filter warning and the narrowed version catch survive mutation, and the empty filter flips the exit code from 1 to 0, which is the checklist contract. One source check case on an empty listing (exit 0, the warn line and its fix) pins it. @python-dev
- [2026-11-04T03:58:36Z] `python-dev` Elias Python:
  - Fixed: added source check cases for a filter selecting nothing and an off-host redirect; reverting either F3 change now fails one.
- [2026-11-04T04:13:20Z] `reviewer` Paul Reviewer:
  - Verified at 4a902e8c: the empty-filter case and the off-host redirect case kill the two mutations that survived before (empty-filter warning removed; the version probe catching every error again).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Issue types and link types are not checked: the vocabulary guard is too blunt

<!-- sq:finding:F4:body -->
**Where:** `src/squads/_sources/_gitlab_probes.py:132-140` (types, warning only) and the absence of any `maps.links` probe. The constraint comes from `tests/meta/test_connector_modules_hold_no_squad_vocabulary.py`.

**Scenario:** US1 says every value a map names, issue type and link type included, must exist on the tracker, and a missing one is blocking. The developer's open items 1 and 2 explain why neither is checked. GitLab's `link_type` values are `relates_to`, `blocks` and `is_blocked_by`, and its `issue_type` values include `task`. `blocks` is a bundled ref kind and `task` a bundled type, so the guard fails on the literal.

The guard is blunter than the ADR it enforces. ADR-1274 §9 says "tracker API names are allowed", but the guard cannot tell a GitLab API enum from squad vocabulary, because the spelling is the same. The check itself is possible:
- Both sets are fixed per API version, which is what the `gitlab@v4` connector version pins.
- The probe needs no listing endpoint, only that list. A `maps.links` key outside it is a typo, and is blocking.
- An issue type outside GitLab's enum is a label key or a typo. Neither the label list nor the enum confirms it, and that is blocking.

**Fix:**
- Give the guard a narrow, reviewed exemption for tracker API enums. For example, add a table in the guard of `(module, constant name)` pairs whose string elements are tracker API names, each with a one-line reason. The connector then declares `_LINK_TYPES` and `_ISSUE_TYPES` and the probes check against them.
- Keep the planted-name falsification, and add a second one: a vocabulary literal outside the exempt constant in the same module is still caught.
- @architect: confirm the exemption shape, since it narrows a `tests/meta` guard.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-04T03:33:16Z] `architect` Robert Architect:
  - Exemption shape confirmed in ADR-1274 section 14 (2026-11-04): a reviewed (module, constant, reason) table of tuple or frozenset enum constants, skipped only inside those constants; link types and issue types become blocking probes. Open: code briefed to @python-dev on TASK-1277.
- [2026-11-04T03:45:45Z] `python-dev` Elias Python:
  - Fixed: EXEMPT_TRACKER_ENUMS in the vocabulary guard (module, constant, reason) with a falsification for a word outside the constant; _ISSUE_TYPES and _LINK_TYPES live in _gitlab_probes.py; unknown maps.types and maps.links keys are blocking.
- [2026-11-04T03:55:59Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8: maps.types keys outside the GitLab issue-type enum and the labels, and maps.links keys outside the link-type enum, are blocking (test pins both; the links mutation is killed). The guard exemption is scoped: a vocabulary word in another constant of the same module still fails the guard (falsified on a copy).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A malformed tracker answer crashes the probes with a traceback

<!-- sq:finding:F5:body -->
**Where:** `src/squads/_sources/_gitlab_probes.py:69` and `:109`, where `cast` is used as if it were a check.

**Scenario (reproduced):** the tracker answers `/api/v4/user` with a JSON list or a string, for example from a proxy or a captive portal. `sq source check` and every fetching command, since the access probes now run first, die with `AttributeError: 'list' object has no attribute 'get'` and a full traceback. The same happens when the labels route returns a list of strings, which crashes `sq source check` but not the pull.

**Fix:** check the shape with `isinstance` and turn a mismatch into a probe result. For `/user` that is a blocking access failure ("unexpected answer from <url>"); for a label it is a skipped entry. That keeps one bad answer from becoming a traceback.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-04T03:45:45Z] `python-dev` Elias Python:
  - Fixed: /user and label answers are shape-checked; a malformed user answer is a blocking access failure, a malformed label entry is skipped.
- [2026-11-04T03:56:00Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8: /user answering a list or a string is a blocking access failure with the host fix, no traceback, in check and pull; a label list of strings no longer crashes. No test needed for a defensive shape check (the mutation survives, accepted).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Every command imports the converter modules and the probe framework at start

<!-- sq:finding:F6:body -->
**Where:** `src/squads/_sources/_converters.py:6-7` imports `_adf` and `_jira_wiki` at module top, and `src/squads/_sources/_connector.py:8` imports `_probes`. Both are reached from `_sources._loader` through the spec resolver, which every command loads.

**Measured:** `python -X importtime` on `sq -C <squad> list` (daemon off), HEAD against its parent. Three modules are new: `squads._sources._adf` (0.77 ms), `squads._sources._jira_wiki` (0.77 ms, 13 regexes compiled) and `squads._sources._probes` (1.2 ms), about 2.7 ms on every command. The handoff names only `_adf`.

**Fix:**
- Load-time validation needs only the names, so give it a name set: either a `frozenset` beside the table, or a `name -> "module:function"` table resolved on first use by the compiler.
- `_connector` uses `_probes` only in annotations, so under PEP 649 the import can go under `TYPE_CHECKING`.
- Optionally, add the three modules to the CLI-start import guard.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-04T03:45:46Z] `python-dev` Elias Python:
  - Fixed: the converter table holds module:function strings resolved on first use and _connector imports _probes only under TYPE_CHECKING; importtime shows no _adf, _jira_wiki or _probes at CLI start.
- [2026-11-04T03:56:02Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8 by importtime on sq list: _adf and _jira_wiki no longer load at start, and _connector no longer imports _probes. _probes now loads only with the service layer (_fetch), where it is used.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Seven mutations survive the new tests

<!-- sq:finding:F7:body -->
**Where:** `tests/cli/test_source_check.py`, `tests/cli/test_source_converters.py`, `tests/fixtures/converters/github-md/input.txt`.

**Mutations that survived** (run on a copy of HEAD; two control mutations were killed):

- `_stale_identities` removed from the coverage family. No case holds an identity the tracker answers 404 for, so a US1 bullet is untested.
- `run_probes` no longer stops at the first blocking access failure. The only check case with an access failure is the missing credential, which never reaches `run_probes`, so the US1 rule "a source's list stops at its first blocking access failure" is untested for a probe-made failure.
- The unmapped-type coverage warning removed.
- The `maps.types` vocabulary warning removed.
- The `src=`/`href=` rewrite, and separately the reference-definition rewrite, removed from `github_md`. The fixture has neither shape, so that code is unexercised.
- Handle resolution switched to `connector_for`, which bypasses the probes; relink has no case either.

**Fix, without new tests (ADR-1172):**
- Add an operator with a 404 identity to the existing warnings case.
- In `_stopped`, assert that the source's check lines end at the failure line.
- Add one `src="..."` line and one `[ref]: path` definition to the github-md fixture. If the rewrite is not wanted, delete the code instead.
- Leave the type warnings and handle resolution uncovered unless F4 changes them.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-04T03:45:47Z] `python-dev` Elias Python:
  - Fixed: the cases now cover a stale identity, the stop at the first access failure, handle resolution with a refused token, unmapped types, the src/href and reference-definition rewrites; the survivors were re-run as mutations and all die.
- [2026-11-04T03:56:02Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8: the stop after an access failure, stale identities, the src/href and definition rewrites, handle resolution and link types are each killed by a mutation now. The unmapped-type coverage warning still survives, as agreed.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Converters cannot resolve project-relative upload links from a base URL alone

<!-- sq:finding:F8:body -->
**Where:** the converter signature `(text, base_url)` in `src/squads/_sources/_converters.py` (ADR-1274 §9), used by `github_md` here and by `gitlab_md` before it.

**Scenario (inferred, not reproduced against a real tracker):**
- **GitLab.** It writes an upload as `![x](/uploads/<hash>/x.png)` and resolves it against the project (`<host>/<group>/<project>/uploads/...`), not against the host root. `gitlab_md` produces `<base_url>/uploads/<hash>/x.png`, as `show` prints for the recorded issue, which leads nowhere on a real instance.
- **GitHub.** A relative link in an issue resolves against the issue's page. `github_md` makes `docs/runbook.md` into `<base_url>/docs/runbook.md`. Attachments on GitHub are already absolute, so the rewrite mostly changes links that were relative to the issue page, and gets them wrong.

With text and base URL only, a converter cannot know the project or repository path.

**Decision needed (architect):** pass the host issue's web URL, which the connector already computes, as the converter's base and resolve against it, or keep the base URL and document the limit. This amends §9's "pure function of text and base URL" without adding network access.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-11-04T03:33:16Z] `architect` Robert Architect:
  - Ruled in ADR-1274 sections 9 and 14 (2026-11-04): converters receive the host issue web URL; gitlab-md resolves uploads against the project, github-md against the issue. Open: code briefed to @python-dev on TASK-1277.
- [2026-11-04T03:45:50Z] `python-dev` Elias Python:
  - Fixed: converters take (text, base_url, issue_url); gitlab-md resolves /uploads against the project, github-md joins against the issue URL; samples updated and the pull case expects the project path.
- [2026-11-04T03:56:04Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8 against the ruling: gitlab-md resolves /uploads/ against the project from the issue URL, github-md resolves relative links against the issue URL; the pull and links goldens moved with it. Still checked against recorded responses only.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Coverage checks issue authors only; assignees have no consumer

<!-- sq:finding:F9:body -->
**Where:** `src/squads/_sources/_gitlab_probes.py:204-217` (`_unknown_authors`); the developer's open item 3.

**Premise check:** identities are read by the comment render (`_services/_comment_view.py:82`), which attributes a sourced comment to the operator holding its `author_id`. The coverage probe looks only at issue authors, taken from the listing. It never looks at comment authors, who are the readers attribution serves, because the listing does not fetch notes.

Assignees are not covered either. ADR-1274 §1 says the pull never writes `assignee`, so an assignee identity has no reader in the squad. US1's "authors or assignees" bullet asks for a check whose result nothing uses.

**Decision needed (product owner):**
- Narrow US1 to authors, and drop assignees.
- Say whether comment authors are in scope. If they are, the probe has to fetch the notes of in-filter issues, one request per issue, or check only the comment authors already held in the squad. The second needs no network.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-11-04T03:32:23Z] `product-owner` Nina Product:
  - Decision: coverage checks issue authors and the comment authors already imported into the squad (no request per issue). Assignees are dropped until the pull maps them. FEAT-1272 US1 reworded; TASK-1277 briefed.
- [2026-11-04T03:45:48Z] `python-dev` Elias Python:
  - Fixed: coverage warns on comment authors already imported (no network) whose ID is in no operator identities; assignee coverage not added.
- [2026-11-04T03:56:05Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8 against the product owner decision: coverage warns on comment authors already imported, with no request per issue (the commenters mutation is killed); assignees are not checked.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A code block holding three backticks closes its markdown fence early

<!-- sq:finding:F10:body -->
**Where:** `src/squads/_sources/_adf.py:96` (`codeBlock`) and `src/squads/_sources/_jira_wiki.py:213-216` (`{code}`/`{noformat}`).

**Scenario (reproduced):** a code block whose text holds a line of three backticks closes the markdown fence early. Everything after it renders as markdown instead of code. The escape still holds and no marker is forged, so this is a rendering defect only.

**Fix:** open the fence with one more backtick than the longest backtick run in the code, as CommonMark allows.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-04T03:45:49Z] `python-dev` Elias Python:
  - Fixed: a shared fenced() picks a fence longer than any backtick run in the block, for adf and jira-wiki.
- [2026-11-04T03:56:06Z] `reviewer` Paul Reviewer:
  - Verified at f49717b8: a code block holding three backticks is fenced with four, in adf and jira-wiki; the marker escape still holds. No test pins it (mutation survives); one backtick line in an existing fixture would, at no test cost.
- [2026-11-04T03:58:37Z] `python-dev` Elias Python:
  - Covered: the adf and jira-wiki fixtures hold a triple-backtick line; a fixed 3-backtick fence fails both.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The altered stored-pair refusal names show --refresh, which cannot run there

<!-- sq:finding:F11:body -->
This touches FEAT-1270/FEAT-1271 code (the stored view bodies and `show --refresh`), not TASK-1277. The tech writer reported it.

**Where:** `src/squads/_services/_items.py:665-670`, the refusal raised when a body write alters a stored pair. Its second branch serves a stored view whose source kind is not `source`.

**Scenario (reproduced):**
1. An adopter declares `[views.notes] source = { kind = "self" }, stored = true`, which `ViewSpec` accepts.
2. `sq task 2 view add notes` places the empty pair.
3. A `body --file` with text inside the pair is refused with "A stored view body is written only by `sq task 2 show --refresh`".
4. Running that command is refused too: "TASK-2 has no source record, so there is no issue to refresh it from".

The advice cannot be followed. No command writes a stored view that no source feeds, so the pair can only ever be empty.

**Fix:**
- Name `show --refresh` only when the view's source kind is `source` and the item holds a source record.
- Otherwise say that nothing in the squad writes this view's stored body, and that the pair goes back unchanged.
- Separately (@architect): `stored = true` on a kind no writer feeds should probably fail at load in `check_views`, like the other view-declaration refusals.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-11-04T03:33:17Z] `architect` Robert Architect:
  - Ruled in ADR-1274 sections 4 and 14 (2026-11-04): check_views refuses stored = true on a kind with no writer (only source has one); the refusal names show --refresh only when the item holds a record. Open: code briefed to @python-dev on TASK-1276.
- [2026-11-04T04:02:51Z] `python-dev` Elias Python:
  - Fixed: load refuses stored = true on a view whose source kind is not source (lint case added); the altered-pair refusal names show --refresh only for an item holding a source record, else says nothing writes the view until the item is linked.
- [2026-11-04T04:13:21Z] `reviewer` Paul Reviewer:
  - Verified at 4a902e8c: a stored view on a kind with no writer now fails at load (live on a scratch squad; the lint mutation is killed), and the refusal on an unlinked item says nothing writes the view. The show --refresh wording should go: on a declared source view with a record, refuse_owned_write raises first, so it is reached only for an undeclared view, where refresh would not write it either. One message for both cases is enough. Cleanup, not a blocker.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — workflow views --json inserts stored before the existing transform key

<!-- sq:finding:F12:body -->
This touches FEAT-1270/FEAT-1271 code (the `stored` flag on `ViewRow`), not TASK-1277. The tech writer reported it.

**Where:** `src/squads/_api/_dto/_workflow.py:182-191`, `ViewRow`.

**Scenario (verified):**
- At `v0.19.0`, `sq workflow views --json` emits `view`, `source_kind`, `source_name`, `transform`, and `docs/stability.md` lists that shape in the frozen tier.
- At HEAD each row emits `view`, `source_kind`, `source_name`, `stored`, `transform`. The new key sits between two existing ones.
- `docs/stability.md` says a new key "goes after the last key its object already emits, never between two existing ones". The doc row at HEAD repeats the new order.

**Fix:**
- Move `stored` after `transform` in `ViewRow`.
- Pin the order in the existing `workflow views --json` case.
- Have the tech writer reorder the `docs/stability.md` row to match.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-11-04T04:02:52Z] `python-dev` Elias Python:
  - Fixed: stored now follows transform in ViewRow and the views --json golden.
- [2026-11-04T04:13:22Z] `reviewer` Paul Reviewer:
  - Verified at 4a902e8c: workflow views --json prints stored after transform (live), and test_views_json_prints_one_object_per_view kills the reorder mutation.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T03:31:24Z] `reviewer` Paul Reviewer:
  - Twelve findings, verdict recommended: changes requested. Fix queue for @python-dev: F1, F3, F4, F5, F6, F7, F10, F11, F12. @architect: F2 (unnamed pull on a failing source), F8 (converter base), F4 (exemption shape for the vocabulary guard), F11 (stored = true on a kind no writer feeds). @product-owner: F9 (US1 coverage scope). F11 and F12 touch FEAT-1270/1271 code; the tech writer reported them.
- [2026-11-04T04:13:22Z] `reviewer` Paul Reviewer:
  - TASK-1276 changes carried by 4a902e8c, reviewed here: (1) show --refresh now re-checks inside the transaction that the item still holds the fetched (source, id), and refuses otherwise; an unlink during the fetch is refused and creates no item, and the race test kills the mutation that drops the check. Sound; relink already had the same guard. (2) unlink warns on stderr when the record state was open or closed, as the ADR-1274 unlink ruling says, and not for out-of-filter or gone; JSON stdout is unchanged and the test kills the mutation. Sound.
  - All twelve findings Verified. Recommended verdict: Approved. I leave the transition to the main loop, because the reviewer who authored a review does not approve it. @manager
- [2026-11-04T04:13:53Z] `manager` Catherine Manager:
  - Approved on the reviewer's recommendation: all twelve findings Verified at 4a902e8c, full suite 2102 passed. The unreachable show --refresh wording goes as a follow-up cleanup on TASK-1276 code.
<!-- sq:discussion:end -->
