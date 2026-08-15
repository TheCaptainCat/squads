"""``.overrides/workflow.toml`` merges over the bundled spec with SHADOWING semantics:
new vocabulary is accepted, a hand-written field replaces its built-in
counterpart (every other field of that entry is inherited unchanged), `[selected]` drops a
built-in by name, an unknown TOML key still raises, and a structurally broken file raises
cleanly. The one locked exception is the roster type-key lock (role/skill/operator) — proven
in its own section below.
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


# --------------------------------------------------------------------------- shadowing: a
# hand-written field replaces its built-in counterpart; every other field is inherited


def test_shadowing_one_field_of_a_builtin_type_inherits_every_other_field(tmp_path: Path) -> None:
    bundled = load_workflow_spec()
    bundled_task = bundled.items["task"]
    _write_override(tmp_path, '[items.task]\nfolder = "tickets"\n')
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.items["task"].folder == "tickets"
    assert spec.items["task"].prefix == bundled_task.prefix
    assert spec.items["task"].lifecycle == bundled_task.lifecycle
    assert spec.items["task"].parents == bundled_task.parents


def test_shadowing_a_builtin_status_role_replaces_it(tmp_path: Path) -> None:
    bundled = load_workflow_spec()
    assert bundled.statuses["Done"].role != "attention"
    _write_override(tmp_path, '[statuses.Done]\nrole = "attention"\n')
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.statuses["Done"].role == "attention"


def test_shadowing_a_builtin_lifecycle_wholesale_replaces_its_transitions(tmp_path: Path) -> None:
    """The deep merge recurses tables per key — a nested table like ``transitions`` merges
    key-by-key rather than being swapped out wholesale, so every one of ``work``'s existing
    state keys must still be supplied (each an array, hence a leaf that replaces outright) for
    every state to stay declared and reachable; a partial rewrite naming only some of the
    keys would leave the rest with their bundled routes, stranding whichever states nothing
    routes to any more. Supplying every key with a different graph is exactly how an adopter
    wholesale-replaces a shared built-in lifecycle's routing."""
    _write_override(
        tmp_path,
        """
[lifecycles.work]
initial = "Draft"
[lifecycles.work.transitions]
Draft = ["Ready", "Cancelled"]
Ready = ["InProgress", "Blocked"]
InProgress = ["InReview"]
InReview = ["Done"]
Blocked = ["Ready"]
Done = []
Cancelled = []
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.lifecycles["work"].transitions == {
        "Draft": ["Ready", "Cancelled"],
        "Ready": ["InProgress", "Blocked"],
        "InProgress": ["InReview"],
        "InReview": ["Done"],
        "Blocked": ["Ready"],
        "Done": [],
        "Cancelled": [],
    }


def test_shadowing_a_builtin_collection_replaces_its_badge_list(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[collections.priority]
label = "Priority"
ordered = true
badges = [{ code = "urgent", label = "Urgent" }]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert {b.code for b in spec.collections["priority"].badges} == {"urgent"}


def test_shadowing_a_builtin_subentity_kind_replaces_its_declaration(tmp_path: Path) -> None:
    _write_override(tmp_path, '[subentity_kinds.finding]\nplural = "issues"\n')
    spec = load_workflow_spec(squad_dir=tmp_path)
    bundled = load_workflow_spec()
    assert spec.subentity_kinds["finding"].plural == "issues"
    # every other field of the shadowed kind is inherited unchanged
    assert spec.subentity_kinds["finding"].lifecycle == bundled.subentity_kinds["finding"].lifecycle
    assert (
        spec.subentity_kinds["finding"].local_prefix
        == bundled.subentity_kinds["finding"].local_prefix
    )


def test_selected_drops_a_builtin_type_from_the_merged_spec(tmp_path: Path) -> None:
    bundled = load_workflow_spec()
    kept = sorted(t for t in bundled.items if t != "guide")
    _write_override(tmp_path, f"[selected]\nitems = {kept!r}\n")
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items
    assert "task" in spec.items  # everything else survives


def test_renaming_a_builtin_type_via_selected_plus_a_splat_ref_produces_it_under_the_new_name(
    tmp_path: Path,
) -> None:
    """A rename is a drop (via selected) plus an add (a new key spliced from the old one via
    the merge engine's $(*self)/$(path) splat grammar) — this loader adds no special "rename"
    verb; the engine already provides everything the combination needs.

    ``selected`` is a wholesale surviving-set replacement applied AFTER the deep merge (the
    engine's own fixed order) — a newly-added key like ``doc`` is already present in the
    merged mapping by the time ``[selected]`` runs, so it must be named in the keep list too,
    or it gets deselected right along with everything else not listed."""
    bundled = load_workflow_spec()
    kept = sorted([t for t in bundled.items if t != "guide"] + ["doc"])
    _write_override(
        tmp_path,
        f"""
[selected]
items = {kept!r}

[items.doc]
prefix = "$(items.guide.prefix)"
folder = "$(items.guide.folder)"
lifecycle = "$(items.guide.lifecycle)"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items
    assert spec.items["doc"].prefix == bundled.items["guide"].prefix
    assert spec.items["doc"].folder == bundled.items["guide"].folder


def test_typo_key_in_override_raises_via_extra_forbid(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[statuses.CustomStatus]\nbogus_key = "should_fail"\n',
    )
    with pytest.raises(SquadsError):
        load_workflow_spec(squad_dir=tmp_path)


def test_malformed_toml_raises_naming_the_override_file(tmp_path: Path) -> None:
    _write_override(tmp_path, "[statuses.Broken\nthis is not valid toml ===")
    with pytest.raises(SquadsError, match="Malformed workflow override"):
        load_workflow_spec(squad_dir=tmp_path)


def test_an_unknown_top_level_key_fails_closed(tmp_path: Path) -> None:
    """The workflow document's top-level key space is closed — a mistyped
    section name is refused, not silently dropped."""
    _write_override(tmp_path, '[bogus_section.task]\nprefix = "X"\n')
    with pytest.raises(SquadsError, match="unknown top-level key 'bogus_section'"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_retired_top_level_override_base_key_fails_closed_as_unknown(tmp_path: Path) -> None:
    """The top-level ``override_base`` spec key is retired in favour of the
    ``# squads:override-base:<version>`` comment stamp — writing it as a real
    TOML key is a mistyped provenance declaration, not a legitimate section."""
    _write_override(tmp_path, 'override_base = "0.1.0"\n')
    with pytest.raises(SquadsError, match="unknown top-level key 'override_base'"):
        load_workflow_spec(squad_dir=tmp_path)


@pytest.mark.parametrize(
    ("toml", "match"),
    [
        (
            """
[statuses.CustomOpen]

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


# --------------------------------------------------------------------------- roster type-key
# lock: the three roster type keys, plus category immobility — never prefix


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
def test_dropping_a_roster_type_via_selected_fails_closed(tmp_path: Path, roster_type: str) -> None:
    bundled = load_workflow_spec()
    kept = sorted(t for t in bundled.items if t != roster_type)
    _write_override(tmp_path, f"[selected]\nitems = {kept!r}\n")
    with pytest.raises(SquadsError, match=f"drop roster type {roster_type!r}"):
        load_workflow_spec(squad_dir=tmp_path)


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
def test_moving_a_roster_type_out_of_category_roster_fails_closed(
    tmp_path: Path, roster_type: str
) -> None:
    _write_override(tmp_path, f'[items.{roster_type}]\ncategory = "work"\n')
    with pytest.raises(SquadsError, match=f"move roster type {roster_type!r} out of category"):
        load_workflow_spec(squad_dir=tmp_path)


def test_declaring_a_new_type_with_category_roster_fails_closed(tmp_path: Path) -> None:
    """An override may not mint a fourth roster type — category='roster' is locked to the
    three existing keys, never adopter-declarable onto a new one."""
    _write_override(
        tmp_path,
        '[items.gadget]\nprefix = "GAD"\nfolder = "gadgets"\nlifecycle = "work"\n'
        'category = "roster"\n',
    )
    with pytest.raises(SquadsError, match="add a new roster type 'gadget'"):
        load_workflow_spec(squad_dir=tmp_path)


def test_renaming_a_roster_type_fails_closed_on_the_drop_half(tmp_path: Path) -> None:
    """A "rename" of a roster type is a drop (of the old key) plus an add (of the new one) —
    both halves are locked, so it fails on whichever the merge engine/loader reaches first;
    here the drop (via selected) is what fires."""
    bundled = load_workflow_spec()
    kept = sorted(t for t in bundled.items if t != "role")
    _write_override(
        tmp_path,
        f"""
[selected]
items = {kept!r}

[items.agent]
prefix = "AGT"
folder = "agents/roles"
lifecycle = "roster_lifecycle"
category = "roster"
""",
    )
    with pytest.raises(SquadsError, match="drop roster type 'role'"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_roster_types_lifecycle_prefix_folder_labels_and_order_are_ordinary_field_merges(
    tmp_path: Path,
) -> None:
    """The lock is written on the key set plus category immobility only — never on prefix (or
    folder/labels/order/lifecycle): those stay ordinary field-mergeable customisation under the
    same full floor every other type faces."""
    _write_override(
        tmp_path,
        """
[statuses.Retired]
role = "done"

[lifecycles.role_lc]
initial = "Active"
[lifecycles.role_lc.transitions]
Active = ["Retired"]
Retired = []

[items.role]
prefix = "AGENT"
folder = "agents/people"
lifecycle = "role_lc"
order = 1
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.items["role"].prefix == "AGENT"
    assert spec.items["role"].folder == "agents/people"
    assert spec.items["role"].lifecycle == "role_lc"
    assert spec.items["role"].category == "roster"


def test_the_universal_roster_lifecycle_floor_still_runs_on_a_shadowed_roster_lifecycle(
    tmp_path: Path,
) -> None:
    """R1 (at least one live status) is not re-derived here — WorkflowSpec._validate already
    enforces it; this proves it runs against the MERGED spec, not only the bundled one."""
    _write_override(
        tmp_path,
        """
[statuses.Spinning]
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"
""",
    )
    with pytest.raises(SquadsError, match="no live status"):
        load_workflow_spec(squad_dir=tmp_path)


# --------------------------------------------------------------------------- referential
# integrity: the refusal names what still references a dropped key, with [selected]
# provenance when that is how the key was dropped


def _drop_status_override(status_to_drop: str) -> str:
    bundled = load_workflow_spec()
    kept = sorted(s for s in bundled.statuses if s != status_to_drop)
    return f"[selected]\nstatuses = {kept!r}\n"


@pytest.mark.parametrize(
    ("dropped_status", "referrer_fragment"),
    [
        ("Approved", "lifecycle 'review'"),
        ("Draft", "lifecycle 'work'"),
    ],
    ids=["lifecycle-transition-target", "lifecycle-initial"],
)
def test_a_status_dropped_via_selected_is_named_by_its_referring_lifecycle_with_provenance(
    tmp_path: Path, dropped_status: str, referrer_fragment: str
) -> None:
    _write_override(tmp_path, _drop_status_override(dropped_status))
    with pytest.raises(SquadsError) as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(exc_info.value)
    assert referrer_fragment in message
    assert f"{dropped_status!r} was dropped from a [selected] list" in message
    assert "selected.statuses" in message


def test_a_lifecycle_dropped_via_selected_is_named_by_its_referring_type_with_provenance(
    tmp_path: Path,
) -> None:
    bundled = load_workflow_spec()
    kept = sorted(lc for lc in bundled.lifecycles if lc != "work")
    _write_override(tmp_path, f"[selected]\nlifecycles = {kept!r}\n")
    with pytest.raises(SquadsError) as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(exc_info.value)
    assert "item 'task'" in message
    assert "'work' was dropped from a [selected] list (selected.lifecycles)" in message


def test_a_type_dropped_via_selected_and_still_named_as_a_parent_is_reported_with_provenance(
    tmp_path: Path,
) -> None:
    bundled = load_workflow_spec()
    kept = sorted(t for t in bundled.items if t != "feature")
    assert "task" in kept  # task's parent_required names "feature"
    _write_override(tmp_path, f"[selected]\nitems = {kept!r}\n")
    with pytest.raises(SquadsError) as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(exc_info.value)
    assert "item 'task'" in message
    assert "parent type 'feature'" in message
    assert "'feature' was dropped from a [selected] list (selected.items)" in message


def test_a_role_dropped_via_selected_and_still_referenced_by_a_status_is_reported_with_provenance(
    tmp_path: Path,
) -> None:
    bundled = load_workflow_spec()
    role_to_drop = next(r for r, spec in bundled.roles.items() if spec.settled and r != "pending")
    referring_status = next(s for s, spec in bundled.statuses.items() if spec.role == role_to_drop)
    kept = sorted(r for r in bundled.roles if r != role_to_drop)
    _write_override(tmp_path, f"[selected]\nroles = {kept!r}\n")
    with pytest.raises(SquadsError) as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(exc_info.value)
    assert f"status {referring_status!r}" in message
    assert f"{role_to_drop!r} was dropped from a [selected] list (selected.roles)" in message


def test_a_directly_declared_missing_reference_is_not_annotated_with_selected_provenance(
    tmp_path: Path,
) -> None:
    """A status that was simply never declared (not dropped via selected) gets the plain
    referential-integrity message, with no provenance note tacked on — the note is only
    correct when a [selected] line actually caused the violation."""
    _write_override(
        tmp_path,
        """
[lifecycles.broken_lc]
initial = "NeverDeclared"
[lifecycles.broken_lc.transitions]
NeverDeclared = []

[items.chore]
prefix = "CHORE"
folder = "chores"
lifecycle = "broken_lc"
""",
    )
    with pytest.raises(SquadsError) as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(exc_info.value)
    assert "'NeverDeclared' not in status set" in message
    assert "was dropped from a [selected] list" not in message


# --------------------------------------------------------------------------- legacy is_meta
# shim


def test_override_type_with_is_meta_false_loads_and_resolves_to_work_category(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
is_meta = false
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.items["incident"].category == "work"


def test_override_type_omitting_is_meta_also_resolves_to_work_category(tmp_path: Path) -> None:
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
    assert spec.items["incident"].category == "work"


def test_override_type_with_is_meta_true_fails_closed_naming_category_and_roster(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
is_meta = true
""",
    )
    with pytest.raises(SquadsError, match="category") as exc_info:
        load_workflow_spec(squad_dir=tmp_path)
    assert "roster" in str(exc_info.value)


def test_an_unrelated_unknown_key_still_fails_via_extra_forbid(tmp_path: Path) -> None:
    """The shim pops only ``is_meta`` — any other unknown key still hard-fails."""
    _write_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
not_a_real_key = true
""",
    )
    with pytest.raises(SquadsError):
        load_workflow_spec(squad_dir=tmp_path)
