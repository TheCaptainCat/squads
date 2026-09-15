"""Every call to ``view_tag(...)`` under ``src/squads`` — attribute-style (``markers.view_tag(
...)``) or bare-name (``view_tag(...)``, reached through a direct ``from squads._models._markers
import view_tag``) — must be one of a small, fully-enumerated set of known sites, each classified
as exactly one of four things — a site that seeds a ``sq:view:<name>`` placement tag with no
check that *name* is actually declared (``gated``, the wrong shape unless its own source proves a
spec.views gate protects it), a site that refuses through the shared resolver before ever seeding
anything of its own (``self-gated``), a site that must keep working precisely for an undeclared
name because it is the recovery path for one (``deliberately-ungated``), or a site that builds
the tag string only to compare it against on-disk content and writes nothing at all
(``not-a-writer``).

The declaration site names its own writers two lines above the constants themselves
(``_interactions/__init__.py``'s ``SYSTEM_SKILL_VIEW_NAMES``/``ITEM_SKILL_VIEW_NAME``
docstrings) — this test is the sweep that makes sure every writer that comment points at is
actually accounted for, so a future seventh site fails outright instead of surviving three
review rounds unnoticed the way one of the six below did. Matching only the attribute-style call
was itself one more instance of that same shape — driven by the reviewer, who added a bare-name
seventh writer in an isolated worktree and found all six tests here passing regardless (see
``test_a_bare_name_view_tag_call_is_discovered_too`` below).
"""

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
    ``view_tag(...)`` under *src_root*, attribute-style or bare-name — walks the parsed AST
    rather than grepping raw text, which is what keeps this immune to a call the formatter has
    line-wrapped mid-expression (a plain line grep can return a false zero on that shape — see
    ``test_the_ast_scan_finds_a_call_a_raw_substring_grep_would_miss`` below, which proves the
    mechanism against a constructed positive before this function's count of six is trusted)."""
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
    """Recursive tree walk, factored out of :func:`_view_tag_call_sites` so *rel* is an
    explicit parameter rather than a variable a nested closure would capture from its
    enclosing loop (every recursive call is made synchronously within the same iteration, so
    capturing would in fact be safe here, but an explicit parameter is what makes that true by
    construction instead of by argument)."""
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
    """Validates the discovery mechanism itself against a known positive before its count of
    six sites (below) is trusted — the false-zero rule: a formatter can wrap a call across a
    line break inside the dotted attribute access itself (splitting on the dot, not just on an
    argument list), which a raw substring/line grep for ``"markers.view_tag("`` does not match
    but the AST walk still resolves correctly, because it parses structure, not lines."""
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
    """The discovery filter originally matched only attribute-style calls (``markers.view_tag(
    ...)``, ``child.func`` an ``ast.Attribute``). A bare-name call reached the same way through
    a direct import — ``from squads._models._markers import view_tag`` then ``view_tag(name)``,
    an ``ast.Name`` — is a different shape the six real sites happen never to use, but nothing
    stops a seventh writer from using it: driven by the reviewer, who added exactly this shape
    to an isolated worktree and found all six tests here still passing, because the writer was
    never discovered in the first place. Uses the real production scanner
    (:func:`_collect_view_tag_calls`), not a reimplementation, so this only passes once the
    scanner itself is widened."""
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

#: (relative path, enclosing function) -> (classification, reason). Exactly the six sites this
#: codebase has today — an ``AssertionError`` below for any discovered site not a key here, or
#: any key here no longer discovered, is the whole point: this dict is a completeness claim,
#: not a convenience cache.
CLASSIFICATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("squads/_services/_base.py", "_create_core"): (
        "gated",
        "role-definition tag seeded only under self.spec.views (the template's own static tag "
        "is overridden with an empty region otherwise)",
    ),
    ("squads/_services/_maintenance.py", "_converge_body_tag"): (
        "gated",
        "gated at its caller, _repair_body_tag's own classifier — never invoked with a view "
        "name the active spec does not declare",
    ),
    ("squads/_backends/_claude_code/_backend.py", "_write_managed_skill"): (
        "gated",
        "every caller resolves body_tag against spec.views before calling, passing None when "
        "the view is undeclared",
    ),
    ("squads/_services/_views.py", "insert_view"): (
        "self-gated",
        "refuses through resolve_view_target before ever writing (see that function's own "
        "docstring)",
    ),
    ("squads/_services/_views.py", "remove_view"): (
        "deliberately-ungated",
        "the recovery path for a tag whose view was dropped out from under it; must keep "
        "working precisely when the name is no longer declared",
    ),
    ("squads/_services/_validators.py", "_item_skill_shadowed"): (
        "not-a-writer",
        "builds tag_line only to compare against on-disk content for a check finding; writes "
        "nothing",
    ),
}

