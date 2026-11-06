"""`sq source pull`: what a pull fetches, maps, imports and reports, per connector."""

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from tests import _tracker_harness as harness
from tests.cli import _source_checks as source_checks
from tests.cli import _source_connectors as source_connectors
from tests.cli import _source_links as source_links
from tests.cli import _source_pulls as source_pulls
from tests.cli._output import MANAGER_ROW, pull_document, pull_report, read_json, without_hashes
from tests.cli._pulled import BASE, COMMENT, DESCRIPTION, RECORDS, item, shown_item, without_digests

pytestmark = pytest.mark.anyio


SECRET = "glpat-not-a-real-token"


SAMPLES = Path(__file__).parents[1] / "fixtures" / "converters"


def _types(profile) -> str:
    return f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n'


_FILTER = "[sources.platform.filter]\nlabels = '{}'\n"


def _notes(tracker: harness.Tracker, issue: int) -> list[dict[str, Any]]:
    route = next(r for r in tracker.routes if r["path"].endswith(f"/issues/{issue}/notes"))
    return route["body"]


async def _state(invoke, profile, tracker: harness.Tracker) -> tuple[str, str]:
    """Every item as `show --json` prints it, and the reflog: what a pull that writes nothing
    leaves as it was."""
    shown = [await invoke([profile.ref, str(n), "show", "--json"]) for n in (2, 3)]
    reflog = await invoke(["reflog", "--json"])
    return "".join(s.output for s in shown), reflog.output


def _links(tracker: harness.Tracker, issue: int) -> dict[str, Any]:
    return next(r for r in tracker.routes if r["path"].endswith(f"/issues/{issue}/links"))


@pytest.mark.covers("source pull", "source")
async def test_a_pull_on_a_source_failing_access_prints_the_checklist_line_and_writes_nothing(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(invoke, project, profile, tracker.base_url)
        source_checks.failing_token(tracker)
        before = (await invoke(["reflog", "--json"])).output
        stopped, asked = await source_checks.stopped(
            invoke, tracker, ["source", "pull", "platform"]
        )
        after = (await invoke(["reflog", "--json"])).output

    assert stopped == source_checks.TOKEN_REFUSED
    assert before == after
    assert asked == ["/api/v4/version", "/api/v4/user"]


@pytest.mark.covers("source pull", "--json")
async def test_an_unnamed_pull_reports_a_source_failing_access_pulls_the_others_and_exits_1(
    project, invoke, credentials_home, profile
) -> None:
    with (
        harness.serve(harness.load_routes("gitlab/routes.json")) as healthy,
        harness.serve(harness.load_routes("gitlab/routes.json")) as refusing,
    ):
        source_checks.failing_token(refusing)
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        maps = source_checks.maps_text(profile)
        path.write_text(
            "".join(
                f'[sources.{name}]\nconnector = "gitlab"\nproject = "platform/api"\n'
                f'base_url = "{tracker.base_url}"\n{maps.replace("platform", name)}\n'
                for name, tracker in (("platform", healthy), ("other", refusing))
            ),
            encoding="utf-8",
        )
        for name in ("platform", "other"):
            stored = await invoke(
                ["source", "credential", "set", name], input=f"{source_checks.SECRET}\n"
            )
            assert stored.exit_code == 0, stored.output
        result = await invoke(["source", "pull", "--json"])
        shown = await invoke([profile.ref, "2", "show", "--json"])
        refusing_url = refusing.base_url

    assert result.exit_code == 1
    assert json.loads(result.stdout.replace(refusing_url, "http://tracker")) == pull_document(
        pull_report(
            "other",
            failed=True,
            left_out="http://tracker did not accept the token: http://tracker rejected the "
            "credential (HTTP 401)\n  fix: run `sq source credential set other` with a valid "
            "personal or project token",
        ),
        pull_report("platform", created=[profile.ref_id(2), profile.ref_id(3)]),
    )
    assert shown.exit_code == 0


@pytest.mark.covers("source pull", "source")
async def test_a_github_pull_skips_pull_requests_and_brings_comments_and_dependencies(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await source_connectors.declare(
            invoke,
            project,
            source_connectors.github(profile, tracker.base_url),
            f"{source_connectors.SECRET}\n",
        )
        pulled = await source_connectors.pull(invoke)
        first = await shown_item(invoke, profile, tracker, 2)
        second = await shown_item(invoke, profile, tracker, 3)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    assert asked == {f"Bearer {source_connectors.SECRET}"}
    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    assert first == source_connectors.github_item(profile, 2, 12)
    assert second == source_connectors.github_item(profile, 3, 13)


@pytest.mark.covers("source pull", "source")
async def test_a_transferred_github_issue_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await source_connectors.declare(
            invoke,
            project,
            source_connectors.github(profile, tracker.base_url),
            f"{source_connectors.SECRET}\n",
        )
        await source_connectors.pull(invoke)
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
        pulled = await source_connectors.pull(invoke)
        shown = await shown_item(invoke, profile, tracker, 2)

    assert pulled == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[f"{profile.ref_id(2)}: comment 301 was deleted on the tracker; kept"],
        )
    )
    moved = source_connectors.github_record(
        12, key="repos/web#40", updated_at="2026-11-05T08:00:00Z"
    )
    assert shown == source_connectors.github_item(profile, 2, 12, "repos/web", source=moved)


