---
id: REV-1283
sequence_id: 1283
type: review
title: GitHub and Jira connectors (FEAT-1273, TASK-1278)
status: Approved
author: reviewer
refs:
- FEAT-1273
- TASK-1278
- ADR-1274
description: Batch review of the GitHub, Jira Cloud and Jira Data Center connectors
subentities:
- local_id: F1
  title: One issue's 404 between listing and detail stops the pull of every source
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F2
  title: A malformed tracker answer is read as closed, gone or out-of-filter
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F3
  title: Jira Data Center pulls agent-only service desk comments
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F4
  title: Jira Cloud handle resolution binds an identity to a fuzzy search hit
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F5
  title: Probe lines blame the filter or the token for a rate limit or an unlistable
    value
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F6
  title: A Jira label spelled like a priority overrides the priority field
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F7
  title: ADR-1274 owes lines for seven connector decisions
  status: Verified
  assignee: architect
  severity: low
- local_id: F8
  title: Four decided behaviours have no test, and three asserts are substrings
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F9
  title: 'Cleanup: Jira updated_at offset, a repos owner, ghe.com hosts'
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F10
  title: A map with no side fails with a raw pydantic dump
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F11
  title: New cases bring substring asserts, and two side rules have no test
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F12
  title: ADR-1274 calls an unconfirmable map key blocking; the probe warns
  status: Verified
  assignee: architect
  severity: low
created_at: '2026-11-04T04:55:55Z'
updated_at: '2026-11-04T05:38:54Z'
---
<!-- sq:body -->
Batch review of FEAT-1273 (the GitHub and Jira connectors) as delivered by TASK-1278, commit `bcbb5ad8` on `release/0.20`, against ADR-1274 (§14 included), FEAT-1273 US1 and US3 to US5, ADR-1172, and the bar REV-1281 and REV-1282 set on GitLab, the pull and the converters.

## How it was checked

- Probes ran the dev CLI (daemon off, a private credential store) on scratch squads against the recorded-HTTP harness on a loopback port, with routes edited per case: a comment endpoint answering 404, malformed listing rows, a Jira page without `total`, exhausted rate limits, Rich markup and control characters in an error reason, a fuzzy user search, a label spelled like a priority, unused labels and issue types.
- Mutations ran on a copy of HEAD, never in the repository, against `tests/cli/test_source_connectors.py`, `test_source_pull.py`, `test_source_check.py`, `test_source_identities.py`, `test_source_links.py`, `test_source.py` and the connector vocabulary guard in `tests/meta`. Nine were killed: pull requests kept, restricted comments kept, priority not read, Link paging off, `nextPageToken` paging off, `startAt` paging off, the redirect guard off, the Cloud handle taken from the display name, and the exemption row removed. Six survived: four are the test gaps of F8, one is F4's fuzzy match, and one (a missing GitHub `state` read as open instead of closed) only shows that no case feeds a malformed answer (F2).
- `python -X importtime` on an in-process `sq list` in a squad that declares a GitHub source.
- No live tracker was reachable. Every API claim below is against recorded responses or the vendors' documentation, and says which.

## What holds

- **Credentials:**
  - Basic (`user:token`) on `jira@cloud-v3`, Bearer on `jira@dc-v2` and GitHub. The tests pin each header.
  - The redirect guard covers every new connector, because each builds one `HttpClient` on its API root. `github.com`, `www.github.com` and `api.github.com` map to `https://api.github.com`, so a transfer redirect stays on that origin. The mapping was checked by calling it directly, since no test can reach those hosts.
  - The reason taken from an error body is only a `message` or the first `errorMessages` string, with non-printable characters replaced and a 200-character cap. Rich markup and an ESC in it are printed as text, both in `source check` and in the pull's error. A 401 or 403 never carries the reason. No connector puts a credential in a URL. A tracker could echo the token only by writing it into the message itself; it already holds the token, so no exposure path was found.
- **No CLI-start import:** an in-process `sq list` loads no connector, `_http`, `urllib.request` or `http.client`. The `ssl` that loads comes from `asyncio`, as before.
- **The vocabulary exemption is needed and narrow:** without the row, the guard fails on `"priority"` in `_ISSUE_FIELDS`. The row's wording needs an ADR line (F7).
- **GitLab after the `_tracker_probes.py` refactor:** the success-path output is unchanged, and the GitLab check and pull cases pass. Error paths changed, each for the better:
  - a 5xx, unreachable or non-JSON answer on the read probe now prints the host line and the host fix, where it used to print "the filter is not accepted";
  - an HTTP error appends the body's reason;
  - 410 reads as not found;
  - a 403 carrying a wait is retried.
  The handback's "output unchanged" holds only for the success path.
