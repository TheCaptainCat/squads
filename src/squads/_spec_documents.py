"""The squad's spec documents, resolved together: the workflow spec, the playbook and the role
catalog, each built from one read of its packaged file and of its project override.

:func:`resolve_documents` is the one place that chooses them; the service it feeds keeps the
documents and the override text (:class:`~squads._specload.OverrideFiles`) they were read from.
"""

from dataclasses import dataclass
from pathlib import Path

from squads._errors import PlaybookConfigError, SquadsError
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME, load_playbook
from squads._interactions._models import PlaybookSpec
from squads._interactions._playbook import get_playbook_spec
from squads._roles._catalog import get_catalog
from squads._roles._loader import ROLES_OVERRIDE_FILENAME, load_role_catalog
from squads._roles._models import CatalogSource, RoleCatalogSpec
from squads._specload import Lazy, OverrideFiles, override_present
from squads._workflow import _loader as workflow_loader
from squads._workflow import bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME
from squads._workflow._models import WorkflowSpec


@dataclass(frozen=True)
class SpecDocuments:
    """The documents one service holds; the role catalog is read on first use, then kept."""

    workflow: WorkflowSpec
    playbook: PlaybookSpec
    catalog: CatalogSource
    files: OverrideFiles


@dataclass(frozen=True)
class SpecSources:
    """The documents of one squad that more than one attempt to build a service may need, each
    read on first use and then kept: the squad's workflow spec and its role catalog."""

    workflow: Lazy[WorkflowSpec]
    catalog: Lazy[RoleCatalogSpec]
    files: OverrideFiles


def spec_sources(squad_dir: Path) -> SpecSources:
    """Fresh, unread :class:`SpecSources` for *squad_dir*."""
    files = OverrideFiles()
    return SpecSources(
        workflow=Lazy(lambda: resolve_workflow(squad_dir, files)),
        catalog=Lazy(lambda: resolve_catalog(squad_dir, files)),
        files=files,
    )


def resolve_workflow(squad_dir: Path, files: OverrideFiles | None = None) -> WorkflowSpec:
    """The squad's workflow spec, without the index check: the bundled one unless the project
    overrides it."""
    if not override_present(squad_dir / WORKFLOW_OVERRIDE_FILENAME):
        return bundled_spec()
    return workflow_loader.load_workflow_spec(squad_dir, files)


def resolve_catalog(squad_dir: Path, files: OverrideFiles | None = None) -> RoleCatalogSpec:
    """The squad's role catalog: the bundled one unless the project overrides it."""
    if not override_present(squad_dir / ROLES_OVERRIDE_FILENAME):
        return get_catalog()
    return load_role_catalog(squad_dir, files)


def resolve_playbook(
    spec: WorkflowSpec,
    squad_dir: Path,
    files: OverrideFiles | None = None,
) -> PlaybookSpec:
    """The merged playbook for *spec*, raising :class:`PlaybookConfigError` when it will not load.

    The bundled playbook is returned as it is only when *spec* is the bundled spec and the
    squad has no playbook override, since coverage is checked against *spec*.
    """
    if spec is bundled_spec() and not override_present(squad_dir / PLAYBOOK_OVERRIDE_FILENAME):
        return get_playbook_spec()
    try:
        return load_playbook(spec=spec, squad_dir=squad_dir, files=files)
    except SquadsError as exc:
        raise PlaybookConfigError(str(exc)) from exc


def resolve_documents(
    squad_dir: Path,
    sources: SpecSources,
    *,
    workflow: WorkflowSpec | None = None,
    bundled_playbook: bool = False,
) -> SpecDocuments:
    """Resolve the documents for *squad_dir*: the given *workflow* spec or the squad's from
    *sources*, the squad's playbook or (with *bundled_playbook*) the bundled one, and the lazy
    catalog from *sources*."""
    spec = workflow if workflow is not None else sources.workflow()
    playbook = (
        get_playbook_spec()
        if bundled_playbook
        else resolve_playbook(spec, squad_dir, sources.files)
    )
    return SpecDocuments(
        workflow=spec, playbook=playbook, catalog=sources.catalog, files=sources.files
    )
