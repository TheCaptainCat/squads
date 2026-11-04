"""`sq source check`, and the access probes every fetching command runs first."""

import json
from typing import Any

import pytest

from tests import _tracker_harness as harness

pytestmark = pytest.mark.anyio

SECRET = "glpat-not-a-real-token"
MAPS = '\n[sources.platform.maps.types.type]\nissue = "task"\n'
PRIORITY = '\n[sources.platform.maps.fields.priority.labels]\n"priority::high" = "high"\n'
HEAD = '[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
ACCESS = [
    "  pass  http://tracker answers",
    "  pass  authenticated as squads-bot (id 1)",
    "  pass  the token reads the issues of the scope",
]
HEADER = "platform (gitlab@v4)"
GITHUB_MAPS = '\n[sources.platform.maps.types.labels]\nsquads = "task"\n'


async def _declare(invoke, project, base_url: str, maps: str = MAPS, head: str = HEAD) -> None:
    """Declare the `platform` source on *base_url* and store its credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{head}base_url = "{base_url}"\n{maps}', encoding="utf-8")
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


async def _operator(invoke, name: str, user_id: str) -> None:
    assert (await invoke(["operator", "add", name])).exit_code == 0
    slug = "op-" + name.split()[0].lower()
    result = await invoke(["operator", slug, "update", "--identities", f"platform={user_id}"])
    assert result.exit_code == 0, result.output


def _route(tracker: harness.Tracker, path: str) -> dict[str, Any]:
    return next(r for r in tracker.routes if r["path"] == path)


async def _checked(invoke, tracker: harness.Tracker, *args: str) -> tuple[int, str]:
    """The exit code of `source check` and its output, the tracker's address made constant."""
    result = await invoke(["source", "check", *args])
    return result.exit_code, result.output.replace(tracker.base_url, "http://tracker")


