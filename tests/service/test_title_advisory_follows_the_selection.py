"""The sub-entity title check and the create-time advisory are one selection. The selection
table drives every hosting type through every shape: a type that does not name
`subentity_title_max` gets neither a finding nor an advisory at any length; one that does gets
both at one character over its number and neither at it. Whatever the shape, the advisory is
produced exactly when a following `check()` reports the title finding for that sub-entity.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    BODY_WRITTEN,
    BUNDLED_HOSTING_ROWS,
    HOSTING_ROWS,
    TITLE_SHAPES,
    TypeRow,
    override_toml,
    service_with,
)
from squads._index._reflog import read_lines, reflog_path
from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio


def _title_findings(issues: list[CheckIssue], parent_id: str) -> dict[str, CheckIssue]:
    return {
        i.message.split()[2]: i for i in issues if i.item == parent_id and "title is" in i.message
    }


async def _drive(svc, row: TypeRow, threshold: int | None, level: str | None) -> None:
    """Add one sub-entity at one under, at and one over the number (120 when nothing is
    selected), then assert the advisory and the finding agree on every one."""
    assert row.kind is not None
    number = threshold if threshold is not None else 120
    parent = (await create_item(svc, row.type, "parent")).item
    added = {}
    for length in (number - 1, number, number + 1):
        res = await svc.add_block(parent.id, row.kind, "x" * length, body=BODY_WRITTEN)
        added[res.local_id] = (length, res.title_advisory)

    findings = _title_findings(await svc.check(), parent.id)
    for local_id, (length, advisory) in added.items():
        fires = threshold is not None and length > threshold
        assert (advisory is not None) is fires, (local_id, length)
        assert (local_id in findings) is fires, (local_id, length)
        if fires:
            assert f"{length} chars" in findings[local_id].message
            assert f"(threshold: {threshold})" in findings[local_id].message
            assert findings[local_id].level == level
            assert str(length) in advisory
            assert local_id in advisory

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    deltas = [
        ln.delta
        for ln in lines
        if ln.op == "subentity" and ln.target == parent.id and ln.delta.get("op") == "add"
    ]
    fired = [length for length, advisory in added.values() if advisory is not None]
    assert len([d for d in deltas if "title_advisory" in d]) == len(fired)


@pytest.mark.parametrize("shape", [s for s in TITLE_SHAPES if s != "unselected"])
@pytest.mark.parametrize("row", HOSTING_ROWS, ids=lambda r: r.id)
async def test_the_advisory_and_the_finding_agree_at_the_selected_number(
    project, row, shape
) -> None:
    entries, threshold, level = TITLE_SHAPES[shape]
    svc = service_with(project.squad_dir, override_toml(row, entries))
    await _drive(svc, row, threshold, level)


@pytest.mark.parametrize("row", HOSTING_ROWS, ids=lambda r: r.id)
async def test_a_hosting_type_that_does_not_select_the_check_gets_neither_at_any_length(
    project, row
) -> None:
    svc = service_with(project.squad_dir, override_toml(row, ()))
    await _drive(svc, row, None, None)


@pytest.mark.parametrize(
    "row", [r for r in HOSTING_ROWS if r.id == "records-hosting-a-kind"], ids=lambda r: r.id
)
async def test_a_type_selecting_another_sub_entity_check_gets_no_title_advisory(
    project, row
) -> None:
    """The hosting type must name some sub-entity check to load; naming a different one than
    the title check leaves the title check off, so a 121-character title is silent."""
    svc = service_with(project.squad_dir, override_toml(row, ("subentity_body_written",)))
    await _drive(svc, row, None, None)


@pytest.mark.parametrize("row", BUNDLED_HOSTING_ROWS, ids=lambda r: r.id)
async def test_selecting_the_check_on_another_type_leaves_this_type_as_it_was(project, row) -> None:
    other = next(r for r in BUNDLED_HOSTING_ROWS if r.type != row.type)
    toml = override_toml(row, (), others={other.type: ("subentity_title_max:80",)})
    svc = service_with(project.squad_dir, toml)
    await _drive(svc, other, 80, "warn")


@pytest.mark.parametrize("shape", TITLE_SHAPES)
@pytest.mark.parametrize("row", HOSTING_ROWS, ids=lambda r: r.id)
async def test_an_import_warns_for_an_imported_sub_entity_exactly_when_the_type_selects_the_check(
    project, row, shape
) -> None:
    entries, threshold, level = TITLE_SHAPES[shape]
    svc = service_with(project.squad_dir, override_toml(row, entries))
    parent = (await create_item(svc, row.type, "parent")).item
    number = threshold if threshold is not None else 120
    lengths = (number - 1, number, number + 1)
    text = "\n".join(
        json.dumps({"op": f"add-{row.kind}", "target": parent.id, "title": "x" * n})
        for n in lengths
    )
    result = await svc.import_events(text, default_as="manager")
    assert result.applied is not None, result.plan.issues
    selected = 1 if threshold is not None else 0
    advisories = [w for w in result.applied.warnings if w.startswith("Title is")]
    findings = [f for f in result.applied.findings if "threshold" in f.message]
    assert (len(advisories), len(findings)) == (selected, selected)
    assert {f.level for f in findings} <= {level}


@pytest.mark.parametrize("item_type", ["bug", "epic"])
async def test_a_type_hosting_no_kind_may_select_the_check_and_reports_nothing(
    project, item_type
) -> None:
    row = TypeRow(item_type, item_type)
    svc = service_with(project.squad_dir, override_toml(row, ("subentity_title_max",)))
    item = (await create_item(svc, item_type, "T" * 200)).item
    assert not [i for i in await svc.check() if i.item == item.id]
