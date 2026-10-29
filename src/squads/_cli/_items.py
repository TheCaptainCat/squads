"""Resource-oriented item commands: ``sq <type> <num> <verb> …`` (sub-entities nest one level).

:func:`build_item_app` builds one Typer group per work-item type. The group callback resolves
``<num>`` to a full item id (validating the type) into the Click context; each verb reads it
back and wraps an existing ``svc.*`` method. A type that declares a sub-entity kind also gets
``add-<kind>``, a ``<plural>`` list verb and a nested ``<kind> <n> <verb>`` subgroup, built
generically from the resolved ``SubentityKindSpec`` (see :func:`_register_subentity`).
"""
# Commands are nested closures registered via Typer decorators (side effect), so they read as
# "unused" to static analysis — disable that one check for this factory module.
# pyright: reportUnusedFunction=false

import inspect
import json
import textwrap
from collections.abc import Callable, Sized
from typing import Any, cast

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main
from rich.table import Table

import squads._cli._common as common
from squads import _badges as badges
from squads import _discussion as discussion
from squads._cli._common import (
    build_item_json,
    build_subentity_json,
    build_subentity_row_json,
    console,
    e,
    get_active_spec,
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
    view_disable_result_message,
)
from squads._errors import SquadsError
from squads._models._item import split_ref
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


def _guard_assignee(assignee: str | None, clear_assignee: bool) -> None:
    """Refuse an empty `--assignee` (it changes nothing) and `--assignee` with its clear flag."""
    if assignee is not None and not assignee.strip():
        raise SquadsError("--assignee needs a slug; use --clear-assignee to remove the assignee")
    if assignee is not None and clear_assignee:
        raise SquadsError("use --assignee or --clear-assignee, not both")


def _anything_asked(*values: object) -> bool:
    """Whether any option value was given (a flag counts when true, a list or dict when
    non-empty, any other value when not None)."""
    return any(
        bool(cast(Sized, v)) if isinstance(v, list | dict) else v not in (None, False)
        for v in values
    )


def _settle_clear_assignee(
    current: str | None, clear_assignee: bool, *others: object
) -> tuple[bool, bool]:
    """Drop `--clear-assignee` when the target has no assignee (*current*), and report whether
    nothing else was asked for either (*others*: the remaining `update` options)."""
    if not clear_assignee or current is not None:
        return clear_assignee, False
    return False, not _anything_asked(*others)


def _guard_update(*, has_any: bool, assignee: str | None, clear_assignee: bool) -> None:
    """Shared `update` validation: valid assignee flags + at least one field given."""
    _guard_assignee(assignee, clear_assignee)
    if not has_any:
        raise SquadsError("nothing to update (pass at least one field, e.g. --title/--status)")


def _priority_help(item_type: str, spec: WorkflowSpec, template: str) -> str:
    """``--priority`` help from the collection *item_type* binds, or a spec pointer if it has none.

    Resolution is strict (:func:`squads._badges.declared_collection`): the same-name fallback
    would list the bundled ``priority`` codes for a type that never declared the field,
    advertising a flag that can only error.
    """
    # sanctioned field-code literal: `--priority` is the flag *for* this field code
    coll_code = badges.declared_collection(item_type, "priority", spec)
    coll = spec.collections.get(coll_code) if coll_code else None
    if coll and coll.badges:
        return template.format(codes="|".join(b.code for b in coll.badges))
    return "Priority code (as defined by your workflow's priority collection)."


def _declares_priority(item_type: str, spec: WorkflowSpec) -> bool:
    """Whether *item_type* declares a ``priority`` field — drives whether ``--priority`` is
    advertised at all (a type that doesn't can only ever be refused by the service gate)."""
    # sanctioned field-code literal: `--priority` is the flag *for* this field code
    return badges.declared_collection(item_type, "priority", spec) is not None


#: One entry per aspect of a sub-entity kind that shapes the generated command surface.
type _FieldSignature = tuple[str, str, str, bool, str | None]
type KindSignature = tuple[str, str, bool, tuple[_FieldSignature, ...]] | None


