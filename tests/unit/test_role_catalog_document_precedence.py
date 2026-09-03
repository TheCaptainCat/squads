"""The role-override precedence: bundled base -> the catalog document
(``.overrides/roles.toml``) -> a per-slug ``.overrides/roles/<slug>.toml`` file, most specific
last. Exercises the seam :func:`~squads._roles._resolver.resolve_role`/``resolve_role_with_base``
share with every existing caller — no call-site change was needed for the catalog-document layer
to take effect.
"""

from pathlib import Path

from squads._roles._catalog import PREDEFINED
from squads._roles._loader import load_role_catalog
from squads._roles._resolver import project_role_slugs, resolve_dev_role, resolve_role


def _bundled_all_bundle() -> list[str]:
    return load_role_catalog().bundles["all"]


def _write_catalog_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "roles.toml").write_text(content, encoding="utf-8")


def _write_slug_override(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_no_catalog_document_resolves_exactly_the_bundled_role(tmp_path: Path) -> None:
    bundled = next(r for r in PREDEFINED if r.slug == "architect")
    assert resolve_role("architect", tmp_path) == bundled


def test_catalog_document_field_overrides_a_bundled_role(tmp_path: Path) -> None:
    _write_catalog_override(tmp_path, '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\n')
    resolved = resolve_role("architect", tmp_path)
    bundled = next(r for r in PREDEFINED if r.slug == "architect")

    assert resolved.title == "Chief Architect"
    assert resolved.mission == bundled.mission  # untouched field falls through


def test_a_per_slug_file_wins_over_the_catalog_document_for_the_same_field(
    tmp_path: Path,
) -> None:
    _write_catalog_override(tmp_path, '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\n')
    _write_slug_override(tmp_path, "architect", 'title = "Principal Architect"\n')

    resolved = resolve_role("architect", tmp_path)

    assert resolved.title == "Principal Architect"


def test_a_per_slug_file_still_inherits_a_field_the_catalog_document_set(
    tmp_path: Path,
) -> None:
    """The per-slug file only overrides the field it names — the catalog document's own
    override of a *different* field survives underneath it, proving the merge is three-layer
    (bundled -> catalog -> per-slug), not a two-layer catalog-vs-per-slug replace."""
    _write_catalog_override(tmp_path, '[[roles]]\nslug = "architect"\ncolor = "purple"\n')
    _write_slug_override(tmp_path, "architect", 'title = "Principal Architect"\n')

    resolved = resolve_role("architect", tmp_path)

    assert resolved.title == "Principal Architect"
    assert resolved.color == "purple"


def test_a_catalog_document_only_new_slug_resolves_with_no_per_slug_file(
    tmp_path: Path,
) -> None:
    all_with_new = [*_bundled_all_bundle(), "security-analyst"]
    _write_catalog_override(
        tmp_path,
        f"""
        [[roles]]
        slug = "security-analyst"
        full_name = "Sam Security"
        title = "security analyst"
        description = "Reviews the project for security issues."
        mission = "Find and report security issues before they ship."

        [bundles]
        all = {all_with_new!r}
        """,
    )
    resolved = resolve_role("security-analyst", tmp_path)
    assert resolved.full_name == "Sam Security"


def test_a_catalog_document_only_new_slug_is_counted_as_a_project_role_slug(
    tmp_path: Path,
) -> None:
    all_with_new = [*_bundled_all_bundle(), "security-analyst"]
    _write_catalog_override(
        tmp_path,
        f"""
        [[roles]]
        slug = "security-analyst"
        full_name = "Sam Security"
        title = "security analyst"
        description = "Reviews the project for security issues."
        mission = "Find and report security issues before they ship."

        [bundles]
        all = {all_with_new!r}
        """,
    )
    assert "security-analyst" in project_role_slugs(tmp_path)


def test_dev_pool_override_reaches_a_newly_generated_dev_role(tmp_path: Path) -> None:
    _write_catalog_override(tmp_path, '[dev]\nmodel = "opus"\n')
    resolved = resolve_dev_role("rust", squad_dir=tmp_path)
    assert resolved.model == "opus"


def test_dev_pool_override_does_not_apply_with_no_squad_dir(tmp_path: Path) -> None:
    resolved = resolve_dev_role("rust")
    assert resolved.model == "sonnet"  # the bundled default, unaffected by any override
