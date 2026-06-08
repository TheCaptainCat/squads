"""`sq create <type> TITLE …` — one command per item type, sharing one implementation."""

import typer

from squads.cli.common import console, get_service, handle_errors
from squads.models import ItemType

create_app = typer.Typer(no_args_is_help=True, help="Create a tracked item.")

# Types creatable via `sq create`. Roles/skills have their own commands (they generate artifacts).
_CREATABLE = (
    ItemType.EPIC,
    ItemType.FEATURE,
    ItemType.TASK,
    ItemType.BUG,
    ItemType.DECISION,
    ItemType.REVIEW,
    ItemType.GUIDE,
)


def _make(item_type: ItemType):
    @handle_errors
    def cmd(
        title: str = typer.Argument(..., help="Item title."),
        parent: str | None = typer.Option(None, "--parent", help="Parent item ID."),
        desc: str = typer.Option("", "--desc", help="Short description (seeds the body)."),
        label: list[str] = typer.Option(None, "--label", help="Label (repeatable)."),
        ref: list[str] = typer.Option(
            None, "--ref", help="Forward-ref to another ID (repeatable)."
        ),
        assignee: str | None = typer.Option(None, "--assignee", help="Role slug or ID."),
        json_out: bool = typer.Option(False, "--json"),
    ):
        svc = get_service()
        res = svc.create(
            item_type,
            title,
            description=desc,
            parent=parent,
            labels=label or None,
            refs=ref or None,
            assignee=assignee,
        )
        if json_out:
            console.print_json(res.item.model_dump_json())
        else:
            console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")

    cmd.__name__ = f"create_{item_type.value}"
    return cmd


for _t in _CREATABLE:
    create_app.command(_t.value, help=f"Create a {_t.value}.")(_make(_t))
