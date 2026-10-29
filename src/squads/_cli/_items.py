"""Resource-oriented item commands: ``sq <type> <num> <verb> …`` (sub-entities nest one level).

:func:`build_item_app` builds one Typer group per work-item type. The group callback puts the
item's address in the Click context, parsed only: each verb's operation checks the item.
A type that declares a sub-entity kind also gets ``add-<kind>``, a ``<plural>`` list verb and a
nested ``<kind> <n> <verb>`` subgroup, built generically from the resolved ``SubentityKindSpec``
(see :func:`_register_subentity`).
"""
# Commands are nested closures registered via Typer decorators (side effect), so they read as
# "unused" to static analysis — disable that one check for this factory module.
# pyright: reportUnusedFunction=false

import inspect
import textwrap
from collections.abc import Callable, Sized
from typing import Any, cast

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main
from pydantic import BaseModel
from rich.console import Console

import squads._cli._common as common
from squads import _badges as badges
from squads._api import _ops as ops
from squads._api._api import Operation
from squads._api._dto._comment_writes import (
    SubentityCommentAddRequest,
    SubentityCommentEditRequest,
    SubentityCommentRequest,
)
from squads._api._dto._item_writes import (
    ItemBodyRequest,
    ItemRefRemoveRequest,
    ItemRefRequest,
    ItemRemoveRequest,
    ItemRetypeRequest,
    ItemUpdateRequest,
    ItemViewChanged,
    ItemViewRequest,
    SubentityAddRequest,
    SubentityBodyRequest,
    SubentityRemoveRequest,
    SubentityUpdated,
    SubentityUpdateRequest,
)
from squads._api._dto._items import ItemShowRequest, ItemStatusRequest
from squads._api._dto._refs import RefsRequest
from squads._api._dto._subentities import SubentitiesRequest, SubentityRequest
from squads._cli import _calls as calls
from squads._cli._common import (
    console,
    handle_errors,
    parse_badge_code,
    parse_status,
    parse_type,
    resolve_body,
    resolve_body_optional,
    resolve_local_id,
)
from squads._cli._render._items import render_show, render_status
from squads._cli._render._refs import render_refs
from squads._cli._render._roster import render_body_written, render_view_change
from squads._cli._render._subentities import render_subentities, render_subentity
from squads._cli._render._writes import (
    render_item_removed,
    render_ref_added,
    render_ref_removed,
    render_retyped,
    render_subentity_added,
    render_subentity_removed,
    render_updated,
)
from squads._errors import SquadsError
from squads._workflow._models import Field, WorkflowSpec


def _address(ctx: typer.Context) -> dict[str, str]:
    """The parsed address the group put on *ctx*."""
    return {key: ctx.obj[key] for key in ("id", "type", "address")}


def _finish[Req: BaseModel, Res](
    op: Operation[Req, Res],
    request: Req,
    json_out: bool,
    render: Callable[[Res, Console], None],
) -> None:
    """Make the command's one call, then print ``data`` with *json_out*, else *render* it."""
    response = calls.call(op, request)
    if json_out:
        calls.print_json(op, response)
    else:
        calls.print_warnings(response)
        render(response.data, console)
    calls.finish(response, json_out=json_out)


def _view_change(
    ctx: typer.Context,
    op: Operation[ItemViewRequest, ItemViewChanged],
    name: str,
    as_: str | None,
    *,
    json_out: bool,
    enable: bool,
) -> None:
    common.declare_actor(as_)

    def render(changed: ItemViewChanged, console: Console) -> None:
        render_view_change(
            changed.entry.id,
            changed.view,
            console,
            enable=enable,
            changed=changed.changed,
            was_present=changed.was_present,
        )

    _finish(op, ItemViewRequest(**_address(ctx), name=name), json_out, render)


