"""`sq source check`, and the access probes every fetching command runs first."""

import json
from typing import Any

import pytest

from tests import _tracker_harness as harness
from tests.cli import _source_checks as source_checks
from tests.cli import _source_connectors as source_connectors

pytestmark = pytest.mark.anyio


ACCESS = [
    "  pass  http://tracker answers",
    "  pass  authenticated as squads-bot (id 1)",
    "  pass  the token reads the issues of the scope",
]


HEADER = "platform (gitlab@v4)"


def _line(family: str, verdict: str, text: str, fix: str = "") -> dict[str, str]:
    return {"family": family, "verdict": verdict, "text": text, "fix": fix}


ACCESS_LINES = [_line("access", "pass", line.removeprefix("  pass  ")) for line in ACCESS]


def _json_report(*lines: dict[str, str], ok: bool = True, enabled: bool = True) -> dict[str, Any]:
    """The `source check --json` document of the one `platform` source, its lines in order."""
    return {
        "ok": ok,
        "sources": [
            {
                "name": "platform",
                "connector": "gitlab",
                "version": "v4",
                "enabled": enabled,
                "ok": ok,
                "lines": list(lines),
            }
        ],
    }


def _priority(profile) -> str:
    return (
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'"priority::high" = "{profile.badge_value}"\n'
    )


def _github_maps(profile) -> str:
    return f'\n[sources.platform.maps.types.labels]\nsquads = "{profile.ref}"\n'


async def _operator(invoke, name: str, user_id: str) -> None:
    assert (await invoke(["operator", "add", name])).exit_code == 0
    slug = "op-" + name.split()[0].lower()
    result = await invoke(["operator", slug, "update", "--identities", f"platform={user_id}"])
    assert result.exit_code == 0, result.output


async def _checked(invoke, tracker: harness.Tracker, *args: str) -> tuple[int, str]:
    """The exit code of `source check` and its output, the tracker's address made constant."""
    result = await invoke(["source", "check", *args])
    return result.exit_code, result.output.replace(tracker.base_url, "http://tracker")


CHECKED = "platform (github@v3)"


@pytest.mark.covers("source check", "source")
async def test_a_source_that_passes_every_probe_prints_an_all_pass_checklist_and_exits_0(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            source_checks.maps_text(profile) + _priority(profile),
        )
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
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(invoke, project, profile, tracker.base_url)
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
    project, invoke, credentials_home, profile
) -> None:
    urgent = _priority(profile) + f'"priority::urgent" = "{profile.badge_other_value}"\n'
    wrong = '\n[sources.platform.maps.links]\nduplicates = "related"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            source_checks.maps_text(profile) + f'ghost = "{profile.ref}"\n' + urgent + wrong,
        )
        result = await invoke(["source", "check", "--json"])
        base = tracker.base_url

    assert result.exit_code == 1
    assert json.loads(result.output.replace(base, "http://tracker")) == _json_report(
        *ACCESS_LINES,
        _line(
            "vocabulary",
            "fail",
            "maps.types.type: 'ghost' is not among the tracker's issue types",
            "correct it in [sources.platform.maps.types.type] in sources.toml, "
            "or create it on the tracker",
        ),
        _line(
            "vocabulary",
            "fail",
            f"maps.fields.{profile.badge}.labels: 'priority::urgent' is not among the "
            "tracker's labels",
            f"correct it in [sources.platform.maps.fields.{profile.badge}.labels] in sources.toml, "
            "or create it on the tracker",
        ),
        _line(
            "vocabulary",
            "fail",
            "maps.links: 'duplicates' is not a GitLab link type",
            "use one of relates_to, blocks, is_blocked_by in "
            "[sources.platform.maps.links] in sources.toml",
        ),
        _line(
            "coverage",
            "warn",
            "author pchat (id 4567) of platform/api#12 is in no operator's identities",
            "run `sq operator <slug> update --identities platform=4567`",
        ),
        _line(
            "coverage",
            "warn",
            "author asmith (id 4568) of platform/api#13 is in no operator's identities",
            "run `sq operator <slug> update --identities platform=4568`",
        ),
        ok=False,
    )