def _kind_signature(item_type: str, spec: WorkflowSpec) -> KindSignature:
    """What ``_register_subentity`` bakes into the generated commands for *item_type*'s kind.

    The kind name, its plural (the list verb), whether it maps a parent story (``--story``), and
    every declared field's code, label, bound collection, requiredness and default (the
    ``--<field-code>`` options, their help and the omitted-flag fallback). Equal signatures
    produce identical command trees, so comparing them tests whether the static tree still
    describes a spec; a name-only comparison would miss a field swap. ``None`` when the type
    hosts no kind.
    """
    kind = spec.item_subentity_kind(item_type)
    ks = spec.subentity_kinds.get(kind) if kind else None
    if kind is None or ks is None:
        return None
    fields = tuple(
        (f.code, f.label, f.collection, f.required, f.default) for f in spec.fields_for(kind)
    )
    return (kind, ks.plural, ks.maps_parent_story, fields)


def _dynamic_subentity_group_cls(item_type: str) -> type[typer.core.TyperGroup]:
    """A ``TyperGroup`` for *item_type* that rebuilds stale sub-entity commands from the live spec.

    A built-in type's sub-entity kind and its ``--<field-code>`` options are baked in at import
    time from the bundled spec. When the live spec renames the kind (``story`` -> ``scenario``)
    or replaces its fields (``severity`` -> a required ``impact``), the static tree would offer
    the old verbs and options, so a missing command is built from the live spec instead. The
    trigger is the whole :func:`_kind_signature`, not just the kind name.

    ``get_command`` leaves the old kind's commands reachable, so ``sq feature N add-story``
    reaches the accurate "features host scenarios" refusal rather than Click's did-you-mean;
    ``list_commands`` hides them so stale verbs do not sit beside the correct ones in help.
    """
    from squads._workflow import bundled_spec

    def _kind_verb_names(kind: str, spec: WorkflowSpec) -> set[str]:
        return {f"add-{kind}", spec.subentity_plural(kind), kind}

    _bundled_spec = bundled_spec()
    bundled_kind = _bundled_spec.item_subentity_kind(item_type)
    # The stale verb names come from the bundled spec: the live one may no longer declare
    # this kind at all and would raise on a plural lookup.
    stale_verb_names: set[str] = (
        _kind_verb_names(bundled_kind, _bundled_spec) if bundled_kind else set()
    )
    bundled_signature = _kind_signature(item_type, _bundled_spec)

    class _Group(common.HelpAwareGroup):
        def get_command(self, ctx: Any, cmd_name: str) -> _click.Command | None:
            try:
                spec = common.get_active_spec()
                kind = spec.item_subentity_kind(item_type)
                rebuild = _kind_signature(item_type, spec) != bundled_signature
            except Exception:  # pylint: disable=broad-except
                return super().get_command(ctx, cmd_name)

            # A renamed kind, or the same kind with different fields, is served from a fresh
            # app so the parameters match the live spec.
            if rebuild:
                fresh = build_item_app(item_type, spec=spec, dynamic_subentity=False)
                fresh_click = cast(typer.core.TyperGroup, typer.main.get_command(fresh))
                fresh_cmd = fresh_click.get_command(ctx, cmd_name)
                if fresh_cmd is not None:
                    return fresh_cmd

            # Fall back to the static tree: the answer for an unchanged squad, and under a
            # rename it keeps the old kind's verbs reachable for the accurate refusal.
            cmd = super().get_command(ctx, cmd_name)
            if cmd is not None:
                return cmd
            if kind is None or cmd_name not in _kind_verb_names(kind, spec):
                return None
            fresh = build_item_app(item_type, spec=spec, dynamic_subentity=False)
            fresh_click = cast(typer.core.TyperGroup, typer.main.get_command(fresh))
            return fresh_click.get_command(ctx, cmd_name)

        def list_commands(self, ctx: Any) -> list[str]:
            base = super().list_commands(ctx)
            try:
                spec = common.get_active_spec()
                kind = spec.item_subentity_kind(item_type)
            except Exception:  # pylint: disable=broad-except
                return base
            # Return `base` untouched in registration order: `list_commands` promises creation
            # order, and a `sorted()` merge would reshuffle `--help` for every squad.
            if kind is None or kind == bundled_kind:
                return base
            visible = [c for c in base if c not in stale_verb_names]
            new_names = sorted(_kind_verb_names(kind, spec) - set(visible))
            return visible + new_names

    return _Group


