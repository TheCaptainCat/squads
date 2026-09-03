"""The override provenance manifest + content store mechanics:
the shipped index carries a current-version hash for every overridable bundled artifact — the
24 bundled templates plus workflow.toml, roles.toml, playbook.toml (the manifest-freshness
guard — an artifact edit without re-running the generator script fails loudly, not silently) —
`artifact_changed_since` is content-gated and version-aware, the template/TOML stamp comment
round-trips insert-vs-replace, and the retention guards (every index-named
hash resolves in the store, every stored blob is referenced, the store stays under its in-wheel
compressed ceiling) hold for the shipped documents. `sq override` command behaviour lives in
tests/integration/test_override_scaffold_scan_diff_update_and_check.py.

The ground-truth-rebuild section near the bottom drives ``scripts/gen_template_manifest.py``
(its write mode and ``--check``) and ``scripts/seed_content_store.py`` (its ``--rebuild``)
against a copied tree, the same way ``tests/meta/test_release_version_bump_script.py`` drives
``scripts/bump_version.py`` — by extending ``sys.path`` and importing the script modules
directly, since ``scripts/`` sits outside both pytest's ``testpaths`` and pyright's ``include``.
"""

import hashlib
import importlib
import importlib.resources as pkg_resources
import json
import os
import re
import shutil
import sys
import types
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest

from squads import __version__
from squads._overrides._manifest import (
    PLAYBOOK_KEY,
    ROLES_KEY,
    WORKFLOW_KEY,
    _load_manifest,
    _load_store,
    artifact_changed_since,
    artifact_floor,
    artifact_hash_at_version,
    base_version_artifact_content,
    bundled_template_content,
    current_artifact_hash,
    current_template_hash,
    invalidate_cache,
    known_index_versions,
    template_changed_since,
    template_hash_at_version,
    template_key,
)
from squads._overrides._stamp import (
    read_template_stamp,
    read_toml_stamp,
    write_template_stamp,
    write_toml_stamp,
)

#: The 256 KB compressed in-wheel ceiling on the content store.
_STORE_CEILING_BYTES = 256 * 1024

#: ``scripts/`` is outside pytest's testpaths and pyright's include, same as
#: tests/meta/test_release_version_bump_script.py — extended onto sys.path so the
#: ground-truth-rebuild section below can import the scripts directly.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _installed_template_hashes() -> dict[str, str]:
    installed: dict[str, str] = {}

    def _walk(node: object, prefix: str) -> None:
        for child in node.iterdir():  # type: ignore[union-attr]
            rel = child.name if not prefix else f"{prefix}/{child.name}"
            if child.is_dir():
                _walk(child, rel)
            elif child.is_file() and child.name.endswith(".md.j2"):
                installed[rel] = hashlib.sha256(child.read_bytes()).hexdigest()

    _walk(pkg_resources.files("squads._rendering.templates"), "")
    return installed


def test_the_index_has_a_current_version_hash_for_every_overridable_bundled_artifact() -> None:
    invalidate_cache()
    installed_templates = _installed_template_hashes()
    assert installed_templates, "no bundled templates found — package data misconfigured?"
    installed_keys = {template_key(name) for name in installed_templates} | {
        WORKFLOW_KEY,
        ROLES_KEY,
        PLAYBOOK_KEY,
    }

    manifest_entry = _load_manifest().get(__version__)
    assert manifest_entry is not None, f"manifest has no entry for v{__version__}"

    missing = installed_keys - set(manifest_entry)
    extra = set(manifest_entry) - installed_keys
    assert not missing, f"manifest is missing hashes for: {sorted(missing)}"
    assert not extra, f"manifest records hashes for non-existent artifacts: {sorted(extra)}"

    # Content, not merely presence — the freshness half of this guard's own name. `missing`/
    # `extra` above catch an artifact that appeared or vanished; this catches the far more
    # likely mistake, an artifact hand-edited without re-running
    # scripts/gen_template_manifest.py, which leaves every key present but the running
    # version's recorded hash for that key still naming the *previous* release's bytes. Over
    # the whole installed set (every bundled template plus the three spec TOMLs), not only the
    # handful of artifacts the content-gated drift tests below happen to exercise.
    installed = {key: current_artifact_hash(key) for key in installed_keys}
    mismatched = {key for key, actual in installed.items() if manifest_entry.get(key) != actual}
    assert not mismatched, f"manifest hashes are stale for: {sorted(mismatched)}"

    one_hash = template_hash_at_version("items/task.md.j2", __version__)
    assert one_hash is not None and len(one_hash) == 64  # SHA-256 hex
    assert artifact_hash_at_version(WORKFLOW_KEY, __version__) is not None


