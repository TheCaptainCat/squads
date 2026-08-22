"""Repo-hygiene gate: every third-party ``uses:`` reference under ``.github/workflows/`` names
a full 40-character commit SHA followed by a human-readable version comment, of the form::

    uses: owner/action@<40-hex-sha>  # vX.Y.Z

A git tag is mutable — a moved upstream tag on a floating reference (``@v6``, ``@main``) would
execute unreviewed code in a workflow that, for this repo's publish pipeline, holds the PyPI and
Marketplace credentials. Pinning by commit SHA makes the reference immutable; the trailing
comment keeps the human-readable version visible so a bump stays reviewable. This guard is the
regression backstop for that hardening: without it, an edit that reverts a pin to a tag passes
every other gate silently.

A first-party local action (``uses: ./path/to/action``) is not a supply-chain surface — it is
this repo's own code, checked out with the workflow — so it is never flagged.

The scan parses each workflow's YAML into a node tree (via ``yaml.compose``, which preserves
source line numbers) to find every ``uses:`` key structurally, rather than regexing whole file
text — reordering, reformatting, or an anchor/alias would not confuse it the way a naive
whole-file regex could. Only the trailing-comment check reads a single already-located raw
line, since PyYAML's parser discards comments during composition and there is no comment-
preserving YAML parser in this project's dependencies.
"""

import re
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"

#: A bare 40-hex commit SHA — nothing shorter (an abbreviated SHA can collide) and nothing
#: else after it.
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

#: The trailing human-readable version comment, e.g. ``# v6.0.3``. Deliberately tolerant of
#: however much space precedes the ``#`` — the form mandate is the SHA-plus-comment pairing,
#: not exact whitespace.
_VERSION_COMMENT_PATTERN = re.compile(r"#\s*v[0-9]+(?:\.[0-9]+){1,2}\s*$")


def _walk_uses_nodes(node: yaml.Node, found: list[tuple[int, str]]) -> None:
    """Collect every (1-indexed line, value) pair for a mapping key literally named ``uses``,
    anywhere in the composed node tree."""
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if (
                isinstance(key_node, yaml.ScalarNode)
                and key_node.value == "uses"
                and isinstance(value_node, yaml.ScalarNode)
            ):
                found.append((value_node.start_mark.line + 1, value_node.value))
            else:
                _walk_uses_nodes(value_node, found)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _walk_uses_nodes(item, found)


def _uses_references(text: str) -> list[tuple[int, str]]:
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    if root is None:
        return []
    found: list[tuple[int, str]] = []
    _walk_uses_nodes(root, found)
    return found


def _pin_violations(text: str) -> list[tuple[int, str]]:
    """Every third-party ``uses:`` value in ``text`` that is not a 40-hex SHA pin with a
    trailing version comment. A ``./``-local reference is first-party and always allowed."""
    lines = text.splitlines()
    violations: list[tuple[int, str]] = []
    for lineno, value in _uses_references(text):
        if value.startswith("./"):
            continue
        _, _, pin = value.partition("@")
        raw_line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        if not (_SHA_PATTERN.match(pin) and _VERSION_COMMENT_PATTERN.search(raw_line)):
            violations.append((lineno, value))
    return violations


def _workflow_files() -> list[Path]:
    if not _WORKFLOWS_DIR.is_dir():
        return []
    return sorted(_WORKFLOWS_DIR.glob("*.yml")) + sorted(_WORKFLOWS_DIR.glob("*.yaml"))


def test_every_third_party_uses_reference_is_sha_pinned_with_a_version_comment() -> None:
    violations: list[tuple[str, int, str]] = []
    for path in _workflow_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for lineno, value in _pin_violations(path.read_text(encoding="utf-8")):
            violations.append((rel, lineno, value))
    detail = "\n".join(f"  {path}:{lineno}: {value!r}" for path, lineno, value in violations)
    assert not violations, (
        "third-party `uses:` reference(s) not pinned to a 40-hex commit SHA with a trailing "
        f"`# vX.Y.Z` comment:\n{detail}"
    )


def test_a_correctly_pinned_reference_passes() -> None:
    text = (
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10  # v6.0.3\n"
    )
    assert _pin_violations(text) == []


def test_a_first_party_local_action_reference_is_never_flagged() -> None:
    text = "jobs:\n  build:\n    steps:\n      - uses: ./.github/actions/my-local-action\n"
    assert _pin_violations(text) == []


def test_a_floating_tag_reference_is_flagged_with_its_line_and_value() -> None:
    text = "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v6.0.3\n"
    assert _pin_violations(text) == [(4, "actions/checkout@v6.0.3")]


def test_a_bare_floating_major_version_is_flagged() -> None:
    text = "jobs:\n  build:\n    steps:\n      - uses: actions/setup-node@v5\n"
    assert _pin_violations(text) == [(4, "actions/setup-node@v5")]


def test_a_full_sha_with_no_version_comment_is_still_flagged() -> None:
    """The SHA alone is not enough — a bump that drops the comment loses the reviewable
    human-readable version, so it must be caught too."""
    text = (
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10\n"
    )
    assert _pin_violations(text) == [
        (4, "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10")
    ]


def test_an_abbreviated_sha_is_not_accepted_as_a_pin() -> None:
    text = "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@df4cb1c  # v6.0.3\n"
    assert _pin_violations(text) == [(4, "actions/checkout@df4cb1c")]