- **Documented API shapes that look right:** Jira Cloud `/search/jql` with `nextPageToken` and `isLast`, `/user?accountId`, `/label` with `values`; Jira DC `/search` paged by the count actually returned, so a capped `maxResults` is followed correctly; `/user?username` and `?key`; GitHub `/issues?filter=all&state=all&labels=`, `pull_request` exclusion, `type.name`, `/dependencies/blocked_by|blocking`, `Link` paging that keeps the path and takes the query.

## The open item: a 404 between listing and detail

It breaks §10 on every connector: GitLab, GitHub and both Jira versions share `_fetch.py`. Worse than the handback says, it stops the unnamed pull of **every** source, not just the one that answered 404 (F1).

## Recommended verdict

Changes requested. F1 to F4 are medium:
- F1 lets one tracker's 404 stop every source;
- F2 reads a malformed answer as closed, gone or out-of-filter without a word;
- F3 copies agent-only service desk comments from Data Center into the squad;
- F4 binds an operator identity to the wrong person.

F7 needs the architect's lines before the decisions it lists are final.

## Not covered

- Real tracker behaviour, as stated above. Unconfirmed: whether adding a GitHub dependency or a Jira link moves the issue's `updated_at` (if not, the ref waits for the issue's next change); whether Cloud still serves the deprecated `GET /rest/api/3/priority` long-term; GitHub App installation tokens, which `GET /issues` and `GET /user` do not accept.
- The converters, beyond what the connector cases run: REV-1282 reviewed them.
- The docs and the CHANGELOG, which are the tech writer's.
- The full suite, per the brief.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1283 add-finding "…" --severity medium`; track with `sq review 1283 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — One issue's 404 between listing and detail stops the pull of every source

<!-- sq:finding:F1:body -->
**Where:** `src/squads/_services/_fetch.py:64-65` (`_with_details` calls `comments` and `links` with no handling), `:84` and `:86`; `src/squads/_services/_pull.py:410`, where `fetch_source` runs for each ready source with no handling, so one exception ends `pull_sources` before any compile.

**Scenario (reproduced, GitHub):** two sources on one GitHub host, `platform` (label `squads`) and `other` (label `other`). On the tracker, `acme/api#12` is listed, but its `/comments` answers 404, as when it is deleted between the listing and the detail fetch. An unnamed `sq source pull` exits 1 with `error: http://…/repos/acme/api/issues/12/comments?per_page=100: not found`, and writes nothing for either source: `other`'s issue, which pulls fine in the control run, is not created. The message names a URL, not the issue or the source.

**Every connector:** the phase is shared. GitLab's notes and links, GitHub's comments, and Jira's `/comment` and `/issue/{id}?fields=issuelinks` all raise `NotFoundError` there. GitHub's dependency 404 is caught, but its comments come first. The same holds for a linked issue that `issue()` found and that vanishes before its details are fetched (`:84`). Any other fetch error of one source, after its probes passed, does the same: a 5xx on page 7 of a listing, or a timeout.

**Rules:**
- ADR-1274 §10: "Per-issue failures never block a source", and an issue not found becomes `gone`.
- §14: an unnamed pull reports a failing source and goes on with the others.

The abort heals on the next run, since the listing no longer names the issue. Until then, one flaky tracker stops every source, and the error does not say which source.

**Fix:**
- **One issue.** In `_with_details`, catch `NotFoundError`. Ask `issue(id, key)` once: `None` means `gone` for a linked issue, and a listed issue no item holds is skipped this run and reported by key. Neither aborts.
- **One source.** In `pull_sources`, catch `SquadsError` around `fetch_source` for an unnamed pull, and report the source the way §14 reports an access failure (`failed`, its line, exit 1) while the others compile. A named pull still stops.
- **Test.** Add one recorded-HTTP row to an existing pull case: a listed issue whose comments answer 404, with the other issue still created.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-04T05:16:14Z] `python-dev` Elias Python:
  - Fixed: a listed issue that vanishes while read is skipped and reported, a linked one reads gone, and a source whose fetch fails is reported failed while the others pull (named pull still stops); cases in test_source_connectors.
