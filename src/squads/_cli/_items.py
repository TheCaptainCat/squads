"""Resource-oriented item commands: ``sq <type> <num> <verb> …`` (sub-entities nest one level).

One Typer group is built per work-item type by :func:`build_item_app`. The group callback resolves
``<num>`` to a full item id (validating the type) into the Click context; each verb reads it back.
feature/task/review additionally get ``add-<kind>`` + a ``<plural>`` list verb + a nested
``<kind> <n> <verb>`` subgroup. Every verb is a thin wrapper over an existing ``svc.*`` method.
"""
# Commands are nested closures registered via Typer decorators (side effect), so they read as
# "unused" to static analysis — disable that one check for this factory module.
# pyright: reportUnusedFunction=false

import json

import typer
from rich.table import Table

from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    parse_severity,
    parse_status,
    print_block,
    print_item,
    print_subentity,
    resolve_body,
    resolve_body_optional,
    resolve_item_id,
    resolve_local_id,
)
from squads._errors import SquadsError
from squads._models._enums import SEVERITY_EMOJI, ItemType
from squads._models._subentity import SubEntity

# Parent type → (sub-entity kind, plural label for the list verb + `list_<plural>` service method).
_SUBENTITY: dict[ItemType, tuple[str, str]] = {
    ItemType.FEATURE: ("story", "stories"),
    ItemType.TASK: ("subtask", "subtasks"),
    ItemType.REVIEW: ("finding", "findings"),
}


def _id(ctx: typer.Context) -> str:
    return ctx.obj["id"]


def _guard_update(*, has_any: bool, assignee: str | None, clear_assignee: bool) -> None:
    """Shared `update` validation: exclusive assignee flags + at least one field given."""
    if assignee and clear_assignee:
        raise SquadsError("use --assignee or --clear-assignee, not both")
    if not has_any:
        raise SquadsError("nothing to update (pass at least one field, e.g. --title/--status)")


def build_item_app(item_type: ItemType) -> typer.Typer:
    """A `sq <type> <num> …` group for one work-item type."""
    item = typer.Typer(no_args_is_help=True, help=f"Operate on a {item_type.value} by number/id.")

    @item.callback()
    @handle_errors
    def _resolve(
        ctx: typer.Context,
        num: str = typer.Argument(..., metavar="N", help=f"{item_type.value} number or id."),
    ):
        ctx.obj = {"id": resolve_item_id(num, item_type)}

    _cmd_show(item)
    _cmd_update(item)
    _cmd_status(item)
    _cmd_body(item)
    _cmd_comment(item)
    _cmd_refs(item)
    if item_type in _SUBENTITY:
        _register_subentity(item, *_SUBENTITY[item_type])
    return item


def _cmd_show(item: typer.Typer) -> None:
    @item.command("show")
    @handle_errors
    def show(ctx: typer.Context, json_out: bool = typer.Option(False, "--json")):
        """Show the item's metadata and body."""
        svc = get_service()
        it = svc.get(_id(ctx))
        if json_out:
            console.print_json(it.model_dump_json())
            return
        print_item(svc, it)


