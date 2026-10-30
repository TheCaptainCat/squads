"""The ``Service`` facade — all concern mixins composed over ``ServiceCore`` — plus the
``init`` / ``adopt`` / ``compose_service`` entry points.

``Service`` keeps a flat API (``svc.create()``, ``svc.comment()``, …); each method lives in the
concern mixin under ``_services/``.
"""

import asyncio
import contextvars
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from squads import _aio, _clock
from squads._api._api import Mode
from squads._api._http import RequestMetadata
from squads._backends._base import AgentBackend
from squads._backends._registry import get_backend
from squads._context import NoticeLog, Preconditions, RequestContext, bind_context
from squads._errors import AlreadyInitializedError, PlaybookConfigError, SquadsError
from squads._index._store import IndexStore
from squads._language import DEFAULT_WORKING_LANGUAGE
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._paths import SquadPaths, load_config, process_dir
from squads._roles._catalog import resolve_roles
from squads._services._board import BoardMixin
from squads._services._check import CheckMixin
from squads._services._collab import CollabMixin
from squads._services._corpus_ops import CorpusOpsMixin
from squads._services._import import ImportMixin
from squads._services._item_ops import ItemOpsMixin
from squads._services._item_read_ops import ItemReadOpsMixin
from squads._services._item_write_ops import ItemWriteOpsMixin, RetypeOpsMixin
from squads._services._items import ItemsMixin
from squads._services._maintenance import MaintenanceMixin, ensure_root_tmp_ignored
from squads._services._memory import MemoryMixin
from squads._services._refs import RefsMixin
from squads._services._rename import RenameMixin
from squads._services._results import AdoptResult, InitResult
from squads._services._retype import RetypeMixin
from squads._services._roster import RosterMixin
from squads._services._roster_ops import RosterOpsMixin
from squads._services._squad_ops import SquadStateOpsMixin
from squads._services._subentities import SubentitiesMixin
from squads._services._views import ViewsMixin
from squads._spec_documents import SpecDocuments, SpecSources, resolve_documents, spec_sources
from squads._specload import Lazy, override_present
from squads._workflow import ROSTER_ROLE, bundled_spec
from squads._workflow._loader import (
    WORKFLOW_OVERRIDE_FILENAME,
    spec_refusal,
    validate_against_index_fail_closed,
)
from squads._workflow._models import WorkflowSpec


class Service(
    ItemWriteOpsMixin,
    ItemReadOpsMixin,
    RosterOpsMixin,
    RetypeOpsMixin,
    ItemOpsMixin,
    SquadStateOpsMixin,
    CorpusOpsMixin,
    ImportMixin,
    ItemsMixin,
    CollabMixin,
    SubentitiesMixin,
    RefsMixin,
    RosterMixin,
    CheckMixin,
    MaintenanceMixin,
    RetypeMixin,
    RenameMixin,
    MemoryMixin,
    BoardMixin,
    ViewsMixin,
):
    """Orchestration façade: the logic behind each CLI command.

    The ``.md`` frontmatter is the durable source of truth; ``.squads.json`` is a rebuildable index.
    """


class Documents(StrEnum):
    """The documents a service is composed over; the fallback tables step through them."""

    #: The squad's merged workflow spec, checked against the live index, and its merged playbook.
    NORMAL = "normal"
    #: The merged workflow spec without the index check, and the bundled playbook.
    INDEX_CHECK_SKIPPED = "index-check-skipped"
    #: The merged workflow spec and playbook, each refused with a pointer back to `sq migrate up`.
    MIGRATE = "migrate"
    #: The merged workflow spec (the bundled one if it will not load) and the bundled playbook.
    PLAYBOOK_UNAVAILABLE = "playbook-unavailable"
    #: The bundled workflow spec and the bundled playbook.
    BUNDLED_FALLBACK = "bundled-fallback"


#: What an operation that must still run beside a refusal tries after :attr:`Documents.NORMAL`
#: fails: the first rung that builds wins, and a refusal on the last one is the caller's.
BYPASS_FALLBACKS: tuple[Documents, ...] = (
    Documents.INDEX_CHECK_SKIPPED,
    Documents.BUNDLED_FALLBACK,
)
MIGRATE_FALLBACKS: tuple[Documents, ...] = (Documents.MIGRATE,)

