"""Load and validate the bundled playbook spec.

``load_playbook(catalog)`` is the single entry point.  It reads
``playbook.toml`` via ``importlib.resources`` (offline, no filesystem
assumption), parses with stdlib ``tomllib``, constructs the pydantic models,
runs fail-closed validation against the already-loaded role catalog and the
loaded ``WorkflowSpec``, and returns a ``PlaybookSpec``.  A corrupt or invalid
playbook raises ``SquadsError``.
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
from squads._roles._models import RoleCatalogSpec
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec

#: The DEV sentinel — exempt from role-catalog slug validation.
DEV = "*dev"


def load_playbook(catalog: RoleCatalogSpec, spec: WorkflowSpec | None = None) -> PlaybookSpec:
    """Read, parse, validate, and return the bundled ``playbook.toml``.

    Takes the already-loaded ``RoleCatalogSpec`` as the slug authority for cross-spec
    referential integrity, and a ``WorkflowSpec`` (the bundled spec by default) as the
    type authority: every one of *spec*'s ``non_roster_types()`` must have a playbook entry,
    and no entry may name anything else (a roster type or unknown name). This replaces the
    the old per-name-enum coercion and the hardcoded ``_WORK_TYPES``/``_ROSTER_TYPES``
    floors — the loaded ``WorkflowSpec`` is now the sole authority on which types exist.
    Called once at module level in ``__init__.py`` to build the singleton. Raises
    ``SquadsError`` on any violation.
    """
    if spec is None:
        spec = bundled_spec()
    try:
        pkg = importlib.resources.files("squads._interactions")
        toml_bytes = (pkg / "playbook.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled playbook.toml: {exc}") from exc

    try:
        raw: dict[str, Any] = tomllib.loads(toml_bytes.decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled playbook.toml: {exc}") from exc

    return _build_spec(raw, catalog, spec)


def _build_spec(raw: dict[str, Any], catalog: RoleCatalogSpec, spec: WorkflowSpec) -> PlaybookSpec:
    types_raw: dict[str, Any] = raw.get("types", {})
    types: dict[str, ItemPlaybookSpec] = {}

    for name, data in types_raw.items():
        roles = [_parse_role_guide(r, name, i) for i, r in enumerate(data.get("roles", []))]
        try:
            # Route through model_validate so extra="forbid" fires on unknown keys.
            entry = ItemPlaybookSpec.model_validate({**data, "roles": roles})
        except Exception as exc:
            raise SquadsError(f"Invalid playbook entry for {name!r}: {exc}") from exc
        types[name] = entry

    _validate(types, catalog, spec)

    try:
        pb_spec = PlaybookSpec(types=types)
    except Exception as exc:
        raise SquadsError(f"Invalid bundled playbook: {exc}") from exc

    return pb_spec


def _parse_role_guide(data: dict[str, Any], type_name: str, idx: int) -> RoleGuideSpec:
    ctx = f"types.{type_name}.roles[{idx}]"
    try:
        # model_validate so extra="forbid" fires on unknown keys (e.g. "doo", "entr").
        return RoleGuideSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid role guide {ctx}: {exc}") from exc


def _check_slugs(
    types: dict[str, ItemPlaybookSpec],
    catalog_slugs: set[str],
    errors: list[str],
) -> None:
    """Cross-spec slug referential integrity (*dev sentinel exempt)."""
    errors.extend(
        f"types.{item_type}: role slug {guide.slug!r} not in role catalog"
        for item_type, entry in types.items()
        for guide in entry.roles
        if guide.slug != DEV and guide.slug not in catalog_slugs
    )


def _check_coverage(
    types: dict[str, ItemPlaybookSpec], spec: WorkflowSpec, errors: list[str]
) -> None:
    """Every non-roster type in *spec* needs a playbook entry; nothing else may have one.

    Replaces the fixed ``_WORK_TYPES``/``_ROSTER_TYPES`` floors: *spec* (the loaded
    ``WorkflowSpec``) is the sole authority on which types exist and which are roster, so
    bundled-playbook coverage tracks whatever the bundled workflow spec declares instead
    of a hand-maintained duplicate list.
    """
    creatable_types = spec.non_roster_types()
    errors.extend(
        f"missing required work-type entry: {wt!r}"
        for wt in sorted(creatable_types)
        if wt not in types
    )
    errors.extend(
        f"types.{name}: not a declared non-roster type in the workflow spec "
        "(role/skill/operator are managed separately; unknown type names are rejected)"
        for name in types
        if name not in creatable_types
    )


def _check_text(types: dict[str, ItemPlaybookSpec], errors: list[str]) -> None:
    """Required text non-empty."""
    for item_type, entry in types.items():
        if not entry.overview.strip():
            errors.append(f"types.{item_type}: overview is empty")
        if not entry.lifecycle.strip():
            errors.append(f"types.{item_type}: lifecycle is empty")


def _validate(
    types: dict[str, ItemPlaybookSpec], catalog: RoleCatalogSpec, spec: WorkflowSpec
) -> None:
    errors: list[str] = []
    catalog_slugs = {r.slug for r in catalog.roles}
    _check_slugs(types, catalog_slugs, errors)
    _check_coverage(types, spec, errors)
    _check_text(types, errors)
    if errors:
        raise SquadsError("Invalid bundled playbook:\n" + "\n".join(f"  - {e}" for e in errors))
