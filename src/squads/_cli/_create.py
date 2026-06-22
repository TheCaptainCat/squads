"""`sq create <type> TITLE …` — one command per item type, sharing one implementation."""

import json

import typer

import squads._cli._common as common
from squads import _actor as actor
from squads._cli._common import (
    console,
    e,
    get_service,
    parse_priority,
    resolve_body_optional,
    resolve_item_id_any,
)
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._item import make_ref, split_ref

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
    @common.command
    async def cmd(  # noqa: PLR0913 — Typer options are the command's surface
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
        priority: str | None = typer.Option(
            None, "--priority", help="Priority: urgent|high|medium|low."
        ),
        message: list[str] = typer.Option(
            None, "-m", "--message", help="Body paragraph; repeat for several (or use --file)."
        ),
        file: str | None = typer.Option(
            None, "--file", help="Read the body from a file ('-' = stdin)."
        ),
        json_out: bool = typer.Option(False, "--json"),
    ):
        svc = get_service()
        actor.set_actor(author)
        resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
        resolved_refs: list[str] | None = None
        if ref:
            resolved_refs = []
            for r in ref:
                rid, kind = split_ref(r)
                resolved_refs.append(make_ref(await resolve_item_id_any(rid, svc), kind))
        res = await svc.create(
            item_type,
            title,
            description=desc,
            parent=resolved_parent,
            author=author,
            labels=label or None,
            refs=resolved_refs,
            assignee=assignee,
            priority=parse_priority(priority) if priority else None,
            body=resolve_body_optional(message or None, file),
        )
        if json_out:
            data = json.loads(res.item.model_dump_json())
            if res.lane_warning is not None:
                data["lane_warning"] = res.lane_warning
            console.print_json(json.dumps(data))
        else:
            console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
            if res.lane_warning is not None:
                console.print(e(res.lane_warning))

    cmd.__name__ = f"create_{item_type.value}"
    return cmd


for _t in _CREATABLE:
    create_app.command(_t.value, help=f"Create a {_t.value}.")(_make(_t))


@create_app.command("guide", help="Create a guide.")
@common.command
async def create_guide(  # noqa: PLR0913 — Typer options are the command's surface
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
    svc = get_service()
    actor.set_actor(author)
    resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
    res = await svc.create(
        ItemType.GUIDE,
        title,
        description=desc,
        parent=resolved_parent,
        author=author,
        assignee=assignee,
        extra=extra or None,
        body=resolve_body_optional(message or None, file),
    )
    if json_out:
        data = json.loads(res.item.model_dump_json())
        if res.lane_warning is not None:
            data["lane_warning"] = res.lane_warning
        console.print_json(json.dumps(data))
    else:
        console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
        if res.lane_warning is not None:
            console.print(e(res.lane_warning))
