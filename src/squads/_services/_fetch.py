"""The fetch phase every command that reads a tracker goes through: the pull, ``show --refresh``,
``relink`` and handle resolution. It refuses a disabled source and runs the blocking connector
calls on a worker thread."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from squads import _aio as aio
from squads._errors import SquadsError
from squads._models import OUT_OF_FILTER
from squads._sources import (
    ACCESS,
    Connector,
    CredentialStore,
    Expected,
    FetchedIssue,
    Issue,
    NotFoundError,
    SourceFetch,
    SourceSpec,
    SourcesSpec,
    load_connector,
    mapped_types,
    missing_credential,
    run_probes,
)


def require_enabled(source: SourceSpec) -> None:
    """Refuse a source that is paused: a disabled source fetches nothing into the squad."""
    if not source.enabled:
        raise SquadsError(
            f"source {source.name!r} is disabled (`enabled = false` in its sources.toml table); "
            "enable it to fetch from it"
        )


def require_credential(credentials: CredentialStore, source: SourceSpec) -> dict[str, str]:
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
    """The connector class *source* names, built for its base URL, scope and *credential*."""
    return connector_class(source)(source.base_url, source.scope, credential)


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


@dataclass
class _Triage:
    """What the listing rows decide before any detail is fetched."""

    wanted: list[Issue] = field(default_factory=list[Issue])
    lines: list[str] = field(default_factory=list[str])
    untouched: int = 0
    filtered_out: int = 0
    no_type: int = 0


def _triage(
    listing: list[Issue], source: SourceSpec, stored: Mapping[str, frozenset[tuple[str, str]]]
) -> _Triage:
    """Sort the listing rows into those to read in detail, those that need nothing, and the
    selected-but-unheld ones the filter or the type map leaves out."""
    out = _Triage()
    for issue in listing:
        accepted = source.accepts(issue)
        if issue.id in stored:
            state = issue.state if accepted else OUT_OF_FILTER
            if stored[issue.id] == frozenset({(issue.updated_at, state)}):
                out.untouched += 1
            else:
                out.wanted.append(issue)
        elif not accepted:
            out.filtered_out += 1
        else:
            types = mapped_types(source.maps, issue)
            if not types:
                out.no_type += 1
            elif len(types) > 1:
                out.lines.append(
                    f"{issue.key}: not created, the issue maps to several types ({sorted(types)})"
                )
            else:
                out.wanted.append(issue)
    return out


def _fetch(
    connector: Connector,
    source: SourceSpec,
    stored: Mapping[str, frozenset[tuple[str, str]]],
    linked: Mapping[str, str],
) -> SourceFetch:
    listing = connector.listing()
    listed = frozenset(issue.id for issue in listing)
    triage = _triage(listing, source, stored)
    skipped = triage.lines
    untouched = triage.untouched
    found: dict[str, FetchedIssue | None] = {}
    changed: list[FetchedIssue] = []
    for issue in triage.wanted:
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
        if issue is None:
            found[issue_id] = None
        elif stored.get(issue_id) == frozenset({(issue.updated_at, OUT_OF_FILTER)}):
            untouched += 1
        else:
            found[issue_id] = _with_details(connector, issue)
    return SourceFetch(
        tuple(changed),
        untouched,
        listed,
        found,
        tuple(skipped),
        connector.restricted,
        triage.filtered_out,
        triage.no_type,
    )


async def fetch_source(
    connector: Connector,
    source: SourceSpec,
    stored: Mapping[str, frozenset[tuple[str, str]]],
    linked: Mapping[str, str],
) -> SourceFetch:
    """The issues of *source* to read in detail, through the *connector* :func:`open_connector`
    returned: a selected issue no item holds that maps to one type, and a held issue whose listed
    ``updated_at`` or state differs from the stored ones (*stored*: ID to the ``(updated_at,
    state)`` of each item holding it). Each held item of *linked* (ID to last known key) the
    listing lacks is fetched by ID."""
    return await aio.to_thread(lambda: _fetch(connector, source, stored, linked))


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
    credentials: CredentialStore,
    sources: Callable[[], SourcesSpec],
    values: Mapping[str, str | None],
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
        out[name] = await resolve_handle(source, require_credential(credentials, source), value)
    return out
