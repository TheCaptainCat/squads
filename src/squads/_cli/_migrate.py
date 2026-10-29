"""`sq migrate` — run schema migrations and read their steps.

- `sq migrate up`                          run the automatic migration(s) for this squad
- `sq migrate help`                        the migration changelog index (every shipped migration)
- `sq migrate chlog vA..vB`                the complete manual steps for migrating across a
                                            release range
- `sq migrate rename-type OLD NEW`         bulk-rename every OLD-type item to NEW type
- `sq migrate rename-status TYPE OLD NEW`  bulk-move every TYPE item at OLD status to NEW status
"""

import typer

import squads._cli._common as common
from squads._cli._common import (
    console,
    e,
    get_service,
    get_service_bypassing_index_cross_check,
    handle_errors,
)
from squads._cli._render._package import render_migrations, render_steps
from squads._errors import SquadsError
from squads._index._reconcile import ReconcileResult
from squads._migrations._registry import MIGRATIONS, Migration, manual_steps, migration_index
from squads._models._schema import SCHEMA_VERSION, schema_tuple

migrate_app = typer.Typer(no_args_is_help=True, help="Run schema migrations and read their steps.")


def _reconcile_line(result: ReconcileResult) -> str:
    """One line for what the index rebuild before the runners changed."""
    parts: list[str] = []
    if result.indexed:
        parts.append(f"indexed {', '.join(e(i) for i in result.indexed)}")
    if result.missing:
        parts.append(f"dropped {', '.join(e(i) for i in result.missing)} (no file backs it)")
    return f"  index reconciled with the files: {'; '.join(parts)}"


@migrate_app.callback()
def migrate_gate(ctx: typer.Context) -> None:
    """Gate each ``sq migrate`` command by the grant it declares."""
    common.gate_group_command(ctx, migrate_app)


def migrate_grants() -> dict[str, common.GateGrant]:
    """The grant each ``sq migrate`` command declares, by command name."""
    return common.grants_by_command(migrate_app)


@migrate_app.command("up")
@common.past_the_gate(common.Ground.MIGRATION, behind=True)
@common.command
async def migrate_up():
    """Migrate this squad to the schema of the installed squads.

    It ends with the same index rebuild as `sq repair`, which can rewrite item
    content.

    Exit codes: 1 not migrated, or the rebuild was incomplete. See sq docs faq.
    """
    # Exit 1 on an incomplete trailing rebuild matches `sq repair`, so a caller gating on `$?`
    # sees the same answer from either route to the same corpus state.
    svc = get_service_bypassing_index_cross_check(bundled_fallback=False)
    disk = svc.paths.config.schema_version
    if schema_tuple(disk) > schema_tuple(SCHEMA_VERSION):
        raise SquadsError(
            f"this squad is at schema v{disk}, newer than this squads (v{SCHEMA_VERSION}); "
            "upgrade the squads package"
        )
    run = await svc.run_pending_migrations()
    applied = run.applied
    if not applied:
        console.print(f"already at schema v{SCHEMA_VERSION}; nothing to migrate")
        return
    if run.reconcile and (run.reconcile.indexed or run.reconcile.missing):
        console.print(_reconcile_line(run.reconcile), soft_wrap=True)
    for m in applied:
        count = run.changed.get(m.to_schema)
        changed_suffix = f" — {count} changed" if count else ""
        console.print(
            f"  {m.version} (schema v{m.from_schema}→v{m.to_schema}): "
            f"{e(m.summary)}{changed_suffix}"
        )
        for line in run.reports.get(m.to_schema, ()):
            console.print(f"    {e(line)}", soft_wrap=True)
        skipped_ids = run.skipped.get(m.to_schema, [])
        if skipped_ids:
            console.print(
                f"  [yellow]skipped[/yellow] {len(skipped_ids)} item(s) rather than abort the "
                f"run: {', '.join(e(i) for i in skipped_ids)} — a missing body region needs one "
                "added by hand; a body carrying "
                "content this step has no model for is left exactly as it was — `sq check` "
                "(reachable once this run completes) names which applies to each. Once the "
                "item's own problem is fixed and it genuinely carries no tag, place one with "
                "`sq <type> <n> view add <name>` (a role or skill instead addresses by slug: "
                "`sq role|skill <slug> view add <name>`); an item already carrying the tag "
                "outside its own region needs its own different fix — placing another copy "
                "inside the region would duplicate it, so delete the outside line from the "
                "file by hand first, then place it with the same `view add`",
                soft_wrap=True,
            )
    if run.config_dropped:
        console.print(
            "  [yellow]dropped[/yellow] from .squads.toml (not read by squads): "
            f"{', '.join(e(k) for k in run.config_dropped)}",
            soft_wrap=True,
        )
    console.print(
        f"[green]migrated[/green] to schema v{SCHEMA_VERSION}; index rebuilt — "
        "run `sq sync` to regenerate the agent files "
        "(pointers, skills, CLAUDE.md/AGENTS.md sections)",
        soft_wrap=True,
    )
    # The rebuild this command runs is also the corpus sweep, and this is the only route a
    # squad behind the current schema takes — so the content diff is announced here too, in
    # the same sentence `sq repair` prints. "index rebuilt" above describes the index alone.
    notice = run.repair.strip_notice() if run.repair else None
    if notice:
        console.print(notice, soft_wrap=True)
    # Files that could not be read or parsed during the rebuild, reported as `sq repair`
    # does. The exit check below includes them, so printing nothing would leave a failing
    # exit code with no stated cause.
    for msg in run.repair.unreadable if run.repair else []:
        console.print(common.unreadable_report(msg), soft_wrap=True)
    if any(m.manual for m in applied):
        span = _manual_chlog_span(applied)
        console.print(
            f"[yellow]manual steps remain[/yellow] — read them with `sq migrate chlog {span}`",
            soft_wrap=True,
        )
    # The condition `sq repair` exits 1 for: the trailing repair is the same rebuild, so a
    # caller gating on `$?` gets the same partial-vs-clean answer from either verb. The
    # body-tag-convergence sweep is strict and has no skip channel to gate on.
    if run.repair and run.repair.unreadable:
        raise typer.Exit(1)


