"""`sq migrate` — run schema migrations and read their steps.

- `sq migrate up`                          run the automatic migration(s) for this squad
- `sq migrate help`                        the migration changelog index (every shipped migration)
- `sq migrate chlog vA..vB`                the complete manual steps for migrating across a
                                            release range
- `sq migrate rename-type OLD NEW`         bulk-rename every OLD-type item to NEW type
- `sq migrate rename-status TYPE OLD NEW`  bulk-move every TYPE item at OLD status to NEW status
- `sq migrate rename-field OLD NEW`        move the values stored under key OLD to key NEW
- `sq migrate rename-kind OLD NEW`         bring the stored spellings of kind OLD to kind NEW
"""

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._squad import (
    MigrateRequest,
    RenameFieldRequest,
    RenameKindRequest,
    RenameStatusRequest,
    RenameTypeRequest,
    RepadRequest,
)
from squads._cli import _calls as calls
from squads._cli._common import console, handle_errors
from squads._cli._render._package import render_migrations, render_steps
from squads._cli._render._squad import (
    render_migration,
    render_rename_field,
    render_rename_kind,
    render_rename_status,
    render_rename_type,
    render_repad,
)
from squads._errors import SquadsError
from squads._migrations._registry import manual_steps, migration_index
from squads._models._item import MAX_ID_PADDING
from squads._util import is_version, version_tuple

migrate_app = typer.Typer(no_args_is_help=True, help="Run schema migrations and read their steps.")


@migrate_app.command("up")
@handle_errors
def migrate_up(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the migrations run and what they did."
    ),
):
    """Migrate this squad to the schema of the installed squads.

    It ends with the same index rebuild as `sq repair`, which can rewrite item
    content.

    Exit codes: 1 not migrated, or the rebuild was incomplete. See sq docs faq.
    """
    response = calls.call(ops.MIGRATE, MigrateRequest())
    report = response.data
    if json_out:
        calls.print_json(ops.MIGRATE, response)
    else:
        calls.print_warnings(response)
        render_migration(report, console)
    # The condition `sq repair` exits 1 for: the trailing rebuild is the same one, so a caller
    # gating on `$?` gets the same partial-vs-clean answer from either verb.
    if report.unreadable:
        raise typer.Exit(1)


@migrate_app.command("help")
@handle_errors
def migrate_help(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: every migration squads ships."
    ),
):
    """List every migration squads ships, oldest first."""
    index = migration_index()
    if json_out:
        common.print_json_clean(index.model_dump_json())
        return
    render_migrations(index, console)


@migrate_app.command("chlog")
@handle_errors
def migrate_chlog(
    span: str = typer.Argument(
        ...,
        metavar="vfrom..vto",
        help="Releases after vFROM up to and including vTO, such as `v0.1.1..v0.2.0`.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the migrations with manual steps."
    ),
):
    """Print the manual steps of the migrations in a release range."""
    steps = manual_steps(*_parse_span(span))
    if json_out:
        common.print_json_clean(steps.model_dump_json())
        return
    render_steps(steps, console)


@migrate_app.command("repad")
@handle_errors
def migrate_repad(
    new_width: int = typer.Argument(
        ...,
        metavar="width",
        help=f"Digits to pad item numbers to: above the current width, up to {MAX_ID_PADDING}.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the padding before and after."
    ),
):
    """Widen the zero padding of item numbers and rename every file to match.

    One-way: the padding cannot be narrowed again. Only filenames change, never
    file contents. Run `sq check` afterwards.
    """
    response = calls.call(ops.REPAD, RepadRequest(width=new_width))
    if json_out:
        calls.print_json(ops.REPAD, response)
        return
    calls.print_warnings(response)
    render_repad(response.data, console)


