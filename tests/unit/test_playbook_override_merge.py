"""``.overrides/playbook.toml`` merges over the bundled playbook via the shared engine, threaded
against the (possibly workflow-overridden) active spec: the one-line append idiom
(``roles = ["$(*self)", {...}]``) adds a role's guidance to a type without restating its other
bundled guides, a hand-written field shadows one field of one bundled guide leaving the rest
intact, coverage validates against the *active* spec (never the bundled one), and there is no
independent deselect for this document — dropping a type's coverage requirement is a consequence
of a workflow override, never a ``[selected]`` declaration of its own.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._roles._catalog import get_catalog
from squads._workflow import load_workflow_spec


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(content, encoding="utf-8")


def _write_workflow_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _bundled() -> object:
    return load_playbook(get_catalog())


# --------------------------------------------------------------------------- no override: byte
# identity against the bundled golden


def test_no_override_file_returns_a_playbook_identical_to_the_bundled_one(tmp_path: Path) -> None:
    bundled = load_playbook(get_catalog())
    merged = load_playbook(get_catalog(), squad_dir=tmp_path)
    assert merged.model_dump(mode="json") == bundled.model_dump(mode="json")


def test_no_override_file_is_identical_even_when_squad_dir_exists_but_empty(
    tmp_path: Path,
) -> None:
    (tmp_path / ".overrides").mkdir()
    bundled = load_playbook(get_catalog())
    merged = load_playbook(get_catalog(), squad_dir=tmp_path)
    assert merged.model_dump(mode="json") == bundled.model_dump(mode="json")


# --------------------------------------------------------------------------- the one-line
# append idiom — driven off a REAL parsed inline-array override, not a hand-built dict


def test_one_line_append_adds_a_role_guide_and_leaves_the_others_untouched(
    tmp_path: Path,
) -> None:
    bundled = load_playbook(get_catalog())
    bundled_task_role_slugs = {g.slug for g in bundled.types["task"].roles}
    assert "architect" not in bundled_task_role_slugs  # precondition: no bundled task guide

    _write_playbook_override(
        tmp_path,
        """
