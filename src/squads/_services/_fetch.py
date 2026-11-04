"""The fetch phase every command that reads a tracker goes through: the pull, ``show --refresh``,
``relink`` and handle resolution. It refuses a disabled source and runs the blocking connector
calls on a worker thread."""

from collections.abc import Callable, Mapping

from squads import _aio as aio
from squads._errors import SquadsError
from squads._sources import _credentials as credentials
from squads._sources._connector import Connector, FetchedIssue, Issue, SourceFetch
from squads._sources._http import NotFoundError
from squads._sources._probes import ACCESS, Expected, missing_credential, run_probes
from squads._sources._registry import load_connector
from squads._sources._spec import SourceSpec, SourcesSpec


def require_enabled(source: SourceSpec) -> None:
    """Refuse a source that is paused: a disabled source fetches nothing into the squad."""
    if not source.enabled:
        raise SquadsError(
            f"source {source.name!r} is disabled (`enabled = false` in its sources.toml table); "
            "enable it to fetch from it"
        )


def require_credential(source: SourceSpec) -> dict[str, str]:
    """The stored credential of *source*; refused naming the command that stores one."""
    credential = credentials.read_entry(source.base_url)
    if credential is None:
        raise SquadsError(missing_credential(source.name).message())
    return credential


def connector_class(source: SourceSpec) -> type[Connector]:
    """The connector class *source* names."""
    cls = load_connector(source.connector, source.version)
    if cls is None:
        raise SquadsError(
            f"source {source.name!r} names connector {source.connector}@{source.version}, "
            "which is not registered"
        )
    return cls


def connector_for(source: SourceSpec, credential: Mapping[str, str]) -> Connector:
    """The connector class *source* names, built for its base URL, filter and *credential*."""
    return connector_class(source)(source.base_url, source.filter, credential)


async def open_connector(source: SourceSpec, credential: Mapping[str, str]) -> Connector:
    """The connector for *source* once its access probes pass: a blocking failure stops the
    command here, with the line ``sq source check`` prints, before anything is fetched."""
    require_enabled(source)
    connector = connector_for(source, credential)
    expected = Expected(source.name, source.maps)
    results = await aio.to_thread(
        lambda: run_probes(lambda family: connector.probes(family, expected), (ACCESS,))
    )
    for result in results:
        if result.blocking:
            raise SquadsError(result.message())
    return connector


def _with_details(connector: Connector, issue: Issue) -> FetchedIssue | None:
    """*issue* with its comments and links, or ``None`` when the tracker stops returning it
    between the listing and this request."""
    try:
        return FetchedIssue(issue, tuple(connector.comments(issue)), tuple(connector.links(issue)))
    except NotFoundError:
        return None


def _fetch(
    connector: Connector,
    stored: Mapping[str, frozenset[tuple[str, str]]],
    linked: Mapping[str, str],
) -> SourceFetch:
    listing = connector.listing()
    listed = frozenset(issue.id for issue in listing)
    wanted = [
        issue
        for issue in listing
        if issue.id not in stored
        or stored[issue.id] != frozenset({(issue.updated_at, issue.state)})
    ]
    found: dict[str, FetchedIssue | None] = {}
    changed: list[FetchedIssue] = []
    skipped: list[str] = []
    for issue in wanted:
        details = _with_details(connector, issue)
        if details is not None:
            changed.append(details)
        elif issue.id in stored and connector.issue(issue.id, issue.key) is None:
            found[issue.id] = None
        else:
            skipped.append(
                f"{issue.key}: skipped, the tracker stopped returning it while it was read"
            )
    for issue_id in sorted(set(linked) - listed):
        issue = connector.issue(issue_id, linked[issue_id])
        found[issue_id] = None if issue is None else _with_details(connector, issue)
    return SourceFetch(tuple(changed), len(listing) - len(wanted), listed, found, tuple(skipped))


async def fetch_source(
    connector: Connector,
    stored: Mapping[str, frozenset[tuple[str, str]]],
    linked: Mapping[str, str],
) -> SourceFetch:
    """The issues of *source*'s filter that no item holds or whose listed ``updated_at`` differs
    from the stored ones (*stored*: ID to the ``(updated_at, state)`` of each item holding it, so an
    issue back in the filter is read again), fetched in
    detail, and each linked item of *linked* (ID to last known key) the filter no longer lists,
    fetched one by one, through the *connector* :func:`open_connector` returned."""
    return await aio.to_thread(lambda: _fetch(connector, stored, linked))


def _fetch_one(connector: Connector, found: Issue | None, issue_id: str) -> SourceFetch:
    """The fetch of the single issue *found* (wanted as *issue_id*): in ``changed`` when the
    filter lists it, else in ``linked``, where ``None`` means the tracker no longer returns it."""
    listed = frozenset(issue.id for issue in connector.listing())
    detailed = None if found is None else _with_details(connector, found)
    if detailed is not None and issue_id in listed:
        return SourceFetch(changed=(detailed,), listed=listed)
    return SourceFetch(listed=listed, linked={issue_id: detailed})


async def fetch_issue(
    source: SourceSpec, credential: Mapping[str, str], issue_id: str, key: str
) -> SourceFetch:
    """The one issue *issue_id* (last known as *key*) of *source*, with its comments and links,
    and the IDs in the filter, so the caller can tell whether it is still in it."""
    connector = await open_connector(source, credential)
    return await aio.to_thread(
        lambda: _fetch_one(connector, connector.issue(issue_id, key), issue_id)
    )


async def fetch_referenced_issue(
    source: SourceSpec, credential: Mapping[str, str], reference: str
) -> tuple[str, SourceFetch]:
    """The issue a person names by *reference*, a key or an immutable ID, as :func:`fetch_issue`
    brings it back, with the immutable ID it resolved to; refused when the tracker returns
    none."""
    connector = await open_connector(source, credential)

    def run() -> tuple[str, SourceFetch]:
        found = connector.lookup(reference)
        if found is None:
            raise SquadsError(
                f"source {source.name!r} has no issue {reference!r} that its credential can read"
            )
        return found.id, _fetch_one(connector, found, found.id)

    return await aio.to_thread(run)


async def resolve_handle(source: SourceSpec, credential: Mapping[str, str], handle: str) -> str:
    """The immutable user ID behind *handle* on *source*; refuses a handle nobody holds."""
    connector = await open_connector(source, credential)
    found = await aio.to_thread(lambda: connector.resolve_handle(handle))
    if found is None:
        raise SquadsError(f"source {source.name!r} has no user {handle!r}")
    return found


async def resolve_identity_handles(
    sources: Callable[[], SourcesSpec], values: Mapping[str, str | None]
) -> dict[str, str | None]:
    """*values* (source name to a user ID, a ``@handle`` or ``None`` to remove) with each handle
    replaced by the immutable ID its source's connector answers; an ID is kept as given.

    A handle needs a declared, enabled source with a stored credential, else it is refused and
    nothing is resolved further."""
    out: dict[str, str | None] = {}
    for name, value in values.items():
        if value is None or not value.startswith("@"):
            out[name] = value
            continue
        source = sources().source(name)
        require_enabled(source)
        out[name] = await resolve_handle(source, require_credential(source), value)
    return out
