"""Migration corpus: one frozen squad per released schema version, migrated to current and
checked clean via both the service call and the real CLI. Never hand-edit the fixtures."""

import re
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._index._resolver import item_file
from squads._interactions import is_system_skill
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._models._metadata import RETIRED_ROLE_EXTRA_KEYS
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._sections import find_markers, get_section, has_section, replace_section
from squads._services._service import Service
from squads._views import place_view_tags, roster_body_view_name
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL, load_workflow_spec

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

#: The role ``extra`` keys the sweep removes — the shared declaration the refusals also read,
#: plus ``model``, which is retired for a bundled role and kept for a developer and so is a
#: question about a role's shape rather than one that declaration answers.
_RETIRED_MIRROR_KEYS: frozenset[str] = RETIRED_ROLE_EXTRA_KEYS | {X.MODEL}

_CORPUS_CASES: list[tuple[str, str]] = [
    ("0.1", "v0_1"),
    ("0.2", "v0_2"),
    ("0.3", "v0_3"),
    ("0.4", "v0_4"),
    ("0.5", "v0_5"),
    ("0.7", "v0_7"),
    ("0.8", "v0_8"),
    ("0.10", "v0_10"),
    ("0.11", "v0_11"),
    ("0.14", "v0_14"),
    ("0.15", "v0_15"),
]


def _load_paths(squad_dir: Path) -> SquadPaths:
    import tomllib

    with (squad_dir / ".squads.toml").open("rb") as fh:
        cfg_data = tomllib.load(fh)
    cfg = SquadsConfig.from_toml_dict(cfg_data)
    resolved = squad_dir / cfg.squad_dir
    return SquadPaths(root=squad_dir, squad_dir=resolved, config=cfg)


