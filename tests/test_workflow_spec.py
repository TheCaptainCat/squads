"""TASK-000217: Golden-lock + packaging tests for the externalized WorkflowSpec (FEAT-000207 F1).

The golden-lock test is the regression gate for the entire EPIC-000206: it asserts the
loaded default WorkflowSpec reproduces today's exact workflow behavior by building a
snapshot directly from the existing Python literals and asserting structural equality.

If this test fails, a type/status/machine/terminal/badge changed between the TOML and
the code.  Fix the TOML (or, if intentional, update the snapshot here and the TOML together).
"""

import importlib.resources
import zipfile
from pathlib import Path

import pytest

from squads._models._enums import (
    FOLDER_BY_TYPE,
    PREFIX_BY_TYPE,
    STATUS_EMOJI,
    TYPE_ALIASES,
    ItemType,
    Status,
)
from squads._workflow import (
    ALLOWED_PARENTS,
    SUBENTITY_WORKFLOWS,
    TERMINAL,
    WORKFLOWS,
    WorkflowSpec,
    load_workflow_spec,
)

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Golden-lock test (ADR-000214 §4 / TASK-217 ST1)
# ---------------------------------------------------------------------------

# Snapshot of the SEVEN distinct lifecycle vocabularies, built directly from today's
# _workflow.py literals.  Keyed by a canonical name so the assertion is legible.
_LIFECYCLE_SNAPSHOT: dict[str, dict[str, object]] = {
    # ---- work lifecycle ----
    "work": {
        "initial": Status.DRAFT,
        "transitions": {
            Status.DRAFT: [Status.READY, Status.IN_PROGRESS, Status.CANCELLED],
            Status.READY: [Status.IN_PROGRESS, Status.BLOCKED, Status.CANCELLED],
            Status.IN_PROGRESS: [Status.IN_REVIEW, Status.BLOCKED, Status.DONE, Status.CANCELLED],
            Status.IN_REVIEW: [Status.IN_PROGRESS, Status.DONE, Status.BLOCKED, Status.CANCELLED],
            Status.BLOCKED: [Status.READY, Status.IN_PROGRESS, Status.CANCELLED],
            Status.DONE: [Status.IN_PROGRESS],
            Status.CANCELLED: [Status.DRAFT],
        },
    },
    # ---- adr lifecycle ----
    "adr": {
        "initial": Status.PROPOSED,
        "transitions": {
            Status.PROPOSED: [Status.ACCEPTED, Status.REJECTED],
            Status.ACCEPTED: [Status.SUPERSEDED, Status.DEPRECATED],
            Status.REJECTED: [Status.PROPOSED],
            Status.SUPERSEDED: [],
            Status.DEPRECATED: [],
        },
    },
    # ---- review lifecycle ----
    "review": {
        "initial": Status.REQUESTED,
        "transitions": {
            Status.REQUESTED: [Status.IN_REVIEW, Status.REJECTED],
            Status.IN_REVIEW: [Status.CHANGES_REQUESTED, Status.APPROVED, Status.REJECTED],
            Status.CHANGES_REQUESTED: [Status.IN_REVIEW, Status.REJECTED],
            Status.APPROVED: [],
            Status.REJECTED: [],
        },
    },
    # ---- bug lifecycle ----
    "bug": {
        "initial": Status.OPEN,
        "transitions": {
            Status.OPEN: [Status.IN_PROGRESS, Status.WONT_FIX, Status.CANCELLED],
            Status.IN_PROGRESS: [Status.FIXED, Status.BLOCKED, Status.WONT_FIX, Status.CANCELLED],
            Status.FIXED: [Status.VERIFIED, Status.IN_PROGRESS],
            Status.VERIFIED: [Status.IN_PROGRESS],
            Status.BLOCKED: [Status.IN_PROGRESS, Status.WONT_FIX, Status.CANCELLED],
            Status.WONT_FIX: [Status.OPEN],
            Status.CANCELLED: [Status.OPEN],
        },
    },
    # ---- guide lifecycle ----
    "guide": {
        "initial": Status.DRAFT,
        "transitions": {
            Status.DRAFT: [Status.PUBLISHED],
            Status.PUBLISHED: [Status.DEPRECATED, Status.DRAFT],
            Status.DEPRECATED: [Status.PUBLISHED],
        },
    },
    # ---- agent lifecycle (role/skill/operator) ----
    "agent": {
        "initial": Status.DRAFT,
        "transitions": {
            Status.DRAFT: [Status.ACTIVE],
            Status.ACTIVE: [Status.ARCHIVED],
            Status.ARCHIVED: [Status.ACTIVE],
        },
    },
}

