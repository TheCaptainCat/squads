"""What a sourced item's tracker owns: the refusal of a squad write to its title, a field its
source maps, its stored view body or a comment a source wrote."""

from collections.abc import Iterable

from squads._errors import SquadsError
from squads._models._item import Item
from squads._models._participants import source_of
from squads._paths import number_for_id
from squads._sources._spec import SourcesSource
from squads._workflow._models import WorkflowSpec


def _unlink_command(item: Item) -> str:
    return f"sq {item.type} {number_for_id(item.id)} source unlink"


def refuse_owned_write(item: Item, what: str) -> None:
    """Raise, naming the source, the issue key and the unlink command, when *item* holds a source
    record: *what* belongs to the tracker."""
    record = item.source
    if record is None:
        return
    raise SquadsError(
        f"{item.id} is owned by source {record.name!r} (issue {record.key}): {what} is set by "
        f"`sq source pull`; run `{_unlink_command(item)}` to edit it here"
    )


def mapped_field_codes(item: Item, sources: SourcesSource) -> frozenset[str]:
    """The badge fields the item's source maps, empty when it has no record or its source cannot
    be read (an undeclared source maps nothing, and `sq check` reports an unreadable document)."""
    if item.source is None:
        return frozenset()
    try:
        declared = sources().sources.get(item.source.name)
    except SquadsError:
        return frozenset()
    return frozenset(declared.maps.fields) if declared is not None else frozenset()


def refuse_owned_update(
    item: Item,
    sources: SourcesSource,
    spec: WorkflowSpec,
    *,
    by: str,
    new_title: str | None,
    touched: Iterable[str],
) -> None:
    """Refuse an update by *by* that changes the title of a sourced item or a field its source
    maps; the pull of that same source is the one writer."""
    record = item.source
    if record is None or source_of(by) == record.name:
        return
    owned: list[str] = []
    if new_title is not None and new_title != item.title:
        owned.append("its title")
    mapped = mapped_field_codes(item, sources)
    codes = {f.code for f in spec.fields_for(item.type)}
    owned += [f"its {key} field" for key in sorted(set(touched)) if key in codes and key in mapped]
    if owned:
        refuse_owned_write(item, " and ".join(owned))
