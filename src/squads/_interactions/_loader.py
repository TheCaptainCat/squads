"""Load and validate the bundled playbook spec.

``load_playbook(catalog)`` is the single entry point.  It reads
``playbook.toml`` via ``importlib.resources`` (offline, no filesystem
assumption), parses with stdlib ``tomllib``, constructs the pydantic models,
runs fail-closed validation against the already-loaded role catalog, and
returns a ``PlaybookSpec``.  A corrupt or invalid playbook raises
``SquadsError``.
"""

import importlib.resources
import tomllib
from typing import Any

from squads._errors import SquadsError
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._models._enums import ItemType
from squads._roles._models import RoleCatalogSpec

#: The DEV sentinel — exempt from role-catalog slug validation.
DEV = "*dev"

#: Work types that must have playbook entries.
_WORK_TYPES: frozenset[ItemType] = frozenset(
    {
        ItemType.EPIC,
        ItemType.FEATURE,
        ItemType.TASK,
        ItemType.BUG,
        ItemType.DECISION,
        ItemType.REVIEW,
        ItemType.GUIDE,
    }
)

#: Meta types that must NOT have playbook entries (deliberately absent).
_META_TYPES: frozenset[ItemType] = frozenset({ItemType.ROLE, ItemType.SKILL, ItemType.OPERATOR})


def load_playbook(catalog: RoleCatalogSpec) -> PlaybookSpec:
    """Read, parse, validate, and return the bundled ``playbook.toml``.

    Takes the already-loaded ``RoleCatalogSpec`` as the slug authority for
    cross-spec referential integrity.  Called once at module level in
    ``__init__.py`` to build the singleton.  Raises ``SquadsError`` on any
    violation.
    """
    try:
        pkg = importlib.resources.files("squads._interactions")
        toml_bytes = (pkg / "playbook.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled playbook.toml: {exc}") from exc

    try:
        raw: dict[str, Any] = tomllib.loads(toml_bytes.decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled playbook.toml: {exc}") from exc

    return _build_spec(raw, catalog)


def _build_spec(raw: dict[str, Any], catalog: RoleCatalogSpec) -> PlaybookSpec:
    types_raw: dict[str, Any] = raw.get("types", {})
    types: dict[ItemType, ItemPlaybookSpec] = {}

    for name, data in types_raw.items():
        item_type = _coerce_item_type(name)
        roles = [_parse_role_guide(r, name, i) for i, r in enumerate(data.get("roles", []))]
        try:
            # Route through model_validate so extra="forbid" fires on unknown keys.
            entry = ItemPlaybookSpec.model_validate({**data, "roles": roles})
        except Exception as exc:
            raise SquadsError(f"Invalid playbook entry for {name!r}: {exc}") from exc
        types[item_type] = entry

    _validate(types, catalog)

    try:
        spec = PlaybookSpec(types=types)
    except Exception as exc:
        raise SquadsError(f"Invalid bundled playbook: {exc}") from exc

    return spec


def _coerce_item_type(name: str) -> ItemType:
    try:
        return ItemType(name)
    except ValueError:
        raise SquadsError(f"playbook.toml: unknown item type key {name!r}") from None


def _parse_role_guide(data: dict[str, Any], type_name: str, idx: int) -> RoleGuideSpec:
    ctx = f"types.{type_name}.roles[{idx}]"
    try:
        # model_validate so extra="forbid" fires on unknown keys (e.g. "doo", "entr").
        return RoleGuideSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid role guide {ctx}: {exc}") from exc


def _check_slugs(
    types: dict[ItemType, ItemPlaybookSpec],
    catalog_slugs: set[str],
    errors: list[str],
) -> None:
    """Cross-spec slug referential integrity (*dev sentinel exempt)."""
    errors.extend(
        f"types.{item_type.value}: role slug {guide.slug!r} not in role catalog"
        for item_type, entry in types.items()
        for guide in entry.roles
        if guide.slug != DEV and guide.slug not in catalog_slugs
    )


def _check_coverage(types: dict[ItemType, ItemPlaybookSpec], errors: list[str]) -> None:
    """Work types required; meta types must be absent."""
    errors.extend(
        f"missing required work-type entry: {wt.value!r}" for wt in _WORK_TYPES if wt not in types
    )
    errors.extend(
        f"meta type {mt.value!r} must not have a playbook entry "
        "(role/skill/operator are managed separately)"
        for mt in _META_TYPES
        if mt in types
    )


def _check_text(types: dict[ItemType, ItemPlaybookSpec], errors: list[str]) -> None:
    """Required text non-empty."""
    for item_type, entry in types.items():
        if not entry.overview.strip():
            errors.append(f"types.{item_type.value}: overview is empty")
        if not entry.lifecycle.strip():
            errors.append(f"types.{item_type.value}: lifecycle is empty")


def _validate(types: dict[ItemType, ItemPlaybookSpec], catalog: RoleCatalogSpec) -> None:
    errors: list[str] = []
    catalog_slugs = {r.slug for r in catalog.roles}
    _check_slugs(types, catalog_slugs, errors)
    _check_coverage(types, errors)
    _check_text(types, errors)
    if errors:
        raise SquadsError("Invalid bundled playbook:\n" + "\n".join(f"  - {e}" for e in errors))
