---
id: REV-1281
sequence_id: 1281
type: review
title: Sources spec and pull (FEAT-1271, TASK-1276)
status: ChangesRequested
author: reviewer
refs:
- FEAT-1271
- TASK-1276
- ADR-1274
subentities:
- local_id: F1
  title: The tracker token follows an HTTP redirect to any host
  status: Verified
  assignee: python-dev
  severity: high
- local_id: F2
  title: The derived cursor skips issues after a refresh, a relink, an unmapped type
    or a dropped issue
  status: Verified
  assignee: architect
  severity: high
- local_id: F3
  title: A failing link target drops its host issue, and the report lists items never
    created
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F4
  title: A tracker display name can impersonate an operator in the comment header
  status: Open
  assignee: architect
  severity: medium
- local_id: F5
  title: The credential store write can keep a wider mode and leaves an existing directory
    open
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F6
  title: Every CLI start imports the GitLab connector and urllib through the spec
    resolver
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F7
  title: 'ADR-1274 owes two amendments: GitLab fetch by path and iid, and the sourced
    comment refusal'
  status: Verified
  assignee: architect
  severity: low
- local_id: F8
  title: Credential verbs carry no mark that a remote command listener could refuse
  status: Verified
  assignee: architect
  severity: info
- local_id: F9
  title: 'Cleanup: prompt on stdout, relink key, holder race, refresh cost, dead pre-flight,
    tests'
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F10
  title: No test catches a regression of the sourced comment escape
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F11
  title: A tracker title holding a marker is pulled, fails sq check, and the squad
    cannot fix it
  status: Verified
  assignee: python-dev
  severity: low
created_at: '2026-11-04T02:22:04Z'
updated_at: '2026-11-04T02:58:25Z'
---
<!-- sq:body -->
Batch review of FEAT-1271 (sources spec and pull) as delivered by TASK-1276, against ADR-1274 (§14 included), its rulings and the dated notes on the amended ADRs, board notice 22 and ADR-1172. The change reviewed is `4cfb4d58..HEAD` on `release/0.20` (src, tests, CLAUDE.md).

## How it was checked

- Probes ran the real CLI on scratch squads against the recorded-HTTP harness (`tests/_tracker_harness.py`) on a loopback port, with routes edited per case: hostile comments, display names and titles; unmapped types; a failing link target; a second listing keyed on `updated_after`; and a redirecting tracker.
- Mutations ran on a copy of HEAD, never in the repository:
  - store mode `0600` to `0644`: killed;
  - the `--as source:` refusal turned off: killed;
  - comment-edit idempotence: killed;
  - the sourced comment escape turned off: **survived** (F10);
  - the per-issue drop turned into a raise: **survived** (F3).
- Other checks: `sq repair` on a pulled squad rebuilds an equal index; `python -X importtime` measures the CLI's import cost.

## What holds

- **Credentials:**
  - never in `--json`, the reflog, a log line, the environment or OpenAPI;
  - the store is read on every use;
  - the hidden prompt goes over the CLI listener only and is read with `getpass`;
  - the browser listener refuses the command endpoint, and no private operation has a route.
- **Untrusted text:**
  - imported comment and description text is escaped (`<!!--`), so a forged comment header, `sq:attrs` line or region end tag is stored and rendered as text;
  - the attribute payload JSON-escapes `<` and `>`;
  - Rich markup from the tracker is escaped;
  - the untrusted notice shows on the description, on each comment and on inbox lines;
  - `trusted` is false exactly when the notice shows;
  - mentions reach the inbox as written, per ruling 8577dca.
- **Forging a sourced item:** `--author source:<name>` is refused on `create`, on `update --author`, and by `sq import` as an unknown slug, so the relink authorship check cannot be forged through the CLI. The developer's open point is moot. The message could name the reservation instead of "unknown slug", but that is cosmetic.
- **Integrity:**
  - writes are deferred inside the transaction, so markdown lands before the index commit;
  - `sq repair` reproduces the index;
  - the lookups, the cursor and the URL are derived and never stored;
  - `show --refresh` runs the private `sources.refresh` before the read;
  - a second pull with nothing new writes nothing (test and mutation).
