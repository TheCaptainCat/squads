"""Repo-hygiene gate: ``squads._index._reflog.REFLOG_OPS`` is the *only* enumeration of the
reflog's ``op`` vocabulary, and it is complete.

The vocabulary used to be written out by hand in three places — the ``_reflog`` module
docstring, ``sq reflog --op``'s help text, and the workflow guide's op table. All three were
incomplete, in different ways, and their union still missed an op that had shipped. Two lists
that must agree are the defect; the mismatch is only the symptom. So:

* ``--op``'s help text now interpolates the constant and the module docstring points at it
  rather than restating it — those copies are gone by construction, not by discipline.
* The doc table is prose an adopter reads, so it keeps its per-op "triggered by" column and is
  pinned here instead.
* The constant itself is pinned against the source, because a ``store.log(...)`` op is a bare
  string literal at arbitrary depth in ``_services/`` with no import-time registry to read.
  The AST scan below is what lets the docstring keep calling the vocabulary *closed*.

Both emitter shapes are scanned: the buffered ``self.store.log("<op>", target, delta)`` used
inside a transaction, and the direct ``append_line(..., op="<op>", …)`` the three squad-level
maintenance ops use because they write outside one.
"""

import ast
import re
from pathlib import Path

from squads._index._reflog import REFLOG_OPS

_SRC = Path(__file__).resolve().parents[2] / "src" / "squads"
_DOCS = Path(__file__).resolve().parents[2] / "docs" / "workflow.md"

# The table row shape in docs/workflow.md's "Op names" section: | `create` | sq create … |
_DOC_ROW = re.compile(r"^\|\s*`([a-z_-]+)`\s*\|")


def _emitted_ops() -> set[str]:
    """Every op literal the source can actually write to the reflog."""
    found: set[str] = set()
    for path in _SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # store.log("<op>", target, delta) — op is the first positional arg.
            if isinstance(func, ast.Attribute) and func.attr == "log" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    found.add(first.value)
            # append_line(..., op="<op>", ...) — op is a keyword.
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "append_line":
                for kw in node.keywords:
                    if (
                        kw.arg == "op"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        found.add(kw.value.value)
    return found


def test_reflog_ops_is_exactly_what_the_source_emits() -> None:
    emitted = _emitted_ops()
    undeclared = emitted - set(REFLOG_OPS)
    stale = set(REFLOG_OPS) - emitted
    assert not undeclared, (
        "an op is written to the reflog that REFLOG_OPS doesn't name — `sq reflog --op` and the "
        f"workflow guide would both omit it; add to the constant: {sorted(undeclared)}"
    )
    assert not stale, (
        "REFLOG_OPS names an op nothing emits any more — the vocabulary is no longer closed; "
        f"remove the stale entry: {sorted(stale)}"
    )


def test_reflog_ops_has_no_duplicates() -> None:
    assert len(REFLOG_OPS) == len(set(REFLOG_OPS)), (
        f"REFLOG_OPS repeats an op: {sorted({o for o in REFLOG_OPS if REFLOG_OPS.count(o) > 1})}"
    )


def test_the_workflow_guide_op_table_covers_the_whole_vocabulary() -> None:
    lines = _DOCS.read_text(encoding="utf-8").splitlines()
    # Anchor on the op table's own header — the field table further up also has an `op` row.
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| `op` | Triggered by |"))
    documented: set[str] = set()
    for ln in lines[start + 1 :]:
        if not ln.startswith("|"):
            break
        match = _DOC_ROW.match(ln)
        if match:
            documented.add(match.group(1))
    assert documented == set(REFLOG_OPS), (
        "docs/workflow.md's op table has drifted from REFLOG_OPS — "
        f"missing from the table: {sorted(set(REFLOG_OPS) - documented)}; "
        f"named there but not in the vocabulary: {sorted(documented - set(REFLOG_OPS))}"
    )


def test_the_op_help_text_names_every_op() -> None:
    """``sq reflog --op``'s help is generated from the constant, so this only has to prove the
    generation is still wired up — a reverted f-string would show up as a missing op here."""
    import typer.main

    from squads._cli import app

    click_app = typer.main.get_command(app)
    reflog_cmd = click_app.commands["reflog"]  # type: ignore[attr-defined]
    op_param = next(p for p in reflog_cmd.params if p.name == "op")
    help_text = op_param.help or ""
    missing = [op for op in REFLOG_OPS if op not in help_text]
    assert not missing, f"`sq reflog --op` help omits: {missing}"
