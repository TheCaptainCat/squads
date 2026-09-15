"""Repo gate: every shipped top-level ``sq`` command must be **named** somewhere an agent
actually reads, or be listed here as deliberately unguided with the reason it is.

This is the missing inverse of ``tests/meta/test_documented_commands_resolve_against_cli.py``.
That guard walks from the prose to the CLI — a doc may not cite a verb that does not exist.
This one walks from the CLI to the prose — a verb may not exist uncited by the guidance the
agents in this repository read at session start. Both halves are static and fully enumerable;
neither says anything about whether an agent then chooses to run the command.

**The corpus is squads' generated output, and only that**: the twelve generated skill bodies
(``squads``, ``greeting``, ``sq-memory`` and one ``sq-<type>`` per playbook-covered item type),
rendered here from the same templates ``sq skill <slug> show`` renders at read time, plus the
managed section of this repository's ``CLAUDE.md`` — taken by its ``squads:start``/``squads:end``
markers, because that section is rendered from a bundled template and every adopting squad
receives it.

The hand-written contributor half of that file, above the markers, is deliberately **not**
measured. It is prose this repository wrote for its own contributors, and no adopting squad has
it; a command credited only there is a command squads does not name anywhere it ships. Including
it made a green run certify this repository's agent surfaces rather than the product's, which is
a false assurance rather than a weak one. So the subject here is what an agent reads in *any*
squad, not what an agent reads in this one.

The extraction asserts the region it finds is non-empty. A marker rename that silently returned
nothing would redden this gate for reasons that have nothing to do with guidance, and an
extraction failure wearing the costume of a real finding is the worst outcome this guard can
have.

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

That generosity is live rather than hypothetical, and ``adopt`` is the measured case: it is
credited by two uses of the ordinary English verb in the managed section's impersonation
paragraph, while the string ``sq adopt`` appears in no generated surface. Tightening the match
to an invocation form would withdraw credit from several more commands whose names double as
prose, each of which is its own question about whether that entry point is guided at all — a
change to what this guard *asserts*, not a correction of what it reads, and one that is
deliberately not made here.
``test_the_matcher_is_validated_against_known_positives`` runs the matcher against terms that
must hit and one that must not, because a zero is the one search result that never proves the
search worked: an earlier byte-wise strip of the same corpus mangled multi-byte characters and
returned zero for every term, including obvious positives.

``reflog`` was the second measured case of that generosity, and unlike ``adopt`` it had no
ruling behind it: it was credited by a single sentence using the word as an ordinary noun to
explain what a sequence-number gap means, while no surface named the command. It is guided now —
the cheatsheet carries a section on it, which the ``squads`` skill body and the AGENTS.md section
both include — and ``test_the_mutation_audit_command_is_named_as_an_invocation`` holds it there
at invocation strength, so deleting that guidance cannot fall back onto the word and stay green.
That test is targeted rather than a general tightening, for the reason the paragraph above gives.

**The corpus asserts its own size**, not only the matcher's behaviour. Validating the matcher
against known positives is necessary and not sufficient, and two distinct broken-corpus shapes
have each defeated a weaker version of that check. A corpus assembled from the on-disk skill
stubs' *body region only* is 0-1 characters per carrier — the shape a first, too-low floor caught.
But a corpus assembled by reading those same stub files *whole* (frontmatter included, the way a
naive "read the file" corpus builder does it) lands at 377-611 characters per carrier on this
repository's own squad, and 327-579 on a fresh ``sq init --default-names`` scratch squad —
comfortably above that first floor, and above
``test_the_matcher_is_validated_against_known_positives``'s own ``len(corpus) > 10_000`` check too,
since the genuine ``CLAUDE.md`` managed region alone clears that on its own and carries several of
the known-positive terms. Neither check caught it; the smallest *genuine* rendered skill body
measured well over 1,000 characters wherever the frontmatter-only stubs measured well under it,
which is the gap ``_MIN_CARRIER_CHARS`` is now calibrated against — not "empty", but "no larger
than a frontmatter-only stub". ``_agent_facing_corpus`` therefore refuses a carrier that renders
anywhere near stub size and refuses a corpus missing carriers outright, catching both shapes
rather than only the emptier one.

As a second, independent layer — because a size floor can only ever be calibrated against shapes
that have actually occurred, not against every shape that could — the broad assertion below also
checks a handful of known-positive terms in the same run it checks for unnamed commands, exactly
as ``test_the_mutation_audit_command_is_named_as_an_invocation`` already did for the reflog case.
A broken corpus that somehow slipped past the size floor still can't be reported as "these commands
lack guidance"; it reports as broken instead.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer.main

from squads import _docfiles
from squads._backends import _managed_region
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
from squads._models._item import Item
from squads._rendering._engine import render
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
        ),
        f"skill:{GREETING_SKILL}": render(
            "views/greeting_skill.md.j2",
            source=_PROBE_SKILL_ITEM,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
        ),
        f"skill:{MEMORY_SKILL}": render(
            "views/memory_skill.md.j2",
            source=_PROBE_SKILL_ITEM,
            item=_PROBE_SKILL_ITEM,
            spec=spec,
            squad_dir="squads",
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
    """Controls run first, in the same assertion: a corpus missing even the terms every genuine
    render carries is broken, and must be reported that way rather than as a list of real
    commands with missing guidance — the misattribution ``_MIN_CARRIER_CHARS`` alone is not
    guaranteed to catch, since a size floor is only ever calibrated against shapes already seen."""
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
    for present in _KNOWN_POSITIVE_TERMS:
        assert _names(present, corpus), f"matcher found no {present!r} — the corpus is broken"
    assert not _names("zzz-not-a-squads-word", corpus)


def test_the_mutation_audit_command_is_named_as_an_invocation(corpus: str) -> None:
    """``sq reflog`` is named as something to run, not merely as a word.

    The name-matcher above credits ``reflog`` from one sentence that uses it as an ordinary noun
    while explaining sequence-number gaps, so it alone cannot tell guidance from a passing
    mention. This is the command an agent reaches for to audit what another agent changed — the
    one question the item files and ``sq check`` cannot answer, since they carry the state
    reached rather than the moves that reached it — so its absence would not be caught by the
    surface that exists to catch exactly that.

    Controls run in the same assertion: a zero on the subject with zeros on the controls means a
    broken corpus, not missing guidance.
    """
    controls = {c: corpus.count(f"sq {c}") for c in ("repair", "graph", "renumber")}
    assert all(controls.values()), f"controls absent — the corpus is broken: {controls}"
    assert corpus.count("sq reflog") > 0, (
        "no generated surface names `sq reflog` as an invocation; the word alone appears in "
        f"prose about sequence gaps and would keep this guard green (controls: {controls})"
    )
