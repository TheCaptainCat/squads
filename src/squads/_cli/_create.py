"""`sq create <type> TITLE …` — one command per item type, sharing one implementation.

Built-in types are registered statically at import time; custom types declared in
``.overrides/workflow.toml`` are dispatched lazily by ``_CustomCreateGroup``, which resolves the
active spec at Click dispatch time, after the root callback has bound it.
"""

import contextlib
import json
from collections.abc import Callable
from typing import Any, ClassVar

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main

import squads._cli._common as common
from squads import _actor as actor
from squads import _badges as badges
from squads._cli._common import (
    console,
    e,
    get_service,
    print_json_clean,
    resolve_body_optional,
    resolve_item_id_any,
    resolve_slug_or_raise,
)
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._models._item import make_ref, split_ref
from squads._services._service import Service
from squads._workflow import bundled_spec
from squads._workflow._models import Field, WorkflowSpec


async def _resolve_parent_option(parent: str | None, svc: Service) -> str | None:
    """Resolve a create command's ``--parent`` option to a full item ID, or ``None``.

    The single parent door for every ``sq create`` command (built-in, custom and ``guide``). It
    tests ``is not None``, not truthiness: ``--parent ""`` is a supplied value, and an empty or
    whitespace-only one is refused here rather than silently creating a parentless item.
    ``create`` has no ``--no-parent``: omitting ``--parent`` is how a parentless item is made.
    """
    if parent is None:
        return None
    if not parent.strip():
        raise SquadsError("--parent needs an item ID; omit --parent to create without a parent")
    return await resolve_item_id_any(parent, svc)


def _priority_help(item_type: str) -> str:
    """``--priority`` help for ``create <item_type>``, from the collection *item_type* binds.

    Read at registration time this is the bundled spec; statically registered commands re-derive
    it at ``--help`` render time through :func:`common.spec_aware_command_cls`. It resolves
    strictly (:func:`squads._badges.declared_collection`): a type declaring no ``priority`` field
    enumerates nothing and the flag is hidden (see :func:`_refresh_priority_help`).
    """
    spec = common.get_active_spec()
    # sanctioned field-code literal: `--priority` is the flag *for* this field code
    coll_code = badges.declared_collection(item_type, "priority", spec)
    coll = spec.collections.get(coll_code) if coll_code else None
    if coll and coll.badges:
        return f"Priority: {'|'.join(b.code for b in coll.badges)}."
    return "Priority code (as defined by your workflow's priority collection)."


def _refresh_priority_help(item_type_str: str) -> Callable[[list[object]], None]:
    """A spec_aware_command_cls refresh re-deriving --priority's help from the live spec.

    On a type declaring no ``priority`` field the flag is hidden from ``--help`` but still
    parses, so the service's declared-field gate (``ServiceCore._check_priority``) owns the one
    accurate refusal.
    """

    def _refresh(params: list[object]) -> None:
        text = _priority_help(item_type_str)
        # sanctioned field-code literal: `--priority` is the flag *for* this field code
        declared = (
            badges.declared_collection(item_type_str, "priority", common.get_active_spec())
            is not None
        )
        for p in params:
            if getattr(p, "name", None) == "priority":
                p.help = text  # type: ignore[attr-defined]
                p.hidden = not declared  # type: ignore[attr-defined]

    return _refresh


def _field_help(item_type: str, field: Field, spec: WorkflowSpec) -> str:
    """``--<field-code>`` help for *field* on *item_type*: its label and the codes of the
    collection it binds."""
    coll = spec.collections.get(field.collection)
    if coll and coll.badges:
        return f"{field.label}: {'|'.join(b.code for b in coll.badges)}."
    return f"{field.label} badge code."


#: ``Context.meta`` key under which the declared-field options file the values they receive.
_FIELDS_META_KEY = "squads.create_fields"


def _remember_field(ctx: _click.Context, param: _click.Parameter, value: str | None) -> None:
    """Option callback: file *value* under its field code. The options are added per
    invocation, so the command function has no parameter to receive them."""
    if value is not None and param.name is not None:
        ctx.meta.setdefault(_FIELDS_META_KEY, {})[param.name] = value


