"""The ``Service`` facade — all concern mixins composed over ``ServiceCore`` — plus the
``init`` / ``adopt`` / ``open_service`` entry points.

``Service`` keeps a flat API (``svc.create()``, ``svc.comment()``, …); each method lives in the
concern mixin under ``_services/``.
"""

from pathlib import Path

from squads import __version__, _aio
from squads._errors import AlreadyInitializedError
from squads._index._store import IndexStore
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._paths import SquadPaths, load_config, resolve
from squads._roles._catalog import RoleDef, resolve_roles
from squads._services._collab import CollabMixin
from squads._services._items import ItemsMixin
from squads._services._maintenance import MaintenanceMixin
from squads._services._memory import MemoryMixin
from squads._services._refs import RefsMixin
from squads._services._rename import RenameMixin
from squads._services._results import AdoptResult, InitResult
from squads._services._retype import RetypeMixin
from squads._services._roster import RosterMixin
from squads._services._subentities import SubentitiesMixin
from squads._workflow import META_ROLE, bundled_spec


class Service(
    ItemsMixin,
    CollabMixin,
    SubentitiesMixin,
    RefsMixin,
    RosterMixin,
    MaintenanceMixin,
    RetypeMixin,
    RenameMixin,
    MemoryMixin,
):
    """Orchestration façade: the logic behind each CLI command.

    The ``.md`` frontmatter is the durable source of truth; ``.squads.json`` is a rebuildable index.
    """


async def init(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: list[str] | None = None,
    roles_spec: str = "all",
    no_claude: bool = False,
    force: bool = False,
    names: dict[str, str] | None = None,
    _skip_skill_seed: bool = False,
) -> InitResult:
    """Initialise a new squad.

    ``names`` maps role slug → full name for any roles that should have a custom name at
    creation time (combines ``--name`` flags and ``[init.names]`` config).  Slugs not in
    ``names`` fall through to the bundled pool / PREDEFINED.

    ``_skip_skill_seed`` is an **internal testing hook** — production callers must never
    set it.  When ``True``, the bundled-skill id-stamping step is omitted so existing tests
    that pre-date skill seeding are not disrupted by the shifted global counter.
    """
    root = (root or Path.cwd()).resolve()
    config_path = root / CONFIG_FILENAME
    if await _aio.path_exists(config_path) and not force:
        raise AlreadyInitializedError(f"{config_path} already exists (use --force to overwrite)")

    effective_names = names or {}
    effective_backends: list[str] = backend if backend is not None else ["claude_code"]
    config = SquadsConfig(
        squad_dir=squad_dir,
        active_backends=effective_backends,
        default_role="manager",
        squads_version=__version__,
        init_names=effective_names,
    )
    await _aio.write_text(config_path, config.to_toml())

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    for ts in bundled_spec().items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    await _aio.write_text(sp.squad_dir / ".gitignore", ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path)
    await store.create_empty_threaded(__version__)

    svc = Service(sp)
    if not no_claude:
        await svc.scaffold_backend()

    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [await svc.activate_role(r.slug, name=effective_names.get(r.slug)) for r in role_defs]

    if not no_claude:
        await svc.refresh_managed()
        # After refresh_managed has written the skill body files (with sq:body markers),
        # stamp each managed skill as a first-class SKILL item in lexical-by-slug order.
        if not _skip_skill_seed:
            await svc.seed_bundled_skills()

    return InitResult(paths=sp, roles=created)


async def adopt(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: list[str] | None = None,
    roles_spec: str = "all",
    no_claude: bool = False,
) -> AdoptResult:
    """Bring an existing squad-structured folder under sq management (non-destructive).

    Unlike ``init``, this tolerates a pre-existing ``.squads.toml``/folder and **imports** any
    squads-native ``.md`` files already present (building the index + counter from them), then
    ensures the backend scaffolding and bundled roles without clobbering.
    """
    root = (root or Path.cwd()).resolve()
    config_path = root / CONFIG_FILENAME
    if await _aio.path_exists(config_path):
        config = load_config(config_path)
        squad_dir = config.squad_dir
    else:
        effective_backends: list[str] = backend if backend is not None else ["claude_code"]
        config = SquadsConfig(
            squad_dir=squad_dir,
            active_backends=effective_backends,
            default_role="manager",
            squads_version=__version__,
        )
        await _aio.write_text(config_path, config.to_toml())

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    for ts in bundled_spec().items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    gitignore = sp.squad_dir / ".gitignore"
    if not await _aio.path_exists(gitignore):
        await _aio.write_text(gitignore, ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path)
    if not store.exists():
        await store.create_empty_threaded(__version__)

    svc = Service(sp)
    # Import any existing squads-native .md files (sets counter from them).
    repair_result = await svc.repair()
    existing_roles = {
        it.extra.get(X.SLUG) for it in repair_result.db.items.values() if it.type == META_ROLE
    }

    if not no_claude:
        await svc.scaffold_backend()
    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [await svc.activate_role(r.slug) for r in role_defs if r.slug not in existing_roles]
    if not no_claude:
        await svc.refresh_managed()

    return AdoptResult(paths=sp, imported=len(repair_result.db.items), roles=created)


def open_service(dir_override: str | None = None) -> Service:
    """Resolve the active squad, load (and activate) its workflow spec, return a Service.

    If the squad has a workflow override under ``<squad_dir>/.overrides/workflow.toml``
    it is merged additively over the bundled default and passed explicitly to
    ``Service``.  A squad with no override uses the cached ``_BUNDLED_SPEC`` fast-path —
    no re-parse on every call.

    A spec that fails validation raises ``SquadsError`` pointing to ``sq workflow lint``.
    No command proceeds with an invalid spec.

    After loading the spec, the live index is cross-checked for items whose type or
    status is no longer declared in the spec.  A mismatch raises ``SquadsError``
    listing every offending item ID.

    ``sq workflow lint`` bypasses this by calling ``lint_workflow_spec`` directly —
    it reports the same errors in collect mode without going through ``open_service``.
    """
    from squads._errors import SquadsError
    from squads._workflow._loader import (
        WORKFLOW_OVERRIDE_FILENAME,
        load_workflow_spec,
        validate_against_index_fail_closed,
    )

    sp = resolve(dir_override)

    override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        # F3 fast-path: no override → use the already-validated bundled singleton.
        return Service(sp, spec=bundled_spec())

    # Override present: load, merge, validate, then AC#5 cross-check.
    try:
        merged_spec = load_workflow_spec(squad_dir=sp.squad_dir)
    except SquadsError as exc:
        raise SquadsError(f"{exc} — run `sq workflow lint` to see details") from exc

    # AC#5: cross-check the merged spec against the live index — raises if any item's
    # type or status is not declared by the new spec.
    validate_against_index_fail_closed(merged_spec, sp.squad_dir)

    return Service(sp, spec=merged_spec)
