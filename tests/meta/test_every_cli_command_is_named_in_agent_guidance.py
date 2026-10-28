"""Repo gate: every shipped top-level ``sq`` command must be **named** somewhere an agent actually
reads, or be listed here as deliberately unguided with the reason it is."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer.main

from squads import _docfiles
from squads._backends import _managed_region
from squads._cli import app
from squads._interactions._playbook import get_playbook_spec, managed_item_types
from squads._interactions._skills import GREETING_SKILL, MEMORY_SKILL, SQUADS_SKILL, item_skill_name
from squads._language import WorkingLanguage
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._projection import RoleView
from squads._views import PlaybookSource
from squads._workflow import bundled_spec

#: Commands deliberately absent from agent guidance, each with the reason. Asserted in BOTH
#: directions — an unexempted command missing from the corpus fails, and an entry here whose
#: command IS named fails as stale — so this list cannot quietly rot into decoration.
_UNGUIDED_BY_DESIGN: dict[str, str] = {
    "ui": "an interactive full-screen TUI: an agent has no terminal to drive it and must not "
    "launch one",
    "init": "bootstrap — the class, not the one verb: generated guidance ships *inside* a squad "
    "and is only ever read by an agent for whom one already exists, so a verb whose job is to "
    "bring a squad into being cannot reach the reader who needs it. Text naming it here would be "
    "unactionable by construction, and the surfaces that can reach that reader (the root "
    "`--help`, which anyone runs first on an unfamiliar CLI, and the offline docs) already name "
    "it. The non-destructive sibling that adopts an existing folder is the same class and the "
    "same ruling, and carries no entry of its own for a reason that is an artefact of the "
    "matcher rather than an inconsistency: its name is also an ordinary English verb, used that "
    "way in the impersonation paragraph of the managed section, so the name-matcher already "
    "credits it as named. `sq adopt` appears in no generated surface at all — that was measured, "
    "not assumed — but an entry for it here would fail the staleness assertion below instead of "
    "recording the ruling.",
}

#: The eight bundled roles plus one developer.
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

#: A well-formed but otherwise inert host item for ``views/squads_skill.md.j2``/
#: ``views/memory_skill.md.j2`` — neither reads any ``item.*`` field, so its content is
#: arbitrary; it exists only because ``render_source_view``'s context always carries one.
_PROBE_SKILL_ITEM = Item(
    sequence_id=1,
    type="skill",
    title="squads",
    slug="squads",
    status="Active",
    path="agents/skills/SKILL-000001-squads.md",
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
)


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def _top_level_commands() -> frozenset[str]:
    """Every registered top-level command name, with the item-type aliases subtracted."""
    aliases: set[str] = set()
    for item_spec in bundled_spec().items.values():
        aliases.update(item_spec.aliases)
    click_app = typer.main.get_command(app)
    return frozenset(click_app.commands.keys()) - aliases  # type: ignore[attr-defined]


def _generated_skill_bodies() -> dict[str, str]:
    """The twelve generated skill definitions, rendered the way a read expands each skill's own
    ``sq:view:<name>`` placement tag, against the pinned roster."""
    spec = bundled_spec()
    playbook = get_playbook_spec()
    playbook_source = PlaybookSource(
        item_type="skill", lane=None, roster=_PINNED_ROSTER, playbook=playbook
    )
    bodies = {
        f"skill:{SQUADS_SKILL}": render(
            "views/squads_skill.md.j2",
            source=playbook_source,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
            working_language=WorkingLanguage("en", "English"),
            from_squad=None,
        ),
        f"skill:{GREETING_SKILL}": render(
            "views/greeting_skill.md.j2",
            source=_PROBE_SKILL_ITEM,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
            working_language=WorkingLanguage("en", "English"),
            from_squad=None,
        ),
        f"skill:{MEMORY_SKILL}": render(
            "views/memory_skill.md.j2",
            source=_PROBE_SKILL_ITEM,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
            working_language=WorkingLanguage("en", "English"),
            from_squad=None,
        ),
    }
    for item_type in managed_item_types(playbook):
        pb = playbook.types.get(item_type)
        item_skill_source = PlaybookSource(
            item_type=item_type, lane=pb, roster=_PINNED_ROSTER, playbook=playbook
        )
        bodies[f"skill:{item_skill_name(item_type)}"] = render(
            "views/item_skill.md.j2",
            source=item_skill_source,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
            working_language=WorkingLanguage("en", "English"),
            from_squad=None,
        )
    return bodies


def _managed_claude_section() -> str:
    """The generated half of this repository's ``CLAUDE.md``, located by its markers.

    By markers rather than by a line offset, so the split cannot drift as the hand-written
    contributor prose above it grows or shrinks; non-empty is asserted here rather than left
    to be inferred from a passing run downstream.
    """
    text = (_repo_root() / "CLAUDE.md").read_text(encoding="utf-8")
    start, end = text.find(_managed_region.START), text.find(_managed_region.END)
    assert start != -1 and end > start, (
        "no managed region found in CLAUDE.md between "
        f"{_managed_region.START!r} and {_managed_region.END!r} — the corpus is broken, "
        "not the guidance"
    )
    section = text[start + len(_managed_region.START) : end]
    assert section.strip(), "the CLAUDE.md managed region extracted empty — the corpus is broken"
    return section


#: Below this many characters a carrier is a stub rather than a render. Calibrated against the
#: shape that actually occurs — a frontmatter-only carrier (an on-disk skill ``.md`` file read
#: whole, body empty because a skill definition renders at read time), measured at 327-611
#: characters across this repository's own squad and a fresh scratch squad — not against an empty
#: carrier, which no real corpus builder produces. The smallest genuine rendered skill body clears
#: 1,000 characters with room to spare, so this sits with headroom on both sides: comfortably
#: above every measured frontmatter-only stub, comfortably below every measured genuine render.
_MIN_CARRIER_CHARS = 1000

#: The three always-present skill bodies (``squads``, ``greeting``, ``sq-memory``) plus one
#: ``sq-<type>`` per playbook-covered type, plus the managed section. Held as a floor rather than
#: an equality so declaring a new item type does not redden this gate.
_MIN_CARRIERS = 6


def _agent_facing_corpus() -> str:
    """Every generated surface, joined — with the corpus's own integrity asserted first.

    A carrier that renders empty makes every absence below unfalsifiable, and an absence that is
    really an extraction failure is the finding this guard most has to avoid manufacturing.
    """
    surfaces = _generated_skill_bodies()
    surfaces["CLAUDE.md:managed"] = _managed_claude_section()
    assert len(surfaces) >= _MIN_CARRIERS, (
        f"only {len(surfaces)} carrier(s) in the corpus — the corpus is broken, not the guidance"
    )
    stubs = sorted(k for k, v in surfaces.items() if len(v) < _MIN_CARRIER_CHARS)
    assert not stubs, (
        f"carrier(s) rendered under {_MIN_CARRIER_CHARS} characters: {stubs} — the corpus is "
        "broken, not the guidance"
    )
    return "\n".join(surfaces.values())


def _names(term: str, corpus: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", corpus, re.IGNORECASE) is not None


#: Terms present in every genuine corpus this guard has measured, reused as controls in more than
#: one assertion below. A zero on all of these alongside zeros on the assertion's own subject
#: means the corpus is broken, not that guidance is missing — the same distinction
#: ``test_the_mutation_audit_command_is_named_as_an_invocation`` already draws for ``reflog``,
#: generalised here for the broad assertion, which has no single always-guided subject of its own
#: to lean on.
_KNOWN_POSITIVE_TERMS = ("create", "comment", "tree", "check", "discussion")


@pytest.fixture(scope="module")
def corpus() -> str:
    text = _agent_facing_corpus()
    # A render carrying escape sequences would break every match below and look like a corpus
    # of missing commands; the harness sets FORCE_COLOR, so this is not hypothetical.
    assert "\x1b[" not in text
    return text


def test_every_top_level_command_is_named_in_the_agent_facing_corpus(corpus: str) -> None:
    """Controls run first."""
    controls = {term: _names(term, corpus) for term in _KNOWN_POSITIVE_TERMS}
    assert all(controls.values()), (
        f"known-positive term(s) absent — the corpus is broken, not the guidance: "
        f"{sorted(t for t, present in controls.items() if not present)}"
    )
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
    """The other direction: an exemption that has stopped being true fails as stale."""
    stale = sorted(c for c in _UNGUIDED_BY_DESIGN if _names(c, corpus))
    assert not stale, (
        f"_UNGUIDED_BY_DESIGN exempts {stale}, but the agent-facing guidance now names them — "
        "drop the stale entry"
    )


def test_every_exemption_names_a_command_that_exists() -> None:
    """A misspelled or since-removed exemption key would sit in the list forever."""
    unknown = sorted(set(_UNGUIDED_BY_DESIGN) - _top_level_commands())
    assert not unknown, f"_UNGUIDED_BY_DESIGN names non-existent command(s): {unknown}"


def test_the_command_inventory_is_de_aliased() -> None:
    """Non-vacuity for the subtraction: the raw table is strictly larger."""
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
    """A zero hit is the one search result that never proves the search worked."""
    assert len(corpus) > 10_000
    for present in _KNOWN_POSITIVE_TERMS:
        assert _names(present, corpus), f"matcher found no {present!r} — the corpus is broken"
    assert not _names("zzz-not-a-squads-word", corpus)


def test_the_mutation_audit_command_is_named_as_an_invocation(corpus: str) -> None:
    """``sq reflog`` is named as something to run, not merely as a word."""
    controls = {c: corpus.count(f"sq {c}") for c in ("repair", "graph", "renumber")}
    assert all(controls.values()), f"controls absent — the corpus is broken: {controls}"
    assert corpus.count("sq reflog") > 0, (
        "no generated surface names `sq reflog` as an invocation; the word alone appears in "
        f"prose about sequence gaps and would keep this guard green (controls: {controls})"
    )
