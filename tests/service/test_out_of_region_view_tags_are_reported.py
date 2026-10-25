"""A ``sq:view:<name>`` tag outside ``sq:body`` never renders. ``sq check`` reports it, and
``view add`` / ``view disable`` refuse instead of placing a second copy. Tags inside the body
keep their behaviour exactly."""

import re
from pathlib import Path

import pytest

from _helpers import catalog_of, make_service
from squads import _view_tags as view_tags
from squads._errors import SquadsError
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_TAG = "<!-- sq:view:milestone_rollup -->\n"
_BODY_OPEN = "<!-- sq:body -->\n"
_BODY_CLOSE = "<!-- sq:body:end -->\n"
_DISCUSSION_OPEN = "<!-- sq:discussion -->\n"


def _without_tag(text: str) -> str:
    return text.replace(_TAG, "")


def _in_body(text: str) -> str:
    return text


def _before_first_region(text: str) -> str:
    return _without_tag(text).replace(_BODY_OPEN, _TAG + _BODY_OPEN, 1)


def _after_body_end(text: str) -> str:
    return _without_tag(text).replace(_BODY_CLOSE, _BODY_CLOSE + _TAG, 1)


def _in_another_region(text: str) -> str:
    return _without_tag(text).replace(_DISCUSSION_OPEN, _DISCUSSION_OPEN + _TAG, 1)


def _one_in_one_out(text: str) -> str:
    return text.replace(_BODY_CLOSE, _BODY_CLOSE + _TAG, 1)


# (id, transform, out_of_region)
_POSITIONS = [
    pytest.param(_in_body, False, id="in-body"),
    pytest.param(_before_first_region, True, id="before-first-region"),
    pytest.param(_after_body_end, True, id="after-body-end"),
    pytest.param(_in_another_region, True, id="inside-another-region"),
    pytest.param(_one_in_one_out, True, id="two-copies-one-in-one-out"),
]


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    return make_service(result.paths)


async def _milestone(svc, transform) -> tuple[str, Path]:
    created = await svc.create("milestone", "Ship it", author="manager")
    item, md = created.item, created.path
    md.write_text(transform(md.read_text(encoding="utf-8")), encoding="utf-8")
    return item.id, md


def _stray_warnings(issues, md: Path):
    return [
        i
        for i in issues
        if i.item == md.name and i.level == "warn" and "outside sq:body" in i.message
    ]


@pytest.mark.parametrize(("transform", "out_of_region"), _POSITIONS)
async def test_check_reports_only_out_of_region_tags(svc, transform, out_of_region):
    _, md = await _milestone(svc, transform)

    stray = _stray_warnings(await svc.check(), md)

    assert bool(stray) == out_of_region
    assert all(i.level == "warn" for i in stray)
    assert all("move it inside sq:body" in i.message for i in stray)


@pytest.mark.parametrize(("transform", "out_of_region"), _POSITIONS)
async def test_render_follows_the_region(svc, transform, out_of_region):
    item_id, md = await _milestone(svc, transform)

    region = md.read_text(encoding="utf-8").split(_BODY_OPEN, 1)[1].split(_BODY_CLOSE, 1)[0]
    rendered = await svc.read_body(item_id)

    in_region_tag = "sq:view:milestone_rollup" in region
    assert (rendered.strip() != view_tags.strip_view_tags(region).strip()) == in_region_tag


@pytest.mark.parametrize("verb", ["add_view", "disable_view"])
@pytest.mark.parametrize(("transform", "out_of_region"), _POSITIONS)
async def test_view_verbs_refuse_out_of_region_and_leave_the_file_alone(
    svc, transform, out_of_region, verb
):
    item_id, md = await _milestone(svc, transform)
    before = md.read_bytes()

    call = getattr(svc, verb)(item_id, "milestone_rollup")
    if out_of_region:
        with pytest.raises(SquadsError, match="outside sq:body"):
            await call
        assert md.read_bytes() == before
    else:
        await call  # in-region behaviour is unchanged: no refusal


@pytest.mark.parametrize("verb", ["add", "disable"])
@pytest.mark.parametrize(("transform", "out_of_region"), _POSITIONS)
async def test_cli_exit_codes(svc, invoke, transform, out_of_region, verb):
    item_id, md = await _milestone(svc, transform)
    before = md.read_bytes()

    result = await invoke(
        ["milestone", str(int(item_id.split("-")[1])), "view", verb, "milestone_rollup"]
    )

    if out_of_region:
        assert result.exit_code == 1, result.output
        assert "outside sq:body" in result.output
        assert md.read_bytes() == before
    else:
        assert result.exit_code == 0, result.output


# --- the three routes that reach the state


async def test_hand_edit_route(svc):
    _, md = await _milestone(svc, _after_body_end)
    assert _stray_warnings(await svc.check(), md)


async def test_template_override_route(svc):
    from squads._overrides._service import check_override_issues, scaffold_template

    path = scaffold_template(svc.paths.squad_dir, "items/task.md.j2")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- sq:view:\w+ -->\n", text)
    tag = match.group(0) if match else _TAG
    moved = _without_tag(text).replace(_BODY_CLOSE, _BODY_CLOSE + tag, 1)
    path.write_text(moved, encoding="utf-8")

    issues = check_override_issues(svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir))

    assert [i for i in issues if "outside sq:body" in i[2] and i[0] == "warn"]


async def test_adopt_route(svc, tmp_path):
    _, md = await _milestone(svc, _after_body_end)
    (svc.paths.squad_dir / ".squads.json").unlink()

    result = await service.adopt(root=tmp_path, roles_spec="minimal")
    adopted = make_service(result.paths)

    assert _stray_warnings(await adopted.check(), md)


async def test_the_duplicate_error_does_not_send_the_operator_to_a_refusing_verb(svc):
    _, md = await _milestone(svc, _one_in_one_out)

    duplicate = [
        i.message for i in await svc.check() if i.item == md.name and "duplicate" in i.message
    ]

    assert duplicate
    assert all("outside sq:body" in m and "remove or move that copy first" in m for m in duplicate)
    assert not any("or `sq milestone" in m for m in duplicate)