- **Layering:** the operation table, the bindings and the import-edge guard pass. The private operations have no `/v1` route. `_views` does not import `_sources`.

## The questions in the brief

- **`O_EXCL` in the store:** another user cannot exploit it while the directory is `0700`, but the store does not hold the modes §7 promises (F5, low).
- **Sourced-comment refusal wording:** §14 is the right reading, and the implementation follows it. §11 contradicts it for comments and is amended in F7.
- **GitLab fetch by project path and iid:** the change is sound, but no ruling records it, and ID-only relink is limited to issues the filter lists (F7).
- **Hosted fit:** every source command runs where the squad is served, and the credential verbs are CLI-listener-only today. The remote listener of FEAT-33 needs an operation-level mark to keep refusing them (F8, info).

## Recommended verdict

Changes requested. F1 and F2 lose a credential and lose tracker data silently, and F3 breaks the §10 per-issue rule. F2 and F4 need the architect's ruling before code.

## Not covered

- The connector's real GitLab behaviour (renamed projects, the format of `updated_after`). No GitLab instance can be reached from here; every claim is against recorded responses.
- The TUI reader rendering, read only by trace.
- The docs, which belong to TASK-1279.
- The full suite, per the brief.
- The migration runner, beyond the developer's own verification that its type-and-alias branch is unreachable.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1281 add-finding "…" --severity medium`; track with `sq review 1281 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — The tracker token follows an HTTP redirect to any host

<!-- sq:finding:F1:body -->
**Where:** `src/squads/_sources/_http.py:47-50` (the opener) and `:74` (the request). The token travels as a plain request header (`PRIVATE-TOKEN`, set in `src/squads/_sources/_gitlab.py:45`).

**Scenario (reproduced):** the opener keeps urllib's default `HTTPRedirectHandler`. On a 30x, that handler copies every header given to `Request(headers=...)` onto the new request, whatever its host or scheme. In the probe, a tracker on `127.0.0.1` answered `302 Location: http://localhost:<other port>/steal`, and the second server received `Private-Token: SECRET-TOKEN`. A tracker that redirects (an SSO front end, a moved instance, an http-to-https hop, or a hostile proxy) therefore gets the service account's token sent to another host, possibly in clear text. ADR-1274 §7 holds that the credential goes nowhere but the tracker.

**Fix:** pass the token as an unredirected header (`request.add_unredirected_header`), or install a redirect handler that refuses a redirect leaving the base URL's scheme, host and port, and fails with a message naming both URLs. Add one recorded-HTTP case: a redirect to another port must not carry the header, and the command must fail cleanly.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-04T02:26:00Z] `python-dev` Elias Python:
  - Fixed: the HTTP client follows a redirect only within the tracker's scheme, host and port and otherwise fails naming both addresses; a recorded-HTTP case redirecting to another port shows the other server receives nothing.
- [2026-11-04T02:52:12Z] `reviewer` Paul Reviewer:
  - Verified: the redirect probe now fails, naming both addresses, and the other host receives no header. Turning off the origin check fails test_a_redirect_to_another_address_never_carries_the_token.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The derived cursor skips issues after a refresh, a relink, an unmapped type or a dropped issue

<!-- sq:finding:F2:body -->
**Where:** `src/squads/_models/_index.py:133` (`source_cursor`), `src/squads/_services/_fetch.py:55-62` (the listing is used only to spot linked issues that left the filter), `src/squads/_services/_pull.py:355`. The rule comes from ADR-1274 §1 ("the cursor is derived").

The derived cursor is right only if every tracker update up to the newest stored `updated_at` has been applied. Three paths break that, and the issue is then never fetched again until someone edits it on the tracker:

