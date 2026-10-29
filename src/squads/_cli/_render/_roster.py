"""The roster renderers: the role catalog and listings, a role's, skill's or operator's show, and
the line each roster write prints."""

from collections.abc import Callable

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from squads._api._dto._display import Column
from squads._api._dto._operators import OperatorList, OperatorRow, OperatorShow
from squads._api._dto._roles import (
    DeveloperList,
    DeveloperRow,
    RoleCatalog,
    RoleCatalogRow,
    RoleDefaultMove,
    RoleList,
    RoleRow,
    RoleShow,
)
from squads._api._dto._roster import SeveredRef
from squads._api._dto._skills import SkillRefChange, SkillRefs, SkillRoleLink, SkillRow, SkillShow
from squads._cli._render._comments import is_styled, print_comments
from squads._cli._render._style import e, print_body
from squads._pronouns import named

_CHECK = "✓"


def _name(full_name: str, pronouns: str | None, *, style: str = "") -> Text:
    """*full_name* with the *pronouns* the squad shows, dimmed."""
    return named(full_name, pronouns, enabled=True, style=style)


def _table[R](
    console: Console,
    columns: list[Column],
    rows: list[R],
    cells: Callable[[R], dict[str, RenderableType]],
) -> None:
    table = Table(box=None, pad_edge=False)
    for column in columns:
        table.add_column(column.header)
    for row in rows:
        shown = cells(row)
        table.add_row(*(shown[column.key] for column in columns))
    console.print(table)


# ----------------------------------------------------------------------------- listings


def _catalog_cells(row: RoleCatalogRow) -> dict[str, RenderableType]:
    return {
        "slug": e(row.slug),
        "full_name": e(row.full_name),
        "title": e(row.title),
        "is_default": _CHECK if row.is_default else "",
        "origin": row.origin,
    }


def render_role_catalog(catalog: RoleCatalog, console: Console) -> None:
    """The catalog table, then how to add a role it does not declare."""
    _table(console, catalog.columns, catalog.items, _catalog_cells)
    console.print(
        "\n[dim]Need a role that is not in this catalog? "
        "Run [cyan]sq role add <slug> --name … --job-title … --desc … --mission …[/cyan], "
        "or build one from a role template with [cyan]sq role activate --from <template>[/cyan]."
        "[/dim]",
        soft_wrap=True,
    )


def _role_cells(row: RoleRow) -> dict[str, RenderableType]:
    return {
        "slug": e(row.slug),
        "display.name": _name(row.full_name, row.display.pronouns),
        "title": e(row.title),
        "capabilities": e(", ".join(row.capabilities)),
        "is_default": _CHECK if row.is_default else "",
        "origin": row.origin or "",
        "display.live": _CHECK if row.display.live else "",
    }


def render_role_list(listing: RoleList, console: Console) -> None:
    """The activated roles as a table."""
    _table(console, listing.columns, listing.items, _role_cells)


def _operator_cells(row: OperatorRow) -> dict[str, RenderableType]:
    return {
        "slug": e(row.slug),
        "display.name": _name(row.full_name, row.display.pronouns),
        "id": row.id,
        "status": e(row.status),
    }


def render_operator_list(listing: OperatorList, console: Console) -> None:
    """The registered people as a table."""
    _table(console, listing.columns, listing.items, _operator_cells)


def _developer_cells(row: DeveloperRow) -> dict[str, RenderableType]:
    return {
        "id": row.id,
        "slug": row.slug,
        "display.name": _name(row.full_name, row.display.pronouns),
        "tech": row.tech or "",
    }


def render_developer_list(listing: DeveloperList, console: Console) -> None:
    """The live developers as a table, or that there are none and how to add one."""
    if not listing.items:
        hint = " (try `sq dev add --tech <t>`)" if listing.template_available else ""
        console.print(f"[dim]no developers{hint}[/dim]", soft_wrap=True)
        return
    _table(console, listing.columns, listing.items, _developer_cells)


# ----------------------------------------------------------------------------- shows


def render_role_show(show: RoleShow, console: Console, *, raw: bool, comments: bool) -> None:
    """A role's card, then its definition and discussion, or how to activate it, then how to
    change it."""
    shown = show.display
    lane = ", ".join(show.create_lane) or "— (out-of-lane creates warn)"
    rows = [
        f"{_name(show.full_name, shown.pronouns, style='bold').markup} (`{e(show.slug)}`)",
        f"[bold]title:[/bold] {e(show.title)}",
        f"[bold]origin:[/bold] {show.origin or '—'}",
        f"[bold]model:[/bold] {e(show.model or 'inherit')}",
        f"[bold]color:[/bold] {e(shown.color or '—')}",
        f"[bold]can spawn:[/bold] {'yes' if show.can_spawn else 'no'}",
        f"[bold]capabilities:[/bold] {e(', '.join(show.capabilities) or '—')}",
        f"[bold]creates:[/bold] {e(lane)}",
        f"[bold]skills:[/bold] {e(', '.join(show.skills) or '—')}",
    ]
    console.print(Panel("\n".join(rows), expand=False))
    if shown.body is not None:
        if not shown.definition_resolves:
            console.print()
            console.print(
                f"[dim](the definition for {e(show.slug)} could not be resolved — "
                "`sq check` reports why, under role_base_resolves)[/dim]",
                soft_wrap=True,
            )
        print_body(
            console,
            shown.body,
            styled=is_styled(console) and not raw,
            empty_hint=shown.empty_hint or "",
        )
        if comments:
            print_comments(console, shown.discussion)
    else:
        console.print()
        console.print(
            f"[dim](no active item for {e(show.slug)} — run `sq role activate {e(show.slug)}`"
            " then `sq sync` to populate the full definition)[/dim]",
            soft_wrap=True,
        )
    console.print()
    console.print(f"[dim]{e(shown.change_hint)}[/dim]", soft_wrap=True)


