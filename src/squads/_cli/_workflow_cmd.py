"""`sq workflow` — workflow cheatsheet + spec validation surface.

Sub-commands:
- ``sq workflow`` / ``sq workflow show``  — print the team cheatsheet.
- ``sq workflow lint``                   — verbose collect-all-errors spec validation.
- one catalog command per declared ``WorkflowSpec`` vocabulary map (``types``,
  ``subentity-kinds``, ``collections``, ``statuses``, ``roles``, ``lifecycles``,
  ``ref-kinds``), each a human Rich table by default and a bare JSON array under ``--json``:
  one row per declared entry in a documented order, every key present on every row, and
  cross-references carried **by name** so a client joins catalogs instead of receiving
  denormalized copies.

``lint`` is the author-facing diagnostic: it runs the same checks that ``open_service`` runs
fail-closed (pure-spec validation + live-index cross-check), but prints EVERY error and
warning with the offending config key and a fix hint instead of aborting on the first problem.
Exit code 0 on a clean spec, 1 when any error is present.

Design: ``lint`` calls ``lint_workflow_spec`` directly — it does NOT go through
``open_service``.  This is intentional: a spec that causes ``open_service`` to hard-stop (e.g.
it drops a status still in use) is precisely what an author runs ``sq workflow lint`` to
diagnose.  Bypassing ``open_service`` means lint is never self-blocked by the same check it is
trying to report.
"""

import json
import math
from typing import TYPE_CHECKING, cast

import typer
from rich.markdown import Markdown
from rich.table import Table

import squads._cli._common as common
from squads._cli._common import console, e, handle_errors, status_text
from squads._errors import SquadsError
from squads._models._vocab import labels_for
from squads._workflow._models import (
    FALLBACK_ROLE_NAME,
    lifecycle_edges_in_order,
    lifecycle_states_in_order,
)

if TYPE_CHECKING:
    from squads._interactions._models import PlaybookSpec
    from squads._workflow._models import WorkflowSpec

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help=(
        "Workflow cheatsheet and spec validation.\n\n"
        "Run `sq workflow` (or `sq workflow show`) for the team cheatsheet. "
        "Run `sq workflow lint` to validate your workflow override spec. "
        "Run `sq workflow types` / `subentity-kinds` / `collections` / `statuses` / `roles` "
        "/ `lifecycles` / `ref-kinds` for the machine-readable type / sub-entity-kind / "
        "badge-collection / status / role / lifecycle / ref-kind catalogs."
    ),
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


_RAW_HELP = "Plain markdown output (opt out of Rich markdown render)."


@workflow_app.callback()
@common.command
async def workflow_default(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help=_RAW_HELP),
) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        await _print_cheatsheet(raw=raw)


@workflow_app.command("show")
@common.command
async def workflow_show(raw: bool = typer.Option(False, "--raw", help=_RAW_HELP)) -> None:
    """Print the team workflow cheatsheet (who writes what, how items link)."""
    await _print_cheatsheet(raw=raw)


