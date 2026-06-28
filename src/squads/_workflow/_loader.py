"""Load and validate the bundled default workflow spec (ADR-000214 §3 / ADR-000232 §5).

``load_workflow_spec()`` is the single entry point.  It reads
``default_workflow.toml`` via ``importlib.resources`` (offline, no filesystem
assumption), parses with stdlib ``tomllib``, coerces all string keys/values into
``ItemType``/``Status`` enums, builds the derived reverse indexes, and runs
``WorkflowSpec.validate()`` (the pydantic ``model_validator``).  A corrupt or
invalid bundled spec raises ``SquadsError`` — fail closed.

ADR-000232 §5: the loader now routes through ``model_validate(...)`` for each
spec model so ``extra="forbid"`` fires at parse time, not just at pydantic
construction, giving consistent fail-closed behaviour across all sub-models.
"""

import importlib.resources
import tomllib
from typing import Any

from squads._errors import SquadsError
from squads._models._enums import ItemType, Status
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec


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
    # Build the dict with ONLY the known keys, then also pass through any extras so
    # model_validate's extra="forbid" fires on unknown fields (ADR-000232 §5).
    # The lifecycle TOML format has exactly "initial" + "transitions"; unknown top-level
    # keys should be rejected, but the transitions sub-table must not be passed as extra.
    known_keys = {"initial", "transitions"}
    extra_keys = {k: data[k] for k in data if k not in known_keys}
    payload: dict[str, Any] = {"initial": initial, "transitions": transitions, **extra_keys}
    try:
        return Lifecycle.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid lifecycle {name!r}: {exc}") from exc


def _parse_ref_rules(raw_rules: list[dict[str, Any]], ctx: str) -> list[RefRule]:
    """Parse a list of ref-rule dicts into ``RefRule`` objects (ADR-000232 §2).

    Passes the raw dict directly to ``model_validate`` so ``extra="forbid"`` rejects
    any unknown keys in a ref-rule table.
    """
    rules: list[RefRule] = []
    for i, rule_data in enumerate(raw_rules):
        try:
            rules.append(RefRule.model_validate(rule_data))
        except Exception as exc:
            raise SquadsError(f"{ctx} ref_rule[{i}]: {exc}") from exc
    return rules


def _build_spec(raw: dict[str, Any]) -> WorkflowSpec:
    # --- lifecycles (merged item + sub-entity machines) ---
    lifecycles: dict[str, Lifecycle] = {
        name: _parse_lifecycle(name, data) for name, data in raw.get("lifecycles", {}).items()
    }

    # --- statuses ---
    statuses: dict[Status, StatusSpec] = {}
    for name, data in raw.get("statuses", {}).items():
        s = _coerce_status(name, "statuses")
        # Pass the full status data dict through model_validate so extra="forbid" fires
        # on any unknown keys (ADR-000232 §5).
        try:
            statuses[s] = StatusSpec.model_validate(data)
        except Exception as exc:
            raise SquadsError(f"Invalid status {name!r}: {exc}") from exc

    # --- items ---
    items: dict[ItemType, ItemSpec] = {}
    prefix_to_type: dict[str, ItemType] = {}
    alias_to_type: dict[str, ItemType] = {}

    for name, data in raw.get("items", {}).items():
        t = _coerce_item_type(name, "items")
        # Pre-coerce enum-typed fields (parents list) while passing the rest through so
        # model_validate's extra="forbid" can reject any unknown keys.
        parents: list[ItemType] = [
            _coerce_item_type(p, f"items.{name}.parents") for p in data.get("parents", [])
        ]
        ref_rules_raw: list[dict[str, Any]] = data.get("ref_rules", [])
        ref_rules = _parse_ref_rules(ref_rules_raw, f"items.{name}")
        # Build the payload: start with the raw data, then override the pre-coerced fields
        # so model_validate sees the right types AND any unknown keys trigger extra="forbid".
        payload: dict[str, Any] = {**data, "parents": parents, "ref_rules": ref_rules}
        try:
            ts = ItemSpec.model_validate(payload)
        except Exception as exc:
            raise SquadsError(f"Invalid item spec {name!r}: {exc}") from exc
        items[t] = ts
        prefix_to_type[ts.prefix] = t
        for alias in ts.aliases:
            alias_to_type[alias] = t

    # WorkflowSpec construction triggers the model_validator (pydantic v2).
    # Route through model_validate so extra="forbid" fires at construction (ADR-000232 §5).
    try:
        spec = WorkflowSpec.model_validate(
            {
                "items": items,
                "statuses": statuses,
                "lifecycles": lifecycles,
                "prefix_to_type": prefix_to_type,
                "alias_to_type": alias_to_type,
            }
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(f"Invalid bundled workflow spec: {exc}") from exc

    return spec