def build_item_app(
    item_type: str, spec: WorkflowSpec | None = None, *, dynamic_subentity: bool = True
) -> typer.Typer:
    """A ``sq <type> <num> …`` group for one work-item type (a plain string name).

    Capability flags (sub-entity kind, retype/remove eligibility) come from *spec*, defaulting
    to ``get_active_spec()``. A caller that already resolved the ctx-appropriate spec, such as
    the root group's custom-type dispatch, passes it so the build uses the spec that decided
    the type exists, not whatever is bound before the root callback runs.

    ``dynamic_subentity`` (default ``True``) wraps the group in
    :func:`_dynamic_subentity_group_cls` so a renamed sub-entity kind is reachable on a built-in
    type. Pass ``False`` only for the spec-resolved rebuild that fallback performs; it already
    has the resolved kind, and enabling it there would recurse.
    """
    item = typer.Typer(
        no_args_is_help=True,
        help=common.type_group_help(item_type),
        cls=_dynamic_subentity_group_cls(item_type) if dynamic_subentity else common.HelpAwareGroup,
    )

    # Resolved once, so every builder below (retype's target help, update's --priority help)
    # derives its help from the same spec that decides eligibility.
    if spec is None:
        spec = common.get_active_spec()

    @item.callback()
    @common.command
    async def _resolve(
        ctx: typer.Context,
        num: str = typer.Argument(..., metavar="N", help=f"Number or ID of the {item_type}."),
    ):
        svc = get_service()
        ctx.obj = await common.address_obj(ctx, lambda: resolve_item_id_typed(num, item_type, svc))

    _cmd_show(item)
    _cmd_update(item, item_type, spec)
    _cmd_status(item)
    _cmd_body(item)
    common.register_comment_verbs(item, _id)
    _cmd_refs(item)
    _cmd_view(item)

    # Sub-entity surface: entirely spec-driven — a type hosts a kind (built-in or a
    # project-declared custom one) or it doesn't; item_subentity_kind() already degrades to
    # None for a type the spec doesn't declare, so no fallback vocabulary is needed here.
    subentity_kind = spec.item_subentity_kind(item_type)
    if subentity_kind is not None:
        _register_subentity(item, subentity_kind, spec)

    # retype/remove: available for all non-roster types. item_is_roster() is False for a type
    # unknown to the spec rather than raising; role/skill/operator can never be dropped.
    if not spec.item_is_roster(item_type):
        _cmd_retype(item)
        _cmd_remove(item)
    return item


