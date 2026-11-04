"""The connector table: a literal ``(name, version)`` to connector mapping with no registration side
effect. A connector class is imported only when a fetch needs it, so reading the table, as the
sources loader does to validate names, loads no HTTP code."""

from dataclasses import dataclass
from importlib import import_module

from squads._sources._connector import LABELS, TYPE, Connector


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


#: The issue sides each tracker API exposes: tracker API names.
_TYPE_SIDES = (LABELS, TYPE)
_JIRA_SIDES = ("labels", "type", "priority")
_JIRA_SCOPE = ("jql",)

CONNECTORS: dict[tuple[str, str], ConnectorEntry] = {
    ("gitlab", "v4"): ConnectorEntry(
        "squads._sources._gitlab", "GitLabConnector", "gitlab-md", _TYPE_SIDES, ("project", "group")
    ),
    ("github", "v3"): ConnectorEntry(
        "squads._sources._github", "GitHubConnector", "github-md", _TYPE_SIDES, ("repository",)
    ),
    ("jira", "cloud-v3"): ConnectorEntry(
        "squads._sources._jira", "JiraCloudConnector", "adf", _JIRA_SIDES, _JIRA_SCOPE
    ),
    ("jira", "dc-v2"): ConnectorEntry(
        "squads._sources._jira", "JiraDcConnector", "jira-wiki", _JIRA_SIDES, _JIRA_SCOPE
    ),
}


def load_connector(name: str, version: str) -> type[Connector] | None:
    """The connector class of ``(name, version)``, imported now, or ``None``."""
    entry = CONNECTORS.get((name, version))
    if entry is None:
        return None
    loaded: type[Connector] = getattr(import_module(entry.module), entry.cls)
    return loaded
