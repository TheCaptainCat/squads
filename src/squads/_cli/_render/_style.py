"""Presentation shared by the renderers: colours for a status's intent, and markup escaping."""

from rich.text import Text

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