- [2026-11-04T05:29:57Z] `reviewer` Paul Reviewer:
  - Verified on 9ac29250: the comments-404 probe now skips the listed issue and pulls the other source; a held issue that 404s reads gone; a listing-phase 500 on one source reports it failed (exit 1) while the other pulls; a named pull still stops. Mutations on both handlers killed.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — A malformed tracker answer is read as closed, gone or out-of-filter

<!-- sq:finding:F2:body -->
The tolerant readers of `_records.py` turn a value of the wrong shape into "absent". In four places, absent then becomes a tracker state that the pull writes and reports as fact.

**Reproduced:**
1. **A missing `state` is closed.** `src/squads/_sources/_github.py:97` reads anything but `"open"` as `closed`. With `state` removed from `acme/api#12`'s listing row, the next pull reports `acme/api#12: closed; TASK-2 stays` and stores `state: closed`.
2. **An unreadable row is gone.** `_github.py:89` and `:113` drop a row without `repository_url`, `number` or `node_id`, without a word. The item holding it is then fetched by ID, and the pull reports `acme/api#13: deleted or no longer readable`, while the issue is in the listing. `sq check` then warns that it is gone. Jira does the same at `_jira.py:145` for a row without `id` or `key`. Against a real tracker the single fetch would usually succeed, and the item would read `out-of-filter` instead; either way the state is invented.
3. **A page without `total` ends the listing.** `_jira.py:60` (`offset_advance`) returns `None` when `total` is not an int. On Data Center, with `total` removed from page 1, the next pull reports `PROJ-46: out-of-filter; TASK-3 stays`. The same reader pages Jira comments, so on Cloud and DC the comments past page 1 drop out, and the pull reports them as deleted on the tracker.

**By trace:**
- `_jira_cloud.py:24` stops when `isLast` is false and no `nextPageToken` is given, with the same result as item 3.
- `records()` (`_records.py:227-233`) drops an element of a listing page that is not an object.
- Jira reads a missing `statusCategory` as `open` (`_jira.py:156`), so a closed item reopens.

**Rule:** §10 gives `closed`, `out-of-filter` and `gone` as findings the pull reports to the adopter. Each one has to rest on what the tracker said, not on what it failed to say.

**Fix:** keep the readers tolerant for optional fields (title, labels, type, author), and be strict where absence changes state:
- **Listing rows.** A listing row without an identity, or with a `state` or `statusCategory` that is neither of the known values, is an `UnexpectedAnswerError` naming the URL. F1's source-level handling then reports the source instead of writing a guess.
- **Paging.** An offset page without an integer `total`, or a token page with `isLast` false and no token, raises the same error instead of ending the listing.
- **Test.** One hostile row in an existing case: a listing row without `state` fails the source and leaves the item's state as stored.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-04T05:16:15Z] `python-dev` Elias Python:
  - Fixed: a row without identity or known state/status category, a non-object row, a page without a total and a token page that ends without isLast now fail the source with a named error; nothing is marked closed, gone or out-of-filter.
- [2026-11-04T05:29:58Z] `reviewer` Paul Reviewer:
  - Verified: a GitHub row without state and a DC page without total now fail the source with the item's stored state kept (probed, and both mutations killed). The message names neither the URL nor the issue, which the report's source prefix makes acceptable.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Jira Data Center pulls agent-only service desk comments

<!-- sq:finding:F3:body -->
**Where:** `src/squads/_sources/_jira.py:209`, shared by both versions: `if record.get("visibility") or record.get("jsdPublic") is False: continue`.

**Scenario (inferred from the API documentation; no Data Center instance was reachable):**
- `jsdPublic` is a field of Jira **Cloud**'s comment resource.
- Jira Data Center's REST v2 comment carries no such field. Jira Service Management on Data Center marks an internal (agent-only) comment through the comment's entity property `sd.public.comment`, with the value `{"internal": true}`, and that property is returned only with `expand=properties`.
- `jira@dc-v2` asks for neither, so every internal service desk comment on a DC instance is pulled.

Once pulled, such a comment is stored in the squad's item files, which are usually committed, and every agent reads it. That is the disclosure the skip exists to prevent: the handback states the rule for both versions.

**The Cloud half has no test:** with the `jsdPublic` test removed (only `visibility` kept), every source case passes, so the half that does exist is unguarded too (mutation `jsd-kept`).

**Fix:**
- In `JiraDcConnector`, request comments with `expand=properties`, and skip a comment whose `sd.public.comment` property has `internal: true`. Keep `visibility` for both versions.
- Move the check behind a method of the version, as `_text` and `_person` are.
- Add one comment with `jsdPublic: false` to the Cloud fixture and one with the DC property to the DC fixture. Assert in the existing pull cases that neither is pulled.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-04T05:16:16Z] `python-dev` Elias Python:
  - Fixed: Data Center asks expand=properties and skips sd.public.comment internal; Cloud keeps jsdPublic; both behind a per-version method with a fixture comment and an assert in each pull case.
