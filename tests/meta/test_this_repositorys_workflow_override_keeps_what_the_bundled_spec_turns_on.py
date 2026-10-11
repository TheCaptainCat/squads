"""This repository's own `squads/.overrides/workflow.toml` selects the two catalog-only checks
on its types, at their strength, without dropping or re-levelling anything the bundled spec
already turns on. A `validators` array replaces a type's bundled list whole, so a missing splat,
a deleted line or a changed level loses a check silently: neither `sq check` nor
`sq workflow lint` can report that, so this table does. Validators are compared as (name,
parameter, level), the level taken from the entry or else from the member's default.

A later selection adds a row or a column here.
"""

from pathlib import Path

import pytest

from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import (
    DEFAULT_VALIDATOR_LEVEL,
    WorkflowSpec,
    effective_validator_names,
    parse_validator_entry,
)

REPO_OVERRIDE = Path(__file__).resolve().parents[2] / "squads" / ".overrides" / "workflow.toml"

type Validator = tuple[str, str | None, str]

#: type -> (level of no_status_banner, or None when not selected; (threshold, level) of
#: subentity_title_max, or None when not selected).
SELECTIONS: dict[str, tuple[str | None, tuple[int, str] | None]] = {
    "epic": ("warn", (120, "warn")),
    "feature": ("warn", (120, "warn")),
    "task": ("warn", (120, "warn")),
    "bug": ("warn", (120, "warn")),
    "review": ("warn", (120, "warn")),
    "decision": ("warn", None),
    "contract": ("warn", None),
    "milestone": ("warn", None),
    "guide": ("warn", None),
    "role": ("warn", None),
    "skill": ("warn", None),
    "operator": ("warn", None),
}


def _effective(spec: WorkflowSpec, item_type: str) -> frozenset[Validator]:
    ts = spec.items[item_type]
    names = effective_validator_names(ts.category, extra=tuple(ts.validators))
    parsed = (parse_validator_entry(n) for n in names)
    return frozenset(
        (bare, param, level or DEFAULT_VALIDATOR_LEVEL[bare]) for bare, param, level in parsed
    )


def _member(effective: frozenset[Validator], name: str) -> list[Validator]:
    return [v for v in effective if v[0] == name]


@pytest.fixture(scope="module")
def bundled() -> WorkflowSpec:
    return load_workflow_spec()


@pytest.fixture
def merged(tmp_path: Path) -> WorkflowSpec:
    (tmp_path / ".overrides").mkdir()
    (tmp_path / ".overrides" / "workflow.toml").write_text(
        REPO_OVERRIDE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return load_workflow_spec(tmp_path)


def test_every_bundled_type_has_a_row(bundled: WorkflowSpec) -> None:
    assert set(bundled.items) == set(SELECTIONS)


@pytest.mark.parametrize("item_type", sorted(SELECTIONS))
def test_the_merged_spec_keeps_everything_the_bundled_spec_turns_on(
    bundled: WorkflowSpec, merged: WorkflowSpec, item_type: str
) -> None:
    assert _effective(merged, item_type) >= _effective(bundled, item_type)


@pytest.mark.parametrize("item_type", sorted(SELECTIONS))
def test_the_merged_spec_selects_both_checks_where_the_table_says(
    merged: WorkflowSpec, item_type: str
) -> None:
    banner, title = SELECTIONS[item_type]
    effective = _effective(merged, item_type)
    assert _member(effective, "no_status_banner") == (
        [("no_status_banner", None, banner)] if banner else []
    )
    assert _member(effective, "subentity_title_max") == (
        [("subentity_title_max", str(title[0]), title[1])] if title else []
    )
    assert merged.item_subentity_title_max(item_type) == (title[0] if title else None)


@pytest.mark.parametrize("item_type", sorted(SELECTIONS))
def test_the_bundled_spec_selects_neither_check(bundled: WorkflowSpec, item_type: str) -> None:
    assert not _member(_effective(bundled, item_type), "no_status_banner")
    assert not _member(_effective(bundled, item_type), "subentity_title_max")
    assert bundled.item_subentity_title_max(item_type) is None
