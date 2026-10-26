"""Skill naming, descriptions, slug vocabularies and origins.

Every skill slug is derived here: the three always-on cross-role skills, the per-item-type
``sq-<type>`` skills, and the question of which of them are template-owned (``system``) versus
authored by the project.
"""

from collections.abc import Mapping
from types import MappingProxyType

from squads._interactions._loader import bundled_type_names
from squads._models import _attributes as attrs
from squads._models._attributes import ORIGIN_PROJECT, ORIGIN_SYSTEM
from squads._models._item import Item
from squads._roles._catalog import PREDEFINED, get_catalog
from squads._workflow._models import ROSTER_SKILL, WorkflowSpec

SQUADS_SKILL = "squads"


#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "greeting"


#: Always-loaded skill for the memory workflow + curation discipline (cross-role, not per-type).
MEMORY_SKILL = "sq-memory"


#: Slug → one-line description for each of the three always-on cross-role skills. A per-type
#: ``sq-<type>`` description is never looked up here — it is generated on the fly by
#: :func:`skill_description`, from the same template :func:`custom_item_skill_description` uses,
#: so a type gaining playbook coverage through a project override (moving it from the "custom,
#: thin skill" bucket to the "rich, playbook-backed" one at render time) needs no entry added
#: here to get a correct description — the two buckets' descriptions were always the same string
#: for the same type name, keyed off the type only, never off playbook content.
SKILL_DESCRIPTIONS: dict[str, str] = {
    SQUADS_SKILL: (
        "How to track work on this project with the squads (`sq`) CLI: create/transition "
        "items, comment, link context. Use whenever you start, hand off, or update work."
    ),
    GREETING_SKILL: (
        "Start of a conversation with a human: detect & register the operator, then greet "
        "them — match their tone, say how you help, and give a quick read of the project. "
        "Use when a person opens a session; skip it when spawned as a subagent for a job."
    ),
    MEMORY_SKILL: (
        "Your role's committed memory notebook and the team bulletin board: check your "
        "index at the start of a run, jot one fact per memory, prune what's stale or wrong, "
        "post/clear board notices, and the memory-vs-board boundary. Use whenever you learn "
        "something worth remembering, or need to announce something to the whole team."
    ),
}


#: Slug -> whether the person at the keyboard is offered each of the three always-on skills,
#: declared beside :data:`SKILL_DESCRIPTIONS`. A release may change a value; a squad's own
#: stored choice is never overwritten by it.
OPERATOR_INVOCABLE_DEFAULTS: Mapping[str, bool] = MappingProxyType(
    {SQUADS_SKILL: False, GREETING_SKILL: False, MEMORY_SKILL: False}
)


#: The one default every per-item-type ``sq-<type>`` skill shares.
ITEM_SKILL_OPERATOR_INVOCABLE = False


def declared_operator_invocable(slug: str, spec: WorkflowSpec) -> bool:
    """The default a skill's bundled definition declares; a skill with no bundled definition
    (:func:`is_system_skill` is false) is invocable."""
    if slug in OPERATOR_INVOCABLE_DEFAULTS:
        return OPERATOR_INVOCABLE_DEFAULTS[slug]
    if is_system_skill(slug, spec):
        return ITEM_SKILL_OPERATOR_INVOCABLE
    return True


def resolve_operator_invocable(
    slug: str, item: Item | None, spec: WorkflowSpec
) -> tuple[bool, bool]:
    """``(value, is_set)``: the squad's stored boolean when *item* carries one, else the
    declared default. Any other stored value resolves as if absent."""
    stored = (
        None if item is None else attrs.flag_attribute(item, attrs.AttributeKey.OPERATOR_INVOCABLE)
    )
    if stored is not None:
        return stored, True
    return declared_operator_invocable(slug, spec), False


def skill_description(slug: str) -> str:
    """Return the canonical description for a bundled or ``sq-<type>`` skill slug.

    The three always-on skills come from :data:`SKILL_DESCRIPTIONS`; any other ``sq-<type>``
    slug gets the generic per-type description computed from its type name — the same template
    :func:`custom_item_skill_description` uses, so this needs no playbook-derived lookup table
    to stay correct for a type a project override newly covers. Falls back to the slug itself
    for anything not shaped like ``sq-<type>`` (should not happen for a real skill slug, but
    avoids ever raising for an unknown one).
    """
    if slug in SKILL_DESCRIPTIONS:
        return SKILL_DESCRIPTIONS[slug]
    if slug.startswith("sq-"):
        return custom_item_skill_description(slug.removeprefix("sq-"))
    return slug


def item_skill_name(item_type: str) -> str:
    return f"sq-{item_type}"


def custom_item_skill_name(type_name: str) -> str:
    """Return the skill slug for a custom (non-built-in) item type."""
    return f"sq-{type_name}"


