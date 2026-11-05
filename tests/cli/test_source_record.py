"""The `source` record an item carries, the lookups derived from it, and the author namespace of
sourced text."""

import json
from pathlib import Path

import pytest

from tests import _tracker_harness as harness

pytestmark = pytest.mark.anyio

RECORD = {
    "name": "platform",
    "id": "48211",
    "key": "platform/api#12",
    "state": "open",
    "updated_at": "2026-11-03T20:41:07Z",
    "author_id": "4567",
}
SECRET = "glpat-not-a-real-token"


async def _pulled(invoke, project, profile, tracker: harness.Tracker) -> None:
    """Pull the two issues of the recorded tracker into the squad as items 2 and 3."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
        f'base_url = "{tracker.base_url}"\n'
        f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n',
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output
    pulled = await invoke(["source", "pull", "platform"])
    assert pulled.exit_code == 0, pulled.output


async def _mirror(invoke, project, profile, title: str, record: dict[str, str]) -> Path:
    """An item of the host type whose file carries *record* as its `source`; no command writes a
    record that lacks a field."""
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
    await _mirror(invoke, project, profile, "Mirror", RECORD)

    result = await invoke(["check"])

    assert (result.exit_code, result.output.splitlines()[0]) == (
        3,
        f"error {profile.host_prefix}-000002-mirror.md: invalid item data in "
        f"{profile.host_path(2, 'mirror')}: "
        "source.author_handle: Field required",
    )


@pytest.mark.covers("repair")
async def test_repair_rebuilds_the_index_of_sourced_items_to_the_one_it_replaces(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        before = [(await invoke([profile.ref, n, "show", "--json"])).output for n in ("2", "3")]
        (project.squad_dir / ".squads.json").unlink()

        rebuilt = await invoke(["repair"])
        after = [(await invoke([profile.ref, n, "show", "--json"])).output for n in ("2", "3")]

    assert (rebuilt.exit_code, rebuilt.output) == (0, "rebuilt index: 3 items, counter=3\n")
    assert after == before
    assert json.loads(before[0])["source"]["key"] == "platform/api#12"


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
async def test_a_comment_header_may_name_a_sourced_author(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await _pulled(invoke, project, profile, tracker)
        comments = json.loads((await invoke([profile.ref, "2", "comments", "--json"])).output)

    assert [(c["author_slug"], c["author"]) for c in comments] == [
        ("source:platform", '"Alice Smith" via platform @asmith')
    ]