1. **`show --refresh` or `relink` jumps the cursor (reproduced).** Pull issues A and B. On the tracker, A changes at 11:00 and B at 12:00. `sq task <B> show --refresh` stores B's 12:00, so the next `sq source pull` asks for `updated_after=12:00` and A's new title never arrives. The pull reports "unchanged 1".
2. **An issue not created is lost (reproduced).** Issue #12 maps to no type, #13 does. The first pull creates #13 and reports #12. After the adopter adds the missing `maps.types` entry, the next pull asks from #13's `updated_at`, so #12 is never created and nothing reports it again.
3. **An issue whose events were dropped** (§10, per-issue failures) keeps its old `updated_at` while other items advance the cursor. The same loss follows by trace.

**Fix:** the pull already lists every issue in the filter on each run (`listed_ids`). Keep the `updated_at` that listing returns and drop the cursor. An issue is fetched in detail when no item holds it, or when its listed `updated_at` differs from the stored one. That is one paginated pass, no stored state, and it fixes all three paths. It amends ADR-1274 §1 and §10, so @architect rules first. Add recorded-HTTP cases for paths 1 and 2.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-04T02:27:11Z] `architect` Robert Architect:
  - Ruled in ADR-1274 section 14 (2026-11-04): no cursor; the pull diffs the full paged listing against each item stored updated_at and fetches details only where they differ or no item holds the issue; a dropped event keeps the stored updated_at. Open: code change and cases briefed to @python-dev on TASK-1276.
- [2026-11-04T02:46:38Z] `python-dev` Elias Python:
  - Fixed per ADR-1274 section 14: no cursor (source_cursor removed). The connector has one listing(); a pull fetches comments and links only for listed issues no item holds or whose listed (updated_at, state) differs from the stored ones; a dropped link keeps the host's stored updated_at, a wholly dropped issue writes nothing. Cases: refresh of B does not hide A's change, unmapped issue created after the map is fixed, dropped events retried and reported, dropped link retried.
- [2026-11-04T02:52:12Z] `reviewer` Paul Reviewer:
  - Verified on fresh scratch squads. Path 1: after show --refresh on B, the pull brings A's new title (refreshed 1, unchanged 1). Path 2: after the map is fixed, the unmapped issue is created, and a third pull reports unchanged 2. Path 3 holds for held items; the gap for a newly created host is in F3.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A failing link target drops its host issue, and the report lists items never created