def _cmd_show(item: typer.Typer) -> None:
    @item.command("show")
    @common.command
    async def show(
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the item."),
        raw: bool = common.raw_option(),
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
        await common.warn_duplicate_id(svc, it)
        await print_item(svc, it, raw=raw, comments=comments, full=full)


def _cmd_update(item: typer.Typer, item_type: str, spec: WorkflowSpec) -> None:
    priority_help = _priority_help(item_type, spec, "Priority: {codes}.")

    def _refresh_priority_help(params: list[object]) -> None:
        live_spec = common.get_active_spec()
        text = _priority_help(item_type, live_spec, "Priority: {codes}.")
        # Hidden, not removed, on a type declaring no priority field: the flag still parses
        # so the service's declared-field gate owns the one accurate refusal, but a flag that
        # can only ever error is never offered in --help (same split as the create side).
        declared = _declares_priority(item_type, live_spec)
        for p in params:
            if getattr(p, "name", None) in ("priority", "no_priority"):
                p.hidden = not declared  # type: ignore[attr-defined]
            if getattr(p, "name", None) == "priority":
                p.help = text  # type: ignore[attr-defined]

    @item.command("update", cls=common.spec_aware_command_cls(_refresh_priority_help))
    @common.command
    async def update(  # noqa: PLR0913 — the one metadata entry point
        ctx: typer.Context,
        title: str | None = typer.Option(None, "--title", help="New title."),
        desc: str | None = common.desc_option(None),
        author: str | None = common.author_option(None),
        status: str | None = common.move_status_option(),
        force: bool = common.force_transition_option(),
        parent: str | None = typer.Option(None, "--parent", help="New parent item ID or number."),
        no_parent: bool = typer.Option(False, "--no-parent", help="Clear the parent."),
        assignee: str | None = common.assignee_option(),
        clear_assignee: bool = typer.Option(False, "--clear-assignee", help="Remove the assignee."),
        priority: str | None = typer.Option(None, "--priority", help=priority_help),
        no_priority: bool = typer.Option(False, "--no-priority", help="Clear the priority."),
        add_label: list[str] = typer.Option(None, "--add-label", help="Label to add (repeatable)."),
        rm_label: list[str] = typer.Option(
            None, "--rm-label", help="Label to remove (repeatable)."
        ),
        set_: list[str] = typer.Option(
            None,
            "--set",
            help="Set a declared attribute as `key=value` (repeatable; see `sq workflow types`).",
        ),
        unset: list[str] = typer.Option(None, "--unset", help="Attribute to remove (repeatable)."),
        as_: str | None = common.edit_as_option(),
    ):
        """Change the item's title, status, parent, assignee, labels or attributes."""
        # `is not None`, not truthiness: `--parent ""` is a supplied value, and a truth test
        # let it through and report "updated" for a parent never written. Same for priority.
        if parent is not None and no_parent:
            raise SquadsError("use either --parent or --no-parent, not both")
        if priority is not None and no_priority:
            raise SquadsError("use either --priority or --no-priority, not both")
        if parent is not None and not parent.strip():
            raise SquadsError("--parent needs an item ID; use --no-parent to clear the parent")
        set_attributes: dict[str, str] = {}
        for pair in set_ or []:
            key, sep, value = pair.partition("=")
            if not sep:
                raise SquadsError(f"--set expects key=value, got {pair!r}")
            set_attributes[key.strip()] = value
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        others = (
            title, desc, author, status, parent, no_parent, priority, no_priority,
            add_label, rm_label, set_, unset,
        )  # fmt: skip
        _guard_update(
            has_any=_anything_asked(*others, assignee, clear_assignee),
            assignee=assignee,
            clear_assignee=clear_assignee,
        )
        clear_assignee, nothing_to_change = _settle_clear_assignee(
            (await svc.get(_id(ctx))).assignee, clear_assignee, *others
        )
        if nothing_to_change:
            console.print(f"{_id(ctx)} has no assignee to clear")
            return
        validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
        validated_author = await resolve_slug_or_raise(author, svc) if author else None
        resolved_parent = await resolve_item_id_any(parent, svc) if parent is not None else None
        it = await svc.update(
            _id(ctx),
            title=title,
            description=desc,
            assignee=validated_assignee,
            clear_assignee=clear_assignee,
            # No pre-parse: the collection `priority` binds is per-type and the service's
            # `_check_priority` resolves it from this item's own declared field. See the
            # matching note in `_cli/_create.py`.
            priority=priority,
            clear_priority=no_priority,
            add_labels=add_label or None,
            rm_labels=rm_label or None,
            author=validated_author,
            status=parse_status(status) if status else None,
            force=force,
            parent=resolved_parent,
            clear_parent=no_parent,
            set_attributes=set_attributes or None,
            unset_attributes=unset or None,
        )
        console.print(f"updated {it.id}  [dim]{it.path}[/dim]")


def _cmd_status(item: typer.Typer) -> None:
    @item.command("status")
    @common.command
    async def status(
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS", help=common.MOVE_STATUS_HELP),
        force: bool = common.force_transition_option(),
        as_: str | None = common.edit_as_option(),
    ):
        """Move the item to another status."""
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        it = await svc.set_status(_id(ctx), parse_status(new_status), force=force)
        console.print(f"{it.id} → [bold]{it.status}[/bold]")


def _cmd_body(item: typer.Typer) -> None:
    @item.command("body")
    @common.command
    async def body(
        ctx: typer.Context,
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        append: bool = common.append_option(),
        force: bool = common.replace_body_option(),
        as_: str | None = common.edit_as_option(),
    ):
        """Set or append to the item's body.

        Replacing a body someone has already written is refused unless `--force`; the
        refusal names what would be lost and writes nothing, so a bare `body` is a
        safe check. A first write over the template just works.
        """
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        await svc.set_body(
            _id(ctx), resolve_body(message or None, file), append=append, force=force
        )
        console.print(f"{_id(ctx)}: body {'appended' if append else 'set'}")


def _cmd_retype(item: typer.Typer) -> None:
    @item.command("retype")
    @common.command
    async def retype(
        ctx: typer.Context,
        new_type: str = typer.Argument(
            ...,
            metavar="NEW-TYPE",
            help=(
                "Type to reclassify to, not a roster type (see `sq workflow types`). "
                "The item number is kept; only the ID prefix changes."
            ),
        ),
        as_: str | None = common.edit_as_option(),
    ):
        """Reclassify this item to a different type, keeping its number and body.

        Only the prefix changes, as `TASK-<n>` to `BUG-<n>`, and every reference to
        the item is rewritten. The status is kept when both types share a lifecycle,
        and reset to the new type's first status otherwise.
        """
        target = parse_type(new_type)
        wt = common.get_active_spec().non_roster_types()
        if target not in wt:
            work = ", ".join(sorted(wt))
            raise SquadsError(f"cannot retype to {new_type!r}; valid targets: {work}")
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
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
            help="Cut the refs other items carry to this one instead of refusing.",
        ),
        yes: bool = common.yes_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the removed ID and the cut refs."
        ),
        as_: str | None = common.edit_as_option(),
    ):
        """Delete this item for good: its file and its index entry.

        Refused while the item has children, or refs from other items unless `--force`
        cuts them. Its number is never reused. To drop work that was considered, move
        it to the type's cancelled status instead (see `sq workflow lifecycles`);
        remove only items that should never have existed.
        """
        item_id = _id(ctx)
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        if not yes:
            common.confirm_or_signal(f"Remove {item_id}? This cannot be undone.")
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
        out: bool = typer.Option(
            False, "--out", help="Show the refs this item carries; the default."
        ),
        incoming: bool = typer.Option(
            False, "--in", help="Show the refs other items carry to this one."
        ),
        all_: bool = typer.Option(False, "--all", help="Show both directions."),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object, with an array per direction shown."
        ),
    ):
        """List the item's refs, or the refs other items carry to it."""
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

    ref_app = typer.Typer(no_args_is_help=True, help="Add or remove the item's refs.")

    @ref_app.command("add")
    @common.command
    async def ref_add(
        ctx: typer.Context,
        target: str = typer.Argument(
            ..., help="Item ID or number to ref; `ID:kind` also sets the kind."
        ),
        kind: str = typer.Option(
            "",
            "--kind",
            help="Ref kind (see `sq workflow ref-kinds`); without it, the default kind.",
        ),
        as_: str | None = common.edit_as_option(),
    ):
        """Add a ref from this item to TARGET."""
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        # target may be a bare number, full ID, or ID:kind — resolve the ID part only
        raw_id, embedded_kind = split_ref(target)
        resolved_id = await resolve_item_id_any(raw_id, svc)
        effective_kind = embedded_kind or kind or svc.spec.default_ref_kind()
        await svc.add_ref(_id(ctx), resolved_id, kind=effective_kind)
        console.print(f"{_id(ctx)} → {resolved_id} ([dim]{effective_kind}[/dim])")

    @ref_app.command("rm")
    @common.command
    async def ref_rm(
        ctx: typer.Context,
        target: str = typer.Argument(..., help="Item ID or number."),
        as_: str | None = common.edit_as_option(),
    ):
        """Remove this item's ref to TARGET."""
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        raw_id, _ = split_ref(target)
        resolved_id = await resolve_item_id_any(raw_id, svc)
        await svc.rm_ref(_id(ctx), resolved_id)
        console.print(f"removed {_id(ctx)} → {resolved_id}")

    item.add_typer(ref_app, name="ref")


