"""Presentation shared by the renderers: colours for a status's intent, markup escaping, and table
cells resolved from their column keys."""

from typing import cast

from rich.text import Text

from squads._api._dto._display import Display
from squads._cli._markup import escape_markup

#: Concrete `rich` colour per colour intent: a total map plus a ``"neutral"`` entry that is also
#: the fallback for an unrecognised intent.
INTENT_COLORS: dict[str, str] = {
    "positive": "green",
    "danger": "red",
    "warning": "yellow",
    "info": "cyan",
    "muted": "bright_black",
    "neutral": "",
}


def intent_style(intent: str) -> str:
    """The `rich` style of a colour intent; an unknown one is uncoloured."""
    return INTENT_COLORS.get(intent, INTENT_COLORS["neutral"])


def status_text(status: str, intent: str) -> Text:
    """*status* coloured by its role's *intent*, applied as a style so no markup is parsed."""
    return Text(status, style=intent_style(intent))


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape_markup(str(value))


def cell_value(row: object, key: str) -> object:
    """The value a column *key* names: the dotted path from *row* through its fields and
    string-keyed maps; ``None`` when a step of the path is missing."""
    value: object = row
    for step in key.split("."):
        if isinstance(value, dict):
            value = cast(dict[str, object], value).get(step)
        else:
            value = getattr(value, step, None)
        if value is None:
            return None
    return value


def cell_text(row: object, key: str) -> str:
    """The escaped text of the cell *key* names; empty when it holds no value."""
    value = cell_value(row, key)
    return "" if value is None or value == "" else e(value)


def lead_badge(display: Display) -> str:
    """The first declared badge field's badge, escaped, as a tree or graph line leads with it
    (``"🟠 high · "``); nothing when the item holds no badge value."""
    first = next(iter(display.badges.values()), None)
    return f"{e(first.badge)} · " if first is not None else ""
