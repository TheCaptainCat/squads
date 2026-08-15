"""Repo-hygiene gate: ``sq:`` marker recognition is defined **once**, in
``src/squads/_sections.py``, and that one definition is **case-blind**.

Both halves are load-bearing, and the bug this guard closes needed both to fail at once.

*Case-blindness.* A sub-entity region tag embeds its ``local_id``, whose ``local_prefix``
comes from the workflow spec and is uppercase for every bundled kind (and free-form for an
adopter-declared one). A lowercase-only tag class therefore matched no sub-entity marker at
all — silently, since it just returned fewer tags. Every consumer went blind with it: the
write-time marker-injection guard accepted a forged sub-entity region inside an
agent-authored body, and ``check``'s marker linter reported a file with a duplicated or
unclosed sub-entity marker as clean.

*Single definition.* The lowercase class survived in **two** places — the primitive and a
verbatim copy in the override service — so fixing the one that showed up in a report would
have left the other blind. A second regex is how this class comes back, so the scan below
flags any ``sq:``-marker-shaped pattern handed to a regex call outside the primitive's module.

The scan reads the **parsed AST**, not source lines. A line-oriented version of this guard was
defeated by the most mechanical shape there is: a compile call whose pattern sits on the next
line, which is exactly what this project's own formatter produces once the call exceeds the
line limit. Formatting must not decide whether a gate sees a construct, so the question is
asked of the syntax tree, where a wrapped call and a one-line call are the same node.

An f-string pattern is read the same way, with each ``{...}`` collapsed to a placeholder, so a
pattern assembled by interpolation cannot slip past as "not a constant".

Exemptions are pinned to **(module, pattern text)**, never to a module alone: a module-granular
exemption blesses whatever is appended to the file later, and a liveness test asking only
whether the module still produces *some* hit can never notice. Paired throughout with
behavioural probes of the live primitive — a scan cannot tell a correct-looking pattern from
one nothing calls.
"""

import ast
import re
from pathlib import Path

from squads import _sections as sections
from squads._models import _markers as markers
from squads._workflow import bundled_spec

#: The module that is allowed to define marker recognition, relative to the repo root.
_PRIMITIVE = "src/squads/_sections.py"

#: Regex-API function names whose first argument is a pattern. Matched on the callee name
#: alone so ``re.compile(...)``, ``regex.compile(...)`` and a ``from re import compile`` all
#: read the same; the pattern-shape test below is what makes the pair meaningful.
_REGEX_CALLS: frozenset[str] = frozenset(
    {"compile", "findall", "search", "match", "fullmatch", "finditer", "sub", "subn", "split"}
)

#: A pattern trying to recognise an sq marker comment: it mentions the HTML-comment opener and
#: the ``sq:`` namespace close together. ``\S{0,4}`` covers the escaped spellings a hand-written
#: pattern may use.
_MARKER_PATTERN = re.compile(r"<!\S{0,4}--.{0,40}sq:")

#: Placeholder standing in for an f-string's ``{...}`` when a pattern's text is normalised, so
#: an interpolated pattern has one stable spelling to pin an exemption to.
_HOLE = "{}"

