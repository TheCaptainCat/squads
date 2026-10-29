"""The workflow renderers: the cheatsheet, one table per catalog, a resolved view and the lint
report."""

from collections.abc import Callable, Sequence

from rich.console import Console
from rich.table import Table
from rich.text import Text

from squads._api._dto._display import Column
from squads._api._dto._workflow import (
    Cheatsheet,
    CollectionCatalog,
    CollectionRow,
    LifecycleCatalog,
    LifecycleRow,
    LintFinding,
    LintReport,
    RefKindCatalog,
    RefKindRow,
    StatusCatalog,
    StatusRoleCatalog,
    StatusRoleRow,
    StatusRow,
    SubentityKindCatalog,
    SubentityKindRow,
    TypeCatalog,
    TypeRow,
    ViewCatalog,
    ViewResult,
    ViewRow,
)
from squads._cli._render._style import e, status_text


def render_cheatsheet(cheatsheet: Cheatsheet, console: Console, *, raw: bool) -> None:
    """The cheatsheet as markdown, or its source text verbatim with *raw*."""
    if raw:
        console.print(cheatsheet.markdown, markup=False, highlight=False, soft_wrap=True)
    else:
        from rich.markdown import Markdown

        console.print(Markdown(cheatsheet.markdown))


def _yes(flag: bool) -> str:
    return "yes" if flag else ""


def _optional(value: str | None) -> str:
    return e(value) if value else ""


def _table[R](
    console: Console, columns: list[Column], rows: Sequence[R], cell: Callable[[R, str], str | Text]
) -> None:
    table = Table(box=None, pad_edge=False)
    for column in columns:
        table.add_column(column.header)
    for row in rows:
        table.add_row(*(cell(row, column.key) for column in columns))
    console.print(table)


def _order(order: float | None) -> str:
    if order is None:
        return ""
    return str(int(order)) if order.is_integer() else str(order)


def _type_cell(row: TypeRow, key: str) -> str:
    match key:
        case "order":
            return _order(row.order)
        case "reserved":
            return _yes(row.reserved)
        case _:
            return e(getattr(row, key))


def render_types(catalog: TypeCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _type_cell)


def _subentity_kind_cell(row: SubentityKindRow, key: str) -> str:
    if key == "fields":
        return e(", ".join(f.code for f in row.fields))
    return e(getattr(row, key))


def render_subentity_kinds(catalog: SubentityKindCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _subentity_kind_cell)


def _lifecycle_cell(row: LifecycleRow, key: str) -> str:
    match key:
        case "states":
            return e(", ".join(row.states))
        case "transitions":
            return e(", ".join(f"{t['from']} → {t['to']}" for t in row.transitions))
        case _:
            return e(getattr(row, key))


def render_lifecycles(catalog: LifecycleCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _lifecycle_cell)


def _collection_cell(row: CollectionRow, key: str) -> str:
    match key:
        case "ordered":
            return _yes(row.ordered)
        case "default":
            return _optional(row.default)
        case "badges":
            return e(", ".join(f"{b.emoji or ''} {b.code}".strip() for b in row.badges))
        case _:
            return e(getattr(row, key))


def render_collections(catalog: CollectionCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _collection_cell)


def _status_cell(row: StatusRow, key: str) -> str | Text:
    match key:
        case "status":
            return status_text(row.status, row.display.intent)
        case "role":
            return _optional(row.role)
        case _:
            return _optional(row.badge)


def render_statuses(catalog: StatusCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _status_cell)


def _role_cell(row: StatusRoleRow, key: str) -> str:
    value: object = getattr(row, key)
    return _yes(value) if isinstance(value, bool) else e(value)


def render_roles(catalog: StatusRoleCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _role_cell)


def _ref_kind_cell(row: RefKindRow, key: str) -> str:
    if key in ("kind", "label"):
        return e(getattr(row, key))
    return _optional(getattr(row, key))


def render_ref_kinds(catalog: RefKindCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _ref_kind_cell)


def _view_cell(row: ViewRow, key: str) -> str:
    if key == "source_name":
        return _optional(row.source_name)
    return e(getattr(row, key))


def render_views(catalog: ViewCatalog, console: Console) -> None:
    _table(console, catalog.columns, catalog.items, _view_cell)


def render_view(result: ViewResult, console: Console) -> None:
    console.print(result.output or "")


def _findings(
    console: Console, title: str, style: str, label: str, found: list[LintFinding]
) -> None:
    table = Table(title=title, show_header=True, header_style=style)
    table.add_column("location", style="dim")
    table.add_column(label)
    table.add_column("fix hint", style="dim")
    for f in found:
        table.add_row(e(f.location), e(f.message), e(f.fix_hint))
    console.print(table)


def render_lint(report: LintReport, console: Console) -> None:
    """The errors and the warnings, each in its table, then the verdict."""
    errors, warnings = report.errors, report.warnings
    if not report.override:
        console.print(
            "[green]workflow spec OK[/green] — no override file found; using the bundled default."
        )
        return
    if not errors and not warnings:
        console.print("[green]workflow spec OK[/green] — no errors or warnings.")
        return
    if errors:
        _findings(console, "workflow spec errors", "red", "error", errors)
    if warnings:
        _findings(console, "workflow spec warnings", "yellow", "warning", warnings)
    if errors:
        console.print(
            f"[red]{len(errors)} error(s)[/red]"
            + (f", {len(warnings)} warning(s)" if warnings else "")
            + " — fix the errors above then re-run `sq workflow lint`."
        )
    else:
        console.print(f"[green]workflow spec OK[/green] — {len(warnings)} warning(s); no errors.")
