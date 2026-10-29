"""The item write renderers: what a create, update, body, retype, remove, ref, view, comment or
sub-entity write did."""

from rich.console import Console

from squads._api._dto._comment_writes import (
    CommentAdded,
    CommentEdited,
    CommentSelection,
    CommentShown,
)
from squads._api._dto._item_writes import (
    ItemCreated,
    ItemRefAdded,
    ItemRefRemoved,
    ItemRemoved,
    ItemRetyped,
    ItemUpdated,
    SubentityAdded,
    SubentityRemoved,
)
from squads._api._dto._items import Comment
from squads._cli._render._comments import is_styled, print_comments_plain, print_comments_styled
from squads._cli._render._style import e


def render_created(created: ItemCreated, console: Console) -> None:
    """The created item's id and file, then the out-of-lane advisory when there is one."""
    console.print(f"created [bold]{created.id}[/bold] → {created.display.file}")
    if created.lane_warning is not None:
        console.print(e(created.lane_warning))


def render_updated(updated: ItemUpdated, console: Console) -> None:
    """The updated item and its file, or that it had no assignee to clear."""
    entry = updated.entry
    if updated.nothing_to_clear:
        console.print(f"{entry.id} has no assignee to clear")
    else:
        console.print(f"updated {entry.id}  [dim]{entry.path}[/dim]")


def render_retyped(retyped: ItemRetyped, console: Console) -> None:
    """The item's id before and after, its status and how many files had their refs
    rewritten."""
    entry = retyped.entry
    console.print(
        f"retyped {e(retyped.old_id)} → [bold]{e(entry.id)}[/bold]  [dim]{entry.path}[/dim]"
    )
    if retyped.status_reset:
        console.print(
            f"  status reset: {e(retyped.old_status)} → [yellow]{e(entry.status)}[/yellow]"
            f" (workflows differ)"
        )
    else:
        console.print(f"  status carried: [bold]{e(entry.status)}[/bold]")
    if retyped.rewritten:
        console.print(f"  rewritten refs in {len(retyped.rewritten)} file(s)")


def render_item_removed(removed: ItemRemoved, console: Console) -> None:
    """The removed item, and the items whose refs to it were cut."""
    console.print(f"removed {e(removed.removed_id)}")
    if removed.severed_refs:
        console.print(f"  severed refs in: {', '.join(e(r) for r in removed.severed_refs)}")


def render_ref_added(changed: ItemRefAdded, console: Console) -> None:
    """The ref added: the item, the target and the kind."""
    console.print(f"{changed.entry.id} → {changed.target} ([dim]{changed.kind}[/dim])")


def render_ref_removed(changed: ItemRefRemoved, console: Console) -> None:
    """The ref removed: the item and the target."""
    console.print(f"removed {changed.entry.id} → {changed.target}")


def _local(scope: str | None) -> tuple[str, str] | None:
    """A sub-entity discussion's ``(kind, local id)``, ``None`` for an item's own."""
    if scope is None:
        return None
    kind, _, local = scope.partition(":")
    return kind, local


def comment_label(item: str, scope: str | None) -> str:
    """The discussion a comment is in: the item, or the item and the sub-entity's local id."""
    sub = _local(scope)
    return item if sub is None else f"{item} {sub[1]}"


def render_comment_added(added: CommentAdded, console: Console) -> None:
    """Where the comment was added, and who wrote it."""
    entry = added.entry
    console.print(f"commented on {comment_label(entry.item, entry.scope)} as {entry.author_slug}")


def render_comment_shown(shown: CommentShown, console: Console, *, raw: bool) -> None:
    """The discussion the comment is in, then the comment as a pane or as delimited text."""
    sub = _local(shown.scope)
    where = shown.item if sub is None else f"{shown.item} · {sub[0]} {sub[1]}"
    console.print(where, markup=False, highlight=False)
    if is_styled(console) and not raw:
        print_comments_styled(console, [shown])
    else:
        print_comments_plain(console, [shown])


def render_comment_edited(edited: CommentEdited, console: Console) -> None:
    """The comment's displayed hash before and after the edit, or that nothing changed."""
    old = edited.previous
    label = comment_label(edited.item, edited.scope)
    if edited.changed:
        console.print(
            f"edited {old.short_hash} on {label} ({old.author_slug}, {old.ts}); "
            f"now {edited.short_hash}",
            markup=False,
            highlight=False,
        )
    else:
        console.print(f"{old.short_hash} on {label} is unchanged; nothing written")


def _first_line(cmt: Comment) -> str:
    return (cmt.body.splitlines() or [""])[0]


def render_comment_removal(group: CommentSelection, console: Console) -> None:
    """One line per comment a removal would delete: its time, author and first line."""
    for cmt in group.items:
        console.print(
            f"{cmt.ts} {cmt.author_slug}: {_first_line(cmt)}", markup=False, highlight=False
        )


def render_comment_removed(group: CommentSelection, console: Console) -> None:
    """The removed comment's displayed hash, where it was, and how many copies went."""
    count = "" if len(group.items) == 1 else f" ({len(group.items)} copies)"
    console.print(
        f"removed {group.items[0].short_hash} from {comment_label(group.item, group.scope)}{count}"
    )


def render_subentity_added(added: SubentityAdded, console: Console) -> None:
    """The new sub-entity, the command that sets its body, and the over-long-title advisory."""
    console.print(f"added [bold]{added.local_id}[/bold] to {added.display.item}")
    console.print(
        f"  set its body:  [cyan]{e(added.display.body_command)}[/cyan]"
        "  [dim](or --file body.md / --file -)[/dim]",
        soft_wrap=True,
    )
    if added.title_advisory is not None:
        console.print(e(added.title_advisory))


def render_subentity_removed(removed: SubentityRemoved, console: Console) -> None:
    """The removed sub-entity and the item it was removed from."""
    console.print(f"removed {removed.removed} from {removed.item}")