- [2026-11-04T05:29:59Z] `reviewer` Paul Reviewer:
  - Verified by code and mutation: DC asks expand=properties and skips sd.public.comment internal; Cloud keeps jsdPublic; each is behind a version method and each switch-off mutation is killed. The DC property shape is still from documentation only.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Jira Cloud handle resolution binds an identity to a fuzzy search hit

<!-- sq:finding:F4:body -->
**Where:** `src/squads/_sources/_jira_cloud.py:68-79` (`resolve_handle`): `chosen = exact if exact else found`, so when no user's display name or email equals the handle, the only user the search returns is taken.

**Scenario (reproduced):** `/rest/api/3/user/search?query=pierre` returns one user, `Pierre Martin` (`712020:mallory`). `sq operator op-pierre update --identities platform=@pierre` succeeds and stores `712020:mallory`. From then on every issue and comment that account writes shows as `op-pierre` (ADR-1274 §3: attribution is computed from `identities`), and `sq source check` raises no flag, since the ID resolves. Jira's search matches on prefixes of the display name and email, so one hit for a short handle is common.

**Rule:** §3 resolves a handle to the immutable ID of that handle. A guess that binds an operator to another person is the impersonation risk REV-1281 F4 raised for the display, reached here through the identity itself.

**The handle shown is the accountId:** the Cloud handle is the accountId (`_person`). `@<accountId>`, the value `sq source check` and the comment display show, does not resolve at all, because `/user/search` does not match on accountId.

**Fix:**
- Accept exactly one exact match on display name or email, and refuse otherwise, listing the candidates' display names and accountIds.
- Resolve `@<accountId>` through `/user?accountId=`.
- No test covers resolution on Jira: with the fuzzy fallback removed, every case passes (mutation `resolve-fuzzy-off`). Add one row to the existing identities case: a prefix-only hit is refused.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-04T05:16:17Z] `python-dev` Elias Python:
  - Fixed: Cloud resolves @accountId by exact lookup, and a display name or email only on one exact match; a prefix-only hit is refused listing candidates; case added.
- [2026-11-04T05:30:00Z] `reviewer` Paul Reviewer:
  - Verified: @pierre with a prefix-only hit is refused listing the candidate; @<accountId> binds through /user?accountId (probed). Restoring the fuzzy fallback is killed.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Probe lines blame the filter or the token for a rate limit or an unlistable value

<!-- sq:finding:F5:body -->
Four probe lines name the wrong cause, and three of them come with a fix that does not apply.

**Reproduced:**
1. **An exhausted rate limit says the filter is wrong.** A GitHub read probe answered `429` (with `Retry-After: 0`), or `403` with `X-RateLimit-Remaining: 0`, prints `FAIL the filter 'squads' is not accepted: … HTTP 429 … API rate limit exceeded`, with `fix: correct filter`.
   - `src/squads/_sources/_http.py:221-233`: once the retries run out, the error is a `StatusError` carrying the 4xx code.
   - `src/squads/_sources/_tracker_probes.py:161-169` classes every 4xx below 500 as a refused filter.
   - This holds for GitLab and Jira too.
   - `_http.py:240` ("kept rate limiting") is unreachable.
2. **A Data Center label is reported missing.** A `maps.fields` key on a label that no in-filter issue carries prints `FAIL … priority or label 'urgent' does not exist on the tracker` and fails the check. `jira@dc-v2` lists no labels (`_jira_dc.py`, `_extra_labels`), so it cannot know that.
3. **An unused GitHub issue type is reported missing.** A `maps.types` key `Bug`, when no in-filter issue currently has that type, prints `FAIL maps.types: 'Bug' is neither a GitHub issue type nor a label`, with "create the label" as the fix. `GitHubProbes.issue_types` (`_github_probes.py:79-81`) reads the types only from in-filter issues, not from the organisation.

**By trace:**
4. **GitHub's secondary limit says the token was refused.** GitHub's secondary limit can answer 403 with neither `Retry-After` nor `X-RateLimit-Remaining: 0`, only a "secondary rate limit" message (`_rate_limited`, `_http.py:131-139`). That is read as `RejectedError`, "did not accept the token", which stops every fetch with a credential fix.