async def _print_cheatsheet(*, raw: bool) -> None:
    """Render the cheatsheet — Rich markdown by default, clean markdown text with ``--raw``.

    ``--raw`` prints the ``workflow.md.j2`` render verbatim (markdown tables, no
    box-drawing/ANSI), mirroring the ``sq show --raw`` / ``sq docs`` precedent: opt out of
    ``rich.Markdown`` rendering, print the source text as-is.
    """
    from squads._rendering._engine import render

    # The cheatsheet's authoring bullets (authoring_owner) are roster-aware when a live
    # roster is available, so an agent reading `sq workflow` sees the same "who actually
    # authors what" answer as CLAUDE.md/the squads skill — never a role this squad doesn't
    # have. `sq workflow` is also a valid reference command *outside* any squad (before
    # `sq init`, or from an unrelated directory), where there is no roster to read; that
    # case degrades to the historical unfiltered-by-catalog-membership-only behaviour rather
    # than failing the whole command.
    roles: list[dict[str, str]] | None = None
    playbook: PlaybookSpec | None = None
    try:
        svc = common.get_service()
        roster = await svc.roster()
    except SquadsError:
        roles = None
    else:
        roles = [{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in roster]
        # Same reason as the roster: resolve the create-lane through the ACTIVE (merged)
        # playbook so an override-declared authoring role is named here too.
        playbook = svc.playbook

    content = render(
        "workflow.md.j2", spec=common.get_active_spec(), roles=roles, playbook=playbook
    )
    if raw:
        console.print(content, markup=False, highlight=False, soft_wrap=True)
    else:
        console.print(Markdown(content))


# ─── types ────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow types --json`` catalog. Kept as a module-level
#: tuple so a test can assert the CLI never drifts from the declared contract.
TYPE_CATALOG_FIELDS: tuple[str, str, str, str, str, str, str, str, str] = (
    "type",
    "order",
    "prefix",
    "reserved",
    "category",
    "subentity_kind",
    "lifecycle",
    "fields",
    "labels",
)

#: Frozen field set for each entry of a ``fields`` array — the SAME entry shape on the type
#: catalog and the sub-entity-kind catalog, deliberately one tuple rather than two parallel
#: ones: the sub-entity field mechanism is the item one unforked, and the published shape is
#: part of that.
FIELD_ENTRY_FIELDS: tuple[str, str, str] = ("code", "label", "collection")


def _field_entries(type_or_kind: str, spec: WorkflowSpec) -> list[dict[str, object]]:
    """The field->collection bindings declared for an item type OR a sub-entity kind — a
    client resolves field code -> collection code here, then collection code -> vocabulary via
    ``sq workflow collections --json``. One builder for both catalogs (see
    :data:`FIELD_ENTRY_FIELDS`)."""
    return [
        {"code": f.code, "label": f.label, "collection": f.collection}
        for f in spec.fields_for(type_or_kind)
    ]


def _type_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen type-catalog rows, ascending resolved ``order`` (type-name string
    tiebreak — the same ordering the CLI uses to register per-type commands).

    Includes every declared type (work AND reserved: role/skill/operator). ``order`` is
    ``None`` when ``ItemSpec.order`` is unset (``+inf``) — present-but-null, never
    omitted, so the key set stays stable across every row. ``category`` is the type's
    declared ``roster``/``work``/``records`` axis (the same taxonomy ``reserved``
    already summarizes as a boolean) — a client reads it here instead of re-deriving the
    split from ``reserved`` or a hardcoded type list. ``subentity_kind`` names the declared
    kind this type hosts (``null`` for a type that hosts none) and is the join key into
    ``sq workflow subentity-kinds --json``: a sub-entity in ``sq show --json`` carries no kind
    of its own, so type -> kind is the only link a client has to the kind's declared field
    labels. ``lifecycle`` names the machine this type binds — a declared choice, derivable
    from nothing else on the row. Both are references *by name*, never inlined copies.
    ``fields`` is the type's declared field->collection bindings — ``[]`` for a type with no
    badge fields. ``labels`` is the type's four resolved display-label forms
    (``singular``/``plural``/``singular_lower``/``plural_lower``), pin-else-derive via
    ``labels_for`` — a client reads a pretty group header here instead of title-casing the
    raw type string itself.
    """
    types = sorted(spec.items, key=lambda t: (spec.items[t].order, t))
    return [
        {
            "type": t,
            "order": None if math.isinf(spec.items[t].order) else spec.items[t].order,
            "prefix": spec.items[t].prefix,
            "reserved": spec.items[t].category == "roster",
            "category": spec.items[t].category,
            "subentity_kind": spec.items[t].subentity_kind,
            "lifecycle": spec.items[t].lifecycle,
            "fields": _field_entries(t, spec),
            "labels": labels_for(t, spec),
        }
        for t in types
    ]


@workflow_app.command("types")
@handle_errors
def workflow_types(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine type catalog."),
) -> None:
    """List every declared type in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared type (work AND reserved), in ascending resolved ``order`` (type-name
    string breaks ties): ``{type, order, prefix, reserved, category, subentity_kind,
    lifecycle, fields, labels}``.
    ``order`` is ``null`` when the type has no explicit order (``+inf``); ``category`` is
    one of ``roster``/``work``/``records`` (``reserved`` is exactly
    ``category == "roster"``); ``subentity_kind`` is the declared sub-entity kind this type
    hosts, or ``null`` — join it to ``sq workflow subentity-kinds --json``; ``lifecycle`` is
    the machine this type binds; ``fields`` is the type's declared field->collection
    bindings (``[{code, label, collection}]``, ``[]`` if none); ``labels`` is the type's
    four resolved display-label forms (``{singular, plural, singular_lower,
    plural_lower}``, pin-else-derive) — all present, never omitted, so the key set is
    stable across every object.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _type_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Type", "Order", "Prefix", "Reserved", "Category"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["type"])),
            "" if row["order"] is None else str(row["order"]),
            e(str(row["prefix"])),
            "yes" if row["reserved"] else "",
            e(str(row["category"])),
        )
    console.print(table)


