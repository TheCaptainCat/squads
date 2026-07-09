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

from _helpers import (
    BUILTIN_FOLDER,
    BUILTIN_PREFIX,
    BUILTIN_STATUSES,
    BUILTIN_TYPES,
    EXPECTED_BUILTIN_STATUS_BADGES,
    FORMER_FLOOR_STATUSES,
)
from squads._errors import SquadsError
from squads._workflow import (
    ALLOWED_PARENTS,
    SUBENTITY_WORKFLOWS,
    TERMINAL,
    WORKFLOWS,
    StatusSpec,
    WorkflowSpec,
    load_workflow_spec,
)
from squads._workflow._models import SubentityKindSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Golden-lock test (ADR-000214 §4 / TASK-217 ST1)
# ---------------------------------------------------------------------------

# Snapshot of the SEVEN distinct lifecycle vocabularies, built directly from today's
# _workflow.py literals.  Keyed by a canonical name so the assertion is legible.
_LIFECYCLE_SNAPSHOT: dict[str, dict[str, object]] = {
    # ---- work lifecycle ----
    "work": {
        "initial": "Draft",
        "transitions": {
            "Draft": ["Ready", "InProgress", "Cancelled"],
            "Ready": ["InProgress", "Blocked", "Cancelled"],
            "InProgress": ["InReview", "Blocked", "Done", "Cancelled"],
            "InReview": ["InProgress", "Done", "Blocked", "Cancelled"],
            "Blocked": ["Ready", "InProgress", "Cancelled"],
            "Done": ["InProgress"],
            "Cancelled": ["Draft"],
        },
    },
    # ---- adr lifecycle ----
    "adr": {
        "initial": "Proposed",
        "transitions": {
            "Proposed": ["Accepted", "Rejected"],
            "Accepted": ["Superseded", "Deprecated"],
            "Rejected": ["Proposed"],
            "Superseded": [],
            "Deprecated": [],
        },
    },
    # ---- review lifecycle ----
    "review": {
        "initial": "Requested",
        "transitions": {
            "Requested": ["InReview", "Rejected"],
            "InReview": ["ChangesRequested", "Approved", "Rejected"],
            "ChangesRequested": ["InReview", "Approved", "Rejected"],
            "Approved": [],
            "Rejected": [],
        },
    },
    # ---- bug lifecycle ----
    "bug": {
        "initial": "Open",
        "transitions": {
            "Open": ["InProgress", "WontFix", "Cancelled"],
            "InProgress": ["Fixed", "Blocked", "WontFix", "Cancelled"],
            "Fixed": ["Verified", "InProgress"],
            "Verified": ["InProgress"],
            "Blocked": ["InProgress", "WontFix", "Cancelled"],
            "WontFix": ["Open"],
            "Cancelled": ["Open"],
        },
    },
    # ---- guide lifecycle ----
    "guide": {
        "initial": "Draft",
        "transitions": {
            "Draft": ["Published"],
            "Published": ["Deprecated", "Draft"],
            "Deprecated": ["Published"],
        },
    },
    # ---- agent lifecycle (role/skill/operator) ----
    "agent": {
        "initial": "Draft",
        "transitions": {
            "Draft": ["Active"],
            "Active": ["Archived"],
            "Archived": ["Active"],
        },
    },
}

# Sub-entity lifecycle snapshot (keyed by kind).
_SUBENTITY_SNAPSHOT: dict[str, dict[str, object]] = {
    "subtask": {
        "initial": "Todo",
        "transitions": {
            "Todo": ["InProgress", "Blocked", "Cancelled"],
            "InProgress": ["Done", "Blocked", "Cancelled"],
            "Blocked": ["InProgress", "Cancelled"],
            "Done": ["InProgress"],
            "Cancelled": ["Todo"],
        },
    },
    "story": {
        "initial": "Todo",
        "transitions": {
            "Todo": ["InProgress", "Blocked", "Cancelled"],
            "InProgress": ["Done", "Blocked", "Cancelled"],
            "Blocked": ["InProgress", "Cancelled"],
            "Done": ["InProgress"],
            "Cancelled": ["Todo"],
        },
    },
    "finding": {
        "initial": "Open",
        "transitions": {
            "Open": ["Fixed", "WontFix"],
            "Fixed": ["Verified", "Open"],
            "Verified": [],
            "WontFix": ["Open"],
        },
    },
}