**Fix:**
- Raise a distinct `RateLimitedError` once the retries are exhausted, so the probe can say "rate limited, try later" with no filter fix.
- Treat a GitHub 403 whose message names a rate limit as a rate limit.
- For DC labels, and for GitHub types that cannot be enumerated, emit WARN with the wording "no in-filter issue carries it", or list the organisation's issue types (`GET /orgs/{org}/issue-types`).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-04T05:16:18Z] `python-dev` Elias Python:
  - Fixed: an exhausted 429 or limit-403 (also one whose message names a rate limit) raises RateLimitedError and the probe says to wait; an unconfirmable DC label or GitHub type is a warning, not 'does not exist'. The secondary-limit message path is untested (backoff sleeps).
- [2026-11-04T05:30:01Z] `reviewer` Paul Reviewer:
  - Verified: an exhausted 403 or 429 now prints the rate-limit line and the wait fix; a DC label and a GitHub issue type no in-filter issue carries are warnings (probed). The rate-limit mutation is killed; the secondary-limit message path is by code.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A Jira label spelled like a priority overrides the priority field

<!-- sq:finding:F6:body -->
**Where:** `src/squads/_sources/_jira.py:161` appends the priority name to `Issue.labels`, and `src/squads/_services/_pull.py:155-163` (`mapped_fields`) reads every badge field's map from that one bag.

**Scenario (reproduced, Jira Cloud):** `PROJ-46` has Jira priority `Low` and the label `High`; the source maps `maps.fields.priority = { High = "high" }`. The pull sets `TASK-3`'s priority to `high`. The tracker's own priority field is overridden by a label anyone can type. With both `High` and `Low` mapped (by trace), the pull reports "priority left alone, its labels map to [high, low]" and leaves it stale. The same bag feeds `maps.types` and every other badge field, so a priority name can type an issue or set a severity badge.

This is the developer's "field maps key on a label or the priority name" decision, filed separately from F7 because it is a defect whatever the ADR says.

**Fix:**
- Keep the priority out of `labels`. Carry it as its own value, for example `Issue.fields = {"priority": "High"}` on the tracker side.
- Give `maps.fields` an addressing rule that tells them apart: a key `priority:High` for the tracker's priority field and a bare key for a label, or a per-field `from = "priority"`.
- The architect picks the spelling (F7 b). The probes' `known_labels` then checks priority keys against `/priority` only.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-04T05:16:19Z] `python-dev` Elias Python:
  - Fixed: maps are keyed by side (maps.types.<side>, maps.fields.<field>.<side>); Issue.sides carries type and priority apart from labels; sides declared per connector version and refused at load; differing sides set nothing.
- [2026-11-04T05:30:02Z] `reviewer` Paul Reviewer:
  - Verified: priority Low plus label High no longer sets high (probed); maps read one side at a time. The labels-side half has no test, filed under F11.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — ADR-1274 owes lines for seven connector decisions

<!-- sq:finding:F7:body -->
The developer asked for these decisions to be confirmed (TASK-1278, comment e7c9d6a). ADR-1274 says nothing on any of them, and each binds adopters' `sources.toml`. My view on each, for @architect to rule and record:

**a. Jira link keys are the directional phrase (`blocks`, `is blocked by`).**
- Sound. It is the only key that carries direction: a link read from its inward side maps from that side, so `"is blocked by" = "depends-on"` gives `B depends-on A`, which is correct.
- The "inward loss" is by design. With the default `blocks = blocks`, the ref is made from the outward issue, and both ends are pulled whenever the ref can exist.
- To record: phrases are admin-edited strings, and `maps.links` keys are checked against `/issueLinkType` per instance.
- The direction has no test (F8).

**b. Jira priority shares the label namespace.** Not sound: see F6 (reproduced). Rule a spelling that keeps the tracker field apart from labels.

**c. The Jira Cloud handle is the accountId.**
- Sound: Cloud has no username, and the accountId is the only stable public handle. The display name stays the readable part.
- To record: `@<accountId>` must then resolve (F4).

**d. Restricted comments are not pulled** (`visibility`, and agent-only service desk comments).
- Sound: the squad's files are readable by everyone with the repository, often more people than the restriction allows.
- To record: a comment pulled and later restricted is then "deleted on the tracker" under §10. It is reported and stays in the squad, and no command can remove it (§6).
- On Data Center the skip is incomplete (F3).

