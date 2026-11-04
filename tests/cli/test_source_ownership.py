"""What a tracker owns on a sourced item: the squad cannot write it, no `--as` names a source, and
a retype keeps the record."""

import json
from pathlib import Path

import pytest

from tests import _tracker_harness as harness
from tests.cli._output import read_json

pytestmark = pytest.mark.anyio

SECRET = "glpat-not-a-real-token"
MAPS = (
    '\n[sources.platform.maps.types.type]\nissue = "task"\n'
    '\n[sources.platform.maps.fields.priority.labels]\n"priority::high" = "high"\n'
)
UNLINK = "sq task 2 source unlink"


async def _mirror(invoke, project) -> None:
    """Pull `platform/api#12` as the first task, with the comment the source wrote on it."""
    override = project.squad_dir / ".overrides" / "sources.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        override.write_text(
            f'[sources.platform]\nconnector = "gitlab"\nfilter = "squads"\n'
            f'base_url = "{tracker.base_url}"\n{MAPS}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform"])
        assert pulled.exit_code == 0, pulled.output


def _events(*events: dict[str, str]) -> None:
    """Write *events* as `events.jsonl` in the working directory."""
    Path("events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


async def _run(invoke, args: list[str]) -> tuple[int, str]:
    result = await invoke(args)
    return result.exit_code, " ".join(result.output.split())


@pytest.mark.covers("<type> update", "--title")
async def test_update_refuses_the_title_and_a_mapped_field_of_a_sourced_item(
    project, invoke, credentials_home
) -> None:
    await _mirror(invoke, project)

    outcomes = [
        await _run(invoke, ["task", "2", "update", flag, value])
        for flag, value in (("--title", "Other"), ("--priority", "high"), ("--desc", "Mine"))
    ]

    owned = "error: TASK-2 is owned by source 'platform' (issue platform/api#12): its "
    assert outcomes == [
        (1, f"{owned}title is set by `sq source pull`; run `{UNLINK}` to edit it here"),
        (1, f"{owned}priority field is set by `sq source pull`; run `{UNLINK}` to edit it here"),
        (0, "updated TASK-2 tasks/TASK-000002-login-fails-on-empty-password.md"),
    ]


@pytest.mark.covers("<type> body", "--message")
async def test_the_body_refuses_to_rewrite_the_stored_description_of_a_sourced_item(
    project, invoke, credentials_home
) -> None:
    await _mirror(invoke, project)
    pair = "<!-- sq:view:source_description -->\nmine\n<!-- sq:view:source_description:end -->"

    assert await _run(invoke, ["task", "2", "body", "-m", pair]) == (
        1,
        "error: TASK-2 is owned by source 'platform' (issue platform/api#12): the stored body "
        f"of view 'source_description' is set by `sq source pull`; run `{UNLINK}` to edit it here",
    )


@pytest.mark.covers("<host> comment", "hash")
async def test_a_comment_a_source_wrote_can_be_neither_edited_nor_removed(
    project, invoke, credentials_home
) -> None:
    await _mirror(invoke, project)
    short = (await read_json(invoke, ["task", "2", "comments", "--json"]))[0]["short_hash"]

    outcomes = [
        await _run(invoke, ["task", "2", "comment", short, *verb, "--as", "manager"])
        for verb in (["edit", "-m", "Mine"], ["remove"])
    ]

    refusal = (
        f"error: {short} on TASK-2 was written by source 'platform' (issue platform/api#12); "
        "only `sq source pull` changes it"
    )
    assert outcomes == [(1, refusal), (1, refusal)]


@pytest.mark.covers("<host> comment", "--as")
@pytest.mark.covers("import", "file")
async def test_no_as_can_name_a_source(project, invoke, credentials_home) -> None:
    await _mirror(invoke, project)
    _events({"op": "comment", "target": "TASK-2", "message": "x", "as": "source:platform"})

    outcomes = [
        await _run(invoke, ["task", "2", "comment", "--as", "source:platform", "-m", "x"]),
        await _run(invoke, ["import", "events.jsonl"]),
    ]

    refusal = (
        "cannot act as 'source:platform': only `sq source pull` writes as a source, and no "
        "`--as` can name one"
    )
    assert outcomes == [
        (1, f"error: {refusal}"),
        (1, f"line 1: {refusal} 1 issue(s) found \u2014 nothing written."),
    ]


@pytest.mark.covers("<type> retype", "new-type")
async def test_a_retyped_item_keeps_its_source_record(project, invoke, credentials_home) -> None:
    await _mirror(invoke, project)

    retyped = await invoke(["task", "2", "retype", "bug"])
    shown = await read_json(invoke, ["bug", "2", "show", "--json"])

    assert retyped.exit_code == 0, retyped.output
    assert (shown["source"]["name"], shown["source"]["key"]) == ("platform", "platform/api#12")
