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

import hashlib
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import typer
from rich.markdown import Markdown
from rich.table import Table

import squads._cli._common as common
from squads._cli._common import (
    ItemRowFields,
    build_item_row_json,
    console,
    e,
    handle_errors,
    status_text,
)
from squads._errors import SquadsError
from squads._interactions._playbook import get_playbook_spec
from squads._models._schema import SCHEMA_VERSION
from squads._models._vocab import labels_for
from squads._paths import number_for_id
from squads._specload import override_present
from squads._workflow._lifecycle_order import lifecycle_edges_in_order, lifecycle_states_in_order
from squads._workflow._models import FALLBACK_ROLE_NAME

if TYPE_CHECKING:
    from squads._models._item import Item
    from squads._models._subentity import SubEntity
    from squads._services._service import Service
    from squads._views import PlaybookSource
    from squads._workflow._models import WorkflowSpec

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help="Show the team workflow and the active spec's vocabulary.",
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


@workflow_app.callback()
@common.command
async def workflow_default(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        await _print_cheatsheet(raw=raw)


@workflow_app.command("show")
@common.command
async def workflow_show(raw: bool = common.raw_option()) -> None:
    """Print the team workflow cheatsheet: who writes what, how items link."""
    await _print_cheatsheet(raw=raw)


async def _print_cheatsheet(*, raw: bool) -> None:
    """Render the cheatsheet — Rich markdown by default, clean markdown text with ``--raw``.

    ``--raw`` prints the ``workflow.md.j2`` render verbatim (markdown tables, no
    box-drawing/ANSI), mirroring the ``sq show --raw`` / ``sq docs`` precedent: opt out of
    ``rich.Markdown`` rendering, print the source text as-is.
    """
    from squads._rendering._engine import render

    # The cheatsheet's authoring bullets (authoring_owners) are roster-aware when a live
    # roster is available, so an agent reading `sq workflow` sees the same "who actually
    # authors what" answer as CLAUDE.md/the squads skill — never a role this squad doesn't
    # have. `sq workflow` is also a valid reference command *outside* any squad (before
    # `sq init`, or from an unrelated directory), where there is no roster to read; that
    # case degrades to the unfiltered-by-catalog-membership-only behaviour rather
    # than failing the whole command.
    roles: list[dict[str, Any]] | None = None
    playbook = get_playbook_spec()
    from_squad: Path | None = None
    try:
        svc = common.get_service()
        roster = await svc.roster()
    except SquadsError:
        roles = None
    else:
        roles = [
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                "capabilities": list(r.capabilities),
            }
            for r in roster
        ]
        # Same reason as the roster: resolve the create-lane through the ACTIVE (merged)
        # playbook so an override-declared authoring role is named here too.
        playbook = svc.playbook
        from_squad = svc.paths.squad_dir

    content = render(
        "workflow.md.j2",
        from_squad=from_squad,
        spec=common.get_active_spec(),
        roles=roles,
        playbook=playbook,
    )
    if raw:
        console.print(content, markup=False, highlight=False, soft_wrap=True)
    else:
        console.print(Markdown(content))


# ─── types ────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow types --json`` catalog. Kept as a module-level
#: tuple so a test can assert the CLI never drifts from the declared contract.
TYPE_CATALOG_FIELDS: tuple[str, str, str, str, str, str, str, str, str, str] = (
    "type",
    "order",
    "prefix",
    "reserved",
    "category",
    "subentity_kind",
    "lifecycle",
    "fields",
    "attributes",
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
    badge fields. ``attributes`` is the type's declared non-badge frontmatter keys, name to
    ``{kind, required, settable}`` — ``{}`` for a type that declares none; a client reads
    here which keys an item row of the type may carry. ``labels`` is the type's four resolved
    display-label forms (``singular``/``plural``/``singular_lower``/``plural_lower``),
    pin-else-derive via ``labels_for`` — a client reads a pretty group header here instead of
    title-casing the raw type string itself.
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
            "attributes": {
                name: {"kind": a.kind, "required": a.required, "settable": a.settable}
                for name, a in spec.item_attributes(t).items()
            },
            "labels": labels_for(t, spec),
        }
        for t in types
    ]


def _order_cell(order: Any) -> str:
    """A type's order as the table prints it: whole as an integer, fractional as is."""
    if order is None:
        return ""
    return str(int(order)) if float(order).is_integer() else str(order)


