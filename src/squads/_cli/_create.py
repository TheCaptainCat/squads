"""`sq create <type> TITLE …` — one command per item type, sharing one implementation."""

import typer

from squads._cli._common import console, get_service, handle_errors, resolve_body_optional
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X

create_app = typer.Typer(no_args_is_help=True, help="Create a tracked item.")

# Generic creatable types. `guide` is created here too but with extra --tech/--tag options;
# roles/skills/devs have their own commands (they generate artifacts).
_CREATABLE = (
    ItemType.EPIC,
    ItemType.FEATURE,
    ItemType.TASK,
    ItemType.BUG,
    ItemType.DECISION,
    ItemType.REVIEW,
)


def _make(item_type: ItemType):
    @handle_errors
    def cmd(  # noqa: PLR0913 — Typer options are the command's surface
        title: str = typer.Argument(..., help="Item title."),
        author: str = typer.Option(
            ..., "--author", help="Authoring agent (role slug); must be registered."
        ),
        parent: str | None = typer.Option(None, "--parent", help="Parent item ID."),
        desc: str = typer.Option(
            "", "--desc", help="Short summary (shown in lists; not the body)."
        ),
        label: list[str] = typer.Option(None, "--label", help="Label (repeatable)."),
        ref: list[str] = typer.Option(
            None, "--ref", help="Forward-ref to another ID (repeatable)."
        ),
        assignee: str | None = typer.Option(None, "--assignee", help="Role slug or ID."),
        message: list[str] = typer.Option(
            None, "-m", "--message", help="Body paragraph; repeat for several (or use --file)."
        ),
        file: str | None = typer.Option(
            None, "--file", help="Read the body from a file ('-' = stdin)."
        ),
        json_out: bool = typer.Option(False, "--json"),
    ):
        svc = get_service()
        res = svc.create(
            item_type,
            title,
            description=desc,
            parent=parent,
            author=author,
            labels=label or None,
            refs=ref or None,
            assignee=assignee,
            body=resolve_body_optional(message or None, file),
        )
        if json_out:
            console.print_json(res.item.model_dump_json())
        else:
            console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")

    cmd.__name__ = f"create_{item_type.value}"
    return cmd


for _t in _CREATABLE:
    create_app.command(_t.value, help=f"Create a {_t.value}.")(_make(_t))


@create_app.command("guide", help="Create a guide.")
@handle_errors
def create_guide(  # noqa: PLR0913 — Typer options are the command's surface
    title: str = typer.Argument(..., help="Guide title."),
    author: str = typer.Option(..., "--author", help="Authoring agent (role slug)."),
    tech: str | None = typer.Option(None, "--tech", help="Technology (e.g. python, react)."),
    tag: list[str] = typer.Option(None, "--tag", help="Tag (repeatable)."),
    parent: str | None = typer.Option(None, "--parent", help="Parent item ID."),
    desc: str = typer.Option("", "--desc", help="Short summary (shown in lists; not the body)."),
    assignee: str | None = typer.Option(None, "--assignee", help="Role slug or ID."),
    message: list[str] = typer.Option(
        None, "-m", "--message", help="Body paragraph; repeat for several (or use --file)."
    ),
    file: str | None = typer.Option(
        None, "--file", help="Read the body from a file ('-' = stdin)."
    ),
    json_out: bool = typer.Option(False, "--json"),
):
    extra: dict[str, object] = {}
    if tech:
        extra[X.TECH] = tech
    if tag:
        extra[X.TAGS] = list(tag)
    res = get_service().create(
        ItemType.GUIDE,
        title,
        description=desc,
        parent=parent,
        author=author,
        assignee=assignee,
        extra=extra or None,
        body=resolve_body_optional(message or None, file),
    )
    if json_out:
        console.print_json(res.item.model_dump_json())
    else:
        console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