@migrate_app.command("rename-type")
@handle_errors
def migrate_rename_type(
    old_type: str = typer.Argument(..., metavar="old_type", help="Declared type to rename from."),
    new_type: str = typer.Argument(..., metavar="new_type", help="Declared type to rename to."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the items moved and their new ids."
    ),
):
    """Move every item of one type to another, with the new prefix and folder.

    Both types must already be declared, non-roster types; this does not declare
    NEW_TYPE. Run `sq check` afterwards.
    """
    request = RenameTypeRequest(old_type=old_type, new_type=new_type)
    response = calls.call(ops.RENAME_TYPE, request)
    if json_out:
        calls.print_json(ops.RENAME_TYPE, response)
        return
    calls.print_warnings(response)
    render_rename_type(response.data, console)


@migrate_app.command("rename-status")
@handle_errors
def migrate_rename_status(
    item_type: str = typer.Argument(
        ..., metavar="type", help="Declared type whose items carry the status."
    ),
    old_status: str = typer.Argument(
        ..., metavar="old_status", help="Status value to rename from."
    ),
    new_status: str = typer.Argument(..., metavar="new_status", help="Status value to rename to."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: how many items were relabelled."
    ),
):
    """Relabel a status on every item of one type, without a transition.

    NEW_STATUS must already be in TYPE's lifecycle. Run `sq check` afterwards.
    """
    request = RenameStatusRequest(type=item_type, old_status=old_status, new_status=new_status)
    response = calls.call(ops.RENAME_STATUS, request)
    if json_out:
        calls.print_json(ops.RENAME_STATUS, response)
        return
    calls.print_warnings(response)
    render_rename_status(response.data, console)


@migrate_app.command("rename-field")
@handle_errors
def migrate_rename_field(
    old: str = typer.Argument(..., metavar="old", help="Stored key to move values from."),
    new: str = typer.Argument(..., metavar="new", help="Declared key to move them to."),
    types: list[str] = typer.Option(
        [], "--type", help="Move only the item key of this type (repeatable)."
    ),
    kinds: list[str] = typer.Option(
        [], "--kind", help="Move only the entry key of this sub-entity kind (repeatable)."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: how many items and entries were moved."
    ),
):
    """Move the values stored under key OLD to key NEW.

    Covers items and sub-entity entries, or only the given --type and --kind
    scopes. Refuses, changing nothing, when a holder does not declare NEW,
    already holds it, or holds a value NEW does not accept. Run `sq check`
    afterwards.
    """
    request = RenameFieldRequest(old=old, new=new, types=types, kinds=kinds)
    response = calls.call(ops.RENAME_FIELD, request)
    if json_out:
        calls.print_json(ops.RENAME_FIELD, response)
        return
    calls.print_warnings(response)
    render_rename_field(response.data, console)


@migrate_app.command("rename-kind")
@handle_errors
def migrate_rename_kind(
    old: str = typer.Argument(..., metavar="old", help="Kind name the block markers carry."),
    new: str = typer.Argument(..., metavar="new", help="Declared kind to bring them to."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: how many items were rewritten."
    ),
):
    """Bring the stored spellings of kind OLD to the declaration of kind NEW.

    Rewrites block markers, the container marker, local ids and mappings. Refuses,
    changing nothing, when NEW is undeclared, a type does not host it, an item
    mixes prefixes or a marker pair is missing. Run `sq check` afterwards.
    """
    request = RenameKindRequest(old=old, new=new)
    response = calls.call(ops.RENAME_KIND, request)
    if json_out:
        calls.print_json(ops.RENAME_KIND, response)
        return
    calls.print_warnings(response)
    render_rename_kind(response.data, console)


def _parse_span(span: str) -> tuple[str, str]:
    expected = f"expected a range like v0.1.1..v0.2.0 (vFROM..vTO, FROM below TO), got {span!r}"
    lo, sep, hi = span.partition("..")
    if not sep:
        raise SquadsError(expected)
    lo, hi = lo.strip().lstrip("vV"), hi.strip().lstrip("vV")
    if not (is_version(lo) and is_version(hi)):
        raise SquadsError(expected)
    if version_tuple(lo) >= version_tuple(hi):
        raise SquadsError(expected)
    return lo, hi