#: What `sq check` falls back to, by the refusal :attr:`Documents.NORMAL` raised; the first row
#: whose error class matches wins, so the narrower class comes first.
CHECK_FALLBACKS: tuple[tuple[type[SquadsError], Documents], ...] = (
    (PlaybookConfigError, Documents.PLAYBOOK_UNAVAILABLE),
    (SquadsError, Documents.BUNDLED_FALLBACK),
)


#: What an operation that reads only the vocabulary falls back to, by the refusal
#: :attr:`Documents.NORMAL` raised; a workflow override that does not load is refused, not
#: fallen back from, and a directory no squad holds gets the bundled documents.
VOCABULARY_FALLBACKS: tuple[tuple[type[SquadsError], Documents], ...] = (
    (SquadsError, Documents.PLAYBOOK_UNAVAILABLE),
)


def _fallbacks(mode: Mode) -> tuple[tuple[type[SquadsError], Documents], ...]:
    """The table *mode* walks after :attr:`Documents.NORMAL` refuses; empty when it has none."""
    match mode:
        case Mode.CHECK:
            return CHECK_FALLBACKS
        case Mode.VOCABULARY:
            return VOCABULARY_FALLBACKS
        case _:
            return ()


def _direct_documents(mode: Mode) -> Documents:
    """The documents a mode with neither a fallback table nor a ladder composes over; a mode that
    has one is refused, so dropping it from its table cannot skip the normal attempt."""
    match mode:
        case Mode.NORMAL:
            return Documents.NORMAL
        case Mode.BUNDLED_FALLBACK:
            return Documents.BUNDLED_FALLBACK
        case Mode.INDEX_CHECK_SKIPPED | Mode.MIGRATE | Mode.CHECK | Mode.VOCABULARY:
            raise ValueError(f"mode {mode} composes through its fallback table or ladder")


def _ladder(mode: Mode) -> tuple[Documents, ...]:
    """The rungs *mode* tries in order after :attr:`Documents.NORMAL` refuses; empty when it has
    none."""
    match mode:
        case Mode.INDEX_CHECK_SKIPPED:
            return BYPASS_FALLBACKS
        case Mode.MIGRATE:
            return MIGRATE_FALLBACKS
        case _:
            return ()


def _squad_workflow_spec(resolved_spec: WorkflowSpec | None, sources: SpecSources) -> WorkflowSpec:
    """*resolved_spec* when the caller already resolved it, else the squad's merged workflow spec
    (the bundled one when it has no override), without the index check."""
    return resolved_spec if resolved_spec is not None else sources.workflow()


def _checked_workflow_spec(
    paths: SquadPaths, resolved_spec: WorkflowSpec | None, sources: SpecSources
) -> WorkflowSpec:
    """The workflow spec :attr:`Documents.NORMAL` holds: *resolved_spec* when the caller already
    resolved and checked it, else the merged spec checked against the live index, refused in the
    shared wording when either half fails."""
    if resolved_spec is not None:
        return resolved_spec
    override_path = paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_present(override_path):
        return bundled_spec()
    try:
        merged = sources.workflow()
        validate_against_index_fail_closed(merged, paths.squad_dir, bundled=bundled_spec())
    except SquadsError as exc:
        raise SquadsError(spec_refusal(override_path, exc)) from exc
    return merged


def _documents_for(
    paths: SquadPaths, mode: Documents, resolved_spec: WorkflowSpec | None, sources: SpecSources
) -> SpecDocuments:
    """The documents *mode* puts in a service for the squad at *paths*."""
    squad_dir = paths.squad_dir
    match mode:
        case Documents.NORMAL:
            return resolve_documents(
                squad_dir, sources, workflow=_checked_workflow_spec(paths, resolved_spec, sources)
            )
        case Documents.INDEX_CHECK_SKIPPED:
            spec = _squad_workflow_spec(resolved_spec, sources)
            return resolve_documents(squad_dir, sources, workflow=spec, bundled_playbook=True)
        case Documents.MIGRATE:
            try:
                spec = _squad_workflow_spec(resolved_spec, sources)
            except SquadsError as exc:
                raise SquadsError(
                    "this squad's workflow override could not be loaded, so `sq migrate up` "
                    "cannot run under the vocabulary it declares.\n"
                    f"  file:  {squad_dir / WORKFLOW_OVERRIDE_FILENAME}\n"
                    f"  cause: {exc}\n"
                    "Correct the file, then re-run `sq migrate up`."
                ) from exc
            try:
                return resolve_documents(squad_dir, sources, workflow=spec)
            except SquadsError as exc:
                raise SquadsError(f"{exc}\nCorrect the file, then re-run `sq migrate up`.") from exc
        case Documents.PLAYBOOK_UNAVAILABLE:
            try:
                spec = _squad_workflow_spec(resolved_spec, sources)
            except SquadsError:
                spec = bundled_spec()
            return resolve_documents(squad_dir, sources, workflow=spec, bundled_playbook=True)
        case Documents.BUNDLED_FALLBACK:
            return resolve_documents(
                squad_dir, sources, workflow=bundled_spec(), bundled_playbook=True
            )


