"""The role catalog as a listing: its rows and columns, and the bundled catalog's own listing,
which answers outside a squad."""

from collections.abc import Sequence

from squads._api._dto._display import Column
from squads._api._dto._roles import RoleCatalog, RoleCatalogRow
from squads._models._attributes import ORIGIN_SYSTEM
from squads._roles._catalog import RoleDef, get_catalog
from squads._roles._models import RoleSpec

#: The columns of the ``role catalog`` table.
CATALOG_COLUMNS: tuple[Column, ...] = (
    Column(key="slug", header="Slug"),
    Column(key="full_name", header="Name"),
    Column(key="title", header="Title"),
    Column(key="is_default", header="Default"),
    Column(key="origin", header="Origin"),
)


def catalog_row(
    role: RoleDef | RoleSpec,
    *,
    is_default: bool,
    origin: str,
    default_role: str | None,
    source: str,
) -> RoleCatalogRow:
    """*role* as a catalog row; *default_role* is the holder *source* names."""
    return RoleCatalogRow(
        slug=role.slug,
        full_name=role.full_name,
        title=role.title,
        is_default=is_default,
        origin=origin,
        capabilities=list(dict.fromkeys(role.capabilities)),
        default_role=default_role,
        default_role_source=source,
    )


def catalog_listing(rows: Sequence[RoleCatalogRow]) -> RoleCatalog:
    """*rows* with the catalog's columns."""
    return RoleCatalog(items=list(rows), columns=list(CATALOG_COLUMNS))


def bundled_catalog() -> RoleCatalog:
    """The packaged catalog, its own default marked: every role in it is bundled."""
    roles = get_catalog().roles
    default = next((r.slug for r in roles if r.is_default), None)
    return catalog_listing(
        [
            catalog_row(
                r,
                is_default=r.is_default,
                origin=ORIGIN_SYSTEM,
                default_role=default,
                source="catalog",
            )
            for r in roles
        ]
    )
