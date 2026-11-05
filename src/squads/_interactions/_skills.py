"""Skill naming, descriptions, slug vocabularies and origins.

Every skill slug is derived here: the three always-on cross-role skills, the per-role
``sq-role-<slug>`` skills, and the question of which skills are template-owned (``system``)
versus authored by the project.
"""

from collections.abc import Mapping
from types import MappingProxyType

from squads._models import ORIGIN_PROJECT, ORIGIN_SYSTEM, AttributeKey, Item, attrs
from squads._roles import PREDEFINED, get_catalog
from squads._workflow import ROSTER_SKILL

SQUADS_SKILL = "sq-how-to"


#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "sq-greeting"


#: Always-loaded skill for the memory workflow + curation discipline (cross-role, not per-type).
MEMORY_SKILL = "sq-memory"


#: What a role skill's name starts with: ``sq-role-<role slug>``.
ROLE_SKILL_PREFIX = "sq-role-"


def role_skill_name(role_slug: str) -> str:
    """The name of the skill that renders role *role_slug*."""
    return f"{ROLE_SKILL_PREFIX}{role_slug}"


def role_slug_of_skill(skill_slug: str) -> str | None:
    """The role slug a skill named ``sq-role-<role slug>`` renders, ``None`` for any other name."""
    if skill_slug.startswith(ROLE_SKILL_PREFIX) and len(skill_slug) > len(ROLE_SKILL_PREFIX):
        return skill_slug.removeprefix(ROLE_SKILL_PREFIX)
    return None


#: Slug to one-line description for the three always-on cross-role skills.
SKILL_DESCRIPTIONS: dict[str, str] = {
    SQUADS_SKILL: (
        "How to track work on this project with the squads (`sq`) CLI: addressing items, "
        "bodies and comments, common commands, and the `sq docs` topics to read next. Use "
        "whenever you start, hand off, or update work."
    ),
    GREETING_SKILL: (
        "For the main session only, never a subagent: identify the operator, adopt a role, "
        "read its role, queue, mentions, board and memory, then greet. Use when a person "
        "opens a session."
    ),
    MEMORY_SKILL: (
        "Your role's committed memory notebook and the team bulletin board: jot one fact per "
        "memory, prune what's stale or wrong, post/clear board notices, and the "
        "memory-vs-board boundary. Use whenever you learn something worth remembering, or "
        "need to announce something to the whole team."
    ),
}


#: Slug -> whether the person at the keyboard is offered each of the three always-on skills,
#: declared beside :data:`SKILL_DESCRIPTIONS`. A release may change a value; a squad's own
#: stored choice is never overwritten by it.
OPERATOR_INVOCABLE_DEFAULTS: Mapping[str, bool] = MappingProxyType(
    {SQUADS_SKILL: False, GREETING_SKILL: False, MEMORY_SKILL: False}
)


def declared_operator_invocable(slug: str) -> bool:
    """The default a skill's bundled definition declares; a skill with no bundled definition
    (:func:`is_system_skill` is false) is invocable."""
    return OPERATOR_INVOCABLE_DEFAULTS.get(slug, True)


def resolve_operator_invocable(slug: str, item: Item | None) -> tuple[bool, bool]:
    """``(value, is_set)``: the squad's stored boolean when *item* carries one, else the
    declared default. Any other stored value resolves as if absent."""
    stored = None if item is None else attrs.flag_attribute(item, AttributeKey.OPERATOR_INVOCABLE)
    if stored is not None:
        return stored, True
    return declared_operator_invocable(slug), False


def skill_description(slug: str) -> str:
    """The canonical description of an always-on skill slug; any other slug returns itself,
    never raising."""
    return SKILL_DESCRIPTIONS.get(slug, slug)


def bundled_skill_slugs() -> list[str]:
    """The three always-on skill slugs in deterministic lexical order.

    The shared ordering primitive of ``sq init`` seeding and the migration: any code allocating
    SKILL ids iterates this list, so both assign the same relative ordinals (absolute numbers
    may differ with the global counter).
    """
    return sorted({SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL})


def is_system_skill(slug: str) -> bool:
    """Whether *slug* names a template-owned skill, one of the three always-on skills.

    A pure function of the slug. Any other SKILL slug is author-defined, a leftover ``sq-<type>``
    skill item included.
    """
    return slug in bundled_skill_slugs()


def role_origin(slug: str, *, template: str | None = None, item_defined: bool = False) -> str:
    """``system`` when the role's base is a bundled catalog entry or a bundled template (even one
    the project overrides), else ``project``. Reads the catalog as packaged, never the squad's
    resolved one. *template* is the template name the role stores; *item_defined* is a role
    that stores its own definition."""
    if template is not None:
        return ORIGIN_SYSTEM if template in get_catalog().templates else ORIGIN_PROJECT
    if item_defined:
        return ORIGIN_PROJECT
    return ORIGIN_SYSTEM if any(r.slug == slug for r in PREDEFINED) else ORIGIN_PROJECT


def skill_origin(slug: str) -> str:
    """``system`` for a bundled skill, else ``project``."""
    return ORIGIN_SYSTEM if is_system_skill(slug) else ORIGIN_PROJECT


def item_origin(item: Item) -> str:
    """The origin a role or skill *item* is classified as, by the one rule every writer uses."""
    if item.type == ROSTER_SKILL:
        return skill_origin(item.slug)
    return role_origin(
        item.slug,
        template=attrs.template(item),
        item_defined=attrs.mission(item) is not None,
    )


assert OPERATOR_INVOCABLE_DEFAULTS.keys() == SKILL_DESCRIPTIONS.keys(), (
    "every always-on skill declares exactly one operator_invocable default"
)