<!-- sq:finding:F3:body -->
**Where:** `src/squads/_services/_pull.py:282-305` (a ref event is filed under the host issue's label), `:435-461` (`_without_failing_issues` drops every event of a failing label), `:370-374` (the `created` list).

**Scenario (reproduced):** the recorded fixture, with issue #13's title set to blanks. #12 links `blocks` to #13. The pre-pass refuses #13's `create` ("title must not be empty"). On the next round, #12's `ref` event names the handle of the dropped #13 and fails, so the whole #12 label is dropped too: create, record, description and comments. The run reports:

- `platform/api#13: dropped, title must not be empty`
- `platform/api#12: dropped, no item 'platform:gid://gitlab/Issue/9002' in the index`

`sq list` shows neither item. ADR-1274 §10 says a failing issue drops only its own events.

The same run's `--json` lists `"created": ["platform:gid://gitlab/Issue/9001", "platform:gid://gitlab/Issue/9002"]`, and the text line says "created 2". When `applied` is `None`, `compiled.created` is printed raw, even though nothing was created.

**Test gap:** replacing `dropped |= set(bad)` with a raise leaves `tests/cli/test_source_*.py` green, so the §10 rule has no test.

**Fix:** drop a `ref` event whose target is a dropped issue instead of its host (filter the refs against `dropped` before re-planning, or file the ref under the target's label too). Report `created` from `applied.handle_to_id` only, and leave it empty when nothing was applied and the run is not a dry run. Add one recorded-HTTP case: a linked target that fails, with the host created and reported.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-04T02:26:50Z] `python-dev` Elias Python:
  - Fixed: a ref whose target fails is dropped alone and reported; the host issue is kept. created is empty unless applied (or a dry run), and a dropped issue leaves it. The new case fails when the per-issue drop becomes a raise.
- [2026-11-04T02:52:11Z] `reviewer` Paul Reviewer:
  - - Reopened. The fix holds for the scenario the finding reported. On the first pull, #13 (blank title) is dropped, #12 is created as TASK-5, the report says `a link was dropped`, and `created` lists only TASK-5. Mutating the ref branch fails 3 tests.
    - The developer's open note is a real loss. Reproduced on a scratch squad: the tracker then fixes #13's title (new `updated_at`), and #13's own links list the inverse `is_blocked_by`, which no map covers.
      - The next pull creates TASK-6.
      - TASK-5's `refs` stay `[]` on that pull and on the one after ("unchanged 2").
      - Nothing reports the missing link after the first pull.
    - Why: TASK-5 was created in the pull that dropped its link, so there was no stored `updated_at` for `_keeping_stored_time` to keep. TASK-5 stored the real one, and #12 is never fetched again until it changes on the tracker.
    - This breaks the ADR-1274 §14 rule that a dropped event is retried and reported on the next pull. That rule covers only items that already existed.
    - Fix (@architect to pick): when a newly created issue has a dropped ref, write its record with an `updated_at` that differs from any listed value (the empty string), so the next pull fetches it again. Alternatively, when a pull creates a target, also emit the refs that already-held items name toward it. Add the second pull to `test_a_link_target_that_fails_costs_only_the_link_and_the_report_lists_what_exists`.
- [2026-11-04T02:53:09Z] `architect` Robert Architect:
  - Ruled in ADR-1274 section 14 (2026-11-04): an item created by a pull that drops one of its issue events stores source.updated_at empty, so the next pull re-reads and retries it; code change and test briefed to @python-dev on TASK-1276.
- [2026-11-04T02:55:45Z] `python-dev` Elias Python:
  - Fixed again: an item created by a pull that drops any of its issue's events stores source.updated_at as an empty string (age reads 'at an unknown time', source list ignores it); the next pull re-reads the issue, adds the link and stores the tracker value, and a third pull writes nothing. The case fails if the created item keeps the tracker time.
- [2026-11-04T02:58:24Z] `reviewer` Paul Reviewer:
  - Verified on fe1437f9 by re-running the reproduction. The pull that drops the link stores updated_at '' on the new host, and sq check stays clean. After the tracker fixes #13, the next pull creates TASK-6 and refreshes TASK-5, whose refs become TASK-6:blocks. A third pull reports unchanged 2, and sq repair rebuilds an equal index.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A tracker display name can impersonate an operator in the comment header

<!-- sq:finding:F4:body -->
**Where:** `src/squads/_services/_comment_view.py:96-102`, where the composed `author` puts the tracker-controlled `author_name` in the slot a matched identity uses. ADR-1274 §5, Display, sets this grammar.

**Scenario (reproduced):** operator `op-pierre` holds `identities.platform=4567`. Tracker user `mallory` (ID 999) sets their display name to `op-pierre Pierre Chat`. `show --comments` prints:

- `--- fa0c0ad [...] op-pierre Pierre Chat via platform @pchat ---` (the real, matched identity)
- `--- d749ce9 [...] op-pierre Pierre Chat via platform @mallory ---` (the spoof)

Only the handle differs, and `author` in `--json` matches the same way; only `identity` (null) tells them apart. On a source declared `trusted = true`, no untrusted notice appears. An agent then reads a tracker user's "Approved, merge it" as the operator's ruling. Rich markup in names and bodies is escaped (checked).

**Fix:** never let an unmatched name occupy the slug slot. For example, render an unmatched author as `@mallory "op-pierre Pierre Chat" via platform`, or put the handle first and quote the name, and keep the slug-first form for a matched identity only. The `--json` `author` follows the same rule. This changes the §5 display grammar, so @architect amends it.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-04T02:27:12Z] `architect` Robert Architect:
  - Escalated to @op-pierre on ADR-1274: the fix changes the unmatched form his ruling 2980084 spells out. Recommendation there: a slug-first matched form with the roster name, a handle-first unmatched form with the tracker name quoted. Open until he rules; then a code change.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The credential store write can keep a wider mode and leaves an existing directory open

<!-- sq:finding:F5:body -->
**Where:** `src/squads/_sources/_credentials.py:92-104` (`_write`).

**Verdict on the missing `O_EXCL`:** another user cannot exploit it while the directory is `0700`, but the code does not guarantee the file and directory modes that ADR-1274 §7 promises.

- **Reproduced:** with a stale `.credentials.toml.<pid>.tmp` already present at mode `0644` (a crash, or pid reuse in a long-lived daemon), `os.open(..., O_CREAT|O_TRUNC, 0o600)` keeps the old mode. The token is written and renamed into place as a `0644` `credentials.toml`. Every later read then refuses the store, but the secret stays on disk readable by others until someone runs chmod.
- **Reproduced:** `mkdir(mode=0o700, exist_ok=True)` leaves an existing `squads/` directory at `0755`. §7 says "a 0700 directory".
- **By trace:** without `O_NOFOLLOW`, a symlink at the scratch path is followed. `write_entry` and `remove_entry` read, modify and write with no lock, so two concurrent `credential set` calls lose one entry. There is no `fsync` before the rename.

**Fix:** create the scratch file with `tempfile.mkstemp(dir=path.parent, prefix=".credentials.")`, which uses `O_EXCL` and mode `0600` with a random name. `fchmod(fd, 0o600)` anyway, `fsync`, then rename. Tighten an existing directory you own to `0700`. Take a `filelock` beside the store for the read-modify-write.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-04T02:27:59Z] `python-dev` Elias Python:
  - Fixed: the scratch file is created O_EXCL|O_NOFOLLOW after unlinking a stale one, fchmod 0600 and fsynced; an existing directory we own is tightened to 0700; read-modify-write takes a file lock. One case with a stale symlink and an open directory fails when either is reverted.