def _cmd_view(item: typer.Typer) -> None:
    """The ``sq <type> <n> view add|disable <name>`` group for an unpaired ``sq:view:<name>`` tag.

    ``add`` places or re-enables the tag in the item's ``sq:body`` region and ``disable`` turns it
    off; a tag is never deleted. It is a verb group, not a ``body`` flag, because it is the only
    door a view tag enters or leaves through: ``reject_markers`` still refuses a hand-typed tag
    in ``body -m``/``--file``.
    """
    view_app = typer.Typer(
        no_args_is_help=True, help="Show or hide declared views in the item's body."
    )

    @view_app.command("add")
    @common.command
    async def view_add(
        ctx: typer.Context,
        name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
        as_: str | None = common.edit_as_option(),
    ):
        """Show a declared view in the item's body, or re-enable it."""
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        placed = await svc.add_view(_id(ctx), name)
        if placed:
            console.print(f"{_id(ctx)}: view {e(name)} placed in sq:body")
        else:
            console.print(f"{_id(ctx)}: view {e(name)} already present, unchanged")

    @view_app.command("disable")
    @common.command
    async def view_disable(
        ctx: typer.Context,
        name: str = typer.Argument(
            ..., help="View name; it need not be declared, so a dropped view can be turned off."
        ),
        as_: str | None = common.edit_as_option(),
    ):
        """Stop showing a view in the item's body; its tag stays, disabled."""
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        item_id = _id(ctx)
        was_present = await svc.view_tag_present(item_id, name)
        disabled = await svc.disable_view(item_id, name)
        console.print(
            view_disable_result_message(item_id, name, was_present=was_present, changed=disabled)
        )

    item.add_typer(view_app, name="view")