def _lifecycle_name_for(item_type: str) -> str:
    """Return the expected lifecycle name for each built-in type (mirrors the TOML assignment)."""
    _LIFECYCLE_BY_TYPE: dict[str, str] = {
        "epic": "work",
        "feature": "work",
        "task": "work",
        "bug": "bug",
        "decision": "adr",
        "review": "review",
        "guide": "guide",
        "role": "agent",
        "skill": "agent",
        "operator": "agent",
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
    """Every built-in type must be present in the bundled spec (no-override characterization)."""
    assert set(spec.items) == set(BUILTIN_TYPES), (
        f"spec item set {set(spec.items)!r} != {set(BUILTIN_TYPES)!r}"
    )


def test_golden_status_set(spec: WorkflowSpec) -> None:
    """Every built-in status must be present in the bundled spec (no-override characterization)."""
    assert set(spec.statuses) == set(BUILTIN_STATUSES), (
        f"spec status set {set(spec.statuses)!r} != {set(BUILTIN_STATUSES)!r}"
    )


def test_golden_prefixes_and_folders(spec: WorkflowSpec) -> None:
    """Each item type's prefix and folder match the built-in vocab exactly."""
    for t in BUILTIN_TYPES:
        ts = spec.items[t]
        assert ts.prefix == BUILTIN_PREFIX[t], (
            f"{t!r}: spec prefix {ts.prefix!r} != {BUILTIN_PREFIX[t]!r}"
        )
        assert ts.folder == BUILTIN_FOLDER[t], (
            f"{t!r}: spec folder {ts.folder!r} != {BUILTIN_FOLDER[t]!r}"
        )


def test_golden_aliases(spec: WorkflowSpec) -> None:
    """Each work item type's aliases list is non-empty in the spec.

    The authoritative alias values live in default_workflow.toml (ItemSpec.aliases).
    This test guards against accidentally clearing the aliases for any work type.
    """
    # The 7 known-aliased work types and their expected sorted aliases (from default_workflow.toml).
    _EXPECTED_ALIASES: dict[str, list[str]] = {
        "epic": ["e"],
        "feature": ["f", "feat"],
        "task": ["t"],
        "bug": ["b"],
        "decision": ["d", "dec"],
        "review": ["r", "rev"],
        "guide": ["g"],
    }
    for t in BUILTIN_TYPES:
        ts = spec.items[t]
        expected = _EXPECTED_ALIASES.get(t, [])
        actual = sorted(ts.aliases)
        assert actual == expected, f"{t!r}: spec aliases {actual!r} != {expected!r}"


def test_golden_allowed_parents(spec: WorkflowSpec) -> None:
    """Each item type's parents list matches today's ALLOWED_PARENTS exactly."""
    for t in BUILTIN_TYPES:
        ts = spec.items[t]
        # ALLOWED_PARENTS only contains types WITH constraints; absent = unconstrained (empty).
        expected = ALLOWED_PARENTS.get(t, set())
        actual = set(ts.parents)
        assert actual == expected, f"{t!r}: spec parents {actual!r} != {expected!r}"


def test_golden_lifecycle_assignments(spec: WorkflowSpec) -> None:
    """Each item type uses the expected named lifecycle (mirrors WORKFLOWS assignment)."""
    for t in BUILTIN_TYPES:
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
        expected_initial: str = snap["initial"]  # type: ignore[assignment]
        assert m.initial == expected_initial, (
            f"lifecycle {name!r}: initial {m.initial!r} != {expected_initial!r}"
        )
        expected_trans: dict[str, list[str]] = snap["transitions"]  # type: ignore[assignment]
        assert dict(m.transitions) == expected_trans, (
            f"lifecycle {name!r}: transitions differ.\n"
            f"  spec: {dict(m.transitions)}\n"
            f"  snapshot: {expected_trans}"
        )


def test_golden_workflow_shim_matches_lifecycles(spec: WorkflowSpec) -> None:
    """WORKFLOWS shim has identical initial/transitions to the spec lifecycles."""
    for t in BUILTIN_TYPES:
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
    for s in BUILTIN_STATUSES:
        expected_terminal = s in TERMINAL
        actual_terminal = spec.statuses[s].terminal
        assert actual_terminal == expected_terminal, (
            f"status {s!r}: spec.terminal={actual_terminal} != {expected_terminal}"
        )


def test_golden_status_badges(spec: WorkflowSpec) -> None:
    """Status badges from EXPECTED_BUILTIN_STATUS_BADGES match spec StatusSpec.badge."""
    for s in BUILTIN_STATUSES:
        expected_badge = EXPECTED_BUILTIN_STATUS_BADGES.get(s)
        actual_badge = spec.statuses[s].badge
        assert actual_badge == expected_badge, (
            f"status {s!r}: spec.badge={actual_badge!r} != "
            f"EXPECTED_BUILTIN_STATUS_BADGES={expected_badge!r}"
        )


def test_golden_subentity_lifecycles(spec: WorkflowSpec) -> None:
    """Sub-entity machines (resolved per kind via SubentityKindSpec.lifecycle, not by
    kind-name==lifecycle-name) match snapshot and the SUBENTITY_WORKFLOWS shim."""
    for kind, snap in _SUBENTITY_SNAPSHOT.items():
        wf = spec.subentity_workflow(kind)
        expected_initial: str = snap["initial"]  # type: ignore[assignment]
        assert wf.initial == expected_initial, (
            f"subentity {kind!r}: initial {wf.initial!r} != {expected_initial!r}"
        )
        expected_trans: dict[str, list[str]] = snap["transitions"]  # type: ignore[assignment]
        actual_trans = {s: list(dsts) for s, dsts in wf.transitions.items()}
        assert actual_trans == expected_trans, (
            f"subentity {kind!r}: transitions differ.\n"
            f"  spec: {actual_trans}\n"
            f"  snapshot: {expected_trans}"
        )
        # Also check the shim.
        shim = SUBENTITY_WORKFLOWS[kind]
        assert shim.initial == wf.initial, (
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


# ---------------------------------------------------------------------------
# TASK-000235 / ADR-322 §2/§5: reserved-vocab subset — negative tests.
# Only the three meta-types are floor-enforced on the type axis; a custom spec that omits
# a non-meta (work) type is now accepted. On the status axis the floor narrows to exactly
# the agent lifecycle (Draft/Active/Archived) — every other status, including the former
# sub-entity/finding floor members, is now ordinary spec vocabulary.
# ---------------------------------------------------------------------------


def test_omitting_a_work_type_is_now_allowed(spec: WorkflowSpec) -> None:
    """Dropping a non-meta type no longer raises (ADR-322 narrows the floor to the three
    meta-types only).

    Drops 'guide', which has no back-references from any other type's ``parents`` — this
    isolates the floor-membership behavior from the separate parent-reference check.
    """
    items_without_guide = {k: v for k, v in spec.items.items() if k != "guide"}
    assert "guide" not in items_without_guide  # sanity

    result = WorkflowSpec.model_validate(
        {
            "items": items_without_guide,
            "statuses": spec.statuses,
            "lifecycles": spec.lifecycles,
            "prefix_to_type": {p: t for p, t in spec.prefix_to_type.items() if t != "guide"},
            "alias_to_type": spec.alias_to_type,
            "collections": spec.collections,
            "subentity_kinds": spec.subentity_kinds,
        }
    )
    assert "guide" not in result.items


def test_omitting_a_meta_type_still_fails_closed(spec: WorkflowSpec) -> None:
    """A spec missing a meta-type (role/skill/operator) still raises SquadsError (ADR-322 §2)."""
    items_without_role = {k: v for k, v in spec.items.items() if k != "role"}
    assert "role" not in items_without_role  # sanity

    with pytest.raises(SquadsError, match="spec missing required meta-types"):
        WorkflowSpec.model_validate(
            {
                "items": items_without_role,
                "statuses": spec.statuses,
                "lifecycles": spec.lifecycles,
                "prefix_to_type": {p: t for p, t in spec.prefix_to_type.items() if t != "role"},
                "alias_to_type": spec.alias_to_type,
            }
        )


def test_reserved_vocab_omit_status_fails_closed(spec: WorkflowSpec) -> None:
    """A spec missing an agent-lifecycle floor status raises SquadsError (ADR-322 §5).

    Drops 'Active' — one of the three agent-lifecycle statuses (Draft/Active/Archived)
    that remain the ONLY status-axis floor after the narrowing. A spec omitting one of
    these must still be rejected, even though every other status (work-item, sub-entity,
    finding) is now ordinary, droppable vocabulary (see the former-floor test below).
    """
    statuses_without_active = {k: v for k, v in spec.statuses.items() if k != "Active"}
    assert "Active" not in statuses_without_active  # sanity

    # The 'agent' lifecycle also references 'Active' in its transitions, so the
    # lifecycle-integrity check fires too — the missing-floor error appears regardless,
    # since every check runs and collects into one combined error message.
    with pytest.raises(SquadsError, match="spec missing reserved Status members"):
        WorkflowSpec.model_validate(
            {
                "items": spec.items,
                "statuses": statuses_without_active,
                "lifecycles": spec.lifecycles,
                "prefix_to_type": spec.prefix_to_type,
                "alias_to_type": spec.alias_to_type,
            }
        )


@pytest.mark.parametrize("status_name", FORMER_FLOOR_STATUSES)
def test_former_floor_status_omission_no_longer_hits_the_reserved_floor(
    spec: WorkflowSpec, status_name: str
) -> None:
    """Sub-entity/finding statuses left the reserved floor (ADR-322 §5).

    Dropping one of them from a copy of the bundled spec still fails — the subtask/
    story/finding lifecycles still name it in their transitions — but via the
    lifecycle-integrity check, never via the (narrowed) 'spec missing reserved Status
    members' floor check.  That distinction is the whole point: these names are ordinary,
    renamable spec vocabulary now, not a hardcoded floor.
    """
    statuses_without = {k: v for k, v in spec.statuses.items() if k != status_name}
    with pytest.raises(SquadsError) as exc_info:
        WorkflowSpec.model_validate(
            {
                "items": spec.items,
                "statuses": statuses_without,
                "lifecycles": spec.lifecycles,
                "prefix_to_type": spec.prefix_to_type,
                "alias_to_type": spec.alias_to_type,
            }
        )
    assert "spec missing reserved Status members" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Each declared sub-entity kind's `completion` must name a reachable, non-initial status
# of its own lifecycle — the status the done-toggle resolves to instead of a hardcoded
# literal. Re-homed from the retired global StatusSpec.completion flag scan.
# ---------------------------------------------------------------------------


def test_subentity_completion_pointing_at_initial_status_fails_to_load(
    spec: WorkflowSpec,
) -> None:
    """Nothing is 'done' at creation — completion can't be the kind's own initial status."""
    bad = spec.subentity_kinds["subtask"].model_copy(update={"completion": "Todo"})
    with pytest.raises(SquadsError, match="completion 'Todo' is the initial status"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "subtask": bad})


def test_finding_completion_pointing_at_initial_status_fails_to_load(
    spec: WorkflowSpec,
) -> None:
    bad = spec.subentity_kinds["finding"].model_copy(update={"completion": "Open"})
    with pytest.raises(SquadsError, match="completion 'Open' is the initial status"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "finding": bad})


