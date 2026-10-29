"""`sq memory <role> …`: a role's notebook of small facts, from adding one to forgetting it."""

import json

import pytest

from tests.cli._output import read_json
from tests.cli._roster import usage_error

pytestmark = pytest.mark.anyio

STAMP = "2026-06-07T10:00:00Z"
NO_TERSE = "error: no memory 'terse' for role 'manager'\n"


async def _remember(invoke, fact: str, *extra: str, role: str = "manager") -> None:
    result = await invoke(["memory", role, "add", fact, *extra])
    assert result.exit_code == 0, result.output


# ------------------------------------------------------------------------------------ role


@pytest.mark.covers("memory", "ROLE")
async def test_the_role_argument_names_whose_notebook_a_verb_reads(project, invoke) -> None:
    await invoke(["role", "activate", "architect"])
    await _remember(invoke, "Prefer uv over pip", role="architect")
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == []
    listed = await read_json(invoke, ["memory", "architect", "list", "--json"])
    assert [m["slug"] for m in listed] == ["prefer-uv-over-pip"]


@pytest.mark.covers("memory", "ROLE")
async def test_the_role_argument_takes_an_operator_slug(project, invoke) -> None:
    await invoke(["operator", "add", "Alice Tester"])
    result = await invoke(["memory", "op-alice", "add", "Likes short replies"])
    assert (result.exit_code, result.output) == (
        0,
        "remembered likes-short-replies for op-alice\n",
    )


@pytest.mark.covers("memory", "ROLE")
async def test_the_role_argument_still_reaches_the_notebook_of_an_archived_role(
    project, invoke
) -> None:
    await invoke(["role", "activate", "architect"])
    await _remember(invoke, "Prefer uv over pip", role="architect")
    await invoke(["role", "architect", "status", "Archived"])
    listed = await read_json(invoke, ["memory", "architect", "list", "--json"])
    assert [m["slug"] for m in listed] == ["prefer-uv-over-pip"]


