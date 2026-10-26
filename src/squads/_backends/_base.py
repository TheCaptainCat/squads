"""Pluggable agent-backend interface. Claude Code is the first implementation."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from squads._interactions._models import PlaybookSpec
from squads._interactions._role_guidance import skills_for_role
from squads._interactions._skills import resolve_operator_invocable
from squads._language import WorkingLanguage, resolve_working_language
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef
from squads._roles._models import CatalogSource
from squads._roles._projection import OperatorView, RoleView
from squads._workflow._models import WorkflowSpec


@dataclass(frozen=True)
class Artifact:
    """A tool-owned file the backend generated (path is project-root-relative)."""

    path: str
    kind: str  # backend-specific category, e.g. agent | skill | config | index
    backend: str
    # Set when writing this artifact surfaced something WARN-only the caller should print —
    # e.g. "inserted the managed region into pre-existing hand-written content". Never gates
    # anything; ``None`` (the common case) means "nothing to report".
    warning: str | None = None


@dataclass
class BackendContext:
    paths: SquadPaths
    # Slug → absolute body path of already-seeded skill items, filled by refresh_managed() from
    # the index so a backend never loads it (_backends reads no index). Empty before seeding,
    # when the backend falls back to the slug-named temporary path.
    skill_paths: dict[str, Path]
    # Role slug → preload-skill list (system membership plus `scopes` ref edges), filled by the
    # service for the same layering reason as skill_paths. An absent entry falls back to the
    # pure `role_guidance.skills_for_role` in :meth:`resolved_skills_for`.
    role_skills: dict[str, list[str]]
    # Active workflow spec — supplied by the Service so backends can enumerate custom types.
    spec: WorkflowSpec
    # Active (merged) playbook — supplied by the Service alongside ``spec`` so a per-type skill
    # writer sees a project override's role guidance.
    playbook: PlaybookSpec
    # The squad's role catalog, read on first use — supplied by the Service so a backend never
    # loads the project's roles override itself.
    catalog: CatalogSource
    # The live role/skill slugs, filled by the caller (`sq check`'s `backend_reconciled`, `sync`'s
    # regeneration report) via `is_live_roster_entry`, for the same layering reason as
    # `skill_paths`. Empty by default, so `managed_entry_paths` names nothing.
    live_role_slugs: frozenset[str]
    live_skill_slugs: frozenset[str]
    # Slug -> resolved ``operator_invocable`` for every live skill item, populated by the service
    # for the item-less managed writer. A slug absent here resolves to its declared default.
    skill_invocable: dict[str, bool]

    def __init__(  # noqa: PLR0913 — one parameter per input a backend reads
        self,
        paths: SquadPaths,
        spec: WorkflowSpec,
        playbook: PlaybookSpec,
        catalog: CatalogSource,
        skill_paths: dict[str, Path] | None = None,
        role_skills: dict[str, list[str]] | None = None,
        live_role_slugs: frozenset[str] | None = None,
        live_skill_slugs: frozenset[str] | None = None,
        skill_invocable: dict[str, bool] | None = None,
    ) -> None:
        self.paths = paths
        self.skill_paths = skill_paths if skill_paths is not None else {}
        self.role_skills = role_skills if role_skills is not None else {}
        self.spec = spec
        self.playbook = playbook
        self.catalog = catalog
        self.live_role_slugs = live_role_slugs if live_role_slugs is not None else frozenset()
        self.live_skill_slugs = live_skill_slugs if live_skill_slugs is not None else frozenset()
        self.skill_invocable = skill_invocable if skill_invocable is not None else {}

    @property
    def root(self) -> Path:
        return self.paths.root

    @property
    def squad_dir(self) -> Path:
        return self.paths.squad_dir

    @property
    def working_language(self) -> WorkingLanguage:
        """The squad's working language, English when the configured value is unusable."""
        return resolve_working_language(self.paths.config.working_language)[0]

    def rel(self, path: Path) -> str:
        """Root-relative forward-slash path (for Artifact paths and backend-owned references)."""
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def operator_invocable(self, slug: str, item: Item | None = None) -> bool:
        """Whether the person at the keyboard is offered skill *slug*: resolved from *item* when
        one is given, else from the service-supplied map, else the declared default."""
        if item is None and slug in self.skill_invocable:
            return self.skill_invocable[slug]
        return resolve_operator_invocable(slug, item, self.spec)[0]

    def resolved_skills_for(self, role: RoleDef) -> list[str]:
        """A role's resolved preload-skill list: ``role_skills[slug]`` when populated, else the
        pure system-membership fallback.

        The single read path every backend uses instead of calling
        ``role_guidance.skills_for_role`` directly, so a data-driven ``scopes`` edge reaches
        every backend uniformly once the service populates ``role_skills`` — never only one.
        """
        if role.slug in self.role_skills:
            return self.role_skills[role.slug]
        return skills_for_role(role, self.spec, self.playbook)