def _cmd_update(item: typer.Typer) -> None:
    @item.command("update")
    @handle_errors
    def update(  # noqa: PLR0913 — the one metadata entry point
        ctx: typer.Context,
        title: str | None = typer.Option(None, "--title"),
        desc: str | None = typer.Option(None, "--desc", help="Short summary (not the body)."),
        author: str | None = typer.Option(None, "--author", help="Authoring agent (role slug)."),
        status: str | None = typer.Option(None, "--status", help="Transition status (validated)."),
        force: bool = typer.Option(False, "--force", help="Force an invalid transition."),
        parent: str | None = typer.Option(None, "--parent", help="Set the parent item ID."),
        no_parent: bool = typer.Option(False, "--no-parent", help="Clear the parent."),
        assignee: str | None = typer.Option(None, "--assignee"),
        add_label: list[str] = typer.Option(None, "--add-label"),
        rm_label: list[str] = typer.Option(None, "--rm-label"),
        set_: list[str] = typer.Option(None, "--set", help="Set a type field: key=value."),
        unset: list[str] = typer.Option(None, "--unset", help="Remove a type field."),
    ):
        """Set the item's metadata — global fields + per-type `--set key=value`."""
        if parent and no_parent:
            raise SquadsError("use either --parent or --no-parent, not both")
        set_extra: dict[str, str] = {}
        for pair in set_ or []:
            key, sep, value = pair.partition("=")
            if not sep:
                raise SquadsError(f"--set expects key=value, got {pair!r}")
            set_extra[key.strip()] = value
        it = get_service().update(
            _id(ctx),
            title=title,
            description=desc,
            assignee=assignee,
            add_labels=add_label or None,
            rm_labels=rm_label or None,
            author=author,
            status=parse_status(status) if status else None,
            force=force,
            parent=parent,
            clear_parent=no_parent,
            set_extra=set_extra or None,
            unset_extra=unset or None,
        )
        console.print(f"updated {it.id}  [dim]{it.path}[/dim]")


def _cmd_status(item: typer.Typer) -> None:
    @item.command("status")
    @handle_errors
    def status(
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS"),
        force: bool = typer.Option(False, "--force"),
    ):
        """Transition the item's status (shortcut for `update --status`)."""
        it = get_service().set_status(_id(ctx), parse_status(new_status), force=force)
        console.print(f"{it.id} → [bold]{it.status.value}[/bold]")


def _cmd_body(item: typer.Typer) -> None:
    @item.command("body")
    @handle_errors
    def body(
        ctx: typer.Context,
        message: list[str] = typer.Option(None, "-m", "--message", help="Body paragraph."),
        file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
        append: bool = typer.Option(False, "--append", help="Append instead of replacing."),
    ):
        """Set (or --append to) the item's body."""
        get_service().set_body(_id(ctx), resolve_body(message or None, file), append=append)
        console.print(f"{_id(ctx)}: body {'appended' if append else 'set'}")


def _cmd_comment(item: typer.Typer) -> None:
    @item.command("comment")
    @handle_errors
    def comment(
        ctx: typer.Context,
        message: list[str] = typer.Option(..., "-m", "--message", help="A talking point."),
        as_: str = typer.Option("operator", "--as", help="Author: a role slug or 'operator'."),
    ):
        """Append a timestamped comment to the item's discussion."""
        get_service().comment(_id(ctx), message, as_slug=as_)
        console.print(f"commented on {_id(ctx)} as {as_}")


def _cmd_refs(item: typer.Typer) -> None:
    @item.command("refs")
    @handle_errors
    def refs(
        ctx: typer.Context,
        out: bool = typer.Option(False, "--out", help="Forward refs (default)."),
        incoming: bool = typer.Option(False, "--in", help="Backrefs (computed)."),
        all_: bool = typer.Option(False, "--all", help="Both directions."),
        json_out: bool = typer.Option(False, "--json"),
    ):
        """Show the item's references (forward stored; backrefs computed)."""
        svc = get_service()
        show_out = out or all_ or not (incoming or all_)
        data: dict[str, list[dict[str, str]]] = {}
        if show_out:
            data["out"] = [{"id": i, "kind": k} for i, k in svc.refs_out(_id(ctx))]
        if incoming or all_:
            data["in"] = [{"id": i, "kind": k} for i, k in svc.refs_in(_id(ctx))]
        if json_out:
            console.print_json(json.dumps(data))
            return
        for direction, label in (("out", "→ refs"), ("in", "← backrefs")):
            if direction not in data:
                continue
            if not data[direction]:
                console.print(f"[dim]{label}: none[/dim]")
                continue
            table = Table(title=label, box=None, pad_edge=False, title_justify="left")
            table.add_column("ID")
            table.add_column("Kind")
            for row in data[direction]:
                table.add_row(row["id"], row["kind"])
            console.print(table)

    ref_app = typer.Typer(no_args_is_help=True, help="Manage forward reference edges.")

    @ref_app.command("add")
    @handle_errors
    def ref_add(
        ctx: typer.Context,
        target: str = typer.Argument(..., help="Target item ID."),
        kind: str = typer.Option(
            "related", "--kind", help="related | blocks | implements | fixes | addresses"
        ),
    ):
        """Add a forward reference to TARGET."""
        get_service().add_ref(_id(ctx), target, kind=kind)
        console.print(f"{_id(ctx)} → {target} ([dim]{kind}[/dim])")

    @ref_app.command("rm")
    @handle_errors
    def ref_rm(ctx: typer.Context, target: str = typer.Argument(..., help="Target item ID.")):
        """Remove a forward reference to TARGET."""
        get_service().rm_ref(_id(ctx), target)
        console.print(f"removed {_id(ctx)} → {target}")

    item.add_typer(ref_app, name="ref")