# ─── subentity-kinds ────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow subentity-kinds --json`` catalog.
#:
#: ``placeholder`` is deliberately absent: scaffold prose is content the engine writes into a
#: file, not vocabulary a client resolves.
SUBENTITY_KIND_CATALOG_FIELDS: tuple[str, str, str, str, str, str, str, str] = (
    "subentity_kind",
    "lifecycle",
    "plural",
    "local_prefix",
    "container_heading",
    "completion",
    "maps_parent_story",
    "fields",
)


def _subentity_kind_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen sub-entity-kind rows, ascending kind name.

    ``subentity_kind`` is the identity key, named as the spec names it, so the type row's
    reference uses the identical key name (``type.subentity_kind`` joins
    ``subentity_kind.subentity_kind``). Not ``kind``: ``kind`` already means ref-kind
    everywhere a client sees ``refs`` (``"ID:kind"``).

    Each remaining key is a declaration a client would otherwise have to guess:

    - ``lifecycle`` — the machine this kind binds, by name.
    - ``plural`` — the CLI list verb AND the persisted container-marker name; a client that
      invokes the verb or reads the marker must read this rather than pluralize the kind name.
    - ``local_prefix`` — the local-id prefix (``US``/``ST``/``F``), for rendering or parsing
      a local id.
    - ``container_heading`` — the resolved ``## <heading>`` above the kind's container block.
      Published because it is an engine derivation with a special case ("User Stories", which
      ``"stories".title()`` does not produce): a client that title-cases ``plural`` itself
      renders a heading that disagrees with the markdown sq writes into the file.
    - ``completion`` — the done-target status inside this kind's own lifecycle, so a "mark
      done" action targets a declared status instead of a hardcoded ``Done``/``Fixed``.
    - ``maps_parent_story`` — completes the roll-up column derivation (fixed base + one column
      per declared field + a story column iff this flag). A client handed ``fields`` but not
      the flag can build every column but the last, and would hardcode that one.
    - ``fields`` — the same ``{code, label, collection}`` entry shape the type row carries
      (:data:`FIELD_ENTRY_FIELDS`), so a client renders a declared label rather than a
      title-cased code.
    """
    return [
        {
            "subentity_kind": kind,
            "lifecycle": ks.lifecycle,
            "plural": ks.plural,
            "local_prefix": ks.local_prefix,
            "container_heading": spec.subentity_container_heading(kind),
            "completion": ks.completion,
            "maps_parent_story": ks.maps_parent_story,
            "fields": _field_entries(kind, spec),
        }
        for kind, ks in sorted(spec.subentity_kinds.items())
    ]


@workflow_app.command("subentity-kinds")
@handle_errors
def workflow_subentity_kinds(
    json_out: bool = typer.Option(
        False, "--json", help="Emit the machine sub-entity-kind catalog."
    ),
) -> None:
    """List every declared sub-entity kind in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per declared
    kind, ascending kind name: ``{subentity_kind, lifecycle, plural, local_prefix,
    container_heading, completion, maps_parent_story, fields}``. ``subentity_kind`` is the
    identity key the type catalog's own ``subentity_kind`` field points at — join the two to
    go from an item's ``type`` to the kind its sub-entities belong to, then to that kind's
    declared field labels. ``fields`` is ``[{code, label, collection}]`` (``[]`` if none), the
    same entry shape ``sq workflow types --json`` uses; resolve a code to its glyph/label
    through ``sq workflow collections --json``. All keys present on every row, never omitted.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _subentity_kind_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Kind", "Lifecycle", "Plural", "Prefix", "Heading", "Completion", "Fields"):
        table.add_column(col)
    for row in rows:
        row_fields = cast("list[dict[str, str]]", row["fields"])
        table.add_row(
            e(str(row["subentity_kind"])),
            e(str(row["lifecycle"])),
            e(str(row["plural"])),
            e(str(row["local_prefix"])),
            e(str(row["container_heading"])),
            e(str(row["completion"])),
            e(", ".join(f["code"] for f in row_fields)),
        )
    console.print(table)