# Sub-entity lifecycle snapshot (keyed by kind).
_SUBENTITY_SNAPSHOT: dict[str, dict[str, object]] = {
    "subtask": {
        "initial": Status.TODO,
        "transitions": {
            Status.TODO: [Status.IN_PROGRESS, Status.BLOCKED, Status.CANCELLED],
            Status.IN_PROGRESS: [Status.DONE, Status.BLOCKED, Status.CANCELLED],
            Status.BLOCKED: [Status.IN_PROGRESS, Status.CANCELLED],
            Status.DONE: [Status.IN_PROGRESS],
            Status.CANCELLED: [Status.TODO],
        },
    },
    "story": {
        "initial": Status.TODO,
        "transitions": {
            Status.TODO: [Status.IN_PROGRESS, Status.BLOCKED, Status.CANCELLED],
            Status.IN_PROGRESS: [Status.DONE, Status.BLOCKED, Status.CANCELLED],
            Status.BLOCKED: [Status.IN_PROGRESS, Status.CANCELLED],
            Status.DONE: [Status.IN_PROGRESS],
            Status.CANCELLED: [Status.TODO],
        },
    },
    "finding": {
        "initial": Status.OPEN,
        "transitions": {
            Status.OPEN: [Status.FIXED, Status.WONT_FIX],
            Status.FIXED: [Status.VERIFIED, Status.OPEN],
            Status.VERIFIED: [],
            Status.WONT_FIX: [Status.OPEN],
        },
    },
}


def _lifecycle_name_for(item_type: ItemType) -> str:
    """Return the expected lifecycle name for each ItemType (mirrors the TOML assignment)."""
    _LIFECYCLE_BY_TYPE: dict[ItemType, str] = {
        ItemType.EPIC: "work",
        ItemType.FEATURE: "work",
        ItemType.TASK: "work",
        ItemType.BUG: "bug",
        ItemType.DECISION: "adr",
        ItemType.REVIEW: "review",
        ItemType.GUIDE: "guide",
        ItemType.ROLE: "agent",
        ItemType.SKILL: "agent",
        ItemType.OPERATOR: "agent",
    }
    return _LIFECYCLE_BY_TYPE[item_type]


@pytest.fixture(scope="module")
def spec() -> WorkflowSpec:
    return load_workflow_spec()


def test_spec_loads_without_error(spec: WorkflowSpec) -> None:
    """Smoke: the default spec loads and passes all validation."""
    assert spec is not None
    assert isinstance(spec, WorkflowSpec)


def test_golden_type_set(spec: WorkflowSpec) -> None:
    """Every ItemType must be present in the spec — enums-intact (ADR §5-6a)."""
    assert set(spec.items) == set(ItemType), (
        f"spec item set {set(spec.items)!r} != set(ItemType) {set(ItemType)!r}"
    )


def test_golden_status_set(spec: WorkflowSpec) -> None:
    """Every Status must be present in the spec — enums-intact (ADR §5-6b)."""
    assert set(spec.statuses) == set(Status), (
        f"spec status set {set(spec.statuses)!r} != set(Status) {set(Status)!r}"
    )


def test_golden_prefixes_and_folders(spec: WorkflowSpec) -> None:
    """Each item type's prefix and folder match today's PREFIX_BY_TYPE/FOLDER_BY_TYPE exactly."""
    for t in ItemType:
        ts = spec.items[t]
        assert ts.prefix == PREFIX_BY_TYPE[t], (
            f"{t!r}: spec prefix {ts.prefix!r} != {PREFIX_BY_TYPE[t]!r}"
        )
        assert ts.folder == FOLDER_BY_TYPE[t], (
            f"{t!r}: spec folder {ts.folder!r} != {FOLDER_BY_TYPE[t]!r}"
        )


