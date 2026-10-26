"""The ``Service`` facade — all concern mixins composed over ``ServiceCore`` — plus the
``init`` / ``adopt`` / ``open_service`` entry points.

``Service`` keeps a flat API (``svc.create()``, ``svc.comment()``, …); each method lives in the
concern mixin under ``_services/``.
"""

from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path

from squads import _aio
from squads._backends._base import AgentBackend
from squads._backends._registry import get_backend
from squads._errors import AlreadyInitializedError, PlaybookConfigError, SquadsError
from squads._index._store import IndexStore
from squads._language import DEFAULT_WORKING_LANGUAGE
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._paths import SquadPaths, load_config, process_dir, resolve
from squads._roles._catalog import resolve_roles
from squads._services._board import BoardMixin
from squads._services._check import CheckMixin
from squads._services._collab import CollabMixin
from squads._services._import import ImportMixin
from squads._services._items import ItemsMixin
from squads._services._maintenance import MaintenanceMixin, ensure_root_tmp_ignored
from squads._services._memory import MemoryMixin
from squads._services._refs import RefsMixin
from squads._services._rename import RenameMixin
from squads._services._results import AdoptResult, InitResult
from squads._services._retype import RetypeMixin
from squads._services._roster import RosterMixin
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


class Mode(StrEnum):
    """How :func:`compose_service` chooses the documents a service holds when something fails."""

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


#: What a command that must still run beside a refusal tries after :attr:`Mode.NORMAL` fails: the
#: first rung that builds wins, and a refusal on the last one is the caller's.
BYPASS_FALLBACKS: tuple[Mode, ...] = (Mode.INDEX_CHECK_SKIPPED, Mode.BUNDLED_FALLBACK)
MIGRATE_FALLBACKS: tuple[Mode, ...] = (Mode.MIGRATE,)

#: What `sq check` falls back to, by the refusal :attr:`Mode.NORMAL` raised; the first row whose
#: error class matches wins, so the narrower class comes first.
CHECK_FALLBACKS: tuple[tuple[type[SquadsError], Mode], ...] = (
    (PlaybookConfigError, Mode.PLAYBOOK_UNAVAILABLE),
    (SquadsError, Mode.BUNDLED_FALLBACK),
)


def check_fallback(error: SquadsError) -> Mode:
    """The mode `sq check` composes its service in after *error* refused :attr:`Mode.NORMAL`."""
    return next(mode for kind, mode in CHECK_FALLBACKS if isinstance(error, kind))


def _squad_workflow_spec(resolved_spec: WorkflowSpec | None, sources: SpecSources) -> WorkflowSpec:
    """*resolved_spec* when the caller already resolved it, else the squad's merged workflow spec
    (the bundled one when it has no override), without the index check."""
    return resolved_spec if resolved_spec is not None else sources.workflow()


def _checked_workflow_spec(
    paths: SquadPaths, resolved_spec: WorkflowSpec | None, sources: SpecSources
) -> WorkflowSpec:
    """The workflow spec :attr:`Mode.NORMAL` holds: *resolved_spec* when the caller already
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
    paths: SquadPaths, mode: Mode, resolved_spec: WorkflowSpec | None, sources: SpecSources
) -> SpecDocuments:
    """The documents *mode* puts in a service for the squad at *paths*."""
    squad_dir = paths.squad_dir
    match mode:
        case Mode.NORMAL:
            return resolve_documents(
                squad_dir, sources, workflow=_checked_workflow_spec(paths, resolved_spec, sources)
            )
        case Mode.INDEX_CHECK_SKIPPED:
            spec = _squad_workflow_spec(resolved_spec, sources)
            return resolve_documents(squad_dir, sources, workflow=spec, bundled_playbook=True)
        case Mode.MIGRATE:
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
        case Mode.PLAYBOOK_UNAVAILABLE:
            try:
                spec = _squad_workflow_spec(resolved_spec, sources)
            except SquadsError:
                spec = bundled_spec()
            return resolve_documents(squad_dir, sources, workflow=spec, bundled_playbook=True)
        case Mode.BUNDLED_FALLBACK:
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
) -> Service:
    """The one place a :class:`Service` is constructed: its index store and backends (the
    squad's configured ones unless *backends* is given) are built here and handed in, with the
    *documents* it holds."""
    return Service(
        paths,
        spec=documents.workflow,
        playbook=documents.playbook,
        store=IndexStore(paths.index_path, paths.lock_path, spec=documents.workflow),
        backends=backends if backends is not None else _backends_of(paths.config.active_backends),
        catalog=documents.catalog,
        files=documents.files,
    )


def compose_service(
    paths: SquadPaths,
    mode: Mode = Mode.NORMAL,
    *,
    resolved_spec: WorkflowSpec | None = None,
    sources: SpecSources | None = None,
) -> Service:
    """The service for the squad at *paths*, holding the documents *mode* chooses; *resolved_spec*
    and *sources* carry what the caller already resolved or read, so none of it is loaded again."""
    sources = sources if sources is not None else spec_sources(paths.squad_dir)
    return build_service(paths, _documents_for(paths, mode, resolved_spec, sources))


def compose_first_of(
    paths: SquadPaths,
    modes: Sequence[Mode],
    *,
    resolved_spec: WorkflowSpec | None = None,
    sources: SpecSources | None = None,
) -> Service:
    """The service of the first of *modes* that builds; the last one's refusal is raised."""
    sources = sources if sources is not None else spec_sources(paths.squad_dir)
    for mode in modes[:-1]:
        try:
            return compose_service(paths, mode, resolved_spec=resolved_spec, sources=sources)
        except SquadsError:
            continue
    return compose_service(paths, modes[-1], resolved_spec=resolved_spec, sources=sources)


def _init_time_spec(sources: SpecSources) -> WorkflowSpec:
    """The spec ``init``/``adopt`` scaffold against: the squad's, from *sources*. A pre-placed
    override is validated here, before anything is written, as ``open_service`` will load it (fail-
    closed, pointing at ``sq workflow lint``).
    """
    try:
        return sources.workflow()
    except SquadsError as exc:
        raise SquadsError(f"{exc} — run `sq workflow lint` to see details") from exc


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
    await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
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
        await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    effective_spec = validated_spec if validated_spec is not None else _init_time_spec(sources)
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
    repair_result = await svc.repair()
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


def open_service(
    *,
    client_cwd: Path | None = None,
    resolved_spec: WorkflowSpec | None = None,
    sources: SpecSources | None = None,
) -> Service:
    """Resolve the active squad and compose its service in :attr:`Mode.NORMAL`. A workflow spec that
    fails to load or conflicts with the index raises ``SquadsError`` pointing to ``sq workflow
    lint``; a playbook that fails raises :class:`~squads._errors.PlaybookConfigError`.
    ``client_cwd`` is the requesting client's directory (``None`` is the process cwd);
    ``resolved_spec`` and ``sources`` are what the caller already resolved and read.
    """
    return compose_service(
        resolve(client_cwd=client_cwd), resolved_spec=resolved_spec, sources=sources
    )