_VALID_CLASSIFICATIONS = frozenset({"gated", "self-gated", "deliberately-ungated", "not-a-writer"})


def test_every_classification_label_is_one_of_the_four_known_shapes() -> None:
    """Cheap self-check on the table above, independent of the discovery scan: catches a typo'd
    label before it could ever silently pass the completeness check below."""
    for site, (label, _reason) in CLASSIFICATIONS.items():
        assert label in _VALID_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_the_discovered_sites_are_exactly_the_classified_six() -> None:
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
# What used to live here was a source-text proxy: `\bin\s+(?:self\s*\.\s*)?spec\s*\.\s*views\b`
# searched for a `spec.views` mention somewhere in a gated site's declared target, and called
# that "the gate exists". It proved a mention existed, not that it guarded the seed — driven by
# the reviewer: with the three real gates removed and one *unused* `in spec.views` mention added
# to each target instead, all six tests in this module still passed. That shape is not
# adversarial; a function computing a declared-views list for one purpose while seeding a tag
# for another is ordinary growth in this file, and the proxy could not tell the two apart.
#
# The replacement was a hand-maintained dict citing, per gated site, the exact behavioural test
# whose own falsification proves that gate — and that dict was itself gameable one level out,
# because it pointed *at* a test rather than being declared *by* one: re-pointing a citation to
# a real, currently-passing, uninvolved sibling test cost one line here and no edit to that
# test's own source, and the resolution check (does the name exist?) could not tell the
# difference. A `@pytest.mark.skip` on the real cited test was the same gap in its accidental
# form — the citation still "resolved" because a decorator is invisible to a bare
# `ast.FunctionDef` name lookup.
#
# So the citation is inverted: the behavioural test declares the site it proves, on itself, via
# `@pytest.mark.gate_for("<module-relative-path>::<function>")` (registered in
# `pyproject.toml`'s `markers`). The map below is *collected* from those markers rather than
# hand-maintained, so a citation cannot exist without a test claiming the job, and this module
# additionally refuses a citation whose own test is `skip`/`skipif`/`xfail`-marked or carries
# `@pytest.mark.slow` (this repo's one default-collection exclusion — see
# `tests/conftest.py::pytest_collection_modifyitems`) — "collected and live" is checkable
# without executing anything.
#
# What this deliberately does *not* close, and must not be read as closing: whether the cited
# test's *assertions* actually falsify the gate is only knowable by mutating the gate and
# running it — mutation testing, not a static check. Each of the three citations below was
# driven that way once, by hand, when it was written (revert the site's `spec.views` gate,
# watch the named test redden, restore it) — the marker keeps the citation attached to that
# recorded event; it does not repeat the proof. And a determined edit that removes a marker
# from its true owner and relabels an uninvolved-but-genuinely-unrelated test with the same
# site name is not caught here either — nothing static can tell a moved, false claim from a
# moved, true one. What *is* caught: two tests both claiming the same site (ambiguous
# ownership — the surviving, purely-structural equivalent of "re-pointing" once there is no
# external map left to silently overwrite), and a citation whose test is not collected by
# default.


def _gated_sites() -> set[tuple[str, str]]:
    return {s for s, (label, _reason) in CLASSIFICATIONS.items() if label == "gated"}


def _tests_root() -> Path:
    return _repo_root() / "tests"


