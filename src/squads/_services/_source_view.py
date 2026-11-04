"""The ``source`` view source: a host's tracker issue, computed where the sources document and the
connectors are reachable and handed to the view engine as a provider."""

from collections.abc import Callable, Iterable

from squads._errors import SquadsError
from squads._models import Item
from squads._services._comment_view import translate_references
from squads._services._fetch import connector_for
from squads._sources import SourceSpec, SourcesSpec
from squads._views import SourceIssue, SourceProvider


def _declared(sources: Callable[[], SourcesSpec], name: str) -> SourceSpec | None:
    """The source declared as *name*, or ``None`` when it is undeclared or the document fails to
    load."""
    try:
        return sources().sources.get(name)
    except SquadsError:
        return None


def described_by(sources: Callable[[], SourcesSpec], items: Iterable[Item]) -> SourceProvider:
    """The provider that answers a host's :class:`SourceIssue`, against *items* for the
    references it translates."""
    held = list(items)

    def provide(item: Item, body: str) -> SourceIssue | None:
        record = item.source
        if record is None:
            return None
        declared = _declared(sources, record.name)
        url = connector_for(declared, {}).issue_url(record.key) if declared else ""
        return SourceIssue(
            name=record.name,
            id=record.id,
            key=record.key,
            state=record.state,
            updated_at=record.updated_at,
            author_id=record.author_id,
            author_handle=record.author_handle,
            url=url,
            trusted=declared.trusted if declared else False,
            text=translate_references(body, record, declared, held),
        )

    return provide
