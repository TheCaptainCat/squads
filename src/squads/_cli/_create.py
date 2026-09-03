"""`sq create <type> TITLE …` — one command per item type, sharing one implementation.

Built-in types are registered statically at import time (unchanged from before).
Custom types declared in ``.overrides/workflow.toml`` are dispatched lazily by
``_CustomCreateGroup``, which follows the same pattern as ``_CustomTypeGroup`` in
``_cli/__init__.py``.  Startup ordering: ``_CustomCreateGroup``
resolves the active spec via ``common.get_active_spec()`` at Click dispatch time
(``get_command`` / ``list_commands``), after ``common.bind_active_spec`` has already run in
the root callback — so the same spec that the resource groups see is also visible here.
"""

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
from squads._models._extras import ExtraKey as X
from squads._models._item import make_ref, split_ref
from squads._services._service import Service
from squads._workflow import bundled_spec


async def _resolve_parent_option(parent: str | None, svc: Service) -> str | None:
    """Resolve a create command's ``--parent`` option to a full item ID, or ``None``.

    The single parent door for every ``sq create`` command: the built-in types, the
    lazily-built custom types, and ``guide``.  Three copies of the resolution used to sit
    inline, so a fix had to be made three times and the next create-shaped command would
    have copied whichever copy it sat nearest.

    ``is not None``, not truthiness: ``--parent ""`` is a value the caller supplied, and
    testing it for truth sent it down the no-parent branch — the command created an item
    with no parent and reported plain success, so the only way to notice was to read the
    item back.  Empty and whitespace-only are refused here rather than handed to
    :func:`resolve_item_id_any`, which would answer about an empty token instead of about
    the flag; ``sq <type> <n> update`` tests the same argument with the same ``is not None``
    and leads with the same sentence.  The remedy differs and is deliberately not copied:
    ``create`` has no ``--no-parent``, because omitting ``--parent`` is how a parentless item
    is made.
    """
    if parent is None:
        return None
    if not parent.strip():
        raise SquadsError("--parent needs an item ID; omit --parent to create without a parent")
    return await resolve_item_id_any(parent, svc)


def _priority_help(item_type: str) -> str:
    """``--priority`` help text for ``create <item_type>``, derived from the priority
    collection *item_type* actually binds in the resolved active spec.

    Read directly at command-registration time this is the bundled spec for the
    statically-registered types (registered at import time, before ``common.bind_active_spec``
    runs) — byte-identical to the previous hardcoded text there for a non-customized squad.
    Statically-registered commands additionally re-derive this at ``--help`` render time via
    :func:`common.spec_aware_command_cls`, so an override's replaced priority collection is
    reflected there too, not just at construction.

    Resolves strictly (:func:`squads._badges.declared_collection`): a type declaring no
    ``priority`` field enumerates nothing rather than borrowing the same-named collection —
    the flag is hidden outright in that case, see :func:`_refresh_priority_help`."""
    spec = common.get_active_spec()
    # sanctioned field-code literal: `--priority` is the flag *for* this field code
    coll_code = badges.declared_collection(item_type, "priority", spec)
    coll = spec.collections.get(coll_code) if coll_code else None
    if coll and coll.badges:
        return f"Priority: {'|'.join(b.code for b in coll.badges)}."
    return "Priority code (as defined by your workflow's priority collection)."


