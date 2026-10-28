"""The corpus integrity rules of `sq check`: the file-load, raw-text, duplicate-id and cross-source
rules, and the reconciliation members. None can be selected or deselected, so each has a breach
case only.

A damaged file is arranged by editing or copying the item file, since no command writes one; the
index is left as it was, because the drift between files and index is what several rules report.
"""

import pytest
import yaml

from squads._workflow import bundled_spec
from tests.check._arrange import (
    activate,
    add_roster,
    address,
    copy_item_file,
    create,
    drop_frontmatter_line,
    edit_item_file,
    fresh_number,
    issue,
    item_path,
    ok,
    write_override,
)

pytestmark = pytest.mark.anyio

MALFORMED_ID = (
    "frontmatter `id` 'nope' is malformed -- an `id:` must read `<PREFIX>-<number>`, and the "
    "prefix half of the item's identity is read from this line, with nothing else in the file "
    "supplying it. Correct the `id:` line to match this file's `sequence_id` and its type's "
    "prefix; removing the line is reported too, so it is not a fix."
)


async def _task(invoke, title: str = "Alpha") -> str:
    """A task whose author role is active, so the type reports no missing author."""
    await activate(invoke, "tech-lead")
    return await create(invoke, "task", title, "tech-lead")


def _squad_path(project, item_id: str) -> str:
    """The squad-relative path of the item's file, forward slashes."""
    return item_path(project, item_id).relative_to(project.squad_dir).as_posix()


def _listed(project, *paths) -> str:
    """The files as a check message names them: squad-relative, with forward slashes."""
    return ", ".join(p.relative_to(project.squad_dir).as_posix() for p in paths)


# index_reconciled


@pytest.mark.breaches("index_reconciled")
async def test_an_indexed_item_whose_file_is_gone_is_an_error(project, invoke, check_json) -> None:
    gone = await _task(invoke, "Gone")
    await create(invoke, "task", "Kept", "tech-lead")
    assert await check_json() == ([], 0)

    # no command leaves the index entry behind: `remove` deletes both, so delete the file
    item_path(project, gone).unlink()

    assert await check_json() == (
        [issue("index_reconciled", "error", gone, "in index but no markdown file found")],
        3,
    )


@pytest.mark.breaches("index_reconciled")
async def test_an_item_file_the_index_does_not_know_is_an_error(
    project, invoke, check_json
) -> None:
    known = await _task(invoke)
    assert await check_json() == ([], 0)

    # no command writes a file without indexing it: copy one under a number the index never gave
    stray, _ = copy_item_file(project, known, number=fresh_number(project))

    assert await check_json() == (
        [issue("index_reconciled", "error", stray, "on disk but not in index (run `sq repair`)")],
        3,
    )


# backend_reconciled


@pytest.mark.breaches("backend_reconciled")
async def test_a_missing_managed_file_of_the_backend_is_an_error(
    project, invoke, check_json
) -> None:
    await _task(invoke)
    managed = "CLAUDE.md"
    assert await check_json() == ([], 0)

    # `sync` is the command that writes it, and none removes it
    (project.root / managed).unlink()

    assert await check_json() == (
        [
            issue(
                "backend_reconciled",
                "error",
                managed,
                "managed file missing — run `sq sync` (backend: claude_code)",
            )
        ],
        3,
    )


@pytest.mark.breaches("backend_reconciled")
async def test_a_missing_pointer_of_a_live_role_is_a_warning(project, invoke, check_json) -> None:
    await _task(invoke)
    pointer = ".claude/agents/tech-lead.md"
    assert await check_json() == ([], 0)

    # `sync` is the command that writes it, and none removes it
    (project.root / pointer).unlink()

    assert await check_json() == (
        [
            issue(
                "backend_reconciled",
                "warn",
                pointer,
                "managed pointer missing — run `sq sync` (backend: claude_code)",
            )
        ],
        0,
    )


# frontmatter_matches_index


