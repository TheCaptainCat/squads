"""Repo-hygiene gate: every override kind wires all five parts of the uniform severity
contract for a shadowing override — a manifest entry for its bundled counterpart, a state
classifier, a stamp-obligation finding, both diff deltas (Δ-mine, Δ-upgrade), and CLI
reachability for its ``scaffold``/``diff``/``update`` verbs.

In the shape of the routing guard that already exists
(``test_every_override_document_merges_through_the_shared_engine.py``), but driven rather than
structural: the first four elements are exercised against a real scratch squad through the
service-layer entry points every ``sq override`` command eventually calls (``scan_overrides``,
``check_override_issues``, ``diff_override``); the fifth is exercised one layer up, through the
actual CLI runner, because a kind can satisfy every one of those service entry points and still
be unreachable from the command line — the argument-parsing/routing layer above them is a
separate surface with its own per-kind branches, and nothing below it can see a gap in it.

Not hypothetical: the ``roles`` kind — the fifth override kind — has at various points had a
manifest entry, a state classifier and both diff deltas while missing a stamp-obligation
finding, and separately has had all four service-level parts while its CLI verbs fell through
to the ``template`` kind's branch and named the wrong kind in every error. Both gaps were
silent under a guard that either hand-enumerated the kind set or never looked past the service
layer.

The kind set itself is not hand-maintained: it is derived at run time from
``scan_overrides`` (see ``test_the_kind_set_is_derived_from_scan_overrides`` below), so a kind
wired into the service dispatchers and nowhere else is *seen* by this file by existing, not by
someone remembering to add a row.
"""

import inspect
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

import pytest

from squads import __version__
from squads._overrides import _service as override_service
from squads._overrides._manifest import (
    PLAYBOOK_KEY,
    ROLES_KEY,
    WORKFLOW_KEY,
    artifact_floor,
    template_key,
)
from squads._overrides._service import STATE_DRIFTED, OverrideEntry
from squads._overrides._stamp import stamp_template_file, stamp_toml_file

pytestmark = pytest.mark.anyio

#: An interior detail check_override_issues relies on -- the manifest module's own resolver. A
#: bogus key that resolves against no version is the "manifest entry" sabotage: no monkeypatch
#: needed, the fixture data itself can name a key the index has never carried.
_NO_SUCH_ARTIFACT_KEY = "_nonexistent/not/a/real/artifact.toml"


class _PlaceOverride(Protocol):
    def __call__(self, squad_dir: Path) -> None: ...


class _Restamper(Protocol):
    def __call__(self, path: Path, version: str) -> None: ...


@dataclass(frozen=True)
class _KindFixture:
    """Everything one override kind needs to drive the five-part check against a real squad."""

    manifest_key: str
    diff_name: str  # the `name` scan_overrides()/diff_override() know this override by
    display: str  # the shadowing override's own item path (check_override_issues() reporting)
    add_only_display: str  # the add-only override's own item path -- may equal `display` for a
    # single-file kind (workflow/playbook/roles, where add-only overwrites the same file) or
    # differ for a per-name kind (template/role, where add-only necessarily needs a name with
    # no bundled counterpart, so it is a different file from the shadowing fixture)
    place_shadowing: _PlaceOverride  # writes an unstamped override that redeclares a bundled key
    place_add_only: _PlaceOverride  # writes an unstamped override with no bundled counterpart
    restamp: _Restamper  # re-stamps the shadowing file in place (template vs TOML)
    cli_argv: list[str]  # argv tokens a human types after `sq override <verb>` for this kind --
    # the same tokens work for scaffold/diff/update alike (a positional name or a flag form),
    # which is itself why the five kinds need their own row: the forms are not uniform.


def _shadowing_path(squad_dir: Path, rel: str) -> Path:
    path = squad_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ─── template ───────────────────────────────────────────────────────────────────

_TEMPLATE_REL = "items/task.md.j2"