def _refresh_priority_help(item_type_str: str) -> Callable[[list[object]], None]:
    """A ``spec_aware_command_cls`` refresh callback that re-derives ``--priority``'s help
    for *item_type_str* from the live per-invocation spec at ``--help`` render time, and
    hides the flag entirely on a type that declares no ``priority`` field.

    Hiding rather than removing keeps the "advertise vs dispatch" split the rest of this
    module uses: the flag still parses, so the service's own declared-field gate
    (``ServiceCore._check_priority``) owns the one accurate refusal — but a flag that can
    only ever error is never offered in ``--help``."""

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
            # No pre-parse here: the collection `priority` binds is per-type, and the
            # service's `_check_priority` already resolves it from the type's own declared
            # field. A second CLI-side parse against a literally-named collection is the
            # third door into a two-door axis, and the one that gets it wrong.
            priority=priority,
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
    _tmp_app.command(
        item_type_str,
        help=f"Create a {item_type_str}.",
        cls=common.spec_aware_command_cls(_refresh_priority_help(item_type_str)),
    )(_cmd)
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
      ``common.bind_active_spec`` in the root callback, so they always see the same spec.
    - The ``_custom_cmd_cache`` is scoped to this class (``ClassVar``), independent of
      the resource-group cache, so the two caches do not interfere.
    """

    _custom_cmd_cache: ClassVar[dict[str, _click.Command]] = {}

    def _dropped_static_names(self, ctx: Any) -> frozenset[str]:
        """Statically-registered command/alias names whose canonical built-in type has been
        dropped from the resolved active spec (via ``[selected]``, or any other means).

        Resolves via ``common.resolve_spec_for_ctx(ctx)``, not ``common.get_active_spec()``
        alone — on the shell-completion path the root callback never runs, so a plain
        ``get_active_spec()`` here would silently see only the bundled spec (the same gap
        fixed for ``_CustomTypeGroup`` at the root level).

        These names still exist as real Click commands in the app built at import time — that
        registration is unconditional and only reflects the *bundled* spec — so without this
        check they would keep being offered by ``--help``/completion: a dropped type must not
        be advertised. **Advertising only** — ``get_command`` deliberately does NOT consult
        this set. Hiding a name from ``get_command`` would make Click's own unknown-command
        handler answer instead of the command itself, and that handler's did-you-mean
        suggestion still sees the (now merely help-hidden) name and would suggest the exact
        string the user typed, reading as a bug in ``sq`` rather than a refusal. Leaving the
        real command reachable lets it dispatch normally into ``svc.create``, whose own
        membership gate is the one accurate, ``[selected]``-aware refusal — one call site
        owns the message instead of two disagreeing ones. Fail-soft: any error resolving the
        active spec returns the empty set (same degrade-gracefully contract as
        ``_custom_non_roster_types``), so a dropped type simply falls back to being offered,
        never to a crash in ``--help``/completion.
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
        """Return custom creatable/trackable (non-roster) type names from the resolved spec.

        "Custom" here means "not already registered by the static import-time loop"
        (``_STATIC_CREATE_TYPES``) — i.e. anything a project's own workflow override adds
        on top of the bundled spec. Safe to call at any time; returns the empty set on any
        error. Resolves via ``common.resolve_spec_for_ctx`` — see
        :meth:`_dropped_static_names` for why (this is the completion path too).
        """
        try:
            spec = common.resolve_spec_for_ctx(ctx)
            return frozenset(t for t in spec.non_roster_types() if t not in _STATIC_CREATE_TYPES)
        except Exception:  # pylint: disable=broad-except
            return frozenset()

    def list_commands(self, ctx: Any) -> list[str]:
        """Built-in commands first, then custom non-roster types alphabetically.

        For a non-custom squad the custom set is empty, so this is byte-identical
        to the previous implementation.
        """
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

            # Resolve alias → canonical (mirrors _CustomTypeGroup.get_command). The canonical
            # type may itself be statically registered — a spec that gives a bundled type a
            # NEW alias (`feature.aliases = ["ft"]`) declares a name the import-time loop
            # never saw, and `sq create ft` has to reach the same command `sq ft` already
            # does; only the *type* being static short-circuits above, not its aliases.
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

        # Fast path: try the statically-built built-in commands first (canonical + hidden
        # aliases) — deliberately including one whose canonical type has been dropped from
        # the active spec (see _dropped_static_names' docstring for why hiding it here would
        # be worse than dispatching it: Click's own unknown-command handler would answer
        # instead, and its did-you-mean would name the very string the user typed). The
        # dispatched command runs through to `svc.create`, whose membership gate is the one
        # refusal that actually names the type as dropped rather than as a typo.
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
# with extra --tech/--tag options; role/skill/operator are roster types with their own
# dedicated commands, never `sq create`.
_create_spec = bundled_spec()
_CREATABLE: tuple[str, ...] = tuple(
    t
    for t in sorted(_create_spec.non_roster_types(), key=lambda t: (_create_spec.items[t].order, t))
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
            # No pre-parse here: the collection `priority` binds is per-type, and the
            # service's `_check_priority` already resolves it from the type's own declared
            # field. A second CLI-side parse against a literally-named collection is the
            # third door into a two-door axis, and the one that gets it wrong.
            priority=priority,
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
    create_app.command(
        _t, help=f"Create a {_t}.", cls=common.spec_aware_command_cls(_refresh_priority_help(_t))
    )(_make(_t))

# Register hidden aliases for the _CREATABLE types so `sq create feat TITLE` dispatches
# identically to `sq create feature TITLE`.  Aliases come from the bundled spec (the single
# source of truth, same as the resource-group loop in _cli/__init__.py).  Hidden = not shown
# in --help, preserving byte-identical output.
for _t in _CREATABLE:
    for _alias in _create_spec.items[_t].aliases:
        create_app.command(
            _alias, hidden=True, cls=common.spec_aware_command_cls(_refresh_priority_help(_t))
        )(_make(_t))

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
