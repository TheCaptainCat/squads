"""`sq repair`: rebuilding the index from the item files, reporting what it found, and
giving a shared number a new one on request."""

import errno
import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests import _stored_view as stored
from tests import _tracker_harness as harness
from tests._profile import REFERENCE, selected
from tests._squadwide import listed
from tests.cli import _source_record as source_record
from tests.cli._output import json_text
from tests.cli._pulled import item, shown_item

pytestmark = pytest.mark.anyio

P = selected()

TASK_FILE = "tasks/TASK-000003-build-the-query-parser.md"
ITEMS = [
    ("ROLE-1", "Catherine Manager"),
    ("FEAT-2", "Search"),
    ("TASK-3", "Build the query parser"),
    ("REV-4", "Review the query parser"),
]
TWIN = ("TASK-5", "Build the query parser")


def _add_twin_numbered_two(squad_dir: Path) -> None:
    """Write a second task whose number, 2, is the feature's."""
    original = (squad_dir / TASK_FILE).read_text(encoding="utf-8")
    twin = original.replace("id: TASK-3", "id: TASK-2").replace("sequence_id: 3", "sequence_id: 2")
    (squad_dir / "tasks/TASK-000002-build-the-query-parser.md").write_text(twin, encoding="utf-8")


@pytest.mark.covers("repair")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_repair_rebuilds_a_lost_index_from_the_item_files(populated_project, invoke) -> None:
    (populated_project.squad_dir / ".squads.json").unlink()
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (0, "rebuilt index: 4 items, counter=4\n")
    assert await listed(invoke) == ITEMS
    shown = await invoke(["task", "3", "show", "--json"])
    assert [s["local_id"] for s in json.loads(shown.output)["subentities"]] == [
        "ST1",
        "ST2",
    ]


@pytest.mark.covers("repair")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_repair_names_an_indexed_item_whose_file_is_gone_and_keeps_the_counter(
    populated_project, invoke
) -> None:
    (populated_project.squad_dir / "reviews/REV-000004-review-the-query-parser.md").unlink()
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        0,
        "rebuilt index: 3 items, counter=4\n"
        "warn REV-4: indexed but no markdown file found (deleted?)\n",
    )
    assert [i for i, _ in await listed(invoke)] == ["ROLE-1", "FEAT-2", "TASK-3"]


@pytest.mark.covers("repair", "--json")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_repair_json_prints_what_the_rebuild_found(populated_project, invoke) -> None:
    (populated_project.squad_dir / "tasks/TASK-000009-broken.md").write_text(
        "---\n: : bad\n", encoding="utf-8"
    )
    result = await invoke(["repair", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        json_text(
            {
                "indexed": 4,
                "counter": 9,
                "notice": None,
                "missing": [],
                "unreadable": [
                    "TASK-000009-broken.md: file has no `id` in frontmatter — its previous index "
                    "entry, if any, was carried forward as-is; fix the file and repair again"
                ],
                "renumbered": [],
                "references_left": False,
                "references": [],
            }
        ),
    )


@pytest.mark.covers("repair", "--renumber")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_renumber_gives_a_shared_number_a_new_one(populated_project, invoke) -> None:
    _add_twin_numbered_two(populated_project.squad_dir)
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (
        0,
        "rebuilt index: 5 items, counter=5\n"
        "  renumbered TASK-2 -> TASK-5 (tasks/TASK-000005-build-the-query-parser.md)\n",
    )
    assert await listed(invoke) == [*ITEMS, TWIN]


@pytest.mark.covers("repair")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_repair_refuses_two_ids_that_share_a_number_and_keeps_the_index(
    populated_project, invoke
) -> None:
    _add_twin_numbered_two(populated_project.squad_dir)
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        1,
        "error: refusing to rebuild the index: it keys items by number:\n"
        "  - 2 files carry number 2 under different ids "
        "(features/FEAT-000002-search.md, tasks/TASK-000002-build-the-query-parser.md); "
        "run `sq repair --renumber` to give one of them a new number\n",
    )
    assert await listed(invoke) == ITEMS


@pytest.mark.covers("repair", "--renumber")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_renumber_refuses_an_id_two_files_carry_to_be_merged_by_hand(
    populated_project, invoke
) -> None:
    original = (populated_project.squad_dir / TASK_FILE).read_bytes()
    (populated_project.squad_dir / "tasks/TASK-000003-dup.md").write_bytes(original)
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (
        1,
        "error: refusing to rebuild the index: it keys items by number:\n"
        "  - 2 files carry the id TASK-3 (tasks/TASK-000003-build-the-query-parser.md, "
        "tasks/TASK-000003-dup.md); merge the content you want into one file, delete the "
        "other by hand, then run `sq repair`\n",
    )
    assert await listed(invoke) == ITEMS