# --------------------------------------------------------------------------- sub-entities
# Everything below is built from the resolved SubentityKindSpec, with no per-kind branches, so
# a custom kind gets the same add-<kind>/<plural>/<kind> <n> <verb> surface.


def _edit_as_param() -> inspect.Parameter:
    """The ``--as`` option of a generated ``add-<kind>`` / ``update`` verb."""
    return inspect.Parameter(
        "as_",
        inspect.Parameter.KEYWORD_ONLY,
        default=common.edit_as_option(),
        annotation=str | None,
    )


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


def _doc[F: Callable[..., object]](text: str) -> Callable[[F], F]:
    """Give a generated command the help text its kind's labels spell out."""

    def apply(fn: F) -> F:
        fn.__doc__ = text
        return fn

    return apply


def _register_subentity(item: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    plural = spec.subentity_plural(kind)

    @item.command(plural)
    @common.command
    @_doc(f"List this item's {plural}.")
    async def list_sub(
        ctx: typer.Context,
        json_out: bool = typer.Option(
            False, "--json", help=f"Print a JSON array, one object per {kind}."
        ),
    ):
        blocks = await get_service().list_blocks(_id(ctx), kind)
        if json_out:
            print_json_clean(
                json.dumps(
                    [
                        build_subentity_row_json(
                            local_id=b.local_id,
                            title=b.title,
                            status=b.status,
                            assignee=b.assignee,
                            severity=b.severity,
                            story=b.story,
                            deferred_to=b.deferred_to,
                        )
                        for b in blocks
                    ]
                )
            )
            return
        _sub_table(kind, blocks, spec)

    _register_add(item, kind, spec)

    sub = typer.Typer(
        no_args_is_help=True,
        help=f"Operate on {common.article(kind)} {kind} by number or local ID.",
    )

    @sub.callback()
    @handle_errors
    def _resolve_sub(
        ctx: typer.Context,
        n: str = typer.Argument(
            ..., metavar="LOCAL-ID", help=f"Number or local ID of the {kind}, such as 2."
        ),
    ):
        assert ctx.parent is not None  # the parent item group always runs first
        ctx.obj = common.extend_obj(ctx.parent.obj, local=resolve_local_id(n, kind))

    _register_sub_verbs(sub, kind, spec)
    item.add_typer(sub, name=kind)


def _resolve_add_fields(
    svc: Service, kind: str, spec: WorkflowSpec, fields: list[Field], kwargs: dict[str, object]
) -> dict[str, str]:
    """One resolved+validated badge value per declared field, applying the field's own default
    when the flag is omitted (every declared field resolves through the generic
    ``SubEntity.set_badge_value`` store)."""
    values: dict[str, str] = {}
    for field in fields:
        raw = _kw_str(kwargs, field.code)
        resolved = raw or svc.field_default(kind, field.code)
        if resolved:
            coll = badges.resolve_collection(kind, field.code, spec)
            values[field.code] = parse_badge_code(coll, resolved, spec)
    return values


def _deferred_to_params(kind: str, spec: WorkflowSpec) -> list[inspect.Parameter]:
    """The ``--deferred-to`` option, present only on a kind whose lifecycle reaches a status of
    a ``deferred`` role."""
    if not spec.subentity_deferred_statuses(kind):
        return []
    return [
        inspect.Parameter(
            "deferred_to",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(
                None,
                "--deferred-to",
                help="Item that carries the work (ID or number); needed for a deferred status.",
            ),
            annotation=str | None,
        )
    ]


async def _resolve_deferred_to(svc: Service, kwargs: dict[str, object]) -> str | None:
    """The full ID behind ``--deferred-to``, or ``None`` when it was not given."""
    token = _kw_str(kwargs, "deferred_to")
    return await resolve_item_id_any(token, svc) if token else None


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
            default=typer.Argument("", help="Optional short title; put the detail in the body."),
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
                    None, "--story", help="Story it implements, as `US<n>` or `<n>`."
                ),
                annotation=str | None,
            )
        )
    params += [
        inspect.Parameter(
            "assignee",
            inspect.Parameter.KEYWORD_ONLY,
            default=common.assignee_option(),
            annotation=str | None,
        ),
        inspect.Parameter(
            "status",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(
                None, "--status", help="Status to start in instead of the first one."
            ),
            annotation=str | None,
        ),
        *_deferred_to_params(kind, spec),
        inspect.Parameter(
            "message",
            inspect.Parameter.KEYWORD_ONLY,
            default=common.message_option(),
            annotation=list[str],
        ),
        inspect.Parameter(
            "file",
            inspect.Parameter.KEYWORD_ONLY,
            default=common.file_option(),
            annotation=str | None,
        ),
        inspect.Parameter(
            "json_out",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(False, "--json", help=f"Print one JSON object: the new {kind}."),
            annotation=bool,
        ),
        _edit_as_param(),
    ]

    async def _add(**kwargs: object) -> None:
        ctx = cast(typer.Context, kwargs["ctx"])
        title = cast(str, kwargs["title"])
        svc = get_service()
        await common.apply_edit_actor(_kw_str(kwargs, "as_"), svc)
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
            deferred_to=await _resolve_deferred_to(svc, kwargs),
            body=resolve_body_optional(message or None, file),
        )
        print_block(_id(ctx), res, _kw_bool(kwargs, "json_out"))

    _add.__doc__ = f"Scaffold {common.article(kind)} {kind} on this item."
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
            default=typer.Option(None, "--title", help="New title."),
            annotation=str | None,
        ),
        *(_field_param(field) for field in fields),
    ]
    if ks.maps_parent_story:
        params += [
            inspect.Parameter(
                "story",
                inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(
                    None, "--story", help="Story to map it to, as `US<n>` or `<n>`."
                ),
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
            default=common.assignee_option(),
            annotation=str | None,
        ),
        inspect.Parameter(
            "clear_assignee",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(False, "--clear-assignee", help="Remove the assignee."),
            annotation=bool,
        ),
        inspect.Parameter(
            "status",
            inspect.Parameter.KEYWORD_ONLY,
            default=common.move_status_option(),
            annotation=str | None,
        ),
        *_deferred_to_params(kind, spec),
        inspect.Parameter(
            "force",
            inspect.Parameter.KEYWORD_ONLY,
            default=common.force_transition_option(),
            annotation=bool,
        ),
        _edit_as_param(),
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
            has_any=any(
                (
                    title is not None,
                    field_values,
                    story,
                    no_story,
                    assignee,
                    clear_assignee,
                    status,
                    _kw_str(kwargs, "deferred_to"),
                )
            ),
            assignee=assignee,
            clear_assignee=clear_assignee,
        )
        svc = get_service()
        await common.apply_edit_actor(_kw_str(kwargs, "as_"), svc)
        clear_assignee, nothing_to_change = _settle_clear_assignee(
            (await svc.get_block(pid, kind, lid)).info.assignee,
            clear_assignee,
            title,
            field_values,
            story,
            no_story,
            status,
            _kw_str(kwargs, "deferred_to"),
        )
        if nothing_to_change:
            console.print(f"{pid} {lid} has no assignee to clear")
            return
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
            deferred_to=await _resolve_deferred_to(svc, kwargs),
            force=force,
        )
        console.print(f"updated {pid} {lid}")

    _update.__doc__ = f"Change the {kind}'s title, status, assignee or declared fields."
    _update.__signature__ = inspect.Signature(params)  # pyright: ignore[reportFunctionMemberAccess]
    sub.command("update")(common.command(_update))


