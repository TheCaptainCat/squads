"""Migration corpus: one frozen squad per released schema version, migrated to current and
checked clean via both the service call `sq migrate up` uses and the real CLI.

**Standing rule** (see `tests/fixtures/corpus/README.md`): every future schema bump must add a
new `vN_M` fixture here. This module — not the frozen fixtures themselves — is where that rule
is enforced; never hand-edit anything under `tests/fixtures/corpus/`.
"""

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
from squads._sections import get_section, has_section
from squads._services._service import Service
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL

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
]


def _load_paths(squad_dir: Path) -> SquadPaths:
    import tomllib

    with (squad_dir / ".squads.toml").open("rb") as fh:
        cfg_data = tomllib.load(fh)
    cfg = SquadsConfig.from_toml_dict(cfg_data)
    resolved = squad_dir / cfg.squad_dir
    return SquadPaths(root=squad_dir, squad_dir=resolved, config=cfg)


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
    applied = (await svc.run_pending_migrations()).applied

    import tomllib

    with (dst / ".squads.toml").open("rb") as fh:
        final_cfg = tomllib.load(fh)
    assert final_cfg["schema_version"] == SCHEMA_VERSION, (
        f"corpus {corpus_name!r} did not reach schema {SCHEMA_VERSION!r}; "
        f"applied: {[m.version for m in applied]}"
    )

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, (
        f"sq check produced errors after migrating {corpus_name!r} from {schema_label!r}:\n"
        + "\n".join(f"  [{i.level}] {i.item}: {i.message}" for i in errors)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
def test_corpus_cli_migrate_up_and_check_both_exit_clean(
    schema_label: str, corpus_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _CORPUS_DIR / corpus_name
    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)
    monkeypatch.chdir(dst)
    runner = CliRunner()

    migrate_result = runner.invoke(app, ["migrate", "up"])
    assert migrate_result.exit_code == 0, (
        f"sq migrate up failed on {corpus_name!r} ({schema_label!r}):\n{migrate_result.output}"
    )

    check_result = runner.invoke(app, ["check"])
    assert check_result.exit_code == 0, (
        f"sq check failed after migrating {corpus_name!r} ({schema_label!r}):\n"
        f"{check_result.output}"
    )


def test_migrate_up_announces_the_content_it_rewrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``sq migrate up`` says a byte of content moved, in the same sentence ``sq repair`` uses.

    The rebuild at the tail of the migration is also the corpus sweep, and the migration is the
    only route a squad behind the current schema takes: on that path "index rebuilt" is the
    whole of what the console said, while item files were being rewritten underneath it. The
    diff is meant to be stated rather than discovered, and an unannounced rewrite is exactly
    the thing an operator reads as a bug in the tool.

    Asserted against a real rewrite, not against the string alone: the fixture's own files are
    compared before and after, so a run that announced a strip it did not perform — or stopped
    performing one — fails here too.
    """
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
    """A v0.2 squad's `.squads.toml` ends with `active_backends` (the canonical shape), never
    the legacy `default_backend` — via the schema-stamp step, not an explicit toml rewrite."""
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


def _md_files(squad_dir: Path) -> list[Path]:
    return sorted(p for p in squad_dir.rglob("*.md") if p.is_file())


def _body_region(text: str) -> str | None:
    return get_section(text, markers.BODY)


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_corpus_carries_no_retired_region_after_migrating(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Migrating a frozen corpus to current leaves none of the retired regions behind.

    The removal is not any runner's: `run_pending_migrations` applies the ordered runners and
    then rebuilds the index, and the sweep rides that rebuild. `v0_1` proves the pipeline in
    both directions at once — its own files carry no summary region, the `0.1 -> 0.2` runner
    materialises one for every sub-entity host on the way up, and the rebuild at the end takes
    them out again.

    `v0_14` is the exception this asserts rather than exempts: a corpus already at the current
    stamp applies no runner, so `repair()` is never called, and it still carries its regions
    afterwards. That tolerance is the point — it is what an un-migrated adopter file needs from
    the read path, and it is why `markers.SUMMARY` stays in the validator's structural tag set.
    """
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)

    applied = (await svc.run_pending_migrations()).applied

    carried = [
        path
        for path in _md_files(paths.squad_dir)
        if has_section(path.read_text(encoding="utf-8"), markers.SUMMARY)
        or ":head -->" in path.read_text(encoding="utf-8")
    ]
    if not applied:
        assert corpus_name == "v0_14", f"{corpus_name!r} applied no runner unexpectedly"
        assert carried, "the frozen current-stamp fixture must keep carrying its regions"
        return
    assert not carried, (
        f"retired regions survived migrating {corpus_name!r} from {schema_label!r}: "
        + ", ".join(p.name for p in carried)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_a_system_skill_body_survives_the_migration_unchanged(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """A system skill's stored body comes out of the migration byte-for-byte as it went in.

    The sweep does not empty it, because on a real corpus it cannot tell a definition an older
    release stored from prose an author wrote: the slug's template-ownership is read off
    today's vocabulary and the body was written under an earlier one, and a release adding a
    bundled type flips that answer for every squad at once.

    **The precondition is the point of the parametrisation**, and it is the one the sibling
    role test below already carries. Without it a fixture that stores no skill body at all
    still passes here — the skills it then asserts on are ones the runners created empty, so
    the assertion confirms that a file just written empty is empty. Ten parameters that read
    as ten proofs and are five. A fixture with nothing to prove now says so.
    """
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    before = {
        path.name: _body_region(path.read_text(encoding="utf-8"))
        for path in _md_files(paths.squad_dir)
    }

    applied = (await svc.run_pending_migrations()).applied
    if not applied:
        pytest.skip(f"{corpus_name!r} is already at the current stamp; no rebuild runs")

    skills = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_SKILL]
    system = [it for it in skills if is_system_skill(it.extra.get(X.SLUG, it.slug), svc.spec)]
    assert system, f"{corpus_name!r} carries no system skill to assert on"
    stored = {
        it.id: (item_file(paths, it), before[item_file(paths, it).name])
        for it in system
        if (before.get(item_file(paths, it).name) or "").strip()
    }
    if not stored:
        pytest.skip(f"{corpus_name!r} stores no system skill body for the sweep to reach")
    for item_id, (path, was) in stored.items():
        text = path.read_text(encoding="utf-8")
        assert has_section(text, markers.BODY), f"{item_id}: the body markers were deleted"
        assert _body_region(text) == was, f"{item_id}: the stored body was rewritten"


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_a_role_keeps_its_record_and_loses_its_mirror_across_the_migration(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Every migrated role keeps the record other surfaces read and loses the definition it
    used to store twice.

    Both halves are asserted per fixture rather than spot-checked, because they fail in
    opposite directions: the top-level ``title``/``description`` are the uniform record and
    are no part of any mirror, while the ``extra`` mirror and the stored body are derived
    copies of a definition that is now resolved on every read.

    The file is the subject and the index is compared to it, not the other way round: the
    rebuild builds each index entry from the very frontmatter it rewrites, so the two agreeing
    is a claim about the sweep and not a restatement of one value read twice.

    ``v0_14`` is stamped current, applies no runner and so is never rebuilt — it keeps its
    mirror here, and the bare verb is what reaches it further down.
    """
    dst = tmp_path / corpus_name
    shutil.copytree(_CORPUS_DIR / corpus_name, dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    before = {
        path.name: read_frontmatter(text=path.read_text(encoding="utf-8"), source=str(path))
        for path in _md_files(paths.squad_dir)
    }

    applied = (await svc.run_pending_migrations()).applied

    roles = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_ROLE]
    assert roles, f"{corpus_name!r} carries no role item to assert on"
    for item in roles:
        path = item_file(paths, item)
        text = path.read_text(encoding="utf-8")
        stored = read_frontmatter(text=text, source=str(path)).get("extra", {})
        was = before[path.name]
        # Precondition: this fixture really did store part of the definition, so the absence
        # asserted below cannot pass against a role that never carried any of it.
        assert set(was.get("extra", {})) & _RETIRED_MIRROR_KEYS
        assert has_section(text, markers.BODY), f"{item.id}: the body markers were deleted"
        if not applied:
            assert corpus_name == "v0_14", f"{corpus_name!r} applied no runner unexpectedly"
            assert set(stored) & _RETIRED_MIRROR_KEYS
            continue
        assert set(stored) & _RETIRED_MIRROR_KEYS == set(), f"{item.id}: the mirror survived"
        assert stored.get(X.SLUG), f"{item.id}: the dispatch identity was stripped with it"
        assert not (get_section(text, markers.BODY) or "").strip()
        assert item.title == was["title"]
        assert item.description == was.get("description", "")
        assert item.extra == stored, f"{item.id}: the index and the file disagree"


async def test_the_sweep_regenerates_no_surface_and_leaves_every_compiled_region_identical(
    tmp_path: Path,
) -> None:
    """A strip must never run ahead of a surface regeneration that reads what it removes, and
    must regenerate nothing itself.

    On this vehicle the first half holds by construction rather than by an ordered pair of
    calls: ``require_current_schema`` refuses every subcommand but ``migrate`` on a mismatched
    stamp, so ``sq repair`` only ever runs against a corpus already at the current schema, and
    the single call on a behind-schema corpus is the tail of ``run_pending_migrations`` —
    after every runner, ``_regenerate_surface`` included. Reordering two adjacent lines cannot
    break it.

    The second half is what this asserts, and it is asserted by outcome rather than by call
    order: the compiled managed regions and the per-entry backend pointers are byte-identical
    across the sweep. An assertion about which call ran first would pass on a sweep that
    quietly rewrote them.
    """
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


async def test_the_bare_verb_strips_a_corpus_already_at_the_current_stamp(tmp_path: Path) -> None:
    """The case the migration path structurally cannot reach, and the whole reason the vehicle
    is ``repair`` rather than a runner.

    ``v0_14`` is stamped current, so ``sq migrate up`` answers "nothing to migrate" and no
    runner — and therefore no rebuild — ever visits it. The population is not an artefact of
    this release's staging either: ``adopt`` over a folder with no config stamps the build's
    own schema and rebuilds, manufacturing the same corpus with no release doing anything.
    """
    dst = tmp_path / "v0_14"
    shutil.copytree(_CORPUS_DIR / "v0_14", dst)
    paths = _load_paths(dst)
    svc = Service(paths)
    run = await svc.run_pending_migrations()
    assert run.applied == [] and run.repair is None  # nothing declared for it

    roles = [it for it in (await svc.store.load()).items.values() if it.type == ROSTER_ROLE]
    assert roles and all(
        set(read_frontmatter(path=item_file(paths, it)).get("extra", {})) & _RETIRED_MIRROR_KEYS
        for it in roles
    ), "this fixture carries no role mirror for the bare verb to reach"

    first = await svc.repair()
    assert first.stripped, "the bare verb reached none of the regions this fixture carries"
    for path in _md_files(paths.squad_dir):
        text = path.read_text(encoding="utf-8")
        assert not has_section(text, markers.SUMMARY)
        assert ":head -->" not in text
    for item in roles:
        text = item_file(paths, item).read_text(encoding="utf-8")
        stored = read_frontmatter(text=text, source=str(item_file(paths, item))).get("extra", {})
        assert set(stored) & _RETIRED_MIRROR_KEYS == set()
        assert not (get_section(text, markers.BODY) or "").strip()

    corpus = {p: p.read_bytes() for p in _md_files(paths.squad_dir)}
    second = await svc.repair()
    assert second.stripped == []
    assert {p: p.read_bytes() for p in corpus} == corpus
    assert not [i for i in await svc.check() if i.level == "error"]