def _declared_field_options(item_type: str, taken: set[str]) -> list[typer.core.TyperOption]:
    """One ``--<field-code>`` option per field *item_type* declares in the active spec, skipping
    the codes whose option already exists (``--priority`` is a static option)."""
    spec = common.get_active_spec()
    return [
        typer.core.TyperOption(
            param_decls=[f"--{f.code}", f.code],
            default=None,
            help=_field_help(item_type, f, spec),
            expose_value=False,
            callback=_remember_field,
        )
        for f in spec.fields_for(item_type)
        if f.code not in taken
    ]


def _create_command_cls(item_type: str) -> type[typer.core.TyperCommand]:
    """The command class for ``sq create <item_type>``: its ``--help`` and its options follow
    the live spec, so a field an override declares is settable by its code like a bundled one.

    The options are added in ``get_params``, which Click runs for parsing and for ``--help``
    alike, after the per-invocation spec is bound. Fail-soft for the reason
    :func:`common.spec_aware_command_cls` documents.
    """
    base = common.spec_aware_command_cls(_refresh_priority_help(item_type))

    class _CreateCommand(base):
        def get_params(self, ctx: Any) -> list[Any]:
            params = super().get_params(ctx)
            with contextlib.suppress(Exception):
                taken = {
                    opt.removeprefix("--") for p in params for opt in (*p.opts, *p.secondary_opts)
                }
                params = [*params, *_declared_field_options(item_type, taken)]
            return params

    return _CreateCommand


def _given_fields(ctx: typer.Context) -> dict[str, str] | None:
    """The values the declared-field options received, keyed by field code; ``None`` when none
    was given."""
    return dict(ctx.meta.get(_FIELDS_META_KEY, {})) or None


def _build_create_cmd(item_type_str: str) -> _click.Command:
    """Build a Click command for ``sq create <item_type_str> TITLE …``, for ``_CustomCreateGroup``.

    Registers the function in a temporary Typer app, converts it to a Click group and extracts
    the named subcommand, so ``incident`` is a leaf command rather than another group.
    """
    # With exactly one command, ``typer.main.get_command`` returns the command itself, not a
    # group, so ``TITLE`` dispatches as its argument.
    _tmp_app = typer.Typer()
    _tmp_app.command(
        item_type_str,
        help=f"Create {common.article(item_type_str)} {item_type_str}.",
        cls=_create_command_cls(item_type_str),
    )(_make(item_type_str))
    leaf: _click.Command = typer.main.get_command(_tmp_app)  # type: ignore[assignment]
    leaf.name = item_type_str
    return leaf


