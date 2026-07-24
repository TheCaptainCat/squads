"""The ``.overrides/workflow.toml`` loader parses a nested ``[items.<type>.labels]`` table
into ``LabelSpec`` via the standard nested-model ``model_validate`` path — no
dedicated parser needed, same as any other nested capability-flag model — and a misspelled
sub-key inside that table is rejected at load time by ``LabelSpec``'s own ``extra="forbid"``.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._workflow import load_workflow_spec


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def test_a_new_types_nested_labels_table_loads_into_labelspec(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"

[items.incident.labels]
singular = "Incident"
plural = "Incidents"
singular_lower = "incident"
plural_lower = "incidents"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    labels = spec.items["incident"].labels
    assert labels is not None
    assert labels.singular == "Incident"
    assert labels.plural == "Incidents"
    assert labels.singular_lower == "incident"
    assert labels.plural_lower == "incidents"


def test_a_partial_labels_table_leaves_the_rest_none(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"

[items.incident.labels]
plural = "Incidents"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    labels = spec.items["incident"].labels
    assert labels is not None
    assert labels.plural == "Incidents"
    assert labels.singular is None


def test_a_misspelled_labels_sub_key_is_rejected_at_load(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"

[items.incident.labels]
plurals = "Incidents"
""",
    )
    with pytest.raises(SquadsError, match="Extra inputs are not permitted"):
        load_workflow_spec(squad_dir=tmp_path)


def test_an_item_type_with_no_labels_table_still_loads_with_none(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.items["incident"].labels is None
