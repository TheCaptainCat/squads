"""`sq create <type> TITLE …` — one command per item type, sharing one implementation.

Built-in types are registered statically at import time (unchanged from before).
Custom types declared in ``.overrides/workflow.toml`` are dispatched lazily by
``_CustomCreateGroup``, which follows the same pattern as ``_CustomTypeGroup`` in
``_cli/__init__.py``.  Startup ordering: ``_CustomCreateGroup``
resolves the active spec via ``common.get_active_spec()`` at Click dispatch time
(``get_command`` / ``list_commands``), after ``_bind_active_spec`` has already run in
the root callback — so the same spec that the resource groups see is also visible here.
"""

import json
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
    parse_badge_code,
    print_json_clean,
    resolve_body_optional,
    resolve_item_id_any,
)
from squads._models._extras import ExtraKey as X
from squads._models._item import make_ref, split_ref
from squads._workflow import bundled_spec


def _priority_help(item_type: str) -> str:
    """``--priority`` help text for ``create <item_type>``, derived from the priority
    collection bound to *item_type* in the resolved active spec (bundled spec for the
    statically-registered types, since it's read before ``_bind_active_spec`` runs at
    import time — byte-identical to the previous hardcoded text there)."""
    spec = common.get_active_spec()
    coll_code = badges.resolve_collection(item_type, "priority", spec)
    coll = spec.collections.get(coll_code)
    if coll and coll.badges:
        return f"Priority: {'|'.join(b.code for b in coll.badges)}."
    return "Priority code (as defined by your workflow's priority collection)."


def _build_create_cmd(item_type_str: str) -> _click.Command:
    """Build a Click command for ``sq create <item_type_str> TITLE …``.

    Used by ``_CustomCreateGroup`` to lazily build per-custom-type create commands.
    The approach mirrors the static ``_make`` / ``create_app.command(...)`` path:
    register the function in a temporary Typer app as a named command, convert the
    app to a Click group, then extract the named subcommand so the caller gets a
    ``click.Command`` (not a group).  This way ``sq create incident TITLE`` dispatches
    correctly — ``incident`` is a leaf command, not another group.
    """

    @common.command
    async def _cmd(  # noqa: PLR0913 — Typer options are the command's surface
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
        priority: str | None = typer.Option(None, "--priority", help=_priority_help(item_type_str)),
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
            item_type_str,
            title,
            description=desc,
            parent=resolved_parent,
            author=author,
            labels=label or None,
            refs=resolved_refs,
            assignee=assignee,
            priority=parse_badge_code("priority", priority) if priority else None,
            body=resolve_body_optional(message or None, file),
        )
        if json_out:
            data = json.loads(res.item.model_dump_json())
            if res.lane_warning is not None:
                data["lane_warning"] = res.lane_warning
            print_json_clean(json.dumps(data))
        else:
            console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
            if res.lane_warning is not None:
                console.print(e(res.lane_warning))

    _cmd.__name__ = f"create_{item_type_str}"

    # Register the function as the sole command in a fresh Typer app.  When there is
    # exactly one command, ``typer.main.get_command`` returns the command directly (a
    # ``TyperCommand``, which is a ``click.Command``), not a group — so the caller gets a
    # leaf command.  This ensures ``sq create incident TITLE`` dispatches ``TITLE`` as
    # an argument to the command, not as a subcommand of a group.
    _tmp_app = typer.Typer()
    _tmp_app.command(item_type_str, help=f"Create a {item_type_str}.")(_cmd)
    leaf: _click.Command = typer.main.get_command(_tmp_app)  # type: ignore[assignment]
    leaf.name = item_type_str
    return leaf