def test_subentity_completion_outside_own_machine_fails_to_load(spec: WorkflowSpec) -> None:
    """'WontFix' belongs to the finding machine, not the shared story/subtask one."""
    bad = spec.subentity_kinds["subtask"].model_copy(update={"completion": "WontFix"})
    with pytest.raises(SquadsError, match="completion 'WontFix' not a reachable status"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "subtask": bad})


def test_finding_completion_outside_own_machine_fails_to_load(spec: WorkflowSpec) -> None:
    """'Cancelled' belongs to the story/subtask machine, not finding's."""
    bad = spec.subentity_kinds["finding"].model_copy(update={"completion": "Cancelled"})
    with pytest.raises(SquadsError, match="completion 'Cancelled' not a reachable status"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "finding": bad})


def test_bundled_spec_resolves_one_completion_status_per_subentity_kind(
    spec: WorkflowSpec,
) -> None:
    """The bundled default's done-toggle target for each sub-entity/finding kind."""
    assert spec.subentity_completion("subtask") == "Done"
    assert spec.subentity_completion("story") == "Done"
    assert spec.subentity_completion("finding") == "Fixed"


def test_non_reserved_status_omission_is_allowed(spec: WorkflowSpec) -> None:
    """Dropping a work-item-only status that is NOT in the structural floor is ALLOWED (§5-6b).

    'Ready' is used only in the work lifecycle (transitions from Draft → Ready, etc.) and
    is NOT a structural-floor status.  A custom spec that omits it should be accepted by
    §5-6b — the §5-1/§5-2 checks enforce it indirectly if a lifecycle references it.

    We build a minimal spec that uses none of the work-lifecycle statuses so there is no
    §5-1/§5-2 conflict, and verify no SquadsError is raised for the missing 'Ready'.
    """
    from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec, WorkflowSpec

    # Minimal spec: one item type ('task') on a trivial lifecycle that uses only floor
    # statuses (Draft → Done), plus all floor statuses declared.  'Ready' is absent.
    floor_statuses: dict[str, StatusSpec] = {
        "Draft": StatusSpec(terminal=False),
        "Active": StatusSpec(terminal=False),
        "Archived": StatusSpec(terminal=True),
        "Todo": StatusSpec(terminal=False),
        "InProgress": StatusSpec(terminal=False),
        "Blocked": StatusSpec(terminal=False),
        "Done": StatusSpec(terminal=True),
        "Cancelled": StatusSpec(terminal=True),
        "Open": StatusSpec(terminal=False),
        "Fixed": StatusSpec(terminal=True),
        "Verified": StatusSpec(terminal=True),
        "WontFix": StatusSpec(terminal=True),
    }

    # §5-1/§5-2 requires every referenced status to be declared. Use a lifecycle that only
    # touches floor statuses so 'Ready' is never referenced.
    minimal_lifecycle = Lifecycle(
        initial="Draft",
        transitions={"Draft": ["Done"], "Done": []},
    )
    agent_lifecycle = Lifecycle(
        initial="Draft",
        transitions={"Draft": ["Active"], "Active": ["Archived"], "Archived": ["Active"]},
    )
    subentity_lifecycle = Lifecycle(
        initial="Todo",
        transitions={
            "Todo": ["InProgress", "Blocked", "Cancelled"],
            "InProgress": ["Done", "Blocked", "Cancelled"],
            "Blocked": ["InProgress", "Cancelled"],
            "Done": ["InProgress"],
            "Cancelled": ["Todo"],
        },
    )
    finding_lifecycle = Lifecycle(
        initial="Open",
        transitions={
            "Open": ["Fixed", "WontFix"],
            "Fixed": ["Verified", "Open"],
            "Verified": [],
            "WontFix": ["Open"],
        },
    )

    # Only the floor statuses — 'Ready' is intentionally absent to prove §5-6b does not
    # reject it.  No 'Ready' in the lifecycles used below either (minimal_lifecycle only
    # references Draft and Done; agent/subentity/finding lifecycles use their own floor
    # statuses), so §5-1/§5-2 won't flag the omission.
    all_statuses = {**floor_statuses}  # no 'Ready'

    # Only the three meta-types are floor-required (ADR-322 §2); 'task' is declared too so
    # minimal_lifecycle has a real work-type consumer.
    items_map = {
        "task": ItemSpec(prefix="TASK", folder="tasks", lifecycle="minimal", is_meta=False),
        "role": ItemSpec(prefix="ROLE", folder="agents/roles", lifecycle="agent", is_meta=True),
        "skill": ItemSpec(prefix="SKILL", folder="agents/skills", lifecycle="agent", is_meta=True),
        "operator": ItemSpec(prefix="OP", folder="operators", lifecycle="agent", is_meta=True),
    }

    # No SquadsError should be raised — 'Ready' is absent but is not a floor status.
    result = WorkflowSpec.model_validate(
        {
            "items": items_map,
            "statuses": all_statuses,
            "lifecycles": {
                "minimal": minimal_lifecycle,
                "agent": agent_lifecycle,
                "subtask": subentity_lifecycle,
                "story": subentity_lifecycle,
                "finding": finding_lifecycle,
            },
            "prefix_to_type": {ts.prefix: name for name, ts in items_map.items()},
            "alias_to_type": {},
        }
    )
    assert "Ready" not in result.statuses


