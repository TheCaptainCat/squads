"""Pluggable agent-backend interface. Claude Code is the first implementation."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from squads._interactions import skills_for_role
from squads._interactions._models import PlaybookSpec
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef
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


@dataclass(frozen=True)
class RoleView:
    """The roster entry passed to backends (decoupled from RoleDef internals).

    Carries every role field a backend renders into a compiled managed region. ``mission`` and
    ``responsibilities`` are here for a specific reason: without them the AGENTS.md backend
    could not see either, and recovered the mission by string-matching the ``**Mission:**``
    line back out of markdown it had itself generated one step earlier — a rendering
    convention standing in for a declaration, over a template that is meant to be editable.
    Relabelling that line silently emptied every mission in the compiled file, and
    ``responsibilities`` was never recovered at all, so the section's responsibilities block
    had never once rendered. A view field is the declaration; the generated text is output,
    never an input.
    """

    slug: str
    full_name: str
    title: str
    is_default: bool
    mission: str = ""
    responsibilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperatorView:
    """A human operator passed to backends for the CLAUDE.md people roster."""

    slug: str
    full_name: str


@dataclass
class BackendContext:
    paths: SquadPaths
    # Slug → absolute body path for already-seeded skill items.  Populated by
    # refresh_managed() from the index before calling write_managed, so backends
    # never need to load the index themselves (layering: _backends reads no index).
    # Empty dict on first-write paths (pre-seeding); skill_paths.get(slug) returns
    # None in that case and the backend falls back to the slug-named temporary path.
    skill_paths: dict[str, Path]
    # Role slug → resolved preload-skill list (system membership unioned with data-driven
    # `scopes` ref edges).  Populated by the service (refresh_managed()/sync()) from the
    # index, same layering rationale as skill_paths: backends read it here rather than
    # resolving scope edges themselves.  Absent entries fall back to the pure
    # `interactions.skills_for_role` in :meth:`resolved_skills_for` — see that method.
    role_skills: dict[str, list[str]]
    # Active workflow spec — supplied by the Service so backends can enumerate custom types.
    # ``None`` means use only built-in types (backward-compatible default for callers that
    # don't supply a spec, e.g. backend conformance tests).
    spec: WorkflowSpec | None
    # Active (merged) playbook — supplied by the Service alongside ``spec`` so a per-type skill
    # writer sees a project override's role guidance. ``None`` means the bundled playbook
    # (:func:`squads._interactions.get_playbook_spec`) — the same backward-compatible default
    # shape as ``spec`` above, for callers (backend conformance tests) that supply neither.
    playbook: PlaybookSpec | None
    # The roster's currently-live role/skill slugs — populated by the caller (``sq check``'s
    # `backend_reconciled`, `sync`'s before/after regeneration report) from the index via
    # `squads._interactions.is_live_roster_entry`, same layering rationale as `skill_paths`/
    # `role_skills`: a backend never loads the index itself, so it reads the live set here
    # rather than deriving it. Empty by default, which makes `managed_entry_paths` report no
    # per-entry paths at all — the correct answer for a caller that has not populated these
    # (e.g. a conformance test using `managed_paths` alone).
    live_role_slugs: frozenset[str]
    live_skill_slugs: frozenset[str]

    def __init__(
        self,
        paths: SquadPaths,
        skill_paths: dict[str, Path] | None = None,
        role_skills: dict[str, list[str]] | None = None,
        spec: WorkflowSpec | None = None,
        playbook: PlaybookSpec | None = None,
        live_role_slugs: frozenset[str] | None = None,
        live_skill_slugs: frozenset[str] | None = None,
    ) -> None:
        self.paths = paths
        self.skill_paths = skill_paths if skill_paths is not None else {}
        self.role_skills = role_skills if role_skills is not None else {}
        self.spec = spec
        self.playbook = playbook
        self.live_role_slugs = live_role_slugs if live_role_slugs is not None else frozenset()
        self.live_skill_slugs = live_skill_slugs if live_skill_slugs is not None else frozenset()

    @property
    def root(self) -> Path:
        return self.paths.root

    @property
    def squad_dir(self) -> Path:
        return self.paths.squad_dir

    def rel(self, path: Path) -> str:
        """Root-relative forward-slash path (for Artifact paths and backend-owned references)."""
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def resolved_skills_for(self, slug: str) -> list[str]:
        """A role's resolved preload-skill list: ``role_skills[slug]`` when populated, else the
        pure system-membership fallback.

        The single read path every backend uses instead of calling
        ``interactions.skills_for_role`` directly, so a data-driven ``scopes`` edge reaches
        every backend uniformly once the service populates ``role_skills`` — never only one.
        """
        if slug in self.role_skills:
            return self.role_skills[slug]
        return skills_for_role(slug, self.spec, self.playbook)


class AgentBackend(ABC):
    """Contract every agent-tool backend (Claude Code today; a future Copilot/Cursor/
    AGENTS.md-only backend tomorrow) must satisfy.

    Two distinct "don't hand-edit" messages live at two different altitudes, and each backend
    owns stamping the second one:

    1. **Squad data is sq-managed.** Everything under the squad folder (items, role/skill
       bodies) is mutated only via the `sq` CLI. Stated once, globally — not this ABC's concern.
    2. **This backend's own generated agent-facing files are tool-generated by ``sq sync``.**
       Every managed region a backend injects into an otherwise user-owned file (its
       `CLAUDE.md`/`AGENTS.md` section) and every whole file it owns outright (a pointer/config
       file under its own tool directory) MUST carry a "regenerated by `sq sync`; do not edit by
       hand" warning near where an agent or human actually reads it — these are the files an
       agent opens as *working context* and could edit in-session without realizing the edit is
       never safe. Use the shared ``_backends._managed_region`` wrap/inject helpers for a managed
       region so every backend inherits the warning consistently instead of re-implementing it.

    Generated files stay regenerable and are never migrated (deleting one loses nothing) — the
    warning only makes that fact visible in place; it doesn't change the promise.

    **The five per-host questions.** A generated pointer materialises only what its host needs
    before an agent can act, plus the commands that fetch the rest — never a local path, never
    more state than the containment rule below allows. That rule is universal; a host's *answer*
    to each question is not, so each is phrased for an author who
    has read only their own host's documentation, with no reading of squads internals required.
    Both bundled backends answer all five explicitly, at their own definitions — search each
    backend's module for "Question" to find them:

    1. **Can an agent running under this host execute a command at all?** Whether a runtime
       fetch can ever substitute for anything this backend materialises. ``_claude_code``
       answers "yes"; ``_agents_md`` answers "not knowably" — a third value, not a missing one:
       a host's command-execution capability is declared by whoever builds a backend for it,
       never assumed here.
    2. **Which of the values squads projects does this host's configuration have a place for?**
       The expressible set, generalising ``_VALID_MODELS``/``model_drop_warning``
       (``_claude_code/_frontmatter.py``) from one field to all of them — a value this host
       cannot express is reported once, at write time, and dropped, never silently, and never
       re-validated a second time at storage time. This is backend-local by the same reasoning
       ``_VALID_MODELS`` already documents: it describes what *this host tool* can express, so a
       second backend is free to know a different vocabulary.
    3. **Which of those must be present for this host to find and dispatch an entry at all?**
       The irreducible set, from the host's own discovery contract — never lifted from Claude
       Code's ``name``/``description``, the least representative example available.
    4. **Which of those constrain what the session may do, rather than configure how it runs?**
       The capability boundary, however the host spells it — :meth:`restriction_fragment`.
    5. **What would you write for this entry, without writing it?** The pure render —
       :meth:`render_role_entry`/:meth:`render_skill_entry` — that :meth:`sq check
       <squads._services._validators.backend_entry_drift>`'s currency comparison consumes,
       compared only against the path the backend itself declares (invariant 6) so the checker
       never reaches into a host's directory on its own.

    Questions 4 and 5 need a code seam and get one below, as **non-abstract methods with a
    working default** (never growing the abstract seven — see :meth:`managed_entry_paths`'s own
    docstring for the precedent and why). Questions 1-3 are answered in prose at each backend's
    own definition: nothing downstream branches on them today, so giving them a runtime
    representation would be a data model with no consumer — exactly what
    ``tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`` exists to keep out
    of a *different* seam. A future backend answers all five when it is built, from its own
    host's documentation, without re-litigating the rule itself.
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
        """Root-relative paths of on-disk agent-pointer/skill files this backend does NOT
        currently manage — present on disk but naming no slug in *roster* and no slug in
        *skill_slugs* (the full known-skill vocabulary: every SKILL item plus every
        system/per-type skill the spec implies, regardless of whether this particular run
        happened to rewrite it).

        WARN-only candidates for the caller (``sq init``/``sq adopt``) to report. Read-only:
        must never delete, move, or rewrite anything; a slug match is NOT reported even when
        this exact invocation didn't literally touch that file (e.g. `adopt` only regenerates
        a NEWLY activated role's pointer), because a matching slug is still squads-managed
        territory, not an orphan.
        """

    @abstractmethod
    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths this backend owns and that sq check expects to exist.

        Read-only: must not create or modify any file.  Returns the same root-relative
        paths that ``ensure_scaffold`` / ``write_managed`` would write, without writing
        them.  Used by ``sq check`` to verify that scaffolding exists (present-only check
        — not a currency/drift check).

        Scope this to the always-present top-level files whose absence means the backend was
        never scaffolded/synced at all (this backend's compiled ``CLAUDE.md``/``AGENTS.md``
        and the like) — never to a per-entry pointer. ``sq check`` reports an absent path here
        at **error**: nothing short of running ``sq sync`` explains it away. A per-entry
        pointer (one role's ``.claude/agents/<slug>.md``, one skill's staging file, …) belongs
        in :meth:`managed_entry_paths` instead, which ``sq check`` reports at **warn** — not
        because gitignoring this backend's whole directory is a choice this gate must not fail
        over (it does not escape this: a fully gitignored directory is already missing the
        very top-level path this method itself declares, and already fails at this method's
        **error** level, before and after the per-entry rule existed). The honest reason is
        narrower: a per-entry pointer going untracked while the top-level files stayed tracked
        was, before that rule, invisible to ``sq check`` altogether — not error, not warn,
        nothing. Warn keeps that previously-silent shape's exit code unchanged rather than
        adding a new error to a patch release.
        """

    def managed_entry_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative per-entry pointer paths — one per role/skill *currently live* in
        *ctx* — this backend expects to exist.

        Same present-only, read-only contract as :meth:`managed_paths`, scoped to the roster
        instead of to this backend's fixed top-level files: never create, modify, or probe the
        filesystem beyond what the caller does with the returned paths, and never compute
        liveness — read ``ctx.live_role_slugs``/``ctx.live_skill_slugs`` as given (a backend
        reads no index; see :class:`BackendContext`'s own fields). An empty *ctx* (the
        conformance-test default) means an empty result, not "declare nothing was ever meant
        to exist" — see the fields' own docstring.

        ``sq check``'s ``backend_reconciled`` rule reports an absent path here at **warn**,
        never at :meth:`managed_paths`'s error — see that method's docstring for why the two
        differ. ``sync`` also calls this, before and after its own writes, to report which of
        these it just had to regenerate (see ``MaintenanceMixin.sync``); both callers hand it
        the exact same live set derived via
        :func:`~squads._interactions.is_live_roster_entry`, so retiring or reactivating a
        role/skill can never produce a false positive on either side of the transition — a
        retired entry's slug is simply absent from ``ctx.live_role_slugs``/
        ``live_skill_slugs``, so this method never names its (correctly withdrawn) pointer at
        all.

        **Not an abstract method.** The documented ``AgentBackend`` surface
        (``docs/stability.md``, ``docs/backends.md``) is exactly seven methods and does not
        grow; this default (an empty list — "no per-entry pointers declared") keeps that
        promise for a third-party backend written against the documented seven while still
        letting a bundled backend override it to opt into the ``sq check``/``sq sync``
        per-entry reporting above. Both bundled backends (``claude_code``, ``agents_md``)
        override it; a backend that doesn't is simply never warned about a missing per-entry
        pointer, exactly as if it had none to declare.
        """
        return []

    def restriction_fragment(self, role: RoleDef) -> str | None:
        """Question 4's per-role answer: the exact substring this backend's rendered role entry
        carries **when and only when** *role*'s current capability boundary applies, or ``None``
        when it does not apply right now (or this backend expresses no such boundary at all).

        Pure and synchronous — a function of *role* alone, no ``ctx``, no I/O: the boundary is a
        property of the role's own declared authority (``role.can_spawn`` today), never of
        anything already on disk. This is the seam that keys ``sq check``'s currency severity to
        the containment rule instead of a hard-coded field name
        (:func:`~squads._services._validators.backend_entry_drift`): a live role whose current
        fragment is absent from its on-disk pointer is a capability escalation — a stale pointer
        still granting authority the squad revoked, unrepairable from inside the session it
        governs — reported at **error**; any other content drift is a **warn**.

        **Not an abstract method**, same rationale as :meth:`managed_entry_paths`: the default
        (``None``, always) keeps the documented seven-method promise for a third-party backend,
        and reads as the honest answer for one that expresses no capability boundary at all —
        never warned at error severity, exactly as if it had none to check.
        """
        return None

    def render_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> str | None:
        """Question 5's role answer: the pure render of what :meth:`generate_role_entry` would
        write for this role, without writing it — ``None`` when this backend has no per-entry
        role artifact (see :class:`AgentsMdBackend
        <squads._backends._agents_md._backend.AgentsMdBackend>`, whose ``generate_role_entry``
        writes nothing but a legacy-file cleanup).

        Synchronous and side-effect-free by contract: never write, never probe the filesystem —
        the render is the expectation an :mod:`_services._validators` currency comparison holds
        the file on disk against, never a value this method or its caller derives *from* that
        file (the never-read-back guard's direction of authority — item to output, never output
        to item — is unaffected: every declaration here still comes from *item*/*role*, exactly
        as :meth:`generate_role_entry` computes them). Compared only against the path this same
        backend declares (:meth:`managed_entry_paths`, scoped to one slug) — the checker never
        reaches into a host's directory on its own (invariant 6).

        **Not an abstract method**, same rationale as :meth:`managed_entry_paths`: the default
        (``None``, always) keeps the documented seven-method promise, and reads as "nothing to
        compare" for a backend with no per-entry role file — never reported as drifted, exactly
        as if it declared no per-entry path for one.
        """
        return None

    def render_skill_entry(self, ctx: BackendContext, item: Item) -> str | None:
        """Question 5's skill sibling — see :meth:`render_role_entry` for the full contract.
        ``None`` by default, same rationale."""
        return None