@migrate_app.command("help")
@common.past_the_gate(common.Ground.NO_SQUAD_STATE, behind=True, ahead=True)
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
@common.past_the_gate(common.Ground.NO_SQUAD_STATE, behind=True, ahead=True)
@handle_errors
def migrate_chlog(
    span: str = typer.Argument(
        ...,
        metavar="vFROM..vTO",
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
@common.command
async def migrate_repad(
    new_width: int = typer.Argument(
        ..., metavar="WIDTH", help="Digits to pad item numbers to; more than the current width."
    ),
):
    """Widen the zero padding of item numbers and rename every file to match.

    One-way: the padding cannot be narrowed again. Only filenames change, never
    file contents. Run `sq check` afterwards.
    """
    svc = get_service()
    db = await svc.store.load()
    current = db.padding
    renamed = await svc.repad(new_width)
    console.print(
        f"[green]repad done[/green]: padding {current} → {new_width}; "
        f"{renamed} file(s) renamed; index rebuilt"
    )
    console.print("  run [cyan]`sq check`[/cyan] to verify integrity", soft_wrap=True)


@migrate_app.command("rename-type")
@common.command
async def migrate_rename_type(
    old_type: str = typer.Argument(..., metavar="OLD_TYPE", help="Declared type to rename from."),
    new_type: str = typer.Argument(..., metavar="NEW_TYPE", help="Declared type to rename to."),
):
    """Move every item of one type to another, with the new prefix and folder.

    Both types must already be declared, non-roster types; this does not declare
    NEW_TYPE. Run `sq check` afterwards.
    """
    svc = get_service()
    result = await svc.rename_type(old_type, new_type)
    console.print(
        f"[green]rename-type done[/green]: {e(old_type)} → {e(new_type)}, "
        f"{result.renamed} item(s) renamed; index rebuilt"
    )
    console.print("  run [cyan]`sq check`[/cyan] to verify integrity", soft_wrap=True)


@migrate_app.command("rename-status")
@common.command
async def migrate_rename_status(
    item_type: str = typer.Argument(
        ..., metavar="TYPE", help="Declared type whose items carry the status."
    ),
    old_status: str = typer.Argument(
        ..., metavar="OLD_STATUS", help="Status value to rename from."
    ),
    new_status: str = typer.Argument(..., metavar="NEW_STATUS", help="Status value to rename to."),
):
    """Relabel a status on every item of one type, without a transition.

    NEW_STATUS must already be in TYPE's lifecycle. Run `sq check` afterwards.
    """
    svc = get_service()
    result = await svc.rename_status(item_type, old_status, new_status)
    console.print(
        f"[green]rename-status done[/green]: {e(item_type)}: {e(old_status)} → {e(new_status)}, "
        f"{result.renamed} item(s) renamed"
    )
    console.print("  run [cyan]`sq check`[/cyan] to verify integrity", soft_wrap=True)


def _parse_span(span: str) -> tuple[str, str]:
    lo, sep, hi = span.partition("..")
    if not sep:
        raise SquadsError(f"expected a range like v0.1.1..v0.2.0, got {span!r}")
    return lo.strip().lstrip("vV"), hi.strip().lstrip("vV")


def _manual_chlog_span(applied: list[Migration]) -> str:
    """The release span ``(lo, hi]`` holding every migration in ``applied``, for ``migrate_chlog``.

    ``hi`` is the last applied migration's version (``applied`` is a suffix of ``MIGRATIONS``, in
    registry order). ``lo`` is the version of the entry just before the first applied one, so the
    open-at-``lo`` filter never yields an empty span; when the first applied migration is
    ``MIGRATIONS[0]``, ``lo`` is ``"0"``, which ``_parse_span``/``version_tuple`` accept and which
    sorts below every release.
    """
    hi = applied[-1].version
    first_index = MIGRATIONS.index(applied[0])
    lo = MIGRATIONS[first_index - 1].version if first_index > 0 else "0"
    return f"v{lo}..v{hi}"