def render_skill_show(show: SkillShow, console: Console, *, raw: bool, comments: bool) -> None:
    """A skill's panel, its body and, with *comments*, its discussion."""
    setter = "set by this squad" if show.operator_invocable_set else "declared default"
    rows = [
        f"[bold]{show.id}[/bold] {e(show.title)}",
        f"[bold]slug:[/bold] {show.slug}",
        f"[bold]origin:[/bold] {show.origin or '—'}",
        f"[bold]status:[/bold] {show.status}",
        f"[bold]operator invocable:[/bold] {'yes' if show.operator_invocable else 'no'} ({setter})",
        f"[bold]file:[/bold] {show.path}",
    ]
    if show.when_to_use:
        rows.append(f"[bold]when to use:[/bold] {e(show.when_to_use)}")
    console.print(Panel("\n".join(rows), expand=False))
    print_body(
        console,
        show.display.body,
        styled=is_styled(console) and not raw,
        empty_hint=show.display.empty_hint,
    )
    if comments:
        print_comments(console, show.display.discussion)


def render_operator_show(
    show: OperatorShow, console: Console, *, raw: bool, comments: bool
) -> None:
    """An operator's panel, their body and, with *comments*, their discussion."""
    rows = [
        _name(show.full_name, show.display.pronouns, style="bold").markup,
        f"[bold]slug:[/bold] {e(show.slug)}",
        f"[bold]id:[/bold] {show.id}",
        f"[bold]status:[/bold] {show.status}",
        f"[bold]file:[/bold] {show.path}",
    ]
    console.print(Panel("\n".join(rows), expand=False))
    print_body(
        console,
        show.display.body,
        styled=is_styled(console) and not raw,
        empty_hint=f'(empty — write their profile with `sq operator {show.slug} body -m "…"`)',
    )
    if comments:
        print_comments(console, show.display.discussion)


def render_skill_refs(refs: SkillRefs, console: Console) -> None:
    """One line per ref the skill carries, then one per ref carried to it."""
    for entries, label in ((refs.out, "→ refs"), (refs.incoming, "← backrefs")):
        for entry in entries or []:
            console.print(f"{label}  {e(entry.id)}  [dim]{entry.kind}[/dim]")


# ----------------------------------------------------------------------------- writes


def render_named_entry(verb: str, row: RoleRow | OperatorRow, console: Console) -> None:
    """A role or operator written under its name: ``<verb> Name (slug) ID``."""
    name = _name(row.full_name, row.display.pronouns).markup
    console.print(f"{verb} [bold]{name}[/bold] (`{row.slug}`) {row.id}")


def render_skill_added(row: SkillRow, console: Console) -> None:
    """The skill created and its file."""
    console.print(f"created skill [bold]{row.id}[/bold] → {row.path}")


def render_updated(entry_id: str, console: Console) -> None:
    """An entry whose fields an update changed."""
    console.print(f"updated {entry_id}")


def render_body_written(entry_id: str, console: Console, *, append: bool) -> None:
    """An entry whose body was set or appended to."""
    console.print(f"{entry_id}: body {'appended' if append else 'set'}")


def render_regenerated(entry_id: str, console: Console) -> None:
    """An entry whose pointer was regenerated."""
    console.print(f"regenerated pointer for {entry_id}")


def render_removed(entry_id: str, console: Console) -> None:
    """An entry deleted for good."""
    console.print(f"removed {entry_id}")


def render_default_move(move: RoleDefaultMove, console: Console) -> None:
    """Where the default designation now is, and each role it left."""
    if not move.changed:
        console.print(f"{move.entry.id} already the default — no change")
        return
    console.print(f"{move.entry.id} is now the default")
    for cleared in move.cleared:
        console.print(f"  cleared {e(cleared)}")


def render_status_move(
    entry_id: str, status: str, severed: list[SeveredRef], console: Console, *, unlink: bool
) -> None:
    """The move an entry made and, with *unlink*, each ref it removed."""
    console.print(f"{entry_id} → [bold]{status}[/bold]")
    if not unlink:
        return
    if not severed:
        console.print("  --unlink: no references severed (nothing was severable)")
    for sev in severed:
        console.print(f"  severed {e(sev.referrer)} → {e(sev.target)} ({sev.kind})")


def render_view_change(
    entry_id: str, view: str, console: Console, *, enable: bool, changed: bool, was_present: bool
) -> None:
    """What a view add or disable did to the tag."""
    if enable:
        outcome = "placed in sq:body" if changed else "already present, unchanged"
    elif not changed:
        outcome = "already disabled, unchanged"
    elif not was_present:
        outcome = "had no existing tag — placed disabled in sq:body"
    else:
        outcome = "disabled in sq:body"
    console.print(f"{entry_id}: view {e(view)} {outcome}")


def render_ref_change(change: SkillRefChange, console: Console) -> None:
    """The ref a skill gained, with its kind, or lost."""
    if change.kind is None:
        console.print(f"removed {change.entry.id} → {change.target}")
    else:
        console.print(f"{change.entry.id} → {change.target} ([dim]{change.kind}[/dim])")


def render_role_link(link: SkillRoleLink, console: Console, *, linked: bool) -> None:
    """The role a skill was scoped to or unscoped from."""
    verb = "scoped to" if linked else "unscoped from"
    console.print(f"{link.entry.id} {verb} {link.role} (role resynced)")
