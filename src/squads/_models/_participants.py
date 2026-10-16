"""The slug grammar and the slugs reserved for authors that are not roles."""

import re

from squads._errors import SquadsError

SLUG_PATTERN = r"[a-z0-9][a-z0-9-]*"
SLUG_RE = re.compile(SLUG_PATTERN)

ANONYMOUS_SLUG = "operator"
ANONYMOUS_NAME = "Operator"
SYSTEM_SLUG = "squads"
OPERATOR_SLUG_PREFIX = "op-"


def is_valid_slug(slug: str) -> bool:
    """Whether ``slug`` is in the grammar a comment header and an ``@mention`` share."""
    return SLUG_RE.fullmatch(slug) is not None


def require_valid_slug(slug: str, *, action: str) -> None:
    """Raise a ``SquadsError`` naming ``action`` when ``slug`` is outside the slug grammar."""
    if not is_valid_slug(slug):
        raise SquadsError(
            f"cannot {action} as {slug!r}: a slug is lowercase letters, digits and hyphens"
        )


def reserved_role_slug_reason(slug: str) -> str | None:
    """Why a role may not take ``slug``, or ``None`` when the slug is free for a role."""
    slug = slug.lower()
    if slug == ANONYMOUS_SLUG:
        return f"slug {slug!r} is reserved for the anonymous author"
    if slug == SYSTEM_SLUG:
        return f"slug {slug!r} is reserved for system entries"
    if slug.startswith(OPERATOR_SLUG_PREFIX):
        return f"slug {slug!r} is reserved for operators (the {OPERATOR_SLUG_PREFIX!r} prefix)"
    return None