def _subentity_comments(kind: str) -> common.CommentHost:
    """The discussion of a sub-entity of *kind*."""
    return common.CommentHost(
        add=ops.SUBENTITY_COMMENT_ADD,
        show=ops.SUBENTITY_COMMENT_SHOW,
        edit=ops.SUBENTITY_COMMENT_EDIT,
        removal=ops.SUBENTITY_COMMENT_REMOVAL,
        remove=ops.SUBENTITY_COMMENT_REMOVE,
        add_request=SubentityCommentAddRequest,
        hash_request=SubentityCommentRequest,
        edit_request=SubentityCommentEditRequest,
        address=lambda ctx: {**_address(ctx), "kind": kind, "local": ctx.obj["local"]},
    )


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

    A built-in type's sub-entity kind and its ``--<field-code>`` options come from the
    bundled spec. When the live spec renames the kind (``story`` -> ``scenario``)
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
    @handle_errors
    def _resolve(
        ctx: typer.Context,
        num: str = typer.Argument(..., metavar="N", help=f"Number or ID of the {item_type}."),
    ):
        ctx.obj = common.parsed_address(ctx, lambda: common.item_address(num, item_type))

    _cmd_show(item)
    _cmd_update(item, item_type, spec)
    _cmd_status(item)
    _cmd_body(item)
    common.register_comment_verbs(item, common.ITEM_COMMENTS)
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
    @handle_errors
    def show(
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
        response = calls.call(ops.ITEM_SHOW, ItemShowRequest(**_address(ctx)))
        if json_out:
            calls.print_json(ops.ITEM_SHOW, response)
        else:
            calls.print_warnings(response)
            render_show(response.data, console, raw=raw, comments=comments, full=full)
        calls.finish(response, json_out=json_out)


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
    @handle_errors
    def update(  # noqa: PLR0913 — the one metadata entry point
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
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the update."
        ),
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
        others = (
            title, desc, author, status, parent, no_parent, priority, no_priority,
            add_label, rm_label, set_, unset,
        )  # fmt: skip
        _guard_update(
            has_any=_anything_asked(*others, assignee, clear_assignee),
            assignee=assignee,
            clear_assignee=clear_assignee,
        )
        common.declare_actor(as_)
        request = ItemUpdateRequest(
            **_address(ctx),
            title=title,
            description=desc,
            author=author,
            status=parse_status(status) if status else None,
            force=force,
            parent=parent,
            clear_parent=no_parent,
            assignee=assignee,
            clear_assignee=clear_assignee,
            # No pre-parse: the collection `priority` binds is per-type, resolved by the operation
            # from this item's own declared field.
            priority=priority,
            clear_priority=no_priority,
            add_labels=add_label or [],
            rm_labels=rm_label or [],
            set_attributes=set_attributes,
            unset_attributes=unset or [],
        )
        _finish(ops.ITEM_UPDATE, request, json_out, render_updated)


def _cmd_status(item: typer.Typer) -> None:
    @item.command("status")
    @handle_errors
    def status(
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS", help=common.MOVE_STATUS_HELP),
        force: bool = common.force_transition_option(),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the move."
        ),
    ):
        """Move the item to another status."""
        common.declare_actor(as_)
        request = ItemStatusRequest(**_address(ctx), status=parse_status(new_status), force=force)
        response = calls.call(ops.ITEM_STATUS, request)
        if json_out:
            calls.print_json(ops.ITEM_STATUS, response)
        else:
            calls.print_warnings(response)
            render_status(response.data.entry, console)
        calls.finish(response, json_out=json_out)


def _cmd_body(item: typer.Typer) -> None:
    @item.command("body")
    @handle_errors
    def body(
        ctx: typer.Context,
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        append: bool = common.append_option(),
        force: bool = common.replace_body_option(),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the write."
        ),
    ):
        """Set or append to the item's body.

        Replacing a body someone has already written is refused unless `--force`; the
        refusal names what would be lost and writes nothing, so a bare `body` is a
        safe check. A first write over the template just works.
        """
        text = resolve_body(message or None, file)
        common.declare_actor(as_)
        request = ItemBodyRequest(**_address(ctx), text=text, append=append, force=force)
        _finish(
            ops.ITEM_BODY,
            request,
            json_out,
            lambda written, console: render_body_written(written.entry.id, console, append=append),
        )


def _cmd_retype(item: typer.Typer) -> None:
    @item.command("retype")
    @handle_errors
    def retype(
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
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row under its new type."
        ),
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
        common.declare_actor(as_)
        request = ItemRetypeRequest(**_address(ctx), target=target)
        _finish(ops.ITEM_RETYPE, request, json_out, render_retyped)


