"""``sq check`` reports a ``sq:view:<name>`` tag that cannot resolve when read against its host,
as an **error-level**, unconditional finding — the binding invariant a document carrying such a
tag must satisfy, so it is not a member of the per-item validator catalog and carries no level
knob. **Two** reasons: *name* is undeclared or its presentation template
is missing, or *name* is declared and templated but its declared source cannot apply to the
host's own type.

It reuses the same ``squads._views.resolve_view_target`` predicate the placement verb
(``insert_view``) and read-time expansion already refuse/skip an unresolvable tag through,
rather than a second implementation of the same question.

All three shapes are covered — a name the spec never declared, a name declared but with no
resolvable template, and a name declared and templated but source-incompatible with the host —
plus the positive controls (a resolvable name reports nothing, for both a ``ref`` source and a
``subentity`` source on its hosting type), table-driven applicability coverage, and
level/catalog-membership assertions.
"""

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
    """A declared ``[views.<name>]`` entry with **no** presentation template anywhere -- the
    "declared but the template is missing" half of the first reason."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """A declared, **templated** ``[views.<name>]`` entry over sub-entity *kind* -- resolvable,
    so planting it on a host exercises the second reason (source applicability) rather than the
    first."""
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
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]


async def test_a_repeated_dangling_tag_is_reported_once_for_the_name(svc) -> None:
    """The finding names the offending view, once per name -- a repeated tag of the same bad
    name is separately caught as a duplicate marker (a distinct signal), not doubled up here
    too."""
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
    """Driven proof that the finding needs no ``[selected]`` validator bundle: ``svc`` here is
    the plain bundled-spec fixture no test in this module configures with any catalog
    selection, and the finding still fires -- because it sits beside the always-on file-level
    marker scan, not behind a catalog clause."""
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "always-on-check"))

    issues = await svc.check()
    assert any("always-on-check" in i.message for i in issues)


# ------------------------------------------------------------------ reason 2: source applicability


async def test_a_tag_naming_a_source_incompatible_view_is_an_error(project) -> None:
    """A declared, templated ``subentity``-source view over ``finding`` planted on a ``task``
    (which hosts ``subtask``, not ``finding``). Named for the second reason, which the first
    reason's own predicate never asked."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "finding")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _write_raw(svc, task.id, _plant_tag(svc, await _text(svc, task.id), "story_board"))

    issues = await svc.check()
    matches = [i for i in issues if "story_board" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    assert any("hosts" in i.message for i in matches)  # names the cause, not just the symptom


async def test_a_tag_naming_a_resolvable_subentity_view_on_its_hosting_type_reports_nothing(
    project,
) -> None:
    """Positive control for the second reason: the identical declaration, planted on a
    ``review`` (which hosts ``finding``), reports nothing -- the predicate refuses only
    the incompatible pairing, not every ``subentity``-source tag."""
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
    """Mirrors the tables in ``test_view_tag_placement.py`` and
    ``test_view_tag_expansion_at_read_time.py`` -- the same classification, exercised at the
    check surface."""
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
    """Control: ``milestone_rollup`` is ``ref``-sourced and carries no host constraint, so it
    reports nothing on any host type, proving the applicability predicate does not affect a
    ref-sourced view."""
    task = (await create_item(svc, "task", "T")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]


# --------------------------------------------------------------- fires on unparseable frontmatter


async def test_the_finding_fires_even_when_the_files_frontmatter_does_not_parse(svc) -> None:
    """The property that puts this finding in the file-level scan rather than the per-item
    validator catalog: it is resolved off the file's own type folder and filename, before
    ``read_frontmatter`` ever runs, so a file too broken to parse at all still reports it --
    exactly where a finding about an unreadable document earns its keep."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    tagged = _plant_tag(svc, text, "no-such-view")
    corrupted = tagged.replace("status: Draft", "status: [unterminated", 1)
    await _write_raw(svc, task.id, corrupted)

    issues = await svc.check()
    messages = [i.message for i in issues]
    assert any("no-such-view" in m for m in messages), messages  # the view finding still fires
    assert any("could not" in m.lower() or "malformed" in m.lower() for m in messages), messages


# --------------------------------------------------------------------------- catalog membership


def test_the_view_target_finding_is_not_a_member_of_the_per_item_validator_catalog() -> None:
    """Structural proof of the same claim for both reasons: ``_view_target_issues`` -- like the
    existing ``_marker_issues`` it sits beside -- is never registered in ``CATALOG``
    (``_services/_validators.py``), the selectable per-item validator catalog. It is floor
    behaviour, wired directly into the always-on file-level scan
    (``MaintenanceMixin._scan_for_check``), never a catalog member with a level knob.

    The broader guard is anchored on a prefix, not a bare substring: ``"view"`` is also a
    substring of ``"review"``, one of this project's own declared item types, so a bare
    ``"view" in name`` check would fail the day the catalog gains its first ``review_*``
    validator, pointing at the view-target finding for a break it had nothing to do with. See
    ``test_the_broadened_canary_does_not_fire_on_a_review_named_validator`` below for the
    anchoring driven against a real review-named entry rather than reasoned about."""
    from squads._services._validators import CATALOG

    assert "dangling_view" not in CATALOG
    assert "view_target" not in CATALOG
    assert not any(name.startswith("view") for name in CATALOG)


def test_the_broadened_canary_does_not_fire_on_a_review_named_validator() -> None:
    """Proof by construction, not by reasoning about the substring: a catalog carrying a
    ``review_*``-named member (exactly the shape that broke the old ``"view" in name`` check)
    must still pass the anchored assertion above. Built as a local dict rather than mutating
    the live, process-shared ``CATALOG`` — this test carries no cleanup burden and cannot leak
    into another test."""
    from squads._services._results import CheckIssue
    from squads._services._validators import CATALOG, ValidatorContext

    def _review_findings_closed(ctx: ValidatorContext) -> list[CheckIssue]:
        return []

    fake_catalog = {**CATALOG, "review_findings_closed": _review_findings_closed}

    # The trap this replaces: a bare substring match fires here, pointing at the view-tag
    # feature for a break the view-tag feature had nothing to do with.
    assert any("view" in name for name in fake_catalog)
    # The anchored form does not.
    assert not any(name.startswith("view") for name in fake_catalog)