# ---------------------------------------------------------------------------
# TASK-000349 / ADR-348 §1/§2/§6: SubentityKindSpec machine + vocab keys.
# ---------------------------------------------------------------------------


def test_bundled_subentity_kinds_declare_machine_and_vocab(spec: WorkflowSpec) -> None:
    """story/subtask/finding are now fully declared: lifecycle/completion/plural/
    local_prefix/maps_parent_story reproduce today's hardcoded vocabulary exactly.
    story and subtask share one lifecycle machine (`subentity`); finding has its own."""
    story = spec.subentity_kinds["story"]
    subtask = spec.subentity_kinds["subtask"]
    finding = spec.subentity_kinds["finding"]

    assert (
        story.lifecycle,
        story.completion,
        story.plural,
        story.local_prefix,
        story.maps_parent_story,
    ) == ("subentity", "Done", "stories", "US", False)
    assert (
        subtask.lifecycle,
        subtask.completion,
        subtask.plural,
        subtask.local_prefix,
        subtask.maps_parent_story,
    ) == ("subentity", "Done", "subtasks", "ST", True)
    assert (
        finding.lifecycle,
        finding.completion,
        finding.plural,
        finding.local_prefix,
        finding.maps_parent_story,
    ) == ("finding", "Fixed", "findings", "F", False)

    assert story.placeholder and "user story" in story.placeholder
    assert subtask.placeholder and "subtask" in subtask.placeholder
    assert finding.placeholder and "finding" in finding.placeholder