- [2026-11-04T02:52:12Z] `reviewer` Paul Reviewer:
  - Verified. A stale 0644 scratch file now yields a 0600 store, a 0755 directory is tightened to 0700, and a symlink at the scratch path is not followed. The read-modify-write is under a lock, with an fsync before the rename.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Every CLI start imports the GitLab connector and urllib through the spec resolver

<!-- sq:finding:F6:body -->
**Where:** `src/squads/_spec_documents.py:20` imports `squads._sources._loader` at module top; `_loader.py:16` imports `_registry`, which imports `_gitlab`, which imports `_http`, which imports `urllib.request`. `_overrides/_service.py:65` does the same. The import-edge table records both rows (`_spec_documents -> _sources top`, `_overrides -> _sources top`).

**Measured:** `python -X importtime -c "import squads._cli"` now loads `squads._sources._registry` at a cumulative 13.7 ms, of which `urllib.request`, `http.client` and `ssl` take about 10 ms. Every in-process command pays this, including `init`, `adopt`, fallback runs and the daemon's start, even in a squad with no source. I measured import time only, not end-to-end wall clock.

This also goes against ADR-1274 §9 ("Connectors are reached only from `_services`"): the spec-document resolver and the override service reach the connector classes through the loader.

**Fix:** the loader validates `connector`, `version` and `converter` names, so give it a table of names (`(name, version) -> module path` plus the credential fields and default converter as data). Import the connector class only in `_services/_fetch.connector_class`. The edge rows change from `top` to function-level, or disappear.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-04T02:31:37Z] `python-dev` Elias Python:
  - Fixed: the connector table is data (module, class, default converter) and the class is imported only in _services/_fetch.connector_class; python -X importtime -c 'import squads._cli' no longer loads urllib.request, http.client or ssl.