# ─── lifecycles ─────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow lifecycles --json`` catalog.
LIFECYCLE_CATALOG_FIELDS: tuple[str, str, str, str] = (
    "lifecycle",
    "initial",
    "states",
    "transitions",
)

#: Frozen field set for each entry of a lifecycle row's ``transitions`` array.
TRANSITION_ENTRY_FIELDS: tuple[str, str] = ("from", "to")


def _lifecycle_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen lifecycle-catalog rows, ascending lifecycle name.

    ``lifecycle`` is the identity key — the map key on ``spec.lifecycles``, named as the spec
    names it, so the type row's and the sub-entity-kind row's own ``lifecycle`` fields join
    here by that identical name.

    ``states`` is :func:`lifecycle_states_in_order` — BFS discovery order from ``initial``,
    then any unreached state appended sorted. Deliberately NOT ``linearize_lifecycle``'s
    prettier spine-then-side-states ordering: that ordering canonicalizes side states through
    a table keyed on bundled status names, so publishing it would freeze a
    bundled-name-dependent order into a contract and silently degrade for an adopter's own
    status names. ``Lifecycle.states`` itself is a ``frozenset`` and is never iterated for
    anything that reaches this row.

    ``transitions`` is one ``{from, to}`` object per edge (:func:`lifecycle_edges_in_order`) —
    sources in ``states`` order, targets in each source's declared order. Not a positional
    pair (``[src, dst]`` cannot grow a named key) and not a map keyed on adopter-declared
    status names, which would have no frozen key set for a strictly-typed client.

    The row does not carry which types/kinds bind this lifecycle — the inversion of a forward
    edge; join ``sq workflow types --json``'s / ``sq workflow subentity-kinds --json``'s own
    ``lifecycle`` field instead — and it does not carry per-state terminality, which is
    ``role.settled`` one join away via ``sq workflow statuses --json`` -> ``sq workflow roles
    --json``.
    """
    return [
        {
            "lifecycle": name,
            "initial": machine.initial,
            "states": lifecycle_states_in_order(machine),
            "transitions": [
                {"from": src, "to": dst} for src, dst in lifecycle_edges_in_order(machine)
            ],
        }
        for name, machine in sorted(spec.lifecycles.items())
    ]


@workflow_app.command("lifecycles")
@handle_errors
def workflow_lifecycles(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine lifecycle catalog."),
) -> None:
    """List every declared lifecycle in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared lifecycle, ascending lifecycle name: ``{lifecycle, initial, states,
    transitions}``. ``states`` is the deterministic BFS-from-``initial`` order (never the raw
    ``frozenset`` order); ``transitions`` is ``[{from, to}]`` in that same source order, targets
    in each source's declared order. Join a type's or a sub-entity kind's own ``lifecycle``
    field (``sq workflow types --json`` / ``sq workflow subentity-kinds --json``) to this
    catalog's identity key to resolve the machine it binds. All keys present on every row,
    never omitted.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _lifecycle_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Lifecycle", "Initial", "States", "Transitions"):
        table.add_column(col)
    for row in rows:
        row_states = cast("list[str]", row["states"])
        row_transitions = cast("list[dict[str, str]]", row["transitions"])
        table.add_row(
            e(str(row["lifecycle"])),
            e(str(row["initial"])),
            e(", ".join(row_states)),
            e(", ".join(f"{t['from']} → {t['to']}" for t in row_transitions)),
        )
    console.print(table)


# ─── collections ────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow collections --json`` catalog.
COLLECTION_CATALOG_FIELDS: tuple[str, str, str, str, str] = (
    "collection",
    "label",
    "ordered",
    "default",
    "badges",
)

#: Frozen field set for each entry of a collection row's ``badges`` array.
COLLECTION_BADGE_ENTRY_FIELDS: tuple[str, str, str] = ("code", "label", "emoji")


