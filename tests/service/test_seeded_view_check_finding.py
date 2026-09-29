"""The unconditional ``sq check`` finding for a document that has lost or duplicated one of
its seeded views' tags, table-driven over the shapes it must and must not fire for."""

import re
from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_DROP_MILESTONE_ROLLUP = """\
[selected]
views = ["role_definition", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _reopen(project) -> Service:
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


def _strip_body(svc, item) -> None:
    path = item_file(svc.paths, item)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")


async def test_a_host_missing_its_seeded_tag_is_reported_at_error_level(svc) -> None:
    milestone = (await create_item(svc, "milestone", "M")).item
    _strip_body(svc, milestone)

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    assert any("milestone_rollup" in i.message for i in matches)
    assert any(
        f"sq milestone {milestone.sequence_id} view add milestone_rollup" in i.message
        and f"sq milestone {milestone.sequence_id} view disable milestone_rollup" in i.message
        for i in matches
    ), [i.message for i in matches]


async def test_a_role_missing_its_tag_beside_prose_names_the_full_four_step_remedy(svc) -> None:
    """A role missing its tag beside real prose names the full four-step remedy, never
    ``view disable`` alone."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    text = replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "# Legacy prose, no tag at all."
    )
    path.write_text(text, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    message = next(i.message for i in matches)
    assert "drop 'role_definition' from [selected]" in message
    assert "sq import -" in message
    assert f'target": "{role.id}"' in message
    assert "restore 'role_definition' to [selected]" in message
    assert "sq role manager view add role_definition" in message
    assert "view disable" not in message


async def test_a_system_skill_missing_its_tag_beside_prose_names_the_four_step_remedy(
    svc,
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "greeting")
    assert skill is not None
    path = item_file(svc.paths, skill)
    text = replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "# Legacy prose, no tag at all."
    )
    path.write_text(text, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    message = next(i.message for i in matches)
    assert "drop 'greeting_skill' from [selected]" in message
    assert 'sq skill greeting body -m "" --force' in message
    assert "restore 'greeting_skill' to [selected]" in message
    assert "sq skill greeting view add greeting_skill" in message
    assert "view disable" not in message


async def test_a_per_item_type_skill_matching_a_declared_type_names_the_move_first_remedy(
    svc,
) -> None:
    """A per-item-type skill matching a declared type names the move-first remedy, never a
    plain clear-first one."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    path = item_file(svc.paths, skill)
    text = replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "# Legacy prose, no tag at all."
    )
    path.write_text(text, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    message = next(i.message for i in matches)
    assert "sq skill add <new-slug>" in message
    assert "sq-task" in message
    clear_cmd = 'sq skill sq-task body -m "" --force'
    assert clear_cmd in message
    assert message.index("sq skill add <new-slug>") < message.index(clear_cmd)
    assert "drop 'item_skill' from [selected]" in message
    assert "restore 'item_skill' to [selected]" in message
    assert "sq skill sq-task view add item_skill" in message


async def test_a_role_with_a_genuinely_empty_body_still_names_both_remedies(svc) -> None:
    """A role with a genuinely empty body still names both remedies."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _strip_body(svc, role)

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    assert any(
        "sq role manager view add role_definition" in i.message
        and "sq role manager view disable role_definition" in i.message
        for i in matches
    ), [i.message for i in matches]


def _remove_body_region(svc, item, replacement: str) -> None:
    """Delete the ``sq:body``/``sq:body:end`` marker pair entirely, leaving *replacement* in
    its place."""
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    region_pat = re.compile(
        re.escape(markers.open_marker(markers.BODY))
        + r".*?"
        + re.escape(markers.close_marker(markers.BODY))
        + r"\n?",
        re.DOTALL,
    )
    assert region_pat.search(text), "fixture no longer carries a sq:body region to remove"
    path.write_text(region_pat.sub(replacement, text), encoding="utf-8")


async def test_an_entirely_absent_region_with_stray_text_names_only_its_own_finding(
    svc,
) -> None:
    """An entirely absent region with unrecoverable stray text names only its own finding,
    never also the seeded-view one whose remedy would fail here."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _remove_body_region(svc, role, "Stray hand-typed text, not a heading, not a tag.\n")

    issues = await svc.check()

    matches = [i for i in issues if i.item == item_file(svc.paths, role).name]
    assert not any("missing seeded view tag" in i.message for i in matches), [
        i.message for i in matches
    ]
    assert any("missing sq:body region" in i.message for i in matches), [i.message for i in matches]
    assert any("recover the file by hand" in i.message for i in matches), [
        i.message for i in matches
    ]


async def test_an_entirely_absent_but_safely_recoverable_region_names_one_working_finding(
    svc,
) -> None:
    """A safely-recoverable absent region names one working finding, not a duplicate remedy."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    tag = markers.open_marker(markers.view_tag("role_definition"))
    _remove_body_region(svc, role, f"{tag}\n")

    issues = await svc.check()

    matches = [i for i in issues if i.item == item_file(svc.paths, role).name]
    assert not any("missing seeded view tag" in i.message for i in matches), [
        i.message for i in matches
    ]
    assert len(matches) == 1, [i.message for i in matches]
    assert "sq role manager view add role_definition" in matches[0].message
    assert "sq role manager view disable role_definition" in matches[0].message

    changed = await svc.add_view(role.id, "role_definition")
    assert changed
    assert not [i for i in await svc.check() if i.item == item_file(svc.paths, role).name]


async def test_a_host_carrying_its_tag_is_reported_nowhere(svc) -> None:
    await create_item(svc, "milestone", "M")

    issues = await svc.check()

    assert not any("missing seeded view tag" in i.message for i in issues)


async def test_a_host_carrying_its_tag_disabled_is_reported_nowhere(svc) -> None:
    """A disabled tag satisfies the presence condition; the check asks presence, not enablement."""
    milestone = (await create_item(svc, "milestone", "M")).item
    await svc.disable_view(milestone.id, "milestone_rollup")

    issues = await svc.check()

    assert not any("missing seeded view tag" in i.message for i in issues)
    assert not any("duplicate sq:view:" in i.message for i in issues)


async def test_a_retype_into_a_seeded_host_is_not_refused_and_not_rewritten(svc) -> None:
    """A retype into a seeded host stays readable and reported, never refused or rewritten."""
    task = (await create_item(svc, "task", "A task")).item
    before_body = await svc.read_body(task.id)

    res = await svc.retype(task.id, "milestone")

    assert res.item.type == "milestone"
    assert await svc.read_body(res.item.id) == before_body
    stored = get_section(item_file(svc.paths, res.item).read_text(encoding="utf-8"), markers.BODY)
    assert stored is not None
    assert "sq:view:milestone_rollup" not in stored

    issues = await svc.check()
    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    assert any("milestone_rollup" in i.message for i in matches)


async def test_the_next_body_write_after_a_retype_inserts_the_new_types_seeded_view(svc) -> None:
    """The next body write after a retype inserts the new type's seeded view."""
    task = (await create_item(svc, "task", "A task")).item
    res = await svc.retype(task.id, "milestone")

    await svc.set_body(res.item.id, "Prose written after the retype.", force=True)

    stored = get_section(item_file(svc.paths, res.item).read_text(encoding="utf-8"), markers.BODY)
    assert stored is not None
    assert "Prose written after the retype." in stored
    assert "<!-- sq:view:milestone_rollup -->" in stored
    issues = await svc.check()
    assert not any("missing seeded view tag" in i.message for i in issues), [
        i.message for i in issues
    ]


async def test_a_view_dropped_from_selected_seeds_nothing_no_report(svc) -> None:
    milestone = (await create_item(svc, "milestone", "M")).item
    _strip_body(svc, milestone)

    _write_override(svc.paths.squad_dir, _DROP_MILESTONE_ROLLUP)
    dropped = _reopen(svc.paths)

    issues = await dropped.check()

    assert not any("missing seeded view tag" in i.message for i in issues)


async def test_the_finding_fires_on_a_file_too_broken_to_parse(svc) -> None:
    """The finding fires even on a file too broken to parse, needing no resolved item."""
    milestone = (await create_item(svc, "milestone", "M")).item
    _strip_body(svc, milestone)
    path = item_file(svc.paths, milestone)
    text = path.read_text(encoding="utf-8")
    corrupted = text.replace("status: Draft", "status: [unterminated")
    path.write_text(corrupted, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    assert any(
        f"sq milestone {milestone.sequence_id} view add milestone_rollup" in i.message
        for i in matches
    ), [i.message for i in matches]


async def test_a_non_seeded_views_tag_is_never_required_absent_or_disabled(svc) -> None:
    """A non-seeded view has no obligation, whether its tag is absent, present, or disabled."""
    task = (await create_item(svc, "task", "A task")).item

    issues = await svc.check()
    assert not any("missing seeded view tag" in i.message for i in issues)

    await svc.add_view(task.id, "milestone_rollup")
    issues = await svc.check()
    assert not any("missing seeded view tag" in i.message for i in issues)

    await svc.disable_view(task.id, "milestone_rollup")
    issues = await svc.check()
    assert not any("missing seeded view tag" in i.message for i in issues)


async def test_a_same_name_duplicate_across_states_is_reported_once(svc) -> None:
    """An enabled and disabled copy of the same view is a duplicate by name, reported once."""
    milestone = (await create_item(svc, "milestone", "M")).item
    path = item_file(svc.paths, milestone)
    text = path.read_text(encoding="utf-8")
    doubled = replace_section(
        text,
        markers.BODY,
        (get_section(text, markers.BODY) or "")
        + f"\n{markers.open_marker(markers.view_tag('milestone_rollup', disabled=True))}\n",
    )
    path.write_text(doubled, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "duplicate sq:view:milestone_rollup" in i.message]
    assert len(matches) == 1, [i.message for i in issues]
    assert matches[0].level == "error"


async def test_a_same_state_duplicate_is_reported_once_naming_its_remedy(svc) -> None:
    """A same-state duplicate gets the same real remedy, reported once, naming it."""
    milestone = (await create_item(svc, "milestone", "M")).item
    path = item_file(svc.paths, milestone)
    text = path.read_text(encoding="utf-8")
    doubled = replace_section(
        text,
        markers.BODY,
        (get_section(text, markers.BODY) or "")
        + f"\n{markers.open_marker(markers.view_tag('milestone_rollup'))}\n",
    )
    path.write_text(doubled, encoding="utf-8")

    issues = await svc.check()

    matches = [i for i in issues if "sq:view:milestone_rollup" in i.message]
    assert len(matches) == 1, [i.message for i in issues]
    assert "duplicate sq:view:milestone_rollup" in matches[0].message
    assert f"sq milestone {milestone.sequence_id} view add milestone_rollup" in matches[0].message
    assert (
        f"sq milestone {milestone.sequence_id} view disable milestone_rollup" in matches[0].message
    )

    changed = await svc.add_view(milestone.id, "milestone_rollup")
    assert changed
    assert not [i for i in await svc.check() if i.item == path.name]
