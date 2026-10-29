"""The display content a DTO carries beside its codes: labels, rendered badges and columns.

Every value here is human text of the display class: the key is part of the contract, its content
is not, and no client parses or compares it.
"""

from squads._api._dto._base import DTO


class Column(DTO):
    """One column of a table: the row key it shows and its header."""

    key: str
    header: str


class StatusDisplay(DTO):
    """A status as shown: its badge, and the colour intent of its role."""

    badge: str
    intent: str


class BadgeDisplay(DTO):
    """One badge field's value as shown: the field's label, then the badge with its code and
    with its label."""

    label: str
    badge: str
    badge_label: str


class AttributeDisplay(DTO):
    """A declared attribute with a label, as shown: its key, its label and its value as text."""

    key: str
    label: str
    value: str


class Display(DTO):
    """How an item or a sub-entity is shown: its type label, status, each badge field with a
    value (by field code, in declared order) and its assignee's name."""

    type: str
    status: StatusDisplay
    badges: dict[str, BadgeDisplay]
    assignee: str | None
