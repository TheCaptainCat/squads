"""Every call to ``view_tag(...)`` under ``src/squads``, attribute-style or bare-name, must be
one of a fully-enumerated set of known sites, each classified as gated, self-gated,
deliberately-ungated, or not actually a writer. A separate section does the same for the
literal ``sq:view:<name>`` tags a Jinja template writes directly."""

import ast
import re
from pathlib import Path

# --------------------------------------------------------------------------- discovery


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _enclosing_function_qualname(stack: list[str]) -> str:
    return ".".join(stack) if stack else "<module>"


def _view_tag_call_sites(src_root: Path) -> list[tuple[str, str, int]]:
    """``(module-relative-posix-path, enclosing function's name, line number)`` for every call to
    ``view_tag(...)`` under *src_root*, attribute-style or bare-name."""
    sites: list[tuple[str, str, int]] = []
    for path in sorted(src_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        rel = path.relative_to(src_root.parent).as_posix()
        _collect_view_tag_calls(tree, rel, [], sites)
    return sites


def _collect_view_tag_calls(
    node: ast.AST, rel: str, stack: list[str], sites: list[tuple[str, str, int]]
) -> None:
    """Recursive tree walk, factored out of :func:`_view_tag_call_sites`."""
    for child in ast.iter_child_nodes(node):
        child_stack = stack
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            child_stack = [*stack, child.name]
        if isinstance(child, ast.Call) and (
            (isinstance(child.func, ast.Attribute) and child.func.attr == "view_tag")
            or (isinstance(child.func, ast.Name) and child.func.id == "view_tag")
        ):
            sites.append((rel, _enclosing_function_qualname(child_stack), child.lineno))
        _collect_view_tag_calls(child, rel, child_stack, sites)


def test_the_ast_scan_finds_a_call_a_raw_substring_grep_would_miss() -> None:
    """An AST walk finds a call wrapped across a line break, which a raw substring grep would
    miss."""
    adversarial = "def g() -> None:\n    tag = (markers\n        .view_tag(name))\n"
    assert "markers.view_tag(" not in adversarial, (
        "fixture no longer demonstrates a raw substring false zero"
    )

    tree = ast.parse(adversarial)
    found = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "view_tag"
        for n in ast.walk(tree)
    )
    assert found, "the AST-based scan must find a call a raw substring grep misses"


def test_a_bare_name_view_tag_call_is_discovered_too() -> None:
    """A bare-name call reached through a direct import is discovered the same as an
    attribute-style one."""
    synthetic = "def h() -> None:\n    return markers.open_marker(view_tag(name))\n"
    assert "markers.view_tag(" not in synthetic, (
        "fixture no longer demonstrates the bare-name shape"
    )

    tree = ast.parse(synthetic)
    sites: list[tuple[str, str, int]] = []
    _collect_view_tag_calls(tree, "synthetic.py", [], sites)

    assert sites == [("synthetic.py", "h", 2)], (
        "the scanner must also match a bare-name view_tag(...) call, not only the "
        "attribute-style markers.view_tag(...) form"
    )


# --------------------------------------------------------------------------- classification

#: (relative path, enclosing function) -> (classification, reason). Exactly the sites this
#: codebase has today — a mismatch below is the whole point: this dict is a completeness
#: claim, not a convenience cache.
CLASSIFICATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("squads/_services/_maintenance.py", "_converge_body_tag"): (
        "gated",
        "gated at its caller, _repair_body_tag's own classifier — never invoked with a view "
        "name the active spec does not declare",
    ),
    ("squads/_migrations/_v0_14_to_v0_15.py", "_reclaim_legacy_roster_bodies"): (
        "gated",
        "view_name comes from roster_body_view_name, which already returns None for a view "
        "not currently declared in spec.views — the loop continues before ever reaching the "
        "write for an undeclared name",
    ),
    ("squads/_migrations/_v0_14_to_v0_15.py", "_tag_present_outside_region"): (
        "not-a-writer",
        "builds both the enabled and disabled tag strings only to check for their presence in "
        "the file's text; writes nothing",
    ),
    ("squads/_views.py", "place_view_tags"): (
        "deliberately-ungated",
        "the one re-placement routine every writer of a sq:body region drives — it must be "
        "able to write ANY name, declared or not: an "
        "undeclared tag already present is carried forward verbatim (the recovery path "
        "inherited by `view disable`'s `force=` argument), and a gated caller "
        "(`view add`, via resolve_view_target) applies its own gate before ever calling this, "
        "never inside it",
    ),
    ("squads/_services/_items.py", "_reject_unwritable_body"): (
        "not-a-writer",
        "composes the bare tag for the roster refusal's own error message only; writes nothing",
    ),
    ("squads/_views.py", "_resolve_final_states"): (
        "not-a-writer",
        "composes the bare tag for ConflictingViewStateError's own message only; writes nothing",
    ),
    ("squads/_services/_maintenance.py", "_seeded_view_issues"): (
        "not-a-writer",
        "composes the bare or full tag for its own check-finding messages only; writes nothing",
    ),
}