@pytest.mark.covers("source pull", "source")
async def test_a_jira_cloud_pull_maps_type_priority_link_and_state_and_converts_adf(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3")
    jira += (
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'High = "{profile.badge_other_value}"\n'
    )
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        pulled = await source_connectors.pull(invoke)
        first = await shown_item(invoke, profile, tracker, 2)
        second = await shown_item(invoke, profile, tracker, 3)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    basic = base64.b64encode(
        f"{source_connectors.EMAIL}:{source_connectors.SECRET}".encode()
    ).decode()
    assert asked == {f"Basic {basic}"}
    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    assert first == source_connectors.jira_cloud_item(profile, 2)
    assert second == source_connectors.jira_cloud_item(profile, 3)


@pytest.mark.covers("source pull", "source")
async def test_a_jira_issue_under_a_security_level_is_not_imported_and_the_report_counts_it(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        first_page = next(
            r for r in tracker.routes if r["path"] == "/rest/api/3/search/jql" and "query" not in r
        )
        first_page["body"]["issues"][0]["fields"]["security"] = {"id": "10000", "name": "Staff"}
        pulled = await source_connectors.pull(invoke)

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            restricted=1,
            lines=["PROJ-46: 1 link(s) not followed, no item holds PROJ-45"],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_a_jira_issue_moved_to_another_project_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        await source_connectors.pull(invoke)
        first_page = next(
            r for r in tracker.routes if r["path"] == "/rest/api/3/search/jql" and "query" not in r
        )
        moved = first_page["body"]["issues"][0]
        moved["key"] = "OPS-7"
        moved["fields"]["updated"] = "2026-11-05T08:00:00.000+0000"
        pulled = await source_connectors.pull(invoke)
        shown = await shown_item(invoke, profile, tracker, 2)

    assert pulled == pull_document(pull_report(refreshed=1, unchanged=1))
    moved = {
        **source_connectors.jira_cloud_item(profile, 2)["source"],
        "key": "OPS-7",
        "updated_at": "2026-11-05T08:00:00.000Z",
    }
    assert shown == source_connectors.jira_cloud_item(profile, 2, source=moved)


@pytest.mark.covers("source pull", "source")
async def test_a_jira_data_center_pull_converts_wiki_markup_with_a_personal_access_token(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), f"{source_connectors.SECRET}\n"
        )
        pulled = await source_connectors.pull(invoke)
        first = await shown_item(invoke, profile, tracker, 2)
        asked = {headers["Authorization"] for _, _, headers in tracker.requests}

    assert asked == {f"Bearer {source_connectors.SECRET}"}
    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    steps = (
        "## Steps\n- open the login page\n- submit an **empty** password\n\n"
        "See [the runbook](https://wiki.acme.example/runbook) and PROJ-46."
    )
    comment = source_connectors.jira_comment(
        "alice",
        "asmith",
        "Alice Smith",
        "JIRAUSER10101",
        "- The endpoint returns **500** when the body is empty.",
        source_id="20001",
        updated="2026-11-02T09:20:31.000Z",
        url=f"{BASE}/secure/ViewProfile.jspa?name=asmith",
    )
    record = {
        **source_connectors.jira_cloud_item(profile, 2)["source"],
        "author_id": "JIRAUSER10102",
        "author_handle": "pchat",
    }
    assert first == item(
        profile,
        2,
        description=steps,
        rendered=steps.replace("PROJ-46", profile.ref_id(3)),
        url=f"{BASE}/browse/PROJ-45",
        source=record,
        discussion=[comment],
    )


@pytest.mark.covers("source pull", "source")
async def test_a_vanished_issue_costs_only_itself_and_a_failing_source_only_itself(
    project, invoke, credentials_home, profile
) -> None:
    other = (
        '\n[sources.other]\nconnector = "github"\nrepository = "acme/other"\nbase_url = "{base}"\n'
    )
    other += f'\n[sources.other.maps.types.labels]\nother = "{profile.ref}"\n'
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        text = source_connectors.github(profile, tracker.base_url) + other.format(
            base=tracker.base_url
        )
        await source_connectors.declare(invoke, project, text, f"{source_connectors.SECRET}\n")
        comments = next(r for r in tracker.routes if r["path"].endswith("/issues/12/comments"))
        comments["status"] = 404
        named = await source_connectors.pull(invoke)
        second_page = next(r for r in tracker.routes if r.get("query") == {"page": "2"})
        second_page["status"] = 500
        unnamed = await invoke(["source", "pull", "--json"])
        base = tracker.base_url

    assert named == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            lines=[
                "acme/api#12: skipped, the tracker stopped returning it while it was read",
                "acme/api#13: 1 link(s) not followed, no item holds acme/api#12",
            ],
        )
    )
    assert unnamed.exit_code == 1
    assert json.loads(unnamed.stdout.replace(base, "http://tracker")) == pull_document(
        pull_report(
            failed=True,
            left_out=(
                "http://tracker/api/v3 answered HTTP 500 for "
                "http://tracker/api/v3/repos/acme/api/issues?state=all&per_page=100&page=2"
            ),
        ),
        pull_report("other"),
    )


@pytest.mark.covers("source pull", "source")
async def test_a_listing_row_without_a_state_fails_the_source_and_leaves_the_item_as_stored(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("github/routes.json")) as tracker:
        await source_connectors.declare(
            invoke,
            project,
            source_connectors.github(profile, tracker.base_url),
            f"{source_connectors.SECRET}\n",
        )
        await source_connectors.pull(invoke)
        first_page = next(
            r
            for r in tracker.routes
            if r["path"] == "/api/v3/repos/acme/api/issues" and "query" not in r
        )
        del first_page["body"][0]["state"]
        result = await invoke(["source", "pull", "--json"])
        shown = await shown_item(invoke, profile, tracker, 2)

    assert (result.exit_code, json.loads(result.stdout)) == (
        1,
        pull_document(
            pull_report(
                failed=True,
                left_out="an issue without an identity or a known state",
            )
        ),
    )
    assert shown == source_connectors.github_item(profile, 2, 12)


@pytest.mark.covers("source pull", "source")
async def test_a_jira_page_without_a_total_fails_the_source_and_marks_nothing_out_of_filter(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "dc-v2")
    with harness.serve(harness.load_routes("jira-dc/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), f"{source_connectors.SECRET}\n"
        )
        await source_connectors.pull(invoke)
        first_page = next(
            r for r in tracker.routes if r["path"].endswith("/search") and "query" not in r
        )
        del first_page["body"]["total"]
        first_page["body"]["issues"][0]["fields"]["updated"] = "2026-11-06T09:00:00.000+0000"
        result = await invoke(["source", "pull", "--json"])
        shown = await shown_item(invoke, profile, tracker, 3)

    assert (result.exit_code, json.loads(result.stdout)) == (
        1,
        pull_document(
            pull_report(
                failed=True,
                left_out="a page of a listing gives no numeric total",
            )
        ),
    )
    closed = {
        "name": "platform",
        "id": "10043",
        "key": "PROJ-46",
        "state": "closed",
        "updated_at": "2026-11-03T10:30:00.000Z",
        "author_id": "JIRAUSER10101",
        "author_handle": "asmith",
    }
    assert shown == item(profile, 3, url=f"{BASE}/browse/PROJ-46", source=closed)


@pytest.mark.covers("source pull", "source")
async def test_a_jira_is_blocked_by_link_read_from_the_inward_side_makes_the_ref_on_the_blocker(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3")
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        blocker = next(r for r in tracker.routes if r["path"] == "/rest/api/3/issue/10042")
        blocker["body"]["fields"]["issuelinks"] = []
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        await source_connectors.pull(invoke)
        first = await shown_item(invoke, profile, tracker, 2)
        second = await shown_item(invoke, profile, tracker, 3)

    assert first == source_connectors.jira_cloud_item(profile, 2)
    assert second == source_connectors.jira_cloud_item(profile, 3)


@pytest.mark.covers("source pull", "source")
@pytest.mark.parametrize("converter", ["adf", "jira-wiki", "github-md"])
async def test_a_description_and_a_comment_in_the_converters_format_show_as_markdown(
    project, invoke, credentials_home, profile, converter
) -> None:
    written = (SAMPLES / converter / "input.txt").read_text(encoding="utf-8").rstrip("\n")
    expected = (SAMPLES / converter / "expected.md").read_text(encoding="utf-8").rstrip("\n")
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        for route in tracker.routes:
            body: Any = route.get("body")
            if route["path"] == "/api/v4/projects/platform%2Fapi/issues":
                body[0]["description"] = written
            elif route["path"] == "/api/v4/projects/platform%2Fapi/issues/12":
                body["description"] = written
            elif route["path"] == "/api/v4/projects/77/issues/12/notes":
                body[1]["body"] = written
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
            f'base_url = "{tracker.base_url}"\nconverter = "{converter}"\n{_types(profile)}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform"])
        assert pulled.exit_code == 0, pulled.output
        shown = await invoke([profile.ref, "2", "show", "--json"])
        base = tracker.base_url

    assert shown.exit_code == 0, shown.output
    document = without_digests(json.loads(shown.output.replace(base, BASE)))
    document.pop("etag")
    # A comment shows as one list entry, its lines indented under the marker.
    comment = {**COMMENT, "body": "- " + expected.replace("\n", "\n  ")}
    assert document == item(
        profile,
        2,
        badge=False,
        description=expected,
        rendered=expected,
        discussion=[comment],
    )


@pytest.mark.covers("source pull", "--json")
async def test_a_hostile_description_drops_only_its_issue_and_the_report_names_it(
    project, invoke, credentials_home, profile
) -> None:
    nested: dict[str, Any] = {"type": "paragraph"}
    for _ in range(400):
        nested = {"type": "blockquote", "content": [nested]}
    hostile = json.dumps({"type": "doc", "content": [nested]})
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        for route in tracker.routes:
            if route["path"] == "/api/v4/projects/platform%2Fapi/issues":
                route["body"][0]["description"] = hostile
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
            f'base_url = "{tracker.base_url}"\nconverter = "adf"\n{_types(profile)}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform", "--json"])

    assert pulled.exit_code == 0, pulled.output
    assert json.loads(pulled.stdout) == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            dropped=1,
            lines=[
                "platform/api#12: dropped, its text cannot be converted (ValueError)",
                "platform/api#13: 1 link(s) not followed, no item holds platform/api#12",
            ],
        )
    )


