"""Repo gate: every shipped top-level ``sq`` command must be **named** somewhere an agent
actually reads, or be listed here as deliberately unguided with the reason it is.

This is the missing inverse of ``tests/meta/test_documented_commands_resolve_against_cli.py``.
That guard walks from the prose to the CLI — a doc may not cite a verb that does not exist.
This one walks from the CLI to the prose — a verb may not exist uncited by the guidance the
agents in this repository read at session start. Both halves are static and fully enumerable;
neither says anything about whether an agent then chooses to run the command.

**The corpus** is the union of the surfaces an agent here is handed: the twelve generated skill
bodies (``squads``, ``greeting``, ``sq-memory`` and one ``sq-<type>`` per playbook-covered item
type), rendered here from the same templates ``sq skill <slug> show`` renders at read time, plus
this repository's own ``CLAUDE.md`` in full — both its managed section and the hand-written
contributor half above it, because the whole file is what an agent working in this repository
reads.

That last inclusion is load-bearing and worth stating plainly, because it bounds what a passing
run means. Measured against squads' *generated* output alone (the twelve skill bodies plus the
``CLAUDE.md`` managed section), five commands — ``graph``, ``import``, ``init``, ``migrate``,
``override`` — are named nowhere, and are credited here only by the hand-written contributor
half of this repository's ``CLAUDE.md``. Whether an agent needs to be told about a bootstrap or
upgrade verb is a judgement nobody has made yet, so this guard does not make it: it holds the
line for *this* repository's agent surfaces, and a squad adopting squads elsewhere would find
those five unnamed.

**The roster is pinned** (the eight bundled roles plus one developer, the same fixture the
skill-body goldens use). The generated ``sq-<type>`` text is roster-dependent through a has-dev
gate, so an unpinned corpus shifts underneath the assertion.

**The command inventory is de-aliased.** The live Typer table holds every item type's short
aliases as registered commands; leaving them in would demand guidance for ``feat``, ``rev``,
``prd`` and eleven more, and the guard would be noise. ``_top_level_commands`` subtracts them,
and ``test_the_command_inventory_is_de_aliased`` proves the subtraction actually happened rather
than leaving that to be inferred from a passing run.

**Matching is by name, not by invocation** — a case-insensitive word-boundary search over the
corpus. That is deliberately generous: a command whose name is also an ordinary English word
(``list``, ``show``, ``check``, ``guide``) is credited by any prose use of that word, so this
guard proves a name is *absent*, never that the guidance around a present name is any good. What
it closes is the class where a command ships and no agent-facing surface mentions it at all.
``test_the_matcher_is_validated_against_known_positives`` runs the matcher against terms that
must hit and one that must not, because a zero is the one search result that never proves the
search worked: an earlier byte-wise strip of the same corpus mangled multi-byte characters and
returned zero for every term, including obvious positives.
"""

import re
from pathlib import Path

import pytest
import typer.main

from squads import _docfiles
from squads._backends._base import RoleView
from squads._cli import app
from squads._interactions import (
    GREETING_SKILL,
    MEMORY_SKILL,
    SQUADS_SKILL,
    get_playbook_spec,
    item_skill_name,
    managed_item_types,
)
from squads._models._vocab import label_for
from squads._rendering._engine import render
from squads._services._base import _item_skill_role_sections
from squads._workflow import bundled_spec, linearize_lifecycle

#: Commands deliberately absent from agent guidance, each with the reason. Asserted in BOTH
#: directions — an unexempted command missing from the corpus fails, and an entry here whose
#: command IS named fails as stale — so this list cannot quietly rot into decoration.
_UNGUIDED_BY_DESIGN: dict[str, str] = {
    "ui": "an interactive full-screen TUI: an agent has no terminal to drive it and must not "
    "launch one",
}

#: The eight bundled roles plus one developer — the same pinned roster the skill-body and
#: managed-section goldens use, reproduced (not imported) because those live in tests/unit and
#: this suite has no cross-test-module import precedent.
_PINNED_ROSTER: list[RoleView] = [
    RoleView(slug="manager", full_name="Catherine Manager", title="manager", is_default=True),
    RoleView(slug="architect", full_name="Robert Architect", title="architect", is_default=False),
    RoleView(slug="tech-lead", full_name="Olivia Lead", title="tech lead", is_default=False),
    RoleView(slug="reviewer", full_name="Paul Reviewer", title="code reviewer", is_default=False),
    RoleView(slug="qa", full_name="Mara Tester", title="QA engineer", is_default=False),
    RoleView(slug="devops", full_name="Hugo Ops", title="DevOps engineer", is_default=False),
    RoleView(
        slug="product-owner", full_name="Nina Product", title="product owner", is_default=False
    ),
    RoleView(
        slug="tech-writer", full_name="Theo Writer", title="technical writer", is_default=False
    ),
    RoleView(
        slug="python-dev", full_name="Elias Python", title="Python developer", is_default=False
    ),
]


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def _top_level_commands() -> frozenset[str]:
    """Every registered top-level command name, with the item-type aliases subtracted.

    The same de-aliasing the ``RESERVED_CLI_VERBS`` lockstep guard performs
    (tests/meta/test_reserved_cli_verbs_matches_the_live_command_table.py): read the live Typer
    table, subtract what the bundled spec declares as an alias. Repeated rather than imported —
    ``tests/`` is not an importable package here and this suite has no ``from tests....``
    precedent.

    One deliberate difference from that guard: it also subtracts each type's canonical *name*,
    because its subject is the set of verbs a declared type may not collide with. This one keeps
    them. ``sq bug``, ``sq role`` and the rest are commands, and an agent is as entitled to find
    them named in guidance as ``sq check``.
    """
    aliases: set[str] = set()
    for item_spec in bundled_spec().items.values():
        aliases.update(item_spec.aliases)
    click_app = typer.main.get_command(app)
    return frozenset(click_app.commands.keys()) - aliases  # type: ignore[attr-defined]


