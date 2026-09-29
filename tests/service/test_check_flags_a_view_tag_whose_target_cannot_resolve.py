"""``sq check`` reports a ``sq:view:<name>`` tag that cannot resolve against its host as an
unconditional, error-level finding, for either an undeclared/templateless name or a
source-incompatible one, with positive controls for a resolvable tag on either source kind."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._models import _markers as markers
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import replace_section
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


async def _text(svc, item_id: str) -> str:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    return path.read_text(encoding="utf-8")


async def _write_raw(svc, item_id: str, text: str) -> None:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    path.write_text(text, encoding="utf-8")


def _plant_tag(svc, text: str, name: str) -> str:
    body = f"<!-- sq:{markers.view_tag(name)} -->\n"
    return replace_section(text, markers.BODY, body)


def _declare_dangling_view(squad_dir: Path, name: str) -> None:
    """Declare a ``[views.<name>]`` entry with no presentation template anywhere."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """Declare a resolvable, templated ``[views.<name>]`` entry over sub-entity *kind*."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{name}.md.j2").write_text(f"{name}\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _reopen(project) -> Service:
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


# ---------------------------------------------------------------------- reason 1: unresolvable


async def test_a_tag_naming_a_view_the_spec_never_declared_is_an_error(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "no-such-view"))

    issues = await svc.check()
    matches = [i for i in issues if "no-such-view" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    filename = svc.paths.abspath((await svc.get(task.id)).path).name
    assert all(i.item == filename for i in matches)


async def test_a_tag_naming_a_declared_view_with_no_resolvable_template_is_an_error(
    project,
) -> None:
    _declare_dangling_view(project.squad_dir, "templateless")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "templateless"))

    issues = await svc.check()
    matches = [i for i in issues if "templateless" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)


async def test_a_tag_naming_a_resolvable_bundled_view_reports_nothing(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]


async def test_a_repeated_dangling_tag_is_reported_once_for_the_name(svc) -> None:
    """A repeated tag of the same bad name is reported once, not doubled up."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    body = f"<!-- sq:{markers.view_tag('bogus')} -->\n<!-- sq:{markers.view_tag('bogus')} -->\n"
    await _write_raw(svc, task.id, replace_section(text, markers.BODY, body))

    issues = await svc.check()
    dangling = [i for i in issues if "bogus" in i.message and "duplicate" not in i.message]
    assert len(dangling) == 1, [i.message for i in issues]


async def test_two_different_dangling_names_in_one_file_are_each_reported(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    tag_a, tag_b = markers.view_tag("first-bogus"), markers.view_tag("second-bogus")
    body = f"<!-- sq:{tag_a} -->\n<!-- sq:{tag_b} -->\n"
    await _write_raw(svc, task.id, replace_section(text, markers.BODY, body))

    issues = await svc.check()
    messages = [i.message for i in issues]
    assert any("first-bogus" in m for m in messages), messages
    assert any("second-bogus" in m for m in messages), messages


async def test_dangling_name_check_fires_with_the_bundled_spec_and_no_catalog_selection(
    svc,
) -> None:
    """The finding fires with the plain bundled spec, needing no catalog selection."""
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "always-on-check"))

    issues = await svc.check()
    assert any("always-on-check" in i.message for i in issues)


# ------------------------------------------------------------------ reason 2: source applicability


async def test_a_tag_naming_a_source_incompatible_view_is_an_error(project) -> None:
    """A subentity-source view planted on a host whose kind it does not host is an error."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "finding")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "story_board"))

    issues = await svc.check()
    matches = [i for i in issues if "story_board" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    assert any("hosts" in i.message for i in matches)


async def test_a_tag_naming_a_resolvable_subentity_view_on_its_hosting_type_reports_nothing(
    project,
) -> None:
    """The same subentity-source view, planted on a host that actually hosts that kind,
    reports nothing."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "finding")
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item
    await _write_raw(svc, review.id, _plant_tag(svc, await _text(svc, review.id), "story_board"))

    issues = await svc.check()
    assert not any("story_board" in i.message for i in issues), [i.message for i in issues]


@pytest.mark.parametrize(
    ("host_type", "hosted_kind", "applies"),
    [
        ("review", "finding", True),
        ("task", "finding", False),
        ("feature", "story", True),
        ("task", "story", False),
        ("task", "subtask", True),
        ("review", "subtask", False),
    ],
)
async def test_source_applicability_is_table_driven_over_host_type_by_kind(
    project, host_type: str, hosted_kind: str, applies: bool
) -> None:
    """Source applicability is table-driven over host type by sub-entity kind, at check time."""
    name = f"probe_{host_type}_{hosted_kind}"
    _declare_resolvable_subentity_view(project.squad_dir, name, hosted_kind)
    svc = _reopen(project)
    host = (await create_item(svc, host_type, "H")).item
    await _write_raw(svc, host.id, _plant_tag(svc, await _text(svc, host.id), name))

    issues = await svc.check()
    matches = [i for i in issues if name in i.message]
    if applies:
        assert matches == []
    else:
        assert matches
        assert all(i.level == "error" for i in matches)


async def test_a_ref_source_tag_is_never_reported_for_source_applicability_the_control(
    svc,
) -> None:
    """A ref-sourced view carries no host constraint and reports nothing on any host type."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]


# --------------------------------------------------------------- fires on unparseable frontmatter


async def test_the_finding_fires_even_when_the_files_frontmatter_does_not_parse(svc) -> None:
    """The finding fires even when the file's frontmatter cannot even be parsed."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    tagged = _plant_tag(svc, text, "no-such-view")
    corrupted = tagged.replace("status: Draft", "status: [unterminated", 1)
    await _write_raw(svc, task.id, corrupted)

    issues = await svc.check()
    messages = [i.message for i in issues]
    assert any("no-such-view" in m for m in messages), messages
    assert any("could not" in m.lower() or "malformed" in m.lower() for m in messages), messages


# --------------------------------------------------------------------------- catalog membership


def test_the_view_target_finding_is_not_a_member_of_the_per_item_validator_catalog() -> None:
    """``_view_target_issues`` is never registered in the selectable per-item validator
    catalog; it is always-on floor behaviour. The guard is anchored on a prefix, not a bare
    substring, since "view" is also a substring of "review"."""
    from squads._services._validators import CATALOG

    assert "dangling_view" not in CATALOG
    assert "view_target" not in CATALOG
    assert not any(name.startswith("view") for name in CATALOG)


def test_the_broadened_canary_does_not_fire_on_a_review_named_validator() -> None:
    """A catalog carrying a ``review_*``-named member still passes the anchored assertion."""
    from squads._services._results import CheckIssue
    from squads._services._validators import CATALOG, ValidatorContext

    def _review_findings_closed(ctx: ValidatorContext) -> list[CheckIssue]:
        return []

    fake_catalog = {**CATALOG, "review_findings_closed": _review_findings_closed}

    assert any("view" in name for name in fake_catalog)
    assert not any(name.startswith("view") for name in fake_catalog)