@pytest.mark.covers("source pull", "source")
@pytest.mark.parametrize(
    ("first", "second", "epic", "other"),
    [("epics", "stories", 2, 3), ("stories", "epics", 3, 2)],
    ids=["host-first", "target-first"],
)
async def test_a_link_between_issues_of_two_sources_on_one_tracker_makes_its_ref_in_either_order(
    project, invoke, credentials_home, first, second, epic, other, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_two(invoke, project, profile, tracker.base_url)
        one = await invoke(["source", "pull", first, "--json"])
        before = await shown_item(invoke, profile, tracker, 2)
        two = await invoke(["source", "pull", second, "--json"])
        host = await shown_item(invoke, profile, tracker, epic)

    assert (one.exit_code, two.exit_code) == (0, 0), (one.output, two.output)
    unfollowed = {
        "epics": "platform/api#12: 1 link(s) not followed, no item holds platform/api#13",
        "stories": "platform/api#13: 1 link(s) not followed, no item holds platform/api#12",
    }
    assert json.loads(one.stdout) == pull_document(
        pull_report(first, created=[profile.ref_id(2)], filtered_out=1, lines=[unfollowed[first]])
    )
    assert json.loads(two.stdout) == pull_document(
        pull_report(second, created=[profile.ref_id(3)], held_elsewhere=1)
    )
    if first == "epics":
        assert before == source_links.platform_item(
            profile,
            2,
            12,
            name="epics",
            refs=[],
            rendered=DESCRIPTION,
            updated_at="2026-11-02T09:14:00Z",
        )
    else:
        assert before == source_links.platform_item(profile, 2, 13, name="stories")
    assert host == source_links.platform_item(profile, epic, 12, name="epics", partner=other)


@pytest.mark.covers("source pull", "--json")
async def test_a_second_pull_of_two_split_sources_names_no_issue_the_other_holds(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_two(invoke, project, profile, tracker.base_url)
        await invoke(["source", "pull", "epics"])
        await invoke(["source", "pull", "stories"])
        again = [await invoke(["source", "pull", name, "--json"]) for name in ("epics", "stories")]

    assert [(r.exit_code, json.loads(r.stdout)) for r in again] == [
        (0, pull_document(pull_report("epics", unchanged=1, held_elsewhere=1))),
        (0, pull_document(pull_report("stories", unchanged=1, held_elsewhere=1))),
    ]


@pytest.mark.covers("source pull", "--json")
async def test_an_unnamed_pull_reports_no_link_unfollowed_that_a_later_source_makes(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_two(invoke, project, profile, tracker.base_url)
        pulled = await invoke(["source", "pull", "--json"])
        host = await shown_item(invoke, profile, tracker, 2)

    assert pulled.exit_code == 0, (pulled.output, pulled.stderr)
    assert json.loads(pulled.stdout) == pull_document(
        pull_report("epics", created=[profile.ref_id(2)], filtered_out=1),
        pull_report("stories", created=[profile.ref_id(3)], filtered_out=1),
    )
    assert host == source_links.platform_item(profile, 2, name="epics")


@pytest.mark.covers("source pull", "source")
async def test_a_source_leaves_an_issue_another_source_of_its_tracker_holds_and_says_so(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_overlap(invoke, project, profile, tracker)
        first = await invoke(["source", "pull", "narrow", "--json"])
        tracker.requests.clear()
        second = await invoke(["source", "pull", "wide", "--json"])
        detail_reads = [p for p, _q, _h in tracker.requests if p.endswith(("/notes", "/links"))]
        tasks = await invoke(["list", "--type", profile.ref, "--json"])

    assert (first.exit_code, second.exit_code) == (0, 0), (second.output, second.stderr)
    assert json.loads(second.stdout) == pull_document(
        pull_report(
            "wide",
            held_elsewhere=2,
            lines=[
                f"platform/api#12: held by {profile.ref_id(2)} of source 'narrow'",
                f"platform/api#13: held by {profile.ref_id(3)} of source 'narrow'",
            ],
        )
    )
    assert len(json.loads(tasks.stdout)) == 2
    assert detail_reads == []


@pytest.mark.covers("source pull", "--json")
async def test_one_unnamed_pull_of_two_overlapping_sources_makes_one_item_per_issue(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_overlap(invoke, project, profile, tracker)
        pulled = await invoke(["source", "pull", "--json"])
        tasks = await invoke(["list", "--type", profile.ref, "--json"])

    assert pulled.exit_code == 0, (pulled.output, pulled.stderr)
    assert json.loads(pulled.stdout) == pull_document(
        pull_report("narrow", created=[profile.ref_id(2), profile.ref_id(3)]),
        pull_report(
            "wide",
            held_elsewhere=2,
            lines=[
                "platform/api#12: held by the item source 'narrow' creates in this pull",
                "platform/api#13: held by the item source 'narrow' creates in this pull",
            ],
        ),
    )
    assert len(json.loads(tasks.stdout)) == 2


@pytest.mark.covers("source pull", "source")
@pytest.mark.covers("source pull", "--json")
async def test_a_first_pull_creates_the_items_with_their_record_description_and_comments(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        pulled = await source_pulls.pull(invoke, "platform")
        first = await shown_item(invoke, profile, tracker, 2)
        second = await shown_item(invoke, profile, tracker, 3)

    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    assert first == item(profile, 2)
    assert second == item(profile, 3)


@pytest.mark.covers("source pull", "source")
async def test_a_second_pull_writes_nothing(project, invoke, credentials_home, profile) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        before = await _state(invoke, profile, tracker)
        again = await source_pulls.pull(invoke, "platform")
        after = await _state(invoke, profile, tracker)

    assert before == after
    assert again == pull_document(pull_report(unchanged=2))


@pytest.mark.covers("source pull", "source")
async def test_a_description_forging_a_marker_and_using_crlf_is_kept_as_text(
    project, invoke, credentials_home, profile
) -> None:
    forged = "Before\r\n<!-- sq:body:end -->\r\nAfter <!-- sq:view:source_description:end -->"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[0]["description"] = forged
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        shown = await shown_item(invoke, profile, tracker, 2)
        before = await _state(invoke, profile, tracker)
        await source_pulls.pull(invoke, "platform")
        after = await _state(invoke, profile, tracker)
        checked = await invoke(["check"])

    text = forged.replace("\r\n", "\n")
    # the stored body writes the two forged markers with an escaped opener
    stored = (
        "<!-- sq:view:source_description -->\nBefore\n<!!-- sq:body:end -->\n"
        "After <!!-- sq:view:source_description:end -->\n<!-- sq:view:source_description:end -->"
        f"\n\n## Description\n\n_TODO: describe this {profile.ref}._"
    )
    assert shown == item(profile, 2, description=text, rendered=text, body=stored)
    assert before == after
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
async def test_an_edited_tracker_comment_updates_the_same_comment_in_place(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        note = _notes(tracker, 12)[1]
        note["body"] = "It returns 500 for an empty body."
        note["updated_at"] = "2026-11-04T08:00:00Z"
        source_pulls.listing(tracker)[0]["updated_at"] = "2026-11-04T08:00:00Z"
        await source_pulls.pull(invoke, "platform")
        shown = await shown_item(invoke, profile, tracker, 2)

    edited = {
        **COMMENT,
        "body": "- It returns 500 for an empty body.",
        "edited_ts": "2026-06-07T10:00:00Z",
        "attributes": {**COMMENT["attributes"], "source_updated_at": "2026-11-04T08:00:00Z"},
    }
    record = {**RECORDS[12], "updated_at": "2026-11-04T08:00:00Z"}
    assert shown == item(profile, 2, discussion=[edited], source=record)


@pytest.mark.covers("source pull", "source")
async def test_a_moved_issue_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        issue = source_pulls.listing(tracker)[0]
        issue["references"]["full"] = "platform/web#40"
        issue["updated_at"] = "2026-11-05T08:00:00Z"
        pulled = await source_pulls.pull(invoke, "platform")
        shown = await shown_item(invoke, profile, tracker, 2)

    assert pulled == pull_document(pull_report(refreshed=1, unchanged=1))
    moved = {**RECORDS[12], "key": "platform/web#40", "updated_at": "2026-11-05T08:00:00Z"}
    web = DESCRIPTION.replace("platform/api", "platform/web")
    assert shown == item(profile, 2, source=moved, description=web, rendered=web)


@pytest.mark.covers("source pull", "--json")
async def test_every_issue_a_pull_sees_lands_in_exactly_one_counter(
    project, invoke, credentials_home, profile
) -> None:
    def another(number: int, **changes: Any) -> dict[str, Any]:
        base = source_pulls.listing(tracker)[1]
        return {
            **base,
            "id": 9100 + number,
            "iid": number,
            "references": {"full": f"platform/api#{number}"},
            **changes,
        }

    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        source_pulls.listing(tracker).append(another(21))
        tracker.routes += [
            {"path": f"/api/v4/projects/77/issues/{n}/{leaf}", "body": []}
            for n in (21, 32)
            for leaf in ("notes", "links")
        ]
        await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[0].update(
            title="Login fails on a blank password", updated_at="2026-11-04T08:00:00Z"
        )
        source_pulls.listing(tracker).pop(2)
        source_pulls.listing(tracker).extend(
            [
                another(30, confidential=True),
                another(31, issue_type="incident"),
                another(32, title="  "),
            ]
        )
        second = await source_pulls.pull(invoke, "platform")

    (report,) = second["sources"]
    counters = (
        "refreshed",
        "unchanged",
        "dropped",
        "gone",
        "restricted",
        "held_elsewhere",
        "filtered_out",
        "skipped_no_type",
    )
    assert {name: report[name] for name in counters} == {
        "refreshed": 1,
        "unchanged": 1,
        "dropped": 1,
        "gone": 1,
        "restricted": 1,
        "held_elsewhere": 0,
        "filtered_out": 0,
        "skipped_no_type": 1,
    }
    assert len(report["created"]) + sum(report[name] for name in counters) == 6


@pytest.mark.covers("source pull", "--dry-run")
async def test_a_dry_run_counts_refreshed_unchanged_and_dropped_as_the_pull_does(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        listing = source_pulls.listing(tracker)
        listing[0].update(
            title="Login fails on a blank password", updated_at="2026-11-04T08:00:00Z"
        )
        listing.append(
            {
                **listing[1],
                "id": 9132,
                "iid": 32,
                "title": "  ",
                "references": {"full": "platform/api#32"},
            }
        )
        tracker.routes += [
            {"path": f"/api/v4/projects/77/issues/32/{leaf}", "body": []}
            for leaf in ("notes", "links")
        ]
        dry = await source_pulls.pull(invoke, "platform", "--dry-run")
        real = await source_pulls.pull(invoke, "platform")

    line = "platform/api#32: dropped, title must not be empty"
    report = pull_report(refreshed=1, unchanged=1, dropped=1, lines=[line])
    assert (dry, real) == (
        pull_document(report, dry_run=True),
        pull_document(report),
    )


@pytest.mark.covers("source pull", "source")
async def test_a_linked_issue_the_filter_lost_is_out_of_filter_or_gone_and_its_item_stays(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        outside = next(r for r in tracker.routes if r["path"].endswith("/issues/20"))["body"]
        gone = {**outside, "id": 9009, "iid": 21, "title": "Removed upstream"}
        gone["references"] = {"full": "platform/api#21"}
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        source_pulls.listing(tracker).extend([outside, gone])
        tracker.routes += [
            {"path": f"/api/v4/projects/77/issues/21/{leaf}", "body": []}
            for leaf in ("notes", "links")
        ]
        first = await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[:] = source_pulls.listing(tracker)[:2]
        second = await source_pulls.pull(invoke, "platform")
        records = [(await shown_item(invoke, profile, tracker, n))["source"] for n in (4, 5)]

    assert first == pull_document(pull_report(created=[profile.ref_id(n) for n in (2, 3, 4, 5)]))
    assert [(r["key"], r["state"]) for r in records] == [
        ("platform/api#20", "out-of-filter"),
        ("platform/api#21", "gone"),
    ]
    assert second == pull_document(
        pull_report(
            refreshed=1,
            unchanged=2,
            gone=1,
            lines=[
                f"platform/api#20: out-of-filter (outside the scope); {profile.ref_id(4)} stays",
                f"platform/api#21: deleted or no longer readable; {profile.ref_id(5)} stays",
            ],
        )
    )


@pytest.mark.covers("source pull", "--dry-run")
async def test_a_dry_run_writes_nothing(project, invoke, credentials_home, profile) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        before = (await invoke(["reflog", "--json"])).output
        planned = await source_pulls.pull(invoke, "platform", "--dry-run")
        listed = await read_json(invoke, ["list", "--json"])
        after = (await invoke(["reflog", "--json"])).output

    assert planned == pull_document(
        pull_report(
            created=["platform:gid://gitlab/Issue/9001", "platform:gid://gitlab/Issue/9002"]
        ),
        dry_run=True,
    )
    assert listed == [MANAGER_ROW]
    assert before == after


@pytest.mark.covers("source pull", "source")
async def test_a_named_source_without_a_credential_errors_naming_the_remedy(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await invoke(["source", "credential", "remove", "platform"])
        named = await invoke(["source", "pull", "platform"])
        unnamed = await invoke(["source", "pull", "--json"])

    assert (named.exit_code, named.output) == (
        1,
        "error: source 'platform' has no stored credential\n"
        "  fix: run `sq source credential set platform`\n",
    )
    assert unnamed.exit_code == 0
    assert json.loads(unnamed.stdout) == pull_document(
        pull_report(left_out="no stored credential; run `sq source credential set platform`")
    )
    assert tracker.requests == []


@pytest.mark.covers("source pull", "source")
async def test_two_items_holding_one_issue_are_both_refreshed_and_no_third_is_made(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, "")
        await source_pulls.pull(invoke, "platform")
        twin = json.loads((await invoke([profile.ref, "2", "show", "--json"])).output)["source"]
        # A second item mirrors the same issue: written as a pull would, then edited upstream.
        await invoke(["create", profile.host, "Parent", "--author", "manager"])
        parent = profile.host_id(4) if profile.ref in profile.needs_parent else None
        under = ["--parent", "4"] if parent else []
        await invoke(["create", profile.ref, "Twin", "--author", "manager", *under])
        path = next(
            project.squad_dir.joinpath(profile.ref_folder).glob(f"{profile.ref_prefix}-*twin.md")
        )
        record = "source:\n" + "".join(f"  {k}: '{v}'\n" for k, v in twin.items())
        text = path.read_text(encoding="utf-8").replace("\nstatus:", f"\n{record}status:", 1)
        path.write_text(text, encoding="utf-8")
        await invoke(["repair"])
        source_pulls.listing(tracker)[0]["updated_at"] = "2026-11-04T08:00:00Z"
        pulled = await source_pulls.pull(invoke, "platform")
        listed = await read_json(invoke, ["list", "--json"])
        twin_row = await shown_item(invoke, profile, tracker, 5)

    assert [r["id"] for r in listed if r["type"] == profile.ref] == [
        profile.ref_id(2),
        profile.ref_id(3),
        profile.ref_id(5),
    ]
    assert pulled == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[
                f"platform/api#12: held by {profile.ref_id(2)}, {profile.ref_id(5)}; "
                "each is refreshed"
            ],
        )
    )
    assert twin_row == item(
        profile,
        5,
        12,
        author="manager",
        parent=parent,
        source={**RECORDS[12], "updated_at": "2026-11-04T08:00:00Z"},
    )


@pytest.mark.covers("source pull", "source")
async def test_a_mapped_field_the_held_item_has_no_such_field_for_is_skipped_and_named(
    project, invoke, credentials_home, profile
) -> None:
    mapped = (
        f"\n[sources.platform.maps.fields.{profile.skipped_field}.labels]\n"
        f'bug = "{profile.skipped_value}"\n'
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, mapped)
        await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[0]["updated_at"] = "2026-11-04T08:00:00Z"
        pulled = await source_pulls.pull(invoke, "platform")

    assert pulled == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[
                f"platform/api#12: {profile.skipped_field} skipped, {profile.ref} items have "
                "no such field"
            ],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_a_named_pull_of_a_disabled_source_is_refused_and_an_unnamed_pull_skips_it(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, "enabled = false\n")
        named = await invoke(["source", "pull", "platform"])
        unnamed = await source_pulls.pull(invoke)
        listed = await read_json(invoke, ["list", "--json"])

    assert (named.exit_code, named.output) == (
        1,
        "error: source 'platform' is disabled (`enabled = false` in its sources.toml table); "
        "enable it to fetch from it\n",
    )
    assert unnamed == pull_document()
    assert listed == [MANAGER_ROW]
    assert tracker.requests == []


@pytest.mark.covers("source pull", "source")
async def test_an_issue_mapping_to_no_item_type_is_counted_not_named_and_not_detailed(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        source_pulls.listing(tracker)[1]["issue_type"] = "incident"
        pulled = await source_pulls.pull(invoke, "platform")
        asked = [path for path, _, _ in tracker.requests]
        shown = await invoke(["source", "pull", "platform"])

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            skipped_no_type=1,
            lines=["platform/api#12: 1 link(s) not followed, no item holds platform/api#13"],
        )
    )
    assert not [p for p in asked if "/issues/13" in p]
    assert (shown.exit_code, shown.output) == (
        0,
        "platform: unchanged 1, skipped 1 (no type)\n",
    )


@pytest.mark.covers("source pull", "source")
async def test_a_link_to_a_confidential_issue_makes_no_ref_and_no_line(
    project, invoke, credentials_home, profile
) -> None:
    secret = {
        "id": 9099,
        "iid": 14,
        "link_type": "relates_to",
        "confidential": True,
        "references": {"full": "platform/api#14"},
    }
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        route = next(
            r for r in tracker.routes if r["path"] == "/api/v4/projects/77/issues/12/links"
        )
        route["body"].append(secret)
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        pulled = await source_pulls.pull(invoke, "platform")

    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))


@pytest.mark.covers("source pull", "source")
async def test_an_issue_mapping_to_two_types_is_named_with_its_values_on_every_pull(
    project, invoke, credentials_home, profile
) -> None:
    two = f'\n[sources.platform.maps.types.labels]\nbug = "{profile.retype_to}"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, two)
        first = await source_pulls.pull(invoke, "platform")
        asked = [path for path, _, _ in tracker.requests]
        second = await source_pulls.pull(invoke, "platform")

    types = ", ".join(sorted([profile.ref, profile.retype_to]))
    expected = [f"platform/api#12: not created, the issue maps to several types: {types}"]
    assert first == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            skipped_no_type=1,
            lines=[
                *expected,
                "platform/api#13: 1 link(s) not followed, no item holds platform/api#12",
            ],
        )
    )
    assert second == pull_document(pull_report(unchanged=1, skipped_no_type=1, lines=expected))
    assert not [p for p in asked if "/issues/12/" in p]


@pytest.mark.covers("source pull", "source")
async def test_an_issue_whose_labels_map_a_field_to_two_values_names_them_and_leaves_the_field(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                f'"priority::high" = "{profile.badge_value}"\n',
                f'"priority::high" = "{profile.badge_value}"\n'
                f'bug = "{profile.badge_other_value}"\n',
            ),
            encoding="utf-8",
        )
        pulled = await source_pulls.pull(invoke, "platform")

    values = ", ".join(sorted([profile.badge_value, profile.badge_other_value]))
    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2), profile.ref_id(3)],
            lines=[f"platform/api#12: {profile.badge} left alone, its values map to {values}"],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_the_filter_selects_issues_and_counts_the_rejected_ones(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(
            invoke, project, profile, tracker.base_url, _FILTER.format("squads and not bug")
        )
        pulled = await source_pulls.pull(invoke, "platform")
        shown = await invoke(["source", "pull", "platform"])

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            filtered_out=1,
            lines=["platform/api#13: 1 link(s) not followed, no item holds platform/api#12"],
        )
    )
    assert (shown.exit_code, shown.output) == (
        0,
        "platform: unchanged 1, filtered out 1\n",
    )