**e. A Jira issue's author is its `reporter`, falling back to `creator`** (`_jira.py:149`). This one is not in the handback's list.
- The reporter is an editable field. A user with the Modify Reporter permission, or a service desk agent raising a request on someone's behalf, sets it to anyone, and the next pull rewrites `source.author_id`.
- `creator` is immutable, which is what §1's "author's immutable user ID" suggests, and what GitLab and GitHub use.
- Choose one and record it. If the reporter stays, say so, since attribution follows it (§3).

**f. A Jira source needs a `filter`; GitHub and GitLab sources may omit it.**
- The Jira refusal comes from the access probe at run time, not from load (§8 lists load-time validation).
- An empty GitHub filter lists `/issues?filter=all`: every issue the token can see in every repository and organisation it belongs to, private ones included, all copied into a committed squad.
- Rule whether `filter` is required for every connector, and validated at load.

**g. The exemption row's wording.**
- §14 allows "a module-level tuple or frozenset of string literals naming one tracker API enum".
- `_ISSUE_FIELDS` in `_jira.py` is the list of Jira issue-object field names, not an enum of values. The guard does need it: removing the row fails the guard on `"priority"`.
- Widen §14's wording to "one fixed set of tracker API names (an enum's values, or an object's field names)", so the next reviewer is not asked to stretch it.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-04T05:00:42Z] `architect` Robert Architect:
  - Recorded in ADR-1274 sections 8, 9 and 14 (2026-11-04): (a) directional link phrases, sound; (b) maps keyed by tracker side, labels never stand in for a field; (c) Cloud handle is the accountId; (d) restricted and agent-only comments skipped on both versions; (e) author is the immutable creator; (f) filter required at load for every source; (g) the exemption covers any fixed set of tracker API names. Code for b to f briefed to @python-dev on TASK-1278.
- [2026-11-04T05:30:03Z] `reviewer` Paul Reviewer:
  - Verified: ADR-1274 section 14 records all seven (a to g), and the code follows b, e and f (creator, sides, filter required at load; the last killed by mutation). One wording mismatch with F5's warnings is filed as F12.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Four decided behaviours have no test, and three asserts are substrings

<!-- sq:finding:F8:body -->
The nine cases are CLI-surface, carry `covers` markers and use the harness; nine mutations were killed (review body). Four survived, each on a behaviour the handback names as decided:

- **Inward link direction** (`inward-as-outward`): with every link labelled by its outward phrase, the inward side of `PROJ-45 blocks PROJ-46` gives the reversed ref `TASK-3 blocks TASK-2`, and every case passes. The Jira cases assert only the outward issue's refs. Fix: assert `second["refs"] == []` in the Cloud pull case, as the GitHub case already does.
- **`jsdPublic`** (`jsd-kept`): see F3.
- **GitHub's 403 rate limit** (`rate403-off`): `_rate_limited` returning false for 403 passes everything. A one-shot harness answer cannot be retried into success, so no cheap case exists; leave it untested, or give the harness a `times` field on a route.
- **Enterprise without dependencies** (`gh-deps-404-raises`): the "404 on older Enterprise means no links" tolerance is untested. One `dependencies/*` route answering 404 in the transfer case covers it.

**Substring assertions (ADR-1172):**
- `tests/cli/test_source_connectors.py`: `"see TASK-3 and acme/other#4." in first["display"]["body"]`, `"Steps: see **TASK-3** and the runbook." in first["display"]["body"]`, and the version case's `… (known: cloud-v3, dc-v2)") in " ".join(result.output.split())`.
- Compare the display body's line after the provenance header exactly, and the version refusal's whole message.

No new case is needed: each item above is a row or an assertion in an existing case.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-11-04T05:16:20Z] `python-dev` Elias Python:
  - Fixed: Cloud asserts the inward side makes no ref, jsdPublic and DC property comments are excluded, the Enterprise 404 on dependencies is covered, and substring asserts are whole comparisons. 403 rate limit stays untested.
- [2026-11-04T05:30:04Z] `reviewer` Paul Reviewer:
  - Verified: inward direction, jsdPublic and the Enterprise dependencies 404 are now pinned (each mutation killed), and the three named substring asserts are whole comparisons. New substring asserts in the added cases are filed as F11; the 403 rate limit stays untested, as stated.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Cleanup: Jira updated_at offset, a repos owner, ghe.com hosts

<!-- sq:finding:F9:body -->
Small items, grouped.