@workflow_app.command("types")
@handle_errors
def workflow_types(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per declared type."
    ),
) -> None:
    """List every declared type in the active workflow spec.

    Fields: sq docs stability
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
            _order_cell(row["order"]),
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
        False, "--json", help="Print a JSON array, one object per sub-entity kind."
    ),
) -> None:
    """List every declared sub-entity kind in the active workflow spec.

    Fields: sq docs stability
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
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per lifecycle."
    ),
) -> None:
    """List every declared lifecycle in the active workflow spec.

    Fields: sq docs stability
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
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per badge collection."
    ),
) -> None:
    """List every declared badge collection in the active workflow spec.

    Fields: sq docs stability
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
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per status."
    ),
) -> None:
    """List every declared status in the active workflow spec.

    Fields: sq docs stability
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
ROLE_CATALOG_FIELDS: tuple[str, str, str, str, str, str, str] = (
    "role",
    "settled",
    "hidden",
    "color",
    "live",
    "blocked",
    "deferred",
)


def _role_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen role-catalog rows, ascending role name — a client joins a status's ``role``
    (from ``sq workflow statuses --json``) to this catalog to resolve ``settled``/``hidden``/
    ``color``/``live``/``blocked``/``deferred`` instead of hardcoding any role name or deriving it
    from category."""
    return [
        {
            "role": name,
            "settled": r.settled,
            "hidden": r.hidden,
            "color": r.color,
            "live": r.live,
            "blocked": r.blocked,
            "deferred": r.deferred,
        }
        for name, r in sorted(spec.roles.items())
    ]


@workflow_app.command("roles")
@handle_errors
def workflow_roles(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per status role."
    ),
) -> None:
    """List every status role in the active workflow spec.

    A status role says whether its statuses are settled, hidden or live.
    Fields: sq docs stability
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _role_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Role", "Settled", "Hidden", "Color", "Live", "Blocked", "Deferred"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["role"])),
            "yes" if row["settled"] else "",
            "yes" if row["hidden"] else "",
            e(str(row["color"])),
            "yes" if row["live"] else "",
            "yes" if row["blocked"] else "",
            "yes" if row["deferred"] else "",
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
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per ref kind."
    ),
) -> None:
    """List every declared ref kind in the active workflow spec.

    Fields: sq docs stability
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
VIEW_CATALOG_FIELDS: tuple[str, str, str, str] = ("view", "source_kind", "source_name", "transform")


def _view_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen view-catalog rows, ascending view name.

    ``view`` is the identity key, named as the spec names it — also the presentation
    template's own identity (``templates/views/<view>.md.j2``; there is no separate
    ``presentation`` key to carry). ``source_kind``/``source_name`` name the declared source
    (``"ref"``/``"subentity"``/``"subtree"``/``"role"``/``"playbook"``/``"self"`` + the
    declared kind/type it names, or ``null`` for the three kinds that take none — join
    ``source_name`` into ``sq workflow ref-kinds``/``subentity-kinds``/``types --json``
    depending on ``source_kind``). ``transform`` is the declaration as merged (``{module,
    function}`` or ``{path, function}``) or ``null``. No
    field/group-by/order-by grammar exists to report.
    """
    return [
        {
            "view": name,
            "source_kind": v.source.kind,
            "source_name": v.source.name,
            "transform": v.transform.model_dump(exclude_none=True) if v.transform else None,
        }
        for name, v in sorted(spec.views.items())
    ]


@workflow_app.command("views")
@handle_errors
def workflow_views(
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per view."),
) -> None:
    """List every declared derived view in the active workflow spec.

    Resolve one against an item with `sq workflow view <name> <id>`.
    Fields: sq docs stability
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _view_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("View", "Source kind", "Source name"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["view"])),
            e(str(row["source_kind"])),
            e(str(row["source_name"])) if row["source_name"] else "",
        )
    console.print(table)