def _backends_of(names: Sequence[str]) -> Callable[[], list[AgentBackend]]:
    """The squad's active backends, instantiated on first use and kept: an unknown name is
    refused when a backend is first needed, not when the service is built."""
    instances = Lazy(lambda: [get_backend(name) for name in names])
    return lambda: list(instances())


def build_service(
    paths: SquadPaths,
    documents: SpecDocuments,
    backends: Callable[[], list[AgentBackend]] | None = None,
    refusal: SquadsError | None = None,
) -> Service:
    """The one place a :class:`Service` is constructed: its index store and backends (the
    squad's configured ones unless *backends* is given) are built here and handed in, with the
    *documents* it holds and the *refusal* that made its composition fall back to them."""
    return Service(
        paths,
        spec=documents.workflow,
        playbook=documents.playbook,
        store=IndexStore(paths.index_path, paths.lock_path, spec=documents.workflow),
        backends=backends if backends is not None else _backends_of(paths.config.active_backends),
        catalog=documents.catalog,
        files=documents.files,
        refusal=refusal,
    )


def _compose(
    paths: SquadPaths,
    documents: Documents,
    resolved_spec: WorkflowSpec | None,
    sources: SpecSources | None,
    refusal: SquadsError | None = None,
) -> Service:
    sources = sources if sources is not None else spec_sources(paths.squad_dir)
    return build_service(
        paths, _documents_for(paths, documents, resolved_spec, sources), refusal=refusal
    )


def _compose_normal(
    paths: SquadPaths,
    resolved_spec: WorkflowSpec | None,
    sources: SpecSources | None,
    spec_error: str | None,
) -> Service:
    """The normal service, refused with *spec_error* when the invocation's spec did not resolve."""
    if spec_error is not None:
        raise SquadsError(spec_error)
    return _compose(paths, Documents.NORMAL, resolved_spec, sources)


def _compose_squadless(base: Path | None, refusal: SquadsError) -> Service:
    """The bundled documents for a directory no squad holds, carrying *refusal*; nothing is read
    from or written to its paths, which name no squad."""
    root = base or process_dir()
    config = SquadsConfig()
    paths = SquadPaths(root=root, squad_dir=root / config.squad_dir, config=config)
    documents = resolve_documents(
        paths.squad_dir,
        spec_sources(paths.squad_dir),
        workflow=bundled_spec(),
        bundled_playbook=True,
    )
    return build_service(paths, documents, backends=list, refusal=refusal)


def compose_service(
    paths: SquadPaths | None,
    mode: Mode = Mode.NORMAL,
    *,
    resolved_spec: WorkflowSpec | None = None,
    sources: SpecSources | None = None,
    spec_error: str | None = None,
    unresolved: SquadsError | None = None,
    base: Path | None = None,
) -> Service:
    """The service for the squad at *paths* in *mode*: the documents it names, or, for a mode with
    a fallback table, the first row that matches the refusal, or for a mode with a ladder, the
    first rung that builds; the service then carries the refusal.

    *resolved_spec*, *sources* and *spec_error* are what the caller already resolved, read or was
    refused, so none of it is loaded again. *paths* is ``None`` when no squad resolves from
    *base*, for the reason *unresolved*: only :attr:`Mode.VOCABULARY` composes then.
    """
    if paths is None:
        refusal = unresolved if unresolved is not None else SquadsError("no squad resolves")
        if mode is not Mode.VOCABULARY:
            raise refusal
        return _compose_squadless(base, refusal)
    fallbacks, ladder = _fallbacks(mode), _ladder(mode)
    if mode in (Mode.NORMAL, Mode.VOCABULARY) and spec_error is not None:
        raise SquadsError(spec_error)
    if not fallbacks and not ladder:
        return _compose(paths, _direct_documents(mode), resolved_spec, sources)
    try:
        return _compose_normal(paths, resolved_spec, sources, spec_error)
    except SquadsError as exc:
        if ladder:
            return _compose_first_of(paths, ladder, resolved_spec, sources, exc)
        fallback = next(documents for kind, documents in fallbacks if isinstance(exc, kind))
        return _compose(paths, fallback, resolved_spec, sources, refusal=exc)


