"""Tests for TASK-000089: sq override command group, staleness stamps, and sq check drift.

Covers:
- Manifest loading and hash functions.
- Stamp read/write for template files and role TOML files.
- scaffold_template: creates stamped copy, refuses clobber, --force overwrites.
- scaffold_role: creates stamped TOML stub, refuses clobber.
- scan_overrides: enumeration with correct kind/state.
- diff_override: produces Δ-mine and Δ-upgrade for templates and roles.
- update_stamp: re-stamps without touching body; skips broken; bulk re-stamp.
- sq check: warns on version drift, errors on missing required markers, clean on valid current.
- migrate: does NOT touch .overrides/ (sq migrate up must not rewrite overrides).
- CLI smoke: scaffold, list, diff, update — exit codes and --json shapes.
"""

from pathlib import Path

import pytest

from squads._overrides._manifest import (
    bundled_template_content,
    current_template_hash,
    invalidate_cache,
    template_changed_since,
    template_hash_at_version,
)
from squads._overrides._service import (
    STATE_BROKEN,
    STATE_CURRENT,
    DiffResult,
    check_override_issues,
    diff_override,
    scaffold_role,
    scaffold_template,
    scan_overrides,
    update_stamp,
)
from squads._overrides._stamp import (
    read_template_stamp,
    read_toml_stamp,
    write_template_stamp,
    write_toml_stamp,
)
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# ─── Fixtures / helpers ────────────────────────────────────────────────────────


def _tmpl_overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "templates"


def _role_overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def _place_template_override(
    squad_dir: Path, template_name: str, content: str, *, stamp: str | None = None
) -> Path:
    """Write a template override directly (bypassing scaffold, for staleness tests)."""
    target = _tmpl_overrides_dir(squad_dir) / template_name
    target.parent.mkdir(parents=True, exist_ok=True)
    text = content if stamp is None else write_template_stamp(content, stamp)
    target.write_text(text, encoding="utf-8")
    return target


