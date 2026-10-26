"""A role's body takes authored prose beside its definition tag, on every role kind: the tag
survives every write and sits first, ``--force`` only consents to overwriting written prose, and
the prose reaches no surface but the role's own body."""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section

pytestmark = pytest.mark.anyio

TAG = markers.open_marker(markers.view_tag("role_definition"))
OFF = markers.open_marker(markers.view_tag("role_definition", disabled=True))
KINDS = ["catalog", "template", "item-defined"]


async def _role(svc, kind: str):
    if kind == "catalog":
        return await svc.activate_role("tech-lead")
    if kind == "template":
        return await svc.activate_role(None, from_template="dev", tech="rust")
    return await svc.add_role(
        "security-analyst",
        name="Sentinel",
        job_title="Security analyst",
        description="Reviews threats.",
        mission="Keep it safe.",
    )


def _file(svc, role) -> Path:
    return item_file(svc.paths, role)


def _region(path: Path) -> str:
    return get_section(path.read_text(encoding="utf-8"), markers.BODY) or ""


def _put(path: Path, inner: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_section(text, markers.BODY, inner), encoding="utf-8")


def _tagged(prose: str, tag: str = TAG) -> str:
    return f"{tag}\n\n{prose}"


#: start region (None: as created) -> write -> expected region, or None when refused
ROWS = {
    "replace-over-tag-only": (None, ("P", False, False), _tagged("P")),
    "append-over-tag-only": (None, ("P", True, False), _tagged("P")),
    "replace-over-prose": (_tagged("Old"), ("P", False, False), None),
    "replace-force-over-prose": (_tagged("Old"), ("P", False, True), _tagged("P")),
    "append-over-prose": (_tagged("Old"), ("P", True, False), _tagged("Old\n\nP")),
    "clear-force": (_tagged("Old"), ("", False, True), TAG),
    "clear-no-force": (_tagged("Old"), ("", False, False), None),
    "append-tag-removed": ("Old", ("P", True, False), _tagged("Old\n\nP")),
    "replace-force-tag-removed": ("Old", ("P", False, True), _tagged("P")),
    "append-tag-at-bottom": ("Old\n\n" + TAG, ("P", True, False), _tagged("Old\n\nP")),
    "append-disabled-tag": (_tagged("Old", OFF), ("P", True, False), _tagged("Old\n\nP", OFF)),
    "replace-force-carrying-placed-tag": (
        _tagged("Old"),
        (_tagged("P"), False, True),
        _tagged("P"),
    ),
}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("row", list(ROWS))
async def test_a_role_body_write_keeps_the_tag_first_and_prose_after_it(svc, kind, row) -> None:
    start, (body, append, force), expected = ROWS[row]
    role = await _role(svc, kind)
    path = _file(svc, role)
    if start is None:
        assert _region(path).strip() == TAG, "a new role holds its tag alone"
    else:
        _put(path, start)
    before = path.read_bytes()

    if expected is None:
        with pytest.raises(SquadsError):
            await svc.set_body(role.id, body, append=append, force=force)
        assert path.read_bytes() == before
    else:
        await svc.set_body(role.id, body, append=append, force=force)
        assert _region(path).strip("\n") == expected


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("placed", "carried"), [(TAG, OFF), (OFF, TAG)])
async def test_a_body_carrying_a_differently_stated_tag_is_refused(
    svc, kind, placed, carried
) -> None:
    role = await _role(svc, kind)
    path = _file(svc, role)
    _put(path, _tagged("Old", placed))
    before = path.read_bytes()

    with pytest.raises(SquadsError, match="not placed"):
        await svc.set_body(role.id, _tagged("P", carried), force=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", KINDS)
async def test_prose_reaches_the_role_body_only(svc, kind) -> None:
    role = await _role(svc, kind)
    line = "distinctive-prose-line-4711"
    await svc.set_body(role.id, line)

    assert line in await svc.read_body(role.id)
    assert line in await svc.read_stored_body(role.id)
    assert line not in (await svc.get(role.id)).model_dump_json()
    await svc.regen(role.id)
    await svc.sync()
    root = svc.paths.root
    for generated in [*root.glob(".claude/agents/*.md"), root / "CLAUDE.md", root / "AGENTS.md"]:
        if generated.exists():
            assert line not in generated.read_text(encoding="utf-8"), generated


@pytest.mark.parametrize("kind", KINDS)
async def test_sync_and_repair_leave_a_role_holding_prose_byte_identical(svc, kind) -> None:
    role = await _role(svc, kind)
    await svc.set_body(role.id, "Prose.")
    path = _file(svc, role)
    before = path.read_bytes()

    await svc.sync()
    assert path.read_bytes() == before
    await svc.repair()
    assert path.read_bytes() == before
    assert [i for i in await svc.check() if i.item == role.id] == []


async def test_a_role_not_on_the_roster_still_refuses_a_body_write(svc) -> None:
    with pytest.raises(SquadsError):
        await svc.set_body("ROLE-009999", "x")


@pytest.mark.parametrize("slug", ["squads", "greeting", "sq-memory", "sq-task"])
@pytest.mark.parametrize(("append", "force"), [(False, False), (True, False), (False, True)])
async def test_system_and_per_type_skills_still_refuse_every_body_write(
    svc, slug, append, force
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", slug)
    assert skill is not None
    before = _file(svc, skill).read_bytes()

    with pytest.raises(SquadsError, match="renders through its declared"):
        await svc.set_body(skill.id, "x", append=append, force=force)
    assert _file(svc, skill).read_bytes() == before


@pytest.mark.parametrize("kind", KINDS)
async def test_a_foreign_view_tag_in_a_role_body_names_no_verb_the_role_refuses(svc, kind) -> None:
    role = await _role(svc, kind)
    foreign = markers.open_marker(markers.view_tag("milestone_rollup"))

    with pytest.raises(SquadsError, match="not placed") as exc:
        await svc.set_body(role.id, f"x {foreign} y", append=True)

    assert "view add" not in str(exc.value)
    assert "view disable" not in str(exc.value)
    assert "Leave it out of the body" in str(exc.value)


@pytest.mark.parametrize("kind", KINDS)
async def test_the_role_refusal_points_at_body_for_prose_and_at_the_view_drop_for_the_definition(
    svc, kind
) -> None:
    role = await _role(svc, kind)

    with pytest.raises(SquadsError, match="is refused") as exc:
        await svc.disable_view(role.id, "role_definition")

    text = str(exc.value)
    assert f"`sq role {role.slug} body`" in text
    assert "replace the generated definition itself, drop the view from `[selected]`" in text
    assert "to author this directly instead" not in text
