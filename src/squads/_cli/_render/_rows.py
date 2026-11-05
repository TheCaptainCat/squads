"""The rows of a show's metadata: one list per show, printed by the styled panel and by `--raw`."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    """One metadata row: a *label* (``None`` for the unlabelled first row), its *plain* value and
    the *markup* the panel prints for it. ``panel`` and ``raw`` say which forms carry the row."""

    label: str | None
    plain: str
    markup: str
    panel: bool = True
    raw: bool = True


def panel_text(rows: list[Row]) -> str:
    """The panel's lines for *rows*, with each label in bold."""
    return "\n".join(
        row.markup if row.label is None else f"[bold]{row.label}:[/bold] {row.markup}"
        for row in rows
        if row.panel
    )


def raw_lines(rows: list[Row]) -> list[str]:
    """The markdown list `--raw` prints for *rows*: ``- **label:** value``, a plain bullet when
    the row has no label."""
    return [
        f"- {row.plain}" if row.label is None else f"- **{row.label}:** {row.plain}"
        for row in rows
        if row.raw
    ]
