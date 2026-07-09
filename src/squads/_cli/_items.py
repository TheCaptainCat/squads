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

import squads._cli._common as common
from squads import _actor as actor
from squads import _discussion as discussion
from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    parse_badge_code,
    parse_status,
    parse_type,
    print_block,
    print_item,
    print_json_clean,
    print_subentity,
    resolve_body,
    resolve_body_optional,
    resolve_item_id_any,
    resolve_item_id_typed,
    resolve_local_id,
    resolve_slug_or_raise,
)
from squads._errors import SquadsError
from squads._models._item import DEFAULT_KIND, split_ref
from squads._models._subentity import SubEntity

#: The bundled default's finding severity field's bound collection code — resolved fresh at
#: each call site via ``get_active_spec()`` (this constant is only the *fallback* used by
#: :func:`squads._discussion.resolve_collection` when a live field can't be found).
_SEVERITY_FIELD_CODE = "severity"


def _severity_collection() -> str:
    """The collection the ``finding`` kind's ``severity`` field is bound to (spec-derived)."""
    return discussion.resolve_collection("finding", _SEVERITY_FIELD_CODE, common.get_active_spec())


# Built-in sub-entity map (keyed by string so custom-type strings compare cleanly).
# Custom types that declare a subentity_kind in the spec are handled via
# ``get_active_spec().item_subentity_kind(item_type)`` at build time.
_SUBENTITY_PLURAL: dict[str, tuple[str, str]] = {
    "feature": ("story", "stories"),
    "task": ("subtask", "subtasks"),
    "review": ("finding", "findings"),
}


def _id(ctx: typer.Context) -> str:
    return ctx.obj["id"]


def _guard_update(*, has_any: bool, assignee: str | None, clear_assignee: bool) -> None:
    """Shared `update` validation: exclusive assignee flags + at least one field given."""
    if assignee and clear_assignee:
        raise SquadsError("use --assignee or --clear-assignee, not both")
    if not has_any:
        raise SquadsError("nothing to update (pass at least one field, e.g. --title/--status)")


def build_item_app(item_type: str) -> typer.Typer:
    """A ``sq <type> <num> …`` group for one work-item type.

    Accepts a plain string type name (``"task"``, ``"incident"`` …) — every type, built-in
    or custom, is ordinary spec vocabulary.

    Capability flags (subentity kind, retype/remove eligibility) are resolved from
    ``get_active_spec()`` at call time so a custom type's spec-declared capabilities are
    honoured without any enum membership requirement.
    """
    item = typer.Typer(no_args_is_help=True, help=f"Operate on a {item_type} by number/id.")

    @item.callback()
    @common.command
    async def _resolve(
        ctx: typer.Context,
        num: str = typer.Argument(..., metavar="N", help=f"{item_type} number or id."),
    ):
        svc = get_service()
        ctx.obj = {"id": await resolve_item_id_typed(num, item_type, svc)}

    _cmd_show(item)
    _cmd_update(item)
    _cmd_status(item)
    _cmd_body(item)
    _cmd_comment(item)
    _cmd_refs(item)
    # Sub-entity kind: check spec first (covers custom types), then fall back to built-in map.
    spec = common.get_active_spec()
    subentity_kind = spec.item_subentity_kind(item_type) if item_type in spec.items else None
    if subentity_kind is None:
        # Fallback for pre-callback build (bundled spec may not have loaded yet for the app
        # tree; the built-in map is always accurate for built-in types).
        sub_info = _SUBENTITY_PLURAL.get(item_type)
    else:
        # Spec-declared subentity kind → look up the plural from the built-in map (custom
        # types would need to declare their own plural, but none do yet).
        sub_info = _SUBENTITY_PLURAL.get(subentity_kind) or _SUBENTITY_PLURAL.get(item_type)
    if sub_info is not None:
        _register_subentity(item, *sub_info)
    # retype/remove: available for all non-meta work types (spec-derived).
    # For types unknown to the spec (pre-callback edge case), fall back to checking
    # against the three meta-type names directly (the irreducible,
    # by-name-bound minimum, not a spec lookup).
    from squads._workflow import META_TYPES

    is_meta = spec.item_is_meta(item_type) if item_type in spec.items else item_type in META_TYPES
    if not is_meta:
        _cmd_retype(item)
        _cmd_remove(item)
    return item


def _cmd_show(item: typer.Typer) -> None:
    @item.command("show")
    @common.command
    async def show(
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json"),
        raw: bool = typer.Option(
            False, "--raw", help="Plain text output (opt out of markdown render)."
        ),
        comments: bool = typer.Option(
            False, "--comments", help="Append the discussion as comment panes."
        ),
        full: bool = typer.Option(
            False, "--full", help="Add one pane per sub-entity (body + badges)."
        ),
    ):
        """Show the item's metadata, body, sub-entity summary, and optional panes."""
        svc = get_service()
        it = await svc.get(_id(ctx))
        if json_out:
            print_json_clean(it.model_dump_json())
            return
        await print_item(svc, it, raw=raw, comments=comments, full=full)


