"""`sq source pull`: the issues a source opts in become items the tracker owns."""

import json
from typing import Any

import pytest

from tests import _tracker_harness as harness
from tests.cli._output import read_json

pytestmark = pytest.mark.anyio

SECRET = "glpat-not-a-real-token"
MAPS = (
    '\n[sources.platform.maps.types.type]\nissue = "task"\n'
    '\n[sources.platform.maps.fields.priority.labels]\n"priority::high" = "high"\n'
)
HEAD = 'connector = "gitlab"\nproject = "platform/api"\n'


_FILTER = "[sources.platform.filter]\nlabels = '{}'\n"


async def _declare(invoke, project, base_url: str, extra: str = "") -> None:
    """Declare the `platform` source on *base_url* and store its credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\n{HEAD}base_url = "{base_url}"\n{extra}{MAPS}', encoding="utf-8"
    )
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


def _listing(tracker: harness.Tracker) -> list[dict[str, Any]]:
    """The recorded issue listing, which a case edits to change what the tracker answers."""
    route = next(r for r in tracker.routes if r["path"] == "/api/v4/projects/platform%2Fapi/issues")
    return route["body"]


def _issue_route(tracker: harness.Tracker, number: int) -> dict[str, Any]:
    """The recorded body of the one-issue route, which a case edits to change the issue."""
    path = f"/api/v4/projects/platform%2Fapi/issues/{number}"
    return next(r for r in tracker.routes if r["path"] == path)["body"]


def _notes(tracker: harness.Tracker, issue: int) -> list[dict[str, Any]]:
    route = next(r for r in tracker.routes if r["path"].endswith(f"/issues/{issue}/notes"))
    return route["body"]


async def _pull(invoke, *args: str) -> dict[str, Any]:
    result = await invoke(["source", "pull", *args, "--json"])
    assert result.exit_code == 0, (result.output, result.stderr, repr(result.exception))
    return json.loads(result.stdout)


async def _shown(invoke, tracker: harness.Tracker, number: int) -> dict[str, Any]:
    """`show --json` of the task, its tracker address made constant and its etag set aside."""
    out = await invoke(["task", str(number), "show", "--json"])
    assert out.exit_code == 0, out.output
    shown = json.loads(out.output.replace(tracker.base_url, "http://tracker"))
    shown.pop("etag")
    return shown


async def _state(invoke, tracker: harness.Tracker) -> tuple[str, str]:
    """Every task as `show --json` prints it, and the reflog: what a pull that writes nothing
    leaves as it was."""
    shown = [await invoke(["task", str(n), "show", "--json"]) for n in (2, 3)]
    reflog = await invoke(["reflog", "--json"])
    return "".join(s.output for s in shown), reflog.output


@pytest.mark.covers("source pull", "source")
@pytest.mark.covers("source pull", "--json")
async def test_a_first_pull_creates_the_items_with_their_record_description_and_comments(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        pulled = await _pull(invoke, "platform")
        first = await _shown(invoke, tracker, 2)
        second = await _shown(invoke, tracker, 3)

    assert pulled == {
        "dry_run": False,
        "sources": [
            {
                "name": "platform",
                "created": ["TASK-2", "TASK-3"],
                "refreshed": 0,
                "unchanged": 0,
                "left_out": None,
                "lines": [],
                "failed": False,
                "restricted": 0,
                "filtered_out": 0,
                "skipped_no_type": 0,
            }
        ],
    }
    assert (first["title"], first["author"], first["refs"], first["badges"]) == (
        "Login fails on empty password",
        "source:platform",
        ["TASK-3:blocks"],
        {"priority": "high"},
    )
    assert first["source"] == {
        "name": "platform",
        "id": "gid://gitlab/Issue/9001",
        "key": "platform/api#12",
        "state": "open",
        "updated_at": "2026-11-02T09:00:00Z",
        "author_id": "4567",
        "author_handle": "pchat",
    }
    assert first["views"] == {
        "source_description": {
            "body": "Steps in ![shot](http://tracker/platform/api/uploads/abc/shot.png), "
            "see #13 and platform/other#4.",
            "data": None,
        }
    }
    assert [(c["ts"], c["body"], c["attributes"]["source_id"]) for c in first["discussion"]] == [
        ("2026-11-02T09:14:00Z", "- The endpoint returns 500 when the body is empty.", "302")
    ]
    assert (second["source"]["state"], second["discussion"]) == ("closed", [])


@pytest.mark.covers("source pull", "source")
async def test_a_second_pull_writes_nothing(project, invoke, credentials_home) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        before = await _state(invoke, tracker)
        again = await _pull(invoke, "platform")
        after = await _state(invoke, tracker)

    assert before == after
    assert [(r["created"], r["refreshed"], r["unchanged"]) for r in again["sources"]] == [
        ([], 0, 2)
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_description_forging_a_marker_and_using_crlf_is_kept_as_text(
    project, invoke, credentials_home
) -> None:
    forged = "Before\r\n<!-- sq:body:end -->\r\nAfter <!-- sq:view:source_description:end -->"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[0]["description"] = forged
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        shown = await _shown(invoke, tracker, 2)
        before = await _state(invoke, tracker)
        await _pull(invoke, "platform")
        after = await _state(invoke, tracker)
        checked = await invoke(["check"])

    assert shown["views"]["source_description"]["body"] == forged.replace("\r\n", "\n")
    assert shown["body"].count("<!-- sq:body:end -->") == 0
    assert before == after
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
async def test_an_edited_tracker_comment_updates_the_same_comment_in_place(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        note = _notes(tracker, 12)[1]
        note["body"] = "It returns 500 for an empty body."
        note["updated_at"] = "2026-11-04T08:00:00Z"
        _listing(tracker)[0]["updated_at"] = "2026-11-04T08:00:00Z"
        await _pull(invoke, "platform")
        shown = await _shown(invoke, tracker, 2)

    [comment] = shown["discussion"]
    assert (comment["ts"], comment["body"], comment["edited_ts"] is not None) == (
        "2026-11-02T09:14:00Z",
        "- It returns 500 for an empty body.",
        True,
    )
    assert comment["attributes"]["source_updated_at"] == "2026-11-04T08:00:00Z"


@pytest.mark.covers("source pull", "source")
async def test_a_moved_issue_keeps_its_item_and_takes_the_new_key(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        issue = _listing(tracker)[0]
        issue["references"]["full"] = "platform/web#40"
        issue["updated_at"] = "2026-11-05T08:00:00Z"
        pulled = await _pull(invoke, "platform")
        shown = await _shown(invoke, tracker, 2)

    assert [(r["created"], r["refreshed"]) for r in pulled["sources"]] == [([], 1)]
    assert (shown["source"]["key"], shown["source"]["updated_at"], shown["id"]) == (
        "platform/web#40",
        "2026-11-05T08:00:00Z",
        "TASK-2",
    )


@pytest.mark.covers("source pull", "source")
async def test_a_linked_issue_the_filter_lost_is_out_of_filter_or_gone_and_its_item_stays(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        outside = next(r for r in tracker.routes if r["path"].endswith("/issues/20"))["body"]
        gone = {**outside, "id": 9009, "iid": 21, "title": "Removed upstream"}
        gone["references"] = {"full": "platform/api#21"}
        await _declare(invoke, project, tracker.base_url)
        _listing(tracker).extend([outside, gone])
        tracker.routes += [
            {"path": f"/api/v4/projects/77/issues/21/{leaf}", "body": []}
            for leaf in ("notes", "links")
        ]
        first = await _pull(invoke, "platform")
        _listing(tracker)[:] = _listing(tracker)[:2]
        second = await _pull(invoke, "platform")
        states = [(await _shown(invoke, tracker, n))["source"]["state"] for n in (4, 5)]

    assert first["sources"][0]["created"] == ["TASK-2", "TASK-3", "TASK-4", "TASK-5"]
    assert states == ["out-of-filter", "gone"]
    assert second["sources"][0]["lines"] == [
        "platform/api#20: out-of-filter (outside the scope); TASK-4 stays",
        "platform/api#21: deleted or no longer readable; TASK-5 stays",
    ]


@pytest.mark.covers("source pull", "--dry-run")
async def test_a_dry_run_writes_nothing(project, invoke, credentials_home) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        before = (await invoke(["reflog", "--json"])).output
        planned = await _pull(invoke, "platform", "--dry-run")
        listed = await read_json(invoke, ["list", "--json"])
        after = (await invoke(["reflog", "--json"])).output

    assert planned["dry_run"] is True
    assert [i["id"] for i in listed] == ["ROLE-1"]
    assert before == after


@pytest.mark.covers("source pull", "source")
async def test_a_named_source_without_a_credential_errors_naming_the_remedy(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await invoke(["source", "credential", "remove", "platform"])
        named = await invoke(["source", "pull", "platform"])
        unnamed = await invoke(["source", "pull", "--json"])

    assert named.exit_code == 1
    assert "run `sq source credential set platform`" in " ".join(named.output.split())
    assert unnamed.exit_code == 0
    assert json.loads(unnamed.stdout)["sources"][0]["left_out"].startswith("no stored credential")
    assert tracker.requests == []


@pytest.mark.covers("source pull", "source")
async def test_two_items_holding_one_issue_are_both_refreshed_and_no_third_is_made(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, "")
        await _pull(invoke, "platform")
        twin = json.loads((await invoke(["task", "2", "show", "--json"])).output)["source"]
        # A second item mirrors the same issue: written as a pull would, then edited upstream.
        await invoke(["create", "task", "Twin", "--author", "manager"])
        path = next(project.squad_dir.joinpath("tasks").glob("TASK-*twin.md"))
        record = "source:\n" + "".join(f"  {k}: '{v}'\n" for k, v in twin.items())
        text = path.read_text(encoding="utf-8").replace("\nstatus:", f"\n{record}status:", 1)
        path.write_text(text, encoding="utf-8")
        await invoke(["repair"])
        _listing(tracker)[0]["updated_at"] = "2026-11-04T08:00:00Z"
        pulled = await _pull(invoke, "platform")
        listed = await read_json(invoke, ["list", "--json"])

    assert [r["id"] for r in listed if r["type"] == "task"] == ["TASK-2", "TASK-3", "TASK-4"]
    [report] = pulled["sources"]
    assert report["created"] == []
    assert "platform/api#12: held by TASK-2, TASK-4; each is refreshed" in report["lines"]
    assert (await _shown(invoke, tracker, 4))["title"] == "Login fails on empty password"


@pytest.mark.covers("source pull", "source")
async def test_a_named_pull_of_a_disabled_source_is_refused_and_an_unnamed_pull_skips_it(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, "enabled = false\n")
        named = await invoke(["source", "pull", "platform"])
        unnamed = await _pull(invoke)
        listed = await read_json(invoke, ["list", "--json"])

    assert named.exit_code == 1
    assert "enabled = false" in " ".join(named.output.split())
    assert unnamed["sources"] == []
    assert [i["id"] for i in listed] == ["ROLE-1"]
    assert tracker.requests == []


@pytest.mark.covers("source pull", "source")
async def test_an_issue_mapping_to_no_item_type_is_counted_not_named_and_not_detailed(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        _listing(tracker)[1]["issue_type"] = "incident"
        pulled = await _pull(invoke, "platform")
        asked = [path for path, _, _ in tracker.requests]
        shown = await invoke(["source", "pull", "platform"])

    [report] = pulled["sources"]
    assert (report["created"], report["skipped_no_type"], report["lines"]) == (
        ["TASK-2"],
        1,
        ["platform/api#12: 1 link(s) not followed, no item holds platform/api#13"],
    )
    assert not [p for p in asked if "/issues/13" in p]
    assert "skipped 1 (no type)" in shown.output


@pytest.mark.covers("source pull", "source")
async def test_a_link_to_a_confidential_issue_makes_no_ref_and_no_line(
    project, invoke, credentials_home
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
        await _declare(invoke, project, tracker.base_url)
        pulled = await _pull(invoke, "platform")

    assert pulled["sources"][0]["lines"] == []


@pytest.mark.covers("source pull", "source")
async def test_an_issue_mapping_to_two_types_is_named_with_its_values_on_every_pull(
    project, invoke, credentials_home
) -> None:
    two = '\n[sources.platform.maps.types.labels]\nbug = "bug"\n'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, two)
        first = await _pull(invoke, "platform")
        asked = [path for path, _, _ in tracker.requests]
        second = await _pull(invoke, "platform")

    expected = ["platform/api#12: not created, the issue maps to several types: bug, task"]
    assert first["sources"][0]["lines"] == [
        *expected,
        "platform/api#13: 1 link(s) not followed, no item holds platform/api#12",
    ]
    assert second["sources"][0]["lines"] == expected
    assert first["sources"][0]["created"] == ["TASK-2"]
    assert not [p for p in asked if "/issues/12/" in p]


@pytest.mark.covers("source pull", "source")
async def test_an_issue_whose_labels_map_a_field_to_two_values_names_them_and_leaves_the_field(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                '"priority::high" = "high"\n', '"priority::high" = "high"\nbug = "low"\n'
            ),
            encoding="utf-8",
        )
        pulled = await _pull(invoke, "platform")

    assert pulled["sources"][0]["lines"][0] == (
        "platform/api#12: priority left alone, its values map to high, low"
    )


@pytest.mark.covers("source pull", "source")
async def test_the_filter_selects_issues_and_counts_the_rejected_ones(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url, _FILTER.format("squads and not bug"))
        pulled = await _pull(invoke, "platform")
        shown = await invoke(["source", "pull", "platform"])

    [report] = pulled["sources"]
    assert (report["created"], report["filtered_out"], report["lines"]) == (
        ["TASK-2"],
        1,
        ["platform/api#13: 1 link(s) not followed, no item holds platform/api#12"],
    )
    assert "filtered out 1" in shown.output


@pytest.mark.covers("source pull", "source")
async def test_a_filter_reads_not_before_and_and_and_before_or(
    project, invoke, credentials_home
) -> None:
    ruled = "not w or x and y"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[0]["labels"] = ["w", "x", "y"]
        _listing(tracker)[1]["labels"] = []
        await _declare(invoke, project, tracker.base_url, _FILTER.format(ruled))
        pulled = await _pull(invoke, "platform")

    [report] = pulled["sources"]
    assert (report["created"], report["filtered_out"]) == (["TASK-2", "TASK-3"], 0)


@pytest.mark.covers("source pull", "source")
async def test_a_quoted_filter_value_takes_an_escaped_quote_and_backslash_as_one_character(
    project, invoke, credentials_home
) -> None:
    expression = r'"say \"hi\"" and "back\\slash"'
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[0]["labels"] = ['say "hi"', "back\\slash"]
        _listing(tracker)[1]["labels"] = [r"say \"hi\"", "back\\\\slash"]
        await _declare(invoke, project, tracker.base_url, _FILTER.format(expression))
        pulled = await _pull(invoke, "platform")
        key = (await _shown(invoke, tracker, 2))["source"]["key"]

    [report] = pulled["sources"]
    assert (report["created"], report["filtered_out"], key) == (["TASK-2"], 1, "platform/api#12")


@pytest.mark.covers("source pull", "source")
async def test_the_sides_of_a_filter_are_anded(project, invoke, credentials_home) -> None:
    both = "[sources.platform.filter]\nlabels = 'squads'\ntype = 'incident'\n"
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[1]["issue_type"] = "incident"
        await _declare(invoke, project, tracker.base_url, both)
        pulled = await _pull(invoke, "platform")

    [report] = pulled["sources"]
    assert (report["created"], report["filtered_out"]) == ([], 1)


@pytest.mark.covers("source pull", "source")
async def test_a_held_issue_the_filter_now_rejects_reads_out_of_filter_and_is_not_read_again(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        await _declare(invoke, project, tracker.base_url, _FILTER.format("squads and not bug"))
        second = await _pull(invoke, "platform")
        state = (await _shown(invoke, tracker, 2))["source"]["state"]
        before = len(tracker.requests)
        third = await _pull(invoke, "platform")
        later = [path for path, _, _ in tracker.requests[before:]]

    assert state == "out-of-filter"
    assert second["sources"][0]["lines"] == [
        "platform/api#12: out-of-filter (rejected by the filter); TASK-2 stays"
    ]
    assert third["sources"][0]["unchanged"] == 2
    assert not [p for p in later if p.endswith(("/notes", "/links"))]


@pytest.mark.covers("source pull", "source")
async def test_an_out_of_filter_issue_the_filter_accepts_again_reads_open_again(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        await _declare(invoke, project, tracker.base_url, _FILTER.format("squads and not bug"))
        await _pull(invoke, "platform")
        await _declare(invoke, project, tracker.base_url)
        again = await _pull(invoke, "platform")
        state = (await _shown(invoke, tracker, 2))["source"]["state"]

    assert (state, again["sources"][0]["refreshed"]) == ("open", 1)


@pytest.mark.covers("source pull", "source")
async def test_an_out_of_filter_issue_outside_the_scope_is_not_fetched_in_detail_again(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        _listing(tracker)[:] = _listing(tracker)[1:]
        await _pull(invoke, "platform")
        before = len(tracker.requests)
        third = await _pull(invoke, "platform")
        later = [path for path, _, _ in tracker.requests[before:]]

    assert (await _shown(invoke, tracker, 2))["source"]["state"] == "out-of-filter"
    assert third["sources"][0]["lines"] == []
    assert not [p for p in later if p.endswith(("/notes", "/links"))]


@pytest.mark.covers("import", "file")
async def test_the_ops_only_a_pull_compiles_are_refused_in_a_jsonl_file(
    project, invoke, tmp_path
) -> None:
    for op in ("source", "view-body", "comment-edit"):
        events = tmp_path / f"{op}.jsonl"
        events.write_text(json.dumps({"op": op, "target": "ROLE-1", "as": "manager"}) + "\n")
        result = await invoke(["import", str(events)])
        assert result.exit_code != 0
        assert f"unknown op '{op}'" in " ".join(result.output.split())


@pytest.mark.covers("source pull", "source")
async def test_a_redirect_to_another_address_never_carries_the_token(
    project, invoke, credentials_home
) -> None:
    with (
        harness.serve([]) as elsewhere,
        harness.serve(harness.load_routes("gitlab/routes.json")) as tracker,
    ):
        route = next(
            r for r in tracker.routes if r["path"] == "/api/v4/projects/platform%2Fapi/issues"
        )
        route.update(status=302, headers={"Location": f"{elsewhere.base_url}/steal"})
        await _declare(invoke, project, tracker.base_url)
        result = await invoke(["source", "pull", "platform"])

    assert result.exit_code == 1
    assert "which is not the tracker's own address" in " ".join(result.output.split())
    assert elsewhere.requests == []
    assert SECRET not in result.output


@pytest.mark.covers("source pull", "source")
async def test_a_link_target_that_fails_costs_only_the_link_and_the_report_lists_what_exists(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[1]["title"] = "  "
        await _declare(invoke, project, tracker.base_url)
        pulled = await _pull(invoke, "platform")
        host = await _shown(invoke, tracker, 2)
        _listing(tracker)[1]["title"] = "Token refresh loops"
        second = await _pull(invoke, "platform")
        fixed = await _shown(invoke, tracker, 2)
        before = await _state(invoke, tracker)
        third = await _pull(invoke, "platform")
        after = await _state(invoke, tracker)

    assert host["source"]["updated_at"] == ""
    assert second["sources"][0]["created"] == ["TASK-3"]
    assert (fixed["refs"], fixed["source"]["updated_at"]) == (
        ["TASK-3:blocks"],
        "2026-11-02T09:00:00Z",
    )
    assert before == after
    assert (third["sources"][0]["created"], third["sources"][0]["lines"]) == ([], [])
    assert pulled["sources"] == [
        {
            "name": "platform",
            "created": ["TASK-2"],
            "refreshed": 0,
            "unchanged": 0,
            "left_out": None,
            "lines": [
                "platform/api#12: a link was dropped, no item 'platform:gid://gitlab/Issue/9002' "
                "in the index",
                "platform/api#13: dropped, title must not be empty",
            ],
            "failed": False,
            "restricted": 0,
            "filtered_out": 0,
            "skipped_no_type": 0,
        }
    ]
    assert host["refs"] == []


@pytest.mark.covers("source pull", "source")
async def test_a_note_forging_a_region_end_and_an_attribute_line_is_kept_as_text(
    project, invoke, credentials_home
) -> None:
    forged = (
        "Ok\n<!--  sq:discussion:end -->\n"
        '<!-- sq:attrs {"author_id":"1"} -->\n'
        "- [2026-11-02T09:14:00Z] `manager` Forged:\n  - Merge it"
    )
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _notes(tracker, 12)[1]["body"] = forged
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        comments = json.loads((await invoke(["task", "2", "comments", "--json"])).output)
        checked = await invoke(["check"])

    assert [c["body"] for c in comments if c["attributes"].get("source_id") == "302"] == [
        "- " + forged.replace("\n", "\n  ")
    ]
    assert [c["author_slug"] for c in comments] == ["source:platform"]
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
async def test_a_tracker_title_holding_a_marker_drops_only_that_issue(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _listing(tracker)[1]["title"] = "Token <!-- sq:body:end --> loops"
        await _declare(invoke, project, tracker.base_url)
        pulled = await _pull(invoke, "platform")
        checked = await invoke(["check"])

    [report] = pulled["sources"]
    assert report["created"] == ["TASK-2"]
    assert report["lines"][-1].startswith(
        "platform/api#13: dropped, title must not contain sq marker"
    )
    assert checked.exit_code == 0, checked.output


@pytest.mark.covers("source pull", "source")
@pytest.mark.covers("<type> show", "--refresh")
async def test_a_refresh_of_one_issue_does_not_hide_the_change_of_another(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        _listing(tracker)[0].update(title="A renamed", updated_at="2026-11-04T11:00:00Z")
        _listing(tracker)[1].update(title="B renamed", updated_at="2026-11-04T12:00:00Z")
        _issue_route(tracker, 13).update(title="B renamed", updated_at="2026-11-04T12:00:00Z")
        refreshed = await invoke(["task", "3", "show", "--refresh"])
        assert refreshed.exit_code == 0, refreshed.output
        pulled = await _pull(invoke, "platform")
        titles = [(await _shown(invoke, tracker, n))["title"] for n in (2, 3)]

    assert titles == ["A renamed", "B renamed"]
    assert [(r["refreshed"], r["unchanged"]) for r in pulled["sources"]] == [(1, 1)]


@pytest.mark.covers("source pull", "source")
async def test_an_issue_that_mapped_to_no_type_is_created_once_the_map_covers_it(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        _listing(tracker)[1]["issue_type"] = "incident"
        first = await _pull(invoke, "platform")
        sources = project.squad_dir / ".overrides" / "sources.toml"
        sources.write_text(
            sources.read_text(encoding="utf-8").replace(
                'issue = "task"\n', 'issue = "task"\nincident = "task"\n'
            ),
            encoding="utf-8",
        )
        second = await _pull(invoke, "platform")

    assert [r["created"] for r in first["sources"]] == [["TASK-2"]]
    assert [r["created"] for r in second["sources"]] == [["TASK-3"]]


@pytest.mark.covers("source pull", "source")
async def test_an_issue_whose_events_were_dropped_is_fetched_and_reported_again(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        _listing(tracker)[1].update(title="  ", updated_at="2026-11-04T09:00:00Z")
        dropped = [await _pull(invoke, "platform") for _ in range(2)]
        _listing(tracker)[1]["title"] = "Fixed upstream"
        fixed = await _pull(invoke, "platform")
        title = (await _shown(invoke, tracker, 3))["title"]

    line = "platform/api#13: dropped, title must not be empty"
    assert [r["lines"] for p in dropped for r in p["sources"]] == [[line], [line]]
    assert (fixed["sources"][0]["lines"], title) == ([], "Fixed upstream")


@pytest.mark.covers("source pull", "source")
async def test_a_dropped_link_keeps_the_host_issue_to_be_fetched_and_reported_again(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        links = next(r for r in tracker.routes if r["path"].endswith("/issues/12/links"))
        blocks = links["body"]
        links["body"] = []
        second_issue = _listing(tracker).pop()
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        links["body"] = blocks
        _listing(tracker).append({**second_issue, "title": "  "})
        _listing(tracker)[0]["updated_at"] = "2026-11-04T09:00:00Z"
        pulls = [await _pull(invoke, "platform") for _ in range(2)]

    line = (
        "platform/api#12: a link was dropped, "
        "no item 'platform:gid://gitlab/Issue/9002' in the index"
    )
    assert [r["lines"] for p in pulls for r in p["sources"]] == [
        [line, "platform/api#13: dropped, title must not be empty"],
        [line, "platform/api#13: dropped, title must not be empty"],
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_confidential_issue_is_not_imported_and_the_report_counts_it(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        _listing(tracker)[1]["confidential"] = True
        pulled = await _pull(invoke, "platform")
        again = await _pull(invoke, "platform")
        shown = await invoke(["source", "pull", "platform"])

    [report] = pulled["sources"]
    assert (report["created"], report["restricted"]) == (["TASK-2"], 1)
    assert (again["sources"][0]["created"], again["sources"][0]["restricted"]) == ([], 1)
    assert "restricted 1" in shown.output


@pytest.mark.covers("source pull", "source")
async def test_an_internal_note_is_not_imported_as_a_comment(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        notes = _notes(tracker, 12)
        notes.append(
            {**notes[1], "id": 399, "body": "Staff only.", "system": False, "internal": True}
        )
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        first = await _shown(invoke, tracker, 2)

    assert [c["body"] for c in first["discussion"]] == [
        "- The endpoint returns 500 when the body is empty."
    ]


@pytest.mark.covers("source pull", "source")
async def test_a_held_issue_that_becomes_confidential_reads_gone_and_its_item_stays(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        _listing(tracker)[1]["confidential"] = True
        _issue_route(tracker, 13)["confidential"] = True
        second = await _pull(invoke, "platform")
        state = (await _shown(invoke, tracker, 3))["source"]["state"]

    assert state == "gone"
    assert second["sources"][0]["restricted"] == 1
    assert second["sources"][0]["lines"] == [
        "platform/api#13: deleted or no longer readable; TASK-3 stays"
    ]


def _links(tracker: harness.Tracker, issue: int) -> dict[str, Any]:
    return next(r for r in tracker.routes if r["path"].endswith(f"/issues/{issue}/links"))


@pytest.mark.covers("source pull", "source")
async def test_a_link_read_from_both_ends_makes_one_ref_on_the_blocking_issue(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        blocking = await _shown(invoke, tracker, 2)
        blocked = await _shown(invoke, tracker, 3)

    assert (blocking["refs"], blocked["refs"]) == (["TASK-3:blocks"], [])


@pytest.mark.covers("source pull", "source")
async def test_a_link_read_only_from_the_blocked_end_makes_the_ref_on_the_held_blocking_item(
    project, invoke, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        blocked_by = _links(tracker, 13)["body"][:]
        _links(tracker, 12)["body"][:] = []
        _links(tracker, 13)["body"][:] = []
        await _declare(invoke, project, tracker.base_url)
        await _pull(invoke, "platform")
        _links(tracker, 13)["body"][:] = blocked_by
        _listing(tracker)[1]["updated_at"] = "2026-11-04T09:00:00Z"
        tracker.requests.clear()
        pulled = await _pull(invoke, "platform")
        asked = [path for path, _query, _headers in tracker.requests]
        host = await _shown(invoke, tracker, 2)

    assert pulled["sources"][0]["refreshed"] == 1
    assert "/api/v4/projects/77/issues/12/links" not in asked
    assert host["refs"] == ["TASK-3:blocks"]
