"""`sq create <type> TITLE …` — one command per item type, sharing one implementation.

Built-in types are registered statically at import time; custom types declared in
``.overrides/workflow.toml`` are dispatched lazily by ``_CustomCreateGroup``, which resolves the
active spec at Click dispatch time, after the root callback has bound it.
"""

import contextlib
from typing import Any, ClassVar

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main

import squads._cli._common as common
import squads._cli._field_options as field_options
from squads._api import _ops as ops
from squads._api._dto._item_writes import ItemCreateRequest
from squads._cli import _calls as calls
from squads._cli._common import console, resolve_body_optional
from squads._cli._render._writes import render_created
from squads._errors import SquadsError
from squads._models._attributes import AttributeSpec
from squads._workflow import bundled_spec


def _check_parent_option(parent: str | None) -> None:
    """Refuse an empty or whitespace-only ``--parent``, the single parent door of every
    ``sq create`` command: ``--parent ""`` is a supplied value, and creating a parentless item
    from it would be silent. ``create`` has no ``--no-parent``: omitting ``--parent`` is how a
    parentless item is made."""
    if parent is not None and not parent.strip():
        raise SquadsError("--parent needs an item ID; omit --parent to create without a parent")


def _create(request: ItemCreateRequest, json_out: bool) -> None:
    """Make the one create call, then print the created item."""
    response = calls.call(ops.ITEMS_CREATE, request)
    if json_out:
        calls.print_json(ops.ITEMS_CREATE, response)
    else:
        calls.print_warnings(response)
        render_created(response.data, console)
    calls.finish(response, json_out=json_out)


def _declared_field_options(item_type: str, taken: set[str]) -> list[typer.core.TyperOption]:
    """One ``--<field-code>`` option per field *item_type* declares in the active spec, skipping
    the codes whose option already exists."""
    spec = common.get_active_spec()
    return [
        field_options.value_option(
            f, field_options.field_help(f, field_options.field_codes(f, spec))
        )
        for f in spec.fields_for(item_type)
        if field_options.flag_name(f.code) not in taken
    ]


#: The attribute kinds a create option is derived for.
CREATE_ATTRIBUTE_KINDS = ("str", "list", "date")

#: ``Context.meta`` key under which the declared-attribute options file the values they receive.
_ATTRIBUTES_META_KEY = "squads.create_attributes"


def attribute_flag(name: str) -> str:
    """The option name of attribute *name*: its key with dashes (``target_date`` is
    ``--target-date``)."""
    return name.replace("_", "-")


def _attribute_option(
    item_type: str, name: str, spec: AttributeSpec, flag: str
) -> typer.core.TyperOption:
    def _remember(ctx: _click.Context, _param: _click.Parameter, value: Any) -> None:
        if value:
            ctx.meta.setdefault(_ATTRIBUTES_META_KEY, {})[name] = (
                list(value) if spec.kind == "list" else value
            )

    label = spec.label or name.replace("_", " ")
    many = spec.kind == "list"
    return typer.core.TyperOption(
        param_decls=[f"--{flag}", f"attribute_{name}"],
        default=None,
        multiple=many,
        help=f"{item_type} attribute: {label}{' (repeatable)' if many else ''}.",
        expose_value=False,
        callback=_remember,
    )


def _declared_attribute_options(item_type: str, taken: set[str]) -> list[typer.core.TyperOption]:
    """One option per settable ``str``, ``list`` or ``date`` attribute *item_type* declares,
    skipping a flag that is already taken."""
    options: list[typer.core.TyperOption] = []
    for name, spec in common.get_active_spec().item_attributes(item_type).items():
        flag = attribute_flag(name)
        if spec.settable and spec.kind in CREATE_ATTRIBUTE_KINDS and flag not in taken:
            options.append(_attribute_option(item_type, name, spec, flag))
            taken.add(flag)
    return options


def _create_command_cls(item_type: str) -> type[typer.core.TyperCommand]:
    """The command class for ``sq create <item_type>``: its ``--help`` and its options follow
    the live spec, so a field an override declares is settable by its code like a bundled one.

    The options are added in ``get_params``, which Click runs for parsing and for ``--help``
    alike, after the per-invocation spec is bound. Fail-soft for the reason
    :func:`common.spec_aware_command_cls` documents.
    """

    class _CreateCommand(typer.core.TyperCommand):
        def get_params(self, ctx: Any) -> list[Any]:
            params = super().get_params(ctx)
            with contextlib.suppress(Exception):
                taken = {
                    opt.removeprefix("--") for p in params for opt in (*p.opts, *p.secondary_opts)
                }
                params = field_options.extended(
                    params,
                    [
                        *_declared_field_options(item_type, taken),
                        *_declared_attribute_options(item_type, taken),
                    ],
                )
            return params

    return _CreateCommand


def _given_attributes(ctx: typer.Context) -> dict[str, str | list[str]]:
    """The values the declared-attribute options received, keyed by attribute name."""
    return dict(ctx.meta.get(_ATTRIBUTES_META_KEY, {}))


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
        help=f"Create one new {item_type_str}.",
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
# one generic `_make` per creatable type, in ItemSpec.order; role/skill/operator are roster types
# with dedicated commands.
_create_spec = bundled_spec()
_CREATABLE: tuple[str, ...] = tuple(
    t
    for t in sorted(_create_spec.non_roster_types(), key=lambda t: (_create_spec.items[t].order, t))
)


def _make(item_type_str: str):
    @common.handle_errors
    def cmd(  # noqa: PLR0913 — Typer options are the command's surface
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
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the created item."
        ),
    ):
        _check_parent_option(parent)
        request = ItemCreateRequest(
            type=item_type_str,
            title=title,
            author=author,
            parent=parent,
            description=desc,
            labels=label or [],
            refs=ref or [],
            assignee=assignee,
            fields=field_options.given_values(ctx),
            attributes=_given_attributes(ctx),
            body=resolve_body_optional(message or None, file),
        )
        _create(request, json_out)

    cmd.__name__ = f"create_{item_type_str}"
    return cmd


for _t in _CREATABLE:
    create_app.command(
        _t,
        help=f"Create one new {_t}.",
        cls=_create_command_cls(_t),
    )(_make(_t))

# Hidden aliases from the bundled spec, so `sq create feat TITLE` dispatches like
# `sq create feature TITLE`; hidden keeps them out of --help.
for _t in _CREATABLE:
    for _alias in _create_spec.items[_t].aliases:
        create_app.command(_alias, hidden=True, cls=_create_command_cls(_t))(_make(_t))

# Type names with a static `sq create <type>` command already registered above — used by
# _CustomCreateGroup to draw the line between "already known" and "resolve dynamically".
_STATIC_CREATE_TYPES: frozenset[str] = frozenset(_CREATABLE)