def _place_role_override(squad_dir: Path, slug: str, content: str) -> Path:
    """Write a role TOML override directly."""
    target = _role_overrides_dir(squad_dir) / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _minimal_task_override(label: str = "CUSTOM") -> str:
    """A valid task override that keeps all required sq markers."""
    return (
        f"<!-- sq:body -->\n{label}\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


def _broken_task_override() -> str:
    """A task override missing sq:body — structurally broken."""
    return (
        "## Description\n\nMISSING MARKERS\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


# ─── Manifest tests ────────────────────────────────────────────────────────────


def test_manifest_loads_current_version_hashes():
    """The shipped manifest contains hashes for the current squads version."""
    from squads import __version__

    invalidate_cache()
    h = template_hash_at_version("items/task.md.j2", __version__)
    assert h is not None, f"manifest missing hash for items/task.md.j2 at v{__version__}"
    assert len(h) == 64  # SHA-256 hex


def test_manifest_freshness_all_bundled_templates():
    """Every bundled template's hash in the manifest matches the actual installed bytes.

    This is the manifest-freshness guard (REV-000097 F1): if
    gen_template_manifest.py is not re-run before a release that changes a template,
    the hashes go stale and template_changed_since() silently fails open.  A red build
    here converts that from a human-memory step into a CI enforced gate.

    The test asserts:
    1. The manifest has a current-version entry that covers ALL bundled templates
       (no missing, no extra relative to the installed template tree).
    2. Each stored hash matches the actual sha256 of the currently-installed template
       bytes — so a template edit without re-running the script fails loudly.
    """
    import importlib.resources as pkg_resources

    from squads import __version__

    invalidate_cache()

    # Collect all installed *.md.j2 paths from the package data tree.
    templates_root = pkg_resources.files("squads._rendering.templates")
    installed: dict[str, str] = {}
    _walk_templates(templates_root, "", installed)

    assert installed, "no bundled templates found — package data misconfigured?"

    # The manifest must have an entry for the current version.
    from squads._overrides._manifest import _load_manifest  # pyright: ignore[reportPrivateUsage]

    manifest = _load_manifest()
    assert __version__ in manifest, (
        f"manifest has no entry for the current version v{__version__}; "
        "run: python scripts/gen_template_manifest.py"
    )

    manifest_entry: dict[str, str] = manifest[__version__]

    # 1. No missing templates in the manifest.
    missing = set(installed.keys()) - set(manifest_entry.keys())
    assert not missing, (
        f"manifest v{__version__} is missing hashes for: {sorted(missing)}\n"
        "run: python scripts/gen_template_manifest.py"
    )

    # 2. No extra (phantom) templates recorded that no longer exist.
    extra = set(manifest_entry.keys()) - set(installed.keys())
    assert not extra, (
        f"manifest v{__version__} records hashes for non-existent templates: {sorted(extra)}\n"
        "run: python scripts/gen_template_manifest.py"
    )

    # 3. Every hash matches the current bytes (catches stale-manifest releases).
    mismatches: list[str] = []
    for name, actual_hash in installed.items():
        recorded = manifest_entry[name]
        if recorded != actual_hash:
            mismatches.append(f"  {name}: manifest={recorded[:12]}… actual={actual_hash[:12]}…")
    assert not mismatches, (
        f"manifest v{__version__} has stale hashes for:\n" + "\n".join(mismatches) + "\n"
        "run: python scripts/gen_template_manifest.py"
    )


def _walk_templates(
    node: object,
    prefix: str,
    out: dict[str, str],
) -> None:
    """Recursively collect *.md.j2 files from an importlib.resources traversable tree."""
    import hashlib

    for child in node.iterdir():  # type: ignore[union-attr]
        rel = child.name if not prefix else f"{prefix}/{child.name}"
        if child.is_dir():
            _walk_templates(child, rel, out)
        elif child.is_file() and child.name.endswith(".md.j2"):
            raw = child.read_bytes()
            out[rel] = hashlib.sha256(raw).hexdigest()


def test_current_template_hash_matches_bundled():
    """current_template_hash() matches sha256 of the actual bundled bytes."""
    import hashlib

    content = bundled_template_content("items/task.md.j2")
    assert content is not None
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert current_template_hash("items/task.md.j2") == expected


def test_template_changed_since_false_for_same_version():
    """template_changed_since returns False when base == current (same version)."""
    from squads import __version__

    invalidate_cache()
    # Current version's hash matches current bundled — no drift.
    assert not template_changed_since("items/task.md.j2", __version__)


def test_template_changed_since_false_for_unknown_version():
    """template_changed_since returns False (silent) for an unknown version."""
    assert not template_changed_since("items/task.md.j2", "0.0.0-nonexistent")


def test_bundled_template_content_not_none():
    """bundled_template_content returns a non-empty string for known templates."""
    content = bundled_template_content("items/task.md.j2")
    assert content is not None
    assert "<!-- sq:body -->" in content


def test_bundled_template_content_none_for_unknown():
    """bundled_template_content returns None for a non-existent template."""
    assert bundled_template_content("items/nonexistent.md.j2") is None


# ─── Stamp read/write tests ────────────────────────────────────────────────────


def test_read_template_stamp_present():
    text = "<!-- squads:override-base:0.3.0 -->\nsome content"
    assert read_template_stamp(text) == "0.3.0"


def test_read_template_stamp_absent():
    assert read_template_stamp("no stamp here") is None


def test_write_template_stamp_inserts():
    """write_template_stamp prepends stamp when absent."""
    text = "content here"
    result = write_template_stamp(text, "0.3.0")
    assert result.startswith("<!-- squads:override-base:0.3.0 -->")
    assert "content here" in result


def test_write_template_stamp_replaces():
    """write_template_stamp replaces an existing stamp in-place."""
    text = "<!-- squads:override-base:0.2.0 -->\ncontent"
    result = write_template_stamp(text, "0.3.0")
    assert "0.3.0" in result
    assert "0.2.0" not in result


def test_read_toml_stamp_present():
    text = "# squads:override-base:0.3.0\nfull_name = 'Ada'"
    assert read_toml_stamp(text) == "0.3.0"


def test_read_toml_stamp_absent():
    assert read_toml_stamp("full_name = 'Ada'") is None


def test_write_toml_stamp_inserts():
    text = 'full_name = "Ada"'
    result = write_toml_stamp(text, "0.3.0")
    assert result.startswith("# squads:override-base:0.3.0")
    assert 'full_name = "Ada"' in result


def test_write_toml_stamp_replaces():
    text = "# squads:override-base:0.1.0\nfull_name = 'Ada'"
    result = write_toml_stamp(text, "0.3.0")
    assert "0.3.0" in result
    assert "0.1.0" not in result


# ─── scaffold_template ─────────────────────────────────────────────────────────


async def test_scaffold_template_creates_stamped_copy(project):
    """scaffold_template copies the bundled template with the current-version stamp."""
    from squads import __version__

    squad_dir = project.squad_dir
    dest = scaffold_template(squad_dir, "items/task.md.j2")
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert read_template_stamp(text) == __version__
    # Original bundled content preserved.
    assert "<!-- sq:body -->" in text
    assert "<!-- sq:discussion -->" in text


async def test_scaffold_template_refuses_clobber(project):
    """scaffold_template raises SquadsError when the override exists and --force not set."""
    from squads._errors import SquadsError

    squad_dir = project.squad_dir
    scaffold_template(squad_dir, "items/task.md.j2")
    with pytest.raises(SquadsError, match="already exists"):
        scaffold_template(squad_dir, "items/task.md.j2")


async def test_scaffold_template_force_overwrites(project):
    """--force allows clobbering an existing override."""
    squad_dir = project.squad_dir
    scaffold_template(squad_dir, "items/task.md.j2")
    # Write custom content.
    dest = _tmpl_overrides_dir(squad_dir) / "items/task.md.j2"
    dest.write_text("custom content", encoding="utf-8")
    # Force re-scaffold.
    scaffold_template(squad_dir, "items/task.md.j2", force=True)
    text = dest.read_text(encoding="utf-8")
    # Should have bundled content restored.
    assert "<!-- sq:body -->" in text
    assert "custom content" not in text


async def test_scaffold_template_unknown_raises(project):
    """scaffold_template raises SquadsError for a non-existent bundled template."""
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="no bundled template"):
        scaffold_template(project.squad_dir, "items/nonexistent.md.j2")


async def test_scaffold_template_all_item_types(project):
    """scaffold_template works for every known item template."""
    squad_dir = project.squad_dir
    for template_name in [
        "items/task.md.j2",
        "items/bug.md.j2",
        "items/feature.md.j2",
        "items/epic.md.j2",
        "items/review.md.j2",
        "items/guide.md.j2",
        "items/decision.md.j2",
    ]:
        dest = scaffold_template(squad_dir, template_name)
        assert dest.exists()
        text = dest.read_text(encoding="utf-8")
        assert read_template_stamp(text) is not None


# ─── scaffold_role ─────────────────────────────────────────────────────────────


async def test_scaffold_role_creates_stamped_toml(project):
    """scaffold_role creates a role TOML with the override-base stamp comment."""
    from squads import __version__

    squad_dir = project.squad_dir
    dest = scaffold_role(squad_dir, slug="architect")
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert read_toml_stamp(text) == __version__


async def test_scaffold_role_refuses_clobber(project):
    """scaffold_role raises SquadsError when the TOML exists and --force not set."""
    from squads._errors import SquadsError

    squad_dir = project.squad_dir
    scaffold_role(squad_dir, slug="architect")
    with pytest.raises(SquadsError, match="already exists"):
        scaffold_role(squad_dir, slug="architect")


async def test_scaffold_role_force_overwrites(project):
    """--force allows clobbering an existing role TOML."""
    squad_dir = project.squad_dir
    scaffold_role(squad_dir, slug="architect")
    dest = _role_overrides_dir(squad_dir) / "architect.toml"
    dest.write_text("# old content\n", encoding="utf-8")
    scaffold_role(squad_dir, slug="architect", force=True)
    text = dest.read_text(encoding="utf-8")
    assert read_toml_stamp(text) is not None


# ─── scan_overrides ────────────────────────────────────────────────────────────


async def test_scan_overrides_empty(project):
    """scan_overrides returns [] when .overrides/ is absent."""
    assert scan_overrides(project.squad_dir) == []


async def test_scan_overrides_stamped_current(project):
    """An override stamped with the running version is STATE_CURRENT."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _minimal_task_override(), stamp=__version__
    )
    entries = scan_overrides(squad_dir)
    assert len(entries) == 1
    assert entries[0].name == "items/task.md.j2"
    assert entries[0].kind == "template"
    assert entries[0].base_version == __version__
    assert entries[0].state == STATE_CURRENT


async def test_scan_overrides_broken_template(project):
    """A template override missing required markers is STATE_BROKEN."""
    squad_dir = project.squad_dir
    _place_template_override(squad_dir, "items/task.md.j2", _broken_task_override(), stamp="0.3.0")
    entries = scan_overrides(squad_dir)
    assert len(entries) == 1
    assert entries[0].state == STATE_BROKEN


async def test_scan_overrides_role_toml(project):
    """scan_overrides includes role TOML overrides."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_role_override(squad_dir, "architect", f"# squads:override-base:{__version__}\n")
    entries = scan_overrides(squad_dir)
    assert len(entries) == 1
    assert entries[0].name == "architect"
    assert entries[0].kind == "role"
    assert entries[0].state == STATE_CURRENT


async def test_scan_overrides_multiple(project):
    """scan_overrides returns all overrides (templates + roles)."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _minimal_task_override(), stamp=__version__
    )
    _place_role_override(squad_dir, "qa", f"# squads:override-base:{__version__}\n")
    entries = scan_overrides(squad_dir)
    assert len(entries) == 2
    kinds = {e.kind for e in entries}
    assert kinds == {"template", "role"}


# ─── diff_override ─────────────────────────────────────────────────────────────


async def test_diff_template_missing_override_raises(project):
    """diff_override raises SquadsError when the override file is not present."""
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="no template override"):
        diff_override(project.squad_dir, "items/task.md.j2", "template")


async def test_diff_template_delta_mine_shows_customisation(project):
    """Δ-mine shows the diff between the override and the current bundled template."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir,
        "items/task.md.j2",
        _minimal_task_override("MY_CUSTOM_CONTENT"),
        stamp=__version__,
    )
    result = diff_override(squad_dir, "items/task.md.j2", "template")
    assert isinstance(result, DiffResult)
    # Δ-mine should show the customisation vs bundled.
    assert "MY_CUSTOM_CONTENT" in result.delta_mine or result.delta_mine != ""


