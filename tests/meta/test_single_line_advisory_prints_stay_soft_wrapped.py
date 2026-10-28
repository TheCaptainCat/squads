"""Durable enforcement that a single-line CLI advisory carrying a copy-pasteable `sq` command or an
`error`/`warning` prefix stays `soft_wrap=True` -- the lasting output of the piped-error sweep is
a guard, not a one-time pass over a hand-picked list of sites."""

import ast
from pathlib import Path

#: The receivers this scan treats as a CLI advisory console -- the two module-level Rich
#: consoles from `_cli/_common.py`, plus `_report_unreadable`'s local `target` (bound to
#: whichever of the two applies for `--json`). A new console alias of the same shape would
#: need adding here to stay in scope.
_CONSOLE_RECEIVERS = frozenset({"console", "err_console", "target"})

#: A literal (compile-time-visible) substring that marks a print's message as carrying a
#: copy-pasteable `sq` command or an error/warning advisory -- the class this guard holds the
#: line on. Matched against the literal parts only (interpolated values are invisible to the
#: scan, which is the point: the bug is exactly that an *interpolated* value can grow long).
MARKERS: tuple[str, ...] = ("[red]error", "[yellow]warning", "`sq ", "[cyan]sq ")

#: file (repo-root-relative, posix) -> {message literal-prefix: one-line reason}, for a
#: marker-matching call deliberately left without soft_wrap=True. Empty on the current tree —
#: every marker-matching call already carries it.
ALLOWLIST: dict[str, dict[str, str]] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cli_root() -> Path:
    return _repo_root() / "src" / "squads" / "_cli"


def _literal_text(node: ast.expr) -> str | None:
    """The compile-time-visible text of a plain string or f-string literal -- the constant
    parts only, with every interpolated ``{...}`` slot invisible (as it must be: an
    interpolated value is exactly what this bug's class lets grow unboundedly long). ``None``
    for anything else (a ``Table``/``Panel``/``Tree``/``Markdown`` call, or a bound variable
    holding free-form prose) -- those are out of scope by construction, not by exclusion."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
    return None


def _receiver_name(func: ast.expr) -> str | None:
    """The receiver name for a bare-name form (``console``) or a module-qualified attribute
    form (``common.console`` -> ``console``) alike -- a module-qualified receiver is not a
    different kind of console, just a different way of spelling the same one, so it must
    resolve to the same name a bare receiver would."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _print_calls(tree: ast.Module) -> list[ast.Call]:
    """Every ``<receiver>.print(...)`` call in *tree* whose receiver is one of
    ``_CONSOLE_RECEIVERS`` and which passes at least one positional argument."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "print"
        and _receiver_name(node.func.value) in _CONSOLE_RECEIVERS
        and node.args
    ]


def _has_soft_wrap_true(call: ast.Call) -> bool:
    return any(
        kw.arg == "soft_wrap" and isinstance(kw.value, ast.Constant) and kw.value.value is True
        for kw in call.keywords
    )


def _unwrapped_marker_hits(root: Path, key_root: Path) -> dict[str, list[tuple[int, str]]]:
    """Walk every ``.py`` file under *root*: for each marker-matching, literal-text print call
    that lacks ``soft_wrap=True``, record ``(line, text-prefix)``. Keyed by path relative to
    *key_root* (posix form) -- the exact walk the real guard runs, reused by the plant tests
    below so they exercise the same wiring, not just the bare predicate."""
    hits: dict[str, list[tuple[int, str]]] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: list[tuple[int, str]] = []
        for call in _print_calls(tree):
            text = _literal_text(call.args[0])
            if text is None or not any(m in text for m in MARKERS):
                continue
            if not _has_soft_wrap_true(call):
                found.append((call.lineno, text[:60]))
        if found:
            hits[path.relative_to(key_root).as_posix()] = found
    return hits


def _missing_against(
    hits: dict[str, list[tuple[int, str]]], allowlist: dict[str, dict[str, str]]
) -> dict[str, list[tuple[int, str]]]:
    """The set-difference the real guard asserts is empty: every hit whose text-prefix is not
    a key of that file's allowlist entry."""
    missing: dict[str, list[tuple[int, str]]] = {}
    for rel, found in hits.items():
        allowed_prefixes = allowlist.get(rel, {})
        leftover = [
            (line, text)
            for line, text in found
            if not any(text.startswith(prefix) for prefix in allowed_prefixes)
        ]
        if leftover:
            missing[rel] = leftover
    return missing


# ---------------------------------------------------------------------------------- the guard


def test_every_marker_matching_advisory_print_is_soft_wrapped() -> None:
    hits = _unwrapped_marker_hits(_cli_root(), _repo_root())
    missing = _missing_against(hits, ALLOWLIST)
    assert not missing, (
        "a single-line CLI advisory carries a copy-pasteable `sq` command or an "
        "error/warning prefix but is not soft_wrap=True (add it, or allowlist with a reason): "
        f"{missing}"
    )