def _collection_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen collection-vocabulary rows, ascending collection code — every
    declared collection's badges once, so a client resolves an item's ``badges`` code (e.g.
    ``"high"``) to its glyph/label here instead of hardcoding the emoji set."""
    return [
        {
            "collection": code,
            "label": coll.label,
            "ordered": coll.ordered,
            "default": coll.default,
            "badges": [{"code": b.code, "label": b.label, "emoji": b.emoji} for b in coll.badges],
        }
        for code, coll in sorted(spec.collections.items())
    ]


@workflow_app.command("collections")
@handle_errors
def workflow_collections(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine collection catalog."),
) -> None:
    """List every declared badge collection in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared collection, ascending collection code: ``{collection, label, ordered,
    default, badges}`` where ``badges`` is ``[{code, label, emoji}]`` in declaration
    order. Items emit badge *codes* only (``sq tree``/``list``/``show``'s generic
    ``badges`` map); this catalog is where a client resolves a code to its glyph/label,
    once per spec instead of duplicated onto every item.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _collection_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Collection", "Label", "Ordered", "Default", "Badges"):
        table.add_column(col)
    for row in rows:
        row_badges = cast("list[dict[str, str | None]]", row["badges"])
        badge_list = ", ".join(f"{b['emoji'] or ''} {b['code']}".strip() for b in row_badges)
        table.add_row(
            e(str(row["collection"])),
            e(str(row["label"])),
            "yes" if row["ordered"] else "",
            e(str(row["default"])) if row["default"] else "",
            e(badge_list),
        )
    console.print(table)


# ─── statuses ────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow statuses --json`` catalog.
STATUS_CATALOG_FIELDS: tuple[str, str, str] = ("status", "role", "badge")