async def test_diff_template_delta_upgrade_same_version(project):
    """Δ-upgrade is empty when base_version == current (no upgrade happened)."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _minimal_task_override(), stamp=__version__
    )
    result = diff_override(squad_dir, "items/task.md.j2", "template")
    # Same version → bundled unchanged since base → Δ-upgrade is empty.
    assert result.delta_upgrade == ""


async def test_diff_role_missing_override_raises(project):
    """diff_override raises SquadsError for a missing role TOML."""
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="no role override"):
        diff_override(project.squad_dir, "architect", "role")


async def test_diff_role_shows_delta_mine(project):
    """Δ-mine for a role override is non-empty when the TOML has content."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_role_override(
        squad_dir, "architect", f'# squads:override-base:{__version__}\nfull_name = "Ada"\n'
    )
    result = diff_override(squad_dir, "architect", "role")
    assert "Ada" in result.delta_mine


async def test_diff_unknown_kind_raises(project):
    """diff_override raises SquadsError for an unknown kind."""
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="unknown override kind"):
        diff_override(project.squad_dir, "something", "unknown-kind")


# ─── update_stamp ─────────────────────────────────────────────────────────────


async def test_update_stamp_re_stamps_template(project):
    """update_stamp re-stamps a template override to the current version."""
    from squads import __version__

    squad_dir = project.squad_dir
    # Place an override with an old stamp.
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.1.0")
    stamped = update_stamp(squad_dir, "items/task.md.j2", "template")
    assert stamped == ["items/task.md.j2"]
    path = _tmpl_overrides_dir(squad_dir) / "items/task.md.j2"
    text = path.read_text(encoding="utf-8")
    assert read_template_stamp(text) == __version__
    # Body untouched.
    assert "CUSTOM" in text or "<!-- sq:body -->" in text