def item_type_for_skill_slug(slug: str, spec: WorkflowSpec) -> str | None:
    """The non-roster item type whose per-item-type skill is named *slug* under *spec* —
    the inverse of :func:`item_skill_name`, composed over the same declared-type
    enumeration :func:`active_skill_slugs` builds from (``item_skill_name(t) == slug`` for a
    non-roster ``t``). ``None`` when *slug* names no declared type's skill: one of the three
    permanently-system slugs, an author-created skill sharing the ``sq-`` naming convention by
    coincidence, or a dropped/renamed type's now-stale slug.

    This is the emptiness case, not a failure — the one call site resolving a ``playbook``
    source's subject from a skill host's own slug (``squads._views._playbook_subject``) falls
    back to the host's own type rather than treating a miss as a refusal, and this function
    makes no claim about which is which; it only answers the inversion.
    """
    return next(
        (
            t
            for t, ts in spec.items.items()
            if ts.category != "roster" and item_skill_name(t) == slug
        ),
        None,
    )


def custom_item_skill_commands(type_name: str) -> list[str]:
    """Return the standard command list for a custom item type.

    Custom types have no playbook entry, so we emit the generic verb set
    (create, show, list, update, status, ref, comment, body, remove, retype).
    """
    return [
        f'sq create {type_name} "…" --author <slug>',
        f"sq {type_name} <n> show --full --comments",
        f"sq list -t {type_name}",
        f"sq {type_name} <n> update --status <status>",
        f"sq {type_name} <n> status <status>",
        f"sq {type_name} <n> ref add <id> [--kind <kind>]",
        f'sq {type_name} <n> comment --as <slug> -m "…"',
        f'sq {type_name} <n> body -m "…"',
        f"sq {type_name} <n> remove",
        f"sq {type_name} <n> retype <new-type>",
    ]


def custom_item_skill_description(type_name: str) -> str:
    """Return the canonical description for a custom type's skill slug."""
    return (
        f"Working with {type_name} items in this squad: "
        "lifecycle, commands, and role-specific guidance."
    )


def bundled_skill_slugs() -> list[str]:
    """All bundled skill slugs in deterministic lexical order.

    This is the **single shared ordering primitive** consumed by both ``sq init`` seeding and
    the migration.  Any code that allocates SKILL ids must iterate this list so migration and
    fresh-init assign the same relative ordinal to each skill (identical absolute numbers are
    impossible because the global counter may differ).

    Deliberately, unconditionally **bundled-blind** — no ``playbook`` parameter at all, not even
    an optional one a caller could thread the active/merged value into. This is the exact
    property :func:`is_system_skill`'s reclaim logic depends on: a type dropped or renamed via a
    workflow override is filtered OUT of the *merged* playbook by design (coverage must not see
    it as an "extra" entry — see ``_interactions._loader._base_raw_for``), so a caller-supplied
    merged playbook here would make a renamed-away built-in's stale ``sq-<type>`` skill
    invisible to every check built on this list, exactly the "outlives the type it described"
    failure the design note below already warns against. The seeding call site
    (``seed_bundled_skills``) does not need the merged playbook either — a type it excludes
    already produced no body file for ``refresh_managed()`` to seed, so the seeding loop's own
    ``legacy_path.is_file()`` gate is the real filter regardless of what this list enumerates.
    """
    all_slugs = [
        SQUADS_SKILL,
        GREETING_SKILL,
        MEMORY_SKILL,
        *(item_skill_name(t) for t in bundled_type_names()),
    ]
    return sorted(set(all_slugs))


def custom_skill_slugs(spec: WorkflowSpec) -> list[str]:
    """All custom type skill slugs for *spec*, in lexical order.

    Extends the same allocation primitive to custom types: each type declared in the spec
    with no *bundled* playbook entry (the thin-auto-generated-skill boundary — regardless of
    whether it's a built-in or a project-declared type) gets a ``sq-<type>`` skill slug
    allocated in the same lexical-by-slug order so there is no churn of existing SKILL ids.

    Deliberately checked against the bundled playbook, never a
    caller-supplied merged one — see :func:`bundled_skill_slugs`'s docstring for why: a
    project-declared type is never in the bundled document regardless of whether it has
    override coverage, so this enumeration is already correct (and stable) without knowing
    about the override at all. Its generated CONTENT (rich vs. thin) is decided entirely by
    :func:`managed_item_types` at the point that actually needs the merged playbook
    (the backend's per-type skill writer); this function only decides *seeding order*.

    The returned list contains only these types' slugs (not the bundled ones returned by
    :func:`bundled_skill_slugs`).  Callers that need the full merged set should sort
    ``bundled_skill_slugs() + custom_skill_slugs(spec)`` lexically.
    """
    return sorted(
        custom_item_skill_name(ctype)
        for ctype in spec.items
        if ctype not in bundled_type_names() and spec.items[ctype].category != "roster"
    )


