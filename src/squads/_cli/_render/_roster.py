"""The roster renderers: the role catalog and listings, a role's, skill's or operator's show, and
the line each roster write prints."""

from collections.abc import Callable

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from squads._api import (
    Column,
    Comment,
    DeveloperList,
    DeveloperRow,
    OperatorList,
    OperatorRow,
    OperatorShow,
    RoleCatalog,
    RoleCatalogRow,
    RoleDefaultMove,
    RoleList,
    RoleRow,
    RoleShow,
    SeveredRef,
    SkillRefChange,
    SkillRefs,
    SkillRoleLink,
    SkillRow,
    SkillShow,
)
from squads._cli._render._comments import is_styled, print_comments
from squads._cli._render._raw import print_raw, raw_discussion, raw_head
from squads._cli._render._rows import Row, panel_text, raw_lines
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


def _print_raw_entry(
    console: Console,
    rows: list[Row],
    body: str,
    discussion: list[Comment] | None,
    *,
    no_header: bool,
) -> None:
    """A roster entry's raw show: its rows as a list, the body and, given *discussion*, its
    comments. The body carries its own heading."""
    lines = [*raw_head(rows, None, no_header=no_header), body]
    if discussion is not None:
        raw_discussion(lines, discussion)
    print_raw(console, lines)


def _role_rows(show: RoleShow) -> list[Row]:
    shown = show.display
    name = _name(show.full_name, shown.pronouns, style="bold")
    lane = ", ".join(show.create_lane) or "— (out-of-lane creates warn)"
    caps = ", ".join(show.capabilities) or "—"
    skills = ", ".join(show.skills) or "—"
    model = show.model or "inherit"
    color = shown.color or "—"
    can_spawn = "yes" if show.can_spawn else "no"
    origin = show.origin or "—"
    return [
        Row(
            None,
            f"{_name(show.full_name, shown.pronouns).plain} (`{show.slug}`)",
            f"{name.markup} (`{e(show.slug)}`)",
        ),
        Row("title", show.title, e(show.title)),
        Row("origin", origin, origin),
        Row("model", model, e(model)),
        Row("color", color, e(color)),
        Row("can spawn", can_spawn, can_spawn),
        Row("capabilities", caps, e(caps)),
        Row("creates", lane, e(lane)),
        Row("skills", skills, e(skills)),
    ]


def _raw_role(show: RoleShow, console: Console, *, no_header: bool, comments: bool) -> None:
    shown = show.display
    if shown.body is None:
        hint = f"(no active item for {show.slug}: run `sq role activate {show.slug}`)"
        lines = [] if no_header else [*raw_lines(_role_rows(show)), ""]
        print_raw(console, [*lines, hint])
        return
    _print_raw_entry(
        console,
        _role_rows(show),
        shown.body,
        shown.discussion if comments else None,
        no_header=no_header,
    )


def render_role_show(
    show: RoleShow, console: Console, *, raw: bool, no_header: bool = False, comments: bool
) -> None:
    """A role's card, then its definition and discussion, or how to activate it, then how to
    change it; *raw* prints plain markdown instead, with *no_header* the body alone."""
    if raw:
        _raw_role(show, console, no_header=no_header, comments=comments)
        return
    shown = show.display
    console.print(Panel(panel_text(_role_rows(show)), expand=False))
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


def _skill_rows(show: SkillShow) -> list[Row]:
    setter = "set by this squad" if show.operator_invocable_set else "declared default"
    invocable = f"{'yes' if show.operator_invocable else 'no'} ({setter})"
    origin = show.origin or "—"
    rows = [
        Row(None, f"{show.id} {show.title}", f"[bold]{show.id}[/bold] {e(show.title)}"),
        Row("slug", show.slug, show.slug),
        Row("origin", origin, origin),
        Row("status", show.status, show.status),
        Row("operator invocable", invocable, invocable),
        Row("file", show.path, show.path),
    ]
    if show.when_to_use:
        rows.append(Row("when to use", show.when_to_use, e(show.when_to_use)))
    return rows


def render_skill_show(
    show: SkillShow, console: Console, *, raw: bool, no_header: bool = False, comments: bool
) -> None:
    """A skill's panel, its body and, with *comments*, its discussion; *raw* prints plain
    markdown instead, with *no_header* the body alone."""
    if raw:
        _print_raw_entry(
            console,
            _skill_rows(show),
            show.display.body,
            show.display.discussion if comments else None,
            no_header=no_header,
        )
        return
    console.print(Panel(panel_text(_skill_rows(show)), expand=False))
    print_body(
        console,
        show.display.body,
        styled=is_styled(console) and not raw,
        empty_hint=show.display.empty_hint,
    )
    if comments:
        print_comments(console, show.display.discussion)


def _operator_rows(show: OperatorShow) -> list[Row]:
    return [
        Row(
            None,
            _name(show.full_name, show.display.pronouns).plain,
            _name(show.full_name, show.display.pronouns, style="bold").markup,
        ),
        Row("slug", show.slug, e(show.slug)),
        Row("id", show.id, show.id),
        Row("status", show.status, show.status),
        Row("file", show.path, show.path),
    ]


def render_operator_show(
    show: OperatorShow, console: Console, *, raw: bool, no_header: bool = False, comments: bool
) -> None:
    """An operator's panel, their body and, with *comments*, their discussion; *raw* prints plain
    markdown instead, with *no_header* the body alone."""
    if raw:
        _print_raw_entry(
            console,
            _operator_rows(show),
            show.display.body,
            show.display.discussion if comments else None,
            no_header=no_header,
        )
        return
    console.print(Panel(panel_text(_operator_rows(show)), expand=False))
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


def render_roster_updated(entry_id: str, console: Console) -> None:
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