class _CustomCreateGroup(typer.core.TyperGroup):
    """Typer group that lazily builds ``sq create <custom-type>`` for types the spec declares.

    Built-in types are registered statically by the loop at the bottom of this file. Unlike
    ``_CustomTypeGroup`` (the ``sq <type> <num> <verb>`` groups) it handles only the create
    entry; both read the spec bound once per invocation by ``common.bind_active_spec``. Its
    ``_custom_cmd_cache`` is a ``ClassVar`` keyed on the spec each command was built for.
    """

    _custom_cmd_cache: ClassVar[common.SpecKeyedCache[_click.Command]] = common.SpecKeyedCache()

    def _dropped_static_names(self, ctx: Any) -> frozenset[str]:
        """Static command and alias names whose built-in type the resolved spec dropped.

        Resolves via ``common.resolve_spec_for_ctx`` because the completion path never runs the root
        callback. Advertising only: ``get_command`` does not consult this set, so the command still
        dispatches into ``svc.create``, whose membership gate is the one ``[selected]``-aware
        refusal; a hidden name would fall to Click's did-you-mean, which suggests the string just
        typed. Any resolution error returns the empty set.
        """
        try:
            spec = common.resolve_spec_for_ctx(ctx)
        except Exception:  # pylint: disable=broad-except
            return frozenset()
        # Stale aliases are refused by get_command, so they must not stay listed either —
        # Click's did-you-mean reads this list (see the root group's own note).
        dropped: set[str] = set(common.stale_static_aliases(spec))
        for name in _STATIC_CREATE_TYPES:
            if name not in spec.items:
                dropped.add(name)
                dropped.update(
                    alias
                    for alias, canonical in _create_spec.alias_to_type.items()
                    if canonical == name
                )
        return frozenset(dropped)

    def _custom_non_roster_types(self, ctx: Any) -> frozenset[str]:
        """Non-roster type names the resolved spec adds beyond ``_STATIC_CREATE_TYPES``.

        Resolves via ``common.resolve_spec_for_ctx`` like :meth:`_dropped_static_names`; empty on
        error.
        """
        try:
            spec = common.resolve_spec_for_ctx(ctx)
            return frozenset(t for t in spec.non_roster_types() if t not in _STATIC_CREATE_TYPES)
        except Exception:  # pylint: disable=broad-except
            return frozenset()

    def list_commands(self, ctx: Any) -> list[str]:
        """Built-in commands first, then custom non-roster types alphabetically."""
        dropped = self._dropped_static_names(ctx)
        base: list[str] = [c for c in super().list_commands(ctx) if c not in dropped]
        custom = sorted(self._custom_non_roster_types(ctx))
        return base + custom

    def _canonical_for(self, ctx: Any, cmd_name: str) -> str | None:
        """The declared non-roster type *cmd_name* names, directly or via an alias — or
        ``None`` when it names none, so Click emits "No such command".

        Errors here (invalid spec, missing active spec, etc.) are swallowed so that
        ``sq create --help`` always degrades gracefully.
        """
        try:
            if cmd_name in _STATIC_CREATE_TYPES:
                return None

            # resolve_spec_for_ctx (not get_active_spec) so this also sees the override on
            # the completion path, where the root callback hasn't run.
            spec = common.resolve_spec_for_ctx(ctx)

            # Alias → canonical, as in _CustomTypeGroup.get_command. The type may be static:
            # an override can give a bundled type a new alias the import-time loop never saw,
            # and `sq create ft` must reach the command `sq ft` does.
            canonical = cmd_name
            if cmd_name not in spec.non_roster_types():
                resolved = spec.alias_to_type.get(cmd_name)
                if resolved is None or resolved not in spec.non_roster_types():
                    return None
                canonical = resolved
            return None if spec.item_is_roster(canonical) else canonical
        except Exception:  # pylint: disable=broad-except
            # Spec resolution failed — degrade gracefully.
            return None

    def get_command(self, ctx: Any, cmd_name: str) -> _click.Command | None:
        # A bundled alias the active spec no longer declares must not dispatch here either —
        # `sq create feat TITLE` is the same stale-alias hazard as `sq feat 9 show`, one level
        # down (see `common.static_alias_is_stale`).
        if common.static_alias_is_stale(ctx, cmd_name):
            return common.stale_alias_command(ctx, cmd_name)

        # Fast path: the static commands, including one whose type the spec dropped (see
        # _dropped_static_names): it dispatches to `svc.create`, whose membership gate names
        # the type as dropped rather than as a typo.
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        canonical = self._canonical_for(ctx, cmd_name)
        if canonical is None:
            # A name this squad may well declare, on a squad whose override did not load —
            # `sq create widget "x"` must not answer "No such command" from bundled vocabulary
            # any more than `sq widget 19 show` does. `None` whenever the spec is healthy.
            return common.spec_error_command(cmd_name, ctx)

        # Past this point canonical IS a declared custom work type.  Build errors here are
        # genuine failures for a type the user declared (and that --help lists), so they
        # must propagate rather than silently become "No such command".
        spec = common.resolve_spec_for_ctx(ctx)
        cached = self._custom_cmd_cache.get(canonical, spec)
        if cached is not None:
            return cached
        return self._custom_cmd_cache.put(canonical, spec, _build_create_cmd(canonical))


create_app = typer.Typer(
    no_args_is_help=True,
    help="Create a tracked item.",
    cls=_CustomCreateGroup,
)

# Static registration from the bundled spec, like the resource-group loop in _cli/__init__.py:
# one generic `_make` per creatable type, in ItemSpec.order. `guide` gets its own command below
# (--tech/--tag); role/skill/operator are roster types with dedicated commands.
_create_spec = bundled_spec()
_CREATABLE: tuple[str, ...] = tuple(
    t
    for t in sorted(_create_spec.non_roster_types(), key=lambda t: (_create_spec.items[t].order, t))
    if t != "guide"
)