@pytest.mark.covers("source pull", "source")
async def test_a_filter_reads_not_before_and_and_and_before_or(
    project, invoke, credentials_home, profile
) -> None:
    ruled = "not w or x and y"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[0]["labels"] = ["w", "x", "y"]
        source_pulls.listing(tracker)[1]["labels"] = []
        await source_pulls.declare(
            invoke, project, profile, tracker.base_url, _FILTER.format(ruled)
        )
        pulled = await source_pulls.pull(invoke, "platform")

    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))


@pytest.mark.covers("source pull", "source")
async def test_a_quoted_filter_value_takes_an_escaped_quote_and_backslash_as_one_character(
    project, invoke, credentials_home, profile
) -> None:
    expression = r'"say \"hi\"" and "back\\slash"'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[0]["labels"] = ['say "hi"', "back\\slash"]
        source_pulls.listing(tracker)[1]["labels"] = [r"say \"hi\"", "back\\\\slash"]
        await source_pulls.declare(
            invoke, project, profile, tracker.base_url, _FILTER.format(expression)
        )
        pulled = await source_pulls.pull(invoke, "platform")
        first = await shown_item(invoke, profile, tracker, 2)

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            filtered_out=1,
            lines=["platform/api#12: 1 link(s) not followed, no item holds platform/api#13"],
        )
    )
    assert first == item(
        profile, 2, badge=False, refs=[], updated_at="2026-11-02T09:14:00Z", rendered=DESCRIPTION
    )


