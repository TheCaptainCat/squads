"""`sq <type> source unlink|relink`: the tracker link a sourced item carries."""

import json
from typing import Any

import pytest

from tests import _tracker_harness as harness
from tests.cli import _source_links as source_links
from tests.cli._output import pull_document, pull_report
from tests.cli._pulled import DESCRIPTION, RECORDS, shown_item

pytestmark = pytest.mark.anyio


def _relinked(profile, state: str, project: str = "platform/api") -> dict[str, Any]:
    """The first item after a relink to an issue of *project*: the view is back, and the prose the
    unlink left stays in the body beside it."""
    moved = source_links.moved(DESCRIPTION, project)
    resolved = moved.replace("#13", profile.ref_id(3)) if project == "platform/api" else moved
    return source_links.platform_item(
        profile,
        2,
        description=moved,
        rendered=f"{resolved}\n\n{DESCRIPTION}",
        body=(
            f"<!-- sq:view:source_description -->\n{moved}\n"
            f"<!-- sq:view:source_description:end -->\n\n{DESCRIPTION}\n\n## Description\n\n"
            f"_TODO: describe this {profile.ref}._"
        ),
        source={
            **RECORDS[12],
            "state": state,
            "key": source_links.moved(RECORDS[12]["key"], project),
        },
    )


async def _pulled(invoke, project, profile, tracker: harness.Tracker) -> None:
    await source_links.declare(invoke, project, profile, tracker.base_url)
    await source_links.pull(invoke)


async def _relink(
    invoke, profile, number: int, source: str, issue: str, item_type: str | None = None
):
    result = await invoke(
        [item_type or profile.ref, str(number), "source", "relink", source, issue]
    )
    return result.exit_code, result.output