@pytest.mark.breaches("frontmatter_matches_index")
async def test_a_title_edited_in_the_file_but_not_the_index_is_a_warning(
    project, invoke, check_json
) -> None:
    drifted = await _task(invoke, "Alpha")
    await create(invoke, "task", "Beta", "tech-lead")
    assert await check_json() == ([], 0)

    # only a command that also updates the index changes a title: edit the file alone
    edit_item_file(project, drifted, "title: Alpha", "title: Gamma")

    assert await check_json() == (
        [
            issue(
                "frontmatter_matches_index",
                "warn",
                drifted,
                "title drift between frontmatter and index; run `sq repair` before this item "
                "is mutated again, or the fix is lost silently",
            )
        ],
        0,
    )


# ids_unique


@pytest.mark.breaches("ids_unique")
async def test_two_files_carrying_one_id_are_an_error(project, invoke, check_json) -> None:
    original = await _task(invoke)
    assert await check_json() == ([], 0)

    # no command writes a second file for an id: copy the file under another slug
    first = item_path(project, original)
    _, copy = copy_item_file(project, original)

    assert await check_json() == (
        [
            issue(
                "ids_unique",
                "error",
                original,
                f"2 files carry this id ({_listed(project, first, copy)}); "
                "merge the content you want into one file, delete the other by hand, then run "
                "`sq repair`",
            )
        ],
        3,
    )


# numbers_unique


@pytest.mark.breaches("numbers_unique")
async def test_one_number_carried_under_two_ids_is_an_error(project, invoke, check_json) -> None:
    task = await _task(invoke)
    assert await check_json() == ([], 0)

    # the counter gives every item its own number: copy the file as a bug with the same one
    first = item_path(project, task)
    _, bug = copy_item_file(project, task, as_type="bug")

    assert await check_json() == (
        [
            issue(
                "numbers_unique",
                "error",
                f"#{task.rsplit('-', 1)[1]}",
                f"2 files carry number {task.rsplit('-', 1)[1]} under different ids "
                f"({_listed(project, bug, first)}); "
                "run `sq repair --renumber` to give one of them a new number",
            )
        ],
        3,
    )


# file_readable


@pytest.mark.breaches("file_readable")
async def test_an_item_file_that_is_not_utf8_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    await create(invoke, "task", "Intact", "tech-lead")
    assert await check_json() == ([], 0)

    # no command writes bytes that are not text: overwrite the file
    path = item_path(project, damaged)
    path.write_bytes(b"\xff" + path.read_bytes())

    assert await check_json() == (
        [
            issue(
                "file_readable",
                "error",
                path.name,
                f"{path} is not valid UTF-8: byte 0xff at offset 0 — invalid start byte",
            )
        ],
        3,
    )


# frontmatter_parses


@pytest.mark.breaches("frontmatter_parses")
async def test_a_frontmatter_that_is_not_yaml_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # no command writes a frontmatter it cannot read back: break the title line
    edit_item_file(project, damaged, "title: Damaged", "title: [Damaged")

    path = item_path(project, damaged)
    frontmatter = path.read_text(encoding="utf-8").split("---\n")[1]
    with pytest.raises(yaml.YAMLError) as parse_error:
        yaml.safe_load(frontmatter)
    assert await check_json() == (
        [
            issue(
                "frontmatter_parses",
                "error",
                path.name,
                f"malformed frontmatter in {path}: {parse_error.value}",
            )
        ],
        3,
    )


# id_present


@pytest.mark.breaches("id_present")
async def test_an_item_file_without_an_id_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # no command removes the id line: drop it from the file
    drop_frontmatter_line(project, damaged, "id")

    assert await check_json() == (
        [
            issue(
                "id_present",
                "error",
                item_path(project, damaged).name,
                "file has no `id` in frontmatter",
            )
        ],
        3,
    )


# id_well_formed


@pytest.mark.breaches("id_well_formed")
async def test_a_malformed_id_in_an_item_file_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # no command writes an id: it is allocated, so edit the line
    edit_item_file(project, damaged, f"id: {damaged}", "id: nope")

    assert await check_json() == (
        [issue("id_well_formed", "error", item_path(project, damaged).name, MALFORMED_ID)],
        3,
    )


# fields_valid


@pytest.mark.breaches("fields_valid")
async def test_an_item_file_without_a_required_field_is_an_error(
    project, invoke, check_json
) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # no command removes a required field: drop the status line
    drop_frontmatter_line(project, damaged, "status")

    assert await check_json() == (
        [
            issue(
                "fields_valid",
                "error",
                item_path(project, damaged).name,
                f"invalid item data in {_squad_path(project, damaged)}: "
                "missing required frontmatter 'status'",
            )
        ],
        3,
    )