# --------------------------------------------------------------------------- sub-entities

_SUB_COLS: dict[str, tuple[str, ...]] = {
    "story": ("ID", "Status", "Assignee", "Story"),
    "subtask": ("ID", "Status", "Assignee", "Subtask", "Story"),
    "finding": ("ID", "Severity", "Status", "Assignee", "Finding"),
}


def _sub_table(kind: str, blocks: list[SubEntity]) -> None:
    if not blocks:
        console.print(f"[dim]no {kind}s[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in _SUB_COLS[kind]:
        table.add_column(col)
    for b in blocks:
        if kind == "finding":
            sev = f"{SEVERITY_EMOJI[b.severity]} {b.severity.value}" if b.severity else ""
            table.add_row(b.local_id, sev, b.status.value, b.assignee or "", e(b.title))
        elif kind == "subtask":
            table.add_row(b.local_id, b.status.value, b.assignee or "", e(b.title), b.story or "")
        else:
            table.add_row(b.local_id, b.status.value, b.assignee or "", e(b.title))
    console.print(table)


def _register_subentity(item: typer.Typer, kind: str, plural: str) -> None:
    @item.command(plural)
    @handle_errors
    def list_sub(ctx: typer.Context):
        """List this item's sub-entities."""
        blocks = getattr(get_service(), f"list_{plural}")(_id(ctx))
        _sub_table(kind, blocks)

    _register_add(item, kind)

    sub = typer.Typer(no_args_is_help=True, help=f"Operate on a {kind} by number/local id.")

    @sub.callback()
    @handle_errors
    def _resolve_sub(
        ctx: typer.Context,
        n: str = typer.Argument(..., metavar="N", help=f"{kind} number or local id (e.g. 2)."),
    ):
        assert ctx.parent is not None  # the parent item group always runs first
        ctx.obj = {**ctx.parent.obj, "local": resolve_local_id(n, kind)}

    _register_sub_verbs(sub, kind)
    item.add_typer(sub, name=kind)


def _register_add(item: typer.Typer, kind: str) -> None:
    if kind == "story":

        @item.command("add-story")
        @handle_errors
        def add_story(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional short label; set the story in body."),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a user story on this feature."""
            res = get_service().add_story(
                _id(ctx),
                title,
                assignee=assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)

    elif kind == "subtask":

        @item.command("add-subtask")
        @handle_errors
        def add_subtask(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional checklist label; detail in body."),
            story: str | None = typer.Option(
                None, "--story", help="User story it implements (USn)."
            ),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a subtask on this task."""
            res = get_service().add_subtask(
                _id(ctx),
                title,
                story=story,
                assignee=assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)

    else:  # finding

        @item.command("add-finding")
        @handle_errors
        def add_finding(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional short label; detail in body."),
            severity: str = typer.Option(
                "medium", "--severity", help="critical|high|medium|low|info."
            ),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a finding on this review."""
            res = get_service().add_finding(
                _id(ctx),
                title,
                severity=parse_severity(severity),
                assignee=assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)


def _register_update(sub: typer.Typer, kind: str) -> None:
    """The sub-entity metadata entry point — kind-aware flags, like `_register_add`."""

    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    if kind == "subtask":

        @sub.command("update")
        @handle_errors
        def u_subtask(
            ctx: typer.Context,
            title: str | None = typer.Option(None, "--title"),
            story: str | None = typer.Option(None, "--story", help="Remap to a user story (USn)."),
            no_story: bool = typer.Option(False, "--no-story", help="Clear the story mapping."),
            assignee: str | None = typer.Option(None, "--assignee"),
            clear_assignee: bool = typer.Option(False, "--clear-assignee"),
            status: str | None = typer.Option(None, "--status"),
            force: bool = typer.Option(False, "--force"),
        ):
            """Update the subtask's metadata (title / story / assignee / status)."""
            pid, lid = ids(ctx)
            if story and no_story:
                raise SquadsError("use --story or --no-story, not both")
            _guard_update(
                has_any=any((title, story, no_story, assignee, clear_assignee, status)),
                assignee=assignee,
                clear_assignee=clear_assignee,
            )
            get_service().update_subtask(
                pid,
                lid,
                title=title,
                story=story,
                clear_story=no_story,
                assignee=assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")

    elif kind == "finding":

        @sub.command("update")
        @handle_errors
        def u_finding(
            ctx: typer.Context,
            title: str | None = typer.Option(None, "--title"),
            severity: str | None = typer.Option(
                None, "--severity", help="critical|high|medium|low|info."
            ),
            assignee: str | None = typer.Option(None, "--assignee"),
            clear_assignee: bool = typer.Option(False, "--clear-assignee"),
            status: str | None = typer.Option(None, "--status"),
            force: bool = typer.Option(False, "--force"),
        ):
            """Update the finding's metadata (title / severity / assignee / status)."""
            pid, lid = ids(ctx)
            _guard_update(
                has_any=any((title, severity, assignee, clear_assignee, status)),
                assignee=assignee,
                clear_assignee=clear_assignee,
            )
            get_service().update_finding(
                pid,
                lid,
                title=title,
                severity=parse_severity(severity) if severity else None,
                assignee=assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")

    else:  # story

        @sub.command("update")
        @handle_errors
        def u_story(
            ctx: typer.Context,
            title: str | None = typer.Option(None, "--title"),
            assignee: str | None = typer.Option(None, "--assignee"),
            clear_assignee: bool = typer.Option(False, "--clear-assignee"),
            status: str | None = typer.Option(None, "--status"),
            force: bool = typer.Option(False, "--force"),
        ):
            """Update the story's metadata (title / assignee / status)."""
            pid, lid = ids(ctx)
            _guard_update(
                has_any=any((title, assignee, clear_assignee, status)),
                assignee=assignee,
                clear_assignee=clear_assignee,
            )
            get_service().update_story(
                pid,
                lid,
                title=title,
                assignee=assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")


def _register_sub_verbs(sub: typer.Typer, kind: str) -> None:
    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    @sub.command("show")
    @handle_errors
    def s_show(ctx: typer.Context):
        """Show the sub-entity's status/assignee, body, and discussion."""
        pid, lid = ids(ctx)
        print_subentity(getattr(get_service(), f"get_{kind}")(pid, lid), kind)

    _register_update(sub, kind)

    @sub.command("body")
    @handle_errors
    def s_body(
        ctx: typer.Context,
        message: list[str] = typer.Option(None, "-m", "--message"),
        file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
        append: bool = typer.Option(False, "--append"),
    ):
        """Set (or --append to) the sub-entity's body."""
        pid, lid = ids(ctx)
        getattr(get_service(), f"set_{kind}_body")(
            pid, lid, resolve_body(message or None, file), append=append
        )
        console.print(f"{pid} {lid}: body {'appended' if append else 'set'}")

    @sub.command("comment")
    @handle_errors
    def s_comment(
        ctx: typer.Context,
        message: list[str] = typer.Option(..., "-m", "--message"),
        as_: str = typer.Option("operator", "--as"),
    ):
        """Comment on the sub-entity's discussion."""
        pid, lid = ids(ctx)
        get_service().comment(pid, message, as_slug=as_, **{kind: lid})
        console.print(f"commented on {pid} {lid} as {as_}")