def _playbook_json_payload(source: PlaybookSource) -> dict[str, object]:
    """A ``playbook`` source's ``--json`` payload — no pre-existing serializer to match (unlike
    the other five kinds), so this is the shape reasoned out directly here: the resolved type,
    its playbook lane's own declared fields (``overview``/``lifecycle``/``commands``/
    ``roles``) when it has one, and the live roster — the raw ingredients
    :class:`~squads._views.PlaybookSource` itself carries, unflattened. ``lane`` is ``None``
    for a type genuinely declared but outside every guide's lane domain — that source's own
    well-formed empty case (see :class:`~squads._views.PlaybookSource`), not a raise. No
    ``fields``/``group_by``/``groups`` key anywhere in this shape: a client reading a
    ``playbook`` payload sees only its own declared fields, never a projection envelope."""
    lane = source.lane
    return {
        "type": source.item_type,
        "lane": None
        if lane is None
        else {
            "overview": lane.overview,
            "lifecycle": lane.lifecycle,
            "commands": list(lane.commands),
            "roles": [
                {
                    "slug": rg.slug,
                    "enter": list(rg.enter),
                    "do": list(rg.do),
                    "handoff": list(rg.handoff),
                    "watch": list(rg.watch),
                    "authors": rg.authors,
                }
                for rg in lane.roles
            ],
        },
        "roster": [
            {
                "slug": rv.slug,
                "full_name": rv.full_name,
                "title": rv.title,
                "is_default": rv.is_default,
                "mission": rv.mission,
                "responsibilities": list(rv.responsibilities),
                "capabilities": list(rv.capabilities),
            }
            for rv in source.roster
        ],
    }


def _spec_identity_json(svc: Service) -> dict[str, object]:
    """The identity of the workflow spec that resolved a ``self``-view payload.

    ``digest`` is the SHA-256 of the merged spec, opaque and compared for equality only;
    ``override`` is a display flag saying a project ``.overrides/workflow.toml`` was merged
    into it, never a change detector."""
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME

    override = override_present(svc.paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME)
    canonical = json.dumps(
        svc.spec.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"schema_version": SCHEMA_VERSION, "override": override, "digest": digest}


def _view_json_child_rows(
    parent_id: str,
    children_by_parent: dict[str, list[Item]],
    spec: WorkflowSpec,
    blocked_ids: set[str],
    seen: set[str],
) -> list[dict[str, Any]]:
    """One matched record's real descendant subtree, recursively, in the same shape
    ``sq tree --json`` builds ``children`` in for that same item — the equivalence
    :func:`_view_json_payload`'s ``ref``/``subtree`` arm declares. Reuses
    ``squads._views.children_by_parent``'s own resolution (no third implementation of "who
    are this item's children") and, unconditionally, every descendant: ``sq workflow view
    --json`` carries no flag equivalent to ``sq tree --all`` for closed-item visibility, so
    closed descendants are included exactly like open ones. *seen* is one call's own set,
    seeded with the matched record's id before the first call — the same cycle guard
    ``_resolve_subtree_source`` already applies to the identical walk, so a genuine parent
    cycle in the corpus terminates here instead of recursing forever."""
    rows: list[dict[str, Any]] = []
    for child in sorted(children_by_parent.get(parent_id, []), key=lambda i: number_for_id(i.id)):
        if child.id in seen:
            continue
        seen.add(child.id)
        rows.append(
            build_item_row_json(
                ItemRowFields(
                    id=child.id,
                    type=child.type,
                    title=child.title,
                    status=child.status,
                    priority=child.badge_value("priority"),
                    assignee=child.assignee,
                    badge_value=child.badge_value,
                ),
                spec=spec,
                blocked_ids=blocked_ids,
                children=_view_json_child_rows(
                    child.id, children_by_parent, spec, blocked_ids, seen
                ),
            )
        )
    return rows


