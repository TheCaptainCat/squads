"""`subentity_deferral_resolved` reads the `deferred` and `retired` role flags of the statuses
involved, never a status name: a deferred sub-entity needs a pointer that resolves to a carrier
that has not been retired, and only a deferred one may hold a pointer.
"""

import pytest

from _helpers import create_item
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio

#: shape -> (carrier type, carrier status, the finding's status, its pointer, message fragment or
#: None). A pointer of "carrier" names the carrier created for the row, "self" its own review.
_SHAPES: dict[str, tuple[str, str, str, str | None, str | None]] = {
    "no-pointer": ("task", "InProgress", "Deferred", None, "names no carrying item"),
    "unresolved-pointer": ("task", "InProgress", "Deferred", "TASK-000999", "not found"),
    "cancelled-carrier": ("task", "Cancelled", "Deferred", "carrier", "will not carry the work"),
    "wontfix-bug-carrier": ("bug", "WontFix", "Deferred", "carrier", "will not carry the work"),
    "superseded-carrier": ("decision", "Superseded", "Deferred", "carrier", None),
    "active-carrier": ("task", "InProgress", "Deferred", "carrier", None),
    "own-review": ("task", "InProgress", "Deferred", "self", "to its own item"),
    "pointer-on-an-open-finding": (
        "task",
        "InProgress",
        "Open",
        "carrier",
        "only a deferred status carries one",
    ),
}


async def _warnings(svc: Service, review_id: str) -> list[str]:
    return [
        i.message
        for i in await svc.check()
        if i.item == review_id and i.level == "warn" and i.message.startswith("finding F1")
    ]


async def _hand_edit(svc: Service, review_id: str, **fields: str | None) -> None:
    """Edit the finding's frontmatter entry as a person would, then rebuild the index from it."""
    path = svc.paths.abspath((await svc.get(review_id)).path)
    text = path.read_text(encoding="utf-8")
    frontmatter = split_frontmatter(text)[0]
    entry = frontmatter["subentities"][0]
    for key, value in fields.items():
        if value is None:
            entry.pop(key, None)
        else:
            entry[key] = value
    path.write_text(replace_frontmatter(text, frontmatter), encoding="utf-8", newline="")
    await svc.repair()


@pytest.mark.parametrize("shape", _SHAPES)
async def test_a_finding_is_reported_exactly_when_its_pointer_or_carrier_is_unsound(
    svc, shape: str
) -> None:
    carrier_type, carrier_status, status, pointer, fragment = _SHAPES[shape]
    review = (await create_item(svc, "review", "r")).item
    await svc.add_finding(review.id, "f")
    carrier = (await create_item(svc, carrier_type, "carrier")).item
    await svc.update(carrier.id, status=carrier_status, force=True)
    tokens = {"carrier": carrier.id, "self": review.id}
    await _hand_edit(svc, review.id, status=status, deferred_to=tokens.get(str(pointer), pointer))
    messages = await _warnings(svc, review.id)
    if fragment is None:
        assert messages == []
    else:
        assert len(messages) == 1 and fragment in messages[0]