def test_a_content_only_edit_with_no_regeneration_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drives the exact state a template edit that forgets to re-run
    ``scripts/gen_template_manifest.py`` leaves behind: the running version's manifest entry
    still names an *earlier* release's hash for one key, while the artifact itself (read fresh
    by :func:`current_artifact_hash`, untouched by this probe) is whatever is actually
    installed. Presence stays intact — only the recorded hash is wrong — so this is exactly
    the case the ``missing``/``extra`` sets above cannot see and only the restored
    ``mismatched`` assertion catches — the case a manifest-widening pass silently dropped,
    leaving this module's own docstring promise (an artifact edit without re-running the
    generator script fails loudly, not silently) unmet until this assertion was restored.

    The control below — the same key deleted from the entry outright — is caught by the
    ``missing`` set instead, proving this probe is sound rather than the assertion being
    vacuously satisfied some other way.
    """
    invalidate_cache()
    real_manifest = _load_manifest()
    victim = template_key("items/task.md.j2")
    an_earlier_version = next(
        v for v in real_manifest if v != __version__ and victim in real_manifest[v]
    )
    stale_hash = real_manifest[an_earlier_version][victim]
    assert stale_hash != real_manifest[__version__][victim], (
        "fixture needs a genuinely different hash to prove the mismatch is caught"
    )

    doctored = {v: dict(entry) for v, entry in real_manifest.items()}
    doctored[__version__][victim] = stale_hash
    monkeypatch.setattr(sys.modules[__name__], "_load_manifest", lambda: doctored)
    with pytest.raises(AssertionError, match="manifest hashes are stale for"):
        test_the_index_has_a_current_version_hash_for_every_overridable_bundled_artifact()

    # Control: the entry deleted outright is still caught, by `missing` rather than
    # `mismatched` — same fixture shape, different (still-detected) defect.
    without_entry = {v: dict(entry) for v, entry in real_manifest.items()}
    del without_entry[__version__][victim]
    monkeypatch.setattr(sys.modules[__name__], "_load_manifest", lambda: without_entry)
    with pytest.raises(AssertionError, match="manifest is missing hashes for"):
        test_the_index_has_a_current_version_hash_for_every_overridable_bundled_artifact()


def test_current_template_hash_matches_the_actual_bundled_bytes() -> None:
    content = bundled_template_content("items/task.md.j2")
    assert content is not None
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert current_template_hash("items/task.md.j2") == expected
    assert bundled_template_content("items/nonexistent.md.j2") is None


def test_template_changed_since_is_false_for_the_current_and_for_an_unknown_version() -> None:
    invalidate_cache()
    assert not template_changed_since("items/task.md.j2", __version__)
    assert not template_changed_since("items/task.md.j2", "0.0.0-nonexistent")


def test_artifact_changed_since_is_content_gated_for_every_kind() -> None:
    """The generalized resolver underlies the drift check for every kind alike:
    unknown history is silent, and the running version is never drifted from itself."""
    invalidate_cache()
    for key in (WORKFLOW_KEY, ROLES_KEY, PLAYBOOK_KEY):
        assert not artifact_changed_since(key, __version__)
        assert not artifact_changed_since(key, "0.0.0-nonexistent")


def test_template_stamp_comment_round_trips_insert_then_replace() -> None:
    assert read_template_stamp("no stamp here") is None
    inserted = write_template_stamp("content here", "0.3.0")
    assert inserted.startswith("<!-- squads:override-base:0.3.0 -->")
    assert "content here" in inserted
    assert read_template_stamp(inserted) == "0.3.0"

    replaced = write_template_stamp(inserted, "0.4.0")
    assert "0.3.0" not in replaced
    assert read_template_stamp(replaced) == "0.4.0"


def test_toml_stamp_comment_round_trips_insert_then_replace() -> None:
    assert read_toml_stamp("full_name = 'Ada'") is None
    inserted = write_toml_stamp('full_name = "Ada"', "0.3.0")
    assert inserted.startswith("# squads:override-base:0.3.0")
    assert 'full_name = "Ada"' in inserted
    assert read_toml_stamp(inserted) == "0.3.0"

    replaced = write_toml_stamp(inserted, "0.4.0")
    assert "0.3.0" not in replaced
    assert read_toml_stamp(replaced) == "0.4.0"


# ─── Retention guards: the shipped index + store ──────────────────────────────


def test_every_index_named_hash_resolves_in_the_store() -> None:
    """The retention promise itself: every ``(version, artifact)`` pair the
    index names, for every release it covers, resolves to bytes in the store."""
    invalidate_cache()
    manifest = _load_manifest()
    store = _load_store()
    unresolved = [
        f"{version}:{key}"
        for version, entry in manifest.items()
        for key, h in entry.items()
        if h not in store
    ]
    assert not unresolved, f"index-named hashes with no store entry: {unresolved[:20]}"


def test_every_stored_blob_is_referenced_by_at_least_one_index_entry() -> None:
    """Not an invariant the generator's write mode maintains — it never deletes, so it can
    leave an orphan behind as ordinary development residue (exercised directly below). This
    holds for the *shipped* documents because a release rebuilds the store from ground truth
    (``scripts/seed_content_store.py --rebuild``) before the tag, which drops what write mode
    alone would have left behind."""
    invalidate_cache()
    manifest = _load_manifest()
    store = _load_store()
    referenced = {h for entry in manifest.values() for h in entry.values()}
    orphans = set(store) - referenced
    assert not orphans, f"content-store blobs with no referencing index entry: {sorted(orphans)}"


def test_the_content_store_stays_under_its_in_wheel_compressed_ceiling() -> None:
    """The 256 KB compressed-in-wheel ceiling, approximated with the same deflate
    algorithm a zip member uses (``zlib`` at the max compression level)."""
    ref = pkg_resources.files("squads._rendering") / "content_store.json"
    raw = ref.read_bytes()
    compressed = len(zlib.compress(raw, level=9))
    assert compressed < _STORE_CEILING_BYTES, (
        f"content_store.json compresses to {compressed} bytes, at/over the "
        f"{_STORE_CEILING_BYTES}-byte ceiling"
    )


def test_the_store_covers_every_release_the_index_covers_from_its_own_floor() -> None:
    """Full retention: the store's version coverage matches the index's, back to
    the index's own floor (0.4.0) — no version the index names is a gap in the store."""
    invalidate_cache()
    versions = known_index_versions()
    assert versions, "index has no versions at all"
    assert versions[0] == "0.4.0", f"expected the index floor to be 0.4.0, got {versions[0]!r}"
    for version in versions:
        entry = _load_manifest()[version]
        for key in entry:
            assert base_version_artifact_content(key, version) is not None, (
                f"{key} at v{version} is index-named but not carried by the store"
            )


