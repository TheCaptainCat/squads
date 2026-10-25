"""`subentities_settled_with_parent`, selected on the review type, reports a review resting in a
status whose role is settled while one of its findings rests in a status whose role is not. Both
sides are read by role: a finding that is Fixed counts as outstanding, one that is Noted or
Deferred does not, and a review status of another name with the `done` role is judged alike.
"""

from dataclasses import dataclass

import pytest

from _helpers import create_item
from _selection_table import service_with
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_FRAGMENT = "unsettled finding"
_SIGNED = (
    '[statuses.Signed]\nrole = "done"\n\n[lifecycles.review.transitions]\n'
    'Approved = ["Signed"]\nSigned = []\n'
)
_NOT_SELECTED = '[items.review]\nvalidators = ["no_status_banner"]\n'


@dataclass(frozen=True)
class Shape:
    review: str
    findings: tuple[str, ...]
    workflow: str = ""
    expect: str | None = None  # the finding's message, None for silence


_SHAPES: dict[str, Shape] = {
    "approved-with-an-open-finding": Shape(
        "Approved", ("Open",), expect="status is Approved with 1 unsettled finding: F1"
    ),
    "approved-with-a-fixed-finding": Shape(
        "Approved", ("Fixed",), expect="status is Approved with 1 unsettled finding: F1"
    ),
    "approved-with-every-finding-settled": Shape(
        "Approved", ("Verified", "WontFix", "Noted", "Deferred")
    ),
    "approved-names-every-unsettled-finding": Shape(
        "Approved",
        ("Open", "Verified", "Fixed"),
        expect="status is Approved with 2 unsettled findings: F1, F3",
    ),
    "rejected-with-an-open-finding": Shape(
        "Rejected", ("Open",), expect="status is Rejected with 1 unsettled finding: F1"
    ),
    "in-review-with-an-open-finding": Shape("InReview", ("Open",)),
    "another-name-with-the-done-role": Shape(
        "Signed", ("Open",), _SIGNED, expect="status is Signed with 1 unsettled finding: F1"
    ),
    "type-not-selecting-the-rule": Shape("Approved", ("Open",), _NOT_SELECTED),
}


@pytest.mark.parametrize("shape", _SHAPES)
async def test_a_settled_review_is_reported_exactly_when_a_finding_is_unsettled(
    project, shape: str
) -> None:
    row = _SHAPES[shape]
    svc = (
        service_with(project.squad_dir, row.workflow)
        if row.workflow
        else service.open_service(client_cwd=project.squad_dir)
    )
    carrier = (await create_item(svc, "task", "carrier")).item
    review = (await create_item(svc, "review", "r")).item
    for status in row.findings:
        await svc.add_finding(
            review.id,
            "f",
            status=status,
            deferred_to=carrier.id if status == "Deferred" else None,
        )
    await svc.update(review.id, status=row.review, force=True)
    found = [(i.level, i.message) for i in await svc.check() if _FRAGMENT in i.message]
    assert found == ([] if row.expect is None else [("warn", row.expect)])