def _cmd_update(item: typer.Typer) -> None:
    @item.command("update")
    @common.command
    async def update(  # noqa: PLR0913 — the one metadata entry point
        ctx: typer.Context,
        title: str | None = typer.Option(None, "--title"),
        desc: str | None = typer.Option(None, "--desc", help="Short summary (not the body)."),
        author: str | None = typer.Option(None, "--author", help="Authoring agent (role slug)."),
        status: str | None = typer.Option(None, "--status", help="Transition status (validated)."),
        force: bool = typer.Option(False, "--force", help="Force an invalid transition."),
        parent: str | None = typer.Option(None, "--parent", help="Set the parent item ID."),
        no_parent: bool = typer.Option(False, "--no-parent", help="Clear the parent."),
        assignee: str | None = typer.Option(None, "--assignee"),
        priority: str | None = typer.Option(
            None, "--priority", help="Priority: urgent|high|medium|low."
        ),
        no_priority: bool = typer.Option(False, "--no-priority", help="Clear the priority."),
        add_label: list[str] = typer.Option(None, "--add-label"),
        rm_label: list[str] = typer.Option(None, "--rm-label"),
        set_: list[str] = typer.Option(None, "--set", help="Set a type field: key=value."),
        unset: list[str] = typer.Option(None, "--unset", help="Remove a type field."),
    ):
        """Set the item's metadata — global fields + per-type `--set key=value`."""
        if parent and no_parent:
            raise SquadsError("use either --parent or --no-parent, not both")
        if priority and no_priority:
            raise SquadsError("use either --priority or --no-priority, not both")
        set_extra: dict[str, str] = {}
        for pair in set_ or []:
            key, sep, value = pair.partition("=")
            if not sep:
                raise SquadsError(f"--set expects key=value, got {pair!r}")
            set_extra[key.strip()] = value
        svc = get_service()
        validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
        validated_author = await resolve_slug_or_raise(author, svc) if author else None
        resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
        it = await svc.update(
            _id(ctx),
            title=title,
            description=desc,
            assignee=validated_assignee,
            priority=parse_badge_code("priority", priority) if priority else None,
            clear_priority=no_priority,
            add_labels=add_label or None,
            rm_labels=rm_label or None,
            author=validated_author,
            status=parse_status(status) if status else None,
            force=force,
            parent=resolved_parent,
            clear_parent=no_parent,
            set_extra=set_extra or None,
            unset_extra=unset or None,
        )
        console.print(f"updated {it.id}  [dim]{it.path}[/dim]")


def _cmd_status(item: typer.Typer) -> None:
    @item.command("status")
    @common.command
    async def status(
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS"),
        force: bool = typer.Option(False, "--force"),
    ):
        """Transition the item's status (shortcut for `update --status`)."""
        it = await get_service().set_status(_id(ctx), parse_status(new_status), force=force)
        console.print(f"{it.id} → [bold]{it.status}[/bold]")


def _cmd_body(item: typer.Typer) -> None:
    @item.command("body")
    @common.command
    async def body(
        ctx: typer.Context,
        message: list[str] = typer.Option(None, "-m", "--message", help="Body paragraph."),
        file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
        append: bool = typer.Option(False, "--append", help="Append instead of replacing."),
    ):
        """Set (or --append to) the item's body."""
        await get_service().set_body(_id(ctx), resolve_body(message or None, file), append=append)
        console.print(f"{_id(ctx)}: body {'appended' if append else 'set'}")


def _cmd_comment(item: typer.Typer) -> None:
    @item.command("comment")
    @common.command
    async def comment(
        ctx: typer.Context,
        message: list[str] = typer.Option(..., "-m", "--message", help="A talking point."),
        as_: str = typer.Option("operator", "--as", help="Author: a role slug or 'operator'."),
    ):
        """Append a timestamped comment to the item's discussion."""
        svc = get_service()
        slug = await resolve_slug_or_raise(as_, svc)
        actor.set_actor(slug)
        await svc.comment(_id(ctx), message, as_slug=slug)
        console.print(f"commented on {_id(ctx)} as {slug}")