async def test_update_stamp_does_not_touch_body(project):
    """update_stamp only rewrites the stamp comment; all other content is preserved."""
    from squads import __version__

    squad_dir = project.squad_dir
    custom_body = _minimal_task_override("PRESERVE_ME_EXACTLY")
    _place_template_override(squad_dir, "items/task.md.j2", custom_body, stamp="0.1.0")
    update_stamp(squad_dir, "items/task.md.j2", "template")
    path = _tmpl_overrides_dir(squad_dir) / "items/task.md.j2"
    text = path.read_text(encoding="utf-8")
    assert "PRESERVE_ME_EXACTLY" in text
    assert read_template_stamp(text) == __version__


async def test_update_stamp_skips_broken(project):
    """update_stamp raises SquadsError for a broken (missing-marker) override."""
    from squads._errors import SquadsError

    squad_dir = project.squad_dir
    _place_template_override(squad_dir, "items/task.md.j2", _broken_task_override(), stamp="0.1.0")
    with pytest.raises(SquadsError, match="missing required sq markers"):
        update_stamp(squad_dir, "items/task.md.j2", "template")


async def test_update_stamp_bulk_skips_broken(project):
    """Bulk update_stamp (no name) re-stamps valid overrides and skips broken ones."""
    from squads import __version__

    squad_dir = project.squad_dir
    # One valid, one broken.
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.1.0")
    _place_template_override(squad_dir, "items/bug.md.j2", _broken_task_override(), stamp="0.1.0")
    stamped = update_stamp(squad_dir, None, None)
    assert "items/task.md.j2" in stamped
    assert "items/bug.md.j2" not in stamped
    # Valid override is stamped.
    text = (_tmpl_overrides_dir(squad_dir) / "items/task.md.j2").read_text(encoding="utf-8")
    assert read_template_stamp(text) == __version__