@pytest.mark.covers("repair")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_repair_refuses_a_same_id_pair_a_renumber_resolves_before_writing(
    populated_project, invoke
) -> None:
    squad = populated_project.squad_dir
    original = (squad / TASK_FILE).read_text(encoding="utf-8")
    (squad / "tasks/TASK-000003-twin.md").write_text(
        original.replace("title: Build the query parser", "title: Twin parser"), encoding="utf-8"
    )
    index = (squad / ".squads.json").read_bytes()
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        1,
        "error: refusing to rebuild the index: it keys items by number:\n"
        "  - 2 files carry the id TASK-3 (tasks/TASK-000003-build-the-query-parser.md, "
        "tasks/TASK-000003-twin.md); run `sq repair --renumber` to give one of them a new "
        "number\n",
    )
    assert (squad / ".squads.json").read_bytes() == index


@pytest.mark.covers("repair", "--json")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_renumber_json_lists_each_moved_file_and_each_reference_left(
    populated_project, invoke
) -> None:
    squad = populated_project.squad_dir
    original = (squad / TASK_FILE).read_text(encoding="utf-8")
    twin = original.replace("title: Build the query parser", "title: Twin parser")
    (squad / "tasks/TASK-000003-twin.md").write_text(twin, encoding="utf-8")
    kept = squad / TASK_FILE
    kept.write_text(original.replace("_TODO: describe this task._", "See TASK-3."), "utf-8")
    result = await invoke(["repair", "--renumber", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        json_text(
            {
                "indexed": 5,
                "counter": 5,
                "notice": None,
                "missing": [],
                "unreadable": [],
                "renumbered": [
                    {
                        "old": "TASK-3",
                        "new": "TASK-5",
                        "file": "tasks/TASK-000003-twin.md",
                        "target": "tasks/TASK-000005-twin.md",
                    }
                ],
                "references_left": True,
                "references": [
                    {
                        "id": "TASK-3",
                        "file": TASK_FILE,
                        "where": "body:23",
                        "text": "See TASK-3.",
                    }
                ],
            }
        ),
    )


@pytest.mark.covers("repair", "--json")
@pytest.mark.bundled_only("repairs items of the bundled types")
async def test_renumber_json_names_the_moved_file_that_holds_a_reference(
    populated_project, invoke
) -> None:
    squad = populated_project.squad_dir
    original = (squad / TASK_FILE).read_text(encoding="utf-8")
    (squad / "tasks/TASK-000003-twin.md").write_text(
        original.replace("title: Build the query parser", "title: Twin parser"), encoding="utf-8"
    )
    note = "See TASK-3 for context, and a long line " + "x" * 70
    cross = (
        original.replace("id: TASK-3", "id: TASK-2")
        .replace("sequence_id: 3", "sequence_id: 2")
        .replace("_TODO: describe this task._", note)
    )
    (squad / "tasks/TASK-000002-cross.md").write_text(cross, encoding="utf-8")
    result = await invoke(["repair", "--renumber", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        json_text(
            {
                "indexed": 6,
                "counter": 6,
                "notice": None,
                "missing": [],
                "unreadable": [],
                "renumbered": [
                    {
                        "old": "TASK-3",
                        "new": "TASK-5",
                        "file": "tasks/TASK-000003-twin.md",
                        "target": "tasks/TASK-000005-twin.md",
                    },
                    {
                        "old": "TASK-2",
                        "new": "TASK-6",
                        "file": "tasks/TASK-000002-cross.md",
                        "target": "tasks/TASK-000006-cross.md",
                    },
                ],
                "references_left": True,
                "references": [
                    {
                        "id": "TASK-3",
                        "file": "tasks/TASK-000006-cross.md",
                        "where": "body:23",
                        "text": note,
                    }
                ],
            }
        ),
    )


def _lock_refused(monkeypatch, code: int) -> None:
    """Make taking the index lock fail with the system error *code*."""

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(code, os.strerror(code))

    monkeypatch.setattr("filelock.FileLock.acquire", refuse)


@pytest.mark.covers("repair")
async def test_repair_on_a_file_system_without_file_locks_names_the_lock(
    populated_project, invoke, monkeypatch
) -> None:
    _lock_refused(monkeypatch, errno.ENOSYS)
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: cannot take the index lock {populated_project.lock_path}: "
        "Function not implemented; this file system does not support file locks, so sq cannot "
        "guard the index there, move the squad to one that does\n",
    )


@pytest.mark.covers("repair")
async def test_repair_with_a_lock_file_it_cannot_open_does_not_blame_the_file_system(
    populated_project, invoke, monkeypatch
) -> None:
    _lock_refused(monkeypatch, errno.EACCES)
    before = (await invoke(["list", "--json"])).output
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: cannot take the index lock {populated_project.lock_path}: Permission denied\n",
    )
    assert (await invoke(["list", "--json"])).output == before