def _cmd_retype(item: typer.Typer) -> None:
    @item.command("retype")
    @common.command
    async def retype(
        ctx: typer.Context,
        new_type: str = typer.Argument(
            ...,
            metavar="NEW-TYPE",
            help=(
                "Target work-item type: epic|feature|task|bug|decision|review|guide. "
                "The item number is preserved; only the ID prefix flips."
            ),
        ),
    ):
        """Reclassify this item to a different type, keeping its number and body.

        The sequence number (and therefore the durable identity) is preserved — only the
        ID prefix changes (e.g. TASK-nnn → BUG-nnn). All incoming references, children's
        parent links, and prose mentions are rewritten to the new ID.
        """
        target = parse_type(new_type)
        wt = common.get_active_spec().work_types()
        if target not in wt:
            work = ", ".join(sorted(wt))
            raise SquadsError(f"cannot retype to {new_type!r}; valid targets: {work}")
        svc = get_service()
        res = await svc.retype(_id(ctx), target)
        console.print(
            f"retyped {e(res.old_id)} → [bold]{e(res.item.id)}[/bold]  [dim]{res.item.path}[/dim]"
        )
        if res.status_reset:
            console.print(
                f"  status reset: {e(res.old_status)} → [yellow]{e(res.item.status)}[/yellow]"
                f" (workflows differ)"
            )
        else:
            console.print(f"  status carried: [bold]{e(res.item.status)}[/bold]")
        if res.rewritten:
            console.print(f"  rewritten refs in {len(res.rewritten)} file(s)")


def _cmd_remove(item: typer.Typer) -> None:
    @item.command("remove")
    @common.command
    async def remove(
        ctx: typer.Context,
        force: bool = typer.Option(
            False,
            "--force",
            help="Sever incoming refs from referrers' frontmatter instead of refusing.",
        ),
        yes: bool = typer.Option(
            False,
            "--yes",
            help="Skip the interactive confirmation prompt.",
        ),
        json_out: bool = typer.Option(False, "--json"),
    ):
        """Hard-delete this item: remove its .md file and index entry atomically.

        Refuses when the item has children (must be re-parented or removed first) or incoming
        refs (list them and exit, unless --force severs them).  The counter high-water mark is
        preserved — the freed sequence number is never reissued.

        Use `sq <type> <n> status Cancelled` to drop work that was genuinely considered; use
        `remove` only for items that should never have existed (mis-creations, test artifacts).
        """
        item_id = _id(ctx)
        if not yes:
            typer.confirm(f"Remove {item_id}? This cannot be undone.", abort=True)
        svc = get_service()
        res = await svc.remove_work_item(item_id, force=force)
        if json_out:
            import json as _json

            print_json_clean(
                _json.dumps(
                    {
                        "removed_id": res.removed_id,
                        "severed_refs": res.severed_refs,
                    }
                )
            )
            return
        console.print(f"removed {e(res.removed_id)}")
        if res.severed_refs:
            console.print(f"  severed refs in: {', '.join(e(r) for r in res.severed_refs)}")