def _template_shadowing_content() -> str:
    return (
        "<!-- sq:body -->\nCUSTOM_UNIFORMITY_PROBE\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


def _place_template_shadowing(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, f".overrides/templates/{_TEMPLATE_REL}")
    path.write_text(_template_shadowing_content(), encoding="utf-8")


def _place_template_add_only(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, ".overrides/templates/custom/not_a_bundled_template.md.j2")
    path.write_text("hand-written content, no bundled counterpart", encoding="utf-8")


# ─── role (per-slug) ────────────────────────────────────────────────────────────

_ROLE_SLUG = "architect"


def _place_role_shadowing(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, f".overrides/roles/{_ROLE_SLUG}.toml")
    path.write_text('full_name = "Uniformity Probe"\n', encoding="utf-8")


def _place_role_add_only(squad_dir: Path) -> None:
    from squads._overrides._service import scaffold_new_role

    dest = scaffold_new_role(squad_dir, slug="uniformity-probe-role")
    # Unstamp: scaffold_new_role always stamps, and this fixture is testing the unstamped
    # add-only case specifically.
    text = dest.read_text(encoding="utf-8")
    dest.write_text(text.split("\n", 1)[1], encoding="utf-8")


# ─── workflow ───────────────────────────────────────────────────────────────────


def _place_workflow_shadowing(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, override_service.WORKFLOW_OVERRIDE_FILENAME)
    path.write_text('[items.task]\nfolder = "uniformity-probe-tickets"\n', encoding="utf-8")


def _place_workflow_add_only(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, override_service.WORKFLOW_OVERRIDE_FILENAME)
    path.write_text(
        '[items.uniformityprobe]\nprefix = "UPR"\nfolder = "uniformity-probes"\n'
        'lifecycle = "work"\n',
        encoding="utf-8",
    )


# ─── playbook ───────────────────────────────────────────────────────────────────


def _place_playbook_shadowing(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, override_service.PLAYBOOK_OVERRIDE_FILENAME)
    path.write_text('[types.task]\nroles = ["$(*self)"]\n', encoding="utf-8")


def _place_playbook_add_only(squad_dir: Path) -> None:
    """A wholly new type, unrelated to any bundled ``[types.*]`` key -- add-only regardless of
    whether the matching workflow item type exists (``check_override_issues`` never validates
    playbook/workflow coverage; that lives in the full ``svc.check()`` merge path, out of
    scope for this file-scan-level guard)."""
    path = _shadowing_path(squad_dir, override_service.PLAYBOOK_OVERRIDE_FILENAME)
    path.write_text(
        '[types.uniformityprobe]\noverview = "A probe."\nlifecycle = "Open -> Closed"\n'
        "commands = []\nroles = []\n",
        encoding="utf-8",
    )


# ─── roles catalog ──────────────────────────────────────────────────────────────


def _place_roles_catalog_shadowing(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, override_service.ROLES_OVERRIDE_FILENAME)
    path.write_text(
        '[[roles]]\nslug = "architect"\ntitle = "Uniformity Probe Architect"\n',
        encoding="utf-8",
    )


def _place_roles_catalog_add_only(squad_dir: Path) -> None:
    path = _shadowing_path(squad_dir, override_service.ROLES_OVERRIDE_FILENAME)
    path.write_text(
        '[[roles]]\nslug = "uniformity-probe-role"\nfull_name = "Sam Probe"\n'
        'title = "Uniformity Prober"\ndescription = "Exists to be new."\n'
        'mission = "Prove add-only stays silent."\n',
        encoding="utf-8",
    )


#: One row per registered override kind -- but the set of keys this dict must cover is not
#: chosen here, it is derived from ``scan_overrides`` at test time
#: (``test_the_kind_set_is_derived_from_scan_overrides``). A sixth kind wired into the service
#: dispatchers and missing a row here fails that test until the row is added; this dict only
#: supplies the per-kind fixture *mechanics* the derivation can't infer (how to place a
#: shadowing/add-only override, how to restamp it, what a human types on the command line).
_KIND_FIXTURES: dict[str, _KindFixture] = {
    "template": _KindFixture(
        manifest_key=template_key(_TEMPLATE_REL),
        diff_name=_TEMPLATE_REL,
        display=f".overrides/templates/{_TEMPLATE_REL}",
        add_only_display=".overrides/templates/custom/not_a_bundled_template.md.j2",
        place_shadowing=_place_template_shadowing,
        place_add_only=_place_template_add_only,
        restamp=stamp_template_file,
        cli_argv=[_TEMPLATE_REL],
    ),
    "role": _KindFixture(
        manifest_key=ROLES_KEY,
        diff_name=_ROLE_SLUG,
        display=f".overrides/roles/{_ROLE_SLUG}.toml",
        add_only_display=".overrides/roles/uniformity-probe-role.toml",
        place_shadowing=_place_role_shadowing,
        place_add_only=_place_role_add_only,
        restamp=stamp_toml_file,
        cli_argv=["--role", _ROLE_SLUG],
    ),
    "workflow": _KindFixture(
        manifest_key=WORKFLOW_KEY,
        diff_name="workflow",
        display=override_service.WORKFLOW_OVERRIDE_FILENAME,
        add_only_display=override_service.WORKFLOW_OVERRIDE_FILENAME,
        place_shadowing=_place_workflow_shadowing,
        place_add_only=_place_workflow_add_only,
        restamp=stamp_toml_file,
        cli_argv=["workflow"],
    ),
    "playbook": _KindFixture(
        manifest_key=PLAYBOOK_KEY,
        diff_name="playbook",
        display=override_service.PLAYBOOK_OVERRIDE_FILENAME,
        add_only_display=override_service.PLAYBOOK_OVERRIDE_FILENAME,
        place_shadowing=_place_playbook_shadowing,
        place_add_only=_place_playbook_add_only,
        restamp=stamp_toml_file,
        cli_argv=["playbook"],
    ),
    "roles": _KindFixture(
        manifest_key=ROLES_KEY,
        diff_name="roles",
        display=override_service.ROLES_OVERRIDE_FILENAME,
        add_only_display=override_service.ROLES_OVERRIDE_FILENAME,
        place_shadowing=_place_roles_catalog_shadowing,
        place_add_only=_place_roles_catalog_add_only,
        restamp=stamp_toml_file,
        cli_argv=["roles"],
    ),
}


def _path_for_display(squad_dir: Path, display: str) -> Path:
    return squad_dir / display


async def _cli_scaffold_gap(
    kind: str, fixture: _KindFixture, squad_dir: Path, invoke
) -> str | None:
    """Drives ``sq override scaffold <cli_argv>`` and checks the *scanned* entry it produced
    resolves to *kind* -- a bare exit code is not enough (a mis-routed verb can still exit 0
    by falling through to a *different* specific kind's branch rather than the catch-all)."""
    scaffolded = await invoke(["override", "scaffold", *fixture.cli_argv, "--force"])
    if scaffolded.exit_code != 0:
        detail = scaffolded.output.strip()
        return f"CLI reachability (scaffold exited {scaffolded.exit_code}: {detail!r})"
    entries = {e.name: e for e in override_service.scan_overrides(squad_dir)}
    entry = entries.get(fixture.diff_name)
    if entry is not None and entry.kind == kind:
        return None
    resolved = entry.kind if entry is not None else "(no scanned entry)"
    return f"CLI reachability (scaffold resolved kind={resolved!r}, expected {kind!r})"


async def _cli_diff_gap(kind: str, fixture: _KindFixture, invoke) -> str | None:
    """Drives ``sq override diff <cli_argv>`` and checks the printed ``(kind: ...)`` line
    names *kind* itself, not another kind's branch."""
    diffed = await invoke(["override", "diff", *fixture.cli_argv])
    if diffed.exit_code != 0:
        return f"CLI reachability (diff exited {diffed.exit_code}: {diffed.output.strip()!r})"
    if f"(kind: {kind})" in diffed.output:
        return None
    return f"CLI reachability (diff did not report kind={kind!r}): {diffed.output.strip()!r}"


async def _cli_update_gap(kind: str, fixture: _KindFixture, squad_dir: Path, invoke) -> str | None:
    """Drives ``sq override update <cli_argv>`` and checks the on-disk file at *kind*'s own
    path actually got re-stamped -- a mis-routed update that raises is caught by the exit code
    above; one that silently no-ops on the wrong file is caught by the stamp staying stale."""
    updated = await invoke(["override", "update", *fixture.cli_argv])
    if updated.exit_code != 0:
        detail = updated.output.strip()
        return f"CLI reachability (update exited {updated.exit_code}: {detail!r})"
    entries = {e.name: e for e in override_service.scan_overrides(squad_dir)}
    restamped = entries.get(fixture.diff_name)
    if restamped is not None and restamped.base_version == __version__:
        return None
    return f"CLI reachability (update did not re-stamp {fixture.diff_name!r} to {__version__!r})"


async def _cli_reachability_gap(
    kind: str, fixture: _KindFixture, squad_dir: Path, invoke
) -> str | None:
    """``None`` when *kind*'s ``scaffold``/``diff``/``update`` verbs are all reachable through
    the CLI runner by the argument form a human types (``fixture.cli_argv``) and each resolves
    to *kind* itself; otherwise a short string naming which verb misbehaved and how."""
    return (
        await _cli_scaffold_gap(kind, fixture, squad_dir, invoke)
        or await _cli_diff_gap(kind, fixture, invoke)
        or await _cli_update_gap(kind, fixture, squad_dir, invoke)
    )


async def _uniformity_gaps(kind: str, fixture: _KindFixture, squad_dir: Path, invoke) -> list[str]:
    """Everything wrong with *kind*'s wiring, driven against *squad_dir* -- empty when every
    one of the five parts is present. Elements 1-4 go through the service-layer dispatch every
    ``sq override`` command eventually calls (``override_service.scan_overrides`` /
    ``.check_override_issues`` / ``.diff_override``), called through the module object rather
    than an imported name, so the removal tests below can monkeypatch the dispatcher itself and
    have this function see it. Element 5 (CLI reachability) drives the actual CLI runner instead
    -- the routing layer above those service entry points, and the one where a kind can pass
    every service-level check while still being unreachable by anything a human would type.
    """
    gaps: list[str] = []

    # 1. Manifest entry.
    if artifact_floor(fixture.manifest_key) is None:
        gaps.append("manifest entry")

    # 2. State classifier + 3. stamp-obligation finding (shadowing, unstamped -> error).
    fixture.place_shadowing(squad_dir)
    entries = {e.name: e for e in override_service.scan_overrides(squad_dir)}
    entry = entries.get(fixture.diff_name)
    if entry is None or entry.state != STATE_DRIFTED:
        gaps.append("state classifier")

    issues = override_service.check_override_issues(squad_dir)
    shadow_errors = [i for i in issues if i[0] == "error" and i[1] == fixture.display]
    if not shadow_errors:
        gaps.append("stamp-obligation finding (shadowing must error)")

    # 3b. Add-only, unstamped -> silent (the other half of the same finding).
    fixture.place_add_only(squad_dir)
    add_only_issues = override_service.check_override_issues(squad_dir)
    if any(i[1] == fixture.add_only_display for i in add_only_issues):
        gaps.append("stamp-obligation finding (add-only must stay silent)")

    # 4. Δ-mine + 5. Δ-upgrade -- re-place the shadowing content (differs from bundled) and
    # walk it through both a same-version stamp (real Δ-mine, empty Δ-upgrade) and an ancient,
    # uncarried-base stamp (empty Δ-mine is impossible to assert content-free here, but
    # Δ-upgrade must turn non-empty -- the "predates squads' own provenance" explanatory pane
    # every kind's own diff already emits for this shape).
    fixture.place_shadowing(squad_dir)
    path = _path_for_display(squad_dir, fixture.display)
    fixture.restamp(path, __version__)
    try:
        same_version = override_service.diff_override(squad_dir, fixture.diff_name, kind)
    except Exception:
        gaps.append("delta-mine")
        gaps.append("delta-upgrade")
    else:
        if not same_version.delta_mine:
            gaps.append("delta-mine")
        if same_version.delta_upgrade != "":
            gaps.append("delta-upgrade")

        fixture.restamp(path, "0.1.0")
        ancient = override_service.diff_override(squad_dir, fixture.diff_name, kind)
        if not ancient.delta_upgrade:
            gaps.append("delta-upgrade")

    # 5. CLI reachability -- the layer above every check so far, and the one where `roles`
    # actually shipped unreachable while every check above it passed.
    cli_gap = await _cli_reachability_gap(kind, fixture, squad_dir, invoke)
    if cli_gap is not None:
        gaps.append(cli_gap)

    return gaps


async def test_every_registered_kind_wires_all_five_parts(project, invoke) -> None:
    squad_dir = project.squad_dir
    gaps_by_kind = {
        kind: gaps
        for kind, fixture in sorted(_KIND_FIXTURES.items())
        if (gaps := await _uniformity_gaps(kind, fixture, squad_dir, invoke))
    }
    assert not gaps_by_kind, f"override kind wiring gaps (kind -> missing part): {gaps_by_kind}"


# ─── The registry itself stays honest ────────────────────────────────────────────


async def test_the_kind_set_is_derived_from_scan_overrides(project, invoke) -> None:
    """The kind set this file must cover is not a second hand-written list -- it is read back
    from ``scan_overrides`` itself, against a squad carrying one override of every kind. A kind
    wired into ``scan_overrides`` (i.e. an override kind at all) with no row in
    ``_KIND_FIXTURES`` is wired into the service and nowhere else covered by this file; a row
    with no matching scanned entry means that fixture's placement no longer produces a
    scannable override. Either way the mismatch names which side is wrong, not just that they
    differ."""
    squad_dir = project.squad_dir
    for fixture in _KIND_FIXTURES.values():
        fixture.place_shadowing(squad_dir)

    scanned_kinds = {entry.kind for entry in override_service.scan_overrides(squad_dir)}
    fixture_kinds = set(_KIND_FIXTURES)

    wired_but_uncovered = scanned_kinds - fixture_kinds
    covered_but_unscanned = fixture_kinds - scanned_kinds
    assert not wired_but_uncovered and not covered_but_unscanned, (
        f"scan_overrides reports kinds {sorted(scanned_kinds)}, _KIND_FIXTURES covers "
        f"{sorted(fixture_kinds)} -- wired into scan_overrides with no fixture row: "
        f"{sorted(wired_but_uncovered) or 'none'}; fixture row whose placement scan_overrides "
        f"no longer sees: {sorted(covered_but_unscanned) or 'none'}"
    )


def test_the_registry_covers_every_kind_the_docstring_names() -> None:
    """A documentation-accuracy check, not the registry (the kind set above is derived, not
    pinned here): ``OverrideEntry.kind``'s docstring comment (the ``name``/``kind`` field
    comments directly above ``kind: str``) is prose naming the same five kinds, and prose goes
    stale silently -- this keeps it matching the derived set so a kind added to the code and
    left undocumented there is caught."""
    source = inspect.getsource(OverrideEntry)
    comment_block = source.split("kind: str")[0]
    named_in_docstring = set(re.findall(r'"([a-z-]+)"', comment_block))
    assert named_in_docstring == set(_KIND_FIXTURES), (
        f"OverrideEntry.kind's docstring names {sorted(named_in_docstring)} but the derived "
        f"kind set covers {sorted(_KIND_FIXTURES)} -- keep the docstring's prose in lockstep "
        f"with the actual kinds"
    )


# ─── Verified by removal: sabotage each of the five, one at a time ──────────────


async def test_removing_the_manifest_entry_is_caught(project, invoke) -> None:
    broken = replace(_KIND_FIXTURES["roles"], manifest_key=_NO_SUCH_ARTIFACT_KEY)
    gaps = await _uniformity_gaps("roles", broken, project.squad_dir, invoke)
    assert "manifest entry" in gaps


@pytest.mark.parametrize("kind", sorted(_KIND_FIXTURES))
async def test_removing_the_state_classifier_is_caught(project, monkeypatch, invoke, kind) -> None:
    fixture = _KIND_FIXTURES[kind]
    real_scan = override_service.scan_overrides

    def sabotaged_scan(squad_dir: Path) -> list[OverrideEntry]:
        return [
            replace(e, state=override_service.STATE_CURRENT) if e.name == fixture.diff_name else e
            for e in real_scan(squad_dir)
        ]

    monkeypatch.setattr(override_service, "scan_overrides", sabotaged_scan)
    gaps = await _uniformity_gaps(kind, fixture, project.squad_dir, invoke)
    assert "state classifier" in gaps, f"{kind}: sabotaged state classifier went undetected"


@pytest.mark.parametrize("kind", sorted(_KIND_FIXTURES))
async def test_removing_the_stamp_obligation_finding_is_caught(
    project, monkeypatch, invoke, kind
) -> None:
    fixture = _KIND_FIXTURES[kind]
    real_check = override_service.check_override_issues

    def sabotaged_check(squad_dir: Path, role_items_by_slug=None):
        return [i for i in real_check(squad_dir, role_items_by_slug) if i[1] != fixture.display]

    monkeypatch.setattr(override_service, "check_override_issues", sabotaged_check)
    gaps = await _uniformity_gaps(kind, fixture, project.squad_dir, invoke)
    assert "stamp-obligation finding (shadowing must error)" in gaps, (
        f"{kind}: sabotaged stamp-obligation finding went undetected"
    )


@pytest.mark.parametrize("kind", sorted(_KIND_FIXTURES))
async def test_removing_delta_mine_is_caught(project, monkeypatch, invoke, kind) -> None:
    fixture = _KIND_FIXTURES[kind]
    real_diff = override_service.diff_override

    def sabotaged_diff(squad_dir: Path, name: str, diff_kind: str):
        result = real_diff(squad_dir, name, diff_kind)
        if diff_kind == kind:
            return replace(result, delta_mine="")
        return result

    monkeypatch.setattr(override_service, "diff_override", sabotaged_diff)
    gaps = await _uniformity_gaps(kind, fixture, project.squad_dir, invoke)
    assert "delta-mine" in gaps, f"{kind}: sabotaged Δ-mine went undetected"


@pytest.mark.parametrize("kind", sorted(_KIND_FIXTURES))
async def test_removing_delta_upgrade_is_caught(project, monkeypatch, invoke, kind) -> None:
    fixture = _KIND_FIXTURES[kind]
    real_diff = override_service.diff_override

    def sabotaged_diff(squad_dir: Path, name: str, diff_kind: str):
        result = real_diff(squad_dir, name, diff_kind)
        if diff_kind == kind:
            return replace(result, delta_upgrade="")
        return result

    monkeypatch.setattr(override_service, "diff_override", sabotaged_diff)
    gaps = await _uniformity_gaps(kind, fixture, project.squad_dir, invoke)
    assert "delta-upgrade" in gaps, f"{kind}: sabotaged Δ-upgrade went undetected"
