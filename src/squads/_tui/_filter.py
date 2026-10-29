"""The filter/sort popup: a modal seeded from and returning a new `BrowseState`.

Imports no `_tui` module but `_session` — the seed/result `BrowseState`/`SortKey` are
only ever handled via `dataclasses.replace()` on the instances they are given, never
constructed from an imported class; both are imported only under `TYPE_CHECKING`.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Switch
from textual.widgets.select import NoSelection

from squads._api._dto._workflow import FieldEntry
from squads._tui._session import Catalogs, status_options, type_options

if TYPE_CHECKING:
    from squads._tui._browse import BrowseState

_BADGE_CODE = "filter-badge-code"
_BADGE_VALUE = "filter-badge-value"
_SORT_SEQUENCE = "sequence"

#: The type categories a filter offers, in the order it offers them.
_CATEGORIES: tuple[str, ...] = ("roster", "work", "records")


def _all_badge_fields(catalogs: Catalogs) -> list[FieldEntry]:
    """Every declared badge field, deduplicated by code across every non-roster type —
    catalog-generic, not hard-coded to `priority`."""
    seen: dict[str, FieldEntry] = {}
    for row in sorted(catalogs.types.items, key=lambda r: r.type):
        if row.reserved:
            continue
        for f in row.fields:
            seen.setdefault(f.code, f)
    return list(seen.values())


def _badge_value_options(field: FieldEntry | None, catalogs: Catalogs) -> list[tuple[str, str]]:
    if field is None:
        return []
    coll = next((c for c in catalogs.collections.items if c.collection == field.collection), None)
    return [(b.label, b.code) for b in coll.badges] if coll else []


def _selected(select: Select[str]) -> str | None:
    value = select.value
    return None if isinstance(value, NoSelection) else value


def _sort_options(badge_fields: list[FieldEntry]) -> list[tuple[str, str]]:
    opts = [
        ("Sequence (default)", _SORT_SEQUENCE),
        ("Status", "status"),
        ("Title", "title"),
        ("Last updated", "updated"),
    ]
    opts += [(f.label, f"badge:{f.code}") for f in badge_fields]
    return opts


def _encode_sort(kind: str, badge_code: str | None) -> str:
    return f"badge:{badge_code}" if kind == "badge" and badge_code else kind


class FilterScreen(ModalScreen["BrowseState | None"]):
    """The filter/sort popup — pushed over `BrowseScreen`, which stays mounted and dimmed."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    FilterScreen {
        align: center middle;
    }
    FilterScreen #filter-dialog {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(self, state: BrowseState, catalogs: Catalogs) -> None:
        super().__init__()
        self._state = state
        self._catalogs = catalogs
        self._badge_fields = _all_badge_fields(catalogs)

        seed_code, seed_value = state.filter.badges[0] if state.filter.badges else (None, None)
        seed_field = next((f for f in self._badge_fields if f.code == seed_code), None)

        self._type_select: Select[str] = Select(
            type_options(catalogs),
            id="filter-type",
            value=state.filter.item_type or Select.NULL,
        )
        self._status_select: Select[str] = Select(
            status_options(catalogs),
            id="filter-status",
            value=state.filter.status or Select.NULL,
        )
        self._category_select: Select[str] = Select(
            [(c.capitalize(), c) for c in _CATEGORIES],
            id="filter-category",
            value=state.filter.category or Select.NULL,
        )
        self._assignee_input = Input(value=state.filter.assignee or "", id="filter-assignee")
        self._label_input = Input(value=state.filter.label or "", id="filter-label")

        self._badge_code_select: Select[str] | None = None
        self._badge_value_select: Select[str] | None = None
        if self._badge_fields:
            self._badge_code_select = Select(
                [(f.label, f.code) for f in self._badge_fields],
                id=_BADGE_CODE,
                value=seed_code or Select.NULL,
            )
            self._badge_value_select = Select(
                _badge_value_options(seed_field, catalogs),
                id=_BADGE_VALUE,
                value=seed_value or Select.NULL,
            )

        self._show_closed_switch = Switch(value=state.include_closed, id="filter-show-closed")
        self._sort_select: Select[str] = Select(
            _sort_options(self._badge_fields),
            id="filter-sort",
            value=_encode_sort(state.sort.kind, state.sort.badge_code),
            allow_blank=False,
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="filter-dialog"):
            yield Label("Filter")
            yield Label("Type")
            yield self._type_select
            yield Label("Status")
            yield self._status_select
            yield Label("Category")
            yield self._category_select
            yield Label("Assignee")
            yield self._assignee_input
            yield Label("Label")
            yield self._label_input
            if self._badge_code_select is not None and self._badge_value_select is not None:
                yield Label("Badge field")
                yield self._badge_code_select
                yield Label("Value")
                yield self._badge_value_select
            with Horizontal():
                yield Label("Show closed")
                yield self._show_closed_switch
            yield Label("Sort by")
            yield self._sort_select
            with Horizontal():
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Clear", id="clear")
                yield Button("Cancel", id="cancel")

    def _field_for(self, code: str | None) -> FieldEntry | None:
        return next((f for f in self._badge_fields if f.code == code), None)

    def on_select_changed(self, event: Select.Changed) -> None:
        code_select = self._badge_code_select
        value_select = self._badge_value_select
        if code_select is None or value_select is None or event.select is not code_select:
            return
        code = _selected(code_select)
        value_select.set_options(_badge_value_options(self._field_for(code), self._catalogs))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            self.dismiss(self._build_state())
        elif event.button.id == "clear":
            self._reset_widgets()
        elif event.button.id == "cancel":
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _reset_widgets(self) -> None:
        self._type_select.value = Select.NULL
        self._status_select.value = Select.NULL
        self._category_select.value = Select.NULL
        self._assignee_input.value = ""
        self._label_input.value = ""
        if self._badge_code_select is not None and self._badge_value_select is not None:
            self._badge_code_select.value = Select.NULL
            self._badge_value_select.set_options([])
        self._show_closed_switch.value = False
        self._sort_select.value = _SORT_SEQUENCE

    def _build_state(self) -> BrowseState:
        item_type = _selected(self._type_select)
        status = _selected(self._status_select)
        category = _selected(self._category_select)
        assignee = self._assignee_input.value.strip() or None
        label = self._label_input.value.strip() or None
        badges: tuple[tuple[str, str], ...] = ()
        if self._badge_code_select is not None and self._badge_value_select is not None:
            code = _selected(self._badge_code_select)
            value = _selected(self._badge_value_select)
            if code and value:
                badges = ((code, value),)
        new_filter = replace(
            self._state.filter,
            item_type=item_type,
            status=status,
            category=category,
            assignee=assignee,
            label=label,
            badges=badges,
        )

        sort_value = _selected(self._sort_select) or _SORT_SEQUENCE
        if sort_value.startswith("badge:"):
            code = sort_value.removeprefix("badge:")
            new_sort = replace(self._state.sort, kind="badge", badge_code=code)
        else:
            new_sort = replace(self._state.sort, kind=sort_value, badge_code=None)

        return replace(
            self._state,
            filter=new_filter,
            include_closed=self._show_closed_switch.value,
            sort=new_sort,
        )