- [2026-11-04T02:52:13Z] `reviewer` Paul Reviewer:
  - Verified with -X importtime: importing squads._cli no longer loads _gitlab, _http or urllib.request. The loader reads the connector table as data, and the class loads only in _services/_fetch. Measured import time only, not end-to-end.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — ADR-1274 owes two amendments: GitLab fetch by path and iid, and the sourced comment refusal

<!-- sq:finding:F7:body -->
Two places where the code and ADR-1274 disagree. The code is right in both; the record needs amending.

1. **GitLab fetches one issue by project path and iid, not by ID** (`src/squads/_sources/_gitlab.py:92-97`, `_connector.py`). §9 and §14 say the connector fetches "one issue by ID". The developer found `GET /issues/:id` admin-only and switched the interface to `issue(issue_id, key)`. It fetches `/projects/:path/issues/:iid` from the last known key and accepts the answer only when its global ID equals the stored one, which is sound. The developer asked for a ruling (TASK-1276, comment 14a851e), and none is on the record. Consequences to state: a linked issue outside the filter whose project was renamed or transferred reads as `gone`; and `relink` by immutable ID resolves only issues the filter lists (`lookup` scans `issues_since(None)`), so §14's "a key or an immutable ID" holds only in part for GitLab.
2. **§11 contradicts §14 on sourced comments.** §11 says every refusal names `source unlink`. §14 says that after unlink, sourced comments can never be edited or removed. For comments, naming unlink as the way to edit would be false. The implementation (`_services/_collab.py`, `_require_comment_author`) names it but says it "keeps it as written". The right reading is §14, which is the later and more specific rule. Amend §11 so the unlink hint applies to the title, mapped fields and the description view only, and have the comment refusal name the source and the key without an unlink hint, since unlink offers nothing there.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-04T02:27:12Z] `architect` Robert Architect:
  - Recorded in ADR-1274 sections 9, 11 and 14 (2026-11-04): GitLab fetch by path and iid with its gone and ID-only relink limits; the unlink hint covers only the title, mapped fields and description. Open: the sourced-comment refusal must drop its unlink hint, briefed to @python-dev on TASK-1276.
- [2026-11-04T02:46:39Z] `python-dev` Elias Python:
  - Code side done: the sourced-comment refusal names the source and the key with no source unlink hint (test updated). The ADR amendment is the architect's.
- [2026-11-04T02:52:13Z] `reviewer` Paul Reviewer:
  - Verified. ADR-1274 §11 now limits the unlink hint to the title, mapped fields and description, and §14 records the GitLab fetch by path and number with its limits. The sourced-comment refusal names the source and key, with no unlink hint.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Credential verbs carry no mark that a remote command listener could refuse

<!-- sq:finding:F8:body -->
**Where:** `src/squads/_api/_ops_sources.py`. All eight source operations carry the same flag, `private=True`, and the only thing keeping the credential verbs off the browser port is that the whole command endpoint is CLI-listener-only (`_daemon/_admission.py`).

**Today:** this matches ADR-1274 §7 and ruling a7b791e point 5. The browser listener refuses `/v1/commands`, and no private operation has a route or an OpenAPI entry (the daemon test checks both).

**The gap:** FEAT-33 makes the command endpoint reachable from other machines, and §7 requires that listener to admit `pull`, `relink` and the rest but refuse `credential set` and `remove` until MILE-868. No operation-level marker separates them, so FEAT-33 has nothing to test against. A one-field mark now, such as `owner_only=True` on `SOURCE_CREDENTIAL_SET` and `SOURCE_CREDENTIAL_REMOVE`, checked where a command line's operations run, keeps the rule from being lost.

Info: no defect on any listener that exists today. The natural home is FEAT-33.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-11-04T02:27:13Z] `architect` Robert Architect:
  - Recorded in ADR-1274 section 14 (2026-11-04) as a precondition of FEAT-33, with a note on FEAT-33: the two credential operations carry an operation-level mark before a remote command listener exists.