_VALID_CLASSIFICATIONS = frozenset({"gated", "self-gated", "deliberately-ungated", "not-a-writer"})


def test_every_classification_label_is_one_of_the_four_known_shapes() -> None:
    """A typo'd classification label in the table above is caught before the check below."""
    for site, (label, _reason) in CLASSIFICATIONS.items():
        assert label in _VALID_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_the_discovered_sites_are_exactly_the_classified_set() -> None:
    src_root = _repo_root() / "src" / "squads"
    discovered = {(rel, qualname) for rel, qualname, _line in _view_tag_call_sites(src_root)}
    expected = set(CLASSIFICATIONS)

    missing = expected - discovered
    assert not missing, f"expected writer site(s) no longer found (renamed or removed?): {missing}"

    extra = discovered - expected
    assert not extra, (
        f"unclassified view_tag call site(s) found — classify each in CLASSIFICATIONS above, "
        f"or this is a new writer that needs its own spec.views gate: {extra}"
    )


# --------------------------------------------------------------------------- gate verification
#
# Each ``gated`` site's protecting behavioural test declares itself via
# ``@pytest.mark.gate_for("<module-relative-path>::<function>")`` (registered in
# ``pyproject.toml``'s ``markers``), so a citation cannot exist without a test claiming the job.
# A citation is refused when its own test is skip/skipif/xfail/slow-marked (not collected by
# default) or when more than one test claims the same site (ambiguous ownership).
#
# This does not prove the cited test's assertions actually falsify the gate — that is a
# mutation-testing question, not a static one.


def _gated_sites() -> set[tuple[str, str]]:
    return {s for s, (label, _reason) in CLASSIFICATIONS.items() if label == "gated"}


def _tests_root() -> Path:
    return _repo_root() / "tests"


_EXCLUDED_MARK_NAMES = frozenset({"skip", "skipif", "xfail", "slow"})


def _pytest_mark_name(deco: ast.expr) -> str | None:
    """The bare mark name of *deco* if it is a ``pytest.mark.<name>`` decorator, else None."""
    target = deco.func if isinstance(deco, ast.Call) else deco
    if (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Attribute)
        and target.value.attr == "mark"
        and isinstance(target.value.value, ast.Name)
        and target.value.value.id == "pytest"
    ):
        return target.attr
    return None