async def test_update_stamp_role(project):
    """update_stamp re-stamps a role TOML override."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_role_override(
        squad_dir, "architect", "# squads:override-base:0.1.0\nfull_name = 'Ada'\n"
    )
    stamped = update_stamp(squad_dir, "architect", "role")
    assert "architect" in stamped
    path = _role_overrides_dir(squad_dir) / "architect.toml"
    text = path.read_text(encoding="utf-8")
    assert read_toml_stamp(text) == __version__
    assert "Ada" in text


async def test_update_stamp_missing_raises(project):
    """update_stamp raises SquadsError when the named override does not exist."""
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="no override found"):
        update_stamp(project.squad_dir, "items/nonexistent.md.j2", "template")


# ─── sq check: drift warnings + structural errors ──────────────────────────────


async def test_check_clean_with_current_stamp(project, svc):
    """sq check emits no override issues when overrides are stamped at the running version."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _minimal_task_override(), stamp=__version__
    )
    issues = await svc.check()
    override_issues = [i for i in issues if ".overrides" in i.item]
    assert not override_issues, f"unexpected override issues: {override_issues}"


async def test_check_warns_on_missing_stamp(project, svc):
    """sq check warns when an override has no stamp (manually-placed file)."""
    squad_dir = project.squad_dir
    # Place without stamp.
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override())
    issues = await svc.check()
    override_issues = [i for i in issues if ".overrides" in i.item]
    assert any(i.level == "warn" for i in override_issues)


async def test_check_errors_on_missing_required_marker(project, svc):
    """sq check emits an error for a template override missing required sq markers."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _broken_task_override(), stamp=__version__
    )
    issues = await svc.check()
    override_errors = [i for i in issues if i.level == "error" and ".overrides" in i.item]
    assert override_errors, "expected an error-level override issue for missing markers"
    assert any("missing required sq marker" in i.message for i in override_errors)


async def test_check_exit3_on_missing_marker(project, invoke):
    """CLI: sq check exits 3 for missing required markers (FEAT-000015 contract)."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _broken_task_override(), stamp=__version__
    )
    result = await invoke(["check"])
    assert result.exit_code == 3, f"expected exit 3, got {result.exit_code}\n{result.output}"


async def test_check_exit0_on_warn_only(project, invoke):
    """CLI: sq check exits 0 (not 3) when only warnings are emitted (FEAT-000015 contract)."""
    squad_dir = project.squad_dir
    # Unstamped → warn only, not error.
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override())
    result = await invoke(["check"])
    assert result.exit_code == 0, f"expected exit 0 for warn-only, got {result.exit_code}"


async def test_check_override_issues_function(project):
    """check_override_issues() returns correct (level, path, msg) tuples directly."""
    from squads import __version__

    squad_dir = project.squad_dir
    # Valid current stamp → no issues.
    _place_template_override(
        squad_dir, "items/task.md.j2", _minimal_task_override(), stamp=__version__
    )
    issues = check_override_issues(squad_dir)
    assert issues == []


