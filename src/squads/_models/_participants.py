"""The slug grammar, the slugs reserved for authors that are not roles, and the rules that keep
roles and operators in one author namespace."""

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from squads._errors import SquadsError
from squads._models._item import Item

SLUG_PATTERN = r"[a-z0-9][a-z0-9-]*"
SLUG_RE = re.compile(SLUG_PATTERN)

ANONYMOUS_SLUG = "operator"
ANONYMOUS_NAME = "Operator"
SYSTEM_SLUG = "squads"
OPERATOR_SLUG_PREFIX = "op-"
#: The group verbs of ``sq role`` and ``sq skill``: a slug equal to one cannot be addressed by slug.
#: Hand-maintained because the models sit below the CLI; ``tests/meta`` pins both against the
#: registered commands.
ROLE_GROUP_VERBS: frozenset[str] = frozenset({"activate", "catalog", "list"})
SKILL_GROUP_VERBS: frozenset[str] = frozenset({"add"})
OPERATOR_SLUG_RE = re.compile(re.escape(OPERATOR_SLUG_PREFIX) + SLUG_PATTERN)


def is_valid_slug(slug: str) -> bool:
    """Whether ``slug`` is in the grammar a comment header and an ``@mention`` share."""
    return SLUG_RE.fullmatch(slug) is not None


def require_valid_slug(slug: str, *, action: str) -> None:
    """Raise a ``SquadsError`` naming ``action`` when ``slug`` is outside the slug grammar."""
    if not is_valid_slug(slug):
        raise SquadsError(
            f"cannot {action} as {slug!r}: a slug is lowercase letters, digits and hyphens"
        )


def refuse_system_actor(slug: str) -> None:
    """Raise when ``slug`` is the system slug: it authors rename and retype entries only, and no
    comment writer may act as it, whatever the roster holds."""
    if slug.lstrip("@").lower() == SYSTEM_SLUG:
        raise SquadsError(f"cannot act as {slug!r}: that slug is reserved for system entries")


def reserved_role_slug_problem(slug: str) -> str | None:
    """What keeps a role from taking ``slug`` (a reserved name or the operator prefix), or
    ``None`` when the slug is free for a role."""
    slug = slug.lower()
    if slug == ANONYMOUS_SLUG:
        return "is reserved for the anonymous author"
    if slug == SYSTEM_SLUG:
        return "is reserved for system entries"
    if slug.startswith(OPERATOR_SLUG_PREFIX):
        return f"is reserved for operators (the {OPERATOR_SLUG_PREFIX!r} prefix)"
    return None


def reserved_role_slug_reason(slug: str) -> str | None:
    """Why a role may not take ``slug``, or ``None`` when the slug is free for a role."""
    problem = reserved_role_slug_problem(slug)
    return None if problem is None else f"slug {slug.lower()!r} {problem}"


def group_verb_problem(kind: str, slug: str) -> str | None:
    """Why a role or skill may not take ``slug`` because it is a verb of its ``sq`` group, or
    ``None``."""
    verbs = {"role": ROLE_GROUP_VERBS, "skill": SKILL_GROUP_VERBS}.get(kind, frozenset[str]())
    if slug in verbs:
        return f"is a verb of `sq {kind}` and cannot be addressed by slug"
    return None


def operator_slug_problem(slug: str) -> str | None:
    """What is wrong with ``slug`` as an operator's, or ``None`` when it is ``op-`` followed by
    the slug grammar."""
    if not slug.startswith(OPERATOR_SLUG_PREFIX):
        return f"does not start with {OPERATOR_SLUG_PREFIX!r}"
    if OPERATOR_SLUG_RE.fullmatch(slug) is None:
        return f"is not {OPERATOR_SLUG_PREFIX!r} followed by lowercase letters, digits and hyphens"
    return None


def role_slug_problem(slug: str) -> str | None:
    """What is wrong with ``slug`` as a role's, or ``None`` when it is in the grammar and free."""
    if not is_valid_slug(slug):
        return "is not lowercase letters, digits and hyphens"
    return reserved_role_slug_problem(slug)


def operator_slug_suggestion(slug: str) -> str | None:
    """The compliant slug closest to a refused operator ``slug``, or ``None`` when nothing of it
    survives."""
    tail = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    tail = "" if tail == "op" else tail.removeprefix(OPERATOR_SLUG_PREFIX)
    return f"{OPERATOR_SLUG_PREFIX}{tail}" if tail else None


@dataclass(frozen=True)
class SlugBreach:
    """One role or operator whose slug breaks its grammar or is shared inside the author
    namespace: ``problem`` is its own rule broken (``None`` when only shared) and ``held_by``
    the ids of the other entries holding the same slug."""

    item: Item
    kind: str
    slug: str
    problem: str | None
    held_by: tuple[str, ...]

    def text(self, held_by_lead: str) -> str:
        """``role slug 'x' <problem>``, then the other holders after *held_by_lead*."""
        parts = [f"{self.kind} slug {self.slug!r} {self.problem or 'is not unique'}"]
        if self.held_by:
            parts.append(f"{held_by_lead} {', '.join(self.held_by)}")
        return "; ".join(parts)


def roster_slug_breaches(
    roles: Iterable[Item],
    operators: Iterable[Item],
    skills: Iterable[Item] = (),
    *,
    group_verbs: bool = False,
) -> list[SlugBreach]:
    """Every role and operator, live or retired, that breaks its slug grammar or shares its slug
    with another of the two. Skills are outside the author namespace and are looked at only for
    ``group_verbs``, which also reports a role or skill whose slug is a verb of its ``sq`` group."""
    entries = [("role", it) for it in roles] + [("operator", it) for it in operators]
    holders: dict[str, list[Item]] = defaultdict(list)
    for _kind, it in entries:
        holders[it.slug].append(it)
    out: list[SlugBreach] = []
    for kind, it in [*entries, *(("skill", it) for it in skills)]:
        slug = it.slug
        problem = (
            role_slug_problem(slug)
            if kind == "role"
            else operator_slug_problem(slug)
            if kind == "operator"
            else None
        )
        if group_verbs and (verb := group_verb_problem(kind, slug)):
            problem = f"{problem}; {verb}" if problem else verb
        others = (
            tuple(sorted(o.id for o in holders[slug] if o is not it)) if kind != "skill" else ()
        )
        if problem or others:
            out.append(SlugBreach(it, kind, slug, problem, others))
    return out
