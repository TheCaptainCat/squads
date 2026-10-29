"""The corpus-wide operations: repair, renumber, the migrations, the repad, the bulk renames and
the import, each answering with its report."""

from collections.abc import Sequence

from squads._api._dto._squad import (
    AppliedMigration,
    ImportFindingRow,
    ImportIssueRow,
    ImportReport,
    ImportRequest,
    MigrateRequest,
    MigrationReport,
    Reconciled,
    RenamedId,
    RenameStatusReport,
    RenameStatusRequest,
    RenameTypeReport,
    RenameTypeRequest,
    Renumbered,
    RenumberReport,
    RenumberRequest,
    RepadReport,
    RepadRequest,
    RepairReport,
    RepairRequest,
)
from squads._api._response import Response
from squads._context import get_context
from squads._migrations._registry import MIGRATIONS, Migration
from squads._models._schema import SCHEMA_VERSION
from squads._services._import import ImportMixin
from squads._services._maintenance import MaintenanceMixin
from squads._services._rename import RenameMixin
from squads._services._results import ImportResult, SelfRemedied

#: What follows an unreadable file's message when the message names no remedy of its own.
_CARRIED_FORWARD = (
    " — its previous index entry, if any, was carried forward as-is; fix the file and repair again"
)


def unreadable_lines(messages: Sequence[str]) -> list[str]:
    """One sentence per file a rebuild could not read: the message, then the carried-forward
    remedy unless the message names its own."""
    return [m if isinstance(m, SelfRemedied) else f"{m}{_CARRIED_FORWARD}" for m in messages]


def _manual_span(applied: list[Migration]) -> str:
    """The ``sq migrate chlog`` range ``vLO..vHI`` holding every migration in *applied*, a suffix
    of the registry: *HI* is the last one's release and *LO* the release before the first, or
    ``0`` when the first is the oldest migration."""
    first_index = MIGRATIONS.index(applied[0])
    lo = MIGRATIONS[first_index - 1].version if first_index > 0 else "0"
    return f"v{lo}..v{applied[-1].version}"


def _import_report(result: ImportResult, *, dry_run: bool) -> ImportReport:
    """The plan of a refused or dry run, or the outcome of an applied one; an applied run's
    issues are its findings, level intact, and it is ``ok`` while none is an error."""
    plan, applied = result.plan, result.applied
    if applied is None:
        return ImportReport(
            op_counts=dict(plan.op_counts.counts),
            handle_to_id=dict(plan.handle_to_id),
            handle_to_sub={h: list(v) for h, v in plan.handle_to_sub.items()},
            issues=[ImportIssueRow(line=i.line, message=i.message) for i in plan.issues],
            ok=plan.ok,
            applied=False,
            dry_run=dry_run,
            created_ids=[],
            warnings=[],
        )
    return ImportReport(
        op_counts=dict(applied.op_counts.counts),
        handle_to_id=dict(applied.handle_to_id),
        handle_to_sub={h: list(v) for h, v in applied.handle_to_sub.items()},
        issues=[
            ImportFindingRow(level=f.level, item=f.item, message=f.message, rule=f.rule)
            for f in applied.findings
        ],
        ok=not applied.error_findings,
        applied=True,
        dry_run=dry_run,
        created_ids=list(applied.created_ids),
        warnings=list(applied.warnings),
    )


class CorpusOpsMixin(ImportMixin, MaintenanceMixin, RenameMixin):
    async def repair_squad(self, req: RepairRequest) -> Response[RepairReport]:
        """Rebuild the index from the item files, renumbering a shared number first on request."""
        result = await self.repair(renumber=req.renumber)
        return Response(
            data=RepairReport(
                indexed=len(result.db.items),
                counter=result.db.counter,
                notice=result.strip_notice(),
                missing=list(result.missing_ids),
                unreadable=unreadable_lines(result.unreadable),
                renumbered=list(result.renumber_report),
                references_left=result.references_left,
            )
        )

    async def renumber_squad(self, req: RenumberRequest) -> Response[RenumberReport]:
        """Move this branch's item numbers past another branch's."""
        result = await self.renumber(from_seq=req.from_seq, onto=req.onto, by=req.by)
        moved = sorted(result.remap.items(), key=lambda pair: pair[1])
        return Response(
            data=RenumberReport(
                moved=[Renumbered(old=old, new=new) for old, new in moved],
                counter=result.db.counter,
                warning=result.warning,
                notice=result.strip_notice(),
            )
        )

    async def migrate_squad(self, req: MigrateRequest) -> Response[MigrationReport]:
        """Run every migration the squad is behind on, then rebuild its index."""
        run = await self.run_pending_migrations()
        reconcile = run.reconcile
        applied = [
            AppliedMigration(
                version=m.version,
                from_schema=m.from_schema,
                to_schema=m.to_schema,
                summary=m.summary,
                changed=run.changed.get(m.to_schema, 0),
                reports=list(run.reports.get(m.to_schema, ())),
                skipped=list(run.skipped.get(m.to_schema, [])),
                manual=bool(m.manual),
            )
            for m in run.applied
        ]
        return Response(
            data=MigrationReport(
                schema_version=SCHEMA_VERSION,
                applied=applied,
                reconciled=(
                    Reconciled(indexed=list(reconcile.indexed), missing=list(reconcile.missing))
                    if reconcile is not None
                    else None
                ),
                config_dropped=list(run.config_dropped),
                notice=run.repair.strip_notice() if run.repair else None,
                unreadable=unreadable_lines(run.repair.unreadable if run.repair else []),
                manual_span=(
                    _manual_span(run.applied) if any(m.manual for m in run.applied) else None
                ),
            )
        )

    async def repad_squad(self, req: RepadRequest) -> Response[RepadReport]:
        """Widen the padding of item numbers and rename every file to match."""
        previous = (await self.store.load()).padding
        renamed = await self.repad(req.width)
        return Response(data=RepadReport(previous=previous, width=req.width, renamed=renamed))

    async def rename_type_items(self, req: RenameTypeRequest) -> Response[RenameTypeReport]:
        """Move every item of one type to another."""
        result = await self.rename_type(req.old_type, req.new_type)
        return Response(
            data=RenameTypeReport(
                old_type=req.old_type,
                new_type=req.new_type,
                renamed=result.renamed,
                ids=[RenamedId(old=old, new=new) for old, new in result.ids],
            )
        )

    async def rename_status_items(self, req: RenameStatusRequest) -> Response[RenameStatusReport]:
        """Relabel a status on every item of one type."""
        result = await self.rename_status(req.type, req.old_status, req.new_status)
        return Response(
            data=RenameStatusReport(
                type=req.type,
                old_status=req.old_status,
                new_status=req.new_status,
                renamed=result.renamed,
            )
        )

    async def import_squad_events(self, req: ImportRequest) -> Response[ImportReport]:
        """Check the events, then apply them in one transaction unless a dry run or a problem
        stops it; an event with no time of its own takes the request's clock."""
        result = await self.import_events(
            req.text,
            default_at=get_context().clock_override,
            default_as=req.default_as,
            dry_run=req.dry_run,
        )
        return Response(data=_import_report(result, dry_run=req.dry_run))