def _status_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen status-vocabulary rows, ascending status name — a client joins
    an item's ``status`` string to this catalog to read ``role``/``badge`` instead of keying
    on the literal status name (e.g. hardcoding ``status == "InProgress"`` to detect "work in
    flight"). ``role`` is the sole status axis — join ``sq workflow roles --json`` to resolve
    it to ``{settled, hidden, color}``; ``terminal``/``is_open`` are not exposed here, they are
    ``role.settled``/``not role.settled`` on that catalog.

    ``role`` is the *resolved* role name (``StatusSpec.role`` or, when a status declares none,
    the engine's own ``FALLBACK_ROLE_NAME`` fallback — the same resolution
    :meth:`WorkflowSpec.role_for` performs) — never the bare, possibly-``None`` declared field.
    A client that receives ``role: null`` here would have no way to distinguish "this status
    genuinely has no behaviour" from "the catalog fetch hasn't loaded yet"; every declared
    status has *some* resolved role, so ``null`` is reserved for the latter. Byte-identical for
    the bundled spec (every bundled status declares its own role already); only a role-less
    custom status sees a different value here than the bare field would have given."""
    return [
        {
            "status": name,
            "role": st.role or FALLBACK_ROLE_NAME,
            "badge": st.badge,
        }
        for name, st in sorted(spec.statuses.items())
    ]


@workflow_app.command("statuses")
@handle_errors
def workflow_statuses(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine status catalog."),
) -> None:
    """List every declared status in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared status, ascending status name: ``{status, role, badge}``. ``role`` is the
    reference into the role catalog (``sq workflow roles --json``) — join it to resolve
    ``settled``/``hidden``/``color``; ``badge`` is the declared status emoji or ``null``.
    Catalog-only: no per-item ``role``/``is_active`` field is added to any item surface — a
    client joins an item's own ``status`` to this catalog instead.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _status_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Status", "Role", "Badge"):
        table.add_column(col)
    for row in rows:
        status = str(row["status"])
        table.add_row(
            status_text(status, spec),
            e(str(row["role"])) if row["role"] else "",
            e(str(row["badge"])) if row["badge"] else "",
        )
    console.print(table)


# ─── roles ───────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow roles --json`` catalog.
ROLE_CATALOG_FIELDS: tuple[str, str, str, str, str] = (
    "role",
    "settled",
    "hidden",
    "color",
    "live",
)


def _role_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen role-catalog rows, ascending role name — a client joins a status's ``role``
    (from ``sq workflow statuses --json``) to this catalog to resolve ``settled``/``hidden``/
    ``color``/``live`` instead of hardcoding any role name or deriving it from category."""
    return [
        {
            "role": name,
            "settled": r.settled,
            "hidden": r.hidden,
            "color": r.color,
            "live": r.live,
        }
        for name, r in sorted(spec.roles.items())
    ]


@workflow_app.command("roles")
@handle_errors
def workflow_roles(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine role catalog."),
) -> None:
    """List every declared role in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared role, ascending role name: ``{role, settled, hidden, color, live}``.
    ``settled`` is the old ``terminal`` (a resting/end state); ``hidden`` is default-visibility;
    ``color`` is a semantic colour intent from the closed palette (``positive``/``danger``/
    ``warning``/``muted``/``neutral``/``info``) — each client maps it to a concrete colour,
    with a neutral fallback for an intent it doesn't recognise. ``live`` (defaults false) is
    the materialisation axis: an item whose status resolves to a live role is on offer to
    be spawned/loaded/cited/assigned. A status references one role by name (``sq workflow
    statuses --json``'s ``role`` field); join the two to resolve behaviour.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _role_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Role", "Settled", "Hidden", "Color", "Live"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["role"])),
            "yes" if row["settled"] else "",
            "yes" if row["hidden"] else "",
            e(str(row["color"])),
            "yes" if row["live"] else "",
        )
    console.print(table)


# ─── ref-kinds ──────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow ref-kinds --json`` catalog.
REF_KIND_CATALOG_FIELDS: tuple[str, str, str, str, str] = (
    "kind",
    "label",
    "hint",
    "role",
    "direction",
)


def _ref_kind_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen ref-kind-vocabulary rows, ascending kind name — the accepted
    ``sq <type> <n> ref add <id> --kind <kind>`` set, replacing the former closed
    ``VALID_REF_KINDS`` frozenset with the merged spec's own declared ``[ref_kinds]``.

    ``kind`` is the identity key — the literal string a ``refs`` entry carries after the
    ``:`` (``"ID:kind"``), or that a bare ``"ID"`` decodes to when it names the kind whose
    ``role`` is ``"default"``. ``role`` binds engine behaviour to a semantic instead of a
    spelling (``null`` for a purely navigational kind); ``direction`` (``"blocker"``/
    ``"dependent"``/``null``) only ever accompanies ``role = "dependency"``. Complete on first
    ship, following the family's own one-catalog-per-spec-map rule: every key is present on
    every row.
    """
    return [
        {
            "kind": code,
            "label": rk.label,
            "hint": rk.hint,
            "role": rk.role,
            "direction": rk.direction,
        }
        for code, rk in sorted(spec.ref_kinds.items())
    ]


@workflow_app.command("ref-kinds")
@handle_errors
def workflow_ref_kinds(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine ref-kind catalog."),
) -> None:
    """List every declared ref kind in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared kind, ascending kind name: ``{kind, label, hint, role, direction}``. ``role``
    is the semantic the engine binds to (``dependency``/``preload``/``supersession``/
    ``default``, or ``null`` for a navigational kind); ``direction`` (``blocker``/
    ``dependent``) only accompanies ``role = "dependency"``, else ``null``. Exactly one row
    carries ``role = "default"`` — the kind a bare ``ref add <id>`` (no ``--kind``) writes.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _ref_kind_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Kind", "Label", "Hint", "Role", "Direction"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["kind"])),
            e(str(row["label"])),
            e(str(row["hint"])) if row["hint"] else "",
            e(str(row["role"])) if row["role"] else "",
            e(str(row["direction"])) if row["direction"] else "",
        )
    console.print(table)


# ─── views ──────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow views --json`` catalog.
VIEW_CATALOG_FIELDS: tuple[str, str, str, str, str, str] = (
    "view",
    "source_kind",
    "source_name",
    "fields",
    "group_by",
    "order_by",
)


