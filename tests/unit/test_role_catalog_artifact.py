"""The bundled role catalog is a tested artifact: it loads without error, every declared
RoleSpec field is covered by the pinned golden, and the loaded shape is byte-identical to
that golden (a human-reviewed reference render — see tests/CONVENTIONS.md's golden
protocol). Packaging (roles.toml ships in the wheel) lives in
tests/meta/test_bundled_toml_packaging.py, deliberately consolidated into one
parametrized test rather than a near-duplicate per asset.
"""

import json
from pathlib import Path

from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleCatalogSpec, RoleSpec

GOLDEN_PATH = Path(__file__).parents[1] / "goldens" / "role_catalog_spec.json"


def _catalog() -> RoleCatalogSpec:
    return load_role_catalog()


def _golden() -> dict[str, object]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_catalog_loads_without_error() -> None:
    catalog = _catalog()
    assert isinstance(catalog, RoleCatalogSpec)
    assert len(catalog.roles) == 8


def test_golden_covers_every_declared_rolespec_field() -> None:
    """If a field is added to RoleSpec without updating the golden, this fails immediately."""
    golden = _golden()
    snapshot_keys = set(golden["roles"][0].keys())  # type: ignore[index]
    assert snapshot_keys == set(RoleSpec.model_fields)


def test_loaded_catalog_is_byte_identical_to_the_golden() -> None:
    actual = _catalog().model_dump(mode="json")
    assert actual == _golden()


def test_default_role_is_manager() -> None:
    catalog = _catalog()
    defaults = [r.slug for r in catalog.roles if r.is_default]
    assert defaults == ["manager"]


def test_exactly_manager_and_tech_lead_can_spawn() -> None:
    catalog = _catalog()
    spawners = {r.slug for r in catalog.roles if r.can_spawn}
    assert spawners == {"manager", "tech-lead"}
