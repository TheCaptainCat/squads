---
id: TASK-1277
sequence_id: 1277
type: task
title: sq source check probes and the converter registry
status: Draft
parent: FEAT-1272
author: tech-lead
refs:
- ADR-1274:implements
- MILE-1269:targets
- TASK-1276:depends-on
description: Connector-neutral probe checklist served with the pull's credentials,
  and the four named text converters
subentities:
- local_id: ST1
  title: Probe framework, GitLab probes and sq source check
  status: Todo
  maps_to: US1
- local_id: ST2
  title: The adf, jira-wiki and github-md converters
  status: Todo
  maps_to: US2
created_at: '2026-11-03T23:02:45Z'
updated_at: '2026-11-03T23:19:01Z'
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
<!-- sq:discussion:end -->