def _compose_first_of(
    paths: SquadPaths,
    rungs: Sequence[Documents],
    resolved_spec: WorkflowSpec | None,
    sources: SpecSources | None,
    refusal: SquadsError,
) -> Service:
    """The service of the first of *rungs* that builds, carrying *refusal*; the last rung's own
    refusal is raised."""
    sources = sources if sources is not None else spec_sources(paths.squad_dir)
    for documents in rungs[:-1]:
        try:
            return _compose(paths, documents, resolved_spec, sources, refusal=refusal)
        except SquadsError:
            continue
    return _compose(paths, rungs[-1], resolved_spec, sources, refusal=refusal)


@dataclass(frozen=True)
class Answered[T]:
    """What a request scope hands back: the handler's value, the ETag of the item it addressed
    (``None`` when it addressed none or removed it) and the handler's own run time in
    milliseconds, which excludes the time the request spent waiting its turn."""

    value: T
    etag: str | None
    handler_ms: float


class RequestScope:
    """The daemon's scope for one request: it runs a handler in a fresh ``contextvars.Context`` on
    a ``RequestContext`` bound from the request's headers and the documents loaded at start-up,
    one request at a time, in arrival order. It redirects no stream, sets no environment
    variable, builds no console and reads neither the process's directory nor its environment for
    a value a header carries."""

    def __init__(self, root: Path, squad_dir: Path, sources: SpecSources) -> None:
        self._root = root
        self._squad_dir = squad_dir
        self._lock = asyncio.Lock()
        self._spec: WorkflowSpec | None = None
        self._startup_refusal: str | None = None
        try:
            self._spec = sources.workflow()
        except (SquadsError, OSError, ValueError) as exc:  # fmt: skip
            self._startup_refusal = spec_refusal(squad_dir / WORKFLOW_OVERRIDE_FILENAME, exc)

    def _spec_refusal(self) -> str | None:
        """The refusal a workflow override that fails its check against the live index is read
        with, as the CLI's root callback finds it; ``None`` when there is none."""
        if self._startup_refusal is not None or self._spec is None:
            return self._startup_refusal
        override = self._squad_dir / WORKFLOW_OVERRIDE_FILENAME
        if not override_present(override):
            return None
        try:
            validate_against_index_fail_closed(self._spec, self._squad_dir, bundled=bundled_spec())
        except Exception as exc:  # any failure of the check is the refusal's text
            return spec_refusal(override, exc)
        return None

    def _context(self, meta: RequestMetadata, *, conditional: bool) -> RequestContext:
        """The context for a request declaring *meta*; *conditional* says whether its
        ``If-Match`` is compared."""
        at = None
        if meta.at is not None:
            try:
                at = _clock.parse_iso(meta.at)
            except ValueError:
                raise SquadsError(
                    f"invalid Squads-At timestamp {meta.at!r} "
                    "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)"
                ) from None
        start = self._root
        if meta.client_dir is not None:
            start = Path(meta.client_dir)
            if not start.is_absolute():
                raise SquadsError(f"Squads-Client-Dir must be an absolute path, got {start}")
        return RequestContext(
            clock_override=at,
            actor_override=meta.actor,
            session_id=meta.session_id,
            parent_session_id=meta.parent_session_id,
            active_spec=self._spec,
            client_cwd=self._root,
            spec_error=self._spec_refusal(),
            start_dir=start,
            notices=NoticeLog(),
            preconditions=Preconditions(meta.if_match if conditional else None),
        )

    async def _bound[T](
        self, meta: RequestMetadata, call: Callable[[], Awaitable[T]], conditional: bool
    ) -> Answered[T]:
        ctx = self._context(meta, conditional=conditional)
        bind_context(ctx)
        started = time.perf_counter()
        value = await call()
        elapsed = (time.perf_counter() - started) * 1000
        return Answered(value, ctx.preconditions.etag if ctx.preconditions else None, elapsed)

    async def run[T](
        self, meta: RequestMetadata, call: Callable[[], Awaitable[T]], *, conditional: bool = False
    ) -> Answered[T]:
        """Run *call* in the scope of a request declaring *meta*. The call runs to completion
        once it has started, even if the caller stops waiting."""

        async def serial() -> Answered[T]:
            async with self._lock:
                return await asyncio.create_task(
                    self._bound(meta, call, conditional), context=contextvars.Context()
                )

        return await asyncio.shield(asyncio.ensure_future(serial()))


