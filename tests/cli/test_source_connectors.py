"""The GitHub and Jira connectors, against recorded API responses on the loopback harness."""

import base64
import json
from typing import Any

import pytest

from tests import _tracker_harness as harness

pytestmark = pytest.mark.anyio

SECRET = "not-a-real-token"
EMAIL = "svc-squads@acme.example"


async def _declare(invoke, project, text: str, credential: str) -> None:
    """Write the squad's `sources.toml` override and store the `platform` credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    stored = await invoke(["source", "credential", "set", "platform"], input=credential)
    assert stored.exit_code == 0, stored.output


async def _shown(invoke, profile, tracker: harness.Tracker, number: int) -> dict[str, Any]:
    """`show --json` of the item, its tracker address made constant and its etag set aside."""
    out = await invoke([profile.ref, str(number), "show", "--json"])
    assert out.exit_code == 0, out.output
    shown = json.loads(out.output.replace(tracker.base_url, "http://tracker"))
    shown.pop("etag")
    return shown


async def _pull(invoke) -> dict[str, Any]:
    result = await invoke(["source", "pull", "platform", "--json"])
    assert result.exit_code == 0, (result.output, result.stderr, repr(result.exception))
    return json.loads(result.stdout)


# ------------------------------------------------------------------------------------ GitHub


def _github(profile, base: str = "{base}") -> str:
    return (
        f'[sources.platform]\nconnector = "github"\nrepository = "acme/api"\nbase_url = "{base}"\n'
        f'\n[sources.platform.maps.types.labels]\nsquads = "{profile.ref}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'"priority: high" = "{profile.badge_value}"\n'
    )


CHECKED = "platform (github@v3)"


@pytest.mark.covers("source pull", "source")
async def test_a_github_pull_skips_pull_requests_and_brings_comments_and_dependencies(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, _github(profile, tracker.base_url), f"{SECRET}\n")
        pulled = await _pull(invoke)
        first = await _shown(invoke, profile, tracker, 2)
        second = await _shown(invoke, profile, tracker, 3)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    assert asked == {f"Bearer {SECRET}"}
    assert pulled["sources"][0]["created"] == [profile.ref_id(2), profile.ref_id(3)]
    assert (first["title"], first["author"], first["refs"], first["badges"]) == (
        "Login fails on empty password",
        "source:platform",
        [f"{profile.ref_id(3)}:blocks"],
        {profile.badge: profile.badge_value},
    )
    assert first["source"] == {
        "name": "platform",
        "id": "I_kwDOAcmeApi12",
        "key": "acme/api#12",
        "state": "open",
        "updated_at": "2026-11-02T09:00:00Z",
        "author_id": "4567",
        "author_handle": "pchat",
    }
    assert first["views"]["source_description"]["body"] == (
        "Steps in [the runbook](http://tracker/acme/api/issues/docs/runbook.md), "
        "see #13 and acme/other#4.\n\n"
        '<img src="http://tracker/user-attachments/assets/abc">'
    )
    assert first["display"]["body"].split("\n\n", 1)[1] == (
        "Steps in [the runbook](http://tracker/acme/api/issues/docs/runbook.md), "
        f"see {profile.ref_id(3)} and acme/other#4.\n\n"
        '<img src="http://tracker/user-attachments/assets/abc">\n\n'
        f"## Description\n\n_TODO: describe this {profile.ref}._"
    )
    assert [(c["ts"], c["body"], c["attributes"]["source_id"]) for c in first["discussion"]] == [
        ("2026-11-02T09:14:00Z", "- The endpoint returns 500 when the body is empty.", "301")
    ]
    assert (second["source"]["state"], second["discussion"], second["refs"]) == ("closed", [], [])


@pytest.mark.covers("source pull", "source")
async def test_a_transferred_github_issue_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, _github(profile, tracker.base_url), f"{SECRET}\n")
        await _pull(invoke)
        first_page = next(
            r
            for r in tracker.routes
            if r["path"] == "/api/v3/repos/acme/api/issues" and "query" not in r
        )
        listing = first_page["body"]
        listing[0]["number"] = 40
        listing[0]["updated_at"] = "2026-11-05T08:00:00Z"
        listing[0]["repository_url"] = "https://ghe.example.com/api/v3/repos/repos/web"
        tracker.routes += [
            {"path": f"/api/v3/repos/repos/web/issues/40/{leaf}", "body": []}
            for leaf in ("comments", "dependencies/blocking")
        ]
        pulled = await _pull(invoke)
        shown = await _shown(invoke, profile, tracker, 2)

    assert [(r["created"], r["refreshed"]) for r in pulled["sources"]] == [([], 1)]
    assert (shown["id"], shown["source"]["key"], shown["source"]["updated_at"]) == (
        profile.ref_id(2),
        "repos/web#40",
        "2026-11-05T08:00:00Z",
    )


@pytest.mark.covers("<type> show", "--refresh")
async def test_refresh_reads_a_github_issue_moved_to_another_repository_out_of_filter(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, _github(profile, tracker.base_url), f"{SECRET}\n")
        await _pull(invoke)
        listing = next(
            r
            for r in tracker.routes
            if r["path"] == "/api/v3/repos/acme/api/issues" and "query" not in r
        )["body"]
        body: dict[str, Any] = dict(listing[0])
        tracker.routes.append({"path": "/api/v3/repos/acme/api/issues/12", "body": body})
        inside = await invoke([profile.ref, "2", "show", "--refresh", "--json"])
        first = (await _shown(invoke, profile, tracker, 2))["source"]["state"]
        body["repository_url"] = "https://ghe.example.com/api/v3/repos/acme/elsewhere"
        tracker.routes += [
            {"path": f"/api/v3/repos/acme/elsewhere/issues/12/{leaf}", "body": []}
            for leaf in ("comments", "dependencies/blocking")
        ]
        outside = await invoke([profile.ref, "2", "show", "--refresh", "--json"])
        second = (await _shown(invoke, profile, tracker, 2))["source"]["state"]

    assert (inside.exit_code, outside.exit_code) == (0, 0), (inside.output, outside.output)
    assert (first, second) == ("open", "out-of-filter")


@pytest.mark.covers("source check", "source")
async def test_a_github_enterprise_base_url_passes_access(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        base = f"{tracker.base_url}/api/v3"
        await _declare(invoke, project, _github(profile, base), f"{SECRET}\n")
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


# ------------------------------------------------------------------------------------ Jira
USER_FIELD = f"{EMAIL}\n{SECRET}\n"


def _jira(profile, version: str, base: str = "{base}") -> str:
    return (
        f'[sources.platform]\nconnector = "jira"\nversion = "{version}"\njql = "labels = squads"\n'
        f'base_url = "{base}"\n'
        f'\n[sources.platform.maps.types.type]\nBug = "{profile.ref}"\nTask = "{profile.ref}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.priority]\n"
        f'High = "{profile.badge_value}"\nLow = "{profile.badge_other_value}"\n'
    )


@pytest.mark.covers("source pull", "source")
async def test_a_jira_cloud_pull_maps_type_priority_link_and_state_and_converts_adf(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    jira += (
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'High = "{profile.badge_other_value}"\n'
    )
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        pulled = await _pull(invoke)
        first = await _shown(invoke, profile, tracker, 2)
        second = await _shown(invoke, profile, tracker, 3)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    basic = base64.b64encode(f"{EMAIL}:{SECRET}".encode()).decode()
    assert asked == {f"Basic {basic}"}
    assert pulled["sources"][0]["created"] == [profile.ref_id(2), profile.ref_id(3)]
    assert (first["title"], first["refs"], first["badges"]) == (
        "Login fails on empty password",
        [f"{profile.ref_id(3)}:blocks"],
        {profile.badge: profile.badge_value},
    )
    assert first["source"] == {
        "name": "platform",
        "id": "10042",
        "key": "PROJ-45",
        "state": "open",
        "updated_at": "2026-11-02T09:00:00.000Z",
        "author_id": "712020:0a1b2c3d-2222-4444-8888-bbbbbbbbbbbb",
        "author_handle": "712020:0a1b2c3d-2222-4444-8888-bbbbbbbbbbbb",
    }
    assert first["views"]["source_description"]["body"] == "Steps: see **PROJ-46** and the runbook."
    assert first["display"]["body"].split("\n\n", 1)[1] == (
        f"Steps: see **{profile.ref_id(3)}** and the runbook.\n\n## Description\n\n"
        f"_TODO: describe this {profile.ref}._"
    )
    assert [(c["author"].split(" via")[0], c["body"]) for c in first["discussion"]] == [
        ('"Alice Smith"', "- The endpoint returns 500 when the body is empty."),
        ('"Pierre Chat"', "- Fixed in **main**"),
    ]
    assert (second["source"]["state"], second["discussion"], second["refs"]) == ("closed", [], [])
    assert second["badges"] == {profile.badge: profile.badge_other_value}


@pytest.mark.covers("source pull", "source")
async def test_a_jira_issue_under_a_security_level_is_not_imported_and_the_report_counts_it(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        first_page = next(
            r for r in tracker.routes if r["path"] == "/rest/api/3/search/jql" and "query" not in r
        )
        first_page["body"]["issues"][0]["fields"]["security"] = {"id": "10000", "name": "Staff"}
        pulled = await _pull(invoke)

    [report] = pulled["sources"]
    assert (report["created"], report["restricted"]) == ([profile.ref_id(2)], 1)


@pytest.mark.covers("<type> show", "--refresh")
async def test_refresh_reads_a_jira_issue_that_gains_a_security_level_gone_and_its_item_stays(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        await _pull(invoke)
        one = next(r for r in tracker.routes if r["path"] == "/rest/api/3/issue/10042")
        one["body"]["fields"]["security"] = {"id": "10000", "name": "Staff"}
        refreshed = await invoke([profile.ref, "2", "show", "--refresh", "--json"])
        shown = await _shown(invoke, profile, tracker, 2)

    assert refreshed.exit_code == 0, (refreshed.output, refreshed.stderr)
    assert shown["source"]["state"] == "gone"


@pytest.mark.covers("source pull", "source")
async def test_a_jira_issue_moved_to_another_project_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        await _pull(invoke)
        first_page = next(
            r for r in tracker.routes if r["path"] == "/rest/api/3/search/jql" and "query" not in r
        )
        moved = first_page["body"]["issues"][0]
        moved["key"] = "OPS-7"
        moved["fields"]["updated"] = "2026-11-05T08:00:00.000+0000"
        pulled = await _pull(invoke)
        shown = await _shown(invoke, profile, tracker, 2)

    assert [(r["created"], r["refreshed"]) for r in pulled["sources"]] == [([], 1)]
    assert (shown["id"], shown["source"]["id"], shown["source"]["key"]) == (
        profile.ref_id(2),
        "10042",
        "OPS-7",
    )


@pytest.mark.covers("source check", "source")
async def test_an_invalid_jql_filter_is_a_blocking_access_failure_with_jiras_own_reason(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3").replace("labels = squads", "labels ===")
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
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
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


@pytest.mark.covers("source pull", "source")
async def test_a_jira_data_center_pull_converts_wiki_markup_with_a_personal_access_token(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), f"{SECRET}\n")
        pulled = await _pull(invoke)
        first = await _shown(invoke, profile, tracker, 2)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    assert asked == {f"Bearer {SECRET}"}
    assert pulled["sources"][0]["created"] == [profile.ref_id(2), profile.ref_id(3)]
    assert first["views"]["source_description"]["body"] == (
        "## Steps\n- open the login page\n- submit an **empty** password\n\n"
        "See [the runbook](https://wiki.acme.example/runbook) and PROJ-46."
    )
    assert first["source"]["author_id"] == "JIRAUSER10102"
    assert [(c["author"].split(" via")[0], c["body"]) for c in first["discussion"]] == [
        ('"Alice Smith"', "- The endpoint returns **500** when the body is empty.")
    ]
    assert (first["refs"], first["badges"]) == (
        [f"{profile.ref_id(3)}:blocks"],
        {profile.badge: profile.badge_value},
    )


@pytest.mark.covers("source check", "source")
async def test_a_jira_data_center_personal_access_token_passes_access(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), f"{SECRET}\n")
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


@pytest.mark.covers("source credential remove", "source")
async def test_a_jira_source_without_a_version_fails_at_load_listing_the_known_versions(
    project, invoke, credentials_home, profile
) -> None:
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    declared = _jira(profile, "x", "http://127.0.0.1:9").replace('version = "x"\n', "")
    path.write_text(declared, encoding="utf-8")

    result = await invoke(["source", "credential", "remove", "platform"])

    assert (result.exit_code, result.output.replace(str(path), "sources.toml")) == (
        1,
        "error: sources.toml: invalid sources after merge:\n  source 'platform': connector 'jira' "
        "has several versions, so `version` is required (known: cloud-v3, dc-v2)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_a_source_without_a_scope_or_with_a_badly_written_map_fails_at_load(
    project, invoke, credentials_home, profile
) -> None:
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    declared = _github(profile, "http://127.0.0.1:9")
    unsided = declared.replace(
        "[sources.platform.maps.types.labels]", "[sources.platform.maps.types]"
    )
    wrong_side = declared.replace(
        f"[sources.platform.maps.fields.{profile.badge}.labels]",
        f"[sources.platform.maps.fields.{profile.badge}.priority]",
    )
    results = []
    for text in (declared.replace('repository = "acme/api"\n', ""), unsided, wrong_side):
        path.write_text(text)
        result = await invoke(["source", "list", "--json"])
        results.append((result.exit_code, result.output.replace(str(path), "sources.toml")))

    head = "error: sources.toml: invalid sources after merge:\n  source 'platform': "
    assert results == [
        (1, head + "no scope key; name exactly one of: repository\n"),
        (
            1,
            head + "maps.types.squads is a value, not a side: write it under "
            "maps.types.<side>, one of: labels, type\n",
        ),
        (
            1,
            head + "maps name the side 'priority', which the connector does not have "
            "(known: labels, type)\n",
        ),
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_vanished_issue_costs_only_itself_and_a_failing_source_only_itself(
    project, invoke, credentials_home, profile
) -> None:
    other = (
        '\n[sources.other]\nconnector = "github"\nrepository = "acme/other"\nbase_url = "{base}"\n'
    )
    other += f'\n[sources.other.maps.types.labels]\nother = "{profile.ref}"\n'
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        text = _github(profile, tracker.base_url) + other.format(base=tracker.base_url)
        await _declare(invoke, project, text, f"{SECRET}\n")
        comments = next(r for r in tracker.routes if r["path"].endswith("/issues/12/comments"))
        comments["status"] = 404
        named = await _pull(invoke)
        second_page = next(r for r in tracker.routes if r.get("query") == {"page": "2"})
        second_page["status"] = 500
        unnamed = await invoke(["source", "pull", "--json"])

    assert [(r["created"], r["lines"]) for r in named["sources"]] == [
        (
            [profile.ref_id(2)],
            [
                "acme/api#12: skipped, the tracker stopped returning it while it was read",
                "acme/api#13: 1 link(s) not followed, no item holds acme/api#12",
            ],
        )
    ]
    reports = {r["name"]: r for r in json.loads(unnamed.stdout)["sources"]}
    assert unnamed.exit_code == 1
    assert (reports["platform"]["failed"], reports["other"]["failed"]) == (True, False)
    assert reports["platform"]["left_out"].replace(tracker.base_url, "http://tracker") == (
        "http://tracker/api/v3 answered HTTP 500 for "
        "http://tracker/api/v3/repos/acme/api/issues?state=all&per_page=100&page=2"
    )


@pytest.mark.covers("source pull", "source")
async def test_a_listing_row_without_a_state_fails_the_source_and_leaves_the_item_as_stored(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, _github(profile, tracker.base_url), f"{SECRET}\n")
        await _pull(invoke)
        first_page = next(
            r
            for r in tracker.routes
            if r["path"] == "/api/v3/repos/acme/api/issues" and "query" not in r
        )
        del first_page["body"][0]["state"]
        result = await invoke(["source", "pull", "--json"])
        shown = await _shown(invoke, profile, tracker, 2)

    [report] = json.loads(result.stdout)["sources"]
    assert (result.exit_code, report["failed"], shown["source"]["state"]) == (1, True, "open")
    assert report["left_out"] == "an issue without an identity or a known state"


@pytest.mark.covers("source pull", "source")
async def test_a_jira_page_without_a_total_fails_the_source_and_marks_nothing_out_of_filter(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), f"{SECRET}\n")
        await _pull(invoke)
        first_page = next(
            r for r in tracker.routes if r["path"].endswith("/search") and "query" not in r
        )
        del first_page["body"]["total"]
        first_page["body"]["issues"][0]["fields"]["updated"] = "2026-11-06T09:00:00.000+0000"
        result = await invoke(["source", "pull", "--json"])
        shown = await _shown(invoke, profile, tracker, 3)

    [report] = json.loads(result.stdout)["sources"]
    assert (result.exit_code, report["failed"], shown["source"]["state"]) == (1, True, "closed")
    assert report["left_out"] == "a page of a listing gives no numeric total"


@pytest.mark.covers("operator update", "--identities")
async def test_a_jira_cloud_handle_binds_only_on_an_exact_match_or_an_account_id(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    pierre = "712020:0a1b2c3d-2222-4444-8888-bbbbbbbbbbbb"
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
        update = ["operator", "op-alice", "update", "--identities"]
        prefix = await invoke([*update, "platform=@Pierre"])
        exact = await invoke([*update, "platform=@Pierre Chat"])
        shown = await invoke(["operator", "op-alice", "show", "--json"])
        by_id = await invoke([*update, f"platform=@{pierre}"])

    assert (prefix.exit_code, " ".join(prefix.output.split())) == (
        1,
        "error: no one user has the display name or email 'Pierre' exactly; Jira found Pierre "
        f"Martin ({pierre}). Name the account as @<accountId>",
    )
    assert (exact.exit_code, by_id.exit_code) == (0, 0)
    assert json.loads(shown.output)["identities"] == {"platform": pierre}


@pytest.mark.covers("source check", "source")
async def test_a_rate_limit_and_an_unconfirmable_value_are_not_blamed_on_the_filter_or_the_map(
    project, invoke, credentials_home, profile
) -> None:
    unused = _github(profile) + f'\n[sources.platform.maps.types.type]\nBug = "{profile.ref}"\n'
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await _declare(invoke, project, unused.format(base=tracker.base_url), f"{SECRET}\n")
        confirmable = await invoke(["source", "check", "platform"])
        for route in tracker.routes:
            if route["path"] == "/api/v3/repos/acme/api/issues":
                route["status"], route["headers"] = 429, {"Retry-After": "0"}
        limited = await invoke(["source", "check", "platform"])
        base = tracker.base_url

    assert confirmable.output.replace(base, "http://tracker").splitlines()[4:6] == [
        "  warn  maps.types.type: 'Bug' is carried by no issue in the scope, so it cannot be "
        "confirmed among the tracker's issue types",
        "        fix: correct it in [sources.platform.maps.types.type] in sources.toml",
    ]
    assert limited.output.replace(base, "http://tracker").splitlines()[3:5] == [
        "  FAIL  http://tracker/api/v3 is rate limiting requests (HTTP 429); try again later",
        "        fix: wait until the tracker's limit resets, then run it again",
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_jira_is_blocked_by_link_read_from_the_inward_side_makes_the_ref_on_the_blocker(
    project, invoke, credentials_home, profile
) -> None:
    jira = _jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        blocker = next(r for r in tracker.routes if r["path"] == "/rest/api/3/issue/10042")
        blocker["body"]["fields"]["issuelinks"] = []
        await _declare(invoke, project, jira.format(base=tracker.base_url), USER_FIELD)
        await _pull(invoke)
        first = await _shown(invoke, profile, tracker, 2)
        second = await _shown(invoke, profile, tracker, 3)

    assert (first["refs"], second["refs"]) == ([f"{profile.ref_id(3)}:blocks"], [])
