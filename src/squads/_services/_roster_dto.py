"""Roles, skills and operators projected onto their DTOs, with the names, hints and columns the
squad's configuration and vocabulary decide."""

from collections.abc import Sequence

from squads import _pronouns
from squads import _views as views
from squads._api._dto._display import Column
from squads._api._dto._operators import OperatorRow
from squads._api._dto._roles import DeveloperRow, RoleDisplay, RoleRow
from squads._api._dto._roster import NameDisplay, SeveredRef
from squads._api._dto._skills import SkillRow
from squads._interactions._models import PlaybookSpec
from squads._interactions._skills import (
    is_system_skill,
    orphaned_skill_item_type,
    resolve_operator_invocable,
)
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import Item
from squads._roles._catalog import RoleDef
from squads._roles._loader import ROLES_OVERRIDE_FILENAME
from squads._services._retirement import Severance
from squads._views import ITEM_SKILL_VIEW_NAME, ROLE_DEFINITION_VIEW_NAME, SYSTEM_SKILL_VIEW_NAMES
from squads._workflow import ROSTER_ROLE
from squads._workflow._models import WorkflowSpec

#: The columns of the ``role list`` table; a dotted key reads the row's ``display``.
ROLE_LIST_COLUMNS: tuple[Column, ...] = (
    Column(key="slug", header="Slug"),
    Column(key="display.name", header="Name"),
    Column(key="title", header="Title"),
    Column(key="capabilities", header="Capabilities"),
    Column(key="is_default", header="Default"),
    Column(key="origin", header="Origin"),
    Column(key="display.live", header="Live"),
)

#: The columns of the ``operator list`` table.
OPERATOR_LIST_COLUMNS: tuple[Column, ...] = (
    Column(key="slug", header="Slug"),
    Column(key="display.name", header="Name"),
    Column(key="id", header="ID"),
    Column(key="status", header="Status"),
)

#: The columns of the ``dev list`` table.
DEVELOPER_LIST_COLUMNS: tuple[Column, ...] = (
    Column(key="id", header="ID"),
    Column(key="slug", header="Slug"),
    Column(key="display.name", header="Name"),
    Column(key="tech", header="Tech"),
)


def name_display(name: str, pronouns: str | None, *, enabled: bool) -> NameDisplay:
    """*name* as shown, with *pronouns* when the squad shows them."""
    shown = pronouns if enabled and pronouns else None
    return NameDisplay(name=_pronouns.named(name, pronouns, enabled=enabled).plain, pronouns=shown)


def role_row(item: Item, role: RoleDef, spec: WorkflowSpec, *, pronouns: bool) -> RoleRow:
    """The role *item* as resolved to *role*, as a listing row."""
    shown = name_display(role.full_name, role.pronouns, enabled=pronouns)
    return RoleRow(
        id=item.id,
        slug=role.slug,
        full_name=role.full_name,
        pronouns=role.pronouns,
        title=role.title,
        description=role.description,
        is_default=role.is_default,
        capabilities=list(role.capabilities),
        status=item.status,
        origin=attrs.origin(item),
        display=RoleDisplay(**dict(shown), live=item.status in spec.live_statuses(ROSTER_ROLE)),
    )


def operator_row(item: Item, *, pronouns: bool) -> OperatorRow:
    """The operator *item* as a listing row."""
    own = _pronouns.pronouns(item)
    return OperatorRow(
        id=item.id,
        slug=item.slug,
        full_name=item.title,
        pronouns=own,
        status=item.status,
        display=name_display(item.title, own, enabled=pronouns),
    )


def developer_row(item: Item, role: RoleDef, *, pronouns: bool) -> DeveloperRow:
    """The developer role *item*, resolved to *role* for its pronouns, as a listing row."""
    return DeveloperRow(
        id=item.id,
        slug=item.slug,
        full_name=item.title,
        pronouns=role.pronouns,
        tech=attrs.tech(item),
        display=name_display(item.title, role.pronouns, enabled=pronouns),
    )


def skill_row(item: Item, spec: WorkflowSpec) -> SkillRow:
    """The skill *item* as a row."""
    invocable, invocable_set = resolve_operator_invocable(item.slug, item, spec)
    return SkillRow(
        id=item.id,
        slug=item.slug,
        title=item.title,
        status=item.status,
        description=item.description,
        when_to_use=attrs.string_attribute(item, AttributeKey.WHEN_TO_USE) or "",
        allowed_tools=attrs.string_attribute(item, AttributeKey.ALLOWED_TOOLS) or "",
        operator_invocable=invocable,
        operator_invocable_set=invocable_set,
        path=item.path,
        origin=attrs.origin(item),
    )