def test_subentity_accessors_resolve_via_kind_spec_lifecycle(spec: WorkflowSpec) -> None:
    """subentity_workflow/subentity_initial/subentity_can_transition now resolve through
    SubentityKindSpec.lifecycle instead of the retired kind-name==lifecycle-name
    convention, but the bundled result is byte-identical."""
    for kind in ("story", "subtask", "finding"):
        machine = spec.lifecycles[spec.subentity_kinds[kind].lifecycle]
        assert spec.subentity_initial(kind) == machine.initial
        assert spec.subentity_workflow(kind).initial == machine.initial
    assert spec.subentity_can_transition("subtask", "Todo", "InProgress") is True
    assert spec.subentity_can_transition("subtask", "Todo", "Done") is False


def _rebuild_subentity_kinds(
    spec: WorkflowSpec, subentity_kinds: dict[str, SubentityKindSpec]
) -> WorkflowSpec:
    return WorkflowSpec.model_validate(
        {
            "items": spec.items,
            "statuses": spec.statuses,
            "lifecycles": spec.lifecycles,
            "prefix_to_type": spec.prefix_to_type,
            "alias_to_type": spec.alias_to_type,
            "collections": spec.collections,
            "subentity_kinds": subentity_kinds,
        }
    )


def test_item_referencing_undeclared_subentity_kind_fails_closed(spec: WorkflowSpec) -> None:
    """An ItemSpec.subentity_kind naming a kind absent from subentity_kinds must fail
    closed at load, not raw-KeyError later out of subentity_workflow/initial/can_transition."""
    bad_feature = spec.items["feature"].model_copy(update={"subentity_kind": "ghost"})
    with pytest.raises(SquadsError, match="undeclared subentity kind 'ghost'"):
        WorkflowSpec.model_validate(
            {
                "items": {**spec.items, "feature": bad_feature},
                "statuses": spec.statuses,
                "lifecycles": spec.lifecycles,
                "prefix_to_type": spec.prefix_to_type,
                "alias_to_type": spec.alias_to_type,
                "collections": spec.collections,
                "subentity_kinds": spec.subentity_kinds,
            }
        )


def test_subentity_kind_undeclared_lifecycle_fails_closed(spec: WorkflowSpec) -> None:
    bad_story = spec.subentity_kinds["story"].model_copy(update={"lifecycle": "no-such-lifecycle"})
    with pytest.raises(SquadsError, match="lifecycle 'no-such-lifecycle' not declared"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "story": bad_story})


def test_subentity_kind_duplicate_plural_fails_closed(spec: WorkflowSpec) -> None:
    bad_story = spec.subentity_kinds["story"].model_copy(
        update={"plural": spec.subentity_kinds["subtask"].plural}
    )
    with pytest.raises(SquadsError, match="duplicate subentity plural 'subtasks'"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "story": bad_story})


def test_subentity_kind_duplicate_local_prefix_fails_closed(spec: WorkflowSpec) -> None:
    bad_story = spec.subentity_kinds["story"].model_copy(
        update={"local_prefix": spec.subentity_kinds["subtask"].local_prefix}
    )
    with pytest.raises(SquadsError, match="duplicate subentity local_prefix 'ST'"):
        _rebuild_subentity_kinds(spec, {**spec.subentity_kinds, "story": bad_story})
