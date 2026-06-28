"""Load and validate the bundled default workflow spec (ADR-000214 §3).

``load_workflow_spec()`` is the single entry point.  It reads
``default_workflow.toml`` via ``importlib.resources`` (offline, no filesystem
assumption), parses with stdlib ``tomllib``, coerces all string keys/values into
``ItemType``/``Status`` enums, builds the derived reverse indexes, and runs
``WorkflowSpec.validate()`` (the pydantic ``model_validator``).  A corrupt or
invalid bundled spec raises ``SquadsError`` — fail closed.
"""

import importlib.resources
import tomllib
from typing import Any

from squads._errors import SquadsError
from squads._models._enums import ItemType, Status
from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec, WorkflowSpec


def load_workflow_spec() -> WorkflowSpec:
    """Read, parse, coerce, and validate the bundled ``default_workflow.toml``.

    Returns a fully-validated ``WorkflowSpec`` singleton (called once at module
    level in ``__init__.py``).  Raises ``SquadsError`` on any violation.
    """
    try:
        pkg = importlib.resources.files("squads._workflow")
        toml_bytes = (pkg / "default_workflow.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled default_workflow.toml: {exc}") from exc

    try:
        raw: dict[str, Any] = tomllib.loads(toml_bytes.decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled default_workflow.toml: {exc}") from exc

    return _build_spec(raw)


def _coerce_status(value: str, ctx: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        raise SquadsError(f"{ctx}: unknown Status value {value!r}") from None


def _coerce_item_type(value: str, ctx: str) -> ItemType:
    try:
        return ItemType(value)
    except ValueError:
        raise SquadsError(f"{ctx}: unknown ItemType value {value!r}") from None


def _parse_lifecycle(name: str, data: dict[str, Any]) -> Lifecycle:
    initial = _coerce_status(data["initial"], f"lifecycle {name!r}")
    raw_trans: dict[str, list[str]] = data.get("transitions", {})
    transitions: dict[Status, list[Status]] = {}
    for src_str, dst_strs in raw_trans.items():
        src = _coerce_status(src_str, f"lifecycle {name!r} transition source")
        transitions[src] = [
            _coerce_status(d, f"lifecycle {name!r} transition target") for d in dst_strs
        ]
    return Lifecycle(initial=initial, transitions=transitions)


def _build_spec(raw: dict[str, Any]) -> WorkflowSpec:
    # --- lifecycles (merged item + sub-entity machines) ---
    lifecycles: dict[str, Lifecycle] = {
        name: _parse_lifecycle(name, data) for name, data in raw.get("lifecycles", {}).items()
    }

    # --- statuses ---
    statuses: dict[Status, StatusSpec] = {}
    for name, data in raw.get("statuses", {}).items():
        s = _coerce_status(name, "statuses")
        statuses[s] = StatusSpec(
            terminal=bool(data["terminal"]),
            badge=data.get("badge"),
        )

    # --- items ---
    items: dict[ItemType, ItemSpec] = {}
    prefix_to_type: dict[str, ItemType] = {}
    alias_to_type: dict[str, ItemType] = {}

    for name, data in raw.get("items", {}).items():
        t = _coerce_item_type(name, "items")
        parents: list[ItemType] = [
            _coerce_item_type(p, f"items.{name}.parents") for p in data.get("parents", [])
        ]
        aliases: list[str] = list(data.get("aliases", []))
        ts = ItemSpec(
            prefix=data["prefix"],
            folder=data["folder"],
            lifecycle=data["lifecycle"],
            parents=parents,
            aliases=aliases,
        )
        items[t] = ts
        prefix_to_type[ts.prefix] = t
        for alias in aliases:
            alias_to_type[alias] = t

    # WorkflowSpec construction triggers the model_validator (pydantic v2).
    try:
        spec = WorkflowSpec(
            items=items,
            statuses=statuses,
            lifecycles=lifecycles,
            prefix_to_type=prefix_to_type,
            alias_to_type=alias_to_type,
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(f"Invalid bundled workflow spec: {exc}") from exc

    return spec
