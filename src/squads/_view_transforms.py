"""Transforms of the bundled views: pure functions from a resolved source to plain data."""

from squads._models._item import Item
from squads._workflow._models import WorkflowSpec

type Row = dict[str, str | None]


def status_rollup(source: list[Item], *, spec: WorkflowSpec) -> dict[str, list[Row]]:
    """The milestone's targeting members split into ``delivered``, ``outstanding`` and
    ``settled`` (stopped without delivering), by status role alone, each ordered by type and
    then sequence number."""
    parts: dict[str, list[Item]] = {"delivered": [], "outstanding": [], "settled": []}
    for member in source:
        if spec.is_delivered(member.type, member.status):
            parts["delivered"].append(member)
        elif spec.role_for(member.status).settled:
            parts["settled"].append(member)
        else:
            parts["outstanding"].append(member)
    return {
        name: [_row(m) for m in sorted(members, key=lambda m: (m.type, m.sequence_id))]
        for name, members in parts.items()
    }


def _row(member: Item) -> Row:
    return {
        "id": member.id,
        "type": member.type,
        "title": member.title,
        "status": member.status,
        "assignee": member.assignee,
    }