def _generated_skill_bodies() -> dict[str, str]:
    """The twelve generated skill definitions, rendered the way the service renders them at
    read time (``ServiceCore.skill_definition_text``) against the pinned roster."""
    spec = bundled_spec()
    playbook = get_playbook_spec()
    roles = [{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in _PINNED_ROSTER]
    bodies = {
        f"skill:{SQUADS_SKILL}": render(
            "agents/squads_skill.md.j2",
            squad_dir="squads",
            spec=spec,
            roles=roles,
            playbook=playbook,
        ),
        f"skill:{GREETING_SKILL}": render("agents/greeting_skill.md.j2", squad_dir="squads"),
        f"skill:{MEMORY_SKILL}": render("agents/memory_skill.md.j2", squad_dir="squads"),
    }
    for item_type in managed_item_types(playbook):
        pb = playbook.types.get(item_type)
        kind = spec.item_subentity_kind(item_type)
        bodies[f"skill:{item_skill_name(item_type)}"] = render(
            "agents/item_skill.md.j2",
            title=label_for(item_type, "singular", spec),
            type=item_type,
            overview=pb.overview if pb is not None else "",
            lifecycle=linearize_lifecycle(spec.machine_for(item_type)),
            commands=list(pb.commands) if pb is not None else [],
            sections=_item_skill_role_sections(pb, _PINNED_ROSTER),
            subentity_kind=kind,
            subentity_plural=spec.subentity_plural(kind) if kind else None,
        )
    return bodies


def _agent_facing_corpus() -> str:
    surfaces = _generated_skill_bodies()
    surfaces["CLAUDE.md"] = (_repo_root() / "CLAUDE.md").read_text(encoding="utf-8")
    return "\n".join(surfaces.values())


def _names(term: str, corpus: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", corpus, re.IGNORECASE) is not None


@pytest.fixture(scope="module")
def corpus() -> str:
    text = _agent_facing_corpus()
    # A render carrying escape sequences would break every match below and look like a corpus
    # of missing commands; the harness sets FORCE_COLOR, so this is not hypothetical.
    assert "\x1b[" not in text
    return text


def test_every_top_level_command_is_named_in_the_agent_facing_corpus(corpus: str) -> None:
    unnamed = sorted(
        c for c in _top_level_commands() if c not in _UNGUIDED_BY_DESIGN and not _names(c, corpus)
    )
    assert not unnamed, (
        "shipped top-level command(s) named in no surface an agent reads: "
        f"{unnamed} — add them to the agent-facing guidance (the workflow cheatsheet and the "
        f"`{SQUADS_SKILL}` skill body are the usual home), or, if an agent genuinely should "
        "never run one, add it to _UNGUIDED_BY_DESIGN with the reason"
    )


def test_no_command_exempted_as_unguided_is_actually_named(corpus: str) -> None:
    """The other direction: an exemption that has stopped being true fails as stale, so the
    list cannot outlive the judgement that put an entry on it."""
    stale = sorted(c for c in _UNGUIDED_BY_DESIGN if _names(c, corpus))
    assert not stale, (
        f"_UNGUIDED_BY_DESIGN exempts {stale}, but the agent-facing guidance now names them — "
        "drop the stale entry"
    )


def test_every_exemption_names_a_command_that_exists() -> None:
    """A misspelled or since-removed exemption key would sit in the list forever, exempting
    nothing and silently passing the staleness check above (a name nobody wrote is a name
    nobody wrote)."""
    unknown = sorted(set(_UNGUIDED_BY_DESIGN) - _top_level_commands())
    assert not unknown, f"_UNGUIDED_BY_DESIGN names non-existent command(s): {unknown}"


def test_the_command_inventory_is_de_aliased() -> None:
    """Non-vacuity for the subtraction: the raw table is strictly larger, every declared alias
    is gone, and the canonical names those aliases stand for are still there."""
    click_app = typer.main.get_command(app)
    raw = frozenset(click_app.commands.keys())  # type: ignore[attr-defined]
    commands = _top_level_commands()
    declared_aliases = {a for s in bundled_spec().items.values() for a in s.aliases}
    assert declared_aliases  # the bundled spec really does declare aliases
    assert declared_aliases <= raw  # ...and they really are registered as commands
    assert len(commands) == len(raw) - len(declared_aliases)
    assert not (declared_aliases & commands)
    assert {"bug", "feature", "review", "contract"} <= commands  # canonical names kept


def test_the_matcher_is_validated_against_known_positives(corpus: str) -> None:
    """A zero hit is the one search result that never proves the search worked. Anchor the
    matcher on terms that must be present and one that must not, so a corpus that failed to
    build (or got mangled on the way in) fails here rather than passing everything above."""
    assert len(corpus) > 10_000
    for present in ("create", "comment", "tree", "check", "discussion"):
        assert _names(present, corpus), f"matcher found no {present!r} — the corpus is broken"
    assert not _names("zzz-not-a-squads-word", corpus)