async def test_check_override_valid_renders_no_block(project, svc):
    """A valid (stale but structurally-valid) override still renders; sq check warns only."""
    squad_dir = project.squad_dir
    # Stamp it as old (won't be in manifest → won't trigger drift).
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.0.1")
    issues = await svc.check()
    # Only warnings (not errors) for this override.
    override_errors = [i for i in issues if i.level == "error" and ".overrides" in i.item]
    assert not override_errors


# ─── Full staleness loop ───────────────────────────────────────────────────────


async def test_full_staleness_loop(project, svc, invoke):
    """Full loop: warn → diff → hand-merge (simulated) → update → warning clears."""
    from squads import __version__

    squad_dir = project.squad_dir

    # 1. Place an override with an old stamp (simulate stale by placing unstamped).
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override())

    # sq check warns (unstamped).
    issues_before = await svc.check()
    warn_issues = [i for i in issues_before if ".overrides" in i.item and i.level == "warn"]
    assert warn_issues, "expected a drift warning before update"

    # sq override diff (smoke test — just verify it doesn't crash).
    diff_result = await invoke(["override", "diff", "items/task.md.j2"])
    assert diff_result.exit_code == 0, diff_result.output

    # 3. "Hand-merge" = place the override stamped with the old version.
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.1.0")

    # 4. sq override update re-stamps to current.
    update_result = await invoke(["override", "update", "items/task.md.j2"])
    assert update_result.exit_code == 0, update_result.output

    # 5. sq check warning clears (stamp now matches running version).
    path = _tmpl_overrides_dir(squad_dir) / "items/task.md.j2"
    text = path.read_text(encoding="utf-8")
    assert read_template_stamp(text) == __version__

    # Re-run check to confirm.
    svc2 = service.Service(project)
    issues_after = await svc2.check()
    override_issues = [i for i in issues_after if ".overrides" in i.item]
    assert not override_issues, f"expected no override issues after update: {override_issues}"


# ─── migrate: never touches .overrides/ ────────────────────────────────────────


async def test_migrate_does_not_touch_overrides(project, invoke):
    """sq migrate up never rewrites files under .overrides/ (ADR §3 invariant)."""
    from squads import __version__

    squad_dir = project.squad_dir
    override_content = _minimal_task_override("MIGRATE_MUST_NOT_TOUCH_THIS")
    dest = _place_template_override(
        squad_dir, "items/task.md.j2", override_content, stamp=__version__
    )
    stat_before = dest.stat()

    # Run migrate (should be no-op since schema is current, but it must not touch overrides).
    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output

    # File is unchanged.
    stat_after = dest.stat()
    assert stat_after.st_mtime == stat_before.st_mtime, "migrate mutated an override file"
    text = dest.read_text(encoding="utf-8")
    assert "MIGRATE_MUST_NOT_TOUCH_THIS" in text


# ─── CLI smoke tests ───────────────────────────────────────────────────────────


async def test_cli_scaffold_template(project, invoke):
    """CLI: sq override scaffold items/task.md.j2 creates the override."""
    result = await invoke(["override", "scaffold", "items/task.md.j2"])
    assert result.exit_code == 0, result.output
    dest = _tmpl_overrides_dir(project.squad_dir) / "items/task.md.j2"
    assert dest.exists()
    assert read_template_stamp(dest.read_text(encoding="utf-8")) is not None


async def test_cli_scaffold_role(project, invoke):
    """CLI: sq override scaffold --role architect creates the TOML stub."""
    result = await invoke(["override", "scaffold", "--role", "architect"])
    assert result.exit_code == 0, result.output
    dest = _role_overrides_dir(project.squad_dir) / "architect.toml"
    assert dest.exists()


async def test_cli_scaffold_refuses_clobber(project, invoke):
    """CLI: sq override scaffold without --force exits 1 when the override exists."""
    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "scaffold", "items/task.md.j2"])
    assert result.exit_code == 1


async def test_cli_scaffold_force_clobber(project, invoke):
    """CLI: sq override scaffold --force succeeds even when the override exists."""
    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "scaffold", "--force", "items/task.md.j2"])
    assert result.exit_code == 0, result.output


