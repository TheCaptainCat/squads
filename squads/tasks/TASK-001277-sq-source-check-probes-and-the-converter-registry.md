---
id: TASK-1277
sequence_id: 1277
type: task
title: sq source check probes and the converter registry
status: Done
parent: FEAT-1272
author: tech-lead
assignee: python-dev
refs:
- ADR-1274:implements
- MILE-1269:targets
- TASK-1276:depends-on
description: Connector-neutral probe checklist served with the pull's credentials,
  and the four named text converters
subentities:
- local_id: ST1
  title: Probe framework, GitLab probes and sq source check
  status: Done
  maps_to: US1
- local_id: ST2
  title: The adf, jira-wiki and github-md converters
  status: Done
  maps_to: US2
created_at: '2026-11-03T23:02:45Z'
updated_at: '2026-11-04T04:14:00Z'
priority: high
---
<!-- sq:body -->
## Goal

`sq source check [<name>]` runs each connector's probes where the squad is served and prints, per source, a checklist of passes, blocking failures and warnings, each failure followed by its fix; every command that fetches from a tracker runs the access probes first. Connectors convert tracker text to markdown through a shared, literal registry of named converters (FEAT-1272 US1, US2).

## ADR-1274 sections implemented

- §7: `sq source check` runs where the squad is served, reads the same credential store as the pull, and is classed `long`.
- §9: the probe method of the connector interface, GitLab's probes, and the converter rows `adf`, `jira-wiki` and `github-md` (pure functions of text and base URL, no network; `gitlab-md` lands with the GitLab connector).
- §14: the probe method lands with the framework; the converter cases pull through the GitLab connector; a disabled source is still probed.
- §8: a source's `converter` override, validated against the registry at load (the validation exists from the pull task; this task adds three rows).
- §3, last bullet: an identity whose ID no longer resolves is a coverage warning.
- §10 phase 1 and §14: the access probes run at the start of the shared fetch phase, so the pull, `show --refresh`, `relink` and handle resolution all run them before fetching.

## Scope

- The probe method on the connector interface, and GitLab's probes (`_sources/_gitlab.py`), the only connector with probes in this task.
- A connector-neutral probe framework: a probe yields pass, blocking failure or warning, with a fix naming what to change on the tracker, in `sources.toml` or in the credential store. Each connector version supplies its probes; the framework names no tracker.
- Probe families, in order: access (credential present, host reachable, authenticated and as whom, project or filter valid, read permission; a source's list stops at its first blocking access failure), vocabulary (every value a map names exists on the tracker; missing is blocking), coverage (unmapped tracker values on in-filter issues, authors or assignees whose immutable ID is in no operator's `identities`, identities that no longer resolve; warnings).
- A disabled source is still probed.
- `--json` prints the checklist; exit code 1 on any blocking failure, 0 otherwise. `sq check` still never calls the network.
- The access probes run at the start of the shared fetch phase the pull task built, so every fetching command (pull, `show --refresh`, `relink`, handle resolution) stops on a blocking failure before anything is fetched or written, printing the same line as `sq source check`. No second fetch path.
- Three converters, each a pure function of text and base URL: `adf`, `jira-wiki`, and `github-md`, which makes relative upload and image links absolute and downloads nothing.

## Layers and expected files

- `src/squads/_sources/_probes.py` (new: the framework and result model), `src/squads/_sources/_connector.py` (the probe method of the interface), `src/squads/_sources/_gitlab.py` (its probes), `src/squads/_sources/_converters.py` (the three rows; split into `_sources/_converters/` per format if one module grows past reason)
- `src/squads/_specs/sources.toml` (no new connector rows; the `jira` and `github` defaults arrive with their connectors)
- Services: `src/squads/_services/_sources_ops.py` (check handler; the access probes at the start of the shared fetch phase), `_bindings.py`
- API: `src/squads/_api/_ops.py`, `src/squads/_api/_dto/_sources.py` (checklist DTO)
- CLI: `src/squads/_cli/_source.py` (`check`), `src/squads/_cli/_render/` (the checklist), `src/squads/_shim.py` (`LONG_COMMANDS` row)
- Tests: `tests/cli/test_source.py` (or the module the pull task created), `tests/fixtures/sources/gitlab/` (recorded responses for the probes), `tests/fixtures/converters/` (recorded samples)

