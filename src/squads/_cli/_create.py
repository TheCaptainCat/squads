"""`sq create <type> TITLE …` — one command per item type, sharing one implementation.

Built-in types are registered statically at import time (unchanged from before).
Custom types declared in ``.overrides/workflow.toml`` are dispatched lazily by
``_CustomCreateGroup``, which follows the same pattern as ``_CustomTypeGroup`` in
``_cli/__init__.py`` (ADR-000263 Option 3).  Startup ordering: ``_CustomCreateGroup``
resolves the active spec via ``common.get_active_spec()`` at Click dispatch time
(``get_command`` / ``list_commands``), after ``_bind_active_spec`` has already run in
the root callback — so the same spec that the resource groups see is also visible here.
"""

import json
from typing import Any, ClassVar

import typer
import typer._click as _click
import typer.core
import typer.main

import squads._cli._common as common
from squads import _actor as actor
from squads._cli._common import (
    console,
    e,
    get_service,
    parse_priority,
    print_json_clean,
    resolve_body_optional,
    resolve_item_id_any,
)
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._item import make_ref, split_ref


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
            item_type_str,
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
        """Return custom (non-built-in) work type names from the resolved spec.

        Safe to call at any time; returns the empty set on any error.
        """
        try:
            spec = common.get_active_spec()
            built_in_names: frozenset[str] = frozenset(t.value for t in ItemType)
            return frozenset(t for t in spec.work_types() if t not in built_in_names)
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
        # Fast path: try the statically-built built-in commands first.
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Spec-resolution region: decide whether cmd_name is a known custom work type.
        # Errors here (invalid spec, missing active spec, etc.) are swallowed so that
        # `sq create --help` always degrades gracefully.  The only valid outcome is either
        # (a) cmd_name confirmed as a declared custom work type, or (b) return None so
        # Click emits "No such command".
        try:
            built_in_names: frozenset[str] = frozenset(t.value for t in ItemType)
            if cmd_name in built_in_names:
                return None

            spec = common.get_active_spec()
            if cmd_name not in spec.work_types():
                return None
            if spec.item_is_meta(cmd_name):
                return None
        except Exception:  # pylint: disable=broad-except
            # Spec resolution failed — degrade gracefully.
            return None

        # Past this point cmd_name IS a declared custom work type.  Build errors here are
        # genuine failures for a type the user declared (and that --help lists), so they
        # must propagate rather than silently become "No such command".
        if cmd_name not in self._custom_cmd_cache:
            self._custom_cmd_cache[cmd_name] = _build_create_cmd(cmd_name)

        return self._custom_cmd_cache.get(cmd_name)


create_app = typer.Typer(
    no_args_is_help=True,
    help="Create a tracked item.",
    cls=_CustomCreateGroup,
)

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
            print_json_clean(json.dumps(data))
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
        print_json_clean(json.dumps(data))
    else:
        console.print(f"created [bold]{res.item.id}[/bold] → {res.path}")
        if res.lane_warning is not None:
            console.print(e(res.lane_warning))