@pytest.mark.covers("source pull", "source")
async def test_the_sides_of_a_filter_are_anded(project, invoke, credentials_home, profile) -> None:
    both = "[sources.platform.filter]\nlabels = 'squads'\ntype = 'incident'\n"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[1]["issue_type"] = "incident"
        await source_pulls.declare(invoke, project, profile, tracker.base_url, both)
        pulled = await source_pulls.pull(invoke, "platform")

    assert pulled == pull_document(pull_report(filtered_out=1, skipped_no_type=1))


@pytest.mark.covers("source pull", "source")
async def test_a_held_issue_the_filter_now_rejects_reads_out_of_filter_and_is_not_read_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        await source_pulls.declare(
            invoke, project, profile, tracker.base_url, _FILTER.format("squads and not bug")
        )
        second = await source_pulls.pull(invoke, "platform")
        held = await shown_item(invoke, profile, tracker, 2)
        before = len(tracker.requests)
        third = await source_pulls.pull(invoke, "platform")
        later = [path for path, _, _ in tracker.requests[before:]]

    assert held == item(profile, 2, source={**RECORDS[12], "state": "out-of-filter"})
    assert second == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[
                f"platform/api#12: out-of-filter (rejected by the filter); "
                f"{profile.ref_id(2)} stays"
            ],
        )
    )
    assert third == pull_document(pull_report(unchanged=2))
    assert not [p for p in later if p.endswith(("/notes", "/links"))]