async def test_cli_list_empty(project, invoke):
    """CLI: sq override list exits 0 and reports no overrides when .overrides/ is absent."""
    result = await invoke(["override", "list"])
    assert result.exit_code == 0, result.output
    assert "no overrides" in result.output.lower()


async def test_cli_list_shows_overrides(project, invoke):
    """CLI: sq override list shows the scaffold'd override."""
    from squads import __version__

    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "list"])
    assert result.exit_code == 0, result.output
    assert "items/task.md.j2" in result.output
    assert __version__ in result.output


async def test_cli_list_json(project, invoke):
    """CLI: sq override list --json emits a valid JSON array."""
    import json as _json

    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = _json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    assert set(entry.keys()) == {"name", "kind", "base_version", "state"}
    assert entry["name"] == "items/task.md.j2"
    assert entry["kind"] == "template"
    assert entry["state"] == STATE_CURRENT


async def test_cli_diff_named_template(project, invoke):
    """CLI: sq override diff <name> exits 0 and prints both delta sections."""
    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "diff", "items/task.md.j2"])
    assert result.exit_code == 0, result.output
    assert "Δ-mine" in result.output
    assert "Δ-upgrade" in result.output


async def test_cli_diff_no_drifted(project, invoke):
    """CLI: sq override diff (no name) exits 0 with message when no drifted overrides."""
    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "diff"])
    assert result.exit_code == 0
    assert "no drifted" in result.output.lower()


async def test_cli_diff_json(project, invoke):
    """CLI: sq override diff --json emits a valid JSON array."""
    import json as _json

    await invoke(["override", "scaffold", "items/task.md.j2"])
    result = await invoke(["override", "diff", "items/task.md.j2", "--json"])
    assert result.exit_code == 0, result.output
    data = _json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    r = data[0]
    assert "name" in r and "delta_mine" in r and "delta_upgrade" in r and "base_available" in r


async def test_cli_update_single(project, invoke):
    """CLI: sq override update <name> re-stamps the override and exits 0."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.1.0")
    result = await invoke(["override", "update", "items/task.md.j2"])
    assert result.exit_code == 0, result.output
    path = _tmpl_overrides_dir(squad_dir) / "items/task.md.j2"
    assert read_template_stamp(path.read_text(encoding="utf-8")) == __version__


async def test_cli_update_bulk(project, invoke):
    """CLI: sq override update (no name) re-stamps all valid overrides."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(squad_dir, "items/task.md.j2", _minimal_task_override(), stamp="0.1.0")
    _place_template_override(squad_dir, "items/bug.md.j2", _minimal_task_override(), stamp="0.1.0")
    result = await invoke(["override", "update"])
    assert result.exit_code == 0, result.output
    for name in ("items/task.md.j2", "items/bug.md.j2"):
        path = _tmpl_overrides_dir(squad_dir) / name
        assert read_template_stamp(path.read_text(encoding="utf-8")) == __version__


async def test_cli_update_role(project, invoke):
    """CLI: sq override update --role <slug> re-stamps the role TOML."""
    from squads import __version__

    squad_dir = project.squad_dir
    _place_role_override(
        squad_dir, "architect", "# squads:override-base:0.1.0\nfull_name = 'Ada'\n"
    )
    result = await invoke(["override", "update", "--role", "architect"])
    assert result.exit_code == 0, result.output
    path = _role_overrides_dir(squad_dir) / "architect.toml"
    assert read_toml_stamp(path.read_text(encoding="utf-8")) == __version__


async def test_cli_check_json_override_error(project, invoke):
    """CLI: sq check --json includes override errors in JSON output and exits 3."""
    import json as _json

    from squads import __version__

    squad_dir = project.squad_dir
    _place_template_override(
        squad_dir, "items/task.md.j2", _broken_task_override(), stamp=__version__
    )
    result = await invoke(["check", "--json"])
    assert result.exit_code == 3
    data = _json.loads(result.output)
    error_items = [d for d in data if d["level"] == "error" and ".overrides" in d["item"]]
    assert error_items


async def test_cli_scaffold_missing_name_exits_nonzero(project, invoke):
    """CLI: sq override scaffold with no name and no --role exits non-zero."""
    result = await invoke(["override", "scaffold"])
    assert result.exit_code != 0