- **Jira `updated_at` is not ISO UTC.** ADR-1274 §1 says the record's `updated_at` is ISO UTC. Jira gives `2026-11-02T09:00:00.000+0000`, in the account's own timezone, and the connector stores it as given (`_jira.py:157`). The pull only tests "differs", so nothing breaks, but the record is not what §1 states. A change to the service account's timezone also refetches every issue once.
  - Fix: normalise to UTC in the connector, keeping the milliseconds so two updates within one second still differ. Or amend §1 to say "as the tracker gives it".
- **`_repository` misreads an owner named `repos`.** `_github.py:40` uses `rpartition("/repos/")`, so `…/repos/repos/x` reads as `x` and the key loses its owner. Use `partition`.
- **GitHub Enterprise Cloud with data residency is not mapped.** `_roots` maps `https://acme.ghe.com` to `https://acme.ghe.com/api/v3`. That instance's API is `https://api.acme.ghe.com`.
  - Fix: map the `*.ghe.com` hosts. Or state in the adopter docs that the API root must be given for them.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-11-04T05:16:21Z] `python-dev` Elias Python:
  - Fixed: Jira timestamps are ISO UTC with milliseconds, an owner named repos keeps its key, *.ghe.com maps to api.<host>.
- [2026-11-04T05:30:05Z] `reviewer` Paul Reviewer:
  - Verified: Jira timestamps are ISO UTC with milliseconds, an owner named repos keeps its key, and *.ghe.com maps to api.<host> (checked directly; the first two mutations killed).
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A map with no side fails with a raw pydantic dump

<!-- sq:finding:F10:body -->
**Where:** `src/squads/_sources/_spec.py` (`SourceMaps.types`, `SourceMaps.fields`, now keyed by side), as rendered by `describe_spec_error` (`src/squads/_specmerge.py:566`). That function folds only unknown keys and returns any other pydantic error verbatim.

**Scenario (reproduced):** the likeliest mistake under the side-keyed grammar is a map with no side, such as `[sources.platform.maps.types]` with `squads = "task"`, or `[sources.platform.maps.fields.priority]` with `High = "high"`. It is also the grammar `docs/sources.md` still teaches (lines 35-56 and 191-195). Every source command then fails with pydantic's dump:
- `maps.types.squads  Input should be a valid dictionary [type=dict_type, input_value='task', input_type=str]`
- `For further information visit https://errors.pydantic.dev/2.14/v/dict_type`

`sq check` prints the same text. The dump names neither the missing side nor the sides the connector has, while the loader's own side check, for a side that does exist in the grammar but not on the connector, gives exactly that: `maps name the side 'priority', which the connector does not have (known: labels, type)`.

**Rule:** ADR-1274 §8 says a load failure names the source, the map and the value.

**Fix:**
- Before the model validates, check that each `maps.types` value and each `maps.fields.<field>` value is a table.
- When it is not, refuse it naming the source, the map, the key, and the connector's sides: "`maps.types.squads` is a value, not a side: write it under `maps.types.labels` or `maps.types.type`".
- Add one row to the existing filter-required load case.
- The docs belong to TASK-1279; flagged to the tech writer.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-04T05:34:58Z] `python-dev` Elias Python:
  - Fixed: a map entry written as a value where a side is due is refused at load naming the source, the entry and the connector's sides; row added to the load case, falsified.
- [2026-11-04T05:38:36Z] `reviewer` Paul Reviewer:
  - Verified on 03af4bb6: a map with no side is refused naming the map, the key and the connector's sides (probed on GitHub and Jira; switching the check off fails the load case). Nit, not blocking: the hint is cut at the last dot, so a key such as v1.2 would read 'write it under maps.types.v1.<side>'; build it from the map path instead of rsplit.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — New cases bring substring asserts, and two side rules have no test

<!-- sq:finding:F11:body -->
F8 removed the three substring asserts it named. The cases added for F1, F2 and F4 bring four new ones, in `tests/cli/test_source_connectors.py`:

- `:375`: `"HTTP 500" in reports["platform"]["left_out"]`
- `:392` and `:413`: `report["left_out"].endswith(...)`
- `:435`: the refusal of the fuzzy handle, compared after a whitespace collapse with `in`

Each one would pass if the message gained a wrong cause or fix in front of the asserted tail. That is exactly what F5 fixed, so these asserts would not have caught it.

**Rule:** ADR-1172. The file already uses the whole-comparison pattern: replace `tracker.base_url` with a constant, then compare the whole string.

**Fix:**
- Compare `left_out` whole, after the base URL is replaced.
- Compare the fuzzy-handle refusal whole, as `test_a_source_without_a_filter_fails_at_load_naming_the_source` does.
- No new case.