# timestamps_present


@pytest.mark.breaches("timestamps_present")
async def test_an_item_file_without_updated_at_is_a_warning(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    await create(invoke, "task", "Intact", "tech-lead")
    assert await check_json() == ([], 0)

    # no command removes a timestamp: drop the line
    drop_frontmatter_line(project, damaged, "updated_at")

    assert await check_json() == (
        [
            issue(
                "timestamps_present",
                "warn",
                item_path(project, damaged).name,
                "frontmatter has no updated_at — a placeholder is invented on each read until "
                "any mutation writes the value the index holds back into the file",
            )
        ],
        0,
    )


# markers_balanced


@pytest.mark.breaches("markers_balanced")
async def test_a_body_region_that_is_never_closed_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # sq writes the markers and rejects them in prose: remove the closing one from the file
    edit_item_file(project, damaged, "<!-- sq:body:end -->\n", "")

    assert await check_json() == (
        [
            issue(
                "markers_balanced",
                "error",
                item_path(project, damaged).name,
                "unclosed marker <!-- sq:body -->",
            )
        ],
        3,
    )


# view_target_resolves


@pytest.mark.breaches("view_target_resolves")
async def test_a_view_tag_naming_no_declared_view_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    sibling = await create(invoke, "task", "Sibling", "tech-lead")
    # a disabled tag is not resolved, so it is the near-miss
    edit_item_file(
        project,
        sibling,
        "<!-- sq:body:end -->",
        "<!-- sq:view:bogus:disabled -->\n<!-- sq:body:end -->",
    )
    assert await check_json() == ([], 0)

    # `body` and `view add` refuse a view that is not declared: put the tag in the file
    edit_item_file(
        project, damaged, "<!-- sq:body:end -->", "<!-- sq:view:bogus -->\n<!-- sq:body:end -->"
    )

    assert await check_json() == (
        [
            issue(
                "view_target_resolves",
                "error",
                item_path(project, damaged).name,
                "no declared view 'bogus' with a resolvable presentation template; see "
                "`sq workflow views` for the declared set (<!-- sq:view:bogus -->)",
            )
        ],
        3,
    )


# view_tag_in_region


@pytest.mark.breaches("view_tag_in_region")
async def test_a_view_tag_outside_the_body_region_is_a_warning(project, invoke, check_json) -> None:
    moved = await _task(invoke, "Moved")
    await ok(invoke, *address(moved), "view", "add", "milestone_rollup")
    assert await check_json() == ([], 0)

    # `view add` places the tag inside the body and no command moves it: edit the file
    edit_item_file(
        project,
        moved,
        "<!-- sq:view:milestone_rollup -->\n<!-- sq:body:end -->",
        "<!-- sq:body:end -->\n<!-- sq:view:milestone_rollup -->",
    )

    assert await check_json() == (
        [
            issue(
                "view_tag_in_region",
                "warn",
                item_path(project, moved).name,
                "view tag <!-- sq:view:milestone_rollup --> sits outside sq:body, so it never "
                "renders; move it inside sq:body",
            )
        ],
        0,
    )


# seeded_view_resolves


@pytest.mark.breaches("seeded_view_resolves")
async def test_a_milestone_without_its_seeded_view_tag_is_an_error(
    project, invoke, check_json
) -> None:
    await activate(invoke, "product-owner")
    milestone = await create(invoke, "milestone", "Release", "product-owner")
    assert await check_json() == ([], 0)

    # `view disable` keeps the tag and no command deletes it: edit the file
    edit_item_file(project, milestone, "<!-- sq:view:milestone_rollup -->\n", "")

    address_words = " ".join(address(milestone))
    assert await check_json() == (
        [
            issue(
                "seeded_view_resolves",
                "error",
                item_path(project, milestone).name,
                "missing seeded view tag <!-- sq:view:milestone_rollup --> — restore it with "
                f"`sq {address_words} view add milestone_rollup`, or disable it with "
                f"`sq {address_words} view disable milestone_rollup`",
            )
        ],
        3,
    )


@pytest.mark.breaches("seeded_view_resolves")
async def test_a_milestone_carrying_its_seeded_view_tag_twice_is_an_error(
    project, invoke, check_json
) -> None:
    await activate(invoke, "product-owner")
    milestone = await create(invoke, "milestone", "Release", "product-owner")
    assert await check_json() == ([], 0)

    # `view add` collapses to one tag: write the second into the file
    edit_item_file(
        project,
        milestone,
        "<!-- sq:view:milestone_rollup -->\n",
        "<!-- sq:view:milestone_rollup -->\n<!-- sq:view:milestone_rollup -->\n",
    )

    address_words = " ".join(address(milestone))
    assert await check_json() == (
        [
            issue(
                "seeded_view_resolves",
                "error",
                item_path(project, milestone).name,
                "duplicate sq:view:milestone_rollup tag (2 copies, counting both states) — "
                f"collapse to one with `sq {address_words} view add milestone_rollup` or "
                f"`sq {address_words} view disable milestone_rollup`",
            )
        ],
        3,
    )


# body_regions_present


@pytest.mark.breaches("body_regions_present")
async def test_an_item_file_without_a_body_region_is_an_error(project, invoke, check_json) -> None:
    damaged = await _task(invoke, "Damaged")
    assert await check_json() == ([], 0)

    # sq writes the region and no command deletes it: remove the pair from the file
    edit_item_file(project, damaged, "<!-- sq:body -->\n", "")
    edit_item_file(project, damaged, "<!-- sq:body:end -->\n", "")

    assert await check_json() == (
        [
            issue(
                "body_regions_present",
                "error",
                item_path(project, damaged).name,
                "missing sq:body region (no `<!-- sq:body -->`/`<!-- sq:body:end -->` pair at "
                "all) — restore the marker pair in this file, for example from git",
            )
        ],
        3,
    )


# block_in_container


@pytest.mark.breaches("block_in_container")
async def test_a_subtask_block_outside_its_container_is_a_warning(
    project, invoke, check_json
) -> None:
    host = await _task(invoke)
    await ok(invoke, *address(host), "add-subtask", "Write it")
    await ok(invoke, *address(host), "subtask", "1", "body", "-m", "Write the first draft.")
    assert await check_json() == ([], 0)

    # sq places the block inside the container: move the container's end above the block
    edit_item_file(
        project, host, "<!-- sq:subtasks -->\n", "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n"
    )
    edit_item_file(
        project,
        host,
        "<!-- sq:subtask:ST1:end -->\n<!-- sq:subtasks:end -->\n",
        "<!-- sq:subtask:ST1:end -->\n",
    )

    assert await check_json() == (
        [
            issue(
                "block_in_container",
                "warn",
                item_path(project, host).name,
                "subtask block ST1 sits outside its 'subtasks' container -- move it between "
                "`<!-- sq:subtasks -->` and `<!-- sq:subtasks:end -->`",
            )
        ],
        0,
    )


# skill_type_declared


@pytest.mark.breaches("skill_type_declared")
async def test_a_live_skill_of_a_type_the_squad_no_longer_declares_is_a_warning(
    project, invoke, check_json
) -> None:
    skill = await add_roster(invoke, "skill", "sq-guide")
    # no command clears the prose beside a declared type's tag: cut it from the file
    body = item_path(project, skill).read_text(encoding="utf-8")
    prose = body.split("<!-- sq:body -->\n", 1)[1].split("<!-- sq:view:item_skill -->", 1)[0]
    edit_item_file(project, skill, prose, "")
    assert await check_json() == ([], 0)

    # a type is dropped by an override listing the types that survive
    kept = ", ".join(f'"{name}"' for name in bundled_spec().items if name != "guide")
    write_override(project, "workflow.toml", f"[selected]\nitems = [{kept}]\n")

    assert await check_json() == (
        [
            issue(
                "skill_type_declared",
                "warn",
                skill,
                "skill 'sq-guide' is Active but type 'guide' is no longer declared — its "
                "generated files have been withdrawn; restore the type to bring it back, or "
                "retire this skill (update its status) to close it out",
            )
        ],
        0,
    )
