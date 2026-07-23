"""Resource-oriented item commands: ``sq <type> <num> <verb> …`` (sub-entities nest one level).

One Typer group is built per work-item type by :func:`build_item_app`. The group callback resolves
``<num>`` to a full item id (validating the type) into the Click context; each verb reads it back.
A type that declares a sub-entity kind (spec-resolved, built-in or custom) additionally gets
``add-<kind>`` + a ``<plural>`` list verb + a nested ``<kind> <n> <verb>`` subgroup, all built
generically from the resolved ``SubentityKindSpec`` (see :func:`_register_subentity`) — no
per-kind closures. Every verb is a thin wrapper over an existing ``svc.*`` method.
"""
# Commands are nested closures registered via Typer decorators (side effect), so they read as
# "unused" to static analysis — disable that one check for this factory module.
# pyright: reportUnusedFunction=false

import inspect
import json
from typing import cast

import typer
from rich.table import Table

import squads._cli._common as common
from squads import _actor as actor
from squads import _badges as badges
from squads import _discussion as discussion
from squads._cli._common import (
    build_item_json,
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
from squads._services._service import Service
from squads._workflow._models import Field, WorkflowSpec


def _id(ctx: typer.Context) -> str:
    return ctx.obj["id"]


def _kw_str(kwargs: dict[str, object], key: str) -> str | None:
    value = kwargs.get(key)
    return value if isinstance(value, str) else None


def _kw_bool(kwargs: dict[str, object], key: str) -> bool:
    return bool(kwargs.get(key))


def _kw_list(kwargs: dict[str, object], key: str) -> list[str] | None:
    value = kwargs.get(key)
    return cast(list[str], value) if isinstance(value, list) else None


def _guard_update(*, has_any: bool, assignee: str | None, clear_assignee: bool) -> None:
    """Shared `update` validation: exclusive assignee flags + at least one field given."""
    if assignee and clear_assignee:
        raise SquadsError("use --assignee or --clear-assignee, not both")
    if not has_any:
        raise SquadsError("nothing to update (pass at least one field, e.g. --title/--status)")


def _priority_help(item_type: str, spec: WorkflowSpec, template: str) -> str:
    """``--priority``/``--min-priority`` help text, derived from the priority collection
    bound to *item_type* — falls back to a spec-pointing phrase (no enumeration) when the
    type doesn't declare a priority field/collection at all."""
    coll_code = badges.resolve_collection(item_type, "priority", spec)
    coll = spec.collections.get(coll_code)
    if coll and coll.badges:
        return template.format(codes="|".join(b.code for b in coll.badges))
    return "Priority code (as defined by your workflow's priority collection)."


def build_item_app(item_type: str, spec: WorkflowSpec | None = None) -> typer.Typer:
    """A ``sq <type> <num> …`` group for one work-item type.

    Accepts a plain string type name (``"task"``, ``"incident"`` …) — every type, built-in
    or custom, is ordinary spec vocabulary.

    Capability flags (subentity kind, retype/remove eligibility) are resolved from *spec*
    (defaulting to ``get_active_spec()`` at call time) so a custom type's spec-declared
    capabilities are honoured without any enum membership requirement. Callers that have
    already resolved the ctx-appropriate spec (e.g. the root group's lazy custom-type
    dispatch, which must build from the *same* spec it used to decide the type exists —
    not whatever ``get_active_spec()`` happens to hold before the root callback binds it)
    should pass it explicitly.
    """
    item = typer.Typer(no_args_is_help=True, help=f"Operate on a {item_type} by number/id.")

    # Resolved once, up front (unless the caller already resolved it), so every command
    # builder below (retype's target-type help, update's --priority help) derives its help
    # text from the same spec used to decide eligibility — help and enforcement can never
    # disagree.
    if spec is None:
        spec = common.get_active_spec()

    @item.callback()
    @common.command
    async def _resolve(
        ctx: typer.Context,
        num: str = typer.Argument(..., metavar="N", help=f"{item_type} number or id."),
    ):
        svc = get_service()
        ctx.obj = {"id": await resolve_item_id_typed(num, item_type, svc)}

    _cmd_show(item)
    _cmd_update(item, item_type, spec)
    _cmd_status(item)
    _cmd_body(item)
    _cmd_comment(item)
    _cmd_comments(item)
    _cmd_refs(item)

    # Sub-entity surface: entirely spec-driven — a type hosts a kind (built-in or a
    # project-declared custom one) or it doesn't; item_subentity_kind() already degrades to
    # None for a type the spec doesn't declare, so no fallback vocabulary is needed here.
    subentity_kind = spec.item_subentity_kind(item_type)
    if subentity_kind is not None:
        _register_subentity(item, subentity_kind, spec)

    # retype/remove: available for all non-roster types (spec-derived).
    # For types unknown to the spec (pre-callback edge case), fall back to checking
    # against the three roster-type names directly (the irreducible,
    # by-name-bound minimum, not a spec lookup).
    from squads._workflow import ROSTER_TYPES

    is_roster = (
        spec.item_is_roster(item_type) if item_type in spec.items else item_type in ROSTER_TYPES
    )
    if not is_roster:
        _cmd_retype(item, spec)
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
            print_json_clean(await build_item_json(svc, it))
            return
        await print_item(svc, it, raw=raw, comments=comments, full=full)


def _cmd_update(item: typer.Typer, item_type: str, spec: WorkflowSpec) -> None:
    priority_help = _priority_help(item_type, spec, "Priority: {codes}.")

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
        priority: str | None = typer.Option(None, "--priority", help=priority_help),
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


def _cmd_comments(item: typer.Typer) -> None:
    @item.command("comments")
    @common.command
    async def comments(ctx: typer.Context, json_out: bool = typer.Option(False, "--json")):
        """Read back the item's top-level discussion (the dedicated, machine-readable verb —
        `show --comments` renders the same discussion inline alongside the rest of the item)."""
        cmt_list = await get_service().comments(_id(ctx))
        if json_out:
            print_json_clean(
                json.dumps(
                    [{"author": c.author, "ts": c.timestamp, "body": c.body} for c in cmt_list]
                )
            )
            return
        common.print_comments(cmt_list)


def _cmd_retype(item: typer.Typer, spec: WorkflowSpec) -> None:
    targets = "|".join(sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)))

    @item.command("retype")
    @common.command
    async def retype(
        ctx: typer.Context,
        new_type: str = typer.Argument(
            ...,
            metavar="NEW-TYPE",
            help=(
                f"Target type (non-roster: work or records): {targets}. "
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
        wt = common.get_active_spec().non_roster_types()
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
            print_json_clean(
                json.dumps(
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
#
# Everything below is built from the resolved SubentityKindSpec (spec.subentity_kinds[kind]) —
# no per-kind ("story"/"subtask"/"finding") branches. A project-declared custom kind gets the
# identical add-<kind>/<plural>/<kind> <n> <verb> surface for free.


def _field_param(field: Field) -> inspect.Parameter:
    """One dynamic ``--<field-code>`` CLI option for a declared field — used to build both
    ``add-<kind>``'s and ``update``'s parameter list at spec-resolution time."""
    return inspect.Parameter(
        field.code,
        inspect.Parameter.KEYWORD_ONLY,
        default=typer.Option(None, f"--{field.code}", help=f"{field.label} badge code."),
        annotation=str | None,
    )


def _sub_table(kind: str, blocks: list[SubEntity], spec: WorkflowSpec) -> None:
    """Render the list-verb table from the same field-driven column derivation the body's
    ``:summary`` region uses (:func:`discussion.summary_columns`/``summary_row``) — one
    definition, so the CLI list table and the body summary table never drift apart."""
    if not blocks:
        console.print(f"[dim]no {kind}s[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in discussion.summary_columns(kind, spec):
        table.add_column(col)
    for b in blocks:
        table.add_row(*(e(c) for c in discussion.summary_row(kind, b, spec)))
    console.print(table)


def _register_subentity(item: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    plural = spec.subentity_plural(kind)

    @item.command(plural)
    @common.command
    async def list_sub(ctx: typer.Context, json_out: bool = typer.Option(False, "--json")):
        """List this item's sub-entities."""
        blocks = await get_service().list_blocks(_id(ctx), kind)
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
        _sub_table(kind, blocks, spec)

    _register_add(item, kind, spec)

    sub = typer.Typer(no_args_is_help=True, help=f"Operate on a {kind} by number/local id.")

    @sub.callback()
    @handle_errors
    def _resolve_sub(
        ctx: typer.Context,
        n: str = typer.Argument(..., metavar="N", help=f"{kind} number or local id (e.g. 2)."),
    ):
        assert ctx.parent is not None  # the parent item group always runs first
        ctx.obj = {**ctx.parent.obj, "local": resolve_local_id(n, kind)}

    _register_sub_verbs(sub, kind, spec)
    item.add_typer(sub, name=kind)


def _resolve_add_fields(
    svc: Service, kind: str, spec: WorkflowSpec, fields: list[Field], kwargs: dict[str, object]
) -> dict[str, str]:
    """One resolved+validated badge value per declared field, applying the field's own default
    when the flag is omitted (generalizes ``add_finding``'s old severity-default fallback to
    every declared field via the generic ``SubEntity.set_badge_value`` store)."""
    values: dict[str, str] = {}
    for field in fields:
        raw = _kw_str(kwargs, field.code)
        resolved = raw or svc.field_default(kind, field.code)
        if resolved:
            coll = badges.resolve_collection(kind, field.code, spec)
            values[field.code] = parse_badge_code(coll, resolved, spec)
    return values


def _register_add(item: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    """Register ``add-<kind>``: base flags + one ``--<field-code>`` option per declared field
    + ``--story`` iff the kind maps to a parent story + ``--status`` to seed a non-initial
    status at creation — built dynamically from the resolved ``SubentityKindSpec``. Replaces
    the three hand-written per-kind ``_register_add`` closures."""
    ks = spec.subentity_kinds[kind]
    fields = spec.fields_for(kind)

    params: list[inspect.Parameter] = [
        inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context),
        inspect.Parameter(
            "title",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=typer.Argument("", help="Optional short label; detail in body."),
            annotation=str,
        ),
        *(_field_param(field) for field in fields),
    ]
    if ks.maps_parent_story:
        params.append(
            inspect.Parameter(
                "story",
                inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(
                    None, "--story", help="User story it implements (USn or bare 1)."
                ),
                annotation=str | None,
            )
        )
    params += [
        inspect.Parameter(
            "assignee",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--assignee"),
            annotation=str | None,
        ),
        inspect.Parameter(
            "status",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--status", help="Seed a non-initial status."),
            annotation=str | None,
        ),
        inspect.Parameter(
            "message",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "-m", "--message"),
            annotation=list[str],
        ),
        inspect.Parameter(
            "file",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--file", help="Body from a file ('-' = stdin)."),
            annotation=str | None,
        ),
        inspect.Parameter(
            "json_out",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(False, "--json"),
            annotation=bool,
        ),
    ]

    async def _add(**kwargs: object) -> None:
        ctx = cast(typer.Context, kwargs["ctx"])
        title = cast(str, kwargs["title"])
        svc = get_service()
        assignee = _kw_str(kwargs, "assignee")
        validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
        story = _kw_str(kwargs, "story")
        # Story-mapping semantics stay wired to the built-in "story" kind regardless of which
        # kind declares maps_parent_story — a bounded built-in, not per-kind.
        normalized_story = resolve_local_id(story, "story") if story else None
        field_values = _resolve_add_fields(svc, kind, spec, fields, kwargs)
        status = _kw_str(kwargs, "status")
        message = _kw_list(kwargs, "message")
        file = _kw_str(kwargs, "file")
        res = await svc.add_block(
            _id(ctx),
            kind,
            title,
            story=normalized_story,
            fields=field_values or None,
            assignee=validated_assignee,
            status=parse_status(status) if status else None,
            body=resolve_body_optional(message or None, file),
        )
        print_block(_id(ctx), res, _kw_bool(kwargs, "json_out"))

    _add.__doc__ = f"Scaffold a {kind} on this item."
    _add.__signature__ = inspect.Signature(params)  # pyright: ignore[reportFunctionMemberAccess]
    item.command(f"add-{kind}")(common.command(_add))


def _register_update(sub: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    """The sub-entity metadata entry point — one ``--<field-code>`` option per declared field
    (identically to ``add-<kind>``) + ``--story``/``--no-story`` iff maps_parent_story."""
    ks = spec.subentity_kinds[kind]
    fields = spec.fields_for(kind)

    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    params: list[inspect.Parameter] = [
        inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context),
        inspect.Parameter(
            "title",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--title"),
            annotation=str | None,
        ),
        *(_field_param(field) for field in fields),
    ]
    if ks.maps_parent_story:
        params += [
            inspect.Parameter(
                "story",
                inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(None, "--story", help="Remap to a user story (USn)."),
                annotation=str | None,
            ),
            inspect.Parameter(
                "no_story",
                inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(False, "--no-story", help="Clear the story mapping."),
                annotation=bool,
            ),
        ]
    params += [
        inspect.Parameter(
            "assignee",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--assignee"),
            annotation=str | None,
        ),
        inspect.Parameter(
            "clear_assignee",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(False, "--clear-assignee"),
            annotation=bool,
        ),
        inspect.Parameter(
            "status",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(None, "--status"),
            annotation=str | None,
        ),
        inspect.Parameter(
            "force",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(False, "--force"),
            annotation=bool,
        ),
    ]

    async def _update(**kwargs: object) -> None:
        ctx = cast(typer.Context, kwargs["ctx"])
        pid, lid = ids(ctx)
        title = _kw_str(kwargs, "title")
        story = _kw_str(kwargs, "story")
        no_story = _kw_bool(kwargs, "no_story")
        assignee = _kw_str(kwargs, "assignee")
        clear_assignee = _kw_bool(kwargs, "clear_assignee")
        status = _kw_str(kwargs, "status")
        force = _kw_bool(kwargs, "force")

        field_values: dict[str, str] = {}
        for field in fields:
            raw = _kw_str(kwargs, field.code)
            if raw is None:
                continue
            coll = badges.resolve_collection(kind, field.code, spec)
            field_values[field.code] = parse_badge_code(coll, raw, spec)

        if story and no_story:
            raise SquadsError("use --story or --no-story, not both")
        _guard_update(
            has_any=any((title, field_values, story, no_story, assignee, clear_assignee, status)),
            assignee=assignee,
            clear_assignee=clear_assignee,
        )
        svc = get_service()
        validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
        normalized_story = resolve_local_id(story, "story") if story else None
        await svc.update_block(
            pid,
            kind,
            lid,
            title=title,
            fields=field_values or None,
            story=normalized_story,
            clear_story=no_story,
            assignee=validated_assignee,
            clear_assignee=clear_assignee,
            status=parse_status(status) if status else None,
            force=force,
        )
        console.print(f"updated {pid} {lid}")

    _update.__doc__ = f"Update the {kind}'s metadata (title / assignee / status / declared fields)."
    _update.__signature__ = inspect.Signature(params)  # pyright: ignore[reportFunctionMemberAccess]
    sub.command("update")(common.command(_update))


def _register_sub_verbs(sub: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    @sub.command("show")
    @common.command
    async def s_show(ctx: typer.Context):
        """Show the sub-entity's status/assignee, body, and discussion."""
        pid, lid = ids(ctx)
        print_subentity(await get_service().get_block(pid, kind, lid), kind)

    _register_update(sub, kind, spec)

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
        await get_service().set_block_body(
            pid, kind, lid, resolve_body(message or None, file), append=append
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
        await svc.comment(pid, message, as_slug=slug, sub=(kind, lid))
        console.print(f"commented on {pid} {lid} as {slug}")

    @sub.command("remove")
    @common.command
    async def s_remove(
        ctx: typer.Context,
        yes: bool = typer.Option(False, "--yes", help="Skip the interactive confirmation prompt."),
        json_out: bool = typer.Option(False, "--json"),
    ):
        """Hard-delete this sub-entity: drop it from the parent and excise its body/discussion.

        Removing a `story` refuses while any subtask still maps to it (remap or remove those
        first). The freed local id is a sanctioned gap the same way a removed item's sequence
        number is — see `sq <type> <n> remove`.
        """
        pid, lid = ids(ctx)
        if not yes:
            typer.confirm(f"Remove {kind} {lid} from {pid}? This cannot be undone.", abort=True)
        await get_service().remove_block(pid, kind, lid)
        if json_out:
            print_json_clean(json.dumps({"removed": f"{kind} {lid}"}))
            return
        console.print(f"removed {kind} {lid} from {pid}")
