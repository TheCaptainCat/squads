"""``.overrides/workflow.toml`` merges additively into the bundled spec: new vocabulary is
accepted, a built-in type/status/lifecycle/collection/subentity_kind cannot be redefined, an
unknown TOML key raises, and a structurally broken file raises cleanly.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._workflow import load_workflow_spec


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- additive merge


def test_no_override_file_returns_the_bundled_spec(tmp_path: Path) -> None:
    spec = load_workflow_spec(squad_dir=tmp_path)
    bundled = load_workflow_spec()
    assert set(spec.items) == set(bundled.items)
    assert set(spec.statuses) == set(bundled.statuses)


def test_override_adds_a_new_type_status_and_lifecycle(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[statuses.Triaged]
terminal = false

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "task" in spec.items and "bug" in spec.items  # bundled types survive
    assert spec.items["incident"].prefix == "INC"
    assert "triage" in spec.lifecycles
    assert "Triaged" in spec.statuses


def test_new_type_may_reference_an_existing_bundled_lifecycle(tmp_path: Path) -> None:
    """Referencing a built-in lifecycle by name is a reference, not a redefinition."""
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
    assert spec.items["incident"].lifecycle == "work"


# --------------------------------------------------------------------------- redefine guards


@pytest.mark.parametrize(
    ("toml", "match"),
    [
        (
            '[items.task]\nprefix = "TSK"\nfolder = "tasks"\nlifecycle = "work"\n',
            "may not redefine built-in type 'task'",
        ),
        ("[statuses.Done]\nterminal = false\n", "may not redefine built-in status 'Done'"),
        (
            '[lifecycles.work]\ninitial = "Draft"\n[lifecycles.work.transitions]\nDraft = []\n',
            "may not redefine built-in lifecycle 'work'",
        ),
    ],
)
def test_redefining_a_builtin_raises(tmp_path: Path, toml: str, match: str) -> None:
    _write_override(tmp_path, toml)
    with pytest.raises(SquadsError, match=match):
        load_workflow_spec(squad_dir=tmp_path)


def test_typo_key_in_override_raises_via_extra_forbid(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[statuses.CustomStatus]\nterminal = false\nbogus_key = "should_fail"\n',
    )
    with pytest.raises(SquadsError):
        load_workflow_spec(squad_dir=tmp_path)


def test_malformed_toml_raises_naming_the_override_file(tmp_path: Path) -> None:
    _write_override(tmp_path, "[statuses.Broken\nthis is not valid toml ===")
    with pytest.raises(SquadsError, match="Malformed workflow override"):
        load_workflow_spec(squad_dir=tmp_path)


@pytest.mark.parametrize(
    ("toml", "match"),
    [
        (
            """
[statuses.CustomOpen]
terminal = false

[lifecycles.custom_lc]
initial = "CustomOpen"
[lifecycles.custom_lc.transitions]
CustomOpen = []

[items.incident]
prefix = "TASK"
folder = "incidents"
lifecycle = "custom_lc"
""",
            "duplicate prefix",
        ),
        (
            """
[statuses.FolderOpen]
terminal = false

[lifecycles.folder_lc]
initial = "FolderOpen"
[lifecycles.folder_lc.transitions]
FolderOpen = []

[items.new_task_like]
prefix = "NTL"
folder = "tasks"
lifecycle = "folder_lc"
""",
            "duplicate folder",
        ),
    ],
)
def test_a_new_type_colliding_with_a_builtin_prefix_or_folder_raises_through_the_loader(
    tmp_path: Path, toml: str, match: str
) -> None:
    """The prefix/folder-uniqueness guard fires through the on-disk override-merge path too —
    not just when a spec is hand-constructed in memory (that direct-construction instance lives
    in tests/unit/test_workflow_reserved_vocab.py; this is the loader's own wiring point)."""
    _write_override(tmp_path, toml)
    with pytest.raises(SquadsError, match=match):
        load_workflow_spec(squad_dir=tmp_path)


# --------------------------------------------------------------------------- gap: conflicting
# field-code override-merge (coverage-ledger gap #4)


def test_two_fields_declared_with_the_same_code_in_one_override_stanza_fails_closed(
    tmp_path: Path,
) -> None:
    """The duplicate-field-code guard is proven elsewhere against a hand-constructed
    ``WorkflowSpec`` (tests/unit/test_badge_collections.py); this proves the SAME guard fires
    for a genuinely conflicting override arriving through the on-disk merge path — two fields on
    one new type, same code, different collections/labels/defaults. The guard lives in
    ``WorkflowSpec``'s own validator (runs on the merged payload regardless of how it was built),
    so this is the override-merge path's explicit proof rather than a second implementation."""
    _write_override(
        tmp_path,
        """
[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High" },
  { code = "low", label = "Low" },
]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
fields = [
  { code = "impact", label = "Impact (priority)", collection = "priority", default = "high" },
  { code = "impact", label = "Impact (level)", collection = "level", default = "low" },
]
""",
    )
    with pytest.raises(SquadsError, match="duplicate field code 'impact'"):
        load_workflow_spec(squad_dir=tmp_path)
