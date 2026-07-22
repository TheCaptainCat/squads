"""`sq workflow` — workflow cheatsheet + spec validation surface.

Sub-commands:
- ``sq workflow`` / ``sq workflow show``  — print the team cheatsheet.
- ``sq workflow lint``                   — verbose collect-all-errors spec validation.

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

from squads._cli._common import console, e, handle_errors
from squads._errors import SquadsError

if TYPE_CHECKING:
    from squads._workflow._models import WorkflowSpec

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help=(
        "Workflow cheatsheet and spec validation.\n\n"
        "Run `sq workflow` (or `sq workflow show`) for the team cheatsheet. "
        "Run `sq workflow lint` to validate your workflow override spec. "
        "Run `sq workflow types` / `collections` / `statuses` / `roles` for the "
        "machine-readable type / badge-collection / status / role catalogs."
    ),
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


_RAW_HELP = "Plain markdown output (opt out of Rich markdown render)."


@workflow_app.callback()
def workflow_default(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help=_RAW_HELP),
) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        _print_cheatsheet(raw=raw)


@workflow_app.command("show")
def workflow_show(raw: bool = typer.Option(False, "--raw", help=_RAW_HELP)) -> None:
    """Print the team workflow cheatsheet (who writes what, how items link)."""
    _print_cheatsheet(raw=raw)


def _print_cheatsheet(*, raw: bool) -> None:
    """Render the cheatsheet — Rich markdown by default, clean markdown text with ``--raw``.

    ``--raw`` prints the ``workflow.md.j2`` render verbatim (markdown tables + fenced
    ```mermaid``` blocks, no box-drawing/ANSI), mirroring the ``sq show --raw`` / ``sq docs``
    precedent: opt out of ``rich.Markdown`` rendering, print the source text as-is.
    """
    from squads._cli._common import get_active_spec
    from squads._rendering._engine import render

    content = render("workflow.md.j2", spec=get_active_spec())
    if raw:
        console.print(content, markup=False, highlight=False, soft_wrap=True)
    else:
        console.print(Markdown(content))


# ─── types ────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow types --json`` catalog. Kept as a module-level
#: tuple so a test can assert the CLI never drifts from the declared contract.
TYPE_CATALOG_FIELDS: tuple[str, str, str, str, str, str] = (
    "type",
    "order",
    "prefix",
    "reserved",
    "category",
    "fields",
)

#: Frozen field set for each entry of a type-catalog row's ``fields`` array.
TYPE_FIELD_ENTRY_FIELDS: tuple[str, str, str] = ("code", "label", "collection")


def _type_fields(t: str, spec: WorkflowSpec) -> list[dict[str, object]]:
    """The field->collection bindings declared for type *t* — a client resolves field
    code -> collection code here, then collection code -> vocabulary via ``sq workflow
    collections --json``."""
    return [
        {"code": f.code, "label": f.label, "collection": f.collection} for f in spec.fields_for(t)
    ]


def _type_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen type-catalog rows, ascending resolved ``order`` (type-name string
    tiebreak — the same ordering the CLI uses to register per-type commands).

    Includes every declared type (work AND reserved: role/skill/operator). ``order`` is
    ``None`` when ``ItemSpec.order`` is unset (``+inf``) — present-but-null, never
    omitted, so the key set stays stable across every row. ``category`` is the type's
    declared ``roster``/``work``/``records`` axis (the same taxonomy ``reserved``
    already summarizes as a boolean) — a client reads it here instead of re-deriving the
    split from ``reserved`` or a hardcoded type list. ``fields`` is the type's declared
    field->collection bindings — ``[]`` for a type with no badge fields.
    """
    types = sorted(spec.items, key=lambda t: (spec.items[t].order, t))
    return [
        {
            "type": t,
            "order": None if math.isinf(spec.items[t].order) else spec.items[t].order,
            "prefix": spec.items[t].prefix,
            "reserved": spec.items[t].category == "roster",
            "category": spec.items[t].category,
            "fields": _type_fields(t, spec),
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
    string breaks ties): ``{type, order, prefix, reserved, category, fields}``. ``order``
    is ``null`` when the type has no explicit order (``+inf``); ``category`` is one of
    ``roster``/``work``/``records`` (``reserved`` is exactly ``category == "roster"``);
    ``fields`` is the type's declared field->collection bindings
    (``[{code, label, collection}]``, ``[]`` if none) — present, never omitted, so the
    key set is stable across every object.
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
    ``role.settled``/``not role.settled`` on that catalog."""
    return [
        {
            "status": name,
            "role": st.role,
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
        table.add_row(
            e(str(row["status"])),
            e(str(row["role"])) if row["role"] else "",
            e(str(row["badge"])) if row["badge"] else "",
        )
    console.print(table)


# ─── roles ───────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow roles --json`` catalog.
ROLE_CATALOG_FIELDS: tuple[str, str, str, str] = ("role", "settled", "hidden", "color")


def _role_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen role-catalog rows, ascending role name — a client joins a status's ``role``
    (from ``sq workflow statuses --json``) to this catalog to resolve ``settled``/``hidden``/
    ``color`` instead of hardcoding any role name or deriving it from category."""
    return [
        {
            "role": name,
            "settled": r.settled,
            "hidden": r.hidden,
            "color": r.color,
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
    declared role, ascending role name: ``{role, settled, hidden, color}``. ``settled`` is
    the old ``terminal`` (a resting/end state); ``hidden`` is default-visibility; ``color``
    is a semantic colour intent from the closed palette (``positive``/``danger``/``warning``/
    ``muted``/``neutral``/``info``) — each client maps it to a concrete colour, with a
    neutral fallback for an intent it doesn't recognise. A status references one role by name
    (``sq workflow statuses --json``'s ``role`` field); join the two to resolve behaviour.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _role_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Role", "Settled", "Hidden", "Color"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["role"])),
            "yes" if row["settled"] else "",
            "yes" if row["hidden"] else "",
            e(str(row["color"])),
        )
    console.print(table)


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
        console.print(f"[red]error[/red]: {e(str(exc))}")
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
