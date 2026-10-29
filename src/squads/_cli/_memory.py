"""`sq memory <role> ...` — a role's committed notebook of small, agent-authored facts.

Grammar:
  sq memory <role> list                     — print the index (one line per memory)
  sq memory <role> search <query>           — memories whose content matches
  sq memory <role> show <slug>              — full body of one memory
  sq memory <role> add "<fact>" [--file f] [--slug s]  — jot a new memory
  sq memory <role> forget <slug>            — delete one

The role is a positional subject like `sq inbox <role>` / `sq mine <role>`, which the group
callback only takes; each operation resolves it against the full roster (agents and operators,
retired included) and refuses an unknown slug. The notebook is read-scoped to the role, not
authorship on someone else's item, so a retired role's memory stays reachable. Memory has no
counter-allocated id (see `squads._memory._store`); `show`/`forget` take the memory's slug.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._memory import (
    MemoryAddRequest,
    MemoryForgetRequest,
    MemoryListRequest,
    MemorySearchRequest,
    MemoryShowRequest,
)
from squads._cli import _calls as calls
from squads._cli._common import console, handle_errors, resolve_body_optional
from squads._cli._render._memory import (
    render_added,
    render_forgotten,
    render_memories,
    render_memory,
    render_search,
)

memory_app = typer.Typer(
    no_args_is_help=True,
    help="Read and write a role's memory notebook.",
)

_ROLE_KEY = "role_slug"


def _role(ctx: typer.Context) -> str:
    return ctx.obj[_ROLE_KEY]


@memory_app.callback()
def _take_role(
    ctx: typer.Context,
    role: str = typer.Argument(..., help="Role or operator slug, such as `python-dev`."),
) -> None:
    ctx.obj = {_ROLE_KEY: role}


@memory_app.command("list")
@handle_errors
def list_memories(
    ctx: typer.Context,
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per memory."
    ),
) -> None:
    """List the role's memories, one line each: slug and summary.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    response = calls.call(ops.MEMORY_LIST, MemoryListRequest(role=_role(ctx)))
    if json_out:
        calls.print_json(ops.MEMORY_LIST, response)
    else:
        calls.print_warnings(response)
        render_memories(response.data, console)
    calls.finish(response, json_out=json_out)


@memory_app.command("search")
@handle_errors
def search_memories(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per matching memory."
    ),
) -> None:
    """Find the role's memories whose summary or body contains text.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    response = calls.call(ops.MEMORY_SEARCH, MemorySearchRequest(role=_role(ctx), query=query))
    if json_out:
        calls.print_json(ops.MEMORY_SEARCH, response)
    else:
        calls.print_warnings(response)
        render_search(response.data, console)
    calls.finish(response, json_out=json_out)


@memory_app.command("show")
@handle_errors
def show_memory(
    ctx: typer.Context,
    slug: str = typer.Argument(..., help="Memory slug, as `sq memory <role> list` prints it."),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the memory."),
) -> None:
    """Print one memory in full, addressed by its slug."""
    response = calls.call(ops.MEMORY_SHOW, MemoryShowRequest(role=_role(ctx), slug=slug))
    if json_out:
        calls.print_json(ops.MEMORY_SHOW, response)
    else:
        calls.print_warnings(response)
        render_memory(response.data, console)


@memory_app.command("add")
@handle_errors
def add_memory(
    ctx: typer.Context,
    fact: str = typer.Argument(
        ...,
        help="One-line summary of the memory, which also names its slug; "
        "put the detail in `--file`.",
    ),
    file: str | None = common.file_option("Read the memory's body from a file; `-` reads stdin."),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to file the memory under instead of one made from the summary."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the memory written and its role."
    ),
) -> None:
    """Add a memory to the role's notebook."""
    request = MemoryAddRequest(
        role=_role(ctx), summary=fact, body=resolve_body_optional(None, file), slug=slug
    )
    response = calls.call(ops.MEMORY_ADD, request)
    if json_out:
        calls.print_json(ops.MEMORY_ADD, response)
    else:
        calls.print_warnings(response)
        render_added(response.data, console)


@memory_app.command("forget")
@handle_errors
def forget_memory(
    ctx: typer.Context,
    slug: str = typer.Argument(..., help="Memory slug, as `sq memory <role> list` prints it."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the memory as it was and its role."
    ),
) -> None:
    """Delete one memory; git history still holds it."""
    response = calls.call(ops.MEMORY_FORGET, MemoryForgetRequest(role=_role(ctx), slug=slug))
    if json_out:
        calls.print_json(ops.MEMORY_FORGET, response)
    else:
        calls.print_warnings(response)
        render_forgotten(response.data, console)