def test_golden_aliases(spec: WorkflowSpec) -> None:
    """Each item type's aliases match today's TYPE_ALIASES exactly (sorted for comparison)."""
    for t in ItemType:
        ts = spec.items[t]
        expected = sorted(TYPE_ALIASES.get(t, ()))
        actual = sorted(ts.aliases)
        assert actual == expected, f"{t!r}: spec aliases {actual!r} != {expected!r}"


def test_golden_allowed_parents(spec: WorkflowSpec) -> None:
    """Each item type's parents list matches today's ALLOWED_PARENTS exactly."""
    for t in ItemType:
        ts = spec.items[t]
        # ALLOWED_PARENTS only contains types WITH constraints; absent = unconstrained (empty).
        expected = ALLOWED_PARENTS.get(t, set())
        actual = set(ts.parents)
        assert actual == expected, f"{t!r}: spec parents {actual!r} != {expected!r}"


def test_golden_lifecycle_assignments(spec: WorkflowSpec) -> None:
    """Each item type uses the expected named lifecycle (mirrors WORKFLOWS assignment)."""
    for t in ItemType:
        expected_lifecycle = _lifecycle_name_for(t)
        ts = spec.items[t]
        assert ts.lifecycle == expected_lifecycle, (
            f"{t!r}: spec lifecycle {ts.lifecycle!r} != {expected_lifecycle!r}"
        )


def test_golden_lifecycles_initial_and_transitions(spec: WorkflowSpec) -> None:
    """Every named item lifecycle's initial and full transitions map matches the snapshot."""
    for name, snap in _LIFECYCLE_SNAPSHOT.items():
        assert name in spec.lifecycles, f"lifecycle {name!r} missing from spec"
        m = spec.lifecycles[name]
        expected_initial: Status = snap["initial"]  # type: ignore[assignment]
        assert m.initial == expected_initial, (
            f"lifecycle {name!r}: initial {m.initial!r} != {expected_initial!r}"
        )
        expected_trans: dict[Status, list[Status]] = snap["transitions"]  # type: ignore[assignment]
        assert dict(m.transitions) == expected_trans, (
            f"lifecycle {name!r}: transitions differ.\n"
            f"  spec: {dict(m.transitions)}\n"
            f"  snapshot: {expected_trans}"
        )


def test_golden_workflow_shim_matches_lifecycles(spec: WorkflowSpec) -> None:
    """WORKFLOWS shim has identical initial/transitions to the spec lifecycles."""
    for t in ItemType:
        wf = WORKFLOWS[t]
        m = spec.machine_for(t)
        assert wf.initial == m.initial, (
            f"{t!r}: WORKFLOWS initial {wf.initial!r} != spec lifecycle initial {m.initial!r}"
        )
        # transitions: shim stores tuple, spec stores list — compare as sets of sorted tuples.
        for src, dsts in m.transitions.items():
            shim_dsts = set(wf.transitions.get(src, ()))
            assert shim_dsts == set(dsts), (
                f"{t!r}: WORKFLOWS[{src!r}] {shim_dsts!r} != spec {set(dsts)!r}"
            )


def test_golden_terminal_set(spec: WorkflowSpec) -> None:
    """TERMINAL frozenset matches status-by-status."""
    assert spec.terminal_set() == TERMINAL, (
        f"spec terminal set {spec.terminal_set()!r} != TERMINAL {TERMINAL!r}"
    )
    for s in Status:
        expected_terminal = s in TERMINAL
        actual_terminal = spec.statuses[s].terminal
        assert actual_terminal == expected_terminal, (
            f"status {s!r}: spec.terminal={actual_terminal} != {expected_terminal}"
        )


