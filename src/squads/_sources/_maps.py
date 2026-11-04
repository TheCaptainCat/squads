"""What a source's maps make of one issue: each map reads one side of the issue at a time."""

from squads._sources._connector import Issue
from squads._sources._spec import SourceMaps


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