**Two side rules have no test:** mutations run on a copy of 9ac29250 against the source cases in `tests/cli` and `tests/check`.
- Putting the priority back into `labels` (`_jira.py:190`) passes everything, because no Jira case reads the `labels` side. So the F6 rule "a label never stands in for a field" is unguarded. Fix: in the existing Jira Cloud pull case, add a `labels` side entry spelled like a priority, such as `High = "low"`, on an issue whose priority is `High`, with no such label, and assert the badge is `high`: the label side finds nothing. With the priority leaking into the labels, the two sides would conflict and leave the badge unset.
- Turning off the undeclared-side refusal (`_loader.py:130`) passes everything. Fix: one row in the filter-required load case, for a GitLab source with a `priority` side.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-11-04T05:34:59Z] `python-dev` Elias Python:
  - Fixed: the four substring asserts compare whole; the Cloud pull case maps a labels-side High and the load case an undeclared side; priority-in-labels and the side refusal each fail a test.
- [2026-11-04T05:38:37Z] `reviewer` Paul Reviewer:
  - Verified: the four asserts are whole comparisons, and the labels-side and undeclared-side rules are now pinned (both mutations killed).
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — ADR-1274 calls an unconfirmable map key blocking; the probe warns

<!-- sq:finding:F12:body -->
**Where:** ADR-1274 §14, "Tracker API enums in connector modules", last bullet: each `maps.types` and `maps.fields` key is checked against its own side, and "a key its side does not hold is blocking".

**The code** (F5's fix, `src/squads/_sources/_tracker_probes.py`, `_missing`) fails only when the side's list is complete. Where the tracker cannot list the side, it warns: Jira Data Center labels, and GitHub issue types, which are read from the in-filter issues only. The warning reads "… is carried by no in-filter issue, so it cannot be confirmed among the tracker's labels" (probed). The code is right, since squads cannot know the value is absent. The record says otherwise.

**Fix:** amend the bullet so that a key its side does not hold is blocking when the connector can list that side, and a warning naming the unconfirmed value when it cannot. Name the two cases: DC labels and GitHub issue types.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-11-04T05:32:09Z] `architect` Robert Architect:
  - Recorded in ADR-1274 section 14 (2026-11-04): a map key missing from a listable side is blocking; on a side the tracker cannot list, a key no in-filter issue carries is a warning.
- [2026-11-04T05:38:38Z] `reviewer` Paul Reviewer:
  - Verified: ADR-1274 section 14 now makes an unheld key blocking only for a listable side, and a warning for DC labels and GitHub issue types, matching the probe.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T04:58:09Z, edited 2026-11-04T04:58:34Z] `reviewer` Paul Reviewer:
  - Verdict recommended: ChangesRequested. Nine findings, four medium, all Open. Each was reproduced on a scratch squad unless its body says by trace; F3's Data Center half is inferred from the API documentation.
  - @python-dev: F1 to F6, F8 and F9. F1 (one 404 or one failing source stops every source's unnamed pull) answers the open item of your handback; F2 (malformed answers read as closed, gone or out-of-filter) shares its fix.
  - @architect: F7 rules the seven connector decisions; F6's fix waits on its point b for the spelling.
- [2026-11-04T05:31:03Z] `reviewer` Paul Reviewer:
  - - Re-review of 9ac29250: F1 to F9 are Verified, each against the scratch probes and 15 mutations (13 killed; the 2 survivors are in F11).
    - The side-keyed maps: GitLab pulls and checks with type and labels sides, scoped-label coverage still reports, and the loader refuses an undeclared side (priority on GitLab) and a missing filter, naming the source. The old flat grammar fails loudly, never misread, but as a pydantic dump (F10).
    - Three new low findings: F10 and F11 for @python-dev, and F12 (an ADR line contradicting F5's warnings) for @architect.
    - Recommended verdict: Approved once F10 to F12 land; nothing medium or higher is open.
    - @tech-writer: docs/sources.md (lines 35-56 and 191-195) still teaches the flat map grammar; the sided form is in ADR-1274 section 14. That is TASK-1279's.
- [2026-11-04T05:38:39Z] `reviewer` Paul Reviewer:
  - All twelve findings Verified. Recommended verdict: Approved (the approver makes the transition).
- [2026-11-04T05:38:54Z] `manager` Catherine Manager:
  - Approved on the reviewer's recommendation: all twelve findings Verified; full suite 2117 passed. The dotted-key hint in the F10 message is a known nit, left as is.
<!-- sq:discussion:end -->