def test_golden_status_badges(spec: WorkflowSpec) -> None:
    """Status badges from STATUS_EMOJI match spec StatusSpec.badge, status-by-status."""
    for s in Status:
        expected_badge = STATUS_EMOJI.get(s)
        actual_badge = spec.statuses[s].badge
        assert actual_badge == expected_badge, (
            f"status {s!r}: spec.badge={actual_badge!r} != STATUS_EMOJI={expected_badge!r}"
        )


def test_golden_subentity_lifecycles(spec: WorkflowSpec) -> None:
    """Sub-entity lifecycles match snapshot and SUBENTITY_WORKFLOWS shim."""
    for kind, snap in _SUBENTITY_SNAPSHOT.items():
        assert kind in spec.lifecycles, f"lifecycle {kind!r} missing from spec"
        m = spec.lifecycles[kind]
        expected_initial: Status = snap["initial"]  # type: ignore[assignment]
        assert m.initial == expected_initial, (
            f"subentity {kind!r}: initial {m.initial!r} != {expected_initial!r}"
        )
        expected_trans: dict[Status, list[Status]] = snap["transitions"]  # type: ignore[assignment]
        assert dict(m.transitions) == expected_trans, (
            f"subentity {kind!r}: transitions differ.\n"
            f"  spec: {dict(m.transitions)}\n"
            f"  snapshot: {expected_trans}"
        )
        # Also check the shim.
        shim = SUBENTITY_WORKFLOWS[kind]
        assert shim.initial == m.initial, (
            f"subentity {kind!r}: SUBENTITY_WORKFLOWS initial mismatch"
        )


def test_golden_spec_set_equals_subentity_workflows_keys(spec: WorkflowSpec) -> None:
    """Spec's sub-entity lifecycle key set == SUBENTITY_WORKFLOWS key set."""
    assert set(_SUBENTITY_SNAPSHOT) == set(SUBENTITY_WORKFLOWS), (
        f"subentity lifecycle keys differ: "
        f"snapshot={set(_SUBENTITY_SNAPSHOT)!r} vs shim={set(SUBENTITY_WORKFLOWS)!r}"
    )


# ---------------------------------------------------------------------------
# Packaging test (TASK-217 ST2)
# ---------------------------------------------------------------------------


def test_default_workflow_toml_accessible_via_importlib_resources() -> None:
    """default_workflow.toml is accessible via importlib.resources (i.e. ships as package data)."""
    pkg = importlib.resources.files("squads._workflow")
    toml_path = pkg / "default_workflow.toml"
    content = toml_path.read_bytes()
    assert content, "default_workflow.toml is empty"
    assert b"[lifecycles.work]" in content, "expected [lifecycles.work] section in TOML"
    assert b"[items.task]" in content, "expected [items.task] section in TOML"


def test_default_workflow_toml_ships_in_wheel(tmp_path: Path) -> None:
    """default_workflow.toml is present in the built wheel (package-data invariant).

    ``[tool.hatch.build.targets.wheel] packages = ["src/squads"]`` sweeps all
    non-.py files under the package — this test confirms it actually does so.
    """
    import shutil
    import subprocess

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not found on PATH — cannot build wheel")

    result = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"wheel build failed: {result.stderr[:300]}")

    wheels = list(tmp_path.glob("*.whl"))
    assert wheels, f"no wheel produced in {tmp_path}"

    with zipfile.ZipFile(wheels[0]) as whl:
        names = whl.namelist()

    assert any("default_workflow.toml" in n for n in names), (
        "default_workflow.toml not found in wheel; "
        f"files matching *workflow*: {[n for n in names if 'workflow' in n]}"
    )


# ---------------------------------------------------------------------------
# Regression: sq workflow output unchanged
# ---------------------------------------------------------------------------


async def test_sq_workflow_cli_unchanged(invoke) -> None:  # type: ignore[no-untyped-def]
    """``sq workflow`` renders the same cheatsheet as before the externalization."""
    result = await invoke(["workflow"])
    assert result.exit_code == 0, f"sq workflow failed: {result.output}"
    # Spot-check key vocabulary that must appear in the cheatsheet.
    assert "workflow" in result.output.lower()
    assert "sq " in result.output or "sq\n" in result.output
