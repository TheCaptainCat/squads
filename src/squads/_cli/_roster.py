"""What the role, skill and operator groups share: the address their verbs read, the body, remove
and status verbs mounted on each by one registration, and how a roster write prints its
notices."""

from collections.abc import Callable
from typing import Any, Protocol

import typer

import squads._cli._common as common
from squads._api._api import Operation
from squads._api._dto._roster import (
    RosterBodyRequest,
    RosterRemoveRequest,
    RosterStatusRequest,
    SeveredRef,
)
from squads._api._response import Response
from squads._cli import _calls as calls
from squads._cli._render._roster import (
    render_body_written,
    render_removed,
    render_status_move,
)

#: The ``ctx.obj`` key of the address as typed, which the operation resolves.
ADDR_KEY = "addr"


class Entry(Protocol):
    """What a roster write prints of the entry it wrote."""

    @property
    def id(self) -> str: ...

    @property
    def status(self) -> str: ...


class EntryWrite(Protocol):
    """A roster write that reports nothing beside the entry it wrote."""

    @property
    def entry(self) -> Entry: ...


class StatusMove(Protocol):
    """A roster status move: the entry, and the refs a retirement removed."""

    @property
    def entry(self) -> Entry: ...

    @property
    def severed(self) -> list[SeveredRef]: ...


def address_of(ctx: typer.Context) -> str:
    """The address the group parsed."""
    return ctx.obj[ADDR_KEY]


def parse_address(ctx: typer.Context, addr: str) -> None:
    """Keep *addr* for the verb's operation, which resolves it within its own roster kind."""
    ctx.obj = {ADDR_KEY: addr}


def json_option(help: str) -> Any:
    """``--json``, printing what *help* names."""
    return typer.Option(False, "--json", help=help)


def print_entry_warnings(response: Response[Any]) -> None:
    """The notices a roster write raised, each on its own ``warning:`` line after the write's
    own; one the invocation already printed is not repeated."""
    printed = common.printed_notices()
    common.print_warnings([w for w in response.warnings if w not in printed])


def finish_write[Res](
    op: Operation[Any, Res],
    response: Response[Res],
    json_out: bool,
    render: Callable[[Res], None],
) -> None:
    """Print a roster write: its ``data`` with *json_out*, else *render* then its notices."""
    if json_out:
        calls.print_json(op, response)
        return
    render(response.data)
    print_entry_warnings(response)


def register_write_verbs[W: EntryWrite](
    addr_app: typer.Typer,
    *,
    body: Operation[RosterBodyRequest, W],
    remove: Operation[RosterRemoveRequest, W],
) -> None:
    """Mount ``body`` and ``remove`` (with its hidden ``rm``) on a roster host, each calling the
    host's own operation."""

    @common.handle_errors
    def body_verb(
        ctx: typer.Context,
        message: list[str] = common.message_option(),
        file: str | None = common.file_option(),
        append: bool = common.append_option(),
        force: bool = common.replace_body_option(),
        as_: str | None = common.edit_as_option(),
        json_out: bool = json_option("Print one JSON object: the entry after the write."),
    ) -> None:
        """Set or append to the body.

        Replacing a body someone has already written is refused unless `--force`.
        A role takes prose beside its generated definition. A body generated from a
        declared view (a system or per-type skill) is refused even with `--force`;
        an operator body is never refused for it.
        """
        text = common.resolve_body(message or None, file)
        common.declare_actor(as_)
        request = RosterBodyRequest(addr=address_of(ctx), text=text, append=append, force=force)
        response = calls.call(body, request)
        finish_write(
            body,
            response,
            json_out,
            lambda write: render_body_written(write.entry.id, common.console, append=append),
        )

    @common.handle_errors
    def remove_verb(
        ctx: typer.Context,
        purge: bool = typer.Option(
            False, "--purge", help="Delete the file too; remove refuses without it."
        ),
        as_: str | None = common.edit_as_option(),
        json_out: bool = json_option("Print one JSON object: the entry removed."),
    ) -> None:
        """Delete this entry for good; it needs `--purge`.

        To keep it on record instead, move it to its archived status
        (see `sq workflow lifecycles`).
        """
        common.declare_actor(as_)
        response = calls.call(remove, RosterRemoveRequest(addr=address_of(ctx), purge=purge))
        finish_write(
            remove, response, json_out, lambda write: render_removed(write.entry.id, common.console)
        )

    addr_app.command("body")(body_verb)
    addr_app.command("remove")(remove_verb)
    addr_app.command("rm", hidden=True)(remove_verb)


def register_roster_status_verb[M: StatusMove](
    addr_app: typer.Typer, *, status: Operation[RosterStatusRequest, M]
) -> None:
    """Mount ``status`` on a roster host, calling the host's own operation; ``--unlink`` is
    offered only here, since only roster entries carry the links a retirement checks."""

    @common.handle_errors
    def status_verb(
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="status", help=common.MOVE_STATUS_HELP),
        force: bool = common.force_transition_option(
            "Make a transition the lifecycle does not allow; a change that would leave "
            "the config invalid is still refused."
        ),
        unlink: bool = typer.Option(
            False,
            "--unlink",
            help=(
                "On a retirement, remove the skill-to-role link the refusal names, then "
                "check again; refused on any other transition."
            ),
        ),
        as_: str | None = common.edit_as_option(),
        json_out: bool = json_option(
            "Print one JSON object: the entry after the move and the refs it severed."
        ),
    ) -> None:
        """Move this entry to another status."""
        common.declare_actor(as_)
        request = RosterStatusRequest(
            addr=address_of(ctx), status=common.parse_status(new_status), force=force, unlink=unlink
        )
        response = calls.call(status, request)
        finish_write(
            status,
            response,
            json_out,
            lambda move: render_status_move(
                move.entry.id, move.entry.status, move.severed, common.console, unlink=unlink
            ),
        )

    addr_app.command("status")(status_verb)