class AgentBackend(ABC):
    """Contract every agent-tool backend (Claude Code, AGENTS.md, a future host) satisfies.

    Two "don't hand-edit" messages live at two altitudes. Squad data (items, role/skill bodies) is
    sq-managed and mutated only via the `sq` CLI, stated once globally and not this ABC's concern.
    A backend's own generated agent-facing files are tool-generated by ``sq sync``: every managed
    region it injects into a user-owned file (its `CLAUDE.md`/`AGENTS.md` section) and every whole
    file it owns (a pointer under its tool directory) MUST carry a "regenerated by `sq sync`; do
    not edit by hand" warning where an agent actually reads it, since an in-session edit is never
    safe. A managed region uses the shared ``_backends._managed_region`` helpers so every backend
    inherits the warning. Generated files stay regenerable and are never migrated.

    The five per-host questions. A generated pointer materialises only what its host needs before
    an agent can act, plus the commands that fetch the rest, never a local path or more state than
    the containment rule allows. A host's answer to each question varies, so each backend answers
    all five at its own definition (search its module for "Question"):

    1. Can an agent under this host execute a command at all? That decides whether a runtime
       fetch can substitute for anything materialised. ``_claude_code`` answers "yes",
       ``_agents_md`` "not knowably", a value of its own: a host's capability is declared by
       whoever builds the backend, never assumed here.
    2. Which projected values does the host's configuration have a place for? The expressible
       set, as ``_VALID_MODELS``/``model_drop_warning`` (``_claude_code/_frontmatter.py``) do for
       one field. A value the host cannot express is reported once at write time and dropped, and
       is not validated again at storage time; the set is backend-local, since a second backend
       may know a different vocabulary.
    3. Which must be present for the host to find and dispatch an entry? The irreducible set from
       the host's own discovery contract, not Claude Code's ``name``/``description`` by default.
    4. Which constrain what the session may do rather than how it runs? The capability boundary,
       however the host spells it: :meth:`restriction_fragment`.
    5. What would you write for this entry, without writing it? The pure render
       (:meth:`render_role_entry`/:meth:`render_skill_entry`) that the currency comparison of
       :func:`~squads._services._validators.backend_entry_drift` consumes, compared only against
       the path the backend declares (invariant 6).

    Questions 4 and 5 are non-abstract methods with a working default, so the abstract set does
    not grow (see :meth:`managed_entry_paths`). Questions 1-3 are prose at each backend, since
    nothing branches on them and a runtime representation would be a model with no consumer, which
    ``tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`` keeps out of a
    different seam.
    """

    name: str

    @abstractmethod
    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        """Create backend dirs and base config (idempotent; never clobber user content)."""

    @abstractmethod
    async def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        """(Re)write roster/version-dependent files: skill definitions and backend config."""

    @abstractmethod
    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        """Write the backend's entry for a role (loads the role's real definition)."""

    @abstractmethod
    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        """Write the backend's entry for a skill (loads the skill's real definition)."""

    @abstractmethod
    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Delete the backend entry/entries for an item."""

    @abstractmethod
    async def candidate_orphans(
        self, ctx: BackendContext, roster: list[RoleView], skill_slugs: set[str]
    ) -> list[str]:
        """Root-relative agent-pointer/skill files on disk that this backend does not manage.

        A file is a candidate when it names no slug in *roster* and none in *skill_slugs* (every
        SKILL item plus every system or per-type skill the spec implies, whether or not this run
        rewrote it). The caller (``sq init``/``sq adopt``) reports them as warnings. Read-only:
        never delete, move or rewrite anything. A matching slug is never reported, even if this
        invocation did not touch the file (``adopt`` regenerates only a newly activated role's
        pointer), since it is squads-managed territory.
        """

    @abstractmethod
    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths this backend owns and ``sq check`` expects to exist.

        Read-only: returns the paths ``ensure_scaffold``/``write_managed`` would write, without
        writing them. ``sq check`` verifies presence only, not currency.

        Scope it to the always-present top-level files whose absence means the backend was never
        scaffolded or synced (the compiled ``CLAUDE.md``/``AGENTS.md``), never to a per-entry
        pointer. ``sq check`` reports an absent path here at error. A per-entry pointer (one
        role's ``.claude/agents/<slug>.md``, one skill's staging file) belongs in
        :meth:`managed_entry_paths`, reported at warn. Gitignoring a backend's whole directory is
        not excused by that level, since it already fails here for the missing top-level path; the
        per-entry rule exists because an untracked pointer beside tracked top-level files was
        otherwise invisible to ``sq check``.
        """

    def managed_entry_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative pointer paths, one per live role/skill in *ctx*, this backend expects.

        The contract is as :meth:`managed_paths`: present-only and read-only, scoped to the
        roster. It never creates, modifies or probes the filesystem and never computes liveness; it
        reads ``ctx.live_role_slugs``/``ctx.live_skill_slugs`` as given, since a backend reads no
        index (see :class:`BackendContext`). An empty *ctx* (the conformance-test default) gives an
        empty result.

        ``sq check``'s ``backend_reconciled`` reports an absent path here at warn, not
        :meth:`managed_paths`'s error. ``sync`` also calls it before and after its writes to report
        what it regenerated (``MaintenanceMixin.sync``). Both callers hand it the same live set
        from :func:`is_live_roster_entry`, so retiring or reactivating an entry never gives a false
        positive on either side: a retired slug is absent from the live set, so its withdrawn
        pointer is never named.

        It is not abstract: the documented ``AgentBackend`` surface (``docs/stability.md``,
        ``docs/backends.md``) is exactly seven methods and does not grow. The default (an empty
        list, "no per-entry pointers declared") keeps a third-party backend written against those
        seven valid; a backend that keeps it is never warned about a missing per-entry pointer.
        Both bundled backends override it.
        """
        return []

    def restriction_fragment(self, role: RoleDef) -> str | None:
        """Question 4: the substring *role*'s entry carries iff its capability boundary applies.

        ``None`` when the boundary does not apply now, or this backend expresses none. It is pure
        and synchronous, a function of *role* alone (``role.can_spawn``), never of what is
        on disk. This seam keys the currency severity of
        :func:`~squads._services._validators.backend_entry_drift` to the containment rule rather
        than a field name: a live role whose current fragment is missing from its on-disk pointer
        is a capability escalation (a stale pointer still granting authority the squad revoked,
        unrepairable from inside the session it governs) and reports at error; other drift is a
        warn.

        Not abstract, as :meth:`managed_entry_paths`: the default (``None``) keeps the
        seven-method promise and means a backend with no boundary is never warned at error.
        """
        return None

    def render_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> str | None:
        """Question 5, role: the pure render of what :meth:`generate_role_entry` would write.

        ``None`` when the backend has no per-entry role artifact (``AgentsMdBackend`` writes only
        a legacy-file cleanup). Synchronous and side-effect-free: never write or probe the
        filesystem. The render is the expectation the :mod:`_services._validators` currency
        comparison holds the on-disk file against; every declaration still comes from
        *item*/*role*, as in :meth:`generate_role_entry`, never from the file. It is compared only
        against the path this backend declares (:meth:`managed_entry_paths`, one slug), so the
        checker never reaches into a host's directory itself (invariant 6).

        Not abstract, as :meth:`managed_entry_paths`: the default (``None``) means "nothing to
        compare", so a backend without a per-entry role file is never reported as drifted.
        """
        return None

    def render_skill_entry(self, ctx: BackendContext, item: Item) -> str | None:
        """Question 5's skill sibling — see :meth:`render_role_entry` for the full contract.
        ``None`` by default, same rationale."""
        return None
