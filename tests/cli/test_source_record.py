"""The `source` record an item carries, the lookups derived from it, and the author namespace of
sourced text."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

RECORD = {
    "name": "platform",
    "id": "48211",
    "key": "platform/api#12",
    "state": "open",
    "updated_at": "2026-11-03T20:41:07Z",
    "author_id": "4567",
    "author_handle": "pchat",
}


async def _mirror(invoke, project, profile, title: str, record: dict[str, str]) -> Path:
    """An item of the host type whose file carries *record* as its `source`."""
    created = await invoke(["create", profile.host, title, "--author", "manager"])
    assert created.exit_code == 0, created.output
    path = next(
        p
        for p in (project.squad_dir / profile.host_folder).glob(f"{profile.host_prefix}-*.md")
        if title.lower() in p.name
    )
    lines = "source:\n" + "".join(f"  {key}: '{value}'\n" for key, value in record.items())
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\nstatus:", f"\n{lines}status:", 1), encoding="utf-8")
    return path


@pytest.mark.covers("check")
async def test_an_item_whose_source_record_is_malformed_is_refused_naming_its_file(
    project, invoke, profile
) -> None:
    incomplete = {key: value for key, value in RECORD.items() if key != "author_handle"}
    await _mirror(invoke, project, profile, "Mirror", incomplete)

    result = await invoke(["check"])

    assert (result.exit_code, result.output.splitlines()[0]) == (
        3,
        f"error {profile.host_prefix}-000002-mirror.md: invalid item data in "
        f"{profile.host_path(2, 'mirror')}: "
        "source.author_handle: Field required",
    )


@pytest.mark.covers("repair")
async def test_repair_rebuilds_the_index_of_sourced_items_to_the_one_it_replaces(
    project, invoke, profile
) -> None:
    await _mirror(invoke, project, profile, "Mirror", RECORD)
    await _mirror(
        invoke, project, profile, "Twin", {**RECORD, "key": "platform/api#13", "id": "48212"}
    )
    await invoke(["repair"])
    before = [(await invoke([profile.host, n, "show", "--json"])).output for n in ("2", "3")]
    index = project.squad_dir / ".squads.json"

    index.unlink()
    rebuilt = await invoke(["repair"])
    after = [(await invoke([profile.host, n, "show", "--json"])).output for n in ("2", "3")]

    assert (rebuilt.exit_code, rebuilt.output) == (0, "rebuilt index: 3 items, counter=3\n")
    assert after == before
    assert json.loads(before[0])["source"] == RECORD
    assert set(json.loads(index.read_text(encoding="utf-8"))) == {
        "schema_version",
        "counter",
        "padding",
        "items",
    }


@pytest.mark.covers("role add", "slug")
async def test_a_role_cannot_take_the_slug_that_names_sourced_authors(project, invoke) -> None:
    result = await invoke(
        [
            *("role", "add", "source", "--name", "Src", "--job-title", "Scribe"),
            *("--desc", "d", "--mission", "m"),
        ]
    )

    assert (result.exit_code, result.output) == (
        1,
        "error: slug 'source' is reserved as the namespace of authors that are not roles; "
        "a role needs another slug\n",
    )


@pytest.mark.covers("<host> comments", "--json")
async def test_a_comment_header_may_name_a_sourced_author(project, invoke, profile) -> None:
    path = await _mirror(invoke, project, profile, "Mirror", RECORD)
    await invoke(["repair"])
    await invoke([profile.host, "2", "comment", "-m", "Seen on the tracker", "--as", "manager"])
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("`manager` Catherine Manager:", "`source:platform` platform:"),
        encoding="utf-8",
    )

    comments = json.loads((await invoke([profile.host, "2", "comments", "--json"])).output)

    assert [(c["author_slug"], c["author"], c["body"]) for c in comments] == [
        ("source:platform", "via platform", "- Seen on the tracker")
    ]