def _is_excluded_from_default_collection(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether *node* carries a mark that keeps it from running in a bare, default collection."""
    return any(_pytest_mark_name(d) in _EXCLUDED_MARK_NAMES for d in node.decorator_list)


def _gate_for_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Every site string named by a ``@pytest.mark.gate_for("...")`` decorator on *node*."""
    sites = []
    for deco in node.decorator_list:
        if _pytest_mark_name(deco) != "gate_for" or not isinstance(deco, ast.Call):
            continue
        sites.extend(
            arg.value
            for arg in deco.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        )
    return sites


#: site-citation-string -> every (test-relative-path, test-function-name,
#: excluded-from-default-collection) that decorates itself with ``@pytest.mark.gate_for(site)``.
def _gate_for_sites_in_module(source: str, rel: str) -> dict[str, list[tuple[str, str, bool]]]:
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError:
        return {}
    mapping: dict[str, list[tuple[str, str, bool]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        excluded = _is_excluded_from_default_collection(node)
        for site in _gate_for_args(node):
            mapping.setdefault(site, []).append((rel, node.name, excluded))
    return mapping


def _gate_for_sites(tests_root: Path) -> dict[str, list[tuple[str, str, bool]]]:
    """The same mapping as :func:`_gate_for_sites_in_module`, collected across *tests_root*."""
    mapping: dict[str, list[tuple[str, str, bool]]] = {}
    for path in sorted(tests_root.rglob("*.py")):
        rel = path.relative_to(tests_root.parent).as_posix()
        for site, owners in _gate_for_sites_in_module(
            path.read_text(encoding="utf-8"), rel
        ).items():
            mapping.setdefault(site, []).extend(owners)
    return mapping


def _owners_by_site_tuple(
    owners: dict[str, list[tuple[str, str, bool]]],
) -> dict[tuple[str, str], list[tuple[str, str, bool]]]:
    """Re-key a ``_gate_for_sites`` result to the ``CLASSIFICATIONS`` tuple shape."""
    out: dict[tuple[str, str], list[tuple[str, str, bool]]] = {}
    for site, tests in owners.items():
        rel, _sep, func = site.partition("::")
        out[(rel, func)] = tests
    return out


def test_the_marker_scan_finds_a_bare_gate_for_citation() -> None:
    """A bare ``@pytest.mark.gate_for`` citation is discovered against a known positive."""
    source = (
        "import pytest\n\n"
        "@pytest.mark.gate_for('squads/_x.py::_y')\n"
        "async def test_z() -> None:\n    pass\n"
    )
    owners = _gate_for_sites_in_module(source, "tests/synthetic.py")
    assert owners == {"squads/_x.py::_y": [("tests/synthetic.py", "test_z", False)]}


def test_every_gated_site_has_exactly_one_behavioural_test_citation() -> None:
    """Every ``gated`` site has exactly one ``@pytest.mark.gate_for`` citation, no more, no
    fewer, and nothing cites a site that is not ``gated``."""
    gated = _gated_sites()
    owners = _owners_by_site_tuple(_gate_for_sites(_tests_root()))

    missing = gated - set(owners)
    assert not missing, f"gated site(s) with no @pytest.mark.gate_for citation: {missing}"

    extra = set(owners) - gated
    assert not extra, f"@pytest.mark.gate_for citation for a non-gated (or unknown) site: {extra}"

    ambiguous = {
        site: [f"{rel}::{name}" for rel, name, _excluded in tests]
        for site, tests in owners.items()
        if len(tests) > 1
    }
    assert not ambiguous, (
        f"gated site(s) claimed by more than one @pytest.mark.gate_for citation — a site must "
        f"have exactly one declared owner: {ambiguous}"
    )


def test_a_repointed_citation_is_refused_as_ambiguous_ownership() -> None:
    """A second test decorating itself for an already-claimed site leaves two declared owners,
    refused as ambiguous ownership rather than a silent substitution."""
    source = (
        "import pytest\n\n"
        "@pytest.mark.gate_for('squads/_x.py::_y')\n"
        "async def test_the_true_owner() -> None:\n    pass\n\n"
        "@pytest.mark.gate_for('squads/_x.py::_y')\n"
        "async def test_an_uninvolved_sibling_repointed_to_the_same_site() -> None:\n    pass\n"
    )
    owners = _gate_for_sites_in_module(source, "tests/synthetic.py")
    claimants = [name for _rel, name, _excluded in owners["squads/_x.py::_y"]]
    assert claimants == [
        "test_the_true_owner",
        "test_an_uninvolved_sibling_repointed_to_the_same_site",
    ], "fixture no longer demonstrates two tests both citing the same site"
    assert len(owners["squads/_x.py::_y"]) > 1, (
        "a re-pointed citation must be discovered as a second claimant, not a silent swap"
    )


def test_every_gate_for_citation_is_collected_and_live() -> None:
    """None of the real corpus's citations are skip/skipif/xfail/slow-marked."""
    owners = _gate_for_sites(_tests_root())
    excluded = {
        site: [f"{rel}::{name}" for rel, name, is_excluded in tests if is_excluded]
        for site, tests in owners.items()
    }
    excluded = {site: names for site, names in excluded.items() if names}
    assert not excluded, (
        f"@pytest.mark.gate_for citation(s) whose test is skip/skipif/xfail/slow-marked — not "
        f"collected by default, so it proves nothing: {excluded}"
    )


def test_a_skip_marked_citation_is_refused() -> None:
    """A skip-marked citation still carries its `gate_for` marker but is flagged excluded."""
    source = (
        "import pytest\n\n"
        "@pytest.mark.gate_for('squads/_x.py::_y')\n"
        "@pytest.mark.skip(reason='flaky in CI, re-enable later')\n"
        "async def test_a_flaky_citation() -> None:\n    pass\n"
    )
    owners = _gate_for_sites_in_module(source, "tests/synthetic.py")
    (_rel, _name, excluded) = owners["squads/_x.py::_y"][0]
    assert excluded, (
        "a skip-marked citation must be flagged excluded from default collection, not treated "
        "as a live proof"
    )


# --------------------------------------------------------------------------- template literals

#: A literal ``sq:view:<name>`` tag written directly into a Jinja template, invisible to the
#: Python scan above. Whitespace-tolerant between each token boundary.
_TEMPLATE_VIEW_TAG_RE = re.compile(r"sq\s*:\s*view\s*:\s*([A-Za-z0-9_]+)")


def _templates_root() -> Path:
    return _repo_root() / "src" / "squads" / "_rendering" / "templates"


def _template_view_tag_sites(templates_root: Path) -> dict[str, list[str]]:
    """template-relative-posix-path -> every view name a literal ``sq:view:`` tag names in that
    file, in file order."""
    hits: dict[str, list[str]] = {}
    for path in sorted(templates_root.rglob("*.j2")):
        text = path.read_text(encoding="utf-8")
        names = [m.group(1) for m in _TEMPLATE_VIEW_TAG_RE.finditer(text)]
        if names:
            hits[path.relative_to(templates_root).as_posix()] = names
    return hits


def test_the_template_scan_finds_a_tag_a_raw_substring_grep_would_miss() -> None:
    """The whitespace-tolerant regex finds a tag wrapped across a line, unlike a raw substring
    search."""
    adversarial = "<!-- sq:view:\n    role_definition -->\n"
    assert "sq:view:role_definition" not in adversarial, (
        "fixture no longer demonstrates a raw substring false zero"
    )

    names = [m.group(1) for m in _TEMPLATE_VIEW_TAG_RE.finditer(adversarial)]
    assert names == ["role_definition"], (
        "the template scan must find a tag a raw substring search misses"
    )


#: template-relative-path -> (classification, reason). Same completeness contract as
#: ``CLASSIFICATIONS`` above, over the template writer class the Python-only scan cannot see.
TEMPLATE_CLASSIFICATIONS: dict[str, tuple[str, str]] = {
    "agents/role.md.j2": (
        "neutralized-by-overwrite",
        "the creation scaffold's static tag: _create_core unconditionally overwrites a role's "
        "sq:body region on the one path that renders this template, so the static tag can "
        "never survive on disk as a value — pristine_body, _template_for's only other "
        "consumer, is unreachable for a role because set_body raises first",
    ),
    "items/milestone.md.j2": (
        "neutralized-by-overwrite",
        "the creation scaffold's static tag: _create_core strips every template tag before "
        "placement and re-seeds only from seeded_view_names, so it never survives on disk "
        "when milestone_rollup is deselected",
    ),
}

_VALID_TEMPLATE_CLASSIFICATIONS = frozenset({"neutralized-by-overwrite", "unconditional-seed"})


def test_every_template_classification_label_is_a_known_shape() -> None:
    for site, (label, _reason) in TEMPLATE_CLASSIFICATIONS.items():
        assert label in _VALID_TEMPLATE_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_the_discovered_template_tags_are_exactly_the_classified_two() -> None:
    discovered = set(_template_view_tag_sites(_templates_root()))
    expected = set(TEMPLATE_CLASSIFICATIONS)

    missing = expected - discovered
    assert not missing, f"expected template tag site(s) no longer found: {missing}"

    extra = discovered - expected
    assert not extra, (
        f"unclassified sq:view: template literal(s) found — classify each in "
        f"TEMPLATE_CLASSIFICATIONS above: {extra}"
    )


def test_a_second_template_writer_is_caught_unclassified(tmp_path: Path) -> None:
    """A static tag added inside a skill template's ``sq:body`` region, unclassified, is
    caught by the extended scan against a copied fixture tree, never the real template."""
    import shutil

    copy_root = tmp_path / "templates"
    shutil.copytree(_templates_root(), copy_root)
    skill_tpl = copy_root / "agents" / "skill.md.j2"
    text = skill_tpl.read_text(encoding="utf-8")
    seeded = text.replace(
        "<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:milestone_rollup -->", 1
    )
    assert seeded != text, "fixture template no longer has an sq:body marker to seed into"
    skill_tpl.write_text(seeded, encoding="utf-8")

    discovered = set(_template_view_tag_sites(copy_root))
    extra = discovered - set(TEMPLATE_CLASSIFICATIONS)
    assert extra == {"agents/skill.md.j2"}, (
        f"the constructed second writer must be discovered as unclassified: {extra}"
    )

    assert set(_template_view_tag_sites(_templates_root())) == set(TEMPLATE_CLASSIFICATIONS)