def active_skill_slugs(spec: WorkflowSpec) -> frozenset[str]:
    """Every ``sq-<type>`` skill slug *spec* should currently have, plus the three always-on
    cross-role skills — the orphan-detection vocabulary, since a type can be dropped, renamed,
    or re-prefixed: unlike
    ``bundled_skill_slugs() | custom_skill_slugs(spec)`` (each an *allocation-order* primitive
    for ``sq init``/``sq sync`` seeding, deliberately covering every historically-bundled slug
    regardless of the active spec), this is the set that should exist *right now*. A dropped or
    renamed built-in's old ``sq-<type>`` slug is not in it — reusing it for orphan detection
    would keep exempting a stale skill from ever being flagged, silently outliving the type it
    described.

    ``item_skill_name``/``custom_item_skill_name`` are the identical ``f"sq-{type}"`` naming
    scheme either way, so one loop over ``spec.items`` covers both a rich (playbook-backed) and
    a thin (custom) skill — there is no "built-in vs custom" split at the slug-naming layer,
    only at the *content* layer (``_write_item_skills``).
    """
    return frozenset(
        {SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL}
        | {item_skill_name(t) for t, ts in spec.items.items() if ts.category != "roster"}
    )


def is_system_skill(slug: str, spec: WorkflowSpec) -> bool:
    """Whether *slug* names a template-owned skill (bundled or a per-type ``sq-<type>``).

    A pure function of the slug and the active spec — derived, not stored, so a project
    that renames/drops a type re-derives cleanly. Any SKILL slug outside this union is
    author-defined ("custom").

    Deliberately bundled-blind on the built-in half (``bundled_skill_slugs()`` takes no
    *spec*, and no *playbook* either — not even optionally): this is the allocation-order/
    no-hand-editing membership test, not the "is this still on offer right now" test — a
    dropped or renamed built-in's stale skill is still a template-owned file nobody should
    hand-edit, and still stays out of the seeding order's churn. Use
    :func:`orphaned_skill_item_type` for "should this per-type skill still be materialised
    today". No ``playbook`` parameter here at all — passing the *merged* playbook into
    :func:`bundled_skill_slugs` would defeat exactly the bundled-blindness this function
    depends on: a workflow-override-renamed built-in's OLD name is filtered out of the merged
    playbook by design (coverage must not see it as a stray "extra" entry), so a caller-supplied
    merged value here would make the renamed-away slug invisible to reclaim, letting its stale
    file silently outlive the type it described — the one failure mode this check exists to
    prevent.
    """
    return slug in bundled_skill_slugs() or slug in custom_skill_slugs(spec)


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


def skill_origin(slug: str, spec: WorkflowSpec) -> str:
    """``system`` for a bundled or spec-generated skill, else ``project``."""
    return ORIGIN_SYSTEM if is_system_skill(slug, spec) else ORIGIN_PROJECT


def item_origin(item: Item, spec: WorkflowSpec) -> str:
    """The origin a role or skill *item* is classified as, by the one rule every writer uses."""
    if item.type == ROSTER_SKILL:
        return skill_origin(item.slug, spec)
    return role_origin(
        item.slug,
        template=attrs.template(item),
        item_defined=attrs.mission(item) is not None,
    )


def orphaned_skill_item_type(slug: str, spec: WorkflowSpec) -> str | None:
    """The item type a ``sq-<type>`` skill slug used to name, when *spec* no longer declares
    that type at all — ``None`` when *slug* is still current, was never a per-type skill at
    all, or names a type this call has no evidence it was ever generated for.

    The single membership test that decides whether a per-type skill's generated
    pointer/body should still be materialised (see ``ServiceCore._project_roster_item``) and
    whether ``sq check`` should flag a live one. Gated on :func:`is_system_skill` — the
    template-owned membership test — rather than the ``sq-`` prefix alone: the prefix is not
    reserved to squads, so an author-created skill named e.g. ``sq-onboarding`` is a real,
    live skill that happens to share the house naming convention, not the residue of a type
    that used to exist. ``is_system_skill`` stays bundled-blind on its built-in half (a
    dropped or renamed *built-in*'s stale ``sq-<type>`` is still reclaimed — it was always a
    template-owned slug, active spec or not), so that case keeps working exactly as before;
    the trade-off is a dropped *custom* type's skill no longer self-identifies here, since a
    custom type leaving the spec also removes its slug from ``custom_skill_slugs`` and this
    function has no other record that the skill was ever generated rather than authored.

    Pure and reversible by construction: nothing here is stored, so restoring the type to
    *spec* makes this return ``None`` again on the very next call — no separate undo step,
    the same way the type's own drop needed none.
    """
    if slug in active_skill_slugs(spec):
        return None
    if slug in (SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL):
        return None
    if not is_system_skill(slug, spec):
        return None
    return slug.removeprefix("sq-")


assert OPERATOR_INVOCABLE_DEFAULTS.keys() == SKILL_DESCRIPTIONS.keys(), (
    "every always-on skill declares exactly one operator_invocable default"
)