async def _expected_seeded_view_gap_files(svc: Service, skipped_ids: set[str]) -> set[str]:
    """Filenames a fixture's own reclaim skip set (*skipped_ids*) is known to still lack its
    required view tag on after migrating, verified against the file's actual on-disk body."""
    skipped_seqs = {int(sid.rsplit("-", 1)[-1]) for sid in skipped_ids}
    db = await svc.store.load()
    expected: set[str] = set()
    for it in db.items.values():
        if it.type not in (ROSTER_ROLE, ROSTER_SKILL):
            continue
        if it.sequence_id not in skipped_seqs:
            continue
        slug = it.extra.get(X.SLUG, it.slug) if it.type == ROSTER_SKILL else it.slug
        view_name = roster_body_view_name(it.type, slug, svc.spec)
        if view_name is None:
            continue
        path = item_file(svc.paths, it)
        text = path.read_text(encoding="utf-8")
        tag_names = {
            parts.name for raw in find_markers(text) if (parts := markers.view_tag_parts(raw))
        }
        if view_name not in tag_names:
            expected.add(path.name)
    return expected


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_corpus_migrates_to_current_schema_and_passes_check(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    src = _CORPUS_DIR / corpus_name
    assert src.is_dir(), f"corpus fixture {corpus_name!r} not found at {src}"
    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)

    paths = _load_paths(dst)
    svc = Service(paths)
    run = await svc.run_pending_migrations()
    applied = run.applied

    import tomllib

    with (dst / ".squads.toml").open("rb") as fh:
        final_cfg = tomllib.load(fh)
    assert final_cfg["schema_version"] == SCHEMA_VERSION, (
        f"corpus {corpus_name!r} did not reach schema {SCHEMA_VERSION!r}; "
        f"applied: {[m.version for m in applied]}"
    )

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    expected_gaps = await _expected_seeded_view_gap_files(svc, set(run.skipped.get("0.15", [])))
    unexpected = [
        i
        for i in errors
        if not ("missing seeded view tag" in i.message and i.item in expected_gaps)
    ]
    assert not unexpected, (
        f"sq check produced errors after migrating {corpus_name!r} from {schema_label!r}:\n"
        + "\n".join(f"  [{i.level}] {i.item}: {i.message}" for i in unexpected)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
def test_corpus_cli_migrate_up_and_check_both_exit_clean(
    schema_label: str, corpus_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _CORPUS_DIR / corpus_name

    import asyncio

    async def _probe() -> set[str]:
        probe_dst = tmp_path / f"{corpus_name}-probe"
        shutil.copytree(src, probe_dst)
        probe_svc = Service(_load_paths(probe_dst))
        probe_run = await probe_svc.run_pending_migrations()
        return await _expected_seeded_view_gap_files(
            probe_svc, set(probe_run.skipped.get("0.15", []))
        )

    expected_gaps = asyncio.run(_probe())

    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)
    monkeypatch.chdir(dst)
    runner = CliRunner()

    migrate_result = runner.invoke(app, ["migrate", "up"])
    assert migrate_result.exit_code == 0, (
        f"sq migrate up failed on {corpus_name!r} ({schema_label!r}):\n{migrate_result.output}"
    )

    check_result = runner.invoke(app, ["check", "--json"])
    import json

    json_start = check_result.output.index("[")
    check_payload = json.loads(check_result.output[json_start:])
    unexpected = [
        i
        for i in check_payload
        if i["level"] == "error"
        and not ("missing seeded view tag" in i["message"] and i["item"] in expected_gaps)
    ]
    assert not unexpected, (
        f"sq check reported unexpected error(s) after migrating {corpus_name!r} "
        f"({schema_label!r}):\n" + "\n".join(f"  {i}" for i in unexpected)
    )
    if expected_gaps:
        assert check_result.exit_code == 3, check_result.output
    else:
        assert check_result.exit_code == 0, check_result.output


def test_migrate_up_announces_the_content_it_rewrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``sq migrate up`` announces a stripped-region rewrite, verified against real file diffs."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    squad_dir = _load_paths(dst).squad_dir
    before = {path: path.read_bytes() for path in _md_files(squad_dir)}
    monkeypatch.chdir(dst)

    result = CliRunner().invoke(app, ["migrate", "up"])

    assert result.exit_code == 0, result.output
    rewritten = [
        path
        for path in _md_files(squad_dir)
        if path in before and path.read_bytes() != before[path]
    ]
    assert rewritten, "precondition: this migration rewrote no item file's content"
    match = re.search(
        r"stripped retired regions from (\d+) item files? — review the diff", result.output
    )
    assert match, f"the content rewrite went unannounced:\n{result.output}"
    assert int(match.group(1)) > 0


async def test_v0_2_migration_rewrites_the_legacy_backend_key(tmp_path: Path) -> None:
    """The legacy `default_backend` key migrates to `active_backends`."""
    import tomllib

    src = _CORPUS_DIR / "v0_2"
    dst = tmp_path / "v0_2"
    shutil.copytree(src, dst)

    with (dst / ".squads.toml").open("rb") as fh:
        pre = tomllib.load(fh)
    assert "default_backend" in pre and "active_backends" not in pre  # precondition

    paths = _load_paths(dst)
    svc = Service(paths)
    await svc.run_pending_migrations()

    with (dst / ".squads.toml").open("rb") as fh:
        post = tomllib.load(fh)
    assert "active_backends" in post and "default_backend" not in post
    assert post["active_backends"] == ["claude_code"]


async def test_the_v0_14_fixtures_milestone_gains_its_roll_up_tag_across_the_chain(
    tmp_path: Path,
) -> None:
    """A milestone predating the roll-up tag gains it across the migration chain."""
    dst = tmp_path / "v0_14"
    shutil.copytree(_CORPUS_DIR / "v0_14", dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    await svc.run_pending_migrations()

    mile_files = sorted((paths.squad_dir / "milestones").glob("*.md"))
    assert mile_files, (
        "the v0_14 fixture carries no milestone for this migration to prove the write on"
    )
    tag = markers.open_marker(markers.view_tag("milestone_rollup"))
    for path in mile_files:
        assert tag in path.read_text(encoding="utf-8"), f"{path.name}: the roll-up tag is missing"


def _md_files(squad_dir: Path) -> list[Path]:
    return sorted(p for p in squad_dir.rglob("*.md") if p.is_file())


def _body_region(text: str) -> str | None:
    return get_section(text, markers.BODY)


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_corpus_carries_no_retired_region_after_migrating(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Migrating a frozen corpus to current leaves none of the retired regions behind."""
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)

    await svc.run_pending_migrations()

    carried = [
        path
        for path in _md_files(paths.squad_dir)
        if has_section(path.read_text(encoding="utf-8"), markers.SUMMARY)
        or ":head -->" in path.read_text(encoding="utf-8")
    ]
    assert not carried, (
        f"retired regions survived migrating {corpus_name!r} from {schema_label!r}: "
        + ", ".join(p.name for p in carried)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_every_template_owned_skills_stored_body_converges_onto_its_tag(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Every template-owned skill's stored body converges onto its own placement tag, unless
    the reclaim step's own skip condition left it unchanged instead."""
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    before = {
        path.name: _body_region(path.read_text(encoding="utf-8"))
        for path in _md_files(paths.squad_dir)
    }

    run = await svc.run_pending_migrations()
    applied = run.applied
    if not applied:
        pytest.skip(f"{corpus_name!r} is already at the current stamp; no rebuild runs")
    skipped_seqs = {int(sid.rsplit("-", 1)[-1]) for sid in run.skipped.get("0.15", [])}

    skills = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_SKILL]
    template_owned = [
        it for it in skills if is_system_skill(it.extra.get(X.SLUG, it.slug), svc.spec)
    ]
    assert template_owned, f"{corpus_name!r} carries no template-owned skill to assert on"
    stored = {
        it.id: (it, item_file(paths, it), before[item_file(paths, it).name])
        for it in template_owned
        if (before.get(item_file(paths, it).name) or "").strip()
    }
    if not stored:
        pytest.skip(f"{corpus_name!r} stores no template-owned skill body for the sweep to reach")
    converged = 0
    skew_skipped = 0
    for it, path, was in stored.values():
        text = path.read_text(encoding="utf-8")
        assert has_section(text, markers.BODY), f"{it.id}: the body markers were deleted"
        slug = it.extra.get(X.SLUG, it.slug)
        view_name = roster_body_view_name(it.type, slug, svc.spec)
        region = (_body_region(text) or "").strip()
        if view_name is not None and it.sequence_id not in skipped_seqs:
            assert region == markers.open_marker(markers.view_tag(view_name)), (
                f"{it.id}: the {slug!r} skill body did not converge onto its tag"
            )
            converged += 1
        else:
            assert region == (was or "").strip(), f"{it.id}: the stored body was rewritten"
            if view_name is not None:
                skew_skipped += 1
    assert converged or skew_skipped, (
        f"{corpus_name!r} carries no template-owned skill to assert on"
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_a_role_keeps_its_record_and_loses_its_mirror_across_the_migration(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Every migrated role keeps its title/description record and loses the ``extra`` mirror
    of its definition, replaced by the ``role_definition`` placement tag its body converges
    onto (unless the reclaim step's own skip condition left the body untouched)."""
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    before_text = {
        path.name: path.read_text(encoding="utf-8") for path in _md_files(paths.squad_dir)
    }
    before = {name: read_frontmatter(text=text, source=name) for name, text in before_text.items()}

    run = await svc.run_pending_migrations()
    applied = run.applied
    if not applied:
        pytest.skip(f"{corpus_name!r} is already at the current stamp; no migration runs")
    skipped_seqs = {int(sid.rsplit("-", 1)[-1]) for sid in run.skipped.get("0.15", [])}

    roles = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_ROLE]
    assert roles, f"{corpus_name!r} carries no role item to assert on"
    for item in roles:
        path = item_file(paths, item)
        text = path.read_text(encoding="utf-8")
        stored = read_frontmatter(text=text, source=str(path)).get("extra", {})
        was = before[path.name]
        assert set(was.get("extra", {})) & _RETIRED_MIRROR_KEYS
        assert has_section(text, markers.BODY), f"{item.id}: the body markers were deleted"
        assert set(stored) & _RETIRED_MIRROR_KEYS == set(), f"{item.id}: the mirror survived"
        assert stored.get(X.SLUG), f"{item.id}: the dispatch identity was stripped with it"
        body = (get_section(text, markers.BODY) or "").strip()
        if item.sequence_id in skipped_seqs:
            was_body = (get_section(before_text[path.name], markers.BODY) or "").strip()
            assert body == was_body, f"{item.id}: a skew-skipped role body should stay untouched"
        else:
            assert body == markers.open_marker(markers.view_tag("role_definition")), (
                f"{item.id}: the body converged onto something other than its placement tag"
            )
        assert item.title == was["title"]
        assert item.description == was.get("description", "")
        assert item.extra == stored, f"{item.id}: the index and the file disagree"


async def test_the_sweep_regenerates_no_surface_and_leaves_every_compiled_region_identical(
    tmp_path: Path,
) -> None:
    """The migration sweep leaves every compiled managed region and backend pointer
    byte-identical, regenerating no surface itself."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    await svc.run_pending_migrations()
    generated = sorted(
        p
        for p in (
            *dst.rglob("CLAUDE.md"),
            *dst.rglob("AGENTS.md"),
            *(dst / ".claude").rglob("*.md"),
        )
        if p.is_file()
    )
    assert generated, "no compiled surface to compare"
    before = {p: p.read_bytes() for p in generated}

    await svc.repair()

    assert {p: p.read_bytes() for p in generated} == before


def _v0_14_copy_stamped_schema_current(tmp_path: Path) -> Path:
    """Build a corpus whose config already stamps the current schema while its content is
    still pre-migration content — a state only the bare ``repair`` verb can sweep."""
    dst = tmp_path / "v0_14_stamped_current"
    shutil.copytree(_CORPUS_DIR / "v0_14", dst)
    cfg_path = dst / ".squads.toml"
    original = cfg_path.read_text(encoding="utf-8")
    stamped = original.replace('schema_version = "0.14"', f'schema_version = "{SCHEMA_VERSION}"')
    assert stamped != original, "v0_14's schema_version line did not match the expected shape"
    cfg_path.write_text(stamped, encoding="utf-8")

    mile_files = sorted((dst / "milestones").glob("*.md"))
    assert mile_files, "v0_14 carries no milestone for this scenario to pre-tag"
    spec = load_workflow_spec(dst)
    for addr, path in enumerate(mile_files):
        text = path.read_text(encoding="utf-8")
        region = get_section(text, markers.BODY) or ""
        new_region = place_view_tags(
            region,
            None,
            seeded=frozenset({"milestone_rollup"}),
            spec=spec,
            item_type="milestone",
            addr=addr,
        )
        new_text = replace_section(text, markers.BODY, new_region)
        path.write_text(new_text, encoding="utf-8")
    return dst


async def test_the_bare_verb_strips_a_corpus_already_at_the_current_stamp(tmp_path: Path) -> None:
    """The bare ``repair`` verb strips retired regions and the role mirror from a corpus
    already stamped current, but preserves plain-prose bodies no migration ever touched."""
    dst = _v0_14_copy_stamped_schema_current(tmp_path)
    paths = _load_paths(dst)
    svc = Service(paths)
    run = await svc.run_pending_migrations()
    assert run.applied == [] and run.repair is None

    roles = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_ROLE]
    assert roles and all(
        set(read_frontmatter(path=item_file(paths, it)).get("extra", {})) & _RETIRED_MIRROR_KEYS
        for it in roles
    ), "this fixture carries no role mirror for the bare verb to reach"
    role_bodies_before = {
        item_file(paths, it).name: (
            get_section(item_file(paths, it).read_text(encoding="utf-8"), markers.BODY) or ""
        ).strip()
        for it in roles
    }

    first = await svc.repair()
    assert first.stripped, "the bare verb reached none of the regions this fixture carries"
    for path in _md_files(paths.squad_dir):
        text = path.read_text(encoding="utf-8")
        assert not has_section(text, markers.SUMMARY)
        assert ":head -->" not in text
    for item in roles:
        path = item_file(paths, item)
        text = path.read_text(encoding="utf-8")
        stored = read_frontmatter(text=text, source=str(path)).get("extra", {})
        assert set(stored) & _RETIRED_MIRROR_KEYS == set()
        body = (get_section(text, markers.BODY) or "").strip()
        assert body == role_bodies_before[path.name], (
            f"{item.id}: the bare verb converged an authored body it has no licence to touch"
        )

    corpus = {p: p.read_bytes() for p in _md_files(paths.squad_dir)}
    second = await svc.repair()
    assert second.stripped == []
    assert {p: p.read_bytes() for p in corpus} == corpus
    system_skills = [
        it
        for it in (await svc.store.load()).items.values()
        if it.type == ROSTER_SKILL and is_system_skill(it.extra.get(X.SLUG, it.slug), svc.spec)
    ]
    expected_gaps = await _expected_seeded_view_gap_files(svc, set())
    expected_gaps |= {item_file(paths, it).name for it in (*roles, *system_skills)}
    unexpected = [
        i
        for i in await svc.check()
        if i.level == "error"
        and not ("missing seeded view tag" in i.message and i.item in expected_gaps)
    ]
    assert not unexpected, unexpected