async def _view_json_payload(
    svc: Service, spec: WorkflowSpec, view_name: str, item_id: str
) -> object:
    """The ``--json`` payload for ``sq workflow view <name> <id> --json`` — *view_name*
    resolved against *item_id* once
    (:meth:`~squads._services._views.ViewsMixin.resolve_view_source`), then serialized in the
    shape its own declared source kind already has a serializer for — never a shared envelope:
    ``ref``/``subtree`` reuse :func:`~squads._cli._common.build_item_row_json` (the
    same builder ``sq tree --json`` renders its own nodes with, ``children`` populated the same
    way — see :func:`_view_json_child_rows`), ``subentity`` reuses
    :func:`~squads._cli._common.build_subentity_row_json` (the same builder ``sq <type> <n>
    <kind>s --json`` uses), ``role`` reuses
    :func:`~squads._cli._common.build_role_json_payload` (the same builder ``sq role <slug>
    show --json`` uses), ``self`` reuses :func:`~squads._cli._common.build_item_json` (the
    same builder an item's own ``show --json`` uses) plus :func:`_spec_identity_json`, and
    ``playbook`` is :func:`_playbook_json_payload`. No kind's output carries a
    ``fields``/``group_by``/``groups`` key: each shape is exactly what its own reused builder
    already produces, nothing added."""
    from squads._cli._common import (
        build_item_json,
        build_role_json_payload,
        build_subentity_row_json,
        role_base_for_show,
    )
    from squads._views import PlaybookSource, children_by_parent

    view, item, result = await svc.resolve_view_source(view_name, item_id)
    kind = view.source.kind

    if kind in ("ref", "subtree"):
        assert isinstance(result, list)
        items = cast("list[Item]", result)
        blocked_ids = {t.id for t, _ in await svc.blocked()}
        db = await svc.store.load()
        child_map = children_by_parent(db)
        return [
            build_item_row_json(
                ItemRowFields(
                    id=r.id,
                    type=r.type,
                    title=r.title,
                    status=r.status,
                    priority=r.badge_value("priority"),
                    assignee=r.assignee,
                    badge_value=r.badge_value,
                ),
                spec=spec,
                blocked_ids=blocked_ids,
                children=_view_json_child_rows(r.id, child_map, spec, blocked_ids, {r.id}),
            )
            for r in items
        ]

    if kind == "subentity":
        assert isinstance(result, list)
        subentities = cast("list[SubEntity]", result)
        return [
            build_subentity_row_json(
                local_id=r.local_id,
                title=r.title,
                status=r.status,
                assignee=r.assignee,
                severity=r.badge_value("severity"),
                story=r.story,
                deferred_to=r.deferred_to,
            )
            for r in subentities
        ]

    if kind == "role":
        # The role source's own applicability already guarantees `item` IS the role item —
        # `result` (the already-resolved `RoleDef`) is not reused here because
        # `build_role_json_payload` resolves its own, the same way `show_role` itself does.
        slug = item.slug
        base_role = role_base_for_show(slug, item, svc.catalog)
        return await build_role_json_payload(svc, slug, item.id, item, base_role, slug)

    if kind == "playbook":
        assert isinstance(result, PlaybookSource)
        return _playbook_json_payload(result)

    # "self" — the only remaining kind; resolves to the host item itself.
    payload: dict[str, object] = json.loads(await build_item_json(svc, item))
    payload["spec"] = _spec_identity_json(svc)
    return payload


@workflow_app.command("view")
@common.command
async def workflow_view(
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
    item_id: str = typer.Argument(..., metavar="ID", help="Item to resolve the view against."),
    json_out: bool = typer.Option(
        False, "--json", help="Print the resolved source as JSON, in its source's own shape."
    ),
) -> None:
    """Resolve one declared view against one item.

    Without `--json` the result renders through the view's template. `--json`
    prints the resolved source in the shape of the command it comes from, such as
    `sq tree --json` for a ref view.
    Fields: sq docs stability
    """
    from squads._cli._common import get_active_spec, get_service, print_json_clean

    svc = get_service()
    if json_out:
        payload = await _view_json_payload(svc, get_active_spec(), name, item_id)
        print_json_clean(json.dumps(payload))
        return
    console.print(await svc.render_view(name, item_id))


# ─── lint ─────────────────────────────────────────────────────────────────────


@workflow_app.command("lint")
@handle_errors
def workflow_lint() -> None:
    """Check the workflow override and list every error with a fix hint.

    It reads the override file directly, so it still runs when a broken spec stops
    other commands.

    Exit codes: 1 the spec has at least one error. See sq docs faq.
    """
    from squads._context import get_context
    from squads._paths import resolve
    from squads._transform import check_view_transforms
    from squads._workflow._loader import (
        WORKFLOW_OVERRIDE_FILENAME,
        lint_workflow_spec,
    )

    ctx = get_context()
    try:
        sp = resolve(client_cwd=ctx.client_cwd)
    except SquadsError as exc:
        console.print(f"[red]error[/red]: {e(common.error_text(exc))}", soft_wrap=True)
        raise typer.Exit(1) from exc

    squad_dir = sp.squad_dir
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME

    if not override_present(override_path):
        console.print(
            "[green]workflow spec OK[/green] — no override file found; using the bundled default."
        )
        return

    sources = common.invocation_sources(squad_dir)
    try:
        loaded = sources.workflow()
    except SquadsError:
        loaded = None
    findings = lint_workflow_spec(squad_dir, sources.files, loaded)
    if not any(f[0] == "error" for f in findings):
        findings.extend(
            (
                "error",
                f"views.{name}.transform",
                message,
                "fix or restore the file under .overrides/ (it is imported, not called).",
            )
            for name, message in check_view_transforms(sources.workflow(), squad_dir)
        )

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