@pytest.mark.covers("source check", "source")
async def test_an_unmapped_label_and_an_unknown_author_are_warnings_and_exit_0(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_checks.route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"][0][
            "labels"
        ].append("priority::low")
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            source_checks.maps_text(profile) + _priority(profile),
        )
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
                f"maps.fields.{profile.badge}.labels",
                f"        fix: add it to [sources.platform.maps.fields.{profile.badge}.labels] in "
                "sources.toml",
                "  warn  author asmith (id 4568) of platform/api#13, a comment on "
                f"{profile.ref_id(4)} is in "
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
    project, invoke, credentials_home, profile
) -> None:
    by_label = f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n'
    only_squads = '\n[sources.platform.filter]\nlabels = "squads"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        issues = source_checks.route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"]
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
        await source_checks.declare(
            invoke, project, profile, tracker.base_url, by_label + only_squads
        )
        await _operator(invoke, "Alice Tester", "4567")
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        0,
        "\n".join(
            [
                HEADER,
                *ACCESS,
                "  pass  every value the maps and the filter name exists on the tracker",
                "  warn  author asmith (id 4568) of platform/api#13, platform/api#14 is in no "
                "operator's identities",
                "        fix: run `sq operator <slug> update --identities platform=4568`",
                "  pass  2 selected issue(s) map to no type and are skipped by the pull",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_an_issue_mapping_to_two_types_stays_a_coverage_warning(
    project, invoke, credentials_home, profile
) -> None:
    two = (
        source_checks.maps_text(profile)
        + f'\n[sources.platform.maps.types.labels]\nbug = "{profile.retype_to}"\n'
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(invoke, project, profile, tracker.base_url, two)
        _, output = await _checked(invoke, tracker, "platform")

    types = ", ".join(sorted([profile.ref, profile.retype_to]))
    assert output == "\n".join(
        [
            HEADER,
            *ACCESS,
            "  pass  every value the maps name exists on the tracker",
            f"  warn  platform/api#12 maps to several types: {types}",
            "        fix: make the maps in [sources.platform.maps.types] in sources.toml choose "
            "one",
            "  warn  author pchat (id 4567) of platform/api#12 is in no operator's identities",
            "        fix: run `sq operator <slug> update --identities platform=4567`",
            "  warn  author asmith (id 4568) of platform/api#13 is in no operator's identities",
            "        fix: run `sq operator <slug> update --identities platform=4568`",
            "",
        ]
    )


@pytest.mark.covers("source check", "--json")
async def test_a_disabled_source_is_still_listed_and_probed(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            head=source_checks.HEAD + "enabled = false\n",
        )
        await _operator(invoke, "Alice Tester", "4567")
        await _operator(invoke, "Bob Tester", "4568")
        result = await invoke(["source", "check", "--json"])
        base = tracker.base_url
        asked = [path for path, _, _ in tracker.requests]

    assert result.exit_code == 0
    assert json.loads(result.output.replace(base, "http://tracker")) == _json_report(
        *ACCESS_LINES,
        _line("vocabulary", "pass", "every value the maps name exists on the tracker"),
        _line("coverage", "pass", "every in-scope value, author and identity is accounted for"),
        enabled=False,
    )
    assert "/api/v4/version" in asked


@pytest.mark.covers("source check", "source")
async def test_a_filter_selecting_nothing_is_a_warning_and_confirms_no_label(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_checks.route(tracker, "/api/v4/projects/platform%2Fapi/issues")["body"] = []
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            source_checks.maps_text(profile) + _priority(profile),
        )
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
                f"  warn  maps.fields.{profile.badge}.labels: 'priority::high' is carried by no "
                "issue in "
                "the scope, so it cannot be confirmed among the tracker's labels",
                "        fix: correct it in "
                f"[sources.platform.maps.fields.{profile.badge}.labels] in "
                "sources.toml",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_scope_the_tracker_does_not_know_is_a_blocking_access_failure_naming_its_key(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            head=source_checks.HEAD.replace("api", "nope"),
        )
        gitlab = await _checked(invoke, tracker, "platform")
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        github_head = '[sources.platform]\nconnector = "github"\nrepository = "acme/nope"\n'
        await source_checks.declare(invoke, project, profile, tracker.base_url, head=github_head)
        github = await _checked(invoke, tracker, "platform")

    assert [gitlab, github] == [
        (
            1,
            "\n".join(
                [
                    HEADER,
                    *ACCESS[:2],
                    "  FAIL  the scope project 'platform/nope' does not exist or is not visible "
                    "to the token",
                    "        fix: correct `project` of source 'platform' in sources.toml",
                    "",
                ]
            ),
        ),
        (
            1,
            "\n".join(
                [
                    "platform (github@v3)",
                    "  pass  http://tracker/api/v3 answers",
                    "  pass  authenticated as squads-bot (id 1001)",
                    "  FAIL  the scope repository 'acme/nope' does not exist or is not visible "
                    "to the token",
                    "        fix: correct `repository` of source 'platform' in sources.toml",
                    "",
                ]
            ),
        ),
    ]


@pytest.mark.covers("source check", "source")
async def test_a_filter_accepting_no_listed_issue_is_a_warning_and_exits_0(
    project, invoke, credentials_home, profile
) -> None:
    only = '\n[sources.platform.filter]\nlabels = "priority::high and not priority::high"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke, project, profile, tracker.base_url, source_checks.maps_text(profile) + only
        )
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        0,
        "\n".join(
            [
                HEADER,
                *ACCESS,
                "  warn  the filter accepts none of the 2 issue(s) of the scope",
                "        fix: correct it in [sources.platform.filter] in sources.toml",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_filter_value_missing_on_a_listable_side_fails_and_on_an_unlistable_side_warns(
    project, invoke, credentials_home, profile
) -> None:
    ghost = '\n[sources.platform.filter]\nlabels = "ghost"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(
            invoke, project, profile, tracker.base_url, source_checks.maps_text(profile) + ghost
        )
        listable = await _checked(invoke, tracker, "platform")
    github_head = '[sources.platform]\nconnector = "github"\nrepository = "acme/api"\n'
    bug = '\n[sources.platform.filter]\ntype = "Ghost"\n'
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await source_checks.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            _github_maps(profile) + bug,
            head=github_head,
        )
        unlistable = await _checked(invoke, tracker, "platform")

    assert listable == (
        1,
        "\n".join(
            [
                HEADER,
                *ACCESS,
                "  FAIL  filter.labels: 'ghost' is not among the tracker's labels",
                "        fix: correct it in [sources.platform.filter] in sources.toml, or create "
                "it on the tracker",
                "  warn  the filter accepts none of the 2 issue(s) of the scope",
                "        fix: correct it in [sources.platform.filter] in sources.toml",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )
    assert unlistable == (
        0,
        "\n".join(
            [
                "platform (github@v3)",
                "  pass  http://tracker/api/v3 answers",
                "  pass  authenticated as squads-bot (id 1001)",
                "  pass  the token reads the issues of the scope",
                "  warn  filter.type: 'Ghost' is carried by no issue in the scope, so it cannot "
                "be confirmed among the tracker's issue types",
                "        fix: correct it in [sources.platform.filter] in sources.toml",
                "  warn  the filter accepts none of the 2 issue(s) of the scope",
                "        fix: correct it in [sources.platform.filter] in sources.toml",
                "  pass  every in-scope value, author and identity is accounted for",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_an_off_host_redirect_is_a_host_failure_naming_base_url_not_an_answer(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_checks.route(tracker, "/api/v4/version").update(
            status=302, headers={"Location": "http://203.0.113.9/elsewhere"}
        )
        await source_checks.declare(invoke, project, profile, tracker.base_url)
        code, output = await _checked(invoke, tracker, "platform")

    assert (code, output) == (
        1,
        "\n".join(
            [
                HEADER,
                "  FAIL  http://tracker/api/v4/version redirected to http://203.0.113.9/elsewhere, "
                "which is not the tracker's own address; the credential is not sent there. Set "
                "the source's base_url to the final address",
                "        fix: correct `base_url` of source 'platform' in sources.toml, "
                "or the host's network",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_github_enterprise_base_url_passes_access(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        base = f"{tracker.base_url}/api/v3"
        await source_connectors.declare(
            invoke,
            project,
            source_connectors.github(profile, base),
            f"{source_connectors.SECRET}\n",
        )
        result = await invoke(["source", "check", "platform"])
        output = result.output.replace(base, "http://tracker/api/v3")

    assert (result.exit_code, output) == (
        0,
        "\n".join(
            [
                CHECKED,
                "  pass  http://tracker/api/v3 answers",
                "  pass  authenticated as squads-bot (id 1001)",
                "  pass  the token reads the issues of the scope",
                "  pass  every value the maps name exists on the tracker",
                "  warn  author pchat (id 4567) of acme/api#12 is in no operator's identities",
                "        fix: run `sq operator <slug> update --identities platform=4567`",
                "  warn  author asmith (id 4568) of acme/api#13 is in no operator's identities",
                "        fix: run `sq operator <slug> update --identities platform=4568`",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_an_invalid_jql_filter_is_a_blocking_access_failure_with_jiras_own_reason(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3").replace("labels = squads", "labels ===")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        for route in tracker.routes:
            if route["path"] == "/rest/api/3/search/jql":
                route["status"] = 400
                route["body"] = {
                    "errorMessages": [
                        "Error in the JQL Query: The operator '===' is not supported."
                    ],
                    "errors": {},
                }
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        result = await invoke(["source", "check", "platform"])
        output = result.output.replace(tracker.base_url, "http://tracker")

    assert (result.exit_code, output) == (
        1,
        "\n".join(
            [
                "platform (jira@cloud-v3)",
                "  pass  http://tracker answers",
                "  pass  authenticated as Squads Bot "
                "(id 712020:0a1b2c3d-3333-4444-8888-cccccccccccc)",
                "  FAIL  the scope jql 'labels ===' is not accepted: http://tracker answered "
                "HTTP 400 for http://tracker/rest/api/3/search/jql?jql=labels+%3D%3D%3D&fields=summary"
                "&maxResults=1: Error in the JQL Query: The operator '===' is not supported.",
                "        fix: correct `jql` of source 'platform' in sources.toml",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_jira_data_center_personal_access_token_passes_access(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), f"{source_connectors.SECRET}\n"
        )
        result = await invoke(["source", "check", "platform"])
        output = result.output.replace(tracker.base_url, "http://tracker")

    assert (result.exit_code, output) == (
        0,
        "\n".join(
            [
                "platform (jira@dc-v2)",
                "  pass  http://tracker answers",
                "  pass  authenticated as squads-bot (id JIRAUSER10100)",
                "  pass  the token reads the issues of the scope",
                "  pass  every value the maps name exists on the tracker",
                "  warn  author asmith (id JIRAUSER10101) of PROJ-46 is in no operator's "
                "identities",
                "        fix: run `sq operator <slug> update --identities platform=JIRAUSER10101`",
                "  warn  author pchat (id JIRAUSER10102) of PROJ-45 is in no operator's identities",
                "        fix: run `sq operator <slug> update --identities platform=JIRAUSER10102`",
                "",
            ]
        ),
    )


@pytest.mark.covers("source check", "source")
async def test_a_rate_limit_and_an_unconfirmable_value_are_not_blamed_on_the_filter_or_the_map(
    project, invoke, credentials_home, profile
) -> None:
    unused = (
        source_connectors.github(profile)
        + f'\n[sources.platform.maps.types.type]\nBug = "{profile.ref}"\n'
    )
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, unused.format(base=tracker.base_url), f"{source_connectors.SECRET}\n"
        )
        confirmable = await invoke(["source", "check", "platform"])
        for route in tracker.routes:
            if route["path"] == "/api/v3/repos/acme/api/issues":
                route["status"], route["headers"] = 429, {"Retry-After": "0"}
        limited = await invoke(["source", "check", "platform"])
        base = tracker.base_url

    assert confirmable.output.replace(base, "http://tracker") == "".join(
        f"{line}\n"
        for line in [
            CHECKED,
            "  pass  http://tracker/api/v3 answers",
            "  pass  authenticated as squads-bot (id 1001)",
            "  pass  the token reads the issues of the scope",
            "  warn  maps.types.type: 'Bug' is carried by no issue in the scope, so it cannot be "
            "confirmed among the tracker's issue types",
            "        fix: correct it in [sources.platform.maps.types.type] in sources.toml",
            "  warn  author pchat (id 4567) of acme/api#12 is in no operator's identities",
            "        fix: run `sq operator <slug> update --identities platform=4567`",
            "  warn  author asmith (id 4568) of acme/api#13 is in no operator's identities",
            "        fix: run `sq operator <slug> update --identities platform=4568`",
        ]
    )
    assert limited.output.replace(base, "http://tracker") == "".join(
        f"{line}\n"
        for line in [
            CHECKED,
            "  pass  http://tracker/api/v3 answers",
            "  pass  authenticated as squads-bot (id 1001)",
            "  FAIL  http://tracker/api/v3 is rate limiting requests (HTTP 429); try again later",
            "        fix: wait until the tracker's limit resets, then run it again",
        ]
    )