class _CustomCreateGroup(typer.core.TyperGroup):
    """Typer group that lazily dispatches ``sq create <custom-type>`` commands.

    Built-in types are registered statically by the loop at the bottom of this file
    (unchanged, byte-identical to the previous implementation for non-custom squads).
    When Click calls ``get_command(ctx, name)`` for an *unknown* name, this group
    checks whether the resolved spec declares that name as a custom work type and, if
    so, builds and returns a per-type create command on the fly.

    Reconciliation with ``_CustomTypeGroup`` (root-level resource groups):
    - ``_CustomTypeGroup`` handles ``sq <type> <num> <verb>`` (resource operations).
    - ``_CustomCreateGroup`` handles only ``sq create <type> TITLE`` (creation entry).
    - Both call ``common.get_active_spec()`` which is bound once per invocation by
      ``_bind_active_spec`` in the root callback, so they always see the same spec.
    - The ``_custom_cmd_cache`` is scoped to this class (``ClassVar``), independent of
      the resource-group cache, so the two caches do not interfere.
    """

    _custom_cmd_cache: ClassVar[dict[str, _click.Command]] = {}

    def _custom_work_types(self) -> frozenset[str]:
        """Return custom work type names from the resolved spec.

        "Custom" here means "not already registered by the static import-time loop"
        (``_STATIC_CREATE_TYPES``) — i.e. anything a project's own workflow override adds
        on top of the bundled spec. Safe to call at any time; returns the empty set on any
        error.
        """
        try:
            spec = common.get_active_spec()
            return frozenset(t for t in spec.work_types() if t not in _STATIC_CREATE_TYPES)
        except Exception:  # pylint: disable=broad-except
            return frozenset()

    def list_commands(self, ctx: Any) -> list[str]:
        """Built-in commands first, then custom work types alphabetically.

        For a non-custom squad the custom set is empty, so this is byte-identical
        to the previous implementation (AC#7/#8).
        """
        base: list[str] = super().list_commands(ctx)
        custom = sorted(self._custom_work_types())
        return base + custom

    def get_command(self, ctx: Any, cmd_name: str) -> _click.Command | None:
        # Fast path: try the statically-built built-in commands first (canonical + hidden aliases).
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Spec-resolution region: decide whether cmd_name is a known custom work type or alias.
        # Errors here (invalid spec, missing active spec, etc.) are swallowed so that
        # `sq create --help` always degrades gracefully.  The only valid outcome is either
        # (a) cmd_name confirmed (or resolved via alias) as a declared custom work type, or
        # (b) return None so Click emits "No such command".
        try:
            if cmd_name in _STATIC_CREATE_TYPES:
                return None

            spec = common.get_active_spec()

            # Resolve alias → canonical for custom types (mirrors _CustomTypeGroup.get_command).
            canonical = cmd_name
            if cmd_name not in spec.work_types():
                resolved = spec.alias_to_type.get(cmd_name)
                if (
                    resolved is not None
                    and resolved in spec.work_types()
                    and resolved not in _STATIC_CREATE_TYPES
                ):
                    canonical = resolved
                else:
                    return None
            if spec.item_is_meta(canonical):
                return None
        except Exception:  # pylint: disable=broad-except
            # Spec resolution failed — degrade gracefully.
            return None

        # Past this point canonical IS a declared custom work type.  Build errors here are
        # genuine failures for a type the user declared (and that --help lists), so they
        # must propagate rather than silently become "No such command".
        if canonical not in self._custom_cmd_cache:
            self._custom_cmd_cache[canonical] = _build_create_cmd(canonical)

        return self._custom_cmd_cache.get(canonical)


create_app = typer.Typer(
    no_args_is_help=True,
    help="Create a tracked item.",
    cls=_CustomCreateGroup,
)

# The bundled spec is the source of truth for the STATIC (import-time) registration loop,
# mirroring the resource-group loop in _cli/__init__.py: one generic `_make` per creatable
# work type, ordered by each type's explicit ItemSpec.order (ascending, type name breaking
# ties) — no hand-maintained type tuple. `guide` is excluded — it gets its own command below
# with extra --tech/--tag options; role/skill/operator are meta-types with their own
# dedicated commands, never `sq create`.
_create_spec = bundled_spec()
_CREATABLE: tuple[str, ...] = tuple(
    t
    for t in sorted(_create_spec.work_types(), key=lambda t: (_create_spec.items[t].order, t))
    if t != "guide"
)


def _make(item_type_str: str):
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
        priority: str | None = typer.Option(None, "--priority", help=_priority_help(item_type_str)),
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
            item_type_str,
            title,
            description=desc,
            parent=resolved_parent,
            author=author,
            labels=label or None,
            refs=resolved_refs,
            assignee=assignee,
            priority=parse_badge_code("priority", priority) if priority else None,
            body=resolve_body_optional(message or None, file),
        )
        if json_out:
            data = json.loads(res.item.model_dump_json())
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
    create_app.command(_t, help=f"Create a {_t}.")(_make(_t))

# Register hidden aliases for the _CREATABLE types so `sq create feat TITLE` dispatches
# identically to `sq create feature TITLE`.  Aliases come from the bundled spec (the single
# source of truth, same as the resource-group loop in _cli/__init__.py).  Hidden = not shown
# in --help, preserving byte-identical output (AC#7/#8).
for _t in _CREATABLE:
    for _alias in _create_spec.items[_t].aliases:
        create_app.command(_alias, hidden=True)(_make(_t))

# Type names with a static `sq create <type>` command already registered above — used by
# _CustomCreateGroup to draw the line between "already known" and "resolve dynamically".
_STATIC_CREATE_TYPES: frozenset[str] = frozenset({*_CREATABLE, "guide"})


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
        "guide",
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
        print_json_clean(json.dumps(data))
    else:
        console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
        if res.lane_warning is not None:
            console.print(e(res.lane_warning))


# Hidden guide aliases (same pattern as _CREATABLE loop above).
for _guide_alias in _create_spec.items["guide"].aliases:
    create_app.command(_guide_alias, hidden=True)(create_guide)