def _make(item_type_str: str):
    @common.command
    async def cmd(  # noqa: PLR0913 — Typer options are the command's surface
        ctx: typer.Context,
        title: str = typer.Argument(..., help="Item title."),
        author: str = common.author_option(),
        parent: str | None = common.parent_option(),
        desc: str = common.desc_option(),
        label: list[str] = common.label_option(),
        ref: list[str] = typer.Option(
            None, "--ref", help="Item to ref, as `ID` or `ID:kind` (repeatable)."
        ),
        assignee: str | None = common.assignee_option(),
        priority: str | None = typer.Option(None, "--priority", help=_priority_help(item_type_str)),
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the created item."
        ),
    ):
        svc = get_service()
        # --author/--assignee accept only a live slug: a retired role stops being
        # an active participant, though its past authorship stays readable.
        validated_author = await resolve_slug_or_raise(author, svc)
        actor.set_actor(validated_author)
        validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
        resolved_parent = await _resolve_parent_option(parent, svc)
        resolved_refs: list[str] | None = None
        if ref:
            resolved_refs = []
            for r in ref:
                rid, kind = split_ref(r)
                resolved_refs.append(make_ref(await resolve_item_id_any(rid, svc), kind))
        res = await svc.create(
            item_type_str,
            title,
            description=desc,
            parent=resolved_parent,
            author=validated_author,
            labels=label or None,
            refs=resolved_refs,
            assignee=validated_assignee,
            # No pre-parse: the collection `priority` binds is per-type, and the service's
            # `_check_priority` resolves it from the type's own declared field.
            priority=priority,
            fields=_given_fields(ctx),
            body=resolve_body_optional(message or None, file),
        )
        if json_out:
            data = res.item.to_row()
            if res.lane_warning is not None:
                data["lane_warning"] = res.lane_warning
            print_json_clean(json.dumps(data))
        else:
            console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
            if res.lane_warning is not None:
                console.print(e(res.lane_warning))

    cmd.__name__ = f"create_{item_type_str}"
    return cmd


for _t in _CREATABLE:
    create_app.command(
        _t,
        help=f"Create {common.article(_t)} {_t}.",
        cls=_create_command_cls(_t),
    )(_make(_t))

# Hidden aliases from the bundled spec, so `sq create feat TITLE` dispatches like
# `sq create feature TITLE`; hidden keeps them out of --help.
for _t in _CREATABLE:
    for _alias in _create_spec.items[_t].aliases:
        create_app.command(_alias, hidden=True, cls=_create_command_cls(_t))(_make(_t))

# Type names with a static `sq create <type>` command already registered above — used by
# _CustomCreateGroup to draw the line between "already known" and "resolve dynamically".
_STATIC_CREATE_TYPES: frozenset[str] = frozenset({*_CREATABLE, "guide"})


@create_app.command("guide", help="Create a guide.")
@common.command
async def create_guide(  # noqa: PLR0913 — Typer options are the command's surface
    title: str = typer.Argument(..., help="Guide title."),
    author: str = common.author_option(),
    tech: str | None = common.tech_option(),
    tag: list[str] = typer.Option(None, "--tag", help="Tag to add (repeatable)."),
    parent: str | None = common.parent_option(),
    desc: str = common.desc_option(),
    assignee: str | None = common.assignee_option(),
    message: list[str] = common.message_option(),
    file: str | None = common.file_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the created item."),
):
    attributes: dict[str, object] = {}
    if tech:
        attributes[AttributeKey.TECH] = tech
    if tag:
        attributes[AttributeKey.TAGS] = list(tag)
    svc = get_service()
    # --author/--assignee accept only a live slug: a retired role stops being an
    # active participant, though its past authorship stays readable.
    validated_author = await resolve_slug_or_raise(author, svc)
    actor.set_actor(validated_author)
    validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
    resolved_parent = await _resolve_parent_option(parent, svc)
    res = await svc.create(
        "guide",
        title,
        description=desc,
        parent=resolved_parent,
        author=validated_author,
        assignee=validated_assignee,
        attributes=attributes or None,
        body=resolve_body_optional(message or None, file),
    )
    if json_out:
        data = res.item.to_row()
        if res.lane_warning is not None:
            data["lane_warning"] = res.lane_warning
        print_json_clean(json.dumps(data))
    else:
        console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
        if res.lane_warning is not None:
            console.print(e(res.lane_warning))


# Hidden guide aliases (same pattern as _CREATABLE loop above).
for _guide_alias in _create_spec.items["guide"].aliases:
    create_app.command(_guide_alias, hidden=True)(create_guide)
