"""The override manifest + stamp mechanics: the shipped manifest carries a current-version
hash for every bundled template with no missing/extra/stale entry (the manifest-freshness
guard — a template edit without re-running the generator script fails loudly, not silently),
`template_changed_since` is version-aware, and the template/TOML stamp comment round-trips
insert-vs-replace. `sq override` command behaviour lives in
tests/integration/test_override_scaffold_scan_diff_update_and_check.py.
"""

import hashlib
import importlib.resources as pkg_resources

from squads import __version__
from squads._overrides._manifest import (
    _load_manifest,  # pyright: ignore[reportPrivateUsage]
    bundled_template_content,
    current_template_hash,
    invalidate_cache,
    template_changed_since,
    template_hash_at_version,
)
from squads._overrides._stamp import (
    read_template_stamp,
    read_toml_stamp,
    write_template_stamp,
    write_toml_stamp,
)


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


def test_the_manifest_has_a_current_version_sha256_hash_for_every_bundled_template() -> None:
    invalidate_cache()
    installed = _installed_template_hashes()
    assert installed, "no bundled templates found — package data misconfigured?"

    manifest_entry = _load_manifest().get(__version__)
    assert manifest_entry is not None, f"manifest has no entry for v{__version__}"

    missing = set(installed) - set(manifest_entry)
    extra = set(manifest_entry) - set(installed)
    mismatched = {name for name, actual in installed.items() if manifest_entry.get(name) != actual}
    assert not missing, f"manifest is missing hashes for: {sorted(missing)}"
    assert not extra, f"manifest records hashes for non-existent templates: {sorted(extra)}"
    assert not mismatched, f"manifest hashes are stale for: {sorted(mismatched)}"

    one_hash = template_hash_at_version("items/task.md.j2", __version__)
    assert one_hash is not None and len(one_hash) == 64  # SHA-256 hex


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