## Tests (about 10 new)

Per subtask below. Recorded responses only; CI never reaches a network host. Every case runs through the GitLab connector on the loopback harness the pull task built: the probe cases through `sq source check`, the converter cases through a pull and `show` with the source's `converter` set in `sources.toml`, so they are CLI surface rather than unit tests on the functions.

## Schema

None. No on-disk format change.

## CHANGELOG

Report to the tech writer: `sq source check`, its checklist and exit code, that a disabled source is still checked, the access check before every fetching command, and the `converter` key in `sources.toml` with the converter names.

## Depends on

The sources spec and pull task (the connector interface, both tables, the GitLab connector, the loopback harness, the credential store, `sq source pull`).

## Can run beside

The converter subtask touches only `_sources/_converters.py` and its samples, so it can start once the pull task's ST10 (GitLab connector and harness) is merged, while the rest of that task is still in progress, if the manager wants it.

## Size

M.

## Working rules

- Work in your own git worktree off `origin/release/0.20`.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects (grep the names you changed across `tests/`) plus the floor (`tests/meta`, `tests/cli`, `tests/check`, `tests/daemon` for any change under `_specs/`, `_rendering/templates/`, `_cli/`, `_shim.py` or `_daemon/`), and `~/.local/bin/sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. Each new check rule gets its `@pytest.mark.breaches(...)` case. Falsify each new test once and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change.
- No credential value in any output, log line, reflog entry, test golden or fixture file committed to the repository; test credentials are fake strings written by the test.
- No module-level mutable state: thread the request's spec, playbook and sources document. A new module-level table goes on the mutable-state guard's allowlist as a code constant.
- No bundled type, kind, field, status, ref-kind or view literal in code outside `_specs/` and `_migrations/`.
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test or file names.
- CHANGELOG and adopter docs are the tech writer's: report, do not edit `CHANGELOG.md` or `docs/`.
- Use `~/.local/bin/sq` for board operations; the dev tree only through `uv run --project <repo> sq -C <scratch>` on a scratch squad under the session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1277 add-subtask "<title>"`; track with `sq task 1277 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Probe framework, GitLab probes and sq source check

<!-- sq:subtask:ST1:body -->
The probe framework (`_sources/_probes.py`), the probe method on the connector interface, GitLab's probes, and `sq source check [<name>]`: served, classed `long`, reading the same credential store as the pull. Results are pass, blocking failure or warning, each failure followed by its fix (tracker, `sources.toml` or credential store). Access probes in order, stopping a source's list at its first blocking failure; vocabulary probes (every mapped value exists on the tracker, blocking); coverage probes (unmapped in-filter values, unknown author or assignee IDs, identities that no longer resolve; warnings). A disabled source is still probed. `--json` prints the checklist; exit 1 on a blocking failure, 0 otherwise. The access probes run at the start of the shared fetch phase, so the pull, `show --refresh`, `relink` and handle resolution stop on a blocking failure before fetching or writing, printing the same line. The framework names no tracker; GitLab supplies its probes through the interface, and later connectors add theirs the same way.

Tests (7), on a `gitlab` source and the loopback harness: a passing source prints an all-pass checklist and exits 0; a missing credential is the first and only line for that source, with the `sq source credential set` fix, and exits 1; a mapped label absent from the recorded tracker labels is a blocking vocabulary failure naming the map; an unmapped label and an unknown author ID are warnings with exit 0; a disabled source is still listed and probed; `sq source pull` on a source failing access prints the same line and writes nothing; `show --refresh` on an item of a source failing access prints the same line and writes nothing. Verify the exit codes on the bare command, not through a pipe.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The adf, jira-wiki and github-md converters

<!-- sq:subtask:ST2:body -->
Three rows in the converter table (`_sources/_converters.py`): `adf` (Atlassian Document Format), `jira-wiki` (Jira wiki markup) and `github-md` (relative upload and image links made absolute against the base URL; nothing downloaded). `gitlab-md` already exists with the GitLab connector. Pure functions of text and base URL, no network. A source's `converter` override is validated at load against the table, listing the known names on a miss; the connector defaults for `jira` and `github` arrive with those connectors.

Tests (3): one case per converter, each pulling a recorded GitLab issue whose description and one comment are written in that format (nested lists, a code block, a table, a link and a mention), through a `gitlab` source with `converter` set in `sources.toml`, and comparing `show` output with a recorded expected markdown sample under `tests/fixtures/converters/`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T23:11:23Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04) changes this task's scope:
      - The GitLab connector and the `gitlab-md` row land with TASK-1276. This task adds the probe method to the interface and **GitLab's probes** with the framework, because ST1's cases need a connector with probes and GitLab is the only one. Take over TASK-1278 ST2's `sq source check` case.
      - ST2 keeps `adf`, `jira-wiki` and `github-md` (drop `gitlab-md`, already covered). Each case pulls through the GitLab connector with the source's `converter` set in `sources.toml`; no other connector is needed.
      - A disabled source is still probed by `sq source check`.
- [2026-11-03T23:15:38Z] `tech-lead` Olivia Lead:
  - Scope updated to ADR-1274 §14 per @architect's comment: body and subtasks revised; see the subtask table for what moved.
- [2026-11-03T23:17:26Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04): ST1's access probes run before every fetching command, not only the pull. That covers `show --refresh`, `relink` and handle resolution, through the shared fetch phase TASK-1276 builds. Extend the pull's access-failure case, or add one: `show --refresh` on a source failing access prints the same line and writes nothing. `sq source check` still probes a disabled source.
- [2026-11-04T03:12:32Z] `python-dev` Elias Python:
  - Handoff, both subtasks Done. Gates green: pyright 0 errors, ruff check and format clean, tests/meta 728 passed, tests/cli + tests/check + tests/daemon 1311 passed 2 skipped, sq check clean. Full suite not run.
    
    Files, new: _sources/_probes.py (framework: ProbeResult, Expected, run_probes, missing_credential), _sources/_gitlab_probes.py, _sources/_adf.py, _sources/_jira_wiki.py, tests/cli/test_source_check.py, tests/cli/test_source_converters.py, tests/fixtures/converters/{adf,jira-wiki,github-md}/{input.txt,expected.md}.
    Files, changed: _sources/_connector.py (abstract probes method), _gitlab.py, _http.py (UnreachableError, RejectedError), _converters.py (adf, jira-wiki, github-md rows; github_md), _services/_fetch.py (open_connector runs the access probes; every fetching path goes through it), _pull.py, _source_links.py (check_sources), _bindings.py, _api/_ops.py, _ops_sources.py, _dto/_sources.py, _cli/_source.py, _cli/_render/_sources.py, _shim.py (LONG row), tests/fixtures/sources/gitlab/routes.json (version, user, labels, users/<id> routes), tests/cli/test_source_identities.py (declares the filter, which the access probe now needs).
    
    Tests (7 + 3): source check/source x3 (all-pass exit 0; missing credential; unmapped label + unknown author warnings exit 0), source check/--json x2 (vocabulary failure exit 1; disabled source probed), source pull/source (pull stops on refused token, asks the tracker only version and user, reflog unchanged), <type> show/--refresh (same, item and reflog unchanged), source pull/source x3 parametrized for adf, jira-wiki, github-md against recorded samples. Each falsified once by a targeted mutation, each failed as expected.
    
    Behaviour: sq source check [name] [--json], exit 1 on a blocking failure, warnings exit 0, disabled sources included. Access probes (credential, host answers, authenticated as whom, filter read) run first in open_connector for pull, show --refresh, relink and handle resolution; the stop prints the check's text and fix. A named or unnamed pull checks every source before fetching any. Unnamed pull still skips a source with no credential, with a warning. Importing: CLI start loads no urllib, http.client, ssl or connector (only _adf, which imports json).
    
    Open: (1) links map keys are not checked against the tracker, because GitLab has no link-type listing and the connector-vocabulary guard bans the name blocks; (2) a types key that is neither a label nor an observed in-filter issue type is a warning, not blocking, for the same guard reason (task, epic cannot be spelled); (3) coverage covers authors only, not assignees (Issue does not carry them); (4) the comment render shows a multi-line comment as an indented list entry, so the converter test expects that shape (comment display code left alone).
    Docs rows for the writer: sq source check (checklist, three families, exit code, disabled source probed, run where the squad is served); the access check before every fetching command; the converter key and names adf, jira-wiki, gitlab-md, github-md; CHANGELOG entry.
- [2026-11-04T03:31:24Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1282: changes requested, twelve findings. @python-dev, the fix queue is on the review.
- [2026-11-04T03:32:23Z, edited 2026-11-04T03:32:36Z] `product-owner` Nina Product:
  - @python-dev REV-1282 F9: extend the coverage probe (_unknown_authors) to also warn on comment authors already held in the squad (the comment attribute `author_id`, no network) whose ID is in no operator identities; remove assignee coverage. See FEAT-1272 US1 for the wording.
- [2026-11-04T03:33:15Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) rules on REV-1282 F2, F4 and F8. Exact changes:
      - **F2, unnamed pull:**
        - In `_pull.py`'s `ready` loop, a source whose access probes fail blocking is no longer raised on an unnamed pull. Record it with its probe line, fetch nothing from it, and pull the others.
        - The response lists it (its line in that source's `--json` report, as `left_out`), and the command exits 1 when any source failed access, after the others have applied.
        - A named pull still raises. A missing credential keeps its warning and exit 0.
        - Test: the reviewer's two-source case. `platform` creates its items, `other` prints its access line, and the exit code is 1 on the bare command, not through a pipe.
      - **F4, guard exemption:**
        - In `tests/meta/test_connector_modules_hold_no_squad_vocabulary.py`, add a literal table `EXEMPT_TRACKER_ENUMS` of `(module, constant name, reason)`. A listed constant must be a module-level tuple or frozenset of string literals. The guard skips only the string literals inside a listed constant, and every other literal in the module is still checked.
        - In `_gitlab.py`, declare `_LINK_TYPES = ("relates_to", "blocks", "is_blocked_by")` and `_ISSUE_TYPES` (GitLab v4's `issue_type` enum), with their table rows.
        - Probes: a `maps.links` key outside `_LINK_TYPES` is a blocking vocabulary failure naming the map; a `maps.types` key that is neither in `_ISSUE_TYPES` nor a tracker label is blocking. This replaces today's warning.
        - Keep the planted-name falsification, and add a second: the same vocabulary word outside the exempt constant in the same module is caught.
      - **F8, converter signature:**
        - Converters are called as `(text, base_url, issue_url)`, with `issue_url` the connector's issue URL for the description, or for the issue that holds a comment.
        - `gitlab-md` resolves `/uploads/...` against the project URL, the part of `issue_url` before `/-/issues/`. `github-md` resolves a relative link with `urljoin(issue_url, link)`. Root-relative links resolve against the host of `base_url`, and absolute links are kept.
        - Update the recorded expected samples, and add a GitLab case where `/uploads/x.png` becomes `<base>/<group>/<project>/uploads/x.png`.
- [2026-11-04T04:14:00Z] `manager` Catherine Manager:
  - Accepted: REV-1282 approved with all findings verified; full suite 2102 passed; gates and sq check clean. Moved to Done under the operator's delegation of the loop.
<!-- sq:discussion:end -->
