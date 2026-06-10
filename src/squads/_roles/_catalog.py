"""Bundled agent-role definitions.

Each role has a real name ("Robert Architect") and a slug ("architect"); agents are referred to
by full name in files and conversation. Stack-specific developers are created on demand via
``sq dev add`` using :data:`DEV_NAME_POOL`.
"""

from dataclasses import dataclass
from typing import Any

from squads._errors import RoleNotFoundError
from squads._models._extras import ExtraKey as X
from squads._util import slugify


@dataclass(frozen=True)
class RoleDef:
    slug: str
    full_name: str
    title: str
    description: str  # one-liner for the Claude pointer frontmatter
    mission: str
    responsibilities: tuple[str, ...] = ()
    model: str | None = None  # sonnet | opus | haiku | inherit
    color: str | None = None
    is_default: bool = False

    def to_extra(self) -> dict[str, Any]:
        """Type-specific fields stored on the ROLE item."""
        return {
            X.FULL_NAME: self.full_name,
            X.SLUG: self.slug,
            X.TITLE: self.title,
            X.MISSION: self.mission,
            X.RESPONSIBILITIES: list(self.responsibilities),
            X.MODEL: self.model,
            X.COLOR: self.color,
            X.IS_DEFAULT: self.is_default,
        }

    @classmethod
    def from_extra(cls, extra: dict[str, Any]) -> RoleDef:
        return cls(
            slug=extra[X.SLUG],
            full_name=extra[X.FULL_NAME],
            title=extra.get(X.TITLE, ""),
            description=extra.get(X.DESCRIPTION, extra.get(X.TITLE, "")),
            mission=extra.get(X.MISSION, ""),
            responsibilities=tuple(extra.get(X.RESPONSIBILITIES, [])),
            model=extra.get(X.MODEL),
            color=extra.get(X.COLOR),
            is_default=extra.get(X.IS_DEFAULT, False),
        )


PREDEFINED: tuple[RoleDef, ...] = (
    RoleDef(
        slug="manager",
        full_name="Catherine Manager",
        title="manager",
        description=(
            "Default agent: triages the operator's request and routes it to the right specialist."
        ),
        mission=(
            "Be the operator's first point of contact and run the work loop: understand the "
            "intent, delegate to the right specialists, integrate what they return, and drive "
            "each feature to done — keeping everything tracked in squads."
        ),
        responsibilities=(
            "Triage incoming requests and clarify intent",
            "Delegate work to the right specialist agents and integrate their results",
            "Drive features through the loop (implement → review → fix) until done",
            "Keep the backlog and statuses honest",
            "Summarise progress for the operator",
        ),
        model="opus",
        color="cyan",
        is_default=True,
    ),
    RoleDef(
        slug="architect",
        full_name="Robert Architect",
        title="architect",
        description="System design and architecture decisions (ADRs).",
        mission=(
            "Own the system's shape: design coherent solutions, record decisions as ADRs, "
            "and guide implementation."
        ),
        responsibilities=(
            "Design components and their interactions",
            "Write and maintain ADRs",
            "Author cross-cutting guides",
            "Review designs before implementation",
        ),
        model="opus",
        color="blue",
    ),
    RoleDef(
        slug="tech-lead",
        full_name="Olivia Lead",
        title="tech lead",
        description="Coordination and breaking features into tasks.",
        mission="Turn features into well-scoped tasks, sequence the work, and unblock the team.",
        responsibilities=(
            "Author tasks (`sq create task`); set each task's parent to the feature it implements",
            'Map each subtask to a single user story (`sq task <n> add-subtask "…" --story USn`)',
            "For a bug fix or review follow-up, link via refs "
            "(`sq task <n> ref add <id> --kind fixes|addresses`)",
            "Leave purely-technical tasks unlinked",
            "Sequence and assign work; unblock developers",
            "Co-author guides with the architect",
        ),
        model="opus",
        color="purple",
    ),
    RoleDef(
        slug="reviewer",
        full_name="Paul Reviewer",
        title="code reviewer",
        description="Reviews code changes for correctness, clarity, and consistency.",
        mission=(
            "Guard quality: review changes critically, request changes when needed, "
            "approve when sound."
        ),
        responsibilities=(
            "Review diffs for correctness and clarity",
            "Drive code-review items to a verdict",
            "Flag risks and missing tests",
        ),
        model="opus",
        color="red",
    ),
    RoleDef(
        slug="qa",
        full_name="Mara Tester",
        title="QA engineer",
        description="Designs and runs tests; verifies behaviour against acceptance criteria.",
        mission="Prove the software works: design test cases from user stories and verify fixes.",
        responsibilities=(
            "Derive test cases from user stories",
            "Verify bug fixes and features",
            "Report defects as bug items",
        ),
        model="sonnet",
        color="green",
    ),
    RoleDef(
        slug="devops",
        full_name="Hugo Ops",
        title="DevOps engineer",
        description="CI/CD, infrastructure, and releases.",
        mission="Keep delivery smooth: maintain CI/CD, infrastructure, and the release process.",
        responsibilities=(
            "Maintain CI/CD pipelines",
            "Manage infrastructure and environments",
            "Run releases",
        ),
        model="sonnet",
        color="orange",
    ),
    RoleDef(
        slug="product-owner",
        full_name="Nina Product",
        title="product owner",
        description="Requirements, user stories, and backlog priorities.",
        mission=(
            "Represent the user: capture requirements as features and user stories, "
            "prioritise the backlog."
        ),
        responsibilities=(
            "Author features (`sq create feature`)",
            "Write each feature's user stories (`sq story add`)",
            "Prioritise the backlog and define acceptance criteria",
        ),
        model="sonnet",
        color="yellow",
    ),
    RoleDef(
        slug="tech-writer",
        full_name="Theo Writer",
        title="technical writer",
        description="Documentation and guides.",
        mission="Make the work understandable: write and maintain clear documentation and guides.",
        responsibilities=(
            "Write user- and developer-facing docs",
            "Keep guides current",
        ),
        model="haiku",
        color="pink",
    ),
)