def _init_time_spec(sources: SpecSources) -> WorkflowSpec:
    """The spec ``init``/``adopt`` scaffold against: the squad's, from *sources*. A pre-placed
    override is validated here, before anything is written, as ``compose_service`` will load it
    (fail-closed, pointing at ``sq workflow lint``).
    """
    try:
        return sources.workflow()
    except SquadsError as exc:
        raise SquadsError(f"{exc} — run `sq workflow lint` to see details") from exc


def _checked_squad_dir(root: Path, squad_dir: str) -> str:
    """*squad_dir* when it is a non-empty relative folder that stays inside *root*, else a
    refusal: it is checked before init or adopt writes anything."""
    if not squad_dir.strip():
        raise SquadsError("--squad-dir must name a folder, not an empty value")
    if Path(squad_dir).is_absolute():
        raise SquadsError(f"--squad-dir must be relative to the project root, got {squad_dir!r}")
    if not (root / squad_dir).resolve().is_relative_to(root):
        raise SquadsError(f"--squad-dir must stay inside the project root, got {squad_dir!r}")
    return squad_dir


def _checked_backends(names: list[str]) -> None:
    """Refuse an unknown backend name before init or adopt writes anything."""
    for name in names:
        get_backend(name)


#: What a refusal over files sharing a number says to run: it needs no configuration.
ADOPT_RENUMBER_REMEDY = "run `sq adopt --renumber` to give one of them a new number and adopt"


async def init(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: list[str] | None = None,
    roles_spec: str = "all",
    no_claude: bool = False,
    force: bool = False,
    names: dict[str, str] | None = None,
    sources: SpecSources | None = None,
    _skip_skill_seed: bool = False,
) -> InitResult:
    """Initialise a new squad. ``names`` maps role slug to full name for custom names (``--name``
    flags and ``[init.names]``); other slugs fall through to the bundled pool. ``sources`` carries
    the documents the caller already read and ``roles_spec`` is resolved against the squad's own
    role catalog. ``_skip_skill_seed`` is an internal testing hook that omits bundled-skill id
    stamping to keep the global counter still; production callers must not set it.
    """
    root = (root or process_dir()).resolve()
    config_path = root / CONFIG_FILENAME
    if await _aio.path_exists(config_path) and not force:
        raise AlreadyInitializedError(f"{config_path} already exists (use --force to overwrite)")
    squad_dir = _checked_squad_dir(root, squad_dir)
    _checked_backends(backend or [])

    # Validate a pre-placed override before any state is written, so a bad one means init never
    # starts rather than leaving a half-created squad.
    sources = sources if sources is not None else spec_sources(root / squad_dir)
    effective_spec = _init_time_spec(sources)
    role_defs = resolve_roles(roles_spec, sources.catalog()) if roles_spec else []

    effective_names = names or {}
    effective_backends: list[str] = backend if backend is not None else ["claude_code"]
    config = SquadsConfig(
        squad_dir=squad_dir,
        active_backends=effective_backends,
        init_names=effective_names,
        working_language=DEFAULT_WORKING_LANGUAGE,
    )
    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    if _holds_item_files(sp, effective_spec):
        # The rebuild below would refuse a corpus whose files share a number; say so before
        # anything is written, so the corrected corpus can be initialised afresh.
        # `sq repair` needs a configuration this folder lacks, so the remedy named is adopt's.
        await compose_service(
            sp, resolved_spec=effective_spec, sources=sources
        ).refuse_shared_numbers(
            ADOPT_RENUMBER_REMEDY,
            same_id=True,
            merge_then="sq repair" if await _aio.path_exists(config_path) else "sq adopt",
        )
    await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    for ts in effective_spec.items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    await _aio.write_text(sp.squad_dir / ".gitignore", ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path, spec=effective_spec)
    index_exists = store.exists()
    holds_corpus = index_exists or _holds_item_files(sp, effective_spec)
    if not index_exists:
        await store.create_empty_threaded()

    svc = compose_service(sp, resolved_spec=effective_spec, sources=sources)
    if holds_corpus:
        # Over an existing squad, rebuild the index from disk over the one already there (under
        # the index lock, carrying forward what cannot be parsed, as `sq repair` does) so roles
        # and skills are not created a second time and the counter does not restart.
        await svc.repair()
    if not no_claude:
        await svc.scaffold_backend()

    created = [await svc.activate_role(r.slug, name=effective_names.get(r.slug)) for r in role_defs]

    warnings: list[str] = []
    if not no_claude:
        warnings += await svc.refresh_managed()
        # Stamp each managed skill as a SKILL item in slug order, bundled and custom types alike,
        # rather than leaving them unindexed until the first `sq sync`.
        if not _skip_skill_seed:
            await svc.seed_bundled_skills()
            await svc.seed_custom_skills()
        warnings += await svc.candidate_orphans()

    return InitResult(paths=sp, roles=created, warnings=warnings)