def _cmd_remove(item: typer.Typer) -> None:
    @item.command("remove")
    @handle_errors
    def remove(
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
        common.declare_actor(as_)
        if not yes:
            common.confirm(
                f"Remove {_address(ctx)['id']}? This cannot be undone.", json_out=json_out
            )
        request = ItemRemoveRequest(**_address(ctx), force=force)
        _finish(ops.ITEM_REMOVE, request, json_out, render_item_removed)


def _cmd_refs(item: typer.Typer) -> None:
    @item.command("refs")
    @handle_errors
    def refs(
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
        request = RefsRequest(
            **_address(ctx),
            out=out or all_ or not (incoming or all_),
            incoming=incoming or all_,
        )
        response = calls.call(ops.ITEM_REFS, request)
        if json_out:
            calls.print_json(ops.ITEM_REFS, response)
        else:
            calls.print_warnings(response)
            render_refs(response.data, console)
        calls.finish(response, json_out=json_out)

    ref_app = typer.Typer(no_args_is_help=True, help="Add or remove the item's refs.")

    @ref_app.command("add")
    @handle_errors
    def ref_add(
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
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the write."
        ),
    ):
        """Add a ref from this item to TARGET."""
        common.declare_actor(as_)
        request = ItemRefRequest(**_address(ctx), target=target, kind=kind)
        _finish(ops.ITEM_REF_ADD, request, json_out, render_ref_added)

    @ref_app.command("rm")
    @handle_errors
    def ref_rm(
        ctx: typer.Context,
        target: str = typer.Argument(..., help="Item ID or number."),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the write."
        ),
    ):
        """Remove this item's ref to TARGET."""
        common.declare_actor(as_)
        request = ItemRefRemoveRequest(**_address(ctx), target=target)
        _finish(ops.ITEM_REF_RM, request, json_out, render_ref_removed)

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
    @handle_errors
    def view_add(
        ctx: typer.Context,
        name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the change."
        ),
    ):
        """Show a declared view in the item's body, or re-enable it."""
        _view_change(ctx, ops.ITEM_VIEW_ADD, name, as_, json_out=json_out, enable=True)

    @view_app.command("disable")
    @handle_errors
    def view_disable(
        ctx: typer.Context,
        name: str = typer.Argument(
            ..., help="View name; it need not be declared, so a dropped view can be turned off."
        ),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the item's row after the change."
        ),
    ):
        """Stop showing a view in the item's body; its tag stays, disabled."""
        _view_change(ctx, ops.ITEM_VIEW_DISABLE, name, as_, json_out=json_out, enable=False)

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


def _doc[F: Callable[..., object]](text: str) -> Callable[[F], F]:
    """Give a generated command the help text its kind's labels spell out."""

    def apply(fn: F) -> F:
        fn.__doc__ = text
        return fn

    return apply


