"""`sq memory <role> ...` — a role's committed notebook of small, agent-authored facts.

Grammar:
  sq memory <role> list                     — print the index (one line per memory)
  sq memory <role> search <query>           — memories whose content matches
  sq memory <role> show <slug>              — full body of one memory
  sq memory <role> add "<fact>" [--file f] [--slug s]  — jot a new memory
  sq memory <role> forget <slug>            — delete one

Role is a positional subject, consistent with `sq inbox <role>` / `sq mine <role>`: resolved
once in the group callback against the roster (agents + operators), raising a clean
SquadsError on an unknown slug — never a stack trace. Memory is a lighter tier than an item
(see `squads._memory._store`) so, unlike the `sq <type> <n> ...` groups, there is no
counter-allocated id to resolve here — only the role slug and, for `show`/`forget`, the memory's
own stable slug.

Resolved against the **full** roster vocabulary, not just live slugs — a role's own
notebook (like `sq inbox`/`sq mine`) is read-scoped to that role, not authorship attributed to
it on someone else's item, so a retired role's memory stays reachable for review.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer

import squads._cli._common as common
from squads._cli._common import (
    console,
    e,
    get_service,
    print_json_clean,
    render_body_text,
    resolve_body_optional,
    resolve_slug_or_raise,
)

memory_app = typer.Typer(
    no_args_is_help=True,
    help="A role's committed memory notebook (list/search/show/add/forget).",
)

_ROLE_KEY = "role_slug"


def _role(ctx: typer.Context) -> str:
    return ctx.obj[_ROLE_KEY]


@memory_app.callback()
@common.command
async def _resolve_role(
    ctx: typer.Context,
    role: str = typer.Argument(..., help="Role slug (e.g. python-dev or op-alice)."),
) -> None:
    svc = get_service()
    ctx.obj = {_ROLE_KEY: await resolve_slug_or_raise(role, svc, live_only=False)}


@memory_app.command("list")
@common.command
async def list_memories(ctx: typer.Context, json_out: bool = typer.Option(False, "--json")) -> None:
    """Print the role's memory index: one line per memory (slug + summary).

    Exit codes: 0 = a clean listing, 4 = one or more memory files could not be read (the
    readable memories are still listed, so a short exit-4 pool is never mistaken for a
    genuinely smaller one). The skipped files are named on stderr: one ``error: <message>``
    line each in human mode, or one ``{"omitted": [...]}`` JSON line under ``--json``. The
    ``--json`` array shape is unchanged either way.
    """
    role_slug = _role(ctx)
    svc = get_service()
    entries, unreadable = await svc.memory_list(role_slug)
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "slug": m.slug,
                        "filename": f"{m.slug}.md",
                        "description": m.summary,
                        "created_at": m.created_at,
                    }
                    for m in entries
                ]
            )
        )
        common.report_omissions(unreadable, json_out=True)
        return
    if not entries:
        console.print(f"[dim]no memories for {e(role_slug)}[/dim]")
    else:
        for m in entries:
            console.print(f"[bold]{e(m.slug)}[/bold]  {e(m.summary)}")
    common.report_omissions(unreadable, json_out=False)


@memory_app.command("search")
@common.command
async def search_memories(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Memories whose summary or body contains the query text.

    Same degrade-signal rule as `sq memory <role> list`: exit 0 = a clean search, 4 = one or
    more memory files could not be read, reported the same way — an ``error: <message>`` line
    per skipped file in human mode, one compact ``{"omitted": [...]}`` JSON line under
    ``--json``.
    """
    role_slug = _role(ctx)
    svc = get_service()
    hits, unreadable = await svc.memory_search(role_slug, query)
    if json_out:
        print_json_clean(
            json.dumps(
                [{"slug": m.slug, "description": m.summary, "hits": lines} for m, lines in hits]
            )
        )
        common.report_omissions(unreadable, json_out=True)
        return
    if not hits:
        console.print(f"[dim]no matches for {e(query)}[/dim]")
    else:
        for m, lines in hits:
            console.print(f"[bold]{e(m.slug)}[/bold]  {e(m.summary)}")
            for ln in lines[:3]:
                console.print(f"    {e(ln)}")
    common.report_omissions(unreadable, json_out=False)


@memory_app.command("show")
@common.command
async def show_memory(
    ctx: typer.Context,
    slug: str = typer.Argument(..., help="Memory slug."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Print one memory's full body, addressed by slug (not index position)."""
    role_slug = _role(ctx)
    svc = get_service()
    entry = await svc.memory_show(role_slug, slug)
    if json_out:
        print_json_clean(
            json.dumps(
                {
                    "slug": entry.slug,
                    "summary": entry.summary,
                    "created_at": entry.created_at,
                    "tags": list(entry.tags),
                    "body": entry.body,
                }
            )
        )
        return
    console.print(f"[bold]{e(entry.slug)}[/bold] [dim]({e(entry.created_at)})[/dim]")
    if entry.tags:
        console.print(f"[dim]tags: {e(', '.join(entry.tags))}[/dim]")
    render_body_text(entry.body)


@memory_app.command("add")
@common.command
async def add_memory(
    ctx: typer.Context,
    fact: str = typer.Argument(
        ...,
        help="A snappy one-line summary of the memory (also the default slug source); "
        "put the detailed write-up in --file.",
    ),
    file: str | None = typer.Option(
        None, "--file", help="Read a longer body from PATH ('-' for stdin)."
    ),
    slug: str | None = typer.Option(
        None, "--slug", help="Name the handle explicitly instead of deriving it from the fact."
    ),
) -> None:
    """Jot a new memory to the role's pool; regenerates the role's index."""
    role_slug = _role(ctx)
    svc = get_service()
    body = resolve_body_optional(None, file)
    entry = await svc.memory_add(role_slug, fact, body=body, slug=slug)
    console.print(f"remembered [bold]{e(entry.slug)}[/bold] for {e(role_slug)}")


@memory_app.command("forget")
@common.command
async def forget_memory(
    ctx: typer.Context, slug: str = typer.Argument(..., help="Memory slug.")
) -> None:
    """Delete one memory for real (history retained in git); regenerates the index."""
    role_slug = _role(ctx)
    svc = get_service()
    await svc.memory_forget(role_slug, slug)
    console.print(f"forgot [bold]{e(slug)}[/bold] for {e(role_slug)}")