def _holds_item_files(sp: SquadPaths, spec: WorkflowSpec) -> bool:
    """Whether the squad folder already holds an item file of any declared type."""
    return any(
        next((sp.squad_dir / ts.folder).glob(f"{ts.prefix}-*.md"), None) is not None
        for ts in spec.items.values()
    )


async def adopt(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: list[str] | None = None,
    roles_spec: str = "all",
    no_claude: bool = False,
    renumber: bool = False,
) -> AdoptResult:
    """Bring an existing squad-structured folder under sq management without destroying anything: it
    imports the squads-native ``.md`` files already present (through :meth:`Service.repair`, so it
    rewrites their content), then ensures the backend scaffolding and bundled roles. The whole
    ``RepairResult`` rides on :class:`~squads._services._results.AdoptResult` so the CLI can
    announce that diff, since no migration will ever tell this population.
    """
    root = (root or process_dir()).resolve()
    config_path = root / CONFIG_FILENAME
    validated_spec: WorkflowSpec | None = None
    existing = load_config(config_path) if await _aio.path_exists(config_path) else None
    if existing is not None:
        squad_dir = existing.squad_dir
    else:
        squad_dir = _checked_squad_dir(root, squad_dir)
        _checked_backends(backend or [])
    sources = spec_sources(root / squad_dir)
    role_defs = resolve_roles(roles_spec, sources.catalog()) if roles_spec else []
    if existing is not None:
        config = existing
    else:
        # Validate a pre-placed override before writing .squads.toml — same ordering as
        # init() and for the same reason: adopt is the other caller that can create the
        # config file, so it must not wedge a half-created squad behind a bad override either.
        validated_spec = _init_time_spec(sources)
        effective_backends: list[str] = backend if backend is not None else ["claude_code"]
        config = SquadsConfig(
            squad_dir=squad_dir,
            active_backends=effective_backends,
            working_language=DEFAULT_WORKING_LANGUAGE,
        )
    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    effective_spec = validated_spec if validated_spec is not None else _init_time_spec(sources)
    if _holds_item_files(sp, effective_spec):
        # Refused before anything is written, as in init(); --renumber resolves what it can in
        # one step, so only the groups it cannot resolve are refused then.
        await compose_service(
            sp, resolved_spec=effective_spec, sources=sources
        ).refuse_shared_numbers(
            ADOPT_RENUMBER_REMEDY,
            same_id=True,
            renumbering=renumber,
            merge_then="sq repair" if existing is not None else "sq adopt",
        )
    if existing is None:
        await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    for ts in effective_spec.items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    gitignore = sp.squad_dir / ".gitignore"
    if not await _aio.path_exists(gitignore):
        await _aio.write_text(gitignore, ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path, spec=effective_spec)
    if not store.exists():
        await store.create_empty_threaded()

    svc = compose_service(sp, resolved_spec=effective_spec, sources=sources)
    # Import any existing squads-native .md files (sets counter from them).
    repair_result = await svc.repair(renumber=renumber)
    existing_roles = {it.slug for it in repair_result.db.items.values() if it.type == ROSTER_ROLE}

    if not no_claude:
        await svc.scaffold_backend()
    created = [await svc.activate_role(r.slug) for r in role_defs if r.slug not in existing_roles]
    warnings: list[str] = []
    if not no_claude:
        warnings += await svc.refresh_managed()
        # As in init(): seed bundled and custom skills so a generated skill file is never left
        # without a SKILL item until the first `sq sync`.
        await svc.seed_bundled_skills()
        await svc.seed_custom_skills()
        warnings += await svc.candidate_orphans()

    return AdoptResult(paths=sp, repair=repair_result, roles=created, warnings=warnings)
