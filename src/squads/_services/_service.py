"""The ``Service`` facade — all concern mixins composed over ``ServiceCore`` — plus the
``init`` / ``adopt`` / ``open_service`` entry points.

``Service`` keeps a flat API (``svc.create()``, ``svc.comment()``, …); each method lives in the
concern mixin under ``_services/``.
"""

from pathlib import Path

from squads import __version__
from squads._errors import AlreadyInitializedError
from squads._index._store import IndexStore
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._models._enums import FOLDER_BY_TYPE, ItemType
from squads._models._extras import ExtraKey as X
from squads._paths import SquadPaths, load_config, resolve
from squads._roles._catalog import RoleDef, resolve_roles
from squads._services._collab import CollabMixin
from squads._services._items import ItemsMixin
from squads._services._maintenance import MaintenanceMixin
from squads._services._refs import RefsMixin
from squads._services._results import AdoptResult, InitResult
from squads._services._retype import RetypeMixin
from squads._services._roster import RosterMixin
from squads._services._subentities import SubentitiesMixin


class Service(
    ItemsMixin,
    CollabMixin,
    SubentitiesMixin,
    RefsMixin,
    RosterMixin,
    MaintenanceMixin,
    RetypeMixin,
):
    """Orchestration façade: the logic behind each CLI command.

    The ``.md`` frontmatter is the durable source of truth; ``.squads.json`` is a rebuildable index.
    """


def init(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: list[str] | None = None,
    roles_spec: str = "all",
    no_claude: bool = False,
    force: bool = False,
    names: dict[str, str] | None = None,
) -> InitResult:
    """Initialise a new squad.

    ``names`` maps role slug → full name for any roles that should have a custom name at
    creation time (combines ``--name`` flags and ``[init.names]`` config).  Slugs not in
    ``names`` fall through to the bundled pool / PREDEFINED.
    """
    root = (root or Path.cwd()).resolve()
    config_path = root / CONFIG_FILENAME
    if config_path.exists() and not force:
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
    config_path.write_text(config.to_toml(), encoding="utf-8")

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    sp.squad_dir.mkdir(parents=True, exist_ok=True)
    for folder in FOLDER_BY_TYPE.values():
        (sp.squad_dir / folder).mkdir(parents=True, exist_ok=True)
    (sp.squad_dir / ".gitignore").write_text(".squads.json.lock\n*.tmp\n", encoding="utf-8")

    store = IndexStore(sp.index_path, sp.lock_path)
    store.create_empty(__version__)

    svc = Service(sp)
    if not no_claude:
        svc.scaffold_backend()

    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [svc.activate_role(r.slug, name=effective_names.get(r.slug)) for r in role_defs]

    if not no_claude:
        svc.refresh_managed()

    return InitResult(paths=sp, roles=created)


def adopt(
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
    if config_path.exists():
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
        config_path.write_text(config.to_toml(), encoding="utf-8")

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    sp.squad_dir.mkdir(parents=True, exist_ok=True)
    for folder in FOLDER_BY_TYPE.values():
        (sp.squad_dir / folder).mkdir(parents=True, exist_ok=True)
    gitignore = sp.squad_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(".squads.json.lock\n*.tmp\n", encoding="utf-8")

    store = IndexStore(sp.index_path, sp.lock_path)
    if not store.exists():
        store.create_empty(__version__)

    svc = Service(sp)
    # Import any existing squads-native .md files (sets counter from them).
    repair_result = svc.repair()
    existing_roles = {
        it.extra.get(X.SLUG) for it in repair_result.db.items.values() if it.type is ItemType.ROLE
    }

    if not no_claude:
        svc.scaffold_backend()
    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [svc.activate_role(r.slug) for r in role_defs if r.slug not in existing_roles]
    if not no_claude:
        svc.refresh_managed()

    return AdoptResult(paths=sp, imported=len(repair_result.db.items), roles=created)


def open_service(dir_override: str | None = None) -> Service:
    return Service(resolve(dir_override))