def _cmd_refs(item: typer.Typer) -> None:
    @item.command("refs")
    @common.command
    async def refs(
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
            data["out"] = [{"id": i, "kind": k} for i, k in await svc.refs_out(_id(ctx))]
        if incoming or all_:
            data["in"] = [{"id": i, "kind": k} for i, k in await svc.refs_in(_id(ctx))]
        if json_out:
            print_json_clean(json.dumps(data))
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
    @common.command
    async def ref_add(
        ctx: typer.Context,
        target: str = typer.Argument(..., help="Target item ID."),
        kind: str = typer.Option(
            "related",
            "--kind",
            help=(
                "Edge kind: related|blocks|depends-on|implements|fixes|addresses|"
                "supersedes|duplicates. Run `sq workflow` for the canonical kinds table "
                "(meaning, direction, and which commands consume each kind)."
            ),
        ),
    ):
        """Add a forward reference to TARGET."""
        svc = get_service()
        # target may be a bare number, full ID, or ID:kind — resolve the ID part only
        raw_id, embedded_kind = split_ref(target)
        resolved_id = await resolve_item_id_any(raw_id, svc)
        effective_kind = embedded_kind if embedded_kind != DEFAULT_KIND else kind
        await svc.add_ref(_id(ctx), resolved_id, kind=effective_kind)
        console.print(f"{_id(ctx)} → {resolved_id} ([dim]{effective_kind}[/dim])")

    @ref_app.command("rm")
    @common.command
    async def ref_rm(ctx: typer.Context, target: str = typer.Argument(..., help="Target item ID.")):
        """Remove a forward reference to TARGET."""
        svc = get_service()
        raw_id, _ = split_ref(target)
        resolved_id = await resolve_item_id_any(raw_id, svc)
        await svc.rm_ref(_id(ctx), resolved_id)
        console.print(f"removed {_id(ctx)} → {resolved_id}")

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
            sev = discussion.badge_render(_severity_collection(), b.severity) if b.severity else ""
            table.add_row(b.local_id, sev, b.status, b.assignee or "", e(b.title))
        elif kind == "subtask":
            table.add_row(b.local_id, b.status, b.assignee or "", e(b.title), b.story or "")
        else:
            table.add_row(b.local_id, b.status, b.assignee or "", e(b.title))
    console.print(table)


def _register_subentity(item: typer.Typer, kind: str, plural: str) -> None:
    @item.command(plural)
    @common.command
    async def list_sub(ctx: typer.Context, json_out: bool = typer.Option(False, "--json")):
        """List this item's sub-entities."""
        blocks = await getattr(get_service(), f"list_{plural}")(_id(ctx))
        if json_out:
            print_json_clean(
                json.dumps(
                    [
                        {
                            "local_id": b.local_id,
                            "title": b.title,
                            "status": b.status,
                            "assignee": b.assignee,
                            "severity": b.severity,
                            "story": b.story,
                        }
                        for b in blocks
                    ]
                )
            )
            return
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
        @common.command
        async def add_story(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional short label; set the story in body."),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a user story on this feature."""
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            res = await svc.add_story(
                _id(ctx),
                title,
                assignee=validated_assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)

    elif kind == "subtask":

        @item.command("add-subtask")
        @common.command
        async def add_subtask(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional checklist label; detail in body."),
            story: str | None = typer.Option(
                None, "--story", help="User story it implements (USn or bare 1)."
            ),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a subtask on this task."""
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            normalized_story = resolve_local_id(story, "story") if story else None
            res = await svc.add_subtask(
                _id(ctx),
                title,
                story=normalized_story,
                assignee=validated_assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)

    else:  # finding

        @item.command("add-finding")
        @common.command
        async def add_finding(
            ctx: typer.Context,
            title: str = typer.Argument("", help="Optional short label; detail in body."),
            severity: str | None = typer.Option(
                None,
                "--severity",
                help="critical|high|medium|low|info (defaults to the spec's severity default).",
            ),
            assignee: str | None = typer.Option(None, "--assignee"),
            message: list[str] = typer.Option(None, "-m", "--message"),
            file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            json_out: bool = typer.Option(False, "--json"),
        ):
            """Scaffold a finding on this review."""
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            res = await svc.add_finding(
                _id(ctx),
                title,
                severity=parse_badge_code(_severity_collection(), severity) if severity else None,
                assignee=validated_assignee,
                body=resolve_body_optional(message or None, file),
            )
            print_block(_id(ctx), res, json_out)


def _register_update(sub: typer.Typer, kind: str) -> None:
    """The sub-entity metadata entry point — kind-aware flags, like `_register_add`."""

    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    if kind == "subtask":

        @sub.command("update")
        @common.command
        async def u_subtask(
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
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            normalized_story = resolve_local_id(story, "story") if story else None
            await svc.update_subtask(
                pid,
                lid,
                title=title,
                story=normalized_story,
                clear_story=no_story,
                assignee=validated_assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")

    elif kind == "finding":

        @sub.command("update")
        @common.command
        async def u_finding(
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
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            await svc.update_finding(
                pid,
                lid,
                title=title,
                severity=parse_badge_code(_severity_collection(), severity) if severity else None,
                assignee=validated_assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")

    else:  # story

        @sub.command("update")
        @common.command
        async def u_story(
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
            svc = get_service()
            validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
            await svc.update_story(
                pid,
                lid,
                title=title,
                assignee=validated_assignee,
                clear_assignee=clear_assignee,
                status=parse_status(status) if status else None,
                force=force,
            )
            console.print(f"updated {pid} {lid}")


def _register_sub_verbs(sub: typer.Typer, kind: str) -> None:
    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    @sub.command("show")
    @common.command
    async def s_show(ctx: typer.Context):
        """Show the sub-entity's status/assignee, body, and discussion."""
        pid, lid = ids(ctx)
        print_subentity(await getattr(get_service(), f"get_{kind}")(pid, lid), kind)

    _register_update(sub, kind)

    @sub.command("body")
    @common.command
    async def s_body(
        ctx: typer.Context,
        message: list[str] = typer.Option(None, "-m", "--message"),
        file: str | None = typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
        append: bool = typer.Option(False, "--append"),
    ):
        """Set (or --append to) the sub-entity's body."""
        pid, lid = ids(ctx)
        await getattr(get_service(), f"set_{kind}_body")(
            pid, lid, resolve_body(message or None, file), append=append
        )
        console.print(f"{pid} {lid}: body {'appended' if append else 'set'}")

    @sub.command("comment")
    @common.command
    async def s_comment(
        ctx: typer.Context,
        message: list[str] = typer.Option(..., "-m", "--message"),
        as_: str = typer.Option("operator", "--as"),
    ):
        """Comment on the sub-entity's discussion."""
        pid, lid = ids(ctx)
        svc = get_service()
        slug = await resolve_slug_or_raise(as_, svc)
        actor.set_actor(slug)
        await svc.comment(pid, message, as_slug=slug, **{kind: lid})
        console.print(f"commented on {pid} {lid} as {slug}")