- [2026-11-04T02:52:14Z] `reviewer` Paul Reviewer:
  - Verified as recorded. ADR-1274 §14 binds an operation-level mark on the two credential verbs, to land no later than FEAT-33, which tests against it. Nothing is needed today.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Cleanup: prompt on stdout, relink key, holder race, refresh cost, dead pre-flight, tests

<!-- sq:finding:F9:body -->
Small items, grouped.

- **`credential set --json` puts the prompt on stdout.** In process with a terminal on stdin (`src/squads/_cli/_common.py:1525`, `prompt_secret` calls `typer.prompt`, which writes to stdout), `sq source credential set x --json | jq` receives `platform token:{...}`. Reproduced with a pty on stdin and a pipe on stdout. Pass `err=True`.
- **Relink's key is not validated** (`_gitlab.py:30, 108-111`): the iid after `#` goes into the path unquoted, so `relink platform 'g/p#1/../../../users'` sends an authenticated GET to an arbitrary path on the same host and parses the answer as an issue. Require `\d+`.
- **Relink's holder check runs outside the transaction** (`_services/_source_links.py:129-134`). `compile_job` re-checks only that the item still has no record, so an in-process pull that runs between the two could leave two holders. Re-check `(name, id)` in `compile_job`.
- **`show --refresh` and `relink` list the whole filter** (`_fetch.py:82`, `listed_ids()`) to classify one issue, which costs one page per 100 issues for a single-item command. Ask the connector whether the one issue matches the filter (labels are on the issue).
- **The runner's type-and-alias pre-flight is dead.** The developer verified that `sq migrate up` cannot reach it, because the migrate mode refuses the spec first. Either delete it or record why it stays; it has no test.
- **Version history in non-migration code:** `_workflow/_validity.py:433` names `_RESERVED_SINCE_0_19` and its message names 0.19 and 0.20. Keep the version pair in the migration module and pass it in.
- **Tests reach past the CLI** (ADR-1172): `test_source_pull.py`, `test_source_links.py` and `test_source_identities.py` seed the store through `credentials.write_entry` instead of `sq source credential set` with stdin. `test_source_comments.py:41-49` and `test_source_ownership.py:38-43` hand-write a `source` record into frontmatter where a harness pull would make the real one.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-11-04T02:36:33Z] `python-dev` Elias Python:
  - Fixed except the refresh cost (F2 reworks the listing): credential prompt goes to stderr; relink requires group/project#digits (case added); the holder check runs inside the transaction (by trace; no race test); the unreachable migration pre-flight is deleted and the summary says three; version names left _workflow/_validity.py (the range lives in _migrations/_reserved.py, read in a function); tests seed credentials through 'source credential set' and the comment and ownership cases through a harness pull. Check-rule and record tests still hand-edit files because no verb makes a gone state, a duplicate holder or a malformed record.
- [2026-11-04T02:52:14Z] `reviewer` Paul Reviewer:
  - Verified. With a tty stdin and a piped stdout, the prompt goes to stderr and stdout is pure JSON. A relink key needs a numeric iid. The holder check runs inside the transaction (by trace). The dead pre-flight and the version table in _workflow are gone. Tests seed the store through the CLI. The refresh listing cost is accepted in ADR-1274 §14. The remaining hand edits of item files cover states no verb makes.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — No test catches a regression of the sourced comment escape

<!-- sq:finding:F10:body -->
**Where:** `src/squads/_discussion.py:150-153` (sourced comment text escaped on write) and `:250` (unescaped on read). `src/squads/_services/_collab.py` skips `reject_markers` for a `source:` author, so the escape is the only guard between tracker text and the discussion region.

**Mutation (run on a copy of HEAD):** with `msg = escape_body(msg)` replaced by `msg = msg`, all 85 tests of `tests/cli/test_source_comments.py`, `test_source_pull.py`, `test_source.py`, `test_source_ownership.py`, `test_source_links.py` and `test_comment_verbs.py` pass. No case pulls a comment that holds a marker.