#: ``(module, pattern text)`` pairs exempt from the single-definition rule, each with the reason
#: it is not a second general recogniser. Pinned to the exact pattern, not the module: a new
#: recogniser appended to an exempt file must fail, and the liveness test below proves each pair
#: is still produced.
_ALLOWED_PATTERNS: dict[tuple[str, str], str] = {
    # Frozen legacy-format readers used only by the schema migrations. Neither is a general
    # recogniser: each interpolates one specific kind and that kind's *historical* literal
    # local prefix, to locate one block shape in a file written in a format that can no longer
    # be produced. Widening the primitive neither helps them nor applies to them, and a
    # migration runner's parse of a frozen format must not shift underneath it.
    (
        "src/squads/_migrations/_meta_compat.py",
        rf"<!--\s*sq:{_HOLE}:({_HOLE}\d+)\s*-->",
    ): "frozen pre-migration block opener",
    (
        "src/squads/_migrations/_meta_compat.py",
        rf"<!--\s*sq:{_HOLE}:{_HOLE}(\d+)\s*-->",
    ): "frozen pre-migration block id scan",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pattern_text(node: ast.expr) -> str | None:
    """The literal text of a pattern argument, with every interpolation collapsed to
    :data:`_HOLE`, or ``None`` when the argument carries no literal text at all.

    Handles the three spellings a pattern is written in: a plain (or implicitly concatenated)
    string constant, an f-string, and a ``+`` concatenation of either. A variable holding a
    pattern yields ``None`` — the literal is then somewhere else, and that somewhere is where
    this scan sees it.
    """
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        parts = [
            p.value if isinstance(p, ast.Constant) and isinstance(p.value, str) else _HOLE
            for p in node.values
        ]
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _pattern_text(node.left), _pattern_text(node.right)
        return None if left is None and right is None else (left or "") + (right or "")
    return None


def _marker_patterns(tree: ast.AST) -> list[str]:
    """Every marker-shaped pattern text passed as the first argument of a regex-API call."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name not in _REGEX_CALLS:
            continue
        text = _pattern_text(node.args[0])
        if text is not None and _MARKER_PATTERN.search(text):
            found.append(text)
    return found


def _scan(root: Path, allowed: frozenset[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    """Every ``(module, pattern text)`` under ``src/squads``, outside the primitive, that hands
    a marker-shaped pattern to a regex call and is not exempt."""
    allowed = frozenset(_ALLOWED_PATTERNS) if allowed is None else allowed
    hits: list[tuple[str, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if rel == _PRIMITIVE:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        hits.extend((rel, text) for text in _marker_patterns(tree) if (rel, text) not in allowed)
    return hits


def test_no_second_sq_marker_regex_exists_outside_the_primitive() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}: {text!r}" for path, text in hits)
    assert not hits, (
        "a second sq-marker regex was found outside squads._sections — recognition must have "
        f"one definition, or a widening fix leaves the copy blind:\n{detail}"
    )


def test_every_exempt_pattern_is_still_produced_by_the_scan_without_it() -> None:
    """A dead exemption is worse than none: it silently blesses whatever later occupies its
    slot. Removing each pair and re-scanning the real tree must reproduce exactly that pair."""
    root = _repo_root()
    for entry in _ALLOWED_PATTERNS:
        without = frozenset(_ALLOWED_PATTERNS) - {entry}
        assert entry in _scan(root, allowed=without), (
            f"exemption {entry!r} is dead — the scan no longer produces it; remove it"
        )


def test_the_scan_would_catch_a_planted_duplicate_regex(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'PAT = re.compile(r"<!--\\s*(sq:[a-z0-9][a-z0-9:_-]*)\\s*-->")\n', encoding="utf-8"
    )
    assert [path for path, _ in _scan(tmp_path, allowed=frozenset())] == ["src/squads/_example.py"]


def test_the_scan_would_catch_a_formatter_wrapped_duplicate_regex(tmp_path: Path) -> None:
    """The hole that defeated the line-oriented version of this guard, pinned as its own case:
    the pattern on a different line from the call is the shape ruff produces past the line
    limit, so it is the *likeliest* way a copy comes back, not an exotic one."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        '_SECOND = re.compile(\n    r"<!--\\s*(sq:[a-z0-9][a-z0-9:_-]*)\\s*-->"\n)\n',
        encoding="utf-8",
    )
    assert [path for path, _ in _scan(tmp_path, allowed=frozenset())] == ["src/squads/_example.py"]


def test_the_scan_would_catch_an_interpolated_or_concatenated_duplicate(tmp_path: Path) -> None:
    """Neither an f-string nor a ``+`` join is "not a literal" as far as this gate goes."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'A = re.compile(rf"<!--\\s*sq:{kind}:([A-Z]+\\d+)\\s*-->")\n'
        'B = re.findall(r"<!--\\s*" + r"(sq:[A-Za-z0-9:_-]+)" + r"\\s*-->", text)\n',
        encoding="utf-8",
    )
    assert len(_scan(tmp_path, allowed=frozenset())) == 2


def test_an_exempt_module_is_not_blanket_exempt(tmp_path: Path) -> None:
    """The second hole: exempting a file rather than its patterns. A brand-new general
    recogniser appended to an exempt module must still be flagged."""
    rel = "src/squads/_migrations/_meta_compat.py"
    planted = tmp_path / rel
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'FROZEN = re.compile(rf"<!--\\s*sq:{kind}:({prefix}\\d+)\\s*-->")\n'
        'GENERAL = re.compile(r"<!--\\s*(sq:[a-z0-9][a-z0-9:_-]*)\\s*-->")\n',
        encoding="utf-8",
    )
    exempt = frozenset({(rel, rf"<!--\s*sq:{_HOLE}:({_HOLE}\d+)\s*-->")})
    hits = _scan(tmp_path, allowed=exempt)
    assert [text for _, text in hits] == [r"<!--\s*(sq:[a-z0-9][a-z0-9:_-]*)\s*-->"]


def test_the_scan_ignores_prose_and_non_marker_regexes(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "# never alter the <!-- sq:* --> marker lines\n"
        'FRONT = re.compile(r"^---\\n(.*?)\\n---\\n?")\n'
        'OTHER = re.compile(r"<!--\\s*squads:start\\s*-->")\n'
        'BUILDER = f"<!-- sq:{tag} -->"\n',  # a marker *constructor*, not a recogniser
        encoding="utf-8",
    )
    assert _scan(tmp_path, allowed=frozenset()) == []


def test_the_live_primitive_recognises_every_declared_local_prefix() -> None:
    """The behavioural half: a scan cannot tell a case-blind pattern from a case-blind pattern
    nobody calls. Drive the real primitive with a real tag per declared kind."""
    spec = bundled_spec()
    assert spec.subentity_kinds, "the bundled spec must declare at least one sub-entity kind"
    blind = [
        kind
        for kind, ks in spec.subentity_kinds.items()
        if not sections.find_markers(markers.open_marker(f"{kind}:{ks.local_prefix}1"))
    ]
    assert not blind, f"find_markers is blind to declared sub-entity kind(s): {blind}"


def test_the_live_primitive_still_refuses_the_documentation_placeholder() -> None:
    """The other half of the contract, pinned here too: widening the tag class must never make
    the product lint its own agent-facing prose (a role file's ``sq:*`` line) as a marker."""
    assert sections.find_markers("never alter the <!-- sq:* --> marker lines") == []