_EXCLUDED_MARK_NAMES = frozenset({"skip", "skipif", "xfail", "slow"})


def _pytest_mark_name(deco: ast.expr) -> str | None:
    """The bare mark name of *deco* (e.g. ``"gate_for"``, ``"skip"``) if it is a
    ``pytest.mark.<name>`` decorator, called (``@pytest.mark.skip(reason=...)``) or bare
    (``@pytest.mark.slow``); ``None`` for any other decorator shape."""
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
    """Whether *node* carries a mark that keeps it from running in a bare, default collection —
    ``skip``/``skipif``/``xfail`` (never runs, or is expected not to) or this repo's one
    opt-in-only mark, ``slow`` (see ``tests/conftest.py``'s collection hook)."""
    return any(_pytest_mark_name(d) in _EXCLUDED_MARK_NAMES for d in node.decorator_list)


def _gate_for_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Every site string named by a ``@pytest.mark.gate_for("...")`` decorator on *node*
    (ordinarily zero or one, never enforced here — a function decorated twice is caught the
    same way two different functions citing the same site are, by the ownership-uniqueness
    check below)."""
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


#: site-citation-string -> every (test-relative-path, test-function-name, excluded-from-
#: default-collection) that decorates itself with ``@pytest.mark.gate_for(site)`` — built from
#: *source*, a full test-module's text, so the discovery mechanism can be driven against a
#: constructed fixture (below) exactly the way the writer scan's own discovery is.
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
    """The same mapping as :func:`_gate_for_sites_in_module`, collected across every ``.py``
    file under *tests_root* — the map this module's checks are actually built from."""
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
    """Re-key a ``_gate_for_sites`` result from the citation string to the ``CLASSIFICATIONS``
    tuple shape, so it can be compared against ``_gated_sites()`` directly."""
    out: dict[tuple[str, str], list[tuple[str, str, bool]]] = {}
    for site, tests in owners.items():
        rel, _sep, func = site.partition("::")
        out[(rel, func)] = tests
    return out


def test_the_marker_scan_finds_a_bare_gate_for_citation() -> None:
    """Validates the discovery mechanism against a known positive before the real corpus's
    citations are trusted, the same false-zero discipline every scan in this module follows."""
    source = (
        "import pytest\n\n"
        "@pytest.mark.gate_for('squads/_x.py::_y')\n"
        "async def test_z() -> None:\n    pass\n"
    )
    owners = _gate_for_sites_in_module(source, "tests/synthetic.py")
    assert owners == {"squads/_x.py::_y": [("tests/synthetic.py", "test_z", False)]}


def test_every_gated_site_has_exactly_one_behavioural_test_citation() -> None:
    """The citation requirement itself, independent of whether the citing test is collected and
    live (the next test) — every ``gated`` site has exactly one test declaring
    ``@pytest.mark.gate_for`` for it: not zero (uncited), not more than one (ambiguous — the
    surviving, structural form of "re-pointing" a citation once there is no external map left
    to silently overwrite: adding the marker to a second, uninvolved test does not remove it
    from the true owner, so both now claim the site, and that ambiguity is what this refuses),
    and nothing cites a site that is not (or is no longer) ``gated``."""
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
    """Refuses a re-pointed citation, in the shape that survives once there is no hand-maintained
    dict to silently overwrite. The reviewer's original drive re-pointed a citation at
    ``test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag`` — a real,
    uninvolved, currently-passing sibling in the very file the true citation already named —
    with no edit to that sibling's own source and the meta module stayed green. Under the
    marker scheme a citation only exists where a test decorates itself, so the same act —
    naming an uninvolved test as a second owner of a site already claimed — leaves *two*
    declared owners rather than a silent substitution, which
    ``test_every_gated_site_has_exactly_one_behavioural_test_citation`` refuses outright.
    Constructed directly against the scanner (never against real source under ``tests/``):"""
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
    """Refuses a skip-marked citation — the accidental form, and the one that will actually
    happen: a real cited test goes flaky in CI, someone reaches for ``@pytest.mark.skip``, and
    a decorator is
    invisible to a bare ``ast.FunctionDef`` name lookup, so the old resolution check kept
    passing while the gate's backing quietly vanished. Checked here instead: none of the real
    corpus's citations are ``skip``/``skipif``/``xfail``/``slow``-marked — "collected and live"
    is checkable without executing anything, and this is the whole of what it checks (see the
    module note above: whether a live test's assertions actually falsify is a mutation-testing
    question, not this one)."""
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
    """Drives the exclusion check above against the reviewer's own reproduction: the real cited
    test, unmodified except for an added ``@pytest.mark.skip``, still carries its
    ``gate_for`` marker (the citation still "exists") but is flagged excluded — exactly what
    ``test_every_gate_for_citation_is_collected_and_live`` refuses. Constructed directly
    against the scanner, not against real source under ``tests/``:"""
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