@pytest.mark.covers("source pull", "source")
async def test_an_out_of_filter_issue_the_filter_accepts_again_reads_open_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        await source_pulls.declare(
            invoke, project, profile, tracker.base_url, _FILTER.format("squads and not bug")
        )
        await source_pulls.pull(invoke, "platform")
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        again = await source_pulls.pull(invoke, "platform")
        reopened = await shown_item(invoke, profile, tracker, 2)

    assert reopened == item(profile, 2)
    assert again == pull_document(pull_report(refreshed=1, unchanged=1))


@pytest.mark.covers("source pull", "source")
async def test_an_out_of_filter_issue_outside_the_scope_is_not_fetched_in_detail_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[:] = source_pulls.listing(tracker)[1:]
        await source_pulls.pull(invoke, "platform")
        before = len(tracker.requests)
        third = await source_pulls.pull(invoke, "platform")
        later = [path for path, _, _ in tracker.requests[before:]]

    held = await shown_item(invoke, profile, tracker, 2)
    assert held == item(profile, 2, source={**RECORDS[12], "state": "out-of-filter"})
    assert third == pull_document(pull_report(unchanged=2))
    assert not [p for p in later if p.endswith(("/notes", "/links"))]


@pytest.mark.covers("source pull", "source")
async def test_a_redirect_to_another_address_never_carries_the_token(
    project, invoke, credentials_home, profile
) -> None:
    with (
        harness.serve([]) as elsewhere,
        harness.serve(harness.load_routes("gitlab/routes.json")) as tracker,
    ):
        route = next(
            r for r in tracker.routes if r["path"] == "/api/v4/projects/platform%2Fapi/issues"
        )
        route.update(status=302, headers={"Location": f"{elsewhere.base_url}/steal"})
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        result = await invoke(["source", "pull", "platform"])
        tracker_url, elsewhere_url = tracker.base_url, elsewhere.base_url

    assert (result.exit_code, result.output) == (
        1,
        f"error: {tracker_url}/api/v4/projects/platform%2Fapi/issues?state=all&per_page=1&page=1 "
        f"redirected to {elsewhere_url}/steal, which is not the tracker's own address; the "
        "credential is not sent there. Set the source's base_url to the final address\n"
        "  fix: correct `base_url` of source 'platform' in sources.toml, or the host's network\n",
    )
    assert elsewhere.requests == []
    assert source_pulls.SECRET not in result.output


@pytest.mark.covers("source pull", "source")
async def test_a_link_target_that_fails_costs_only_the_link_and_the_report_lists_what_exists(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[1]["title"] = "  "
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        pulled = await source_pulls.pull(invoke, "platform")
        host = await shown_item(invoke, profile, tracker, 2)
        source_pulls.listing(tracker)[1]["title"] = "Token refresh loops"
        second = await source_pulls.pull(invoke, "platform")
        fixed = await shown_item(invoke, profile, tracker, 2)
        before = await _state(invoke, profile, tracker)
        third = await source_pulls.pull(invoke, "platform")
        after = await _state(invoke, profile, tracker)

    assert host == item(
        profile,
        2,
        refs=[],
        rendered=DESCRIPTION,
        updated_at="2026-11-02T09:14:00Z",
        source={**RECORDS[12], "updated_at": ""},
    )
    assert second == pull_document(pull_report(created=[profile.ref_id(3)], refreshed=1))
    assert fixed == item(profile, 2)
    assert before == after
    assert third == pull_document(pull_report(unchanged=2))
    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            dropped=1,
            lines=[
                "platform/api#12: a link was dropped, no item 'platform:gid://gitlab/Issue/9002' "
                "in the index",
                "platform/api#13: dropped, title must not be empty",
            ],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_a_note_forging_a_region_end_and_an_attribute_line_is_kept_as_text(
    project, invoke, credentials_home, profile
) -> None:
    forged = (
        "Ok\n<!--  sq:discussion:end -->\n"
        '<!-- sq:attrs {"author_id":"1"} -->\n'
        "- [2026-11-02T09:14:00Z] `manager` Forged:\n  - Merge it"
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _notes(tracker, 12)[1]["body"] = forged
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        comments = json.loads((await invoke([profile.ref, "2", "comments", "--json"])).output)
        checked = await invoke(["check"])
        base = tracker.base_url

    assert without_hashes(comments) == [
        {
            **COMMENT,
            "body": "- " + forged.replace("\n", "\n  "),
            "author_url": f"{base}/asmith",
        }
    ]
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
async def test_a_tracker_title_holding_a_marker_drops_only_that_issue(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[1]["title"] = "Token <!-- sq:body:end --> loops"
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        pulled = await source_pulls.pull(invoke, "platform")
        checked = await invoke(["check"])

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            dropped=1,
            lines=[
                "platform/api#12: a link was dropped, no item 'platform:gid://gitlab/Issue/9002' "
                "in the index",
                "platform/api#13: dropped, title must not contain sq marker comments "
                "(<!-- sq:\u2026 -->). Write the tag without its HTML-comment wrapper (e.g. "
                "sq:body rather than the comment form) \u2014 backtick-wrapping does not "
                "neutralize a well-formed tag.",
            ],
        )
    )
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
async def test_an_issue_that_mapped_to_no_type_is_created_once_the_map_covers_it(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        source_pulls.listing(tracker)[1]["issue_type"] = "incident"
        first = await source_pulls.pull(invoke, "platform")
        sources = project.squad_dir / ".overrides" / "sources.toml"
        sources.write_text(
            sources.read_text(encoding="utf-8").replace(
                f'issue = "{profile.ref}"\n',
                f'issue = "{profile.ref}"\nincident = "{profile.ref}"\n',
            ),
            encoding="utf-8",
        )
        second = await source_pulls.pull(invoke, "platform")

    assert first == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            skipped_no_type=1,
            lines=["platform/api#12: 1 link(s) not followed, no item holds platform/api#13"],
        )
    )
    assert second == pull_document(pull_report(created=[profile.ref_id(3)], unchanged=1))


@pytest.mark.covers("source pull", "source")
async def test_an_issue_whose_events_were_dropped_is_fetched_and_reported_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[1].update(title="  ", updated_at="2026-11-04T09:00:00Z")
        dropped = [await source_pulls.pull(invoke, "platform") for _ in range(2)]
        source_pulls.listing(tracker)[1]["title"] = "Fixed upstream"
        fixed = await source_pulls.pull(invoke, "platform")
        renamed = await shown_item(invoke, profile, tracker, 3)

    line = "platform/api#13: dropped, title must not be empty"
    assert dropped == [
        pull_document(pull_report(unchanged=1, dropped=1, lines=[line])),
        pull_document(pull_report(unchanged=1, dropped=1, lines=[line])),
    ]
    assert fixed == pull_document(pull_report(refreshed=1, unchanged=1))
    assert renamed == item(
        profile,
        3,
        title="Fixed upstream",
        slug="fixed-upstream",
        path=profile.ref_path(3, "fixed-upstream"),
        source={**RECORDS[13], "updated_at": "2026-11-04T09:00:00Z"},
    )


