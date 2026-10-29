"""The squad-state operations: the board, memory notebooks, the workflow cheatsheet, catalogs,
views and lint, overrides, the reflog, check and sync, each answering with its DTO."""

from typing import TYPE_CHECKING, cast

from squads import __version__
from squads._actor import current_actor
from squads._api._dto._board import (
    BoardClearRequest,
    BoardListRequest,
    BoardPostRequest,
    Notice,
    NoticeList,
    NoticeRow,
    NoticeWrite,
)
from squads._api._dto._check import (
    CheckIssueRow,
    CheckReport,
    CheckRequest,
    SyncReport,
    SyncRequest,
)
from squads._api._dto._memory import (
    Memory,
    MemoryAdded,
    MemoryAddRequest,
    MemoryForgetRequest,
    MemoryForgotten,
    MemoryHit,
    MemoryList,
    MemoryListRequest,
    MemoryRow,
    MemorySearch,
    MemorySearchRequest,
    MemoryShowRequest,
)
from squads._api._dto._overrides import (
    OverrideDiff,
    OverrideDiffRequest,
    OverrideDiffRow,
    OverrideFile,
    OverrideList,
    OverrideListRequest,
    OverrideRow,
    OverrideScaffoldRequest,
    OverrideUpdateRequest,
    ScaffoldedOverride,
    StampedOverrides,
)
from squads._api._dto._reflog import Reflog, ReflogEntryRow, ReflogRequest
from squads._api._dto._workflow import (
    CatalogRequest,
    Cheatsheet,
    CheatsheetRequest,
    CollectionCatalog,
    LifecycleCatalog,
    LintFinding,
    LintReport,
    LintRequest,
    RefKindCatalog,
    StatusCatalog,
    StatusRoleCatalog,
    SubentityKindCatalog,
    TypeCatalog,
    ViewCatalog,
    ViewResolveRequest,
    ViewResult,
)
from squads._api._response import Response
from squads._board._model import BoardNotice
from squads._errors import PlaybookConfigError, SquadsError
from squads._interactions._playbook import get_playbook_spec
from squads._memory._model import MemoryEntry
from squads._overrides._service import (
    STATE_BROKEN,
    STATE_DRIFTED,
    OverrideEntry,
    diff_override,
    scaffold_playbook,
    scaffold_role,
    scaffold_roles_catalog,
    scaffold_template,
    scaffold_workflow,
    scan_overrides,
    update_stamp,
)
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import role_base_from_item
from squads._services._board import BoardMixin
from squads._services._catalogs import (
    collection_catalog,
    lifecycle_catalog,
    ref_kind_catalog,
    role_catalog,
    status_catalog,
    subentity_kind_catalog,
    type_catalog,
    view_catalog,
)
from squads._services._check import CheckMixin
from squads._services._items import ItemsMixin
from squads._services._maintenance import MaintenanceMixin
from squads._services._memory import MemoryMixin
from squads._services._refs import RefsMixin
from squads._services._results import CheckIssue, check_issue_sort_key
from squads._services._subentities import SubentitiesMixin
from squads._services._view_source import view_source
from squads._services._views import ViewsMixin
from squads._spec_documents import resolve_workflow
from squads._specload import override_present
from squads._transform import check_view_transforms
from squads._workflow import ROSTER_ROLE
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, lint_workflow_spec, refusal_cause

if TYPE_CHECKING:
    from squads._services._service import Service

#: The remedy named for a broken override whose file reads but lacks a required region.
_BROKEN_REGION = (
    "{name} is broken (a required sq region is missing); "
    "run `sq override list` for the state of every override"
)


def _notice(notice: BoardNotice) -> Notice:
    return Notice(
        id=notice.id,
        author=notice.author,
        posted_at=notice.posted_at,
        until=notice.until,
        body=notice.body,
    )


def _memory(entry: MemoryEntry) -> Memory:
    return Memory(
        slug=entry.slug,
        summary=entry.summary,
        created_at=entry.created_at,
        tags=list(entry.tags),
        body=entry.body,
    )


def _broken(entries: list[OverrideEntry]) -> list[OverrideEntry]:
    return [entry for entry in entries if entry.state == STATE_BROKEN]