@pytest.mark.covers("source check", "source")
async def test_a_source_that_passes_every_probe_prints_an_all_pass_checklist_and_exits_0(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, MAPS + PRIORITY)
        await _operator(invoke, "Alice Tester", "4567")
        await _operator(invoke, "Bob Tester", "4568")
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        0,
        "\n".join(
            [
                HEADER,
                *ACCESS,
                "  pass  every value the maps name exists on the tracker",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_missing_credential_is_the_only_line_of_its_source_and_exits_1(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        assert (await invoke(["source", "credential", "remove", "platform"])).exit_code == 0
        code, output = await _checked(invoke, tracker, "platform")
        asked = tracker.requests

    assert (code, output) == (
        1,
        "\n".join(
            [
                HEADER,
                "  FAIL  source 'platform' has no stored credential",
                "        fix: run `sq source credential set platform`",
                "",
            ]
        ),
    )
    assert asked == []


@pytest.mark.covers("source check", "--json")
async def test_a_mapped_label_the_tracker_lacks_is_a_blocking_vocabulary_failure_naming_the_map(
    project, invoke, credentials_home
) -> None:
    urgent = PRIORITY + '"priority::urgent" = "medium"\n'
    wrong = '\n[sources.platform.maps.links]\nduplicates = "related"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(
            invoke, project, tracker.base_url, MAPS + 'ghost = "task"\n' + urgent + wrong
        )
        result = await invoke(["source", "check", "--json"])
        base = tracker.base_url

    checked = json.loads(result.output.replace(base, "http://tracker"))
    assert result.exit_code == 1
    assert checked["ok"] is False
    assert [
        (line["family"], line["verdict"], line["text"], line["fix"])
        for line in checked["sources"][0]["lines"]
        if line["family"] == "vocabulary"
    ] == [
        (
            "vocabulary",
            "fail",
            "maps.types.type: 'ghost' is not among the tracker's issue types",
            "correct it in [sources.platform.maps.types.type] in sources.toml, "
            "or create it on the tracker",
        ),
        (
            "vocabulary",
            "fail",
            "maps.fields.priority.labels: 'priority::urgent' is not among the tracker's labels",
            "correct it in [sources.platform.maps.fields.priority.labels] in sources.toml, "
            "or create it on the tracker",
        ),
        (
            "vocabulary",
            "fail",
            "maps.links: 'duplicates' is not a GitLab link type",
            "use one of relates_to, blocks, is_blocked_by in "
            "[sources.platform.maps.links] in sources.toml",
        ),
    ]


@pytest.mark.covers("source check", "source")
async def test_an_unmapped_label_and_an_unknown_author_are_warnings_and_exit_0(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"][0]["labels"].append(
            "priority::low"
        )
        await _declare(invoke, project, tracker.base_url, MAPS + PRIORITY)
        await _operator(invoke, "Alice Tester", "4567")
        await _operator(invoke, "Carol Tester", "7777")
        assert (await invoke(["source", "pull", "platform"])).exit_code == 0
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        0,
        "\n".join(
            [
                HEADER,
                *ACCESS,
                "  pass  every value the maps name exists on the tracker",
                "  warn  label 'priority::low' on platform/api#12 has no entry in "
                "maps.fields.priority.labels",
                "        fix: add it to [sources.platform.maps.fields.priority.labels] in "
                "sources.toml",
                "  warn  author asmith (id 4568) of platform/api#13, a comment on TASK-4 is in "
                "no operator's identities",
                "        fix: run `sq operator <slug> update --identities platform=4568`",
                "  warn  op-carol holds user id 7777 of source 'platform', which the tracker no "
                "longer resolves",
                "        fix: run `sq operator op-carol update --identities platform=<handle>`",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_the_coverage_probes_read_only_the_issues_the_filter_selects(
    project, invoke, credentials_home
) -> None:
    by_label = '\n[sources.platform.maps.types.labels]\nbug = "task"\n'
    only_squads = '\n[sources.platform.filter]\nlabels = "squads"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        issues = _route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"]
        issues.append(
            {
                **issues[1],
                "iid": 14,
                "labels": ["squads", "other"],
                "references": {"full": "platform/api#14"},
            }
        )
        issues.append(
            {
                **issues[1],
                "iid": 15,
                "labels": ["unrelated"],
                "references": {"full": "platform/api#15"},
                "author": {"id": 9999, "username": "zed", "name": "Zed"},
            }
        )
        await _declare(invoke, project, tracker.base_url, by_label + only_squads)
        await _operator(invoke, "Alice Tester", "4567")
        code, output = await _checked(invoke, tracker, "platform")

    assert code == 0, output
    assert "  pass  2 selected issue(s) map to no type and are skipped by the pull" in output
    assert "  warn  2 selected" not in output
    assert "platform/api#13, platform/api#14" in output
    assert "#15" not in output
    assert "zed" not in output


@pytest.mark.covers("source check", "source")
async def test_an_issue_mapping_to_two_types_stays_a_coverage_warning(
    project, invoke, credentials_home
) -> None:
    two = MAPS + '\n[sources.platform.maps.types.labels]\nbug = "bug"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, two)
        _, output = await _checked(invoke, tracker, "platform")

    assert "  warn  platform/api#12 maps to several types: bug, task" in output


@pytest.mark.covers("source check", "--json")
async def test_a_disabled_source_is_still_listed_and_probed(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, head=HEAD + "enabled = false\n")
        await _operator(invoke, "Alice Tester", "4567")
        await _operator(invoke, "Bob Tester", "4568")
        result = await invoke(["source", "check", "--json"])
        base = tracker.base_url
        asked = [path for path, _, _ in tracker.requests]

    checked = json.loads(result.output.replace(base, "http://tracker"))
    assert result.exit_code == 0
    assert [(s["name"], s["enabled"], s["ok"]) for s in checked["sources"]] == [
        ("platform", False, True)
    ]
    assert [line["text"] for line in checked["sources"][0]["lines"][:3]] == [
        line.removeprefix("  pass  ") for line in ACCESS
    ]
    assert "/api/v4/version" in asked


def _failing_token(tracker: harness.Tracker) -> None:
    """Make the tracker refuse the token at its user endpoint."""
    _route(tracker, "/api/v4/user").update(status=401, body={"message": "401 Unauthorized"})


async def _stopped(invoke, tracker: harness.Tracker, args: list[str]) -> tuple[str, list[str]]:
    """The error a fetching command stops with when the token is refused, the tracker's address
    made constant, and the paths it asked the tracker for; checked to be the line
    `sq source check --json` gives."""
    before = len(tracker.requests)
    result = await invoke(args)
    asked = [path for path, _, _ in tracker.requests[before:]]
    checked = await invoke(["source", "check", "--json"])
    fail = next(
        line
        for line in json.loads(checked.output)["sources"][0]["lines"]
        if line["verdict"] == "fail"
    )
    lines = json.loads(checked.output)["sources"][0]["lines"]
    assert (result.exit_code, checked.exit_code) == (1, 1)
    assert lines[-1] == fail
    assert fail["text"] in result.output and fail["fix"] in result.output
    return result.output.replace(tracker.base_url, "http://tracker"), asked


@pytest.mark.covers("source pull", "source")
async def test_a_pull_on_a_source_failing_access_prints_the_checklist_line_and_writes_nothing(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        _failing_token(tracker)
        before = (await invoke(["reflog", "--json"])).output
        stopped, asked = await _stopped(invoke, tracker, ["source", "pull", "platform"])
        after = (await invoke(["reflog", "--json"])).output

    assert stopped == (
        "error: http://tracker did not accept the token: http://tracker rejected the credential "
        "(HTTP 401)\n  fix: run `sq source credential set platform` with a valid personal or "
        "project token\n"
    )
    assert before == after
    assert asked == ["/api/v4/version", "/api/v4/user"]


@pytest.mark.covers("<type> show", "--refresh")
async def test_show_refresh_on_a_source_failing_access_prints_the_line_and_writes_nothing(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        assert (await invoke(["source", "pull", "platform"])).exit_code == 0
        _failing_token(tracker)
        before = (await invoke(["task", "2", "show", "--json"])).output
        reflog = (await invoke(["reflog", "--json"])).output
        stopped, asked = await _stopped(invoke, tracker, ["task", "2", "show", "--refresh"])
        after = (await invoke(["task", "2", "show", "--json"])).output
        reflog_after = (await invoke(["reflog", "--json"])).output

    assert stopped.startswith("error: http://tracker did not accept the token")
    assert (before, reflog, asked[-2:]) == (
        after,
        reflog_after,
        ["/api/v4/version", "/api/v4/user"],
    )


@pytest.mark.covers("source pull", "--json")
async def test_an_unnamed_pull_reports_a_source_failing_access_pulls_the_others_and_exits_1(
    project, invoke, credentials_home
) -> None:
    with (
        harness.serve(harness.load_routes("gitlab/routes.json")) as healthy,
        harness.serve(harness.load_routes("gitlab/routes.json")) as refusing,
    ):
        _failing_token(refusing)
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                f'[sources.{name}]\nconnector = "gitlab"\nproject = "platform/api"\n'
                f'base_url = "{tracker.base_url}"\n{MAPS.replace("platform", name)}\n'
                for name, tracker in (("platform", healthy), ("other", refusing))
            ),
            encoding="utf-8",
        )
        for name in ("platform", "other"):
            stored = await invoke(["source", "credential", "set", name], input=f"{SECRET}\n")
            assert stored.exit_code == 0, stored.output
        result = await invoke(["source", "pull", "--json"])
        shown = await invoke(["task", "2", "show", "--json"])

    reports = {r["name"]: r for r in json.loads(result.stdout)["sources"]}
    assert result.exit_code == 1
    assert (reports["platform"]["created"], reports["platform"]["failed"]) == (
        ["TASK-2", "TASK-3"],
        False,
    )
    assert reports["other"]["failed"] is True
    assert reports["other"]["left_out"].startswith("http://127.0.0.1:")
    assert "rejected the credential (HTTP 401)" in reports["other"]["left_out"]
    assert shown.exit_code == 0


@pytest.mark.covers("operator update", "--identities")
async def test_resolving_a_handle_on_a_source_failing_access_stops_and_stores_nothing(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
        _failing_token(tracker)
        stopped, asked = await _stopped(
            invoke, tracker, ["operator", "op-alice", "update", "--identities", "platform=@pchat"]
        )
        shown = await invoke(["operator", "op-alice", "show", "--json"])

    assert stopped.startswith("error: http://tracker did not accept the token")
    assert (json.loads(shown.output)["identities"], asked) == (
        {},
        ["/api/v4/version", "/api/v4/user"],
    )


@pytest.mark.covers("source check", "source")
async def test_a_filter_selecting_nothing_is_a_warning_and_confirms_no_label(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"] = []
        await _declare(invoke, project, tracker.base_url, MAPS + PRIORITY)
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        0,
        "\n".join(
            [
                HEADER,
                *ACCESS[:2],
                "  warn  the scope project 'platform/api' holds no issue",
                "        fix: create an issue in the scope, or correct `project` of source "
                "'platform' in sources.toml",
                "  warn  maps.fields.priority.labels: 'priority::high' is carried by no issue in "
                "the scope, so it cannot be confirmed among the tracker's labels",
                "        fix: correct it in [sources.platform.maps.fields.priority.labels] in "
                "sources.toml",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_scope_the_tracker_does_not_know_is_a_blocking_access_failure_naming_its_key(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, head=HEAD.replace("api", "nope"))
        gitlab = await _checked(invoke, tracker, "platform")
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        github_head = '[sources.platform]\nconnector = "github"\nrepository = "acme/nope"\n'
        await _declare(invoke, project, tracker.base_url, head=github_head)
        github = await _checked(invoke, tracker, "platform")

    assert [(code, output.splitlines()[-2:]) for code, output in (gitlab, github)] == [
        (
            1,
            [
                "  FAIL  the scope project 'platform/nope' does not exist or is not visible to "
                "the token",
                "        fix: correct `project` of source 'platform' in sources.toml",
            ],
        ),
        (
            1,
            [
                "  FAIL  the scope repository 'acme/nope' does not exist or is not visible to "
                "the token",
                "        fix: correct `repository` of source 'platform' in sources.toml",
            ],
        ),
    ]


@pytest.mark.covers("source check", "source")
async def test_a_filter_accepting_no_listed_issue_is_a_warning_and_exits_0(
    project, invoke, credentials_home
) -> None:
    only = '\n[sources.platform.filter]\nlabels = "priority::high and not priority::high"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, MAPS + only)
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output.splitlines()[4:6]) == (
        0,
        [
            "  warn  the filter accepts none of the 2 issue(s) of the scope",
            "        fix: correct it in [sources.platform.filter] in sources.toml",
        ],
    )


@pytest.mark.covers("source check", "source")
async def test_a_filter_value_missing_on_a_listable_side_fails_and_on_an_unlistable_side_warns(
    project, invoke, credentials_home
) -> None:
    ghost = '\n[sources.platform.filter]\nlabels = "ghost"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, MAPS + ghost)
        listable = await _checked(invoke, tracker, "platform")
    github_head = '[sources.platform]\nconnector = "github"\nrepository = "acme/api"\n'
    bug = '\n[sources.platform.filter]\ntype = "Ghost"\n'
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, GITHUB_MAPS + bug, head=github_head)
        unlistable = await _checked(invoke, tracker, "platform")

    assert [(code, output.splitlines()[4:6]) for code, output in (listable, unlistable)] == [
        (
            1,
            [
                "  FAIL  filter.labels: 'ghost' is not among the tracker's labels",
                "        fix: correct it in [sources.platform.filter] in sources.toml, or create "
                "it on the tracker",
            ],
        ),
        (
            0,
            [
                "  warn  filter.type: 'Ghost' is carried by no issue in the scope, so it cannot "
                "be confirmed among the tracker's issue types",
                "        fix: correct it in [sources.platform.filter] in sources.toml",
            ],
        ),
    ]


@pytest.mark.covers("source check", "source")
async def test_an_off_host_redirect_is_a_host_failure_naming_base_url_not_an_answer(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _route(tracker, "/api/v4/version").update(
            status=302, headers={"Location": "http://203.0.113.9/elsewhere"}
        )
        await _declare(invoke, project, tracker.base_url)
        code, output = await _checked(invoke, tracker, "platform")

    lines = output.splitlines()
    assert code == 1
    assert len(lines) == 3
    assert lines[1].startswith(
        "  FAIL  http://tracker/api/v4/version redirected to http://203.0.113.9/"
    )
    assert lines[2] == (
        "        fix: correct `base_url` of source 'platform' in sources.toml, "
        "or the host's network"
    )