def test_a_spec_document_has_a_later_artifact_floor_than_a_template() -> None:
    """``roles.toml``/``workflow.toml``/``playbook.toml`` were introduced partway through the
    index's history (v0.13.0), so their own floor is later than a template overridable since
    the index's own floor — this is exactly the "index did not then cover" case."""
    invalidate_cache()
    templates_floor = artifact_floor(template_key("items/task.md.j2"))
    workflow_floor = artifact_floor(WORKFLOW_KEY)
    assert templates_floor == "0.4.0"
    assert workflow_floor is not None
    from squads._util import version_tuple

    assert version_tuple(workflow_floor) > version_tuple(templates_floor)


def test_regenerating_the_manifest_twice_at_the_same_version_is_stable() -> None:
    """Re-running the generator at an unchanged version replaces the index entry
    (a no-op when content is unchanged) and leaves the store byte-identical — nothing gained,
    nothing lost. Exercised at the JSON-document level (not by invoking the release script) so
    the test stays hermetic; the two writers share the same shipped documents as ground truth."""
    invalidate_cache()
    manifest = json.loads(
        (pkg_resources.files("squads._rendering") / "templates_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    store = json.loads(
        (pkg_resources.files("squads._rendering") / "content_store.json").read_text(
            encoding="utf-8"
        )
    )
    current_entry = manifest[__version__]

    # Simulate a second write-mode pass: wholesale-replace this version's entry with itself,
    # and insert-if-absent every hash it names.
    manifest[__version__] = dict(current_entry)
    inserted = 0
    for h in current_entry.values():
        if h not in store:
            inserted += 1
    assert inserted == 0
    assert manifest[__version__] == current_entry


# ─── The ground-truth rebuild: gen_template_manifest.py write mode/--check, and
# seed_content_store.py --rebuild ──────────────────────────────────────────────


@pytest.fixture
def rebuild_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], types.SimpleNamespace]:
    """Factory: a copy of the real templates, spec TOMLs, and the *shipped* index + store,
    wired to fresh imports of both ``scripts/gen_template_manifest`` (its write mode and
    ``--check``) and ``scripts/seed_content_store`` (its ``--rebuild``), with their document
    path constants monkeypatched onto the copy — so a run drives the real scripts against
    isolated documents (multi-release history included) with the repo's own documents left
    untouched. ``seed_content_store``'s git-reading calls are left pointed at the real
    repository root, so a historic version's tag still resolves against real release history;
    only the document paths and the disk-tree root for the running version move.

    The one entry that would always be untagged noise here — the repository's own real running
    version, copied verbatim into the index like every other entry — is dropped from the copy,
    since it represents nothing about whatever synthetic version an individual test chooses.

    Call the returned factory with the desired ``[project].version`` for the test. **The
    version must differ from the repository's own** — the factory asserts this itself, so a
    future accidental fallback to the running version fails loudly instead of quietly
    exercising only the half of the argument that was always true.
    """
    repo_root = _SCRIPTS_DIR.parent
    squads_root = repo_root / "src" / "squads"

    dest_root = tmp_path / "squads"
    shutil.copytree(
        squads_root / "_rendering" / "templates", dest_root / "_rendering" / "templates"
    )
    (dest_root / "_specs").mkdir(parents=True)
    for name in ("workflow.toml", "roles.toml", "playbook.toml"):
        shutil.copy2(squads_root / "_specs" / name, dest_root / "_specs" / name)
    for name in ("templates_manifest.json", "content_store.json"):
        shutil.copy2(squads_root / "_rendering" / name, dest_root / "_rendering" / name)
    pyproject_path = tmp_path / "pyproject.toml"

    manifest_path = dest_root / "_rendering" / "templates_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop(__version__, None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    gen = importlib.reload(importlib.import_module("gen_template_manifest"))
    seed = importlib.reload(importlib.import_module("seed_content_store"))

    monkeypatch.setattr(gen, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(gen, "_SQUADS_ROOT", dest_root)
    monkeypatch.setattr(gen, "_TEMPLATES_DIR", dest_root / "_rendering" / "templates")
    monkeypatch.setattr(gen, "_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(gen, "_STORE_PATH", dest_root / "_rendering" / "content_store.json")
    monkeypatch.setattr(gen, "_PYPROJECT_PATH", pyproject_path)

    # seed_content_store's _REPO_ROOT stays the REAL repo — its git subprocess calls need real
    # tags to resolve against. Only the document paths and the disk-tree root move to the copy.
    monkeypatch.setattr(seed, "_SQUADS_ROOT", dest_root)
    monkeypatch.setattr(seed, "_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(seed, "_STORE_PATH", dest_root / "_rendering" / "content_store.json")
    monkeypatch.setattr(seed, "_PYPROJECT_PATH", pyproject_path)

    def _build(version: str) -> types.SimpleNamespace:
        assert version != __version__, (
            "rebuild_tree's version must differ from the repository's own — a fallback to the "
            "running version would make every test built on this fixture pass whether the "
            "mechanism worked or not"
        )
        pyproject_path.write_text(
            f'[project]\nname = "squads"\nversion = "{version}"\n', encoding="utf-8"
        )
        return types.SimpleNamespace(gen=gen, seed=seed, dest_root=dest_root)

    return _build


def _docs(gen: types.ModuleType) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    return gen._load_json(gen._MANIFEST_PATH), gen._load_json(gen._STORE_PATH)


def _run_write_mode(gen: types.ModuleType) -> str:
    version = gen._current_version()
    gen._write_mode(version, gen._collect_current_tree())
    return version


def test_rebuild_tree_asserts_its_version_differs_from_the_repository(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    """The fixture's own non-vacuity guarantee: calling it with the repository's own version
    must fail loudly, not silently fall back and let every test built on it pass vacuously."""
    with pytest.raises(AssertionError, match="must differ from the repository's own"):
        rebuild_tree(__version__)


def test_editing_and_regenerating_twice_leaves_the_orphan_unswept(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    """Write mode never deletes: two regenerations of the same template at the same version
    leave the first edit's blob in the store with nothing referencing it — ordinary development
    residue, not a defect — while every index-named hash still resolves."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    victim = gen._TEMPLATES_DIR / "agents" / "role.md.j2"

    with victim.open("a", encoding="utf-8") as f:
        f.write("# first edit\n")
    _run_write_mode(gen)
    manifest_mid, _store_mid = _docs(gen)
    first_edit_hash = manifest_mid["9.9.9"]["_rendering/templates/agents/role.md.j2"]

    with victim.open("a", encoding="utf-8") as f:
        f.write("# second edit\n")
    _run_write_mode(gen)

    manifest, store = _docs(gen)
    assert first_edit_hash in store, "write mode must never remove a blob, even an orphan"
    referenced = {h for entry in manifest.values() for h in entry.values()}
    assert first_edit_hash not in referenced, "fixture assumption: the first edit is now an orphan"
    unresolved = [
        f"{v}:{key}" for v, entry in manifest.items() for key, h in entry.items() if h not in store
    ]
    assert not unresolved, f"index-named hashes stopped resolving: {unresolved}"


def test_deleting_a_bundled_artifact_and_regenerating_keeps_history_and_never_sweeps(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    built = rebuild_tree("9.9.9")
    gen = built.gen
    key = "_rendering/templates/agents/role.md.j2"
    manifest_before, _store_before = _docs(gen)
    older_versions_naming_it = [
        v for v in manifest_before if v != "9.9.9" and key in manifest_before[v]
    ]
    assert len(older_versions_naming_it) >= 2, "fixture needs the artifact edited across releases"
    older_hashes = {manifest_before[v][key] for v in older_versions_naming_it}
    assert len(older_hashes) >= 2, "fixture needs genuinely distinct historic revisions"
    current_hash, _current_text = gen._collect_current_tree()[key]

    (gen._TEMPLATES_DIR / "agents" / "role.md.j2").unlink()
    _run_write_mode(gen)

    manifest, store = _docs(gen)

    # The key is gone only from the current version's entry; historic entries are untouched.
    assert key not in manifest["9.9.9"]
    for v in older_versions_naming_it:
        assert manifest[v] == manifest_before[v], f"{v}'s historic entry was rewritten"

    # Every historic revision — several distinct hashes across releases — is still there, and
    # so is the revision the deletion itself just orphaned: write mode never sweeps anything.
    for h in older_hashes:
        assert h in store, f"historic revision {h[:12]} was removed though an entry still names it"
    assert current_hash in store, (
        "the just-orphaned revision was removed — write mode must never sweep"
    )


def test_write_mode_never_removes_a_blob_only_a_historic_entry_names(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    """A hash the *current* version's entry does not name at all, while an older entry does,
    must survive a write-mode run at that unreleased version. Write mode has no removal path at
    all now, but this is the regression test for the case the withdrawn sweep once had to
    reason its way around instead of simply not having."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    manifest_before, store_before = _docs(gen)  # "9.9.9" has no entry yet — this is its first run

    current_tree_hashes = {h for h, _text in gen._collect_current_tree().values()}
    historic_only_hash = next(
        h
        for entry in manifest_before.values()
        for h in entry.values()
        if h not in current_tree_hashes
    )
    assert historic_only_hash in store_before

    _run_write_mode(gen)  # v9.9.9's first write-mode run — no historic entry is touched

    _manifest, store = _docs(gen)
    assert historic_only_hash in store, "a blob only a historic entry names was removed"


def test_regenerating_at_an_already_indexed_version_keeps_its_prior_hashes(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    """The exact scenario the withdrawn sweep got wrong: ``[project].version`` names a release
    the index already carries, and the current tree's hashes differ from what is recorded for
    it. Write mode still wholesale-replaces the entry (unchanged, sanctioned semantics) — but
    every hash the *prior* entry named must still resolve in the store afterward. Every earlier
    sweep test ran at the repository's own unreleased version and so could never reach this."""
    built = rebuild_tree("0.9.0")
    gen = built.gen
    manifest_before, _store_before = _docs(gen)
    prior_hashes = set(manifest_before["0.9.0"].values())

    victim = gen._TEMPLATES_DIR / "agents" / "role.md.j2"
    with victim.open("a", encoding="utf-8") as f:
        f.write("# edited while pinned to an already-shipped version\n")
    _run_write_mode(gen)

    manifest, store = _docs(gen)
    assert manifest["0.9.0"] != manifest_before["0.9.0"], "the entry should be wholesale-replaced"
    for h in prior_hashes:
        assert h in store, f"a hash the prior v0.9.0 entry named was removed: {h[:12]}"


def test_seed_content_store_rebuild_prefers_the_tag_even_when_it_is_also_the_running_version(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
) -> None:
    """The critical case: a version that is BOTH already tagged AND the one
    ``[project].version`` currently names — the state a release enters the moment its tag is
    cut and stays in until the next bump. Publication, not "is this the running version", is
    the discriminator: a tagged version is sourced from its own tag regardless of whether it is
    also pinned as running, so the shipped blob must survive and the tag must win even though
    no version is ever moved off it.

    Driven end to end: pin the version to an already-shipped, already-tagged release and
    regenerate — the mis-ordered regeneration, which now corrupts only the index entry (nothing
    is deleted, the sweep is withdrawn) — then run the rebuild *without moving the version away
    from the damaged release first*, and assert the damaged entry is corrected back to what its
    tag actually ships, the shipped blob is still in the store, and the whole index resolves.
    This is the regression test for the finding: the tag winning only while the running version
    happens to differ from it is exactly the discriminator that failed."""
    built = rebuild_tree("0.9.0")  # 0.9.0 is a real, already-tagged release
    gen, seed = built.gen, built.seed

    real_manifest = json.loads(
        (pkg_resources.files("squads._rendering") / "templates_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert real_manifest.get("0.9.0"), "fixture assumption: 0.9.0 is a real shipped entry"
    shipped_hashes = set(real_manifest["0.9.0"].values())

    _run_write_mode(gen)  # the damage: 0.9.0's entry now reflects the *current* tree, not v0.9.0
    manifest_damaged, _store_damaged = _docs(gen)
    assert manifest_damaged["0.9.0"] != real_manifest["0.9.0"], "fixture setup: damage did not take"

    # [project].version is still "0.9.0" here — the exact state the finding turned on.
    seed._rebuild_mode()

    manifest, store = _docs(gen)
    assert manifest["0.9.0"] == real_manifest["0.9.0"], (
        "the tag must win even while 0.9.0 is also the running version"
    )
    for h in shipped_hashes:
        assert h in store, (
            f"a shipped 0.9.0 blob was lost though its tag was never moved off: {h[:12]}"
        )
    unresolved = [
        f"{v}:{key}" for v, entry in manifest.items() for key, h in entry.items() if h not in store
    ]
    assert not unresolved, f"index-named hashes that don't resolve after the rebuild: {unresolved}"


def test_seed_content_store_rebuild_refuses_and_writes_nothing_for_an_untagged_version(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """All-or-nothing, driven on a version whose tag is absent: the rebuild refuses rather than
    silently dropping that version's history, names the version, points at ``git fetch --tags``
    first, and — because it is all-or-nothing — writes nothing at all, not even the versions it
    could have resolved."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    _run_write_mode(gen)
    manifest_before, store_before = _docs(gen)
    assert "0.9.0" in manifest_before, "fixture assumption: 0.9.0 is a real indexed version"

    manifest_before["0.9.0-does-not-exist"] = dict(manifest_before["0.9.0"])
    gen._write_json(gen._MANIFEST_PATH, manifest_before)

    with pytest.raises(SystemExit) as exc_info:
        seed._rebuild_mode()
    assert exc_info.value.code == 1
    reported = capsys.readouterr().err
    assert "0.9.0-does-not-exist" in reported
    assert "not tagged locally" in reported
    assert "git fetch --tags" in reported

    manifest_after, store_after = _docs(gen)
    assert manifest_after == manifest_before, (
        "a refusal must write nothing, not even a partial result"
    )
    assert store_after == store_before


def test_seed_content_store_rebuild_refuses_when_a_tag_resolves_but_lacks_an_artifact(
    rebuild_tree: Callable[[str], types.SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The second all-or-nothing floor: a tag that exists locally but whose listing comes back
    without the templates the index still records for it (a moved or emptied tag, a broken
    ``git ls-tree``) must refuse exactly like a missing tag — never silently narrow that entry
    to whatever it could find. Only one tag's listing is faked; every other version still
    resolves against real release history, so this isolates the one broken tag."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    manifest_before, store_before = _docs(gen)
    assert "0.9.0" in manifest_before, "fixture assumption: 0.9.0 is a real indexed version"
    assert any(key.startswith("_rendering/templates/") for key in manifest_before["0.9.0"]), (
        "fixture assumption: 0.9.0's entry records at least one template"
    )

    real_ls_tree = seed._git_ls_tree

    def _fake_ls_tree(tag: str, repo_subpath: str) -> list[str] | None:
        if tag == "v0.9.0":
            return []  # the tag resolves, but the listing comes back suspiciously empty
        return real_ls_tree(tag, repo_subpath)

    monkeypatch.setattr(seed, "_git_ls_tree", _fake_ls_tree)

    with pytest.raises(SystemExit) as exc_info:
        seed._rebuild_mode()
    assert exc_info.value.code == 1
    reported = capsys.readouterr().err
    assert "v0.9.0" in reported
    assert "could not be read in full" in reported

    manifest_after, store_after = _docs(gen)
    assert manifest_after == manifest_before, (
        "a refusal must write nothing, not even a partial result"
    )
    assert store_after == store_before


def test_check_mode_fails_for_a_hash_missing_from_a_historic_entry(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole-index widening's own regression test: a hash missing from a *historic*
    entry's store coverage — not the running version's — must fail ``--check``. Before the
    widening this was invisible: ``--check`` verified store coverage for the running version's
    own entry alone."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    _run_write_mode(gen)  # gives v9.9.9 a fresh entry so `version in manifest` holds

    manifest, store = _docs(gen)
    historic_version = next(v for v in manifest if v != "9.9.9")
    missing_key, missing_hash = next(iter(manifest[historic_version].items()))
    del store[missing_hash]
    gen._write_json(gen._STORE_PATH, store)

    with pytest.raises(SystemExit) as exc_info:
        gen._check_mode("9.9.9", gen._collect_current_tree())
    assert exc_info.value.code == 1
    reported = capsys.readouterr().err
    assert f"{historic_version}:{missing_key}" in reported


def test_check_mode_reports_an_orphan_without_failing_and_writes_nothing(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """An ordinary ``--check`` reports an orphan but does not fail over it — between releases
    an orphan is ordinary development residue the next rebuild clears — and still writes
    nothing, exactly like every other ``--check`` outcome."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    _run_write_mode(gen)
    _manifest, store = _docs(gen)
    orphan_hash = "0" * 64
    store[orphan_hash] = "nothing references this"
    gen._write_json(gen._STORE_PATH, store)
    manifest_before = json.loads(gen._MANIFEST_PATH.read_text(encoding="utf-8"))

    gen._check_mode("9.9.9", gen._collect_current_tree())  # must not raise

    reported = capsys.readouterr().err
    assert "orphaned blob in content store" in reported
    assert orphan_hash in reported

    assert json.loads(gen._MANIFEST_PATH.read_text(encoding="utf-8")) == manifest_before
    store_after = gen._load_json(gen._STORE_PATH)
    assert orphan_hash in store_after


def test_release_gate_fails_on_an_orphan_and_still_writes_nothing(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """The failure the ordinary check no longer performs moves here: ``--release-gate`` fails
    on the same orphan an ordinary ``--check`` only reports — and, like every ``--check``
    outcome, still writes nothing."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    _run_write_mode(gen)
    _manifest, store = _docs(gen)
    orphan_hash = "0" * 64
    store[orphan_hash] = "nothing references this"
    gen._write_json(gen._STORE_PATH, store)
    manifest_before = json.loads(gen._MANIFEST_PATH.read_text(encoding="utf-8"))

    with pytest.raises(SystemExit) as exc_info:
        gen._check_mode("9.9.9", gen._collect_current_tree(), release_gate=True)
    assert exc_info.value.code == 1
    reported = capsys.readouterr().err
    assert "orphaned blob in content store" in reported

    assert json.loads(gen._MANIFEST_PATH.read_text(encoding="utf-8")) == manifest_before
    store_after = gen._load_json(gen._STORE_PATH)
    assert orphan_hash in store_after


# ─── Rebuild reporting: restored/dropped as two independent counts, never a size delta ─────


def _restored_and_dropped(reported: str) -> tuple[int, int]:
    match = re.search(r"\((\d+) restored, (\d+) dropped", reported)
    assert match, f"rebuild summary line did not match the expected shape: {reported!r}"
    return int(match.group(1)), int(match.group(2))


def test_rebuild_reports_a_restore_only_run_as_restored_not_zero_dropped(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that only re-inserts a blob the closure still needs — recovery's headline case —
    must report it as a restore, never as ``0 dropped`` reading as "nothing happened"."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    _run_write_mode(gen)
    manifest, store = _docs(gen)

    victim_version = next(v for v in manifest if v != "9.9.9")
    victim_hash = next(iter(manifest[victim_version].values()))
    del store[victim_hash]
    gen._write_json(gen._STORE_PATH, store)

    seed._rebuild_mode()
    restored, dropped = _restored_and_dropped(capsys.readouterr().out)
    assert (restored, dropped) == (1, 0)


def test_rebuild_reports_a_drop_only_run_as_dropped_not_restored(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that only drops an orphan outside the closure must report it as a drop, with the
    restore count at zero — the mirror of the restore-only case above."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    _run_write_mode(gen)
    _manifest, store = _docs(gen)
    orphan_hash = "1" * 64
    store[orphan_hash] = "nothing references this"
    gen._write_json(gen._STORE_PATH, store)

    seed._rebuild_mode()
    restored, dropped = _restored_and_dropped(capsys.readouterr().out)
    assert (restored, dropped) == (0, 1)


def test_rebuild_reports_a_restore_and_a_drop_in_the_same_run_as_two_separate_counts(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """The exact case the finding turned on: a shipped release's blob restored and a stale
    orphan dropped in the same pass. The net-delta formula this replaces would print
    ``0 dropped`` here (the two changes cancel in size) and read as though nothing happened;
    set-based counting must report both independently."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    _run_write_mode(gen)
    manifest, store = _docs(gen)

    victim_version = next(v for v in manifest if v != "9.9.9")
    victim_hash = next(iter(manifest[victim_version].values()))
    del store[victim_hash]
    orphan_hash = "2" * 64
    store[orphan_hash] = "nothing references this"
    gen._write_json(gen._STORE_PATH, store)

    # The old formula's own reproduction: -1 (removed victim) + 1 (added orphan) nets to zero
    # blobs of size change, though a restore and a drop both genuinely happened underneath.
    seed._rebuild_mode()
    restored, dropped = _restored_and_dropped(capsys.readouterr().out)
    assert (restored, dropped) == (1, 1)


# ─── Durability: both scripts stage both documents before replacing either, and a truncated
# document is diagnosed by name rather than raised as a bare JSONDecodeError ─────────────────


@pytest.fixture(params=["gen_template_manifest", "seed_content_store"])
def rebuild_writer(request: pytest.FixtureRequest) -> types.ModuleType:
    """Either script module, freshly imported. ``_stage_json``/``_write_json_pair``/
    ``_load_json`` are written out verbatim in both scripts (they stay standalone, dependency-
    free dev tools — see the module docstrings), so this parametrization proves the mechanism
    in each rather than assuming one stands in for the other."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    return importlib.reload(importlib.import_module(request.param))


def test_write_json_pair_stages_both_documents_before_replacing_either(
    rebuild_writer: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fault while serializing/fsyncing either document's temporary must leave BOTH targets
    exactly as they were, with no stray temp file behind — proof that both documents are staged
    in full before either replace runs, so an interruption during staging can never leave one
    file new and the other old."""
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text('{"old": "first"}\n', encoding="utf-8")
    second_path.write_text('{"old": "second"}\n', encoding="utf-8")

    real_fsync = os.fsync
    calls = {"n": 0}

    def _flaky_fsync(fd: int) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # the second document's staging fsync
            raise OSError("simulated staging failure")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", _flaky_fsync)

    with pytest.raises(OSError, match="simulated staging failure"):
        rebuild_writer._write_json_pair(
            (first_path, {"new": "first"}), (second_path, {"new": "second"})
        )

    assert json.loads(first_path.read_text(encoding="utf-8")) == {"old": "first"}
    assert json.loads(second_path.read_text(encoding="utf-8")) == {"old": "second"}
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert not leftovers, f"a failed stage must not leave a temp file behind: {leftovers}"


def test_write_json_pair_interrupted_between_the_two_renames_never_truncates_the_second(
    rebuild_writer: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates the one window the fix narrows to but does not close: the first document's
    rename lands, then the process dies before the second's. The first document must read as
    the new value; the second must read as its complete previous value — never a truncated
    document either way, which is the honest residual the durability prose now states."""
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text('{"old": "first"}\n', encoding="utf-8")
    second_path.write_text('{"old": "second"}\n', encoding="utf-8")

    real_replace = Path.replace
    calls = {"n": 0}

    def _flaky_replace(self: Path, target: str | Path) -> Path:
        calls["n"] += 1
        if calls["n"] == 2:  # the second document's rename
            raise RuntimeError("simulated interruption between the two writes")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _flaky_replace)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        rebuild_writer._write_json_pair(
            (first_path, {"new": "first"}), (second_path, {"new": "second"})
        )

    assert json.loads(first_path.read_text(encoding="utf-8")) == {"new": "first"}, (
        "the first document's rename had already landed — it must read as the new value"
    )
    assert json.loads(second_path.read_text(encoding="utf-8")) == {"old": "second"}, (
        "the second document's rename never ran — it must read as its complete previous value, "
        "never a truncated one"
    )


def test_load_json_diagnoses_a_truncated_document_instead_of_raising(
    rebuild_writer: types.ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A partially-written (truncated/corrupted) document must surface as a named diagnosis
    with a recovery command — never an unhandled ``JSONDecodeError`` traceback."""
    manifest_path = tmp_path / "templates_manifest.json"
    store_path = tmp_path / "content_store.json"
    monkeypatch.setattr(rebuild_writer, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(rebuild_writer, "_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(rebuild_writer, "_STORE_PATH", store_path)

    store_path.write_text('{"abc123": "trunc', encoding="utf-8")  # truncated mid-value

    with pytest.raises(SystemExit) as exc_info:
        rebuild_writer._load_json(store_path)
    assert exc_info.value.code == 1

    reported = capsys.readouterr().err
    assert "not valid JSON" in reported
    assert str(store_path) in reported
    assert "git checkout" in reported
    assert "--rebuild" in reported


def test_rebuild_interrupted_between_the_two_writes_leaves_a_diagnosable_not_corrupted_tree(
    rebuild_tree: Callable[[str], types.SimpleNamespace], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drives an actual ``--rebuild`` run and kills it between the manifest rename and the
    store rename — the exact window the durability fix narrows to but cannot close. The result
    must be neither silently lost (both documents are git-tracked) nor a truncated document
    (the atomic pattern); it must be exactly what the whole-index ``--check`` widening already
    catches: an index naming a hash the store does not yet have."""
    built = rebuild_tree("9.9.9")
    gen, seed = built.gen, built.seed
    _run_write_mode(gen)
    manifest_before, store_before = _docs(gen)

    victim_version = next(v for v in manifest_before if v != "9.9.9")
    victim_key, victim_hash = next(iter(manifest_before[victim_version].items()))
    del store_before[victim_hash]
    gen._write_json(gen._STORE_PATH, store_before)

    real_replace = Path.replace
    calls = {"n": 0}

    def _flaky_replace(self: Path, target: str | Path) -> Path:
        calls["n"] += 1
        if calls["n"] == 2:  # the store's rename — the second of the pair
            raise RuntimeError("simulated interruption between the two writes")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _flaky_replace)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        seed._rebuild_mode()

    # Both documents must still parse in full — no truncation either side of the interruption.
    manifest_after = json.loads(gen._MANIFEST_PATH.read_text(encoding="utf-8"))
    store_after = json.loads(gen._STORE_PATH.read_text(encoding="utf-8"))

    assert manifest_after[victim_version][victim_key] == victim_hash, (
        "the manifest's rename had already landed — it must carry the corrected/rebuilt entry"
    )
    assert victim_hash not in store_after, "the store's rename never ran — it must be the old store"

    unresolved = gen._whole_index_unresolved(manifest_after, store_after)
    assert f"{victim_version}:{victim_key}" in unresolved, (
        "the interrupted state must be exactly what --check's whole-index widening diagnoses, "
        "not a state that check can't see"
    )


# ─── Release gate: the success line states what only it verified, and is never byte-identical
# to plain --check's ──────────────────────────────────────────────────────────────────────────


def test_check_and_release_gate_success_lines_are_distinguishable(
    rebuild_tree: Callable[[str], types.SimpleNamespace], capsys: pytest.CaptureFixture[str]
) -> None:
    """Driven on a clean tree (no orphans, nothing stale): the two modes' success lines must
    differ, ``--release-gate``'s must state the orphan-free property only it verifies, and both
    must word the coverage count as index references over stored blobs rather than an
    unqualified ``hash(es)`` that cannot be reconciled against the store's own size."""
    built = rebuild_tree("9.9.9")
    gen = built.gen
    _run_write_mode(gen)
    manifest, store = _docs(gen)
    keys_checked = sum(len(entry) for entry in manifest.values())

    gen._check_mode("9.9.9", gen._collect_current_tree())
    check_line = capsys.readouterr().out.strip()

    gen._check_mode("9.9.9", gen._collect_current_tree(), release_gate=True)
    gate_line = capsys.readouterr().out.strip()

    assert check_line != gate_line, "the two modes' success lines must not be byte-identical"
    assert "release gate" in gate_line.lower()
    assert "orphan-free" in gate_line
    assert "orphan-free" not in check_line

    for line in (check_line, gate_line):
        assert f"{keys_checked} index reference(s)" in line
        assert f"{len(store)} stored blob(s)" in line