@pytest.mark.covers("memory", "ROLE")
async def test_the_role_argument_refuses_a_slug_nobody_on_the_roster_has(project, invoke) -> None:
    result = await invoke(["memory", "nobody", "list"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------------- add


@pytest.mark.covers("memory add", "FACT")
async def test_add_files_the_fact_under_a_slug_made_from_it(project, invoke) -> None:
    result = await invoke(["memory", "manager", "add", "Prefer uv over pip"])
    assert (result.exit_code, result.output) == (0, "remembered prefer-uv-over-pip for manager\n")
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == [
        {
            "slug": "prefer-uv-over-pip",
            "filename": "prefer-uv-over-pip.md",
            "description": "Prefer uv over pip",
            "created_at": STAMP,
        }
    ]


@pytest.mark.covers("memory add", "FACT")
async def test_add_numbers_the_slug_of_a_fact_that_would_collide(project, invoke) -> None:
    await _remember(invoke, "Prefer uv over pip")
    result = await invoke(["memory", "manager", "add", "Prefer uv over pip"])
    assert (result.exit_code, result.output) == (
        0,
        "remembered prefer-uv-over-pip-2 for manager\n",
    )


@pytest.mark.covers("memory add", "FACT")
async def test_add_needs_a_fact(project, invoke) -> None:
    result = await invoke(["memory", "manager", "add"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq memory ROLE add [OPTIONS] FACT",
            "sq memory ROLE add --help",
            "Missing argument 'FACT'.",
        ),
    )


@pytest.mark.covers("memory add", "--slug")
async def test_add_slug_files_the_memory_under_the_given_slug(project, invoke) -> None:
    result = await invoke(["memory", "manager", "add", "Terse replies", "--slug", "terse"])
    assert (result.exit_code, result.output) == (0, "remembered terse for manager\n")
    shown = await read_json(invoke, ["memory", "manager", "show", "terse", "--json"])
    assert shown["summary"] == "Terse replies"


@pytest.mark.covers("memory add", "--file")
async def test_add_file_reads_the_memorys_body_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "detail.md"
    source.write_text("First paragraph.\n\nSecond paragraph.\n", encoding="utf-8")
    await _remember(invoke, "Terse replies", "--slug", "terse", "--file", str(source))
    shown = await read_json(invoke, ["memory", "manager", "show", "terse", "--json"])
    assert shown == {
        "slug": "terse",
        "summary": "Terse replies",
        "created_at": STAMP,
        "tags": [],
        "body": "First paragraph.\n\nSecond paragraph.",
    }


@pytest.mark.covers("memory add", "--file")
async def test_add_file_dash_reads_the_body_from_standard_input(project, invoke) -> None:
    result = await invoke(
        ["memory", "manager", "add", "Terse replies", "--slug", "terse", "--file", "-"],
        input="From stdin.\n",
    )
    assert result.exit_code == 0, result.output
    shown = await read_json(invoke, ["memory", "manager", "show", "terse", "--json"])
    assert shown["body"] == "From stdin."


@pytest.mark.covers("memory add", "--file")
async def test_add_file_refuses_a_path_that_cannot_be_read(project, invoke, tmp_path) -> None:
    missing = tmp_path / "missing.md"
    result = await invoke(["memory", "manager", "add", "Terse replies", "--file", str(missing)])
    assert (result.exit_code, result.output) == (
        1,
        f"error: cannot read file {str(missing)!r}: No such file or directory\n",
    )
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == []


# ------------------------------------------------------------------------------------ list


@pytest.mark.covers("memory list", "--json")
async def test_list_json_lists_the_notebook_and_is_empty_before_the_first_fact(
    project, invoke
) -> None:
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == []
    await _remember(invoke, "Terse replies", "--slug", "terse")
    assert json.dumps(
        await read_json(invoke, ["memory", "manager", "list", "--json"])
    ) == json.dumps(
        [
            {
                "slug": "terse",
                "filename": "terse.md",
                "description": "Terse replies",
                "created_at": STAMP,
            }
        ]
    )


# ------------------------------------------------------------------------------------ show


@pytest.mark.covers("memory show", "SLUG")
async def test_show_prints_the_memory_with_its_stamp_and_body(project, invoke, tmp_path) -> None:
    source = tmp_path / "detail.md"
    source.write_text("First paragraph.\n", encoding="utf-8")
    await _remember(invoke, "Terse replies", "--slug", "terse", "--file", str(source))
    result = await invoke(["memory", "manager", "show", "terse"])
    assert (result.exit_code, result.output) == (
        0,
        f"terse ({STAMP})\n\nFirst paragraph.\n",
    )


@pytest.mark.covers("memory show", "--json")
async def test_show_json_describes_the_memory(project, invoke) -> None:
    await _remember(invoke, "Terse replies", "--slug", "terse")
    shown = await read_json(invoke, ["memory", "manager", "show", "terse", "--json"])
    assert shown == {
        "slug": "terse",
        "summary": "Terse replies",
        "created_at": STAMP,
        "tags": [],
        "body": "Terse replies",
    }


@pytest.mark.covers("memory show", "SLUG")
async def test_show_refuses_a_slug_the_notebook_does_not_hold(project, invoke) -> None:
    result = await invoke(["memory", "manager", "show", "terse"])
    assert (result.exit_code, result.output) == (1, NO_TERSE)


# ---------------------------------------------------------------------------------- search


@pytest.mark.covers("memory search", "QUERY")
async def test_search_prints_each_matching_memory_with_the_lines_that_matched(
    project, invoke, tmp_path
) -> None:
    source = tmp_path / "detail.md"
    source.write_text("Pin the lockfile.\n", encoding="utf-8")
    await _remember(invoke, "Prefer uv over pip", "--slug", "tooling", "--file", str(source))
    await _remember(invoke, "Terse replies", "--slug", "terse")
    result = await invoke(["memory", "manager", "search", "UV"])
    assert (result.exit_code, result.output) == (
        0,
        "tooling  Prefer uv over pip\n    Prefer uv over pip\n",
    )


@pytest.mark.covers("memory search", "QUERY")
async def test_search_reads_the_body_as_well_as_the_summary(project, invoke, tmp_path) -> None:
    source = tmp_path / "detail.md"
    source.write_text("First paragraph.\n\nThe release is on Friday.\n", encoding="utf-8")
    await _remember(invoke, "Terse replies", "--slug", "terse", "--file", str(source))
    result = await invoke(["memory", "manager", "search", "FRIDAY"])
    assert (result.exit_code, result.output) == (
        0,
        "terse  Terse replies\n    The release is on Friday.\n",
    )


@pytest.mark.covers("memory search", "QUERY")
async def test_search_says_when_nothing_matches(project, invoke) -> None:
    await _remember(invoke, "Terse replies", "--slug", "terse")
    result = await invoke(["memory", "manager", "search", "nothing-like-this"])
    assert (result.exit_code, result.output) == (0, "no matches for nothing-like-this\n")


@pytest.mark.covers("memory search", "QUERY")
async def test_search_needs_a_query(project, invoke) -> None:
    result = await invoke(["memory", "manager", "search"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq memory ROLE search [OPTIONS] QUERY",
            "sq memory ROLE search --help",
            "Missing argument 'QUERY'.",
        ),
    )


@pytest.mark.covers("memory search", "--json")
async def test_search_json_lists_the_matching_memories_with_their_hits(
    project, invoke, tmp_path
) -> None:
    source = tmp_path / "detail.md"
    source.write_text("First paragraph.\n\nThe release is on Friday.\n", encoding="utf-8")
    await _remember(invoke, "Terse replies", "--slug", "terse", "--file", str(source))
    await _remember(invoke, "Prefer uv over pip", "--slug", "tooling")
    found = await read_json(invoke, ["memory", "manager", "search", "friday", "--json"])
    assert json.dumps(found) == json.dumps(
        [{"slug": "terse", "description": "Terse replies", "hits": ["The release is on Friday."]}]
    )
    assert await read_json(invoke, ["memory", "manager", "search", "absent", "--json"]) == []


# ---------------------------------------------------------------------------------- forget


@pytest.mark.covers("memory forget", "SLUG")
async def test_forget_deletes_the_memory(project, invoke) -> None:
    await _remember(invoke, "Terse replies", "--slug", "terse")
    result = await invoke(["memory", "manager", "forget", "terse"])
    assert (result.exit_code, result.output) == (0, "forgot terse for manager\n")
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == []


@pytest.mark.covers("memory forget", "SLUG")
async def test_forget_refuses_a_slug_the_notebook_does_not_hold(project, invoke) -> None:
    result = await invoke(["memory", "manager", "forget", "terse"])
    assert (result.exit_code, result.output) == (1, NO_TERSE)


# ------------------------------------------------------------------------------------ json


@pytest.mark.covers("memory add", "--json")
async def test_add_json_prints_the_memory_written_and_its_role(project, invoke, tmp_path) -> None:
    body = tmp_path / "body.md"
    body.write_text("Answer in one line.\n", encoding="utf-8")
    add = ["memory", "@Manager", "add", "Terse replies", "--file", str(body)]
    result = await invoke(["--at", STAMP, *add, "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "slug": "terse-replies",
                    "summary": "Terse replies",
                    "created_at": STAMP,
                    "tags": [],
                    "body": "Answer in one line.",
                },
                "role": "manager",
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.covers("memory forget", "--json")
async def test_forget_json_prints_the_memory_as_it_was_and_its_role(project, invoke) -> None:
    await _remember(invoke, "Terse replies", "--slug", "terse")
    result = await invoke(["memory", "@Manager", "forget", "terse", "--json"])
    assert result.exit_code == 0, result.output
    entry = {
        "slug": "terse",
        "summary": "Terse replies",
        "created_at": STAMP,
        "tags": [],
        "body": "Terse replies",
    }
    assert result.output == json.dumps({"entry": entry, "role": "manager"}, indent=2) + "\n"
    assert await read_json(invoke, ["memory", "manager", "list", "--json"]) == []
