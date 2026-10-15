"""A squad that selects `item_title_max:120` and `body_written` on every `work` and `records`
type gets both findings and keeps every validator its types ran before; its roster types keep
their lists unchanged and refuse either check; a squad that selects neither sees nothing. The
override text is generated from the bundled spec, so the table covers every bundled type.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    BODY_WRITTEN,
    BODY_WRITTEN_MEMBER,
    ITEM_TITLE_MAX,
    effective_triples,
    member_findings,
    two_check_override,
    write_override,
)
from squads._errors import SquadsError
from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._loader import lint_workflow_spec, load_workflow_spec

pytestmark = pytest.mark.anyio

_BASE = bundled_spec()
_TYPES = sorted(_BASE.items)
_WORK_AND_RECORDS = sorted(t for t, s in _BASE.items.items() if s.category != "roster")
_ROSTER = sorted(t for t, s in _BASE.items.items() if s.category == "roster")
_VARIANTS = {"two-checks": False, "with-older-checks": True}


def test_every_bundled_type_has_a_row_in_the_generated_override() -> None:
    text = two_check_override()
    assert {t for t in _BASE.items if f"[items.{t}]" in text} == set(_WORK_AND_RECORDS)
    older = two_check_override(older_checks=True)
    assert all(f"[items.{t}]" in older for t in _TYPES)


@pytest.mark.parametrize("variant", _VARIANTS)
@pytest.mark.parametrize("item_type", _TYPES)
async def test_the_merged_spec_keeps_what_the_bundled_spec_ran_and_adds_the_two_checks(
    project, item_type: str, variant: str
) -> None:
    write_override(project.squad_dir, two_check_override(older_checks=_VARIANTS[variant]))
    merged = load_workflow_spec(squad_dir=project.squad_dir)
    before = effective_triples(_BASE, item_type)
    after = effective_triples(merged, item_type)
    assert before <= after
    added = {name for name, _, _ in after - before}
    if item_type in _ROSTER:
        assert not added & {"item_title_max", "body_written"}
        assert merged.item_title_max(item_type) is None
        return
    assert {("item_title_max", "120", "warn"), ("body_written", None, "warn")} <= after
    assert merged.item_title_max(item_type) == 120


@pytest.mark.parametrize("item_type", _TYPES)
def test_under_the_bundled_spec_neither_check_is_effective_for_any_type(item_type: str) -> None:
    assert not {name for name, _, _ in effective_triples(_BASE, item_type)} & {
        "item_title_max",
        "body_written",
    }
    assert _BASE.item_title_max(item_type) is None


_TITLE = (
    "advisory: title is 121 chars (threshold: 120)"
    " — an item title is a one-line handle; put the detail in the body"
)


@pytest.mark.parametrize("variant", _VARIANTS)
@pytest.mark.parametrize("item_type", _WORK_AND_RECORDS)
async def test_each_type_reports_its_long_title_and_its_unwritten_body_and_nothing_else(
    project, item_type: str, variant: str
) -> None:
    write_override(project.squad_dir, two_check_override(older_checks=_VARIANTS[variant]))
    svc = service.open_service()
    long_title = (await create_item(svc, item_type, "T" * 121, body=BODY_WRITTEN)).item
    at_number = (await create_item(svc, item_type, "T" * 120, body=BODY_WRITTEN)).item
    unwritten = (await create_item(svc, item_type, "short")).item
    written = (await create_item(svc, item_type, "short too", body=BODY_WRITTEN)).item
    operator = await svc.add_operator("Alice Tester")
    skill = await svc.add_skill("a skill", description="d")

    issues = await svc.check()
    ours = [
        *member_findings(issues, ITEM_TITLE_MAX),
        *member_findings(issues, BODY_WRITTEN_MEMBER),
    ]
    assert sorted(ours) == sorted(
        [
            ("warn", long_title.id, _TITLE),
            (
                "warn",
                unwritten.id,
                "body is unwritten (still the template scaffold)"
                f' — write it with `sq {item_type} {unwritten.sequence_id} body -m "..."`',
            ),
        ]
    )
    reported = {item for _, item, _ in ours}
    assert not reported & {at_number.id, written.id, operator.id, skill.id}
    assert not reported & {i.id for i in await svc.list_roles()}


@pytest.mark.parametrize("entry", ["item_title_max:120", "body_written"])
@pytest.mark.parametrize("roster_type", _ROSTER)
async def test_either_check_on_a_roster_type_is_refused_naming_the_type_and_the_entry(
    project, roster_type: str, entry: str
) -> None:
    write_override(
        project.squad_dir,
        two_check_override() + f'\n[items.{roster_type}]\nvalidators = ["{entry}"]\n',
    )
    errors = [f for f in lint_workflow_spec(project.squad_dir) if f[0] == "error"]
    assert errors
    text = " ".join(f[2] for f in errors)
    assert f"item {roster_type!r}" in text
    assert repr(entry) in text
    with pytest.raises(SquadsError, match=f"item '{roster_type}'"):
        service.open_service()


async def test_a_squad_that_selects_neither_reports_no_finding_of_either(project) -> None:
    assert not (project.squad_dir / ".overrides" / "workflow.toml").exists()
    svc = service.open_service()
    for item_type in _WORK_AND_RECORDS:
        await create_item(svc, item_type, "T" * 200)
    issues = await svc.check()
    assert member_findings(issues, ITEM_TITLE_MAX) == []
    assert member_findings(issues, BODY_WRITTEN_MEMBER) == []