[types.task]
roles = [
    "$(*self)",
    { slug = "architect", enter = ["read the task body"], do = ["verify the fix"] },
]
""",
    )
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)

    merged_slugs = [g.slug for g in merged.types["task"].roles]
    # every bundled guide survives, in order, with a new one appended
    assert merged_slugs == [*[g.slug for g in bundled.types["task"].roles], "architect"]
    new_guide = merged.types["task"].roles[-1]
    assert new_guide.enter == ["read the task body"]
    assert new_guide.do == ["verify the fix"]

    # a later bundled improvement to task's OTHER guides flows through untouched: every
    # bundled guide's fields are byte-identical to the bundled document's own copy.
    for bundled_guide, merged_guide in zip(
        bundled.types["task"].roles, merged.types["task"].roles, strict=False
    ):
        assert merged_guide == bundled_guide


def test_appending_to_one_type_leaves_every_other_types_entry_untouched(tmp_path: Path) -> None:
    bundled = load_playbook(get_catalog())
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = ["$(*self)", { slug = "architect" }]\n',
    )
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    for item_type in bundled.types:
        if item_type == "task":
            continue
        assert merged.types[item_type] == bundled.types[item_type]


# --------------------------------------------------------------------------- shadowing one
# field of one bundled guide leaves that guide's other fields intact


def _guide_toml(
    slug: str, enter: list[str], do: list[str], handoff: list[str], watch: list[str]
) -> str:
    return (
        f"{{ slug = {slug!r}, enter = {enter!r}, do = {do!r}, "
        f"handoff = {handoff!r}, watch = {watch!r} }}"
    )


def test_shadowing_one_field_of_a_bundled_role_guide_leaves_its_other_fields_intact(
    tmp_path: Path,
) -> None:
    """``roles`` is a plain array — a leaf the engine never element-merges (``_specmerge``'s
    own docstring) — so there is no per-index splice into ONE existing entry: shadowing one
    field of one bundled guide is ordinary TOML authoring over the WHOLE array, restating every
    guide with the one being changed carrying every OTHER field copied verbatim (the shape an
    adopter reading the bundled document/`sq override diff playbook` would produce by hand).
    This proves the field survives the round trip once copied, never that the engine infers
    it — there is no mechanism at this granularity that could."""
    bundled = load_playbook(get_catalog())
    guides = bundled.types["task"].roles
    target = guides[0]
    restated = [
        _guide_toml(target.slug, target.enter, target.do, target.handoff, ["a new watch line"]),
        *(_guide_toml(g.slug, g.enter, g.do, g.handoff, g.watch) for g in guides[1:]),
    ]
    _write_playbook_override(tmp_path, f"[types.task]\nroles = [{', '.join(restated)}]\n")
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    merged_guide = merged.types["task"].roles[0]
    assert merged_guide.slug == target.slug
    assert merged_guide.watch == ["a new watch line"]
    # every OTHER field of that same guide survives untouched — copied verbatim, not inherited
    # by any engine magic (there is none at this granularity).
    assert merged_guide.enter == target.enter
    assert merged_guide.do == target.do
    assert merged_guide.handoff == target.handoff
    # every OTHER guide is byte-identical to its bundled counterpart.
    assert merged.types["task"].roles[1:] == guides[1:]


def test_shadowing_via_the_append_idiom_targets_only_the_named_field_of_the_spliced_copy(
    tmp_path: Path,
) -> None:
    """The append idiom splices in a full COPY of each bundled guide (via ``$(*self)``); a
    hand-written table appended alongside it is a wholly separate, new entry — not a
    field-level shadow of any spliced one. This is the shape an adopter reaches for to ADD a
    role, contrasted with the previous test's shape for MODIFYING an existing one."""
    bundled = load_playbook(get_catalog())
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = ["$(*self)", { slug = "architect", watch = ["new"] }]\n',
    )
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert len(merged.types["task"].roles) == len(bundled.types["task"].roles) + 1
    assert merged.types["task"].roles[-1].watch == ["new"]


# --------------------------------------------------------------------------- coverage
# validates against the ACTIVE spec, never the bundled one


def test_an_override_entry_for_a_project_declared_type_validates(tmp_path: Path) -> None:
    _write_workflow_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
""",
    )
    _write_playbook_override(
        tmp_path,
        """
[types.incident]
overview = "An incident."
lifecycle = "Draft -> Active -> Archived"
commands = ["sq create incident \\"...\\" --author qa"]
roles = [{ slug = "qa" }]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert "incident" in merged.types
    assert merged.types["incident"].overview == "An incident."