@pytest.mark.covers("repair")
async def test_repair_leaves_the_pair_of_a_stored_view_named_head_alone(
    populated_project, invoke
) -> None:
    # the tag of a view named `head` is shaped like a retired badge region's; the sweep must skip it
    stored.declare_stored_view(populated_project.squad_dir, "head")
    added = await invoke([P.ref, str(REFERENCE), "view", "add", "head"])
    assert added.exit_code == 0, added.output
    [path] = (populated_project.squad_dir / P.ref_folder).glob(
        f"{P.ref_prefix}-{REFERENCE:06d}-*.md"
    )
    pair = stored.pair().replace(stored.VIEW, "head")
    # no verb writes this view's stored body: put the text between the tags in the file
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            stored.pair("").replace(stored.VIEW, "head"), pair
        ),
        encoding="utf-8",
    )
    shown = await invoke([P.ref, str(REFERENCE), "show", "--json"])

    repaired = await invoke(["repair"])

    assert repaired.exit_code == 0, repaired.output
    assert (await invoke([P.ref, str(REFERENCE), "show", "--json"])).output == shown.output


MANAGER_FILE = "agents/roles/ROLE-000001-manager.md"
DEFINITION_TAG = "<!-- sq:view:role_definition -->"
PLAYBOOK_TAG = "<!-- sq:view:role_playbook -->"


def _without_playbook_tag(squad_dir: Path, *, prose: str = "") -> Path:
    """The manager's role file with its playbook tag taken out and *prose* put in its place."""
    path = squad_dir / MANAGER_FILE
    text = path.read_text(encoding="utf-8")
    assert PLAYBOOK_TAG in text
    path.write_text(text.replace(PLAYBOOK_TAG, prose), encoding="utf-8")
    return path


@pytest.mark.covers("repair")
async def test_repair_places_the_playbook_tag_after_the_definition_tag_of_a_role_body(
    populated_project, invoke
) -> None:
    path = _without_playbook_tag(populated_project.squad_dir)
    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert f"{DEFINITION_TAG}\n\n{PLAYBOOK_TAG}" in path.read_text(encoding="utf-8")


@pytest.mark.covers("repair")
async def test_repair_keeps_the_prose_of_a_role_body_when_it_places_the_playbook_tag(
    populated_project, invoke
) -> None:
    path = _without_playbook_tag(populated_project.squad_dir, prose="Our own rule.")
    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert f"{DEFINITION_TAG}\n\n{PLAYBOOK_TAG}\n\nOur own rule." in path.read_text(
        encoding="utf-8"
    )


@pytest.mark.covers("repair")
async def test_repair_leaves_a_disabled_playbook_tag_of_a_role_body_alone(
    populated_project, invoke
) -> None:
    disabled = await invoke(["role", "manager", "view", "disable", "role_playbook"])
    assert disabled.exit_code == 0, disabled.output
    path = populated_project.squad_dir / MANAGER_FILE
    before = path.read_text(encoding="utf-8")
    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert path.read_text(encoding="utf-8") == before
    assert "<!-- sq:view:role_playbook:disabled -->" in before


@pytest.mark.covers("repair")
async def test_repair_rebuilds_the_index_of_sourced_items_to_the_one_it_replaces(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_record.pulled(invoke, project, profile, tracker)
        before = [(await invoke([profile.ref, n, "show", "--json"])).output for n in ("2", "3")]
        (project.squad_dir / ".squads.json").unlink()

        rebuilt = await invoke(["repair"])
        after = [(await invoke([profile.ref, n, "show", "--json"])).output for n in ("2", "3")]
        rebuilt_docs = [await shown_item(invoke, profile, tracker, n) for n in (2, 3)]

    assert (rebuilt.exit_code, rebuilt.output) == (0, "rebuilt index: 3 items, counter=3\n")
    assert after == before
    assert rebuilt_docs == [item(profile, 2, badge=False), item(profile, 3, badge=False)]