def test_the_allowlist_has_no_stale_entry() -> None:
    """Every allowlisted (file, prefix) pair must still be a real, currently-unwrapped hit."""
    hits = _unwrapped_marker_hits(_cli_root(), _repo_root())
    stale: dict[str, list[str]] = {}
    for rel, prefixes in ALLOWLIST.items():
        file_hits = [text for _line, text in hits.get(rel, [])]
        dead = [prefix for prefix in prefixes if not any(t.startswith(prefix) for t in file_hits)]
        if dead:
            stale[rel] = dead
    assert not stale, f"allowlist entries with no corresponding unwrapped hit: {stale}"


# ------------------------------------------------------------- wired-guard plant tests
# These exercise the SAME file-walk (`_unwrapped_marker_hits`) + allowlist-diff
# (`_missing_against`) the real assertion above runs -- not just the bare predicate -- against
# a synthetic tree, so a new unwrapped site reddens the actual guard path automatically.


def test_the_wired_guard_reddens_on_a_planted_unwrapped_error_site(tmp_path: Path) -> None:
    planted_root = tmp_path / "_cli"
    planted_root.mkdir()
    (planted_root / "_leaky.py").write_text(
        "from squads._cli._common import console\n\n\n"
        "def _boom(path: str) -> None:\n"
        '    console.print(f"[red]error:[/red] could not read {path}")\n',
        encoding="utf-8",
    )

    hits = _unwrapped_marker_hits(planted_root, tmp_path)
    missing = _missing_against(hits, ALLOWLIST)  # the real allowlist — nothing here is on it

    assert list(missing) == ["_cli/_leaky.py"]


def test_the_wired_guard_reddens_on_a_planted_unwrapped_command_reference(tmp_path: Path) -> None:
    """The other marker family (an inline `sq` command reference), not just the error prefix."""
    planted_root = tmp_path / "_cli"
    planted_root.mkdir()
    (planted_root / "_leaky.py").write_text(
        "from squads._cli._common import console\n\n\n"
        "def _hint(dest: str) -> None:\n"
        "    console.print(f'edit {dest}, then verify with `sq check`')\n",
        encoding="utf-8",
    )

    hits = _unwrapped_marker_hits(planted_root, tmp_path)
    missing = _missing_against(hits, ALLOWLIST)

    assert list(missing) == ["_cli/_leaky.py"]


def test_the_wired_guard_reddens_on_a_planted_attribute_receiver(tmp_path: Path) -> None:
    """The shape the bare-name plant tests above cannot cover: a module-qualified receiver."""
    planted_root = tmp_path / "_cli"
    planted_root.mkdir()
    (planted_root / "_leaky.py").write_text(
        "import squads._cli._common as common\n\n\n"
        "def _boom(path: str) -> None:\n"
        '    common.err_console.print(f"[red]error:[/red] could not read {path}")\n',
        encoding="utf-8",
    )

    hits = _unwrapped_marker_hits(planted_root, tmp_path)
    missing = _missing_against(hits, ALLOWLIST)

    assert list(missing) == ["_cli/_leaky.py"]


def test_the_wired_guard_stays_green_when_the_planted_site_carries_soft_wrap(
    tmp_path: Path,
) -> None:
    planted_root = tmp_path / "_cli"
    planted_root.mkdir()
    (planted_root / "_ok.py").write_text(
        "from squads._cli._common import console\n\n\n"
        "def _boom(path: str) -> None:\n"
        '    console.print(f"[red]error:[/red] could not read {path}", soft_wrap=True)\n',
        encoding="utf-8",
    )

    hits = _unwrapped_marker_hits(planted_root, tmp_path)

    assert hits == {}


def test_the_wired_guard_stays_green_on_a_planted_allowlisted_exception(tmp_path: Path) -> None:
    planted_root = tmp_path / "_cli"
    planted_root.mkdir()
    (planted_root / "_ok.py").write_text(
        "from squads._cli._common import console\n\n\n"
        "def _boom(path: str) -> None:\n"
        '    console.print(f"[red]error:[/red] could not read {path}")\n',
        encoding="utf-8",
    )
    custom_allowlist = {"_cli/_ok.py": {"[red]error:[/red] could not read": "planted example"}}

    hits = _unwrapped_marker_hits(planted_root, tmp_path)

    assert _missing_against(hits, custom_allowlist) == {}


def test_a_prebuilt_renderable_or_bound_prose_variable_is_never_a_candidate() -> None:
    """A `Table`, `Panel` or bound variable is not a constant, so it is never inspected."""
    source = (
        "from squads._cli._common import console\n\n\n"
        "def _show(table, title: str) -> None:\n"
        "    console.print(table)\n"
        '    console.print(f"[red]error:[/red] {title}")\n'
    )
    tree = ast.parse(source)
    calls = _print_calls(tree)
    literal_calls = [c for c in calls if _literal_text(c.args[0]) is not None]

    # `console.print(table)` (a bound Name, not a literal) never reaches the marker check;
    # `console.print(f"...")` does, even though its *interpolated* content (`title`) is
    # exactly the kind of free-form value the marker check cannot and must not try to read.
    assert len(calls) == 2
    assert len(literal_calls) == 1


def test_a_non_console_receiver_is_ignored() -> None:
    """Only the declared advisory-console names are in scope."""
    source = 'def _use(logger) -> None:\n    logger.print(f"[red]error:[/red] `sq check` this")\n'
    tree = ast.parse(source)
    assert _print_calls(tree) == []