def severed_refs(severed: Sequence[Severance]) -> list[SeveredRef]:
    """The refs a retirement removed."""
    return [SeveredRef(referrer=s.referrer, target=s.target, kind=s.kind) for s in severed]


def role_empty_body_hint(hint_state: views.EmptyBodyHintState, slug: str) -> str:
    """The empty-body hint of ``sq role <slug> show`` for *hint_state*: the remedy follows the
    view's state, and ``sq sync`` is named only where it fills an empty body from its tag."""
    name = ROLE_DEFINITION_VIEW_NAME
    if hint_state == "disabled":
        return f"(disabled — `sq role {slug} view add {name}` re-enables it)"
    if hint_state == "declared":
        return (
            "(empty — run `sq sync`; if it stays empty, declare the definition in "
            f"`{ROLES_OVERRIDE_FILENAME}`, or `.overrides/roles/<slug>.toml`, or run "
            f"`sq role {slug} view add {name}`)"
        )
    return (
        f"(empty — the view {name!r} is not declared in this project's spec, so `sq sync` "
        "cannot populate it; declare it in `.overrides/workflow.toml` to restore the "
        f'generated definition — or write the body with `sq role {slug} body -m "…"` and, '
        f"if it still carries this tag from before the view was dropped, disable the tag with "
        f"`sq role {slug} view disable {name}`)"
    )


def change_role_hint(slug: str, item: Item | None, resolved: bool) -> str:
    """How to change a role's definition: update a role that defines itself, scaffold an override
    for a role whose base resolves, say what is missing for any other."""
    if item is not None and attrs.mission(item) is not None:
        return f"To change its definition: `sq role {slug} update --mission …` (or --file)."
    if resolved:
        return (
            "To change its mission or responsibilities: "
            f"`sq override scaffold --role {slug}`, edit the file, then `sq sync`. "
            f"To change its model: `sq role {slug} update --model …`."
        )
    return (
        "Nothing backs its definition: restore the catalog entry or template it came from, or "
        f"make it define itself with `sq role {slug} update --job-title … --desc … --mission …`."
    )


def skill_empty_body_hint(
    slug: str, spec: WorkflowSpec, playbook: PlaybookSpec, *, view_disabled: bool
) -> str:
    """The empty-body hint of ``sq skill <slug> show``. A system skill's body is generated, and
    empty for one of three reasons: the item type it documents is gone, its view is not declared,
    or ``sq sync`` has not filled it. A custom skill is empty because nobody wrote it."""
    system = is_system_skill(slug, spec)
    dropped_type = orphaned_skill_item_type(slug, spec) if system else None
    view_name = SYSTEM_SKILL_VIEW_NAMES.get(slug) or (ITEM_SKILL_VIEW_NAME if system else None)
    if dropped_type is not None:
        return (
            f"(no definition — the item type {dropped_type!r} this skill described is no "
            "longer declared; restore the type, or retire this skill)"
        )
    if not system or view_name is None:
        return f'(empty — write it with `sq skill {slug} body -m "…"`)'
    hint_state = views.empty_body_hint_state(view_name, spec, disabled=view_disabled)
    if hint_state == "disabled":
        return f"(disabled — `sq skill {slug} view add {view_name}` re-enables it)"
    if hint_state == "view_undeclared":
        return (
            f"(empty — the view {view_name!r} this skill renders is not declared in this "
            "project's spec, so `sq sync` cannot populate it; declare it to restore the "
            "generated definition — or, if this skill's body still carries this tag from "
            f"before it was dropped, disable it with `sq skill {slug} view disable "
            f"{view_name}`)"
        )
    surface = views.skill_authoring_surface(view_name, slug, spec, playbook)
    return (
        "(empty — run `sq sync`; if it stays empty, its content's real authoring "
        f"surface is {surface}; author it there instead — or run "
        f"`sq skill {slug} view add {view_name}`)"
    )


def skill_view_name(slug: str, spec: WorkflowSpec) -> str | None:
    """The view a system skill's body renders, ``None`` for a custom skill."""
    if not is_system_skill(slug, spec):
        return None
    return SYSTEM_SKILL_VIEW_NAMES.get(slug) or ITEM_SKILL_VIEW_NAME
