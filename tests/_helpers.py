"""Plain helpers shared across the tests: service construction, roles, item creation."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from squads._backends._base import AgentBackend
    from squads._interactions._models import PlaybookSpec
    from squads._paths import SquadPaths
    from squads._roles._models import CatalogSource
    from squads._services._service import Service
    from squads._workflow._models import WorkflowSpec

#: Author given to an item whose creation is setup, not the subject: a slug every fixture squad has.
DEFAULT_TEST_AUTHOR = "manager"


def squad_tree(root: Path) -> dict[str, str]:
    """Every file under *root* (the git directory aside) keyed by relative path, valued by hash."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


async def create_item(svc: Any, item_type: str, title: str, **kwargs: Any) -> Any:
    """`svc.create()` defaulting the author, for setup that has no opinion about attribution."""
    kwargs.setdefault("author", DEFAULT_TEST_AUTHOR)
    return await svc.create(item_type, title, **kwargs)


def catalog_of(squad_dir: Path | None) -> CatalogSource:
    """The role catalog source reading *squad_dir*'s roles override per call (bundled for None)."""
    from squads._roles._catalog import get_catalog
    from squads._roles._loader import load_role_catalog

    if squad_dir is None:
        return get_catalog
    return lambda: load_role_catalog(squad_dir)


def role_of(slug: str, *capabilities: str) -> Any:
    """A resolved role for *slug*; a `-dev` slug holds `dev` unless told otherwise."""
    from squads._roles._projection import RoleView

    held = capabilities or (("dev",) if slug.endswith("-dev") else ())
    return RoleView(slug=slug, full_name=slug, title=slug, is_default=False, capabilities=held)


def make_service(
    paths: SquadPaths,
    spec: WorkflowSpec | None = None,
    playbook: PlaybookSpec | None = None,
    backends: Callable[[], list[AgentBackend]] | None = None,
) -> Service:
    """A `Service` over *paths* with the bundled spec and playbook unless one is given."""
    from squads._interactions._playbook import get_playbook_spec
    from squads._services._service import build_service
    from squads._spec_documents import SpecDocuments
    from squads._specload import OverrideFiles
    from squads._workflow import bundled_spec

    return build_service(
        paths,
        SpecDocuments(
            workflow=spec if spec is not None else bundled_spec(),
            playbook=playbook if playbook is not None else get_playbook_spec(),
            catalog=catalog_of(paths.squad_dir),
            files=OverrideFiles(),
        ),
        backends,
    )
