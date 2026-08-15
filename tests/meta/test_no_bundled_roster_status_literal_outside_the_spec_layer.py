"""Repo-hygiene gate: none of the bundled roster (role/skill/operator) lifecycle's status
names — ``Draft``, ``Active``, ``Archived`` — may appear as a bare Python string-constant
literal anywhere under ``src/squads/`` outside two legitimate exceptions:

- ``_specs/`` — where the bundled vocabulary is actually declared (``workflow.toml``, not
  even Python, but the whole package is exempted for symmetry with the other scans' shape).
- ``_migrations/`` — a migration runner legitimately pins the vocabulary of the schema
  version it transforms, never the live spec; see each runner's own frozen ``_STATUS_ACTIVE``
  module constant.

Everywhere else, engine behaviour must resolve "is this entry on offer" through
``WorkflowSpec.live_statuses``/``live_initial`` (both keyed by item type alone — no
role-*name* argument at all), never by naming ``Draft``/``Active``/``Archived`` directly. This
is the same shape as the other ``tests/meta`` guards (the stray-ticket-reference scan, the
mutable-state guard): a cheap, readable AST scan, not a new framework.

Scoped to a bare ``ast.Constant`` whose value is *exactly* one of the three names — a longer
string merely containing the substring (a docstring paragraph, a playbook lifecycle-summary
line) never matches, so the existing legitimate prose citing "Draft" for the work/guide
lifecycles is left alone without needing an allowlist entry for it.
"""

import ast
from pathlib import Path

import pytest

#: The bundled roster lifecycle's status names — the literal-value floor this scan protects.
_STATUS_LITERALS: frozenset[str] = frozenset({"Draft", "Active", "Archived"})

#: Directories under src/squads/ exempt from the scan, for the two reasons in the module
#: docstring above.
_EXEMPT_DIR_NAMES: frozenset[str] = frozenset({"_specs", "_migrations"})

#: (path, lineno, value) hits allowlisted because they are not a status-literal comparison at
#: all — each entry carries its own one-line reason. Empty today: the one entry this ever held
#: (the roster table's "Active" column header) was retired along with the header text itself
#: once the materialisation axis moved onto the ``live`` flag and the column started saying
#: "Live" instead. Kept as a frozenset of ``(path, lineno, value)`` triples rather than
#: widened to a coarser ``(path, value)`` key: a per-line key can never over-exempt a
#: *different* occurrence of the same literal elsewhere in the same file, which a per-file key
#: would do silently. What a line-numbered key actually needs — and did not have before this
#: change — is a liveness check: see
#: ``test_every_allowlisted_hit_is_still_produced_by_the_scan_without_it`` below, which fails
#: loudly the moment a future entry goes stale (because a later edit moved the line, e.g.)
#: instead of letting it quietly start excusing whatever code lands on that line next.
_ALLOWED_HITS: frozenset[tuple[str, int, str]] = frozenset()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scan(
    root: Path, allowed: frozenset[tuple[str, int, str]] = _ALLOWED_HITS
) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts or any(part in _EXEMPT_DIR_NAMES for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        rel = path.relative_to(root).as_posix()
        hits.extend(
            (rel, node.lineno, node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in _STATUS_LITERALS
            and (rel, node.lineno, node.value) not in allowed
        )
    return hits


def test_no_bundled_roster_status_literal_appears_outside_the_spec_layer() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}: {value!r}" for path, lineno, value in hits)
    assert not hits, (
        f"bundled roster status literal(s) found outside _specs/ and _migrations/ — use "
        f"WorkflowSpec.live_statuses/live_initial instead:\n{detail}"
    )


def test_the_scan_would_catch_a_planted_status_literal(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('status = "Active"\n', encoding="utf-8")

    assert _scan(tmp_path) == [("src/squads/_example.py", 1, "Active")]


@pytest.mark.parametrize("exempt_dir", sorted(_EXEMPT_DIR_NAMES))
def test_the_scan_exempts_the_spec_layer_directories(tmp_path: Path, exempt_dir: str) -> None:
    planted = tmp_path / "src" / "squads" / exempt_dir / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('_STATUS_ACTIVE = "Active"\n', encoding="utf-8")

    assert _scan(tmp_path) == []


def test_the_scan_never_flags_a_longer_string_merely_containing_the_substring(
    tmp_path: Path,
) -> None:
    """Docstring/prose text citing the work or guide lifecycle ("Draft → Ready → …") is not a
    bare status-literal comparison and must never trip this gate."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        '"""The guide lifecycle: Draft -> Published -> Deprecated."""\n', encoding="utf-8"
    )

    assert _scan(tmp_path) == []


def test_an_allowlisted_hit_does_not_mask_a_second_unallowlisted_literal_on_the_same_line(
    tmp_path: Path,
) -> None:
    """Two distinct constants on the same line are two distinct AST nodes — allowlisting one
    (path, lineno, value) triple never suppresses a different value at the same location. The
    production allowlist is empty today, so this exercises a synthetic one built the same shape
    the real allowlist would use — otherwise, with nothing allowlisted, this test would pass
    without ever exercising the masking property its name claims to test."""
    planted = tmp_path / "src" / "squads" / "_cli" / "_role.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('cols = ("Active", "Draft")\n', encoding="utf-8")

    synthetic_allowlist = frozenset({("src/squads/_cli/_role.py", 1, "Active")})
    hits = _scan(tmp_path, allowed=synthetic_allowlist)
    assert ("src/squads/_cli/_role.py", 1, "Draft") in hits
    assert ("src/squads/_cli/_role.py", 1, "Active") not in hits


def test_every_allowlisted_hit_is_still_produced_by_the_scan_without_it() -> None:
    """A dead allowlist entry — one the scan would no longer actually produce — is worse than
    no entry at all: it silently starts excusing whatever new code later lands on that exact
    (path, line). Removing each entry one at a time and re-scanning the real tree must
    reproduce exactly that hit, proving the entry is still live rather than a stale
    line-numbered exemption nobody has re-checked since the line moved."""
    root = _repo_root()
    for entry in _ALLOWED_HITS:
        without_this_entry = _ALLOWED_HITS - {entry}
        assert entry in _scan(root, allowed=without_this_entry), (
            f"allowlist entry {entry!r} is dead — the scan no longer produces it; remove it"
        )