def _register_subentity(item: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    plural = spec.subentity_plural(kind)

    @item.command(plural)
    @handle_errors
    @_doc(f"List this item's {plural}.")
    def list_sub(
        ctx: typer.Context,
        json_out: bool = typer.Option(
            False, "--json", help=f"Print a JSON array, one object per {kind}."
        ),
    ):
        request = SubentitiesRequest(**_address(ctx), kind=kind)
        response = calls.call(ops.ITEM_SUBENTITIES, request)
        if json_out:
            calls.print_json(ops.ITEM_SUBENTITIES, response)
        else:
            calls.print_warnings(response)
            render_subentities(response.data, console)
        calls.finish(response, json_out=json_out)

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


def _given_fields(kind: str, spec: WorkflowSpec, kwargs: dict[str, object]) -> dict[str, str]:
    """The badge code given for each declared field, checked against its collection; an omitted
    field is left to the operation, which applies its default."""
    values: dict[str, str] = {}
    for field in spec.fields_for(kind):
        raw = _kw_str(kwargs, field.code)
        if raw is not None:
            coll = badges.resolve_collection(kind, field.code, spec)
            values[field.code] = parse_badge_code(coll, raw, spec)
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

    def _add(**kwargs: object) -> None:
        ctx = cast(typer.Context, kwargs["ctx"])
        story = _kw_str(kwargs, "story")
        status = _kw_str(kwargs, "status")
        message = _kw_list(kwargs, "message")
        request = SubentityAddRequest(
            **_address(ctx),
            kind=kind,
            title=cast(str, kwargs["title"]),
            # Story-mapping semantics stay wired to the built-in "story" kind regardless of which
            # kind declares maps_parent_story: a bounded built-in, not per-kind.
            story=resolve_local_id(story, "story") if story else None,
            fields=_given_fields(kind, spec, kwargs),
            assignee=_kw_str(kwargs, "assignee"),
            status=parse_status(status) if status else None,
            deferred_to=_kw_str(kwargs, "deferred_to"),
            body=resolve_body_optional(message or None, _kw_str(kwargs, "file")),
        )
        common.declare_actor(_kw_str(kwargs, "as_"))
        _finish(ops.SUBENTITY_ADD, request, _kw_bool(kwargs, "json_out"), render_subentity_added)

    _add.__doc__ = f"Scaffold {common.article(kind)} {kind} on this item."
    _add.__signature__ = inspect.Signature(params)  # pyright: ignore[reportFunctionMemberAccess]
    item.command(f"add-{kind}")(handle_errors(_add))


def _register_update(sub: typer.Typer, kind: str, spec: WorkflowSpec) -> None:
    """The sub-entity metadata entry point — one ``--<field-code>`` option per declared field
    (identically to ``add-<kind>``) + ``--story``/``--no-story`` iff maps_parent_story."""
    ks = spec.subentity_kinds[kind]
    fields = spec.fields_for(kind)

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
        inspect.Parameter(
            "json_out",
            inspect.Parameter.KEYWORD_ONLY,
            default=typer.Option(
                False, "--json", help=f"Print one JSON object: the {kind} after the update."
            ),
            annotation=bool,
        ),
    ]

    def _update(**kwargs: object) -> None:
        ctx = cast(typer.Context, kwargs["ctx"])
        title = _kw_str(kwargs, "title")
        story = _kw_str(kwargs, "story")
        no_story = _kw_bool(kwargs, "no_story")
        assignee = _kw_str(kwargs, "assignee")
        clear_assignee = _kw_bool(kwargs, "clear_assignee")
        status = _kw_str(kwargs, "status")
        field_values = _given_fields(kind, spec, kwargs)
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
        common.declare_actor(_kw_str(kwargs, "as_"))
        request = SubentityUpdateRequest(
            **_address(ctx),
            kind=kind,
            local=ctx.obj["local"],
            title=title,
            fields=field_values,
            story=resolve_local_id(story, "story") if story else None,
            clear_story=no_story,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=parse_status(status) if status else None,
            deferred_to=_kw_str(kwargs, "deferred_to"),
            force=_kw_bool(kwargs, "force"),
        )

        def render(updated: SubentityUpdated, console: Console) -> None:
            label = f"{ctx.obj['id']} {updated.entry.local_id}"
            if updated.nothing_to_clear:
                console.print(f"{label} has no assignee to clear")
            else:
                console.print(f"updated {label}")

        _finish(ops.SUBENTITY_UPDATE, request, _kw_bool(kwargs, "json_out"), render)

    _update.__doc__ = f"Change the {kind}'s title, status, assignee or declared fields."
    _update.__signature__ = inspect.Signature(params)  # pyright: ignore[reportFunctionMemberAccess]
    sub.command("update")(handle_errors(_update))


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
    @sub.command("show")
    @handle_errors
    @_doc(f"Show the {kind}'s status, assignee, body and discussion.")
    def s_show(
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json", help=f"Print one JSON object: the {kind}."),
    ):
        request = SubentityRequest(**_address(ctx), kind=kind, local=ctx.obj["local"])
        response = calls.call(ops.ITEM_SUBENTITY, request)
        if json_out:
            calls.print_json(ops.ITEM_SUBENTITY, response)
        else:
            calls.print_warnings(response)
            render_subentity(response.data, console)
        calls.finish(response, json_out=json_out)

    _register_update(sub, kind, spec)

    @sub.command("body")
    @handle_errors
    @_doc(
        f"Set or append to the {kind}'s body.\n\n"
        "Replacing a body someone has already written is refused unless `--force`."
    )
    def s_body(
        ctx: typer.Context,
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        append: bool = common.append_option(),
        force: bool = common.replace_body_option(),
        as_: str | None = common.edit_as_option(),
        json_out: bool = typer.Option(
            False, "--json", help=f"Print one JSON object: the {kind} after the write."
        ),
    ):
        text = resolve_body(message or None, file)
        common.declare_actor(as_)
        request = SubentityBodyRequest(
            **_address(ctx),
            kind=kind,
            local=ctx.obj["local"],
            text=text,
            append=append,
            force=force,
        )
        label = f"{ctx.obj['id']} {ctx.obj['local']}"
        _finish(
            ops.SUBENTITY_BODY,
            request,
            json_out,
            lambda _, console: console.print(f"{label}: body {'appended' if append else 'set'}"),
        )

    common.register_comment_group(sub, _subentity_comments(kind))

    @sub.command("remove")
    @handle_errors
    @_doc(_remove_help(kind, spec))
    def s_remove(
        ctx: typer.Context,
        yes: bool = common.yes_option(),
        json_out: bool = typer.Option(
            False, "--json", help=f"Print one JSON object naming the removed {kind}."
        ),
        as_: str | None = common.edit_as_option(),
    ):
        common.declare_actor(as_)
        if not yes:
            common.confirm(
                f"Remove {kind} {ctx.obj['local']} from {ctx.obj['id']}? This cannot be undone.",
                json_out=json_out,
            )
        request = SubentityRemoveRequest(**_address(ctx), kind=kind, local=ctx.obj["local"])
        _finish(ops.SUBENTITY_REMOVE, request, json_out, render_subentity_removed)
