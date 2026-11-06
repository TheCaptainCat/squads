"""The connector table: a literal ``(name, version)`` to connector mapping with no registration side
effect. A connector class is imported only when a fetch needs it, so reading the table, as the
sources loader does to validate names, loads no HTTP code."""

from dataclasses import dataclass
from importlib import import_module

from squads._sources._connector import (
    CATEGORY_SIDE,
    LABELS,
    STATE_SIDE,
    STATUS_SIDE,
    TYPE,
    Connector,
)


@dataclass(frozen=True)
class ConnectorEntry:
    """Where a connector version lives and the converter its sources default to."""

    module: str
    cls: str
    default_converter: str
    #: The sides of an issue a map reads a value from, besides its labels.
    sides: tuple[str, ...]
    #: The keys a source of this version names its scope with; a source names exactly one.
    scope_keys: tuple[str, ...]
    #: The sides the status map reads, in the order they are checked: the first that maps one of
    #: an issue's values decides.
    status_sides: tuple[str, ...]
    #: The values a status side with a fixed set of them accepts, by side.
    status_enums: tuple[tuple[str, tuple[str, ...]], ...]


#: The issue sides each tracker API exposes: tracker API names.
_TYPE_SIDES = (LABELS, TYPE)
_JIRA_SIDES = ("labels", "type", "priority")
_JIRA_SCOPE = ("jql",)
_STATE_STATUS_SIDES = (STATE_SIDE, LABELS)
_JIRA_STATUS_SIDES = (STATUS_SIDE, CATEGORY_SIDE, LABELS)
_JIRA_STATUS_ENUMS = ((CATEGORY_SIDE, ("new", "indeterminate", "done")),)

CONNECTORS: dict[tuple[str, str], ConnectorEntry] = {
    ("gitlab", "v4"): ConnectorEntry(
        "squads._sources._gitlab",
        "GitLabConnector",
        "gitlab-md",
        _TYPE_SIDES,
        ("project", "group"),
        _STATE_STATUS_SIDES,
        ((STATE_SIDE, ("opened", "closed")),),
    ),
    ("github", "v3"): ConnectorEntry(
        "squads._sources._github",
        "GitHubConnector",
        "github-md",
        _TYPE_SIDES,
        ("repository",),
        _STATE_STATUS_SIDES,
        ((STATE_SIDE, ("open", "closed")),),
    ),
    ("jira", "cloud-v3"): ConnectorEntry(
        "squads._sources._jira",
        "JiraCloudConnector",
        "adf",
        _JIRA_SIDES,
        _JIRA_SCOPE,
        _JIRA_STATUS_SIDES,
        _JIRA_STATUS_ENUMS,
    ),
    ("jira", "dc-v2"): ConnectorEntry(
        "squads._sources._jira",
        "JiraDcConnector",
        "jira-wiki",
        _JIRA_SIDES,
        _JIRA_SCOPE,
        _JIRA_STATUS_SIDES,
        _JIRA_STATUS_ENUMS,
    ),
}


def load_connector(name: str, version: str) -> type[Connector] | None:
    """The connector class of ``(name, version)``, imported now, or ``None``."""
    entry = CONNECTORS.get((name, version))
    if entry is None:
        return None
    loaded: type[Connector] = getattr(import_module(entry.module), entry.cls)
    return loaded