def _view_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen view-catalog rows, ascending view name.

    ``view`` is the identity key, named as the spec names it — also the presentation
    template's own identity (``templates/views/<view>.md.j2``; there is no separate
    ``presentation`` key to carry). ``source_kind``/``source_name`` name the projected
    relation (``"ref"``/``"subentity"``/``"subtree"`` + the declared kind/type it names —
    join ``source_name`` into ``sq workflow ref-kinds``/``subentity-kinds``/``types --json``
    depending on ``source_kind``). ``fields`` is the view's declared projection columns
    (``[{code, label}]``); ``group_by``/``order_by`` name declared field codes, ``null``/
    ``[]`` when the view declares neither — present on every row either way.
    """
    return [
        {
            "view": name,
            "source_kind": v.source.kind,
            "source_name": v.source.name,
            "fields": [{"code": f.code, "label": f.label} for f in v.fields],
            "group_by": v.group_by,
            "order_by": list(v.order_by),
        }
        for name, v in sorted(spec.views.items())
    ]


@workflow_app.command("views")
@handle_errors
def workflow_views(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine view catalog."),
) -> None:
    """List every declared derived view in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared view, ascending view name: ``{view, source_kind, source_name, fields,
    group_by, order_by}``. Resolve one view against an item with
    ``sq workflow view <name> <item-id>``.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _view_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("View", "Source kind", "Source name", "Fields", "Group by"):
        table.add_column(col)
    for row in rows:
        row_fields = cast("list[dict[str, str]]", row["fields"])
        field_codes = ", ".join(f["code"] for f in row_fields)
        table.add_row(
            e(str(row["view"])),
            e(str(row["source_kind"])),
            e(str(row["source_name"])),
            e(field_codes),
            e(str(row["group_by"])) if row["group_by"] else "",
        )
    console.print(table)


@workflow_app.command("view")
@common.command
async def workflow_view(
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
    item_id: str = typer.Argument(..., metavar="ID", help="Item to resolve the view against."),
    json_out: bool = typer.Option(False, "--json", help="Emit the projection, no presentation."),
) -> None:
    """Resolve one declared view against one item.

    Default: rendered through the view's declared presentation template
    (``templates/views/<name>.md.j2``, adopter-overridable). ``--json`` emits the
    projection instead — field metadata, grouping, and records — and skips presentation
    entirely: the CLI rendering is one presentation over the records, never their source.
    """
    from squads._cli._common import get_service, print_json_clean
    from squads._views import projection_json

    svc = get_service()
    if json_out:
        projection = await svc.resolve_view(name, item_id)
        print_json_clean(json.dumps(projection_json(projection)))
        return
    console.print(await svc.render_view(name, item_id))


# ─── lint ─────────────────────────────────────────────────────────────────────


@workflow_app.command("lint")
@handle_errors
def workflow_lint() -> None:
    """Validate the workflow override spec — collect ALL errors and exit 0/1.

    Prints every error with the offending config key and a fix hint.
    Exits 0 with "workflow spec OK" on a clean spec; exits 1 when any error is
    present.  Warnings alone (if any) still exit 0.

    This command intentionally does NOT go through ``open_service``, so it can
    diagnose a spec that would cause normal commands to hard-stop.
    """
    from squads._context import get_context
    from squads._paths import resolve
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, lint_workflow_spec

    ctx = get_context()
    try:
        sp = resolve(ctx.active_dir, client_cwd=ctx.client_cwd)
    except SquadsError as exc:
        console.print(f"[red]error[/red]: {e(str(exc))}", soft_wrap=True)
        raise typer.Exit(1) from exc

    squad_dir = sp.squad_dir
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME

    if not override_path.is_file():
        console.print(
            "[green]workflow spec OK[/green] — no override file found; using the bundled default."
        )
        return

    findings = lint_workflow_spec(squad_dir)

    errors = [f for f in findings if f[0] == "error"]
    warnings = [f for f in findings if f[0] == "warn"]

    if not findings:
        console.print("[green]workflow spec OK[/green] — no errors or warnings.")
        return

    # Print errors.
    if errors:
        table = Table(title="workflow spec errors", show_header=True, header_style="red")
        table.add_column("location", style="dim")
        table.add_column("error")
        table.add_column("fix hint", style="dim")
        for _level, location, message, fix_hint in errors:
            table.add_row(e(location), e(message), e(fix_hint))
        console.print(table)

    # Print warnings.
    if warnings:
        table = Table(title="workflow spec warnings", show_header=True, header_style="yellow")
        table.add_column("location", style="dim")
        table.add_column("warning")
        table.add_column("fix hint", style="dim")
        for _level, location, message, fix_hint in warnings:
            table.add_row(e(location), e(message), e(fix_hint))
        console.print(table)

    if errors:
        console.print(
            f"[red]{len(errors)} error(s)[/red]"
            + (f", {len(warnings)} warning(s)" if warnings else "")
            + " — fix the errors above then re-run `sq workflow lint`."
        )
        raise typer.Exit(1)
    else:
        # Warnings only — exit 0.
        console.print(f"[green]workflow spec OK[/green] — {len(warnings)} warning(s); no errors.")
