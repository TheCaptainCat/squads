"""Repo gate: the bundled template tree ships to every adopter, so it must not carry this
squad's own people or present squads itself as the adopter's project.

Both leaks were real and both read as harmless in review. A tone-matching example greeted the
maintainer by first name, so every ``sq init`` wrote a greeting skill instructing the adopter's
agents to greet someone who is not their operator; the worked greeting then described *squads*
as the project being worked on, illustrating an adopter's repo with our own product.

The operator half is derived, not listed: it reads this squad's own operator roster off disk, so
a person registered later is covered without touching this file. The placeholder convention the
templates and docs use instead is ``Alice Tester`` / ``op-alice``.

The bundled agent ROSTER names (Robert Architect, Mara Tester, …) are deliberately not scanned:
those are squads' own shipped roles, which an adopter's squad really does get, so naming them in
an example is accurate rather than a leak.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "src" / "squads" / "_rendering" / "templates"
_OPERATORS_DIR = _REPO_ROOT / "squads" / "operators"

_FULL_NAME_RE = re.compile(r"^\s*full_name:\s*(.+?)\s*$", re.MULTILINE)
_SLUG_RE = re.compile(r"^\s*slug:\s*(op-[a-z0-9-]+)\s*$", re.MULTILINE)


def _bundled_template_texts() -> dict[str, str]:
    return {
        str(p.relative_to(_TEMPLATES_DIR)): p.read_text(encoding="utf-8")
        for p in sorted(_TEMPLATES_DIR.rglob("*.j2"))
    }


def _this_squads_operator_identities() -> set[str]:
    """Every full name and ``op-`` slug this squad's own operator roster carries."""
    identities: set[str] = set()
    for path in sorted(_OPERATORS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        identities.update(m.strip().strip("'\"") for m in _FULL_NAME_RE.findall(text))
        identities.update(_SLUG_RE.findall(text))
    return {i for i in identities if i}


def _identity_tokens(identity: str) -> set[str]:
    """The forms an identity can leak as: the whole string, and each name part on its own."""
    return {identity, *(part for part in identity.split() if len(part) > 2)}


def test_this_squad_has_an_operator_to_scan_for() -> None:
    """Falsification floor: an empty roster would make the scan below vacuously pass."""
    assert _this_squads_operator_identities(), (
        f"no operator identities read from {_OPERATORS_DIR} — this guard would pass vacuously"
    )


def test_no_bundled_template_names_one_of_this_squads_operators() -> None:
    tokens = {t for i in _this_squads_operator_identities() for t in _identity_tokens(i)}
    offenders: list[str] = []
    for rel, text in _bundled_template_texts().items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            offenders.extend(
                f"{rel}:{lineno} names {token!r}"
                for token in tokens
                if re.search(rf"\b{re.escape(token)}\b", line)
            )
    assert not offenders, (
        "bundled package data names a real person from this squad's operator roster — use the "
        f"placeholder `Alice Tester` / `op-alice` instead: {offenders}"
    )


@pytest.mark.parametrize("rel", ["agents/greeting_skill.md.j2"])
def test_a_worked_example_does_not_use_squads_itself_as_the_example_project(rel: str) -> None:
    """The blockquote example describes the project the adopter's agents work on. Naming our
    own product there tells them their repo is squads."""
    text = (_TEMPLATES_DIR / rel).read_text(encoding="utf-8")
    quoted = [ln for ln in text.splitlines() if ln.lstrip().startswith(">")]
    assert quoted, f"{rel}: no blockquote example found — has the example moved?"
    offenders = [ln for ln in quoted if re.search(r"\bsquads\b", ln, re.IGNORECASE)]
    assert not offenders, (
        f"{rel}: the worked example describes squads itself as the project being worked on — "
        f"use a generic fictional project instead: {offenders}"
    )