@pytest.mark.covers("<type> source unlink", "--json")
async def test_unlink_keeps_the_description_as_prose_and_the_author_and_works_when_disabled(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        await source_links.pull(invoke)
        before = await shown_item(invoke, profile, tracker)
        await source_links.declare(invoke, project, profile, tracker.base_url, "enabled = false\n")
        unlinked = await invoke([profile.ref, "2", "source", "unlink", "--json"])
        after = await shown_item(invoke, profile, tracker)

    assert unlinked.exit_code == 0, unlinked.output
    assert json.loads(unlinked.stdout) == {
        "id": profile.ref_id(2),
        "source": "platform",
        "key": "platform/api#12",
    }
    assert before == source_links.platform_item(profile, 2)
    assert after == source_links.platform_item(profile, 2, unlinked=True)


@pytest.mark.covers("<type> source relink", "source", "--json")
async def test_relink_restores_the_record_and_the_view_in_one_command_and_keeps_the_prose(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        await source_links.pull(invoke)
        before = await shown_item(invoke, profile, tracker)
        await invoke([profile.ref, "2", "source", "unlink"])
        source_links.issue_route(tracker, 12)["description"] = "Rewritten upstream."
        relinked = await invoke(
            [profile.ref, "2", "source", "relink", "platform", "platform/api#12", "--json"]
        )
        after = await shown_item(invoke, profile, tracker)

    assert relinked.exit_code == 0, (relinked.output, relinked.stderr)
    assert json.loads(relinked.output) == {
        "id": profile.ref_id(2),
        "source": "platform",
        "key": "platform/api#12",
        "lines": [],
    }
    prose = before["views"]["source_description"]["body"]
    assert before == source_links.platform_item(profile, 2)
    # the old prose stays in the body beside the restored view, which holds the tracker's text
    assert after == source_links.platform_item(
        profile,
        2,
        description="Rewritten upstream.",
        rendered=f"Rewritten upstream.\n\n{prose}",
        body=(
            "<!-- sq:view:source_description -->\nRewritten upstream.\n"
            f"<!-- sq:view:source_description:end -->\n\n{prose}\n\n## Description\n\n"
            f"_TODO: describe this {profile.ref}._"
        ),
    )


@pytest.mark.covers("<type> source relink", "source")
async def test_relink_refuses_an_item_that_still_holds_a_record(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        refused = await _relink(invoke, profile, 2, "platform", "platform/api#12")

    assert refused == (
        1,
        f"error: {profile.ref_id(2)} still holds a source record (platform platform/api#12); "
        f"run `sq {profile.ref} 2 source unlink` first\n",
    )


@pytest.mark.covers("<type> source relink", "source")
async def test_relink_refuses_an_item_no_source_made(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        await invoke(["create", profile.host, "Plain", "--author", "manager"])
        refused = await _relink(invoke, profile, 4, "platform", "platform/api#12", profile.host)

    assert refused == (
        1,
        f"error: {profile.host_id(4)} was not created by a source, so it cannot be relinked\n",
    )


@pytest.mark.covers("<type> source relink", "source")
async def test_relink_refuses_a_source_other_than_the_one_that_made_the_item(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        source_links.declare_more(
            project,
            '\n[sources.other]\nconnector = "gitlab"\nproject = "platform/api"\n'
            f'base_url = "{tracker.base_url}"\n'
            f'\n[sources.other.maps.types.type]\nissue = "{profile.ref}"\n',
        )
        await invoke([profile.ref, "2", "source", "unlink"])
        refused = await _relink(invoke, profile, 2, "other", "platform/api#12")

    assert refused == (
        1,
        f"error: {profile.ref_id(2)} was created by source 'platform', not 'other'; "
        "relink it to 'platform'\n",
    )


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_refuses_an_issue_another_item_of_the_source_holds(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        await invoke([profile.ref, "2", "source", "unlink"])
        refused = await _relink(invoke, profile, 2, "platform", "platform/api#13")

    assert refused == (
        1,
        "error: issue 'platform/api#13' of source 'platform' is already held by "
        f"{profile.ref_id(3)} of source 'platform'\n",
    )


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_refuses_a_key_that_is_not_an_issue_key_and_fetches_nothing(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        await invoke([profile.ref, "2", "source", "unlink"])
        refused = await _relink(invoke, profile, 2, "platform", "g/p#1/../../users")
        asked = [path for path, _query, _headers in tracker.requests]

    assert refused == (
        1,
        "error: g/p#1/../../users is not an issue key (group/project#number)\n",
    )
    assert not [path for path in asked if "users" in path]


@pytest.mark.covers("<type> source unlink", "--json")
async def test_unlink_warns_when_the_issue_is_still_in_scope_and_a_pull_imports_it_again(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        outside = next(r for r in tracker.routes if r["path"].endswith("/issues/20"))["body"]
        await source_links.declare(invoke, project, profile, tracker.base_url)
        source_links.listing(tracker).append(outside)
        await source_links.pull(invoke)
        source_links.listing(tracker)[:] = source_links.listing(tracker)[:2]
        await source_links.pull(invoke)
        open_one = await invoke([profile.ref, "2", "source", "unlink", "--json"])
        closed_one = await invoke([profile.ref, "3", "source", "unlink", "--json"])
        lost = await invoke([profile.ref, "4", "source", "unlink", "--json"])
        before = await shown_item(invoke, profile, tracker, 2)
        pulled = await invoke(["source", "pull", "platform", "--json"])
        after = await shown_item(invoke, profile, tracker, 2)
        again = await shown_item(invoke, profile, tracker, 5)

    def warning(key: str) -> str:
        return (
            f"warning: {key} is still in the scope of source 'platform' and accepted by its "
            "filter: the next `sq source pull` imports it again as a new item; to prevent that, "
            "narrow the scope or the filter in sources.toml, or change the issue on the tracker "
            "so neither selects it\n"
        )

    def unlinked(number: int, key: str) -> dict[str, str]:
        return {"id": profile.ref_id(number), "source": "platform", "key": key}

    assert (open_one.exit_code, open_one.stderr) == (0, warning("platform/api#12"))
    assert json.loads(open_one.stdout) == unlinked(2, "platform/api#12")
    assert (closed_one.exit_code, closed_one.stderr) == (0, warning("platform/api#13"))
    assert json.loads(closed_one.stdout) == unlinked(3, "platform/api#13")
    assert (lost.exit_code, lost.stderr) == (0, "")
    assert json.loads(lost.stdout) == unlinked(4, "platform/api#20")
    assert json.loads(pulled.stdout) == pull_document(
        pull_report(created=[profile.ref_id(5), profile.ref_id(6)])
    )
    assert after == before == source_links.platform_item(profile, 2, unlinked=True)
    assert again == source_links.platform_item(profile, 5, 12, partner=6)


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_of_an_issue_the_filter_rejects_links_it_out_of_filter_without_listing(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        await source_links.pull(invoke)
        await invoke([profile.ref, "2", "source", "unlink"])
        await source_links.declare(
            invoke, project, profile, tracker.base_url, source_links.REJECTING_FILTER
        )
        tracker.requests.clear()
        relinked = await invoke(
            [profile.ref, "2", "source", "relink", "platform", "platform/api#12"]
        )
        shown = await shown_item(invoke, profile, tracker)
        asked = source_links.full_listings(tracker)

    assert (relinked.exit_code, relinked.output) == (
        0,
        f"relinked {profile.ref_id(2)} to platform platform/api#12\n",
    )
    assert shown == _relinked(profile, "out-of-filter")
    assert asked == []


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_of_an_issue_outside_the_scope_links_it_out_of_filter_without_listing(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        await source_links.pull(invoke)
        await invoke([profile.ref, "2", "source", "unlink"])
        source_links.issue_route(tracker, 12)["references"]["full"] = "elsewhere/api#12"
        tracker.requests.clear()
        relinked = await invoke(
            [profile.ref, "2", "source", "relink", "platform", "platform/api#12"]
        )
        shown = await shown_item(invoke, profile, tracker)
        asked = source_links.full_listings(tracker)

    assert (relinked.exit_code, relinked.output) == (
        0,
        f"relinked {profile.ref_id(2)} to platform elsewhere/api#12\n",
    )
    assert shown == _relinked(profile, "out-of-filter", "elsewhere/api")
    assert asked == []


@pytest.mark.covers("<type> source relink", "issue")
async def test_a_jira_relink_decides_scope_with_one_search_for_the_issue(
    project, invoke, credentials_home, profile
) -> None:
    jira = (
        '[sources.platform]\nconnector = "jira"\nversion = "cloud-v3"\n'
        'jql = "labels = squads"\nbase_url = "{base}"\n'
        f'\n[sources.platform.maps.types.type]\nBug = "{profile.ref}"\nTask = "{profile.ref}"\n'
    )
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(jira.format(base=tracker.base_url), encoding="utf-8")
        stored = await invoke(
            ["source", "credential", "set", "platform"], input="pchat@example.com\nsecret\n"
        )
        assert stored.exit_code == 0, stored.output
        await source_links.pull(invoke)
        await invoke([profile.ref, "2", "source", "unlink"])
        tracker.requests.clear()
        relinked = await invoke([profile.ref, "2", "source", "relink", "platform", "10042"])
        searches = [
            (q["jql"], q["maxResults"])
            for p, q, _h in tracker.requests
            if p == "/rest/api/3/search/jql"
        ]

    assert (relinked.exit_code, relinked.output) == (
        0,
        f"relinked {profile.ref_id(2)} to platform PROJ-45\n",
    )
    assert searches == [
        ("labels = squads", "1"),
        ("id = 10042 AND (labels = squads)", "1"),
    ]


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_of_an_issue_an_item_of_another_source_of_its_tracker_holds_is_refused(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare_two(invoke, project, profile, tracker.base_url)
        for name in ("epics", "stories"):
            await invoke(["source", "pull", name])
        await invoke([profile.ref, "3", "source", "unlink"])
        result = await invoke([profile.ref, "3", "source", "relink", "stories", "platform/api#12"])

    assert (result.exit_code, result.output) == (
        1,
        "error: issue 'platform/api#12' of source 'stories' is already held by "
        f"{profile.ref_id(2)} of source "
        "'epics'\n",
    )


@pytest.mark.covers("<type> source relink", "issue")
async def test_relink_by_a_gitlab_id_the_scope_does_not_list_says_to_use_the_key(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        await source_links.pull(invoke)
        await invoke([profile.ref, "2", "source", "unlink"])
        result = await invoke(
            [profile.ref, "2", "source", "relink", "platform", "gid://gitlab/Issue/99999"]
        )

    assert (result.exit_code, result.output) == (
        1,
        "error: source 'platform' lists no issue 'gid://gitlab/Issue/99999' in its scope; GitLab "
        "resolves an ID only through the scope's listing, so relink it by its key "
        "(group/project#12)\n",
    )