def _remove_help(kind: str, spec: WorkflowSpec) -> str:
    """The help of ``<kind> remove``, naming the kind that maps onto it when one does."""
    mapping = sorted(
        {
            child
            for item_type, ts in spec.items.items()
            if (child := ts.subentity_kind) is not None
            and spec.subentity_kinds[child].maps_parent_story
            and spec.item_subentity_kind(spec.item_parent_required(item_type) or "") == kind
        }
    )
    note = "Its local id is never reused."
    if mapping:
        note += (
            f" {common.article(kind).capitalize()} {kind} that {common.article(mapping[0])} "
            f"{mapping[0]} still maps to is refused; remap or remove the {mapping[0]} first."
        )
    summary = f"Delete this {kind} for good, with its body and discussion."
    return f"{summary}\n\n{textwrap.fill(note, 78)}"


def _register_sub_verbs(sub: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    def ids(ctx: typer.Context) -> tuple[str, str]:
        return ctx.obj["id"], ctx.obj["local"]

    @sub.command("show")
    @common.command
    @_doc(f"Show the {kind}'s status, assignee, body and discussion.")
    async def s_show(
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json", help=f"Print one JSON object: the {kind}."),
    ):
        pid, lid = ids(ctx)
        detail = await get_service().get_block(pid, kind, lid)
        if json_out:
            print_json_clean(json.dumps(build_subentity_json(get_active_spec(), kind, detail)))
            return
        print_subentity(detail, kind)

    _register_update(sub, kind, spec)

    @sub.command("body")
    @common.command
    @_doc(
        f"Set or append to the {kind}'s body.\n\n"
        "Replacing a body someone has already written is refused unless `--force`."
    )
    async def s_body(
        ctx: typer.Context,
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        append: bool = common.append_option(),
        force: bool = common.replace_body_option(),
        as_: str | None = common.edit_as_option(),
    ):
        pid, lid = ids(ctx)
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        await svc.set_block_body(
            pid, kind, lid, resolve_body(message or None, file), append=append, force=force
        )
        console.print(f"{pid} {lid}: body {'appended' if append else 'set'}")

    common.register_comment_group(sub, lambda ctx: (ids(ctx)[0], (kind, ids(ctx)[1])))

    @sub.command("remove")
    @common.command
    @_doc(_remove_help(kind, spec))
    async def s_remove(
        ctx: typer.Context,
        yes: bool = common.yes_option(),
        json_out: bool = typer.Option(
            False, "--json", help=f"Print one JSON object naming the removed {kind}."
        ),
        as_: str | None = common.edit_as_option(),
    ):
        pid, lid = ids(ctx)
        svc = get_service()
        await common.apply_edit_actor(as_, svc)
        if not yes:
            common.confirm_or_signal(f"Remove {kind} {lid} from {pid}? This cannot be undone.")
        await svc.remove_block(pid, kind, lid)
        if json_out:
            print_json_clean(json.dumps({"removed": f"{kind} {lid}"}))
            return
        console.print(f"removed {kind} {lid} from {pid}")