@pytest.mark.covers("source pull", "source")
async def test_an_issue_titled_over_several_lines_is_dropped_and_the_others_are_kept(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        source_pulls.listing(tracker)[1]["title"] = "Token refresh\nloops"
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        pulled = await source_pulls.pull(invoke, "platform")

    assert pulled == pull_document(
        pull_report(
            created=[profile.ref_id(2)],
            dropped=1,
            lines=[
                "platform/api#12: a link was dropped, no item 'platform:gid://gitlab/Issue/9002' "
                "in the index",
                "platform/api#13: dropped, title must be a single line",
            ],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_a_dropped_link_keeps_the_host_issue_to_be_fetched_and_reported_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        links = next(r for r in tracker.routes if r["path"].endswith("/issues/12/links"))
        blocks = links["body"]
        links["body"] = []
        second_issue = source_pulls.listing(tracker).pop()
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        links["body"] = blocks
        source_pulls.listing(tracker).append({**second_issue, "title": "  "})
        source_pulls.listing(tracker)[0]["updated_at"] = "2026-11-04T09:00:00Z"
        pulls = [await source_pulls.pull(invoke, "platform") for _ in range(2)]

    line = (
        "platform/api#12: a link was dropped, "
        "no item 'platform:gid://gitlab/Issue/9002' in the index"
    )
    lines = [line, "platform/api#13: dropped, title must not be empty"]
    assert pulls == [
        pull_document(pull_report(unchanged=1, dropped=1, lines=lines)),
        pull_document(pull_report(unchanged=1, dropped=1, lines=lines)),
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_confidential_issue_is_not_imported_and_the_report_counts_it(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        source_pulls.listing(tracker)[1]["confidential"] = True
        pulled = await source_pulls.pull(invoke, "platform")
        again = await source_pulls.pull(invoke, "platform")
        shown = await invoke(["source", "pull", "platform"])

    lines = ["platform/api#12: 1 link(s) not followed, no item holds platform/api#13"]
    assert pulled == pull_document(
        pull_report(created=[profile.ref_id(2)], restricted=1, lines=lines)
    )
    assert again == pull_document(pull_report(unchanged=1, restricted=1))
    assert (shown.exit_code, shown.output) == (
        0,
        "platform: unchanged 1, restricted 1\n",
    )


@pytest.mark.covers("source pull", "source")
async def test_an_internal_note_is_not_imported_as_a_comment(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        notes = _notes(tracker, 12)
        notes.append(
            {**notes[1], "id": 399, "body": "Staff only.", "system": False, "internal": True}
        )
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        first = await shown_item(invoke, profile, tracker, 2)

    assert first == item(profile, 2)


@pytest.mark.covers("source pull", "source")
async def test_a_held_issue_that_becomes_confidential_reads_gone_and_its_item_stays(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[1]["confidential"] = True
        source_pulls.issue_route(tracker, 13)["confidential"] = True
        second = await source_pulls.pull(invoke, "platform")
        gone = await shown_item(invoke, profile, tracker, 3)

    assert gone == item(profile, 3, source={**RECORDS[13], "state": "gone"})
    assert second == pull_document(
        pull_report(
            unchanged=1,
            gone=1,
            lines=[f"platform/api#13: deleted or no longer readable; {profile.ref_id(3)} stays"],
        )
    )


@pytest.mark.covers("source pull", "source")
async def test_a_link_read_from_both_ends_makes_one_ref_on_the_blocking_issue(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        blocking = await shown_item(invoke, profile, tracker, 2)
        blocked = await shown_item(invoke, profile, tracker, 3)

    assert (blocking, blocked) == (item(profile, 2), item(profile, 3))


@pytest.mark.covers("source pull", "source")
async def test_a_link_read_only_from_the_blocked_end_makes_the_ref_on_the_held_blocking_item(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        blocked_by = _links(tracker, 13)["body"][:]
        _links(tracker, 12)["body"][:] = []
        _links(tracker, 13)["body"][:] = []
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        _links(tracker, 13)["body"][:] = blocked_by
        source_pulls.listing(tracker)[1]["updated_at"] = "2026-11-04T09:00:00Z"
        tracker.requests.clear()
        pulled = await source_pulls.pull(invoke, "platform")
        asked = [path for path, _query, _headers in tracker.requests]
        host = await shown_item(invoke, profile, tracker, 2)

    assert pulled == pull_document(pull_report(refreshed=1, unchanged=1))
    assert "/api/v4/projects/77/issues/12/links" not in asked
    assert host == item(profile, 2)


@pytest.mark.covers("source pull", "source")
async def test_a_first_pull_creates_each_item_at_the_status_its_map_gives(
    project, invoke, credentials_home, profile
) -> None:
    extra = source_pulls.status_map(
        state={"closed": [profile.foreign, profile.done]},
        labels={"squads": profile.working, "priority::high": profile.working},
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, extra)
        pulled = await source_pulls.pull(invoke, "platform")
        statuses = await source_pulls.statuses(invoke, profile)

    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    # the closed issue takes the first status of its list its type has, from the state, which is
    # checked before the labels; the open one falls through to its labels, which agree
    assert statuses == {2: profile.working, 3: profile.done}


@pytest.mark.covers("source pull", "source")
async def test_a_status_the_map_cannot_give_is_reported_and_an_out_of_filter_item_is_not_moved(
    project, invoke, credentials_home, profile
) -> None:
    extra = source_pulls.status_map(
        state={"closed": [profile.foreign]},
        labels={"squads": profile.working, "priority::high": profile.moved},
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, extra)
        created = await source_pulls.pull(invoke, "platform")
        first = await source_pulls.statuses(invoke, profile)
        await source_pulls.declare(
            invoke,
            project,
            profile,
            tracker.base_url,
            _FILTER.format("squads and not bug")
            + source_pulls.status_map(labels={"squads": profile.working}),
        )
        again = await source_pulls.pull(invoke, "platform")
        second = await source_pulls.statuses(invoke, profile)

    names = [profile.ref_id(2), profile.ref_id(3)]
    assert created == pull_document(
        pull_report(
            created=names,
            lines=[
                f"platform/api#12: status left alone, its labels map to "
                f"{profile.working}, {profile.moved}",
                f"platform/api#13: closed maps to {profile.foreign}, none of which is a status "
                f"of {profile.ref}; left alone",
            ],
        )
    )
    # a side that maps a value decides even when no listed status fits: the closed issue's label
    # does not speak in its place
    assert first == {2: profile.initial, 3: profile.initial}
    assert again == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[
                "platform/api#12: out-of-filter (rejected by the filter); "
                f"{profile.ref_id(2)} stays"
            ],
        )
    )
    assert second == first


@pytest.mark.covers("source pull", "--dry-run")
async def test_a_changed_issue_moves_its_item_and_a_hand_set_status_holds_until_it_changes_again(
    project, invoke, credentials_home, profile
) -> None:
    mapped = source_pulls.status_map(state={"closed": [profile.done]})
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        await source_pulls.declare(invoke, project, profile, tracker.base_url, mapped)
        # items pulled before the map was declared stay until their issue changes
        declared = await source_pulls.pull(invoke, "platform")
        source_pulls.listing(tracker)[1]["updated_at"] = "2026-11-05T08:00:00Z"
        before = await _state(invoke, profile, tracker)
        dry = await source_pulls.pull(invoke, "platform", "--dry-run")
        untouched = await _state(invoke, profile, tracker)
        moved = await source_pulls.pull(invoke, "platform")
        statuses = await source_pulls.statuses(invoke, profile)
        hand = await invoke([profile.ref, "3", "status", profile.moved, "--force"])
        held = await source_pulls.pull(invoke, "platform")
        after = await source_pulls.statuses(invoke, profile)

    third = profile.ref_id(3)
    assert declared == pull_document(pull_report(unchanged=2))
    assert before == untouched
    assert dry == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[f"platform/api#13: {third} would move to {profile.done} (state closed)"],
        ),
        dry_run=True,
    )
    assert moved == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[f"platform/api#13: {third} moved to {profile.done} (state closed)"],
        )
    )
    assert statuses == {2: profile.initial, 3: profile.done}
    assert hand.exit_code == 0, hand.output
    assert held == pull_document(pull_report(unchanged=2))
    assert after == {2: profile.initial, 3: profile.moved}


@pytest.mark.covers("source pull", "source")
async def test_a_jira_issue_takes_its_status_from_the_status_name_before_its_category(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3") + (
        f'\n[sources.platform.maps.statuses.status]\n"In Progress" = "{profile.working}"\n'
        f'\n[sources.platform.maps.statuses.category]\nindeterminate = "{profile.moved}"\n'
        f'done = "{profile.done}"\n'
    )
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        pulled = await source_connectors.pull(invoke)
        statuses = await source_pulls.statuses(invoke, profile)

    assert pulled == pull_document(pull_report(created=[profile.ref_id(2), profile.ref_id(3)]))
    # the first issue's status name is mapped, so its category does not speak; the second
    # issue's status name is not, so its category does
    assert statuses == {2: profile.working, 3: profile.done}


@pytest.mark.covers("source pull", "--full")
async def test_a_full_pull_applies_the_map_to_every_held_item_and_reads_what_a_pull_misses(
    project, invoke, credentials_home, profile
) -> None:
    mapped = source_pulls.status_map(state={"closed": [profile.done]})
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        await source_pulls.declare(invoke, project, profile, tracker.base_url, mapped)
        note = _notes(tracker, 12)[1]
        note["body"] = "It returns 500 for an empty body."
        note["updated_at"] = "2026-11-04T08:00:00Z"
        before = len(tracker.requests)
        plain = await source_pulls.pull(invoke, "platform")
        plain_asked = [p for p, _, _ in tracker.requests[before:] if p.endswith("/notes")]
        state = await _state(invoke, profile, tracker)
        dry = await source_pulls.pull(invoke, "platform", "--full", "--dry-run")
        unwritten = await _state(invoke, profile, tracker)
        before = len(tracker.requests)
        full = await source_pulls.pull(invoke, "platform", "--full")
        full_asked = {p for p, _, _ in tracker.requests[before:] if p.endswith("/notes")}
        statuses = await source_pulls.statuses(invoke, profile)
        edited = await shown_item(invoke, profile, tracker, 2)
        quiet = await _state(invoke, profile, tracker)
        second = await source_pulls.pull(invoke, "platform", "--full")
        after = await _state(invoke, profile, tracker)

    third = profile.ref_id(3)
    move = f"platform/api#13: {third} moved to {profile.done} (state closed)"
    assert plain == pull_document(pull_report(unchanged=2))
    assert plain_asked == []
    assert dry == pull_document(
        pull_report(refreshed=2, lines=[move.replace("moved", "would move")]), dry_run=True
    )
    assert unwritten == state
    assert full == pull_document(pull_report(refreshed=2, lines=[move]))
    assert full_asked == {
        "/api/v4/projects/77/issues/12/notes",
        "/api/v4/projects/77/issues/13/notes",
    }
    assert statuses == {2: profile.initial, 3: profile.done}
    assert edited["discussion"][0]["body"] == "- It returns 500 for an empty body."
    assert second == pull_document(pull_report(unchanged=2))
    assert after == quiet


@pytest.mark.bundled_only("the validator is selected on the bundled task type")
@pytest.mark.covers("source pull", "source")
async def test_a_status_a_validator_refuses_is_left_alone_and_the_rest_of_the_issue_lands(
    project, invoke, credentials_home, profile
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f'[items.{profile.ref}]\nvalidators = ["assignee_present@error"]\n', encoding="utf-8"
    )
    extra = source_pulls.status_map(labels={"squads": profile.working})
    refused = (
        f"status left alone, {profile.working} is refused: "
        f"status is {profile.working} but nobody is assigned"
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, extra)
        created = await source_pulls.pull(invoke, "platform")
        first = await source_pulls.statuses(invoke, profile)
        issue = source_pulls.listing(tracker)[0]
        issue["title"] = "Login fails on a blank password"
        issue["updated_at"] = "2026-11-05T08:00:00Z"
        changed = await source_pulls.pull(invoke, "platform")
        statuses = await source_pulls.statuses(invoke, profile)
        shown = await shown_item(invoke, profile, tracker, 2)

    names = [profile.ref_id(2), profile.ref_id(3)]
    assert created == pull_document(
        pull_report(
            created=names,
            lines=[f"platform/api#12: {refused}", f"platform/api#13: {refused}"],
        )
    )
    assert first == {2: profile.initial, 3: profile.initial}
    assert changed == pull_document(
        pull_report(refreshed=1, unchanged=1, lines=[f"platform/api#12: {refused}"])
    )
    assert statuses == first
    assert shown["title"] == "Login fails on a blank password"
    assert shown["source"]["updated_at"] == "2026-11-05T08:00:00Z"


@pytest.mark.bundled_only("the validator is selected on the bundled task type")
@pytest.mark.covers("source pull", "source")
async def test_a_refusal_that_holds_at_every_status_is_not_blamed_on_the_mapped_status(
    project, invoke, credentials_home, profile
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f'[items.{profile.ref}]\nvalidators = ["parent_present@error"]\n', encoding="utf-8"
    )
    extra = source_pulls.status_map(
        state={"closed": [profile.done]}, labels={"squads": profile.working}
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url, extra)
        pulled = await source_pulls.pull(invoke, "platform")

    why = f"{profile.ref} requires a parent of type {profile.host}"
    assert pulled == pull_document(
        pull_report(
            dropped=2,
            lines=[
                "platform/api#12: a link was dropped, no item "
                "'platform:gid://gitlab/Issue/9001' in the index",
                f"platform/api#12: dropped, {why}",
                f"platform/api#13: dropped, {why}",
            ],
        )
    )


@pytest.mark.bundled_only("the validator is selected on the bundled task type")
@pytest.mark.covers("source pull", "source")
async def test_an_item_failing_a_validator_at_its_status_still_moves_to_one_that_passes(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_pulls.declare(invoke, project, profile, tracker.base_url)
        await source_pulls.pull(invoke, "platform")
        hand = await invoke([profile.ref, "3", "status", profile.working])
        overrides = project.squad_dir / ".overrides"
        (overrides / "workflow.toml").write_text(
            f'[items.{profile.ref}]\nvalidators = ["assignee_present@error"]\n', encoding="utf-8"
        )
        mapped = source_pulls.status_map(state={"closed": [profile.done]})
        await source_pulls.declare(invoke, project, profile, tracker.base_url, mapped)
        source_pulls.listing(tracker)[1]["updated_at"] = "2026-11-05T08:00:00Z"
        pulled = await source_pulls.pull(invoke, "platform")
        statuses = await source_pulls.statuses(invoke, profile)

    assert hand.exit_code == 0, hand.output
    assert pulled == pull_document(
        pull_report(
            refreshed=1,
            unchanged=1,
            lines=[f"platform/api#13: {profile.ref_id(3)} moved to {profile.done} (state closed)"],
        )
    )
    assert statuses == {2: profile.initial, 3: profile.done}
