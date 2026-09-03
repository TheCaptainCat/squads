"""The ``Service`` facade — all concern mixins composed over ``ServiceCore`` — plus the
``init`` / ``adopt`` / ``open_service`` entry points.

``Service`` keeps a flat API (``svc.create()``, ``svc.comment()``, …); each method lives in the
concern mixin under ``_services/``.
"""

from pathlib import Path

from squads import __version__, _aio
from squads._errors import AlreadyInitializedError, PlaybookConfigError, SquadsError
from squads._index._store import IndexStore
from squads._interactions import get_playbook_spec
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME, load_playbook
from squads._interactions._models import PlaybookSpec
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._paths import SquadPaths, load_config, resolve
from squads._roles._catalog import RoleDef, get_catalog, resolve_roles
from squads._services._board import BoardMixin
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
from squads._workflow import ROSTER_ROLE, bundled_spec
from squads._workflow._models import WorkflowSpec


class Service(
    ImportMixin,
    ItemsMixin,
    CollabMixin,
    SubentitiesMixin,
    RefsMixin,
    RosterMixin,
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


def resolve_playbook(spec: WorkflowSpec, squad_dir: Path) -> PlaybookSpec:
    """The merged playbook for *spec*/*squad_dir* — the playbook counterpart to the workflow
    spec's own fast-path/merge split in :func:`open_service`.

    Coverage always validates against *spec* (see ``_interactions._loader``'s module
    docstring), so this must still run through :func:`load_playbook` — reparsing the bundled
    ``playbook.toml`` and revalidating coverage — whenever *spec* is not the untouched bundled
    singleton, even with no ``.overrides/playbook.toml`` present: a workflow override alone can
    change which types the playbook must now cover. Only when *spec* IS the bundled singleton
    **and** no playbook override file exists does this take the zero-reparse fast path and
    return the cached bundled playbook — byte-identical to a squad with no overrides at all.

    Raises :class:`~squads._errors.PlaybookConfigError` (never a plain ``SquadsError``) on any
    load/validation failure — the one place that distinction is made, so both call sites in
    :func:`open_service` (the fast path and the merged path) get it for free rather than each
    wrapping the loader's error separately. The wrapped message names the override file
    directly: unlike the workflow spec, there is today no dedicated lint surface to point a
    caller at (``sq override diff playbook`` diffs raw text; it does not load or validate), so
    this names *what* is wrong (the loader's own message, already specific — a malformed-TOML
    location, a referential/coverage violation) and *where* (the file) rather than inventing a
    command that would not actually diagnose it.
    """
    override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if spec is bundled_spec() and not override_path.is_file():
        return get_playbook_spec()
    try:
        return load_playbook(get_catalog(), spec=spec, squad_dir=squad_dir)
    except SquadsError as exc:
        raise PlaybookConfigError(f"{exc} — see {override_path}") from exc


def _init_time_spec(squad_dir: Path) -> WorkflowSpec:
    """The spec ``init``/``adopt`` must scaffold against.

    The override lives *inside* the squad directory these two callers are creating/populating
    (``<squad_dir>/.overrides/workflow.toml``), so a pre-placed override — dropped there by hand
    before a fresh ``sq init``, or already part of a folder ``sq adopt`` is importing — is only
    visible once ``squad_dir`` itself exists, which both callers guarantee before calling this.
    When present, it is loaded and validated exactly the way ``open_service`` loads it later
    (fail-closed on a floor violation, pointing at ``sq workflow lint``) so every scaffolding
    decision this call makes — which folders to create, what initial status a freshly-activated
    roster item gets via ``self.spec.initial_status`` — is made against the SAME spec every
    subsequent command will load, not the bundled default the merged spec may disagree with.

    With no override file present this returns the cached bundled singleton with no extra
    parsing — byte-identical to the pre-existing behaviour.
    """
    from squads._errors import SquadsError
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec

    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return bundled_spec()
    try:
        return load_workflow_spec(squad_dir=squad_dir)
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

    # Validate a pre-placed override before any state is written: the override path is
    # derivable from root/squad_dir alone, so a malformed or floor-violating override means
    # init never starts (no config, no scaffolding) rather than wedging a half-created squad
    # a retry can neither finish nor cleanly restart from.
    effective_spec = _init_time_spec(root / squad_dir)

    effective_names = names or {}
    effective_backends: list[str] = backend if backend is not None else ["claude_code"]
    config = SquadsConfig(
        squad_dir=squad_dir,
        active_backends=effective_backends,
        squads_version=__version__,
        init_names=effective_names,
    )
    await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    for ts in effective_spec.items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    await _aio.write_text(sp.squad_dir / ".gitignore", ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path)
    await store.create_empty_threaded(__version__)

    svc = Service(sp, spec=effective_spec, playbook=resolve_playbook(effective_spec, sp.squad_dir))
    if not no_claude:
        await svc.scaffold_backend()

    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [await svc.activate_role(r.slug, name=effective_names.get(r.slug)) for r in role_defs]

    warnings: list[str] = []
    if not no_claude:
        warnings += await svc.refresh_managed()
        # After refresh_managed has written the skill body files (with sq:body markers),
        # stamp each managed skill as a first-class SKILL item in lexical-by-slug order.
        # `_init_time_spec` resolves the merged (possibly overridden) spec, so `init` sees
        # custom types just as well as bundled ones — seed both here rather than leaving
        # custom-type skills unindexed until the first `sq sync`.
        if not _skip_skill_seed:
            await svc.seed_bundled_skills()
            await svc.seed_custom_skills()
        warnings += await svc.candidate_orphans()

    return InitResult(paths=sp, roles=created, warnings=warnings)


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

    The import runs through :meth:`Service.repair`, which is also the corpus sweep — so this
    verb rewrites the content of the files it is importing. The whole ``RepairResult`` is
    carried out on :class:`~squads._services._results.AdoptResult` rather than reduced to a
    count so the CLI can announce that diff: a folder of squads-native markdown meeting sq for
    the first time is behind no schema stamp sq can migrate, so this is the only route that
    population takes and its only chance to be told.
    """
    root = (root or Path.cwd()).resolve()
    config_path = root / CONFIG_FILENAME
    if await _aio.path_exists(config_path):
        config = load_config(config_path)
        squad_dir = config.squad_dir
    else:
        # Validate a pre-placed override before writing .squads.toml — same ordering as
        # init() and for the same reason: adopt is the other caller that can create the
        # config file, so it must not wedge a half-created squad behind a bad override either.
        _init_time_spec(root / squad_dir)
        effective_backends: list[str] = backend if backend is not None else ["claude_code"]
        config = SquadsConfig(
            squad_dir=squad_dir,
            active_backends=effective_backends,
            squads_version=__version__,
        )
        await _aio.atomic_write_text(config_path, config.to_toml())
    await ensure_root_tmp_ignored(root)

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    await _aio.mkdir(sp.squad_dir, parents=True, exist_ok=True)
    effective_spec = _init_time_spec(sp.squad_dir)
    for ts in effective_spec.items.values():
        await _aio.mkdir(sp.squad_dir / ts.folder, parents=True, exist_ok=True)
    gitignore = sp.squad_dir / ".gitignore"
    if not await _aio.path_exists(gitignore):
        await _aio.write_text(gitignore, ".squads.json.lock\n*.tmp\n")

    store = IndexStore(sp.index_path, sp.lock_path)
    if not store.exists():
        await store.create_empty_threaded(__version__)

    svc = Service(sp, spec=effective_spec, playbook=resolve_playbook(effective_spec, sp.squad_dir))
    # Import any existing squads-native .md files (sets counter from them).
    repair_result = await svc.repair()
    existing_roles = {
        it.extra.get(X.SLUG) for it in repair_result.db.items.values() if it.type == ROSTER_ROLE
    }

    if not no_claude:
        await svc.scaffold_backend()
    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [await svc.activate_role(r.slug) for r in role_defs if r.slug not in existing_roles]
    warnings: list[str] = []
    if not no_claude:
        warnings += await svc.refresh_managed()
        # Mirrors init()'s seeding step. adopt is the other path that can create a squad's
        # config, so it has to seed both halves — bundled and custom — exactly as init does:
        # without them a generated skill file sits on disk with no SKILL item indexing it,
        # and stays that way until the first `sq sync` seeds it.
        await svc.seed_bundled_skills()
        await svc.seed_custom_skills()
        warnings += await svc.candidate_orphans()

    return AdoptResult(paths=sp, repair=repair_result, roles=created, warnings=warnings)


def open_service(
    dir_override: str | None = None,
    *,
    client_cwd: Path | None = None,
    resolved_spec: WorkflowSpec | None = None,
) -> Service:
    """Resolve the active squad, load (and activate) its workflow spec, return a Service.

    If the squad has a workflow override under ``<squad_dir>/.overrides/workflow.toml``
    it is merged (may shadow the bundled default, not only add to it) and
    passed explicitly to ``Service``.  A squad with no override uses the cached
    ``_BUNDLED_SPEC`` fast-path — no re-parse on every call.

    A spec that fails validation raises ``SquadsError`` pointing to ``sq workflow lint``.
    No command proceeds with an invalid spec. A playbook (bundled + any
    ``.overrides/playbook.toml``) that fails to load or validate raises
    :class:`~squads._errors.PlaybookConfigError` instead — a distinct ``SquadsError``
    subclass, so a caller that wants to tell the two failures apart (``sq check``) can,
    rather than reporting a playbook problem as a workflow one and pointing at a lint command
    that never reads ``.overrides/playbook.toml``.

    After loading the spec, the live index is cross-checked for items whose type or
    status is no longer declared in the spec.  A mismatch raises ``SquadsError``
    listing every offending item ID.

    ``sq workflow lint`` bypasses this by calling ``lint_workflow_spec`` directly —
    it reports the same errors in collect mode without going through ``open_service``.

    ``client_cwd`` threads straight to :func:`squads._paths.resolve` — the requesting
    client's working directory (``None`` falls back to the process cwd, one-shot CLI's
    only case). This function stays a pure, explicit-input call; the CLI edge is what
    reads the ambient request context and passes its ``client_cwd`` in.

    ``resolved_spec``, when given, is a spec the caller has *already* resolved — merged and,
    if an override is present, already run through ``validate_against_index_fail_closed`` —
    for this exact ``(dir_override, client_cwd)``. ``_build_plain_service()``
    (``_cli/_common.py``) is what supplies it, built from the per-invocation spec the CLI's
    root callback already bound via ``bind_active_spec`` — to avoid re-running the same
    load/merge/cross-check a second time on the same corpus within one invocation. Every CLI
    command reaches this, ``sq ui`` included: ``get_service()`` calls
    ``_build_plain_service()`` directly, and ``get_service_bypassing_index_cross_check()``'s
    own first fallback step is a plain ``get_service()`` call, so it supplies
    ``resolved_spec`` too — only that function's steps 2/3 (a genuinely broken override or a
    live-index conflict) construct a ``Service`` straight from
    ``load_workflow_spec``/``bundled_spec`` and never call ``open_service`` at all. The
    callers that actually leave this ``None`` and get the full, independent resolution below
    are the ones that call ``open_service`` directly rather than through ``get_service()`` —
    a direct test call being the common example.
    """
    from squads._workflow._loader import (
        WORKFLOW_OVERRIDE_FILENAME,
        load_workflow_spec,
        spec_refusal,
        validate_against_index_fail_closed,
    )

    sp = resolve(dir_override, client_cwd=client_cwd)

    if resolved_spec is not None:
        return Service(
            sp, spec=resolved_spec, playbook=resolve_playbook(resolved_spec, sp.squad_dir)
        )

    override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        # Fast path: no workflow override → use the already-validated bundled singleton.
        # The playbook may still have its OWN override even with no workflow override, so it
        # is resolved unconditionally through the same helper the merge path below uses —
        # resolve_playbook's own fast path collapses to the bundled playbook singleton too
        # when neither override is present, so a squad with neither still lands on the
        # bundled playbook singleton here.
        spec = bundled_spec()
        return Service(sp, spec=spec, playbook=resolve_playbook(spec, sp.squad_dir))

    # Override present: load, merge, validate, then cross-check. Both halves are rewrapped in
    # the one shared refusal (`spec_refusal`) so this hard stop reads identically to the CLI's
    # own per-invocation binding — the same failure reported twice in two voices is how an
    # adopter ends up believing they are two problems.
    try:
        merged_spec = load_workflow_spec(squad_dir=sp.squad_dir)
        # Cross-check the merged spec against the live index — raises if any item's
        # type or status is not declared by the new spec.
        validate_against_index_fail_closed(merged_spec, sp.squad_dir)
    except SquadsError as exc:
        raise SquadsError(spec_refusal(override_path, exc)) from exc

    # resolve_playbook raises PlaybookConfigError (not a plain SquadsError) on its own
    # failure — no rewrap needed here; see that function's docstring for why the message
    # already names the actually-broken file rather than a non-diagnosing command.
    return Service(sp, spec=merged_spec, playbook=resolve_playbook(merged_spec, sp.squad_dir))