def _check_refusal(refusal: SquadsError) -> CheckIssue:
    """The finding for a workflow or playbook override that stopped the squad's service from
    being composed; no command lints the playbook, so its finding names the loader's cause."""
    if isinstance(refusal, PlaybookConfigError):
        return CheckIssue(
            "error", "playbook", f"playbook config invalid: {refusal}", "playbook_loads"
        )
    return CheckIssue(
        "error",
        "workflow",
        f"workflow config invalid: {refusal_cause(str(refusal))} — run `sq workflow lint`",
        "workflow_loads",
    )


class SquadStateOpsMixin(
    ItemsMixin,
    SubentitiesMixin,
    RefsMixin,
    CheckMixin,
    MaintenanceMixin,
    MemoryMixin,
    BoardMixin,
    ViewsMixin,
):
    # --- board

    async def list_board(self, req: BoardListRequest) -> Response[NoticeList]:
        """The current notices, numbered from 1, and the notice files that could not be read."""
        notices, unreadable = await self.board_list()
        rows = [
            NoticeRow(
                n=i, id=n.id, author=n.author, posted_at=n.posted_at, until=n.until, body=n.body
            )
            for i, n in enumerate(notices, start=1)
        ]
        return Response(data=NoticeList(items=rows), omitted=list(unreadable))

    async def post_to_board(self, req: BoardPostRequest) -> Response[NoticeWrite]:
        """Post the notice as the declared actor, who must be on the live roster."""
        await self.adopt_declared_actor()
        notice = await self.board_post(current_actor(), req.body, until=req.until)
        return Response(data=NoticeWrite(entry=_notice(notice)))

    async def clear_from_board(self, req: BoardClearRequest) -> Response[NoticeWrite]:
        """Take down the notice at the requested position."""
        return Response(data=NoticeWrite(entry=_notice(await self.board_clear(req.n))))

    # --- memory

    async def _memory_role(self, role: str) -> str:
        """*role* resolved against the whole roster, retired roles and operators included."""
        return await self.resolve_participant(role, live_only=False)

    async def list_memories(self, req: MemoryListRequest) -> Response[MemoryList]:
        """The role's memories, and the memory files that could not be read."""
        role = await self._memory_role(req.role)
        entries, unreadable = await self.memory_list(role)
        rows = [
            MemoryRow(
                slug=m.slug, filename=f"{m.slug}.md", description=m.summary, created_at=m.created_at
            )
            for m in entries
        ]
        return Response(data=MemoryList(role=role, items=rows), omitted=list(unreadable))

    async def search_memories(self, req: MemorySearchRequest) -> Response[MemorySearch]:
        """The role's memories that hold the query, each with its matching lines."""
        role = await self._memory_role(req.role)
        hits, unreadable = await self.memory_search(role, req.query)
        rows = [MemoryHit(slug=m.slug, description=m.summary, hits=lines) for m, lines in hits]
        return Response(
            data=MemorySearch(role=role, query=req.query, items=rows), omitted=list(unreadable)
        )

    async def show_memory(self, req: MemoryShowRequest) -> Response[Memory]:
        """One memory of the role, in full."""
        role = await self._memory_role(req.role)
        return Response(data=_memory(await self.memory_show(role, req.slug)))

    async def add_memory(self, req: MemoryAddRequest) -> Response[MemoryAdded]:
        """Write a memory into the role's notebook."""
        role = await self._memory_role(req.role)
        entry = await self.memory_add(role, req.summary, body=req.body, slug=req.slug)
        return Response(data=MemoryAdded(entry=_memory(entry), role=role))

    async def forget_memory(self, req: MemoryForgetRequest) -> Response[MemoryForgotten]:
        """Delete one memory of the role."""
        role = await self._memory_role(req.role)
        entry = await self.memory_show(role, req.slug)
        await self.memory_forget(role, req.slug)
        return Response(data=MemoryForgotten(entry=_memory(entry), role=role))

    # --- workflow

    async def render_cheatsheet(self, req: CheatsheetRequest) -> Response[Cheatsheet]:
        """The cheatsheet, its authoring lines naming this squad's roles; outside a squad, or
        when the squad's roster or playbook cannot be read, they name the catalog's."""
        from squads._rendering._engine import render

        roles: list[dict[str, object]] | None = None
        playbook = get_playbook_spec()
        from_squad = None
        if self.refusal is None:
            try:
                roster = await self.roster()
            except SquadsError:
                pass
            else:
                roles = [
                    {
                        "full_name": r.full_name,
                        "title": r.title,
                        "slug": r.slug,
                        "capabilities": list(r.capabilities),
                    }
                    for r in roster
                ]
                playbook = self.playbook
                from_squad = self.paths.squad_dir
        markdown = render(
            "workflow.md.j2", from_squad=from_squad, spec=self.spec, roles=roles, playbook=playbook
        )
        return Response(data=Cheatsheet(markdown=markdown))

    async def list_types(self, req: CatalogRequest) -> Response[TypeCatalog]:
        """The type catalog of the active spec."""
        return Response(data=type_catalog(self.spec))

    async def list_subentity_kinds(self, req: CatalogRequest) -> Response[SubentityKindCatalog]:
        """The sub-entity kind catalog of the active spec."""
        return Response(data=subentity_kind_catalog(self.spec))

    async def list_lifecycles(self, req: CatalogRequest) -> Response[LifecycleCatalog]:
        """The lifecycle catalog of the active spec."""
        return Response(data=lifecycle_catalog(self.spec))

    async def list_collections(self, req: CatalogRequest) -> Response[CollectionCatalog]:
        """The badge collection catalog of the active spec."""
        return Response(data=collection_catalog(self.spec))

    async def list_statuses(self, req: CatalogRequest) -> Response[StatusCatalog]:
        """The status catalog of the active spec."""
        return Response(data=status_catalog(self.spec))

    async def list_status_roles(self, req: CatalogRequest) -> Response[StatusRoleCatalog]:
        """The status role catalog of the active spec."""
        return Response(data=role_catalog(self.spec))

    async def list_ref_kinds(self, req: CatalogRequest) -> Response[RefKindCatalog]:
        """The ref kind catalog of the active spec."""
        return Response(data=ref_kind_catalog(self.spec))

    async def list_views(self, req: CatalogRequest) -> Response[ViewCatalog]:
        """The view catalog of the active spec."""
        return Response(data=view_catalog(self.spec))

    async def resolve_view(self, req: ViewResolveRequest) -> Response[ViewResult]:
        """The view resolved against the item: its source, or, when asked, its output rendered
        through its template, so a template that does not render leaves the source readable."""
        if req.render:
            output = await self.render_view(req.name, req.item)
            return Response(data=ViewResult(source=None, output=output))
        # Every operation runs on the composed ``Service``; the source reuses its other commands.
        source = await view_source(cast("Service", self), req.name, req.item)
        return Response(data=ViewResult(source=source.data, output=None), warnings=source.warnings)

    async def lint_workflow(self, req: LintRequest) -> Response[LintReport]:
        """Every error and warning of the squad's workflow override, read from the file itself so
        an override that stops every other command is still diagnosed."""
        squad_dir = self.paths.squad_dir
        if not override_present(squad_dir / WORKFLOW_OVERRIDE_FILENAME):
            return Response(data=LintReport(override=False, errors=[], warnings=[]))
        try:
            loaded = resolve_workflow(squad_dir, self.files)
        except SquadsError:
            loaded = None
        findings = lint_workflow_spec(squad_dir, self.files, loaded)
        if not any(f[0] == "error" for f in findings):
            spec = loaded if loaded is not None else resolve_workflow(squad_dir, self.files)
            findings.extend(
                (
                    "error",
                    f"views.{name}.transform",
                    message,
                    "fix or restore the file under .overrides/ (it is imported, not called).",
                )
                for name, message in check_view_transforms(spec, squad_dir)
            )

        def of(level: str) -> list[LintFinding]:
            return [
                LintFinding(location=location, message=message, fix_hint=hint)
                for found, location, message, hint in findings
                if found == level
            ]

        return Response(data=LintReport(override=True, errors=of("error"), warnings=of("warn")))

    # --- overrides

    async def list_overrides(self, req: OverrideListRequest) -> Response[OverrideList]:
        """Every override and its state; a broken one fails the listing, naming its cause when
        its file cannot be read."""
        entries = scan_overrides(self.paths.squad_dir)
        rows = [
            OverrideRow(name=e.name, kind=e.kind, base_version=e.base_version, state=e.state)
            for e in entries
        ]
        broken = _broken(entries)
        errors = [e.cause for e in broken if e.cause]
        return Response(data=OverrideList(items=rows, errors=errors, failed=bool(broken)))

    async def diff_overrides(self, req: OverrideDiffRequest) -> Response[OverrideDiff]:
        """The requested override's deltas, or every drifted one's; each broken override is
        named and fails the command."""
        squad_dir = self.paths.squad_dir
        entries: list[OverrideEntry] = []
        if req.kind is not None:
            results = [diff_override(squad_dir, name=req.name or req.kind, kind=req.kind)]
        else:
            entries = scan_overrides(squad_dir)
            results = [
                diff_override(squad_dir, name=e.name, kind=e.kind)
                for e in entries
                if e.state == STATE_DRIFTED
            ]
        rows = [
            OverrideDiffRow(
                name=r.name,
                kind=r.kind,
                base_version=r.base_version,
                base_available=r.base_available,
                delta_mine=r.delta_mine,
                delta_upgrade=r.delta_upgrade,
            )
            for r in results
        ]
        broken = _broken(entries)
        errors = [e.cause or _BROKEN_REGION.format(name=e.name) for e in broken]
        return Response(data=OverrideDiff(items=rows, errors=errors, failed=bool(broken)))

    async def scaffold_override(self, req: OverrideScaffoldRequest) -> Response[ScaffoldedOverride]:
        """Copy the bundled default into ``.overrides/``; a role override starts from the role's
        current definition, and only a role on the roster or in the catalog has one."""
        squad_dir = self.paths.squad_dir
        prefilled = False
        if req.kind == "role":
            item = await self.roster_item(ROSTER_ROLE, req.name)
            base = role_base_from_item(item, self.catalog) if item is not None else None
            if item is None and req.name not in {r.slug for r in self.catalog().roles}:
                raise SquadsError(
                    f"no role {req.name!r} to override: create it with `sq role add {req.name} "
                    "--name … --job-title … --desc … --mission …` or "
                    f"`sq role activate {req.name}`"
                )
            dest = scaffold_role(squad_dir, slug=req.name, force=req.force, base=base)
            prefilled = base is not None or req.name in {r.slug for r in PREDEFINED}
        elif req.kind == "workflow":
            dest = scaffold_workflow(squad_dir, force=req.force)
        elif req.kind == "playbook":
            dest = scaffold_playbook(squad_dir, force=req.force)
        elif req.kind == "roles":
            dest = scaffold_roles_catalog(squad_dir, force=req.force)
        else:
            dest = scaffold_template(squad_dir, template_name=req.name, force=req.force)
        return Response(
            data=ScaffoldedOverride(
                entry=OverrideFile(kind=req.kind, name=req.name, path=str(dest)),
                prefilled=prefilled,
            )
        )

    async def stamp_overrides(self, req: OverrideUpdateRequest) -> Response[StampedOverrides]:
        """Re-stamp the requested override, or every valid one; each one that cannot be read is
        named."""
        squad_dir = self.paths.squad_dir
        entries = scan_overrides(squad_dir) if req.kind is None else []
        stamped = update_stamp(squad_dir, name=req.name, kind=req.kind)
        errors = [e.cause for e in entries if e.cause]
        return Response(data=StampedOverrides(stamped=stamped, version=__version__, errors=errors))

    # --- reflog, check, sync

    async def list_reflog(self, req: ReflogRequest) -> Response[Reflog]:
        """The reflog entries that match every filter."""
        entries = await self.read_reflog(
            item=req.item,
            actor_filter=req.actor,
            op_filter=req.op,
            since=req.since,
            tail=req.tail,
        )
        rows = [
            ReflogEntryRow(
                v=e.v,
                ts=e.ts,
                actor=e.actor,
                op=e.op,
                target=e.target,
                delta=e.delta,
                session_id=e.session_id,
                parent_session_id=e.parent_session_id,
            )
            for e in entries
        ]
        return Response(data=Reflog(items=rows))

    async def check_squad(self, req: CheckRequest) -> Response[CheckReport]:
        """Every finding in its stable order. A workflow or playbook override that would not load
        is itself a finding, and the scan runs on the fallback documents; a scan that cannot run
        is a finding too, so the others still print."""
        issues: list[CheckIssue] = []
        if self.refusal is not None:
            issues.append(_check_refusal(self.refusal))
        try:
            issues += await self.check()
        except SquadsError as exc:
            issues.append(
                CheckIssue("error", "corpus", f"could not scan the corpus: {exc}", "corpus_scans")
            )
        rows = [
            CheckIssueRow(level=i.level, item=i.item, message=i.message, rule=i.rule)
            for i in sorted(issues, key=check_issue_sort_key)
        ]
        errors = sum(1 for row in rows if row.level == "error")
        return Response(data=CheckReport(items=rows, errors=errors))

    async def sync_squad(self, req: SyncRequest) -> Response[SyncReport]:
        """Regenerate every managed file; what the regeneration left alone is reported."""
        return Response(data=SyncReport(skipped=list(await self.sync())))
