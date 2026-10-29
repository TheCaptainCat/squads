"""The memory renderers: a role's notebook listed and searched, one memory shown, added and
forgotten."""

from rich.console import Console

from squads._api._dto._memory import Memory, MemoryAdded, MemoryForgotten, MemoryList, MemorySearch
from squads._cli._render._style import e


def render_memories(listing: MemoryList, console: Console) -> None:
    """One line per memory: its slug and summary."""
    if not listing.items:
        console.print(f"[dim]no memories for {e(listing.role)}[/dim]")
        return
    for m in listing.items:
        console.print(f"[bold]{e(m.slug)}[/bold]  {e(m.description)}")


def render_search(found: MemorySearch, console: Console) -> None:
    """Each memory that matched, with up to three of its matching lines."""
    if not found.items:
        console.print(f"[dim]no matches for {e(found.query)}[/dim]")
        return
    for m in found.items:
        console.print(f"[bold]{e(m.slug)}[/bold]  {e(m.description)}")
        for line in m.hits[:3]:
            console.print(f"    {e(line)}")


def render_memory(memory: Memory, console: Console) -> None:
    """The memory's slug, time and tags, then its body: markdown on a terminal, plain text
    otherwise."""
    console.print(f"[bold]{e(memory.slug)}[/bold] [dim]({e(memory.created_at)})[/dim]")
    if memory.tags:
        console.print(f"[dim]tags: {e(', '.join(memory.tags))}[/dim]")
    console.print()
    if not memory.body:
        console.print(f"[dim]{e('(empty — set it with `body`)')}[/dim]")
    elif console.is_terminal and not console.no_color:
        from rich.markdown import Markdown

        console.print(Markdown(memory.body))
    else:
        console.print(memory.body, markup=False, highlight=False)


def render_added(added: MemoryAdded, console: Console) -> None:
    console.print(f"remembered [bold]{e(added.entry.slug)}[/bold] for {e(added.role)}")


def render_forgotten(forgotten: MemoryForgotten, console: Console) -> None:
    console.print(f"forgot [bold]{e(forgotten.entry.slug)}[/bold] for {e(forgotten.role)}")
