"""This repository's own `squads/.overrides/workflow.toml` selects the two catalog-only checks
on its types without dropping anything the bundled spec already turns on. A `validators` array
replaces a type's bundled list whole, so a missing splat or a deleted line loses a check
silently: neither `sq check` nor `sq workflow lint` can report that, so this table does.

A later selection adds its row here.
"""

from pathlib import Path

import pytest

from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec, effective_validator_names, parse_validator_entry

REPO_OVERRIDE = Path(__file__).resolve().parents[2] / "squads" / ".overrides" / "workflow.toml"

#: type -> (no_status_banner effective, subentity_title_max threshold or None).
SELECTIONS: dict[str, tuple[bool, int | None]] = {
    "epic": (True, 120),
    "feature": (True, 120),
    "task": (True, 120),
    "bug": (True, 120),
    "review": (True, 120),
    "decision": (True, None),
    "contract": (True, None),
    "milestone": (True, None),
    "guide": (True, None),
    "role": (True, None),
    "skill": (True, None),
    "operator": (True, None),
}


def _effective(spec: WorkflowSpec, item_type: str) -> frozenset[str]:
    ts = spec.items[item_type]
    names = effective_validator_names(ts.category, extra=tuple(ts.validators))
    return frozenset(parse_validator_entry(n)[0] for n in names)


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
    assert ("no_status_banner" in _effective(merged, item_type)) is banner
    assert merged.item_subentity_title_max(item_type) == title
    assert ("subentity_title_max" in _effective(merged, item_type)) is (title is not None)


@pytest.mark.parametrize("item_type", sorted(SELECTIONS))
def test_the_bundled_spec_selects_neither_check(bundled: WorkflowSpec, item_type: str) -> None:
    assert "no_status_banner" not in _effective(bundled, item_type)
    assert bundled.item_subentity_title_max(item_type) is None