_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}

#: Named bundles selectable at ``sq init --roles``.
BUNDLES: dict[str, tuple[str, ...]] = {
    "all": tuple(r.slug for r in PREDEFINED),
    "core": ("manager", "architect", "tech-lead", "reviewer"),
    "minimal": ("manager",),
}

#: First-name pool for auto-named developers (surname = the tech).
DEV_NAME_POOL: tuple[str, ...] = (
    "Elias",
    "Ada",
    "Linus",
    "Grace",
    "Dennis",
    "Margaret",
    "Alan",
    "Barbara",
    "Ken",
    "Edsger",
    "Radia",
    "Donald",
)


def role_by_slug(slug: str) -> RoleDef:
    try:
        return _BY_SLUG[slug]
    except KeyError:
        raise RoleNotFoundError(
            f"no predefined role {slug!r} (known: {', '.join(_BY_SLUG)})"
        ) from None


def resolve_roles(spec: str) -> list[RoleDef]:
    """Resolve a ``--roles`` spec: a bundle name, or a comma-separated list of slugs."""
    spec = spec.strip()
    if spec in BUNDLES:
        return [role_by_slug(s) for s in BUNDLES[spec]]
    slugs = [s.strip() for s in spec.split(",") if s.strip()]
    return [role_by_slug(s) for s in slugs]


def dev_role(
    tech: str, *, name: str | None = None, seq: int = 0, model: str | None = None
) -> RoleDef:
    """Build a stack-specific developer role on demand.

    If ``name`` is omitted, a first name is taken from :data:`DEV_NAME_POOL` (by ``seq``) and the
    surname is the tech (→ "Elias Dotnet"); the slug is ``<tech>-dev``.
    """
    tech_label = tech.strip()
    surname = tech_label[:1].upper() + tech_label[1:]
    if name:
        full_name = name
    else:
        first = DEV_NAME_POOL[seq % len(DEV_NAME_POOL)]
        full_name = f"{first} {surname}"
    slug = f"{slugify(tech_label)}-dev"
    return RoleDef(
        slug=slug,
        full_name=full_name,
        title=f"{surname} developer",
        description=f"Implements {surname} code following the project's guides and standards.",
        mission=(
            f"Implement assigned tasks in {surname}, following the project's guides, with tests."
        ),
        responsibilities=(
            f"Implement tasks in {surname}",
            "Write tests for changes",
            "Follow the relevant guides; ask the architect when unsure",
        ),
        model=model or "sonnet",
        color="green",
    )