def test_a_project_declared_type_with_no_playbook_entry_is_not_a_coverage_violation(
    tmp_path: Path,
) -> None:
    """The "missing" coverage direction is scoped to BUNDLED type names only — a
    project-declared type with no playbook entry at all is not an error; it is the existing,
    sanctioned thin-skill fallback every custom type already gets (predates this feature).
    Requiring an entry for every project-declared type would turn "add a custom type via a
    workflow override" — legal on its own — into a hard failure unless a playbook override is
    ALSO written, which would break that unrelated, already-shipped capability."""
    _write_workflow_override(
        tmp_path,
        """
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert "incident" not in merged.types


def test_a_bundled_type_missing_its_own_entry_is_still_a_coverage_violation() -> None:
    """The maintainer safety net the "missing" direction preserves: a BUNDLED type absent
    from the (still bundled-spec-active) types dict is still refused — this is what protects
    the shipped ``playbook.toml`` from an incomplete edit; only a PROJECT-declared type's
    absence is ever tolerated (see the sibling test above)."""
    from squads._interactions._loader import _check_coverage

    bundled = load_playbook(get_catalog())
    spec = load_workflow_spec()
    incomplete = dict(bundled.types)
    del incomplete["task"]
    errors: list[str] = []
    _check_coverage(incomplete, spec, errors)
    assert any("missing required work-type entry: 'task'" in e for e in errors)


def test_dropping_a_type_via_workflow_override_drops_its_playbook_coverage_requirement(
    tmp_path: Path,
) -> None:
    """No independent deselect for the playbook: dropping a type from the workflow spec's
    active set drops its playbook-coverage requirement as a CONSEQUENCE, with no ``[selected]``
    key of the playbook's own — proven with NO playbook override file present at all, and no
    coverage false positive (the bundled document's own stale entry for the dropped type would
    otherwise read as an "extra" entry the merged spec no longer recognises — see
    :func:`~squads._interactions._loader._base_raw_for`, which is exactly what stops that)."""
    bundled_wf = load_workflow_spec()
    kept = sorted(t for t in bundled_wf.items if t != "guide")
    _write_workflow_override(tmp_path, f"[selected]\nitems = {kept!r}\n")
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items

    # no .overrides/playbook.toml at all — loads clean, with the dropped type's entry gone
    # from the merged playbook too (never required, never present as a stray "extra").
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    bundled_pb = _bundled()
    assert "guide" not in merged.types
    assert set(merged.types) == set(bundled_pb.types) - {"guide"}  # type: ignore[attr-defined]
    # every surviving type's entry is otherwise untouched.
    for t in merged.types:
        assert merged.types[t] == bundled_pb.types[t]  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- no independent
# deselect: a [selected] table on this document is refused, not silently accepted


def test_a_selected_table_on_the_playbook_override_is_refused(tmp_path: Path) -> None:
    _write_playbook_override(tmp_path, '[selected]\ntypes = ["task"]\n')
    spec = load_workflow_spec()
    with pytest.raises(SquadsError, match="unknown \\[selected\\] section 'types'"):
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)


def test_the_selected_refusal_names_the_real_reason_not_an_empty_menu(tmp_path: Path) -> None:
    """The generic merge-engine message ("use one of the accepted [selected] sections: []")
    offers an empty menu, since this document has no deselectable sections at all — the
    playbook loader supplies its own reason instead."""
    _write_playbook_override(tmp_path, '[selected]\ntypes = ["task"]\n')
    spec = load_workflow_spec()
    with pytest.raises(SquadsError) as exc_info:
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    message = str(exc_info.value)
    assert "accepted [selected] sections: []" not in message
    assert "no [selected] sections to deselect" in message
    assert "coverage" in message  # names the actual reason (derived, not declared)


# --------------------------------------------------------------------------- fail-closed shape


def test_malformed_toml_raises_naming_the_override_file(tmp_path: Path) -> None:
    _write_playbook_override(tmp_path, "[types.broken\nthis is not valid toml ===")
    with pytest.raises(SquadsError, match="Malformed playbook override"):
        load_playbook(get_catalog(), squad_dir=tmp_path)


def test_an_unknown_top_level_key_fails_closed(tmp_path: Path) -> None:
    _write_playbook_override(tmp_path, '[bogus_section.task]\noverview = "x"\n')
    with pytest.raises(SquadsError, match="unknown top-level key 'bogus_section'"):
        load_playbook(get_catalog(), squad_dir=tmp_path)


def test_a_stray_role_slug_not_in_the_catalog_fails_closed(tmp_path: Path) -> None:
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = ["$(*self)", { slug = "no-such-role" }]\n',
    )
    spec = load_workflow_spec()
    with pytest.raises(SquadsError, match="role slug 'no-such-role' not in role catalog"):
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)


def test_the_dev_sentinel_role_slug_is_exempt_from_catalog_validation(tmp_path: Path) -> None:
    # "epic" has no bundled "*dev" guide (unlike "task"), so appending one here exercises the
    # DEV-exemption without also tripping the (separate) duplicate-slug refusal.
    _write_playbook_override(
        tmp_path,
        '[types.epic]\nroles = ["$(*self)", { slug = "*dev" }]\n',
    )
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert merged.types["epic"].roles[-1].slug == "*dev"


def test_a_typo_field_on_a_role_guide_table_raises_via_extra_forbid(tmp_path: Path) -> None:
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = ["$(*self)", { slug = "qa", doo = ["typo"] }]\n',
    )
    spec = load_workflow_spec()
    with pytest.raises(SquadsError):
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