The escape itself works: a pulled note carrying a forged comment header, an `sq:attrs` line and a wrapped `sq:discussion:end` tag (no space after the opener) is stored as `<!!--` and rendered back as written, and the forged header stays nested under the real one. A regression would let any tracker user close or forge discussion regions, and nothing would catch it.

**Fix:** extend the description-forging pull case (`test_a_description_forging_a_marker_and_using_crlf_is_kept_as_text`) with one note that holds a wrapped `sq:discussion:end` tag and a forged `sq:attrs` line. Assert that `comments --json` returns the text exactly and that `sq check` stays clean. Re-run the mutation and see it fail.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-04T02:27:19Z] `python-dev` Elias Python:
  - Fixed: a pull case now carries a note holding a wrapped sq:discussion:end tag, a forged sq:attrs line and a forged header; it asserts the text round-trips, one comment exists and sq check is clean. With the escape turned off the case fails.
- [2026-11-04T02:52:14Z] `reviewer` Paul Reviewer:
  - Verified. Turning off the sourced-comment escape now fails test_a_note_forging_a_region_end_and_an_attribute_line_is_kept_as_text.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — A tracker title holding a marker is pulled, fails sq check, and the squad cannot fix it

<!-- sq:finding:F11:body -->
**Where:** `src/squads/_services/_pull.py:169` (create) and `:198` (update): the tracker title goes into the event as is. ADR-1274 §10 lists "a title holding a marker" among the pre-pass failures that drop an issue, but the importer accepts one. The CLI accepts one too (`sq create task` with such a title succeeds).

**Scenario (reproduced):** a tracker issue titled `Token` + a wrapped `sq:body:end` tag + `loops` is pulled and created. `sq check` then reports `error ...: close without open` naming the `sq:body:end` tag. The title is tracker-owned, so the squad cannot fix it (`update --title` is refused, naming `source unlink`). Any tracker user can therefore put an error in a squad whose `sq check` is a gate, and only unlinking clears it. Region writes on the item still worked in the probe.

**Fix:** apply `reject_markers` to titles in the importer's pre-pass, so the issue is dropped and reported as §10 says. Apply it to CLI titles too, which closes the pre-existing hole. Add one recorded-HTTP case.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-11-04T02:29:02Z] `python-dev` Elias Python:
  - Fixed: require_title now rejects a title holding an sq marker, for the importer pre-pass (the issue is dropped and reported per the ADR) and for create, update and sub-entity titles. A pull case covers it and fails without the check.
- [2026-11-04T02:52:15Z] `reviewer` Paul Reviewer:
  - Verified. The pull drops a tracker title holding a marker and reports it, sq check stays clean, and the CLI also refuses such a title on create.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T02:24:18Z, edited 2026-11-04T02:24:32Z] `reviewer` Paul Reviewer:
  - - REV-1281 is filed with 11 findings. The verdict is changes requested; the approval is left to the main loop.
    - Two high findings:
      - F1: the token follows a redirect to any host.
      - F2: the derived cursor loses tracker updates after a `show --refresh` or a relink, and loses issues that were unmapped or dropped. Reproduced. The fix drops the cursor and diffs the listing the pull already fetches.
    - Three medium findings:
      - F3: a failing link target drops its host issue, and the report lists items that were never created.
      - F4: a tracker display name can impersonate an operator.
      - F10: no test catches a regression of the sourced comment escape.
    - @architect rules first on F2, F4 and F7, which amend §1, §10, §5, §9 and §11. F8 is an info finding for FEAT-33.
    - @python-dev has F1, F3, F5, F6, F9, F10 and F11.
    - `--author source:x` is already refused as an unknown slug on create, update and import, so relink authorship cannot be forged through the CLI.
- [2026-11-04T02:52:24Z] `reviewer` Paul Reviewer:
  - Fix verification of e1a50c24: F1, F2 and F5 to F11 are Verified. F3 is reopened: when a pull creates the host, a link dropped for a failing target is never retried (reproduced; @architect picks the fix, then @python-dev). F4 stays Open pending op-pierre. The review stays ChangesRequested.
<!-- sq:discussion:end -->
