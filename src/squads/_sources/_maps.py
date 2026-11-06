"""What a source's maps make of one issue: each map reads one side of the issue at a time."""

from collections.abc import Collection
from dataclasses import dataclass

from squads._sources._connector import Issue
from squads._sources._registry import CONNECTORS
from squads._sources._spec import SourceMaps, SourceSpec


def mapped_types(maps: SourceMaps, issue: Issue) -> set[str]:
    """The item types the values of *issue* map to, over every side the type map names."""
    return {
        table[value]
        for side, table in maps.types.items()
        for value in issue.values(side)
        if value in table
    }


def mapped_values(maps: SourceMaps, code: str, issue: Issue) -> set[str]:
    """The values of badge field *code* that *issue* maps to, over every side its map names."""
    return {
        table[value]
        for side, table in maps.fields.get(code, {}).items()
        for value in issue.values(side)
        if value in table
    }


@dataclass(frozen=True)
class StatusChoice:
    """What a source's status map makes of one issue for one item type: the status to set and the
    side and value that gave it, or *problem*, the line saying why the status is left alone."""

    status: str = ""
    side: str = ""
    value: str = ""
    problem: str = ""


def mapped_status(
    source: SourceSpec, issue: Issue, item_type: str, states: Collection[str]
) -> StatusChoice | None:
    """The status the map of *source* gives *issue* as an item of *item_type* whose lifecycle holds
    *states*, or ``None`` when no side maps one of its values. The first side, in the connector
    version's order, that maps a value decides, even when it gives no status for the type."""
    for side in CONNECTORS[(source.connector, source.version)].status_sides:
        table = source.maps.statuses.get(side)
        hits = sorted(v for v in issue.values(side) if table and v in table)
        if not table or not hits:
            continue
        found = {value: next((s for s in table[value] if s in states), "") for value in hits}
        gives = {status for status in found.values() if status}
        if not gives:
            value = hits[0]
            return StatusChoice(
                problem=f"{value} maps to {', '.join(table[value])}, none of which is a status "
                f"of {item_type}; left alone"
            )
        if len(gives) > 1:
            return StatusChoice(
                problem=f"status left alone, its {side} map to {', '.join(sorted(gives))}"
            )
        value = next(v for v in hits if found[v])
        return StatusChoice(status=found[value], side=side, value=value)
    return None