#: The Python scan above globs ``*.py``, so a literal ``sq:view:<name>`` tag written directly
#: into a Jinja template — not through :func:`~squads._models._markers.view_tag` at all — is
#: invisible to it by construction. One such writer exists today:
#: ``templates/agents/role.md.j2``, the creation scaffold's static tag —
#: ``ROLE_DEFINITION_VIEW_NAME``'s own docstring points at it. Whitespace-tolerant between each
#: token boundary (``sq``/``:``/``view``/``:``/name), the same false-zero defence the Python
#: scan gets from walking the AST rather than grepping lines — see
#: ``test_the_template_scan_finds_a_tag_a_raw_substring_grep_would_miss`` below.
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
    """Same false-zero rule as the Python scan's own validation, applied to the template scan: a
    formatter can wrap a tag's HTML comment across a line, splitting whitespace between
    ``sq:view:`` and the name it carries, which a raw ``"sq:view:role_definition"`` substring
    search does not match but the whitespace-tolerant regex still resolves."""
    adversarial = "<!-- sq:view:\n    role_definition -->\n"
    assert "sq:view:role_definition" not in adversarial, (
        "fixture no longer demonstrates a raw substring false zero"
    )

    names = [m.group(1) for m in _TEMPLATE_VIEW_TAG_RE.finditer(adversarial)]
    assert names == ["role_definition"], (
        "the template scan must find a tag a raw substring search misses"
    )


#: template-relative-path -> (classification, reason). Same completeness contract as
#: ``CLASSIFICATIONS`` above, over the second writer class the Python-only scan cannot see: an
#: ``AssertionError`` below for any discovered template tag not a key here, or any key here no
#: longer discovered, means a template writer exists with no accounted-for reason.
TEMPLATE_CLASSIFICATIONS: dict[str, tuple[str, str]] = {
    "agents/role.md.j2": (
        "neutralized-by-overwrite",
        "the creation scaffold's static tag: _create_core unconditionally overwrites a role's "
        "sq:body region on the one path that renders this template, so the static tag can "
        "never survive on disk as a value — pristine_body, _template_for's only other "
        "consumer, is unreachable for a role because set_body raises first",
    ),
}

_VALID_TEMPLATE_CLASSIFICATIONS = frozenset({"neutralized-by-overwrite"})


def test_every_template_classification_label_is_a_known_shape() -> None:
    for site, (label, _reason) in TEMPLATE_CLASSIFICATIONS.items():
        assert label in _VALID_TEMPLATE_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_the_discovered_template_tags_are_exactly_the_classified_one() -> None:
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
    """Driven by the reviewer: a static tag added inside ``agents/skill.md.j2``'s ``sq:body``
    region left every pre-existing test green, and then survives into every skill ``sq skill
    add`` creates afterward — nothing overwrites a skill's body region the way ``_create_core``
    does a role's. Constructed here as a copied fixture tree, never against the real bundled
    template (which must stay untouched — see the regression check below): confirms the
    extended scan catches the second writer as unclassified."""
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

    # Regression control: the fixture copy is the only tree that changed — the real bundled
    # template corpus must still pass with just its one classified hit.
    assert set(_template_view_tag_sites(_templates_root())) == set(TEMPLATE_CLASSIFICATIONS)
